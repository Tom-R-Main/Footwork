"""Client/proxy development checks over real sockets and retained native bodies."""
import socket
import time
import unittest
import uuid
from pathlib import Path

import body_client
import body_network
import network_fault_proxy
import order_protocol as storage

BASE = Path(__file__).resolve().parent
ZONE = {"x_min": .04, "x_max": .10, "y_min": -.025, "y_max": .025}


class BodyClientTests(unittest.TestCase):
    def setUp(self):
        self.root = BASE / "output" / ("sim9-client-" + uuid.uuid4().hex[:12])
        self.root.mkdir(mode=0o700)
        body_network.initialize(self.root / "server", diagnostic_enabled=True)
        self.server = body_network.BodyService(self.root / "server").start()
        self.proxy = network_fault_proxy.FaultProxy(self.server.origin, self.root / "proxy").start()
        self.client = body_client.BodyClient(self.root / "client", self.proxy.origin, timeout=.5)
        self.clients = [self.client]
        self.evidence = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.proxy.close()
        self.server.close()
        result = self._outcome.result
        failed = any(test is self for test, _ in (*result.failures, *result.errors))
        storage.create_file(self.root / "conformance.json", storage.encoded({"test_id": self.id(), "passed": not failed,
                            "scenario_kind": "actual_tcp_native_client_proxy", "evidence": self.evidence}))

    def event(self, value):
        self.evidence.append(value)
        return value

    def proposal(self):
        self.client.acquire()
        self.client.start_job("job", ZONE)
        observation = self.client.observe()
        return self.client.propose(observation["challenge_id"], "move", "bounded native approach", -.19, 0)

    def events(self):
        return [storage.decode(storage.read_bytes(path)) for path in sorted((self.root / "proxy" / "events").glob("*.json"))]

    def test_images_are_downloaded_hash_bound_without_changing_nested_packet(self):
        self.client.acquire()
        self.client.start_job("job", ZONE)
        challenge = self.event(self.client.observe())
        image = Path(challenge["image_path"])
        self.assertEqual(image.parent, self.root / "client" / "images")
        self.assertNotEqual(challenge["image_path"], challenge["observation"]["image_path"])
        self.assertEqual(storage.sha(storage.read_bytes(image, maximum=body_client.MAX_IMAGE)), challenge["observation"]["image_sha256"])
        self.assertEqual(storage.sha(storage.encoded(challenge["observation"])), challenge["observation_sha256"])
        self.assertTrue(any(event.get("path", "").startswith("/images/") for event in self.events()))

    def test_drop_after_native_effect_reconciles_without_resending(self):
        proposal = self.proposal()
        before = self.server.state()["bench"]["generation"]
        self.proxy.arm("drop_after")
        with self.assertRaises(body_client.Uncertain) as caught:
            self.client.dispatch(proposal["proposal_id"])
        token = caught.exception.command_id
        self.event(self.client.status())
        with self.assertRaises(body_client.Uncertain):
            self.client.observe()
        envelope = self.event(self.client.reconcile(token))
        self.assertEqual(envelope["state"], "completed")
        self.assertEqual(envelope["result"]["outcome"], "executed")
        self.assertEqual(self.server.state()["bench"]["generation"], before + 1)
        forwards = [event for event in self.events() if event["kind"] == "forwarded" and event.get("command_id") == token]
        self.assertEqual(len(forwards), 1)
        manifest = storage.decode(storage.read_bytes(self.root / "client" / "client.json"))
        self.assertEqual(manifest["commands"][token]["send_count"], 1)
        self.assertFalse(manifest["pending_command_ids"])

    def test_drop_before_remains_unknown_across_client_restart_until_lease_fence(self):
        self.client.acquire(duration_s=.25)
        self.proxy.arm("drop_before", operation="observe")
        with self.assertRaises(body_client.Uncertain) as caught:
            self.client.observe()
        token = caught.exception.command_id
        self.client.close()
        restarted = body_client.BodyClient(self.root / "client", self.proxy.origin, timeout=.5)
        self.clients.append(restarted)
        self.assertEqual(restarted.status()["pending_command_ids"], [token])
        with self.assertRaises(body_client.Uncertain):
            restarted.acquire()
        with self.assertRaises(body_client.Uncertain):
            restarted.reconcile(token)
        time.sleep(.3)
        envelope = self.event(restarted.reconcile(token))
        self.assertEqual(envelope["state"], "not_accepted")
        self.assertFalse(restarted.status()["pending_command_ids"])
        self.assertFalse([event for event in self.events() if event["kind"] == "forwarded" and event.get("command_id") == token])
        restarted.acquire()
        self.assertIn("challenge_id", restarted.observe())

    def test_duplicate_real_socket_dispatch_has_one_native_effect(self):
        proposal = self.proposal()
        before = self.server.state()["bench"]["generation"]
        self.proxy.arm("duplicate")
        result = self.event(self.client.dispatch(proposal["proposal_id"]))
        self.assertEqual(result["outcome"], "executed")
        self.assertEqual(self.server.state()["bench"]["generation"], before + 1)
        duplicates = [event for event in self.events() if event["kind"] == "duplicate_replies"]
        self.assertEqual(len(duplicates), 1)
        self.assertTrue(duplicates[0]["same_reply"])
        self.assertEqual(len([event for event in self.events() if event["kind"] == "forwarded" and
                              event.get("command_id") == duplicates[0]["command_id"]]), 2)

    def test_delays_before_and_after_forwarding_use_real_transport(self):
        self.client.acquire()
        for mode in ("delay_before", "delay_after"):
            self.proxy.arm(mode, operation="observe", delay_s=.03)
            challenge = self.event(self.client.observe())
            self.assertIn("challenge_id", challenge)
        self.assertEqual(len([event for event in self.events() if event["kind"] in {"delay_before", "delay_after"}]), 2)

    def test_rotating_lease_and_exclusive_client_holder(self):
        first = self.client.acquire()
        second = self.client.acquire()
        self.assertNotEqual(first["lease_id"], second["lease_id"])
        outsider = body_client.BodyClient(self.root / "outsider", self.proxy.origin)
        self.clients.append(outsider)
        with self.assertRaises(body_client.Refusal):
            outsider.acquire()
        self.assertEqual(self.client.status()["server_state"]["lease"]["lease_id"], second["lease_id"])

    def test_unbound_error_after_native_success_stays_pending(self):
        proposal = self.proposal()
        original = self.server.command

        def broken_reply(request):
            response = original(request)
            if request["operation"] == "dispatch":
                return {"state": "not_accepted", "reason": "injected unbound terminal transport error"}
            return response

        self.server.command = broken_reply
        with self.assertRaises(body_client.Uncertain) as caught:
            self.client.dispatch(proposal["proposal_id"])
        self.server.command = original
        token = caught.exception.command_id
        self.assertEqual(self.server.state()["bench"]["generation"], 1)
        with self.assertRaises(body_client.Uncertain):
            self.client.start_job("other", ZONE)
        reconciled = self.event(self.client.reconcile(token))
        self.assertEqual(reconciled["state"], "completed")
        self.assertEqual(self.server.state()["bench"]["generation"], 1)

    def test_unknown_request_corruption_cannot_clear_or_resend(self):
        self.client.acquire()
        self.proxy.arm("drop_before", operation="observe")
        with self.assertRaises(body_client.Uncertain) as caught:
            self.client.observe()
        token = caught.exception.command_id
        path = self.root / "client" / "requests" / (token + ".json")
        request = storage.decode(storage.read_bytes(path))
        request["epoch"] += 1
        path.write_bytes(storage.encoded(request))
        with self.assertRaises(body_client.Refusal):
            self.client.reconcile(token)
        self.assertFalse([event for event in self.events() if event["kind"] == "forwarded" and event.get("command_id") == token])

    def test_malformed_proxy_headers_never_forward_or_admit_a_native_command(self):
        proposal = self.proposal()
        manifest = storage.decode(storage.read_bytes(self.root / "client" / "client.json"))
        pinned = manifest["identity"]
        request = {"protocol": body_client.PROTOCOL, "adapter_id": pinned["adapter_id"], "body_id": pinned["body_id"],
                   "source_sha256": pinned["source_sha256"], "client_id": manifest["client_id"],
                   "lease_id": manifest["lease"]["lease_id"], "epoch": manifest["lease"]["epoch"],
                   "command_id": "command-malformed-" + uuid.uuid4().hex, "operation": "dispatch",
                   "arguments": {"proposal_id": proposal["proposal_id"]}}
        payload = storage.encoded(request)
        host, port = body_client.endpoint(self.proxy.origin)
        good = [("Host", f"{host}:{port}"), ("Content-Type", "application/json"),
                *body_client.pinned_headers(pinned).items(), ("Content-Length", str(len(payload)))]
        invalid = [good + [(name, dict(good)[name])] for name in
                   ("Host", "Content-Type", "X-Body-Id", "X-Adapter-Id", "X-Source-Sha256")]
        invalid += [[(name, "foreign.example" if name == "Host" else value) for name, value in good],
                    [(name, "text/plain" if name == "Content-Type" else value) for name, value in good]]
        before = {str(path.relative_to(self.root / "server" / "commands")): path.read_bytes()
                  for path in (self.root / "server" / "commands").rglob("*") if path.is_file()}
        generation = self.server.state()["bench"]["generation"]
        self.event({"rejected_command": request})
        for headers in invalid:
            self.event({"header_attempt": headers})
            wire = ("POST /commands HTTP/1.1\r\n" + "".join(f"{name}: {value}\r\n" for name, value in headers) +
                    "\r\n").encode() + payload
            with socket.create_connection((host, port), timeout=2) as connection:
                connection.sendall(wire)
                try:
                    reply = connection.recv(1024)
                except ConnectionResetError:
                    reply = b""
                self.assertEqual(reply, b"")
        after = {str(path.relative_to(self.root / "server" / "commands")): path.read_bytes()
                 for path in (self.root / "server" / "commands").rglob("*") if path.is_file()}
        self.assertEqual(after, before)
        self.assertEqual(self.server.state()["bench"]["generation"], generation)
        self.assertFalse([event for event in self.events() if event["kind"] == "forwarded" and
                          event.get("command_id") == request["command_id"]])
        failures = [event for event in self.events() if event["kind"] == "transport_failure"]
        self.assertEqual(len(failures), len(invalid))
        self.event({"malformed_header_attempts": len(invalid), "accepted_intents_unchanged": True,
                    "native_generation_unchanged": generation})

    def test_exact_256_record_client_journal_reloads_and_refuses_send_257(self):
        self.client.acquire()
        self.client.observe()
        manifest = storage.decode(storage.read_bytes(self.root / "client" / "client.json"))
        original_id = next(iter(manifest["commands"]))
        original_record = manifest["commands"][original_id]
        original_request = storage.decode(storage.read_bytes(self.root / "client" / "requests" / (original_id + ".json")))
        response_path = self.root / "client" / "responses" / (original_id + "-" + original_record["response_sha256"] + ".json")
        original_response = storage.decode(storage.read_bytes(response_path))
        for index in range(255):
            token = "command-capacity-" + f"{index:032x}"
            request = {**original_request, "command_id": token}
            content = storage.encoded(request)
            digest = storage.sha(content)
            storage.create_file(self.root / "client" / "requests" / (token + ".json"), content)
            response = {**original_response, "command_id": token, "request_sha256": digest}
            reply = storage.encoded(response)
            reply_sha = storage.sha(reply)
            storage.create_file(self.root / "client" / "responses" / (token + "-" + reply_sha + ".json"), reply)
            manifest["commands"][token] = {"request_sha256": digest, "state": "completed", "send_count": 1,
                                           "response_sha256": reply_sha}
        raw = storage.encoded(manifest)
        self.assertGreater(len(raw), storage.MAX_BYTES)
        self.assertLess(len(raw), 128 * 1024)
        storage.persist(self.root / "client" / "client.json", manifest)
        self.event({"fixture_kind": "256 local bound records derived from one real RPC; not 256 native effects",
                    "serialized_bytes": len(raw), "records": len(manifest["commands"])})
        self.client.close()
        reopened = body_client.BodyClient(self.root / "client", self.proxy.origin)
        self.clients.append(reopened)
        self.assertEqual(reopened.status()["pending_command_ids"], [])
        requests_before = len([event for event in self.events() if event["kind"] == "received"])
        with self.assertRaises(body_client.Refusal):
            reopened.observe()
        self.assertEqual(len([event for event in self.events() if event["kind"] == "received"]), requests_before)
        self.assertEqual((self.root / "client" / "client.json").read_bytes(), raw)
        reopened.close()
        invalid = {"duplicate": raw.replace(b'"version": 1', b'"version": 1, "version": 1'),
                   "nonfinite": raw.replace(b'"sequence": 3', b'"sequence": NaN'),
                   "oversized": raw + b" " * (128 * 1024)}
        # Find the actual current sequence rather than relying on fixture event order.
        invalid["nonfinite"] = raw.replace(f'"sequence": {manifest["sequence"]}'.encode(), b'"sequence": NaN')
        for label, malformed in invalid.items():
            storage.create_file(self.root / ("capacity-invalid-" + label + ".json"), malformed)
            (self.root / "client" / "client.json").write_bytes(malformed)
            with self.assertRaises(body_client.Refusal):
                body_client.BodyClient(self.root / "client", self.proxy.origin)
        (self.root / "client" / "client.json").write_bytes(raw)
        with self.assertRaises(storage.Refusal):
            storage.decode(b" " * (storage.MAX_BYTES + 1))

    def test_endpoint_pin_and_lifetime_client_lock(self):
        with self.assertRaises(body_client.Refusal):
            body_client.BodyClient(self.root / "client", self.proxy.origin)
        for origin in (self.server.origin + "/", "http://localhost:80", "http://127.0.0.1:80?x=1"):
            with self.assertRaises(body_client.Refusal):
                body_client.BodyClient(self.root / "other", origin)
        self.client.close()
        with self.assertRaises(body_client.Refusal):
            body_client.BodyClient(self.root / "client", self.server.origin)


if __name__ == "__main__":
    unittest.main()
