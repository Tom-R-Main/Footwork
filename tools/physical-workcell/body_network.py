"""Durable loopback body server; uncertainty never causes an effect replay."""
import argparse
import os
import signal
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import agent_bench as agent
import bench
import body_protocol as wire
import order_protocol as storage

BASE = Path(__file__).resolve().parent


def sources():
    return {**agent.sources(), **{name: storage.sha(storage.read_bytes(BASE / name))
            for name in ("body_protocol.py", "body_network.py")}}


def source_sha():
    return storage.sha(storage.encoded(sources()))


def initialize(root, diagnostic_enabled=False):
    root = storage.directory(root, create=True)
    with storage.locked(root):
        if any(p.name != "app.lock" for p in root.iterdir()):
            raise wire.Refusal("body initialization requires an empty owned directory")
        native = bench.initialize(root / "bench", diagnostic_enabled=diagnostic_enabled)
        agent.initialize(root / "agent", root / "bench")
        (root / "commands").mkdir(mode=0o700)
        identity = {"protocol": wire.PROTOCOL, "adapter_id": uuid.uuid4().hex,
                    "body_id": native["bench_id"], "source_sha256": source_sha(), "simulation": True}
        storage.create_file(root / "identity.json", storage.encoded(identity))
        storage.persist(root / "service.json", {"epoch": 0, "identity_sha256": storage.sha(storage.encoded(identity))})
    return identity


