"""Diagnostic socket/byte conformance; no UI, model, or native-state trial."""
import http.client
import threading
import time
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import body_client
import order_protocol as protocol
import qualify_workbench_health as harness
import score_workbench_health as scorer

IDENTITY = {"protocol": "footwork.body/1", "body_id": "body-test", "adapter_id": "adapter-test",
            "source_sha256": "a" * 64, "epoch": 1, "simulation": True}


class HealthHarnessTests(unittest.TestCase):
    def setUp(self):
        self.root = protocol.directory(harness.BASE / "output" / ("sim12-harness-" + uuid.uuid4().hex[:12]), create=True)
        self.calls, self.lock = [], threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.reply()

            def do_POST(self):
                self.reply()

            def reply(self):
                length = int(self.headers.get("Content-Length", 0))
                payload = self.rfile.read(length)
                with owner.lock:
                    owner.calls.append({"method": self.command, "path": self.path, "payload": payload,
                                        "headers": dict(self.headers)})
                value = IDENTITY if self.path == "/identity" else {"identity": IDENTITY, "state": "ready"}
                content = protocol.encoded(value)
                self.send_response(200)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .01})
        self.thread.start()
        self.relay = harness.HealthRelay(f"http://127.0.0.1:{self.server.server_port}", self.root / "health-relay").start()

    def tearDown(self):
        self.relay.close()
        self.server.shutdown()
        self.thread.join(3)
        self.server.server_close()
        self.assertFalse(self.thread.is_alive())
        cleanup = protocol.decode(protocol.read_bytes(self.relay.root / "cleanup.json"))
        self.assertTrue(cleanup["server_thread_exited"])
        self.assertEqual(cleanup["active_workers"], 0)
        self.assertLessEqual(cleanup["peak_workers"], harness.MAX_WORKERS)

    def read(self, path, tagged=False):
        headers = {**body_client.pinned_headers(IDENTITY), **({"X-Footwork-Health-Probe": "1"} if tagged else {})}
        started = time.monotonic()
        status, content = body_client.http_call(self.relay.origin, "GET", path, headers, timeout=4)
        return status, content, time.monotonic() - started

    def test_only_tagged_identity_and_state_receive_actual_delay(self):
        for path in ("/identity", "/state"):
            with self.subTest(path=path):
                _, plain, _ = self.read(path)
                status, tagged, elapsed = self.read(path, tagged=True)
                self.assertEqual(status, 200)
                self.assertEqual(tagged, plain)
                self.assertGreaterEqual(elapsed, 1.2)
        records, valid = scorer.relay_records(self.root)
        self.assertTrue(valid)
        self.assertEqual([record["request"]["injected_delay_s"] for record in records], [0, 1.2, 0, 1.2])
        self.assertEqual(len(self.calls), 4)

    def test_post_bytes_identity_headers_immediate_and_no_retry(self):
        payload = b'{"operation":"dispatch","command_id":"diagnostic-command","literal":"exact bytes"}'
        headers = body_client.pinned_headers(IDENTITY)
        status, _ = body_client.http_call(self.relay.origin, "POST", "/commands", headers, payload, timeout=4)
        self.assertEqual(status, 200)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["payload"], payload)
        for key, value in headers.items():
            self.assertEqual(self.calls[0]["headers"][key], value)
        records, valid = scorer.relay_records(self.root)
        self.assertTrue(valid)
        self.assertEqual(records[0]["request"]["operation"], "dispatch")
        self.assertEqual(records[0]["request"]["injected_delay_s"], 0)
        self.assertEqual(records[0]["request"]["upstream_sends"], 1)

    def test_probe_annotation_cannot_change_effect_or_image_routes(self):
        for method, path, payload in (("POST", "/commands", b'{"operation":"dispatch"}'),
                                      ("GET", "/images/diagnostic", None)):
            with self.assertRaises((OSError, http.client.HTTPException)):
                body_client.http_call(self.relay.origin, method, path, {"X-Footwork-Health-Probe": "1"}, payload, timeout=2)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.relay.sequence, 0)

    def test_owned_control_selects_state_without_changing_normal_reads(self):
        protocol.persist(self.root / "health-relay-control.json", {"enabled": True, "paths": ["/state"]})
        self.read("/identity", tagged=True)
        self.read("/state", tagged=True)
        self.read("/state")
        records, valid = scorer.relay_records(self.root)
        self.assertTrue(valid)
        self.assertEqual([record["request"]["injected_delay_s"] for record in records], [0, 1.2, 0])


class AdmissionScorerTests(unittest.TestCase):
    def fixture(self):
        remote = {"state": "ready", "identity": IDENTITY}
        state = {"request": {"method": "GET", "path": "/state", "tagged_health": False, "sequence": 1,
                            "headers": body_client.pinned_headers(IDENTITY), "started_monotonic": 1.0},
                 "upstream": {"http_status": 200, "wall": 2.0, "finished_monotonic": 2.0},
                 "content": protocol.encoded(remote)}
        lease = {"request": {"method": "POST", "path": "/lease", "sequence": 2,
                            "started_monotonic": 3.0, "started_wall": 3.0},
                 "upstream": {"http_status": 200, "finished_monotonic": 3.1},
                 "content": protocol.encoded({"lease_id": "lease-1"}),
                 "payload": protocol.encoded({"expected_epoch": 1})}
        command = {"request": {"method": "POST", "path": "/commands", "sequence": 3, "started_monotonic": 4.0},
                   "upstream": {"finished_monotonic": 5.0},
                   "payload": protocol.encoded({"command_id": "command-1", "lease_id": "lease-1", "epoch": 1,
                                                "operation": "dispatch"})}
        event = {"kind": "admission_proof", "seq": 1, "time": 2.1, "outcome": "dispatch",
                 "evidence": {**{key: IDENTITY[key] for key in ("body_id", "adapter_id", "source_sha256", "epoch")},
                              "state_sha256": protocol.sha(protocol.encoded(remote))}}
        return [state, lease, command], [event]

    def test_exact_fresh_untagged_state_before_lease_and_command_passes(self):
        records, events = self.fixture()
        self.assertTrue(scorer.fresh_admissions(records, events, IDENTITY)[0]["passed"])

    def test_tagged_stale_foreign_or_unbound_proof_fails(self):
        for case in ("tagged", "late", "foreign", "missing", "wrong_header", "wrong_epoch"):
            records, events = self.fixture()
            if case == "tagged":
                records[0]["request"]["tagged_health"] = True
            elif case == "late":
                records[0]["upstream"]["finished_monotonic"] = 3.5
            elif case == "foreign":
                events[0]["evidence"]["body_id"] = "foreign"
            elif case == "missing":
                events = []
            elif case == "wrong_header":
                records[0]["request"]["headers"]["X-Body-Id"] = "foreign"
            else:
                events[0]["evidence"]["epoch"] = 2
            with self.subTest(case=case):
                self.assertFalse(scorer.fresh_admissions(records, events, IDENTITY)[0]["passed"])

    def test_one_proof_cannot_authorize_a_second_command(self):
        records, events = self.fixture()
        duplicate = {**records[2], "request": {**records[2]["request"], "started_monotonic": 6.0, "sequence": 4}}
        records.append(duplicate)
        reports = scorer.fresh_admissions(records, events, IDENTITY)
        self.assertTrue(reports[0]["passed"])
        self.assertFalse(reports[1]["passed"])


if __name__ == "__main__":
    unittest.main()
