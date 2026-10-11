"""Retained workbench-link checks with real TCP and unchanged native authority."""
import socket
import time
import unittest
import uuid
from pathlib import Path

import body_client
import body_network
import order_protocol as storage
import workbench_link

BASE = Path(__file__).resolve().parent
ZONE = {"x_min": .04, "x_max": .10, "y_min": -.025, "y_max": .025}


class WorkbenchLinkTests(unittest.TestCase):
    def setUp(self):
        self.root = BASE / "output" / ("sim10-link-" + uuid.uuid4().hex[:12])
        self.root.mkdir(mode=0o700)
        body_network.initialize(self.root / "body", diagnostic_enabled=True)
        self.server = body_network.BodyService(self.root / "body").start()
        self.link = workbench_link.WorkbenchLink(self.server.origin, self.root / "link").start()
        self.client = body_client.BodyClient(self.root / "client", self.link.origin, timeout=2)
        self.evidence = []

    def tearDown(self):
        self.client.close()
        self.link.close()
        self.server.close()
        result = self._outcome.result
        failed = any(test is self for test, _ in (*result.failures, *result.errors))
        storage.create_file(self.root / "conformance.json", storage.encoded({"test_id": self.id(), "passed": not failed,
                            "scenario_kind": "actual_tcp_retained_link_native_body", "evidence": self.evidence}))

    def events(self):
        return [storage.decode(storage.read_bytes(path)) for path in sorted((self.root / "link" / "events").glob("*.json"))]

    def prepare(self):
        self.client.acquire()
        self.client.start_job("job", ZONE)
        challenge = self.client.observe()
        return self.client.propose(challenge["challenge_id"], "move", "bounded real native approach", -.19, 0)

    def command_id(self, proposal_id):
        manifest = body_client.read_journal(self.root / "client" / "client.json")
        matches = []
        for command_id in manifest["commands"]:
            request = storage.decode(storage.read_bytes(self.root / "client" / "requests" / (command_id + ".json")))
            if request["operation"] == "dispatch" and request["arguments"]["proposal_id"] == proposal_id:
                matches.append(command_id)
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_drop_after_effect_is_unknown_and_read_only_recovery_has_one_forward(self):
        proposal = self.prepare()
        self.link.arm("drop_after")
        with self.assertRaises(body_client.Uncertain) as caught:
            self.client.dispatch(proposal["proposal_id"])
        command_id = caught.exception.command_id
        self.assertIsNone(self.link.state()["fault"])
        self.assertEqual(self.server.state()["bench"]["generation"], 1)
        receipt = self.client.reconcile(command_id)
        self.evidence.append(receipt)
        self.assertEqual(receipt["state"], "completed")
        self.assertEqual(receipt["result"]["outcome"], "executed")
        forwards = [event for event in self.events() if event["kind"] == "forwarded" and event.get("command_id") == command_id]
        self.assertEqual(len(forwards), 1)
        self.assertEqual(self.server.state()["bench"]["generation"], 1)

    def test_duplicate_and_cached_terminal_requests_never_add_native_effects(self):
        proposal = self.prepare()
        self.link.arm("duplicate")
        result = self.client.dispatch(proposal["proposal_id"])
        command_id = self.command_id(proposal["proposal_id"])
        manifest = body_client.read_journal(self.root / "client" / "client.json")
        request = storage.read_bytes(self.root / "client" / "requests" / (command_id + ".json"))
        status, content = body_client.http_call(self.link.origin, "POST", "/commands",
                                               body_client.pinned_headers(manifest["identity"]), request)
        cached = storage.decode(content)
        self.evidence.append(cached)
        self.assertEqual(status, 200)
        self.assertEqual(cached["result"], result)
        self.assertEqual(self.server.state()["bench"]["generation"], 1)
        forwards = [event for event in self.events() if event["kind"] == "forwarded" and event.get("command_id") == command_id]
        self.assertEqual(len(forwards), 3)
        duplicate = [event for event in self.events() if event["kind"] == "duplicate_replies"]
        self.assertEqual(len(duplicate), 1)
        self.assertTrue(duplicate[0]["same_reply"])

    def test_offline_and_reconnect_never_forward_the_saved_command(self):
        self.client.acquire(duration_s=.1)
        self.link.set_connected(False)
        with self.assertRaises(body_client.Uncertain) as caught:
            self.client.observe()
        token = caught.exception.command_id
        with self.assertRaises(body_client.Uncertain):
            self.client.reconcile(token)
        before = len([event for event in self.events() if event["kind"] == "forwarded"])
        self.link.set_connected(True)
        self.assertEqual(len([event for event in self.events() if event["kind"] == "forwarded"]), before)
        self.assertEqual(self.server.state()["bench"]["generation"], 0)
        time.sleep(.15)
        result = self.client.reconcile(token)
        self.evidence.append(result)
        self.assertEqual(result["state"], "not_accepted")
        self.assertFalse([event for event in self.events() if event["kind"] == "forwarded" and event.get("command_id") == token])
        self.assertTrue(any(event["kind"] == "disconnected_request" and event["path"].startswith("/commands/")
                            for event in self.events()))

    def test_restart_retains_fixed_endpoint_offline_and_payload_history(self):
        self.prepare()
        self.link.set_connected(False)
        origin = self.link.origin
        before = {p.name: p.read_bytes() for p in (self.root / "link" / "requests").iterdir()}
        self.link.close()
        self.link = workbench_link.WorkbenchLink(self.server.origin, self.root / "link").start()
        self.assertEqual(self.link.origin, origin)
        self.assertFalse(self.link.state()["connected"])
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / "link" / "requests").iterdir()}, before)
        self.assertEqual(self.server.state()["bench"]["generation"], 0)
        self.link.set_connected(True)
        self.assertIn("challenge_id", self.client.observe())
        self.assertEqual(self.server.state()["bench"]["generation"], 0)
        self.evidence.append(self.link.state())

    def test_restart_cancels_armed_fault_without_forwarding(self):
        self.link.arm("duplicate")
        origin = self.link.origin
        self.link.close()
        self.link = workbench_link.WorkbenchLink(self.server.origin, self.root / "link").start()
        self.assertEqual(self.link.origin, origin)
        self.assertIsNone(self.link.state()["fault"])
        self.assertTrue(any(event["kind"] == "fault_cancelled_on_restart" for event in self.events()))
        self.assertFalse([event for event in self.events() if event["kind"] == "forwarded"])
        self.assertEqual(self.server.state()["bench"]["generation"], 0)

    def test_delay_does_not_hold_state_or_disconnect_lock(self):
        proposal = self.prepare()
        self.link.arm("delay_after", delay_s=.2)
        self.client.timeout = .05
        with self.assertRaises(body_client.Uncertain) as caught:
            self.client.dispatch(proposal["proposal_id"])
        token = caught.exception.command_id
        started = time.monotonic()
        snapshot = self.link.state()
        self.link.set_connected(False)
        self.assertLess(time.monotonic() - started, .1)
        self.assertTrue(snapshot["connected"])
        self.assertFalse(self.link.state()["connected"])
        self.link.set_connected(True)
        self.client.timeout = 2
        result = self.client.reconcile(token)
        self.evidence.append(result)
        self.assertEqual(result["state"], "completed")
        self.assertEqual(self.server.state()["bench"]["generation"], 1)

    def test_header_rejection_never_forwards_or_admits_dispatch(self):
        proposal = self.prepare()
        manifest = body_client.read_journal(self.root / "client" / "client.json")
        pinned = manifest["identity"]
        request = {"protocol": body_client.PROTOCOL, "adapter_id": pinned["adapter_id"], "body_id": pinned["body_id"],
                   "source_sha256": pinned["source_sha256"], "client_id": manifest["client_id"],
                   "lease_id": manifest["lease"]["lease_id"], "epoch": manifest["lease"]["epoch"],
                   "command_id": "command-invalid-" + uuid.uuid4().hex, "operation": "dispatch",
                   "arguments": {"proposal_id": proposal["proposal_id"]}}
        payload = storage.encoded(request)
        host, port = body_client.endpoint(self.link.origin)
        good = [("Host", f"{host}:{port}"), ("Content-Type", "application/json"),
                *body_client.pinned_headers(pinned).items(), ("Content-Length", str(len(payload)))]
        attempts = [good + [(name, dict(good)[name])] for name in ("Host", "Content-Type", "X-Body-Id")]
        attempts += [good + [("Origin", "http://foreign.invalid")],
                     [(k, "foreign.invalid" if k == "Host" else v) for k, v in good]]
        before = {str(p.relative_to(self.root / "body" / "commands")): p.read_bytes()
                  for p in (self.root / "body" / "commands").rglob("*") if p.is_file()}
        for headers in attempts:
            wire = ("POST /commands HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers) + "\r\n").encode() + payload
            with socket.create_connection((host, port), timeout=2) as connection:
                connection.sendall(wire)
                try:
                    reply = connection.recv(1024)
                except ConnectionResetError:
                    reply = b""
                self.assertEqual(reply, b"")
        self.assertEqual({str(p.relative_to(self.root / "body" / "commands")): p.read_bytes()
                         for p in (self.root / "body" / "commands").rglob("*") if p.is_file()}, before)
        self.assertEqual(self.server.state()["bench"]["generation"], 0)
        self.assertFalse([event for event in self.events() if event["kind"] == "forwarded" and
                          event.get("command_id") == request["command_id"]])
        self.evidence.append({"rejected_command": request, "invalid_headers": attempts})

    def test_identity_endpoint_lock_and_state_copy_guards(self):
        snapshot = self.link.state()
        snapshot["connected"] = False
        self.assertTrue(self.link.state()["connected"])
        with self.assertRaises(storage.Refusal):
            workbench_link.WorkbenchLink(self.server.origin, self.root / "link").start()
        origin = self.link.origin
        self.link.close()
        with self.assertRaises(storage.Refusal):
            workbench_link.WorkbenchLink("http://127.0.0.1:1", self.root / "link").start()
        with self.assertRaises(storage.Refusal):
            workbench_link.WorkbenchLink(self.server.origin, self.root / "link", port=1).start()
        self.link = workbench_link.WorkbenchLink(self.server.origin, self.root / "link").start()
        self.assertEqual(self.link.origin, origin)
        with self.assertRaises(storage.Refusal):
            self.link.set_connected(1)
        with self.assertRaises(storage.Refusal):
            self.link.arm("drop_before")
        with self.assertRaises(storage.Refusal):
            self.link.arm("delay_after", delay_s=3)

    def test_idle_polling_does_not_exhaust_retained_command_journal(self):
        self.client.acquire()
        before = len(self.events())
        for _ in range(10):
            self.client.status()
        self.assertEqual(len(self.events()), before)
        self.evidence.append({"ordinary_state_polls": 10, "additional_journal_events": 0})


if __name__ == "__main__":
    unittest.main()
