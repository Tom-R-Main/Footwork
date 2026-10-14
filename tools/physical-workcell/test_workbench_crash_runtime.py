"""Real SIGKILL host qualification at an externally withheld, known body reply.

The deterministic planners are diagnostic only, never paid model evidence.
"""
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import body_client
import body_network
import codex_policy
import network_operator_runtime as runtime
import order_protocol as protocol

BASE = Path(__file__).resolve().parent


def free_port():
    with socket.socket() as transport:
        transport.bind(("127.0.0.1", 0))
        return transport.getsockname()[1]


def descendants(pid):
    result = subprocess.run(["ps", "-axo", "pid=,ppid=,comm="], capture_output=True, text=True, check=True)
    table = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) == 3:
            table[int(parts[0])] = {"pid": int(parts[0]), "ppid": int(parts[1]), "name": Path(parts[2]).name}
    owned = {pid}
    while True:
        added = {child for child, info in table.items() if info["ppid"] in owned} - owned
        if not added:
            break
        owned.update(added)
    return [table[child] for child in sorted(owned - {pid})]


def fixture(root, port, mode):
    def policy(challenge, *_):
        log = root / "diagnostic-policy.jsonl"
        previous = log.read_text().splitlines() if log.exists() else []
        with log.open("a") as sink:
            sink.write(json.dumps({"challenge_id": challenge["challenge_id"],
                "generation": challenge["observation"]["generation"]}) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
        return {"action": "move" if not previous else "stop", "target_x": -.25 if not previous else None,
                "target_y": 0 if not previous else None, "intent": "Deterministic hard-crash conformance"}, {}

    if mode == "server":
        import network_bench_operator
        network_bench_operator.serve(root, port, policy)
        return
    if mode in {"planner", "planner-before"}:
        import network_bench_operator
        original_launch = codex_policy.subprocess.Popen
        def launch_guard(*args, **kwargs):
            argv = args[0]
            if mode == "planner-before" and str(runtime.BASE / "planner_guard.py") in argv:
                protocol.create_file(root / "pre-guardian.json", protocol.encoded({"pid": os.getpid()}))
                os.kill(os.getpid(), signal.SIGSTOP)
            return original_launch(*args, **kwargs)
        with patch.object(codex_policy, "preflight", return_value={"available": True, "cli_version": codex_policy.EXPECTED_CLI}), \
                patch.object(codex_policy.shutil, "which", return_value=str(root.parent / "fake-cli")), \
                patch.object(codex_policy.subprocess, "Popen", side_effect=launch_guard):
            network_bench_operator.serve(root, port, codex_policy.decide)
        return
    op = runtime.Operator(root, policy, start_worker=False)
    original = protocol.persist
    def stop_after_event(path, value):
        if path == root / "operator.json" and value["activity"][-1]["kind"] == "diagnostic_tail":
            protocol.create_file(root / "tail-barrier.json", protocol.encoded({"pid": os.getpid(), "sequence": value["sequence"]}))
            os.kill(os.getpid(), signal.SIGSTOP)
        return original(path, value)
    protocol.persist = stop_after_event
    op._event("diagnostic_tail", outcome="Known event file, not yet published in host manifest")
    raise AssertionError("publication-tail fixture continued without its external controller")


class ReceiptGate:
    """External fault owner; never changes command bytes or body receipts."""
    def __init__(self, upstream):
        self.upstream = upstream
        self.held, self.release = threading.Event(), threading.Event()
        self.lock = threading.Lock()
        self.records = []
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def handle_request(self):
                payload = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                headers = {key: self.headers[key] for key in ("X-Body-Id", "X-Adapter-Id", "X-Source-Sha256") if key in self.headers}
                try:
                    status, reply = body_client.http_call(owner.upstream, self.command, self.path, headers,
                        payload if self.command == "POST" else None, timeout=15, maximum=body_client.MAX_IMAGE)
                    request = protocol.decode(payload) if self.command == "POST" else None
                    entry = {"method": self.command, "path": self.path, "request": request,
                             "request_sha256": protocol.sha(payload), "response_sha256": protocol.sha(reply), "status": status}
                    with owner.lock:
                        owner.records.append(entry)
                    if request and request.get("operation") == "dispatch" and not owner.held.is_set():
                        envelope = protocol.decode(reply)
                        if envelope["state"] != "completed":
                            raise AssertionError("gate requires independent body completion before host death")
                        owner.envelope = envelope
                        owner.held.set()
                        owner.release.wait(20)
                    self.send_response(status)
                    self.send_header("Content-Length", str(len(reply)))
                    self.send_header("Content-Type", "image/png" if self.path.startswith("/images/") else "application/json")
                    self.end_headers()
                    self.wfile.write(reply)
                except (OSError, BrokenPipeError):
                    self.close_connection = True
            do_GET = handle_request
            do_POST = handle_request
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.origin = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .1}, daemon=True)
        self.thread.start()

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.thread.join(3)
        self.server.server_close()


class WorkbenchCrashRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.root = BASE / "output" / ("sim13-host-crash-" + uuid.uuid4().hex[:10])
        self.root.mkdir(mode=0o700)
        self.body_root = self.root / "body"
        body_network.initialize(self.body_root, diagnostic_enabled=True)
        self.body = body_network.BodyService(self.body_root).start()
        self.gate = ReceiptGate(self.body.origin)
        self.host = self.root / "host"
        runtime.initialize(self.host, self.gate.origin)
        self.processes, self.sinks = [], []
        self.evidence = {"policy": "explicitly_fake_diagnostic", "case": self.id(), "processes": []}
        self.op = None

    def tearDown(self):
        self.gate.release.set()
        if self.op:
            self.op.close()
        for child in self.processes:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(5)
            self.evidence["processes"].append({"pid": child.pid, "exit_code": child.returncode})
        self.gate.close()
        self.body.close()
        for sink in self.sinks:
            sink.close()
        self.evidence["relay"] = self.gate.records
        self.evidence["host_state"] = body_client.read_journal(self.host / "operator.json")
        failed = any(test is self for test, _ in (*self._outcome.result.failures, *self._outcome.result.errors))
        self.evidence["passed"] = not failed
        protocol.create_file(self.root / "conformance.json", protocol.encoded(self.evidence))

    def launch(self, port, mode="server"):
        sink = (self.root / f"child-{len(self.processes)}.log").open("wb")
        self.sinks.append(sink)
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--fixture", mode,
            "--root", str(self.host), "--port", str(port)], stdout=sink, stderr=subprocess.STDOUT)
        self.processes.append(child)
        return child

    def wait(self, predicate, timeout=15):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            if predicate():
                return
            time.sleep(.02)
        self.fail("owned crash fixture did not reach its declared boundary")

    def read_state(self, origin):
        try:
            status, content = body_client.http_call(origin, "GET", "/api/state", timeout=1)
            return protocol.decode(content) if status == 200 else None
        except (OSError, ValueError):
            return None

    def post(self, origin, app_id, route, value):
        status, content = body_client.http_call(origin, "POST", route,
            {"Origin": origin, "X-Footwork-App-ID": app_id, "Content-Type": "application/json"}, protocol.encoded(value))
        self.assertEqual(status, 200, content.decode())
        return protocol.decode(content)

    def test_sigkill_host_after_known_body_effect_recovers_exact_receipt_without_replay(self):
        port = free_port()
        origin = f"http://127.0.0.1:{port}"
        child = self.launch(port)
        self.wait(lambda: self.read_state(origin) is not None)
        initial = self.read_state(origin)
        self.post(origin, initial["app_id"], "/api/jobs",
            {"job_id": "crash-one", "label": "Owned host crash", "target": "A", "disturbance_test": False})
        self.assertTrue(self.gate.held.wait(15))
        before = body_client.read_journal(self.host / "client" / "client.json")
        token = self.gate.envelope["command_id"]
        self.assertEqual(before["pending_command_ids"], [token])
        self.assertEqual(self.body.body.status()["generation"], 1)
        self.evidence["children_at_dispatch_gate"] = descendants(child.pid)
        self.assertEqual(self.evidence["children_at_dispatch_gate"], [])
        child.kill()
        self.assertEqual(child.wait(5), -signal.SIGKILL)
        retained = body_client.read_journal(self.host / "operator.json")
        self.assertEqual(retained["stage"]["operation"], "dispatch")
        self.assertNotIn(token, retained["applied_commands"])
        self.gate.release.set()
        restarted = self.launch(port)
        self.wait(lambda: self.read_state(origin) is not None)
        recovered = self.read_state(origin)
        self.assertEqual(recovered["app_id"], initial["app_id"])
        self.assertEqual(recovered["runner_status"], "blocked")
        self.assertEqual(recovered["recovery"]["command_id"], token)
        self.assertEqual(len(body_client.read_journal(self.host / "client" / "client.json")["commands"]), len(before["commands"]))
        calls = (self.host / "diagnostic-policy.jsonl").read_text().splitlines()
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.read_state(origin)["jobs"][0]["status"], "unknown")
        settled = self.post(origin, initial["app_id"], "/api/reconcile", {})
        self.assertEqual(settled["runner_status"], "paused")
        self.assertEqual(settled["recovery"]["state"], "recovered")
        self.assertEqual(body_client.read_journal(self.host / "operator.json")["applied_commands"].count(token), 1)
        self.assertEqual(len(body_client.read_journal(self.host / "client" / "client.json")["commands"]), len(before["commands"]))
        self.post(origin, initial["app_id"], "/api/resume", {})
        self.wait(lambda: self.read_state(origin)["runner_status"] == "paused")
        calls = [json.loads(line) for line in (self.host / "diagnostic-policy.jsonl").read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0]["challenge_id"], calls[1]["challenge_id"])
        self.assertEqual(calls[1]["generation"], 1)
        self.assertEqual(self.body.body.status()["generation"], 1)
        self.assertEqual(body_client.read_journal(self.host / "client" / "client.json")["commands"][token]["send_count"], 1)
        dispatches = [r for r in self.gate.records if r["request"] and r["request"].get("operation") == "dispatch"]
        self.assertEqual([r["request"]["command_id"] for r in dispatches], [token])
        self.assertEqual(self.gate.envelope["recorded_epoch"], self.body.epoch)
        self.evidence.update(command_id=token, before_count=len(before["commands"]), challenges=calls,
            recovered=recovered, settled=settled, original_body_receipt=self.gate.envelope)
        restarted.terminate()
        self.assertEqual(restarted.wait(10), 0)

    def test_publication_tail_sigkill_repairs_only_audit_index_without_replay(self):
        child = self.launch(0, "publication-tail")
        self.wait(lambda: (self.host / "tail-barrier.json").exists())
        marker = protocol.decode(protocol.read_bytes(self.host / "tail-barrier.json"))
        saved = body_client.read_journal(self.host / "operator.json")
        self.assertEqual(marker["sequence"], saved["sequence"] + 1)
        self.assertTrue((self.host / "events" / f"{marker['sequence']:06d}.json").exists())
        child.kill()
        self.assertEqual(child.wait(5), -signal.SIGKILL)
        self.op = runtime.Operator(self.host, lambda *_: self.fail("tail restart ran planner"), start_worker=False)
        self.assertEqual(self.op.state()["runner_status"], "paused")
        self.assertEqual(self.op.m["activity"][-1]["kind"], "journal_recovered")
        self.op.resume()
        self.assertEqual(self.op.state()["runner_status"], "running")
        self.evidence["recovery"] = {"boundary": "event-fsync-before-manifest-publication",
            "sequence": marker["sequence"], "effect_commands": 0}
        self.assertEqual(len(self.op._journal()["commands"]), 0)

    def test_active_planner_host_sigkill_retires_group_and_resume_uses_fresh_image(self):
        fake = self.root / "fake-cli"
        fake.write_text("#!" + sys.executable + "\n" + '''import json,os,subprocess,sys,time
from pathlib import Path
args=sys.argv[1:]
out=Path(args[args.index('--output-last-message')+1])
call=out.parent
sys.stdin.read()
if call.name.endswith('-01'):
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)'])
    (call/'child-ready.json').write_text(json.dumps({'pid':os.getpid(),'child_pid':child.pid}))
    while True:
        print(json.dumps({'type':'diagnostic_heartbeat'}),flush=True)
        time.sleep(.05)
out.write_text(json.dumps({'action':'stop','target_x':None,'target_y':None,'intent':'Fresh fake planner after crash.'}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':20,'output_tokens':10}}))
''')
        fake.chmod(0o700)
        port = free_port()
        origin = f"http://127.0.0.1:{port}"
        child = self.launch(port, "planner")
        self.wait(lambda: self.read_state(origin) is not None)
        initial = self.read_state(origin)
        self.post(origin, initial["app_id"], "/api/jobs",
            {"job_id": "planner-crash", "label": "Active planner crash", "target": "A", "disturbance_test": False})
        call = self.host / "calls" / "planner-crash-01"
        self.wait(lambda: (call / "child-ready.json").exists())
        startup = protocol.decode(protocol.read_bytes(call / "planner-process.json"))
        pids = protocol.decode(protocol.read_bytes(call / "child-ready.json"))
        self.assertEqual(startup["planner_pid"], pids["pid"])
        self.assertEqual(os.getpgid(pids["pid"]), startup["planner_pgid"])
        self.assertEqual(os.getpgid(pids["child_pid"]), startup["planner_pgid"])
        before = body_client.read_journal(self.host / "client" / "client.json")
        challenge = protocol.decode(protocol.read_bytes(call / "reservation.json"))["challenge"]
        owner = body_client.read_journal(self.host / "operator.json")["planner_owner"]
        child.kill()  # Host PID only: the separate guardian must detect EOF.
        self.assertEqual(child.wait(5), -signal.SIGKILL)
        self.wait(lambda: (call / "planner-closure.json").exists(), timeout=12)
        closure = protocol.decode(protocol.read_bytes(call / "planner-closure.json"))
        self.assertEqual(closure["reason"], "host liveness pipe closed")
        self.assertTrue(closure["group_closed"])
        for pid in pids.values():
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
        before_bytes = (call / "events.jsonl").read_bytes()
        self.launch(port, "planner")
        self.wait(lambda: self.read_state(origin) is not None)
        paused = self.read_state(origin)
        self.assertEqual(paused["runner_status"], "paused")
        self.assertEqual(paused["jobs"][0]["status"], "paused")
        self.assertEqual(paused["activity"][-1]["kind"], "planner_retired")
        self.assertNotEqual(body_client.read_journal(self.host / "operator.json")["planner_owner"], owner)
        self.assertEqual(len(body_client.read_journal(self.host / "client" / "client.json")["commands"]), len(before["commands"]))
        self.assertFalse((call / "decision.json").exists())
        self.post(origin, initial["app_id"], "/api/resume", {})
        next_call = self.host / "calls" / "planner-crash-02"
        self.wait(lambda: (next_call / "decision.json").exists())
        next_challenge = protocol.decode(protocol.read_bytes(next_call / "reservation.json"))["challenge"]
        self.assertNotEqual(next_challenge["challenge_id"], challenge["challenge_id"])
        self.assertEqual((call / "events.jsonl").read_bytes(), before_bytes)
        self.assertEqual(self.body.body.status()["generation"], 0)
        self.assertFalse(any(r["request"] and r["request"].get("operation") == "dispatch" for r in self.gate.records))
        self.evidence.update(guardian=startup, closure=closure, paused=paused, no_dispatch=True,
            challenge_before=challenge["challenge_id"], challenge_after=next_challenge["challenge_id"])

    def test_host_sigkill_before_guardian_launch_keeps_reserved_budget_without_replay(self):
        fake = self.root / "fake-cli"
        fake.write_text("#!" + sys.executable + "\n" + '''import json,sys
from pathlib import Path
args=sys.argv[1:]
sys.stdin.read()
out=Path(args[args.index('--output-last-message')+1])
out.write_text(json.dumps({'action':'stop','target_x':None,'target_y':None,'intent':'Fresh pre-launch recovery.'}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':20,'output_tokens':10}}))
''')
        fake.chmod(0o700)
        port = free_port()
        origin = f"http://127.0.0.1:{port}"
        child = self.launch(port, "planner-before")
        self.wait(lambda: self.read_state(origin) is not None)
        initial = self.read_state(origin)
        self.post(origin, initial["app_id"], "/api/jobs",
            {"job_id": "planner-before", "label": "Planner pre-launch crash", "target": "A", "disturbance_test": False})
        self.wait(lambda: (self.host / "pre-guardian.json").exists())
        call = self.host / "calls" / "planner-before-01"
        self.assertTrue((call / "planner-intent.json").exists())
        self.assertFalse((call / "planner-process.json").exists())
        before = body_client.read_journal(self.host / "client" / "client.json")
        self.assertEqual(descendants(child.pid), [])
        child.kill()
        self.assertEqual(child.wait(5), -signal.SIGKILL)
        self.launch(port, "planner")
        self.wait(lambda: self.read_state(origin) is not None)
        paused = self.read_state(origin)
        self.assertEqual(paused["runner_status"], "paused")
        self.assertEqual(paused["jobs"][0]["call_count"], 1)
        self.assertEqual(paused["usage"]["calls"], 1)
        self.assertEqual(paused["activity"][-1]["kind"], "planner_retired")
        self.assertEqual(len(body_client.read_journal(self.host / "client" / "client.json")["commands"]), len(before["commands"]))
        self.post(origin, initial["app_id"], "/api/resume", {})
        next_call = self.host / "calls" / "planner-before-02"
        self.wait(lambda: (next_call / "decision.json").exists())
        first = protocol.decode(protocol.read_bytes(call / "reservation.json"))["challenge"]
        second = protocol.decode(protocol.read_bytes(next_call / "reservation.json"))["challenge"]
        self.assertNotEqual(first["challenge_id"], second["challenge_id"])
        self.assertFalse((call / "decision.json").exists())
        self.assertEqual(self.body.body.status()["generation"], 0)
        self.evidence.update(paused=paused, pre_guardian_kill=True, no_dispatch=True,
            challenge_before=first["challenge_id"], challenge_after=second["challenge_id"])


if __name__ == "__main__":
    if "--fixture" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--fixture", choices=("server", "publication-tail", "planner", "planner-before"), required=True)
        parser.add_argument("--root", type=Path, required=True)
        parser.add_argument("--port", type=int, required=True)
        args = parser.parse_args()
        fixture(args.root, args.port, args.fixture)
    else:
        unittest.main()
