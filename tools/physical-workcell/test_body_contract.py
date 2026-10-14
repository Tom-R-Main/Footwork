"""Shared body transport with an alternate vocabulary; synthetic TCP, no hardware."""
import copy
import json
import socket
import subprocess
import sys
import threading
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import bench_body_contract
import body_contract as wire
import body_protocol
import order_protocol as storage
from persistent_body_client import PersistentBodyClient, Refusal, Uncertain

BASE = Path(__file__).resolve().parent
SOURCE_FILES = ("body_contract.py", "bench_body_contract.py", "persistent_body_client.py", "body_protocol.py",
                "order_protocol.py", "test_body_contract.py")


class CameraOperations:
    """A fixture schema, not a camera driver or physical qualification."""
    @staticmethod
    def validate_arguments(operation, arguments):
        if operation != "aim":
            raise Refusal("unsupported fixture operation")
        storage.fields(arguments, ("yaw_deg",), "aim")
        if not -30 <= storage.finite(arguments["yaw_deg"]) <= 30:
            raise Refusal("fixture yaw exceeds bounds")

    @staticmethod
    def validate_result(request, result, pinned):
        storage.fields(result, ("device_id", "yaw_deg", "settled"), "aim result")
        if result["device_id"] != pinned["body_id"] or result["yaw_deg"] != request["arguments"]["yaw_deg"] or type(result["settled"]) is not bool:
            raise Refusal("fixture aim result binding changed")

    @staticmethod
    def is_unknown(result):
        return isinstance(result, dict) and result.get("settled") is False


