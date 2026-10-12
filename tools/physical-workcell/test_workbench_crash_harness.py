"""Mechanical owned-process/wire controls; no AI or browser qualification."""
import concurrent.futures
import os
import signal
import subprocess
import threading
import time
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import body_client
import order_protocol as protocol
import qualify_workbench_crashes as harness


class CrashHarnessTests(unittest.TestCase):
    def setUp(self):
        self.root = protocol.directory(harness.BASE / "output" / ("sim13-harness-" + uuid.uuid4().hex[:12]), create=True)
        self.children = []

    def tearDown(self):
        for process in self.children:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)

    def control(self, **changes):
        return {"sequence": 1, "action": "crash-role", "role": "workbench", "requested_time": 1.0,
                "expect": {"app_id": "app", "body_id": "body", "epoch": 1, "runner_status": "blocked",
                           "active_job_id": "job", "command_id": "command", "model_request_pending": False}, **changes}

    def owned(self):
        trial = harness.Trial(self.root, "diagnostic-not-a-source-freeze", "host-uncertain")
        process = subprocess.Popen([str(harness.BASE / ".venv/bin/python"), "-c", "import time; time.sleep(20)"], start_new_session=True)
        self.children.append(process)
        record = {"role": "workbench", "boot": 1, "pid": process.pid, "group": os.getpgid(process.pid)}
        trial.processes.append((process, record))
        trial.active["workbench"] = process
        return trial, process, record

    def test_exact_registered_group_is_sigkilled_and_reaped(self):
        trial, process, _ = self.owned()
        result = trial.kill("workbench")
        self.assertEqual(process.returncode, -signal.SIGKILL)
        self.assertTrue(result["exit_observed"])
        self.assertEqual(result["children_before"], [])
        self.assertEqual(result["children_after"], [])
        self.assertIsNone(trial.active["workbench"])

    def test_foreign_role_group_or_missing_registration_never_signalled(self):
        trial, process, record = self.owned()
        for case in ("role", "group", "missing"):
            with self.subTest(case=case):
                original = dict(record)
                if case == "role":
                    record["role"] = "body"
                elif case == "group":
                    record["group"] = process.pid + 1
                else:
                    trial.processes.clear()
                with self.assertRaises(protocol.Refusal):
                    trial.kill("workbench")
                self.assertIsNone(process.poll())
                record.clear()
                record.update(original)
                trial.processes = [(process, record)]

    def test_control_schema_rejects_stale_or_unscoped_crashes(self):
        self.assertEqual(harness.validate_control(self.control())["action"], "crash-role")
        for value in (self.control(sequence=True), self.control(role=None), self.control(pid=123),
                      self.control(expect={**self.control()["expect"], "runner_status": "running"}),
                      self.control(expect={**self.control()["expect"], "model_request_pending": True}),
                      self.control(action="start-role"), self.control(action="finish", role="body")):
            with self.assertRaises((protocol.Refusal, TypeError)):
                harness.validate_control(value)

    def test_indexed_receipt_requires_exact_digest_and_identity(self):
        token = "diagnostic-command"
        directory = protocol.directory(self.root / "body" / "commands" / protocol.sha(token.encode()), create=True)
        request = {"command_id": token, "operation": "dispatch", "body_id": "body", "adapter_id": "adapter", "source_sha256": "a" * 64}
        result = {**request, "state": "completed", "request_sha256": protocol.sha(protocol.encoded(request))}
        content = protocol.encoded(result)
        protocol.create_file(directory / "result.json", content)
        protocol.persist(directory / "intent.json", {"request": request, "request_sha256": result["request_sha256"], "result_sha256": protocol.sha(content)})
        self.assertTrue(harness.indexed_command(self.root, token)["digest_valid"])
        protocol.persist(directory / "intent.json", {"request": request, "request_sha256": result["request_sha256"], "result_sha256": "f" * 64})
        with self.assertRaises(protocol.Refusal):
            harness.indexed_command(self.root, token)

    def test_stopped_body_snapshot_does_not_query_body_endpoint(self):
        trial = harness.Trial(self.root, "diagnostic", "body-native-gap")
        trial.browser_origin, trial.body_origin, trial.identity = "http://127.0.0.1:1", "http://127.0.0.1:2", {}
        for name in ("snapshots", "operator", "operator/client", "operator/link/events"):
            protocol.directory(self.root / name, create=True)
        host = {key: None for key in ("body_identity", "stage", "frame", "usage")}
        host.update(app_id="app", runner_status="running", sequence=0)
        protocol.persist(self.root / "operator" / "operator.json", host)
        protocol.persist(self.root / "operator" / "client" / "client.json", {"commands": {}, "pending_command_ids": [], "lease": None, "identity": {}})
        with mock.patch.object(harness, "get", return_value={"app_id": "app"}) as getter:
            _, snapshot = trial.snapshot("before", body_reads=False)
        self.assertIsNone(snapshot["body_identity"])
        self.assertIsNone(snapshot["body_state"])
        self.assertEqual(getter.call_count, 1)
        self.assertEqual(getter.call_args.args[:2], (trial.browser_origin, "/api/state"))

    def test_manual_crash_does_not_apply_to_automatic_gate_case(self):
        protocol.directory(self.root / "control", create=True)
        protocol.persist(self.root / "ready.json", {"case": "body-native-gap", "browser_origin": "http://127.0.0.1:1"})
        public = {"app_id": "app", "connection": {"body_id": "body", "epoch": 1}, "runner_status": "blocked",
                  "active_job_id": "job", "recovery": {"command_id": "command"}, "model_request_pending": False}
        with mock.patch.object(harness, "get", return_value=public), self.assertRaises(protocol.Refusal):
            harness.request(self.root, "crash-role", "body")
        self.assertEqual(list((self.root / "control").iterdir()), [])

    def test_restart_waits_for_current_pinned_boot_before_snapshot(self):
        trial = harness.Trial(self.root, "diagnostic", "body-uncertain")
        protocol.directory(self.root / "control", create=True)
        trial.browser_origin, trial.body_origin = "http://127.0.0.1:1", "http://127.0.0.1:2"
        trial.identity = {"protocol": "footwork.body/1", "body_id": "body", "adapter_id": "adapter",
                          "source_sha256": "a" * 64, "simulation": True, "epoch": 1}
        trial.boundary = {"role": "body", "command_id": "command", "restored_snapshot": None}
        trial.stops["body"] = True
        trial.active["body"] = None
        public = {"runner_status": "blocked", "recovery": {"command_id": "command"}, "model_request_pending": False,
                  "connection": {"body_id": "body", "adapter_id": "adapter", "epoch": 1}}
        current = {**public, "connection": {**public["connection"], "epoch": 2}}
        snapshot = {"body_identity": {**trial.identity, "epoch": 2}}
        with mock.patch.object(trial, "launch"), mock.patch.object(trial, "wait_public", return_value=snapshot["body_identity"]),                 mock.patch.object(harness, "get", side_effect=[public,current]) as getter,                 mock.patch.object(harness.time, "sleep"), mock.patch.object(trial, "snapshot", return_value=("restored.json",snapshot)) as capture:
            trial.control({"sequence": 1, "action": "start-role", "role": "body", "expect": None, "requested_time": 1.0})
        self.assertEqual(getter.call_count, 2)
        self.assertEqual(capture.call_count, 1)
        self.assertEqual(trial.boundary["new_epoch"], 2)

    def test_host_offline_record_is_cached_provenance_not_live_authority(self):
        protocol.directory(self.root / "snapshots", create=True)
        public = {"app_id": "app", "runner_status": "running", "jobs": [],
                  "connection": {"body_id": "body"}, "recovery": {}, "model_request_pending": False,
                  "active_job_id": None, "current_frame": None, "activity": [{"intent": "Excluded from bounded UI ledger"}]}
        protocol.persist(self.root / "ready.json", {"app_id": "app", "body_id": "body", "browser_origin": "http://127.0.0.1:1"})
        protocol.persist(self.root / "snapshots" / "before.json", {"public": public})
        protocol.persist(self.root / "snapshots" / "offline.json", {"client": {"commands": {}, "pending_command_ids": []}})
        protocol.persist(self.root / "crash-ledger.json", {"boundaries": [{"role": "workbench", "pre_snapshot": "before.json",
            "offline_snapshot": "offline.json", "restored_snapshot": None}]})
        (self.root / "offline.txt").write_text("Disconnected; last observation retained")
        with mock.patch.object(harness, "get", side_effect=OSError("owned host unavailable")):
            harness.record(self.root, "crash-offline", self.root / "offline.txt", "Observed browser after owned SIGKILL")
        step = harness.read(self.root / "ui-ledger.json")["steps"][0]
        self.assertIsNone(step["state"])
        self.assertTrue(step["offline"])
        self.assertEqual(step["cached_public"]["runner_status"], "running")
        self.assertNotIn("activity", step["cached_public"])
        self.assertEqual(step["snapshot_provenance"]["sha256"], protocol.sha(protocol.read_bytes(self.root / "snapshots" / "offline.json")))
        with mock.patch.object(harness, "get", return_value={**public, "app_id": "foreign"}), self.assertRaises(protocol.Refusal):
            harness.record(self.root, "foreign-online", self.root / "offline.txt", "Foreign application rejected")
        self.assertEqual(len(harness.read(self.root / "ui-ledger.json")["steps"]), 1)

    def test_external_relay_holds_exact_completed_reply_without_retry(self):
        calls = []
        request = {"command_id": "fixture-command", "operation": "dispatch", "body_id": "body", "epoch": 1,
                   "arguments": {"proposal_id": "fixture-proposal"}}
        response = {"state": "completed", "result": {"outcome": "executed"}}
        payload, content = protocol.encoded(request), protocol.encoded(response)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                calls.append(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=upstream.serve_forever, kwargs={"poll_interval": .01})
        thread.start()
        relay = harness.HeldReplyRelay(f"http://127.0.0.1:{upstream.server_port}", self.root / "relay").start()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(body_client.http_call, relay.origin, "POST", "/commands", {}, payload, 4)
                until = time.monotonic() + 3
                while not (relay.root / "barrier.json").exists() and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue((relay.root / "barrier.json").exists())
                marker = harness.read(relay.root / "barrier.json")
                self.assertFalse(future.done())
                self.assertEqual(marker["request_sha256"], protocol.sha(payload))
                self.assertEqual(marker["response_sha256"], protocol.sha(content))
                relay.release.set()
                self.assertEqual(future.result(timeout=3), (200, content))
            self.assertEqual(calls, [payload])
        finally:
            relay.release.set()
            relay.close()
            upstream.shutdown()
            thread.join(3)
            upstream.server_close()
        self.assertEqual(harness.read(relay.root / "cleanup.json")["active_workers"], 0)


if __name__ == "__main__":
    unittest.main()
