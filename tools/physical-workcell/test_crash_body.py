"""Real-process native/receipt SIGKILL checks; all actions use public TCP."""
import concurrent.futures
import http.client
import signal
import socket
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

import bench
import body_client
import body_network
import body_protocol as wire
import crash_body
import mujoco
import numpy as np
import order_protocol as storage

BASE = Path(__file__).resolve().parent
ZONE = {"x_min": .04, "x_max": .10, "y_min": -.025, "y_max": .025}


class CrashBodyTests(unittest.TestCase):
    def setUp(self):
        self.root = BASE / "output" / ("sim13-crash-body-" + uuid.uuid4().hex[:12])
        self.root.mkdir(mode=0o700)
        self.body_root = self.root / "body"
        self.processes, self.handles, self.events = [], [], []
        self.client = None
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            self.port = reserve.getsockname()[1]
        self.origin = f"http://127.0.0.1:{self.port}"
        self.sources = {**body_network.sources(), "crash_body.py": storage.sha(storage.read_bytes(BASE / "crash_body.py"))}

    def tearDown(self):
        if self.client:
            self.client.close()
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        for handle in self.handles:
            handle.close()
        failed = any(test is self for test, _ in (*self._outcome.result.failures, *self._outcome.result.errors))
        current = {**body_network.sources(), "crash_body.py": storage.sha(storage.read_bytes(BASE / "crash_body.py"))}
        storage.create_file(self.root / "conformance.json", storage.encoded({
            "test_id": self.id(), "passed": not failed, "scenario_kind": "actual_process_SIGKILL_TCP_native",
            "sources_unchanged": current == self.sources, "processes_reaped": all(p.poll() is not None for p in self.processes),
            "processes": [{"pid": p.pid, "returncode": p.returncode} for p in self.processes], "events": self.events}))
        self.assertEqual(current, self.sources)

    def record(self, kind, **value):
        event = {"kind": kind, **value}
        storage.create_file(self.root / f"event-{len(self.events):04d}.json", storage.encoded(event))
        self.events.append(event)

    def start(self, gate=None):
        path = self.root / f"service-{len(self.processes)}.log"
        handle = path.open("xb")
        path.chmod(0o600)
        self.handles.append(handle)
        launcher = "crash_body.py" if gate else "body_network.py"
        command = [sys.executable, str(BASE / launcher), "--root", str(self.body_root), "--port", str(self.port)]
        if not self.processes:
            command += ["--initialize", "--diagnostic"]
        if gate:
            command += ["--gate", gate]
        self.process = subprocess.Popen(command, cwd=BASE, stdout=handle, stderr=subprocess.STDOUT)
        self.processes.append(self.process)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and self.process.poll() is None:
            try:
                status, content = body_client.http_call(self.origin, "GET", "/identity", timeout=.3)
                if status == 200:
                    identity = body_client.identity(storage.decode(content))
                    self.record("ready", pid=self.process.pid, identity=identity, diagnostic_gate=gate,
                                launcher=launcher)
                    return identity
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(.02)
        self.fail("owned body failed to start; inspect retained service log")

    def prepare(self):
        self.client = body_client.BodyClient(self.root / "client", self.origin, timeout=2)
        self.client.acquire()
        self.client.start_job("job", ZONE)
        challenge = self.client.observe()
        proposal = self.client.propose(challenge["challenge_id"], "move", "Owned hard-crash native approach", -.19, 0)
        return proposal

    def wait_marker(self, expected):
        path = self.body_root / "barrier.json"
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and self.process.poll() is None:
            if path.exists():
                marker = storage.decode(storage.read_bytes(path))
                self.assertEqual(marker["pid"], self.process.pid)
                self.assertEqual(marker["barrier"], expected)
                self.record("stopped_barrier", marker=marker)
                return marker
            time.sleep(.005)
        self.fail("owned process did not reach its bound crash gate")

    def kill_dispatch(self, gate, proposal):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.client.dispatch, proposal["proposal_id"])
            marker = self.wait_marker(gate)
            self.process.kill()
            self.process.wait(timeout=5)
            self.assertEqual(self.process.returncode, -signal.SIGKILL)
            with self.assertRaises(body_client.Uncertain) as caught:
                future.result(timeout=5)
        self.assertEqual(caught.exception.command_id, marker["command_id"])
        request = storage.decode(storage.read_bytes(self.root / "client" / "requests" / (marker["command_id"] + ".json")))
        self.assertEqual(request["arguments"], {"proposal_id": proposal["proposal_id"]})
        self.assertEqual(request["operation"], "dispatch")
        if "request_sha256" in marker:
            self.assertEqual(marker["request_sha256"], wire.command_digest(request))
        self.record("SIGKILL", pid=self.process.pid, command_id=marker["command_id"], returncode=self.process.returncode)
        return marker, request

    def native_state(self, generation):
        content = bench.body.read_bytes(bench.body.state_path(self.body_root / "bench", generation))
        state = bench.body.decoded(content)
        model = mujoco.MjModel.from_xml_path(str(self.body_root / "bench" / "model.xml"))
        data = mujoco.MjData(model)
        mujoco.mj_setState(model, data, np.array(state["values"]), mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(model, data)
        return content, {"time_s": float(data.time), "pusher_xyz": data.xpos[model.body("pusher").id].tolist(),
                         "block_xyz": data.xpos[model.body("block").id].tolist()}

    def snapshot_effects(self):
        # Independent stopped evidence; never passed to an agent or used to authorize an effect.
        paths = [self.body_root / "bench" / "bench.json", self.body_root / "agent" / "agent.json"]
        for directory in (self.body_root / "bench", self.body_root / "agent"):
            paths += [p for p in directory.rglob("*") if p.is_file() and p.name not in {"app.lock", "bench.json", "agent.json"}]
        return {str(p.relative_to(self.body_root)): storage.sha(bench.body.read_bytes(p)) for p in paths}

    def test_after_native_SIGKILL_retains_real_actuation_but_stays_unknown_without_replay(self):
        initial = self.start("after_native")
        proposal = self.prepare()
        marker, request = self.kill_dispatch("after_native", proposal)
        native = self.body_root / "bench"
        manifest = storage.decode(storage.read_bytes(native / "bench.json"))
        self.assertEqual(marker["bench_id"], initial["body_id"])
        self.assertEqual(marker["operation_id"], proposal["operation_id"])
        self.assertEqual(manifest["generation"], marker["manifest_generation"])
        self.assertEqual(manifest["busy"]["operation_id"], marker["operation_id"])
        self.assertNotIn(marker["operation_id"], manifest["operations"])
        self.assertEqual(marker["native_generation"], manifest["generation"] + 1)
        before_bytes, before = self.native_state(manifest["generation"])
        next_bytes, advanced = self.native_state(marker["native_generation"])
        self.assertEqual(storage.sha(next_bytes), marker["native_state_sha256"])
        self.assertNotEqual(before_bytes, next_bytes)
        self.assertEqual(advanced["time_s"], marker["native_time_s"])
        self.assertGreater(advanced["time_s"], before["time_s"])
        self.assertGreater(abs(advanced["pusher_xyz"][0] - before["pusher_xyz"][0]), .05)
        agent_manifest = storage.decode(storage.read_bytes(self.body_root / "agent" / "agent.json"))
        self.assertIn(proposal["proposal_id"], agent_manifest["intents"])
        self.assertNotIn(proposal["proposal_id"], agent_manifest["results"])
        effects = self.snapshot_effects()
        restarted = self.start()
        self.assertEqual({k: v for k, v in restarted.items() if k != "epoch"}, {k: v for k, v in initial.items() if k != "epoch"})
        self.assertEqual(restarted["epoch"], initial["epoch"] + 1)
        state = self.client.status()
        self.assertEqual(state["server_state"]["state"], "unknown")
        self.assertEqual(state["server_state"]["bench"]["state"], "unknown")
        self.assertIn(marker["command_id"], state["server_state"]["unresolved_commands"])
        for _ in range(2):
            with self.assertRaises(body_client.Uncertain) as caught:
                self.client.reconcile(marker["command_id"])
            self.assertEqual(caught.exception.command_id, marker["command_id"])
        for action in (self.client.acquire, self.client.observe, lambda: self.client.dispatch(proposal["proposal_id"])):
            with self.assertRaises(body_client.Uncertain):
                action()
        # Challenge the server independently with a new lease/command; unknown cannot admit successors.
        headers = body_client.pinned_headers(restarted)
        value = {"client_id": request["client_id"], "expected_epoch": restarted["epoch"], "duration_s": 30}
        status, content = body_client.http_call(self.origin, "POST", "/lease", headers, storage.encoded(value))
        self.assertEqual(status, 200)
        lease = storage.decode(content)
        successor = {**request, **{k: lease[k] for k in ("client_id", "lease_id", "epoch")},
                     "command_id": "successor-" + uuid.uuid4().hex, "operation": "observe", "arguments": {}}
        _, content = body_client.http_call(self.origin, "POST", "/commands", headers, storage.encoded(successor))
        self.assertEqual(storage.decode(content)["state"], "not_accepted")
        self.assertFalse((self.body_root / "commands" / storage.sha(successor["command_id"].encode())).exists())
        self.assertEqual(self.snapshot_effects(), effects)
        journal = self.client._load()
        self.assertEqual(journal["commands"][marker["command_id"]]["send_count"], 1)
        self.record("blocked_after_native", marker=marker, before=before, advanced=advanced, public_state=state,
                    exact_single_send=True, state_unchanged=True)

    def test_indexed_lower_receipt_SIGKILL_recovers_exact_command_without_motion_replay(self):
        initial = self.start("after_dispatch")
        proposal = self.prepare()
        marker, request = self.kill_dispatch("after_dispatch", proposal)
        agent_manifest = storage.decode(storage.read_bytes(self.body_root / "agent" / "agent.json"))
        content = storage.read_bytes(self.body_root / "agent" / "results" / (proposal["proposal_id"] + ".json"))
        self.assertEqual(storage.sha(content), agent_manifest["results"][proposal["proposal_id"]])
        lower = storage.decode(content)
        self.assertEqual(lower["outcome"], "executed")
        command_dir = self.body_root / "commands" / storage.sha(marker["command_id"].encode())
        self.assertIsNone(storage.decode(storage.read_bytes(command_dir / "intent.json"))["result_sha256"])
        effects = self.snapshot_effects()
        restarted = self.start()
        self.assertEqual(restarted["body_id"], initial["body_id"])
        self.assertEqual(restarted["epoch"], initial["epoch"] + 1)
        receipt = self.client.reconcile(marker["command_id"])
        self.assertEqual(receipt["state"], "completed")
        self.assertEqual(receipt["recorded_epoch"], request["epoch"])
        self.assertEqual(receipt["request_sha256"], wire.command_digest(request))
        self.assertEqual(receipt["result"], body_network.agent.public_response(lower))
        self.assertEqual(self.client.reconcile(marker["command_id"]), receipt)
        self.assertEqual(self.snapshot_effects(), effects)
        self.assertEqual(self.client.status()["server_state"]["state"], "ready")
        self.assertEqual(self.client._load()["commands"][marker["command_id"]]["send_count"], 1)
        self.record("exact_lower_receipt_recovered", receipt=receipt, exact_single_send=True, native_unchanged=True)

    def test_crash_gate_refuses_a_nondiagnostic_body_and_stale_marker(self):
        body_network.initialize(self.body_root, diagnostic_enabled=False)
        with self.assertRaises(storage.Refusal):
            crash_body.CrashBody(self.body_root)
        other = self.root / "diagnostic-body"
        body_network.initialize(other, diagnostic_enabled=True)
        storage.persist(other / "barrier.json", {"pid": 1, "barrier": "after_native"})
        with self.assertRaises(storage.Refusal):
            crash_body.CrashBody(other)
        with self.assertRaises(storage.Refusal):
            crash_body.CrashBody(other, gate="invented")


if __name__ == "__main__":
    unittest.main()
