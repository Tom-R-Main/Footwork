"""Real HTTP boundary conformance; the operator is an explicitly labelled test double."""
import json
import threading
import unittest
from http.client import HTTPConnection

import network_bench_operator as product


class DiagnosticOperator:
    """Records handler admission without starting a body or model."""

    def __init__(self):
        self.m = {"app_id": "http-conformance-app"}
        self.calls = []

    def _identity(self):
        pass

    def state(self):
        return {"app_id": self.m["app_id"], "simulation": True}

    def frame(self, path):
        self.calls.append(("frame", path))
        return b"\x89PNG\r\n\x1a\n"

    def enqueue(self, request):
        self.calls.append(("enqueue", request))
        return {"app_id": self.m["app_id"]}

    def fault(self, request):
        self.calls.append(("fault", request))
        return {"app_id": self.m["app_id"]}

    def __getattr__(self, name):
        if name not in ("pause", "resume", "disconnect", "reconnect", "reconcile"):
            raise AttributeError(name)
        def control():
            self.calls.append((name, None))
            return {"app_id": self.m["app_id"]}
        return control


class NetworkHTTPTests(unittest.TestCase):
    def setUp(self):
        self.operator = DiagnosticOperator()
        self.server = product.Server(("127.0.0.1", 0), self.operator)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.assertFalse(self.thread.is_alive())

    def request(self, method, path, payload=None, overrides=None, extra=()):
        headers = {"Host": self.server.host}
        body = json.dumps(payload).encode() if payload is not None else b""
        if method == "POST":
            headers.update({"Origin": self.server.origin,
                            "X-Footwork-App-ID": self.operator.m["app_id"],
                            "Content-Type": "application/json", "Content-Length": str(len(body))})
        for name, value in (overrides or {}).items():
            if value is None:
                headers.pop(name, None)
            else:
                headers[name] = value
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        try:
            connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for name, value in headers.items():
                connection.putheader(name, value)
            for name, value in extra:
                connection.putheader(name, value)
            connection.endheaders(body)
            response = connection.getresponse()
            return response.status, response.read(), response.getheader("Content-Type")
        finally:
            connection.close()

    def test_new_controls_admitted_only_with_exact_identity(self):
        for route in ("disconnect", "reconnect", "reconcile", "pause", "resume"):
            self.assertEqual(self.request("POST", "/api/" + route, {})[0], 200)
        self.assertEqual([call[0] for call in self.operator.calls],
                         ["disconnect", "reconnect", "reconcile", "pause", "resume"])

    def test_missing_foreign_or_duplicate_headers_never_mutate(self):
        for name, foreign in (("Host", "localhost:9999"), ("Origin", "https://foreign.invalid"),
                              ("X-Footwork-App-ID", "foreign-app")):
            for value in (None, foreign):
                with self.subTest(header=name, value=value):
                    self.assertEqual(self.request("POST", "/api/reconnect", {}, {name: value})[0], 409)
            valid = {"Host": self.server.host, "Origin": self.server.origin,
                     "X-Footwork-App-ID": self.operator.m["app_id"]}[name]
            self.assertEqual(self.request("POST", "/api/reconcile", {}, extra=((name, valid),))[0], 409)
        self.assertEqual(self.operator.calls, [])

    def test_controls_require_empty_exact_json_body(self):
        for route in ("disconnect", "reconnect", "reconcile"):
            for value in ({"replay": True}, [], {"command_id": "other"}):
                self.assertEqual(self.request("POST", "/api/" + route, value)[0], 409)
        self.assertEqual(self.operator.calls, [])

    def test_fault_schema_is_bounded_and_dispatch_only(self):
        for mode in ("drop_after", "delay_after", "duplicate"):
            for delay in (0, 2):
                self.assertEqual(self.request("POST", "/api/fault", {"mode": mode, "delay_s": delay})[0], 200)
        before = list(self.operator.calls)
        for value in ({"mode": "other", "delay_s": 0}, {"mode": "duplicate", "delay_s": True},
                      {"mode": "duplicate", "delay_s": -1}, {"mode": "duplicate", "delay_s": 3},
                      {"mode": "duplicate", "delay_s": 0, "operation": "begin"}):
            self.assertEqual(self.request("POST", "/api/fault", value)[0], 409)
        self.assertEqual(self.operator.calls, before)

    def test_network_html_read_only_state_and_unknown_routes(self):
        status, body, content_type = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        for label in (b"Check receipt", b"Lose next reply", b"Duplicate next command"):
            self.assertIn(label, body)
        self.assertEqual(self.request("GET", "/api/state")[0], 200)
        self.assertEqual(self.request("POST", "/api/reconcile?command=other", {})[0], 409)
        self.assertEqual(self.request("GET", "/api/disconnect")[0], 404)
        self.assertEqual(self.operator.calls, [])

    def test_http_body_framing_is_closed_before_mutation(self):
        for overrides, extra in (({"Content-Type": "text/plain"}, ()),
                                 ({"Content-Length": "4097"}, ()),
                                 ({}, (("Content-Length", "2"),)),
                                 ({}, (("Transfer-Encoding", "chunked"),))):
            self.assertEqual(self.request("POST", "/api/reconnect", {}, overrides, extra)[0], 409)
        self.assertEqual(self.operator.calls, [])


if __name__ == "__main__":
    unittest.main()
