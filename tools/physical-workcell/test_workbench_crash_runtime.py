"""Real SIGKILL host qualification at an externally withheld, known body reply.

The deterministic planner is diagnostic only. The publication-tail case records
an explicit current recovery limitation, rather than claiming arbitrary crashes.
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

import body_client
import body_network
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

    def test_publication_tail_sigkill_is_retained_as_explicit_recovery_limit(self):
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
        with self.assertRaises(FileExistsError) as refusal:
            self.op.resume()
        self.evidence["explicit_limit"] = {"boundary": "event-fsync-before-manifest-publication",
            "error": str(refusal.exception), "sequence": marker["sequence"], "effect_commands": 0}
        self.assertEqual(len(self.op._journal()["commands"]), 0)


if __name__ == "__main__":
    if "--fixture" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--fixture", choices=("server", "publication-tail"), required=True)
        parser.add_argument("--root", type=Path, required=True)
        parser.add_argument("--port", type=int, required=True)
        args = parser.parse_args()
        fixture(args.root, args.port, args.fixture)
    else:
        unittest.main()
