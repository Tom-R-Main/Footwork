"""Actual TCP/native conformance; no model calls or uncertain effect retries."""
import concurrent.futures
import json
import time
import unittest
import uuid
from http.client import HTTPConnection
from unittest import mock
from urllib.parse import urlencode, urlsplit

import body_network as body
import body_protocol as wire
import order_protocol as storage

ZONE = {"x_min": .035, "x_max": .105, "y_min": -.025, "y_max": .025}


class BodyNetworkTests(unittest.TestCase):
    def setUp(self):
        self.root = body.BASE / "output" / ("body-net-test-" + uuid.uuid4().hex[:10])
        body.initialize(self.root, diagnostic_enabled=True)
        self.service = body.BodyService(self.root).start()
        self.identity = self.get("/identity")
        self.headers = {"X-Body-Id": self.identity["body_id"], "X-Adapter-Id": self.identity["adapter_id"],
                        "X-Source-Sha256": self.identity["source_sha256"]}
        self.lease = self.post("/lease", {"client_id": "diagnostic-client", "expected_epoch": self.identity["epoch"], "duration_s": 30})
        self.events = []

    def tearDown(self):
        if self.service:
            self.service.close()
        failed = any(test is self for test, _ in (*self._outcome.result.failures, *self._outcome.result.errors))
        storage.create_file(self.root / "conformance.json", storage.encoded(
            {"test_id": self.id(), "passed": not failed, "events": self.events}))

    def http(self, method, path, value=None, headers=None):
        parsed = urlsplit(self.service.origin)
        connection = HTTPConnection(parsed.hostname, parsed.port, timeout=10)
        request_headers = getattr(self, "headers", {}) | (headers or {})
        content = None if value is None else storage.encoded(value)
        if content is not None:
            request_headers["Content-Type"] = "application/json"
        connection.request(method, path, body=content, headers=request_headers)
        response = connection.getresponse()
        content = response.read()
        connection.close()
        result = content if path.startswith("/images/") else json.loads(content)
        if hasattr(self, "events"):
            self.events.append({"method": method, "path": path, "status": response.status,
                                "response": "PNG" if isinstance(result, bytes) else result})
        return response.status, result

    def get(self, path):
        return self.http("GET", path)[1]

    def post(self, path, value):
        return self.http("POST", path, value)[1]

    def request(self, operation, arguments, command_id=None):
        return {**{k: self.identity[k] for k in ("protocol", "adapter_id", "body_id", "source_sha256")},
                **{k: self.lease[k] for k in ("client_id", "lease_id", "epoch")},
                "command_id": command_id or "command-" + uuid.uuid4().hex,
                "operation": operation, "arguments": arguments}

    def command(self, operation, arguments):
        request = self.request(operation, arguments)
        reply = self.post("/commands", request)
        self.assertEqual(reply["state"], "completed", reply)
        return request, reply["result"]

    def start_and_propose(self):
        self.command("start_job", {"job_id": "test-job", "target_zone": ZONE})
        _, challenge = self.command("observe", {})
        _, proposal = self.command("propose", {"challenge_id": challenge["challenge_id"], "action": "move",
                                             "intent": "Diagnostic fixture", "target_x": -.25, "target_y": 0})
        return challenge, proposal

    def query(self, request):
        return "/commands/" + request["command_id"] + "?" + urlencode({
            **{k: request[k] for k in ("client_id", "lease_id", "epoch")}, "request_sha256": wire.command_digest(request)})

    def test_image_crosses_tcp_with_exact_challenge_sha(self):
        self.command("start_job", {"job_id": "test-job", "target_zone": ZONE})
        _, challenge = self.command("observe", {})
        status, image = self.http("GET", "/images/" + challenge["challenge_id"])
        self.assertEqual(status, 200)
        self.assertEqual(storage.sha(image), challenge["observation"]["image_sha256"])
        self.assertNotIn("block_center_xy", json.dumps(challenge))

    def test_exact_concurrent_duplicate_executes_one_native_effect(self):
        _, proposal = self.start_and_propose()
        request = self.request("dispatch", {"proposal_id": proposal["proposal_id"]})
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            replies = list(pool.map(lambda _: self.post("/commands", request), range(2)))
        self.assertEqual(replies[0], replies[1])
        self.assertEqual(replies[0]["result"]["outcome"], "executed")
        self.assertEqual(self.get("/state")["bench"]["generation"], 1)
        self.assertEqual(self.get(self.query(request)), replies[0])

    def test_conflicting_duplicate_refuses_without_second_effect(self):
        _, proposal = self.start_and_propose()
        request = self.request("dispatch", {"proposal_id": proposal["proposal_id"]})
        first = self.post("/commands", request)
        conflicting = dict(request, operation="observe", arguments={})
        self.assertEqual(self.post("/commands", conflicting)["state"], "refused")
        self.assertEqual(self.get(self.query(request)), first)
        self.assertEqual(self.get("/state")["bench"]["generation"], 1)

    def test_expired_and_rotated_leases_fence_new_admission(self):
        first = self.request("observe", {})
        self.lease = self.post("/lease", {"client_id": "diagnostic-client", "expected_epoch": self.identity["epoch"], "duration_s": .05})
        self.assertEqual(self.post("/commands", first)["state"], "not_accepted")
        late = self.request("observe", {})
        time.sleep(.07)
        self.assertEqual(self.post("/commands", late)["state"], "not_accepted")
        self.assertEqual(self.get(self.query(late))["state"], "not_accepted")
        self.assertEqual(self.service.records, {})

    def test_lease_rechecked_after_slow_validation_before_intent(self):
        self.lease = self.post("/lease", {"client_id": "diagnostic-client", "expected_epoch": self.identity["epoch"], "duration_s": .05})
        request = self.request("observe", {})
        original = self.service._known_body
        def slow():
            time.sleep(.08)
            return original()
        with mock.patch.object(self.service, "_known_body", side_effect=slow):
            reply = self.post("/commands", request)
        self.assertEqual(reply["state"], "not_accepted")
        self.assertEqual(self.service.records, {})

    def test_identity_source_origin_and_exclusive_lease_refuse(self):
        request = self.request("observe", {})
        self.assertEqual(self.http("POST", "/commands", request, {"Origin": self.service.origin})[0], 409)
        for key, value in (("adapter_id", "foreign"), ("body_id", "foreign"), ("source_sha256", "0" * 64)):
            self.assertEqual(self.post("/commands", dict(request, **{key: value}))["state"], "not_accepted")
        reply = self.post("/lease", {"client_id": "other-client", "expected_epoch": self.identity["epoch"], "duration_s": 30})
        self.assertEqual(reply["state"], "not_accepted")
        self.assertEqual(self.service.records, {})

    def test_known_result_survives_restart_and_old_lease_is_fenced(self):
        _, proposal = self.start_and_propose()
        request = self.request("dispatch", {"proposal_id": proposal["proposal_id"]})
        first = self.post("/commands", request)
        self.service.close()
        self.service = body.BodyService(self.root).start()
        new_identity = self.get("/identity")
        self.assertEqual(new_identity["body_id"], self.identity["body_id"])
        self.assertEqual(new_identity["adapter_id"], self.identity["adapter_id"])
        self.assertGreater(new_identity["epoch"], self.identity["epoch"])
        self.assertEqual(self.get(self.query(request)), first)
        self.assertEqual(self.post("/commands", request), first)
        late = self.request("observe", {})
        self.assertEqual(self.post("/commands", late)["state"], "not_accepted")
        self.assertEqual(self.get("/state")["bench"]["generation"], 1)

    def test_read_only_recovery_requires_indexed_hash_verified_lower_receipt(self):
        _, proposal = self.start_and_propose()
        request = self.request("dispatch", {"proposal_id": proposal["proposal_id"]})
        # A precise diagnostic interruption after lower receipt, before transport terminal.
        with mock.patch.object(self.service, "_terminal", side_effect=OSError("fixture terminal storage failure")):
            reply = self.post("/commands", request)
        self.assertEqual(reply["state"], "unknown")
        self.assertEqual(self.get("/state")["state"], "unknown")
        self.service.close()
        with mock.patch.object(body.agent.AgentBench, "dispatch", side_effect=AssertionError("recovery replayed dispatch")):
            self.service = body.BodyService(self.root).start()
        recovered = self.get(self.query(request))
        self.assertEqual(recovered["state"], "completed")
        self.assertEqual(recovered["result"]["outcome"], "executed")
        self.assertEqual(self.get("/state")["bench"]["generation"], 1)

    def test_terminal_pointer_persist_failure_keeps_cache_and_disk_unknown(self):
        _, proposal = self.start_and_propose()
        request = self.request("dispatch", {"proposal_id": proposal["proposal_id"]})
        directory = self.service._directory(request["command_id"])
        original = storage.persist
        def fail_pointer(path, value):
            if path == directory / "intent.json" and value["result_sha256"] is not None:
                self.assertTrue((directory / "result.json").exists())
                raise OSError("fixture terminal pointer persistence failure")
            return original(path, value)
        with mock.patch.object(storage, "persist", side_effect=fail_pointer):
            reply = self.post("/commands", request)
        self.assertEqual(reply["state"], "unknown")
        durable = storage.decode(storage.read_bytes(directory / "intent.json"))
        cached_pointer = self.service.records[request["command_id"]]["result_sha256"]
        self.events.append({"kind": "partial_terminal_persistence", "cached_result_sha256": cached_pointer,
                            "durable_result_sha256": durable["result_sha256"]})
        self.assertIsNone(durable["result_sha256"])
        self.assertEqual(self.get("/state")["state"], "unknown")
        blocked = self.post("/commands", self.request("observe", {}))
        self.assertEqual(blocked["state"], "not_accepted")
        self.assertEqual(self.get("/state")["bench"]["generation"], 1)
        self.service.close()
        with mock.patch.object(body.agent.AgentBench, "dispatch", side_effect=AssertionError("recovery replayed dispatch")):
            self.service = body.BodyService(self.root).start()
        recovered = self.get(self.query(request))
        self.assertEqual(recovered["state"], "completed")
        self.assertEqual(recovered["result"]["outcome"], "executed")
        self.assertEqual(self.get("/state")["bench"]["generation"], 1)
        self.assertIsNone(cached_pointer, "cached terminal pointer must change only after durable commit")

    def test_accepted_intent_without_lower_receipt_blocks_restart(self):
        _, proposal = self.start_and_propose()
        request = self.request("dispatch", {"proposal_id": proposal["proposal_id"]})
        directory = self.service._directory(request["command_id"])
        directory.mkdir(mode=0o700)
        storage.persist(directory / "intent.json", {"request": request, "request_sha256": wire.command_digest(request), "result_sha256": None})
        self.service.close()
        self.service = body.BodyService(self.root).start()
        self.assertEqual(self.get(self.query(request))["state"], "unknown")
        new = self.get("/identity")
        self.lease = self.post("/lease", {"client_id": "diagnostic-client", "expected_epoch": new["epoch"], "duration_s": 30})
        self.identity = new
        self.assertEqual(self.post("/commands", self.request("observe", {}))["state"], "not_accepted")
        self.assertEqual(self.get("/state")["bench"]["generation"], 0)

    def test_missing_command_not_seen_then_not_accepted_after_lease_expiry(self):
        self.lease = self.post("/lease", {"client_id": "diagnostic-client", "expected_epoch": self.identity["epoch"], "duration_s": .05})
        request = self.request("observe", {})
        self.assertEqual(self.get(self.query(request))["state"], "not_seen")
        time.sleep(.06)
        self.assertEqual(self.get(self.query(request))["state"], "not_accepted")

    def test_stale_observation_is_retained_known_dispatch_refusal(self):
        _, proposal = self.start_and_propose()
        self.command("disturb", {"operation_id": "diagnostic-force", "force_x_n": -.4, "steps": 50})
        _, result = self.command("dispatch", {"proposal_id": proposal["proposal_id"]})
        self.assertEqual(result["outcome"], "refused")
        self.assertIn("stale", result["reason"])
        self.assertEqual(self.get("/state")["bench"]["generation"], 1)

    def test_invalid_arguments_never_create_intent(self):
        for arguments in ({"job_id": "job", "target_zone": dict(ZONE, x_min=True)}, {"job_id": "../bad", "target_zone": ZONE}):
            self.assertEqual(self.http("POST", "/commands", self.request("start_job", arguments))[0], 409)
        self.assertEqual(self.http("POST", "/commands", dict(self.request("observe", {}), success=True))[0], 409)
        self.assertEqual(self.service.records, {})


if __name__ == "__main__":
    unittest.main()
