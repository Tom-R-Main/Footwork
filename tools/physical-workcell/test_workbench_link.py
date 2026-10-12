"""Retained workbench-link checks with real TCP and unchanged native authority."""
import concurrent.futures
import contextlib
import http.client
import socket
import threading
import time
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import body_client
import body_network
import order_protocol as storage
import workbench_link

BASE = Path(__file__).resolve().parent
ZONE = {"x_min": .04, "x_max": .10, "y_min": -.025, "y_max": .025}
PROBE_HEADER = "X-Footwork-Health-Probe"


class DelayedHealthGateway:
    """Test-only real TCP response barrier; never extends the product fault API."""
    def __init__(self, upstream, trickle=False):
        self.upstream = upstream
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.calls = []
        self.active = {}
        self.peak = {}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                tagged = self.headers.get(PROBE_HEADER) == "1"
                with owner.lock:
                    owner.calls.append({"path": self.path, "tagged": tagged})
                    if tagged:
                        owner.active[self.path] = owner.active.get(self.path, 0) + 1
                        owner.peak[self.path] = max(owner.peak.get(self.path, 0), owner.active[self.path])
                try:
                    if tagged and not trickle:
                        owner.release.wait(3)
                    headers = {key: value for key, value in self.headers.items() if key.lower() != "host"}
                    status, content = body_client.http_call(owner.upstream, "GET", self.path, headers, timeout=2)
                    self.send_response(status)
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    if tagged and trickle:
                        for byte in content:
                            try:
                                self.wfile.write(bytes([byte]))
                                self.wfile.flush()
                            except OSError:
                                break
                            time.sleep(.03)
                    else:
                        with contextlib.suppress(OSError):
                            self.wfile.write(content)
                finally:
                    if tagged:
                        with owner.lock:
                            owner.active[self.path] -= 1

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .05})
        self.thread.start()

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


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

    def test_slow_auxiliary_probes_are_single_flight_and_never_reuse_late_results(self):
        gateway = DelayedHealthGateway(self.server.origin)
        link = workbench_link.WorkbenchLink(gateway.origin, self.root / "slow-link").start()
        pinned = body_client.read_journal(self.root / "client" / "client.json")["identity"]
        headers = {**body_client.pinned_headers(pinned), PROBE_HEADER: "1"}
        def probe(path):
            started = time.monotonic()
            status, content = body_client.http_call(link.origin, "GET", path, headers, timeout=2)
            return path, status, storage.decode(content), time.monotonic() - started
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=6)
        futures = []
        try:
            futures = [pool.submit(probe, path) for path in ("/state", "/identity", "/state", "/identity", "/state", "/identity")]
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                with gateway.lock:
                    if len(gateway.calls) >= 2:
                        break
                time.sleep(.005)
            status, fresh = body_client.http_call(link.origin, "GET", "/state", body_client.pinned_headers(pinned), timeout=2)
            self.assertEqual(status, 200)
            self.assertEqual(storage.decode(fresh)["identity"], pinned)
            # The barrier outlasts the .8-second caller budget, then releases all owned transports.
            time.sleep(.8)
            repeated = [probe(path) for path in ("/state", "/identity")]
            gateway.release.set()
            results = [future.result() for future in futures] + repeated
            with gateway.lock:
                peak = dict(gateway.peak)
                tagged_before = sum(call["tagged"] for call in gateway.calls)
            self.evidence.append({"results": results, "upstream_peak_by_path": peak,
                                  "tagged_upstream_calls": tagged_before, "independent_full_status": status})
            self.assertEqual(peak, {"/state": 1, "/identity": 1})
            self.assertEqual(tagged_before, 2)
            for path, status, result, elapsed in results:
                self.assertEqual(status, 504)
                self.assertEqual(result, {"version": 1, "kind": "health_read_pending", "path": path})
                self.assertLess(elapsed, .8)
            # A subsequent probe obtains a new upstream response rather than the discarded late one.
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                with gateway.lock:
                    if not any(gateway.active.values()):
                        break
                time.sleep(.005)
            for path in ("/state", "/identity"):
                deadline = time.monotonic() + 2
                while True:
                    _, status, _, _ = probe(path)
                    if status == 200 or time.monotonic() >= deadline:
                        break
                    time.sleep(.005)
                self.assertEqual(status, 200)
            with gateway.lock:
                self.assertEqual(sum(call["tagged"] for call in gateway.calls), 4)
        finally:
            gateway.release.set()
            pool.shutdown(wait=True)
            link.close()
            gateway.close()

    def test_probe_annotation_is_refused_before_any_upstream_dispatch(self):
        proposal = self.prepare()
        manifest = body_client.read_journal(self.root / "client" / "client.json")
        pinned = manifest["identity"]
        request = {"protocol": body_client.PROTOCOL, "adapter_id": pinned["adapter_id"], "body_id": pinned["body_id"],
                   "source_sha256": pinned["source_sha256"], "client_id": manifest["client_id"],
                   "lease_id": manifest["lease"]["lease_id"], "epoch": manifest["lease"]["epoch"],
                   "command_id": "command-invalid-probe-" + uuid.uuid4().hex, "operation": "dispatch",
                   "arguments": {"proposal_id": proposal["proposal_id"]}}
        payload = storage.encoded(request)
        host, port = body_client.endpoint(self.link.origin)
        before = {str(p.relative_to(self.root / "body" / "commands")): p.read_bytes()
                  for p in (self.root / "body" / "commands").rglob("*") if p.is_file()}
        cases = [("GET", "/state", ["0"]), ("GET", "/identity", ["1", "1"]),
                 ("GET", "/identity?probe=1", ["1"]), ("GET", "/commands/missing", ["1"]),
                 ("POST", "/commands", ["1"])]
        forwards = sum(event["kind"] == "forwarded" for event in self.events())
        for method, path, annotations in cases:
            content = payload if method == "POST" else b""
            headers = [("Host", f"{host}:{port}"), *body_client.pinned_headers(pinned).items(),
                       ("Content-Length", str(len(content))), ("Content-Type", "application/json"),
                       *[(PROBE_HEADER, value) for value in annotations]]
            wire = (f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers) + "\r\n").encode() + content
            with socket.create_connection((host, port), timeout=2) as connection:
                connection.sendall(wire)
                try:
                    reply = connection.recv(1024)
                except ConnectionResetError:
                    reply = b""
                self.assertEqual(reply, b"")
        self.assertEqual(sum(event["kind"] == "forwarded" for event in self.events()), forwards)
        self.assertEqual({str(p.relative_to(self.root / "body" / "commands")): p.read_bytes()
                          for p in (self.root / "body" / "commands").rglob("*") if p.is_file()}, before)
        self.assertEqual(self.server.state()["bench"]["generation"], 0)
        self.evidence.append({"refused_probe_routes": cases, "generation": 0})

    def test_probe_cleanup_joins_upstream_readers_before_releasing_root(self):
        gateway = DelayedHealthGateway(self.server.origin)
        link = workbench_link.WorkbenchLink(gateway.origin, self.root / "cleanup-link").start()
        origin = link.origin
        finished = threading.Event()
        closer = None
        try:
            status, _ = body_client.http_call(origin, "GET", "/identity", {PROBE_HEADER: "1"}, timeout=2)
            self.assertEqual(status, 504)
            owned = [flight["thread"] for flight in link._probe_flights.values()]
            def close():
                link.close()
                finished.set()
            closer = threading.Thread(target=close)
            closer.start()
            self.assertFalse(finished.wait(.1))
            with self.assertRaises(storage.Refusal):
                workbench_link.WorkbenchLink(gateway.origin, self.root / "cleanup-link").start()
            gateway.release.set()
            self.assertTrue(finished.wait(2))
            closer.join()
            self.assertTrue(all(not thread.is_alive() for thread in owned))
            events = [storage.decode(storage.read_bytes(path)) for path in sorted((self.root / "cleanup-link" / "events").glob("*.json"))]
            self.assertEqual(events[-1]["kind"], "closed")
            self.assertEqual(events[-1]["health_readers_alive"], 0)
            self.assertEqual(events[-1]["health_readers_peak"], 1)
            frozen = {path.name: path.read_bytes() for path in (self.root / "cleanup-link" / "events").iterdir()}
            time.sleep(.05)
            self.assertEqual(frozen, {path.name: path.read_bytes() for path in (self.root / "cleanup-link" / "events").iterdir()})
            link = workbench_link.WorkbenchLink(gateway.origin, self.root / "cleanup-link").start()
            self.assertEqual(link.origin, origin)
            status, _ = body_client.http_call(origin, "GET", "/identity", {PROBE_HEADER: "1"}, timeout=2)
            self.assertEqual(status, 200)
            self.evidence.append({"joined_readers": len(owned), "restart_origin": origin, "closed": events[-1]})
        finally:
            gateway.release.set()
            if closer is not None:
                closer.join(timeout=3)
            link.close()
            gateway.close()

    def test_probe_hard_failure_and_absolute_deadline_keep_transport_loss_semantics(self):
        gateway = DelayedHealthGateway(self.server.origin, trickle=True)
        link = workbench_link.WorkbenchLink(gateway.origin, self.root / "deadline-link").start()
        try:
            with mock.patch.object(workbench_link, "HEALTH_HARD_SECONDS", .15):
                started = time.monotonic()
                with self.assertRaises((OSError, http.client.HTTPException)):
                    body_client.http_call(link.origin, "GET", "/identity", {PROBE_HEADER: "1"}, timeout=2)
                self.assertLess(time.monotonic() - started, .6)
            link.close()
            self.assertFalse(link._probe_flights)
            self.evidence.append({"short_owned_hard_deadline_s": .15, "outcome": "transport_loss"})
        finally:
            gateway.release.set()
            link.close()
            gateway.close()
        # The production deadline remains thirty seconds, while an already dead body fails promptly.
        self.assertEqual(workbench_link.HEALTH_HARD_SECONDS, 30)
        self.server.close()
        started = time.monotonic()
        with self.assertRaises((OSError, http.client.HTTPException)):
            body_client.http_call(self.link.origin, "GET", "/identity", {PROBE_HEADER: "1"}, timeout=2)
        self.assertLess(time.monotonic() - started, .6)


if __name__ == "__main__":
    unittest.main()