class CameraFixture:
    def __init__(self):
        self.identity = {"protocol": wire.PROTOCOL, "adapter_id": "camera-fixture-adapter", "body_id": "camera-fixture",
                         "source_sha256": "a" * 64, "epoch": 1, "simulation": True}
        self.effects, self.reads, self.commands = 0, 0, []
        self.results = {}
        self.drop, self.settled, self.corrupt = False, True, False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, value):
                content = storage.encoded(value)
                self.send_response(200)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(content)

            def do_GET(self):
                path = urlsplit(self.path)
                if path.path == "/identity":
                    self.reply(owner.identity)
                elif path.path.startswith("/commands/"):
                    owner.reads += 1
                    query = {k: v[0] for k, v in parse_qs(path.query).items()}
                    query["epoch"] = int(query["epoch"])
                    wire.validate_reconcile(query)
                    token = path.path.removeprefix("/commands/")
                    value = copy.deepcopy(owner.results[token])
                    if owner.corrupt:
                        value["request_sha256"] = "b" * 64
                    self.reply(value)
                else:
                    self.reply({"identity": owner.identity, "state": "ready"})

            def do_POST(self):
                value = storage.decode(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/lease":
                    duration = wire.validate_lease_request(value)
                    self.reply({"client_id": value["client_id"], "lease_id": "1" * 32, "epoch": 1, "duration_s": duration})
                    return
                wire.validate_command(value)
                CameraOperations.validate_arguments(value["operation"], value["arguments"])
                owner.commands.append(value)
                owner.effects += 1
                result = {"device_id": owner.identity["body_id"], "yaw_deg": value["arguments"]["yaw_deg"], "settled": owner.settled}
                envelope = {**{k: owner.identity[k] for k in wire.PIN_KEYS}, "command_id": value["command_id"],
                            "request_sha256": wire.command_digest(value), "state": "completed", "result": result,
                            "reason": None, "receipt_scope": wire.RECEIPT_SCOPE, "recorded_epoch": 1}
                owner.results[value["command_id"]] = envelope
                if owner.drop:
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                else:
                    self.reply(envelope)

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, kwargs={"poll_interval": .05}, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.http.server_port}"

    def close(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(2)


class BodyContractTests(unittest.TestCase):
    def setUp(self):
        self.root = BASE / "output" / ("sim14-body-contract-" + uuid.uuid4().hex[:12])
        self.root.mkdir(mode=0o700)
        self.sources = {name: storage.sha(storage.read_bytes(BASE / name)) for name in SOURCE_FILES}
        self.service = CameraFixture()
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.service.close()
        result = self._outcome.result
        failed = any(test is self for test, _ in (*result.failures, *result.errors))
        unchanged = self.sources == {name: storage.sha(storage.read_bytes(BASE / name)) for name in SOURCE_FILES}
        storage.create_file(self.root / "conformance.json", storage.encoded({"test_id": self.id(), "passed": not failed and unchanged,
                            "sources": self.sources, "sources_unchanged": unchanged,
                            "scenario_kind": "synthetic_alternate_vocabulary_actual_tcp", "effects": self.service.effects,
                            "receipt_reads": self.service.reads, "command_ids": [v["command_id"] for v in self.service.commands]}))
        self.assertTrue(unchanged, "shared contract source changed during case")

    def client(self, root=None):
        client = PersistentBodyClient(root or self.root / "client", self.service.origin, CameraOperations(), timeout=.5)
        self.clients.append(client)
        return client

    def test_alternate_command_recovers_after_reply_loss_and_client_restart_without_replay(self):
        client = self.client()
        client.acquire()
        self.service.drop = True
        with self.assertRaises(Uncertain) as caught:
            client.command("aim", {"yaw_deg": 15})
        token = caught.exception.command_id
        client.close()
        client = self.client()
        with self.assertRaises(Uncertain):
            client.command("aim", {"yaw_deg": -15})
        receipt = client.reconcile(token)
        self.assertEqual(receipt["result"]["yaw_deg"], 15)
        self.assertEqual(self.service.effects, 1)
        self.assertEqual(self.service.reads, 1)
        manifest = client._load()
        self.assertEqual(manifest["commands"][token]["send_count"], 1)
        self.assertFalse(manifest["pending_command_ids"])

    def test_unknown_lower_proof_blocks_completed_outer_receipt_until_exact_proof(self):
        client = self.client()
        client.acquire()
        self.service.settled = False
        with self.assertRaises(Uncertain) as caught:
            client.command("aim", {"yaw_deg": 15})
        token = caught.exception.command_id
        with self.assertRaises(Uncertain):
            client.acquire()
        with self.assertRaises(Uncertain):
            client.reconcile(token)
        self.service.results[token]["result"]["settled"] = True
        self.assertEqual(client.reconcile(token)["state"], "completed")
        self.assertEqual(self.service.effects, 1)
        self.assertEqual(self.service.reads, 2)

    def test_unbound_historical_receipt_does_not_release_unknown_command(self):
        client = self.client()
        client.acquire()
        self.service.drop = True
        with self.assertRaises(Uncertain) as caught:
            client.command("aim", {"yaw_deg": 15})
        self.service.corrupt = True
        with self.assertRaises(Uncertain):
            client.reconcile(caught.exception.command_id)
        self.assertEqual(client._load()["pending_command_ids"], [caught.exception.command_id])
        self.assertEqual(self.service.effects, 1)

    def test_required_operation_schema_refuses_before_send_or_journal(self):
        with self.assertRaises(Refusal):
            PersistentBodyClient(self.root / "invalid", self.service.origin, object())
        self.assertFalse((self.root / "invalid").exists())
        client = self.client()
        client.acquire()
        for operation, args in (("move", {}), ("aim", {"yaw_deg": True}), ("aim", {"yaw_deg": 31}), ("aim", {"yaw_deg": 15, "extra": 1})):
            with self.assertRaises(Refusal):
                client.command(operation, args)
        self.assertEqual(self.service.effects, 0)
        self.assertEqual(client._load()["commands"], {})

    def test_shared_transport_import_has_no_simulator_dependency(self):
        code = "import json,sys; import persistent_body_client; print(json.dumps(sorted(sys.modules)))"
        result = subprocess.run([sys.executable, "-c", code], cwd=BASE, capture_output=True, text=True, check=True)
        modules = json.loads(result.stdout)
        self.assertFalse(any(m in modules for m in ("bench", "agent_bench", "bench_body_contract", "mujoco", "numpy")))

    def test_shared_envelope_refuses_wrong_identity_epoch_state_and_schema(self):
        client = self.client()
        client.acquire()
        client.command("aim", {"yaw_deg": 15})
        request = self.service.commands[0]
        good = self.service.results[request["command_id"]]
        for key, value in (("adapter_id", "wrong"), ("request_sha256", "b" * 64), ("recorded_epoch", True),
                           ("recorded_epoch", 2), ("state", "success"), ("receipt_scope", "current_pose"), ("result", None)):
            with self.assertRaises(Refusal, msg=key):
                wire.validate_envelope({**good, key: value}, request, wire.command_digest(request))
        with self.assertRaises(Refusal):
            wire.validate_envelope({**good, "extra": True}, request, wire.command_digest(request))
        self.assertFalse(wire.terminal({"state": "not_seen"}, False))
        self.assertFalse(wire.terminal({"state": "completed"}, True))
        with self.assertRaises(Refusal):
            wire.terminal({"state": "completed"}, 0)

    def test_bench_schema_still_refuses_alternate_operations_and_unsafe_motion(self):
        request = {**{k: self.service.identity[k] for k in wire.PIN_KEYS}, "client_id": "client", "lease_id": "lease",
                   "epoch": 1, "command_id": "command", "operation": "aim", "arguments": {"yaw_deg": 15}}
        wire.validate_command(request)
        with self.assertRaises(Refusal):
            body_protocol.validate_command(request)
        # General tabletop zones must not relax the bench's reachable job region.
        for zone in ({"x_min": -.1, "x_max": .1, "y_min": -.03, "y_max": .03},
                     {"x_min": .04, "x_max": .06, "y_min": -.025, "y_max": .025}):
            with self.assertRaises(Refusal):
                bench_body_contract.validate_arguments("start_job", {"job_id": "job", "target_zone": zone})
        for x, y in ((.181, 0), (0, .151), (True, 0), (float("nan"), 0)):
            with self.assertRaises(Refusal):
                bench_body_contract.validate_arguments("propose", {"challenge_id": "challenge", "action": "move",
                    "intent": "bounded motion", "target_x": x, "target_y": y})


if __name__ == "__main__":
    unittest.main()