class BodyService:
    def __init__(self, root, host="127.0.0.1", port=0, barrier=None):
        if host != "127.0.0.1" or type(port) is not int or not 0 <= port <= 65535:
            raise wire.Refusal("body service must bind literal IPv4 loopback")
        if barrier not in (None, "before_dispatch", "after_dispatch"):
            raise wire.Refusal("unknown diagnostic barrier")
        self.root = storage.directory(root)
        self.lock = threading.RLock()
        self.owner = storage.locked(self.root)
        self.owner.__enter__()
        self.closed = False
        self.lease = None
        self.barrier = barrier
        self.thread = None
        try:
            self.pinned = storage.decode(storage.read_bytes(self.root / "identity.json"))
            storage.fields(self.pinned, ("protocol", "adapter_id", "body_id", "source_sha256", "simulation"), "adapter identity")
            m = storage.decode(storage.read_bytes(self.root / "service.json"))
            storage.fields(m, ("epoch", "identity_sha256"), "service boot record")
            if m["identity_sha256"] != storage.sha(storage.encoded(self.pinned)) or type(m["epoch"]) is not int:
                raise wire.Refusal("adapter identity or boot record changed")
            self.epoch = wire.epoch(m["epoch"] + 1)
            self.body = bench.Bench(self.root / "bench")
            self.agent = agent.AgentBench(self.root / "agent")
            self._identity_guard()
            storage.persist(self.root / "service.json", {"epoch": self.epoch, "identity_sha256": m["identity_sha256"]})
            self.records = {}
            self._restore()
            self.http = _Server((host, port), self)
            self.origin = f"http://127.0.0.1:{self.http.server_address[1]}"
        except Exception:
            self.owner.__exit__(None, None, None)
            raise

    def _identity_guard(self):
        if (self.pinned["protocol"] != wire.PROTOCOL or self.pinned["simulation"] is not True or
                self.pinned["source_sha256"] != source_sha() or
                storage.decode(storage.read_bytes(self.root / "identity.json")) != self.pinned or
                self.body.status()["bench_id"] != self.pinned["body_id"]):
            raise wire.Refusal("pinned adapter, body, or measured source changed")

    def identity(self):
        with self.lock:
            self._identity_guard()
            return {**self.pinned, "epoch": self.epoch}

    def start(self):
        if self.thread is not None:
            raise wire.Refusal("body service has already started")
        self.thread = threading.Thread(target=self.http.serve_forever, kwargs={"poll_interval": .1}, daemon=True)
        self.thread.start()
        return self

    def close(self):
        self.closed = True
        if self.thread:
            self.http.shutdown()
            self.thread.join(5)
        self.http.server_close()
        with self.lock:
            self.lease = None
        self.owner.__exit__(None, None, None)

    def _directory(self, command_id):
        wire.identity(command_id)
        return self.root / "commands" / storage.sha(command_id.encode())

    def _envelope(self, request, state, result=None, reason=None):
        return {**{k: self.pinned[k] for k in ("protocol", "adapter_id", "body_id", "source_sha256")}, "command_id": request["command_id"], "request_sha256": wire.command_digest(request),
                "state": state, "result": result, "reason": reason, "receipt_scope": "retained_command_result",
                "recorded_epoch": request["epoch"]}

    def _reply(self, request, state, result=None, reason=None):
        value = self._envelope(request, state, result, reason)
        return value

    def _read_record(self, directory):
        raw = storage.read_bytes(directory / "intent.json")
        record = storage.decode(raw)
        storage.fields(record, ("request", "request_sha256", "result_sha256"), "command journal")
        request = wire.validate_command(record["request"])
        if (record["request_sha256"] != wire.command_digest(request) or directory != self._directory(request["command_id"]) or
                any(request[key] != self.pinned[key] for key in ("protocol", "adapter_id", "body_id", "source_sha256"))):
            raise wire.Refusal("retained command request or identity changed")
        if record["result_sha256"] is not None:
            wire.digest(record["result_sha256"])
            content = storage.read_bytes(directory / "result.json")
            result = storage.decode(content)
            storage.fields(result, wire.ENVELOPE_FIELDS, "command result")
            if result["state"] not in {"completed", "refused", "unknown"}:
                raise wire.Refusal("retained result state is invalid")
            if storage.sha(content) != record["result_sha256"] or any(result[k] != self._reply(request, result["state"])[k]
                    for k in ("protocol", "adapter_id", "body_id", "source_sha256", "command_id", "request_sha256", "recorded_epoch", "receipt_scope")):
                raise wire.Refusal("retained terminal result changed")
        return record

    def _terminal(self, directory, record, envelope):
        content = storage.encoded(envelope)
        path = directory / "result.json"
        # An orphan transport result is never an authority source; retain it separately.
        if path.exists():
            path.rename(directory / ("orphan-result-" + uuid.uuid4().hex + ".json"))
        storage.create_file(path, content)
        terminal = {**record, "result_sha256": storage.sha(content)}
        storage.persist(directory / "intent.json", terminal)
        record.update(terminal)

    def _restore(self):
        entries = list((self.root / "commands").iterdir())
        if len(entries) > wire.MAX_COMMANDS:
            raise wire.Refusal("retained command budget exceeded")
        for directory in entries:
            if directory.is_symlink() or not directory.is_dir():
                raise wire.Refusal("command journal must contain owned directories")
            if not (directory / "intent.json").exists():
                # No accepted intent implies no effect; admission has not happened.
                continue
            record = self._read_record(directory)
            request = record["request"]
            self.records[request["command_id"]] = record
            if record["result_sha256"] is None and request["operation"] == "dispatch":
                # Recover only indexed, SHA-verified historical lower proof. Never dispatch.
                try:
                    with storage.locked(self.root / "agent"):
                        manifest, _ = self.agent._load()
                        proposal_id = request["arguments"]["proposal_id"]
                        self.agent._read(manifest, "proposals", proposal_id)
                        self.agent._read(manifest, "intents", proposal_id)
                        result = self.agent._read(manifest, "results", proposal_id)
                        if result["proposal_id"] != proposal_id:
                            raise wire.Refusal("lower dispatch identity differs")
                    outer = "unknown" if result["outcome"] == "unknown" else "completed"
                    self._terminal(directory, record, self._reply(request, outer, agent.public_response(result),
                                   "read-only lower receipt recovered after restart"))
                except Exception as exc:  # noqa: BLE001 - absent lower proof must remain unresolved.
                    storage.persist(directory / f"recovery-{self.epoch}.json", {"reason": str(exc), "state": "unknown"})

    def _unresolved(self):
        unknown = []
        for key in self.records:
            record = self._read_record(self._directory(key))
            if record["result_sha256"] is None or storage.decode(storage.read_bytes(
                    self._directory(key) / "result.json"))["state"] == "unknown":
                unknown.append(key)
        return unknown

    def _known_body(self):
        status = self.agent.status()
        if status["bench"]["state"] != "ready" or status["unresolved_proposals"] or self._unresolved():
            raise wire.Refusal("accepted outcome is unknown; new commands are blocked")
        return status["bench"]

    def state(self):
        with self.lock:
            self._identity_guard()
            native = self.agent.status()
            unresolved = self._unresolved()
            lease = None
            if self.lease:
                lease = {k: self.lease[k] for k in ("client_id", "lease_id", "epoch")}
                lease["expires_in_s"] = max(0, self.lease["expires_at"] - time.monotonic())
            return {"identity": {**self.pinned, "epoch": self.epoch}, "state": "unknown" if unresolved or
                    native["unresolved_proposals"] or native["bench"]["state"] != "ready" else "ready",
                    "bench": agent.public_response(native["bench"]), "unresolved_commands": unresolved, "lease": lease}

    def _lease_valid(self, client_id, lease_id, epoch):
        return bool(self.lease and epoch == self.epoch == self.lease["epoch"] and
                    client_id == self.lease["client_id"] and lease_id == self.lease["lease_id"] and
                    time.monotonic() < self.lease["expires_at"])

    def acquire(self, value):
        storage.fields(value, ("client_id", "expected_epoch", "duration_s"), "lease request")
        wire.identity(value["client_id"])
        wire.epoch(value["expected_epoch"])
        duration = wire.finite(value["duration_s"])
        if not .05 <= duration <= 30:
            raise wire.Refusal("lease duration must be between 0.05 and 30 seconds")
        with self.lock:
            self._identity_guard()
            if self.closed or value["expected_epoch"] != self.epoch:
                raise wire.Refusal("requested boot epoch is no longer current")
            if self.lease and time.monotonic() < self.lease["expires_at"] and self.lease["client_id"] != value["client_id"]:
                raise wire.Refusal("another client owns the unexpired body lease")
            self.lease = {"client_id": value["client_id"], "lease_id": uuid.uuid4().hex, "epoch": self.epoch,
                          "expires_at": time.monotonic() + duration}
            return {k: self.lease[k] for k in ("client_id", "lease_id", "epoch")} | {"duration_s": duration}

    def reconcile(self, command_id, value):
        wire.identity(command_id)
        storage.fields(value, ("client_id", "lease_id", "epoch", "request_sha256"), "reconcile query")
        for key in ("client_id", "lease_id"):
            wire.identity(value[key])
        wire.epoch(value["epoch"])
        wire.digest(value["request_sha256"])
        with self.lock:
            self._identity_guard()
            record = self.records.get(command_id)
            if record:
                record = self._read_record(self._directory(command_id))
                request = record["request"]
                if wire.command_digest(request) != value["request_sha256"] or any(
                        request[k] != value[k] for k in ("client_id", "lease_id", "epoch")):
                    raise wire.Refusal("reconcile identity or digest conflicts with retained command")
                if record["result_sha256"]:
                    return storage.decode(storage.read_bytes(self._directory(command_id) / "result.json"))
                return self._reply(request, "unknown", reason="accepted intent has no verified terminal proof")
            return {**{k: self.pinned[k] for k in ("protocol", "adapter_id", "body_id", "source_sha256")},
                    "command_id": command_id, "request_sha256": value["request_sha256"], "state": "not_seen" if
                    self._lease_valid(value["client_id"], value["lease_id"], value["epoch"]) else "not_accepted",
                    "result": None, "reason": "no accepted command in retained journal", "receipt_scope": "retained_command_result",
                    "recorded_epoch": value["epoch"]}

    def _barrier(self, where, request):
        if (self.barrier == where and request["operation"] == "dispatch" and
                self.body.status()["diagnostic_enabled"]):
            storage.persist(self.root / "barrier.json", {"barrier": where, "command_id": request["command_id"], "pid": os.getpid()})
            os.kill(os.getpid(), signal.SIGSTOP)

    def command(self, request):
        wire.validate_command(request)
        with self.lock:
            self._identity_guard()
            if any(request[k] != self.pinned[k] for k in ("protocol", "adapter_id", "body_id", "source_sha256")):
                return self._reply(request, "not_accepted", reason="pinned command identity changed")
            existing = self.records.get(request["command_id"])
            if existing:
                existing = self._read_record(self._directory(request["command_id"]))
                if existing["request_sha256"] != wire.command_digest(request):
                    return self._reply(request, "refused", reason="command identity conflicts with its retained digest")
                if existing["result_sha256"]:
                    return storage.decode(storage.read_bytes(self._directory(request["command_id"]) / "result.json"))
                return self._reply(request, "unknown", reason="accepted intent has no verified terminal proof")
            if self.closed or not self._lease_valid(request["client_id"], request["lease_id"], request["epoch"]):
                return self._reply(request, "not_accepted", reason="body lease expired or was revoked before admission")
            try:
                self._known_body()
            except (wire.Refusal, bench.Refusal) as exc:
                return self._reply(request, "not_accepted", reason=str(exc))
            if len(self.records) >= wire.MAX_COMMANDS:
                return self._reply(request, "not_accepted", reason="body command journal budget exhausted")
            args, operation = request["arguments"], request["operation"]
            if operation == "disturb" and not self.body.status()["diagnostic_enabled"]:
                return self._reply(request, "not_accepted", reason="diagnostic disturbance is disabled")
            if not self._lease_valid(request["client_id"], request["lease_id"], request["epoch"]):
                return self._reply(request, "not_accepted", reason="body lease expired during admission validation")
            directory = self._directory(request["command_id"])
            directory.mkdir(mode=0o700, exist_ok=True)
            storage.directory(directory)
            record = {"request": request, "request_sha256": wire.command_digest(request), "result_sha256": None}
            storage.persist(directory / "intent.json", record)
            self.records[request["command_id"]] = record
            result, state, reason = None, "unknown", None
            try:
                self._barrier("before_dispatch", request)
                if operation == "start_job":
                    result = self.body.start_job(**args)
                elif operation == "observe":
                    result = self.agent.observe()
                elif operation == "propose":
                    result = self.agent.propose(**args)
                elif operation == "dispatch":
                    result = self.agent.dispatch(**args)
                else:
                    result = self.body.disturb(**args)
                self._barrier("after_dispatch", request)
                state = "unknown" if operation == "dispatch" and result["outcome"] == "unknown" else "completed"
            except Exception as exc:  # noqa: BLE001 - accepted command may have partial effects.
                reason = str(exc)
                try:
                    core = self.agent.status()
                    if isinstance(exc, (wire.Refusal, bench.Refusal)) and core["bench"]["state"] == "ready" and not core["unresolved_proposals"]:
                        state = "refused"
                except Exception as status_error:  # noqa: BLE001 - missing native readback cannot resolve uncertainty.
                    reason += "; native status unresolved: " + str(status_error)
            envelope = self._reply(request, state, agent.public_response(result), reason)
            try:
                self._terminal(directory, record, envelope)
            except OSError:
                return self._reply(request, "unknown", reason="accepted effect has no durable transport result")
            return envelope

    def image(self, challenge_id):
        with self.lock:
            self._identity_guard()
            with storage.locked(self.root / "agent"):
                manifest, _ = self.agent._load()
                challenge = self.agent._challenge(manifest, challenge_id)
                return storage.read_bytes(Path(challenge["image_path"]), maximum=wire.MAX_MEDIA)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, service):
        super().__init__(address, _Handler)
        self.service = service
        self.host = f"127.0.0.1:{self.server_address[1]}"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, code, value, mime="application/json"):
        content = value if isinstance(value, bytes) else storage.encoded(value)
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(content)
        self.close_connection = True

    def _headers(self, pinned=True):
        if (self.headers.get_all("Host") != [self.server.host] or self.headers.get_all("Origin") is not None):
            raise wire.Refusal("exact loopback Host and absence of browser Origin are required")
        if pinned:
            for name, key in (("X-Body-Id", "body_id"), ("X-Adapter-Id", "adapter_id"), ("X-Source-Sha256", "source_sha256")):
                if self.headers.get_all(name) != [self.server.service.pinned[key]]:
                    raise wire.Refusal("pinned body request headers are required")

    def do_GET(self):
        try:
            parsed = urlsplit(self.path)
            self._headers(pinned=parsed.path != "/identity")
            if parsed.path == "/identity" and not parsed.query:
                result = self.server.service.identity()
            elif parsed.path == "/state" and not parsed.query:
                result = self.server.service.state()
            elif parsed.path.startswith("/images/") and not parsed.query:
                result = self.server.service.image(parsed.path.removeprefix("/images/"))
                self.reply(200, result, "image/png")
                return
            elif parsed.path.startswith("/commands/"):
                query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
                if any(len(value) != 1 for value in query.values()):
                    raise wire.Refusal("reconcile query has duplicate fields")
                value = {key: values[0] for key, values in query.items()}
                if "epoch" in value and value["epoch"].isascii() and value["epoch"].isdigit():
                    value["epoch"] = int(value["epoch"])
                result = self.server.service.reconcile(parsed.path.removeprefix("/commands/"), value)
            else:
                raise wire.Refusal("unknown body read route")
            self.reply(200, result)
        except (wire.Refusal, bench.Refusal, OSError, ValueError, TypeError, KeyError) as exc:
            self.reply(409, {"state": "not_accepted", "reason": str(exc)})

    def do_POST(self):
        try:
            self._headers()
            lengths = self.headers.get_all("Content-Length")
            if (lengths is None or len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit() or
                    not 1 <= int(lengths[0]) <= storage.MAX_BYTES or self.headers.get_all("Transfer-Encoding") or
                    self.headers.get_all("Content-Type") != ["application/json"]):
                raise wire.Refusal("one bounded exact JSON body is required")
            self.connection.settimeout(5)
            content = self.rfile.read(int(lengths[0]))
            if len(content) != int(lengths[0]):
                raise wire.Refusal("body request is truncated")
            request = storage.decode(content)
            if self.path == "/lease":
                result = self.server.service.acquire(request)
            elif self.path == "/commands":
                result = self.server.service.command(request)
            else:
                raise wire.Refusal("unknown body mutation route")
            self.reply(200, result)
        except (wire.Refusal, bench.Refusal, OSError, ValueError, TypeError, KeyError) as exc:
            self.reply(409, {"state": "not_accepted", "reason": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument("--barrier", choices=("before_dispatch", "after_dispatch"))
    args = parser.parse_args()
    if args.initialize:
        initialize(args.root, args.diagnostic)
    service = BodyService(args.root, port=args.port, barrier=args.barrier).start()
    print(storage.encoded({"origin": service.origin, "identity": service.identity()}).decode(), flush=True)
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    try:
        stopped.wait()
    finally:
        service.close()


if __name__ == "__main__":
    main()
