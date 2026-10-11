"""Durable single-send client for a pinned loopback simulated body.

BodyClient returns RPC results, except reconcile() returns the historical envelope.
A pending command blocks new commands and lease rotation. Request files and send
intent are durable before HTTP; reconciliation only issues GET and never replays.
"""
import fcntl
import http.client
import json
import os
import stat
import threading
import uuid
from urllib.parse import urlencode, urlsplit

import order_protocol as protocol

PROTOCOL = "footwork.body/1"
MAX_IMAGE = 8 * 1024 * 1024
MAX_CLIENT_JOURNAL = 128 * 1024
IDENTITY_KEYS = {"protocol", "adapter_id", "body_id", "source_sha256", "epoch", "simulation"}
ENVELOPE_KEYS = {"protocol", "adapter_id", "body_id", "source_sha256", "command_id", "request_sha256", "state",
                 "result", "reason", "receipt_scope", "recorded_epoch"}
Refusal = protocol.Refusal


class Uncertain(Refusal):
    def __init__(self, command_id, reason="command outcome is unknown"):
        self.command_id = command_id
        super().__init__(reason)


def endpoint(origin):
    if not isinstance(origin, str):
        raise Refusal("body endpoint must be text")
    parsed = urlsplit(origin)
    try:
        port = parsed.port
    except ValueError as exc:
        raise Refusal("invalid loopback endpoint") from exc
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not port or
            parsed.username is not None or parsed.password is not None or parsed.path or parsed.query or parsed.fragment or
            origin != f"http://127.0.0.1:{port}"):
        raise Refusal("body endpoint must be an exact literal IPv4 loopback HTTP origin")
    return "127.0.0.1", port


def identity(value):
    protocol.fields(value, IDENTITY_KEYS, "body identity")
    if value["protocol"] != PROTOCOL or value["simulation"] is not True:
        raise Refusal("unsupported body protocol or simulation identity")
    for key in ("adapter_id", "body_id"):
        protocol.identity(value[key])
    if not isinstance(value["source_sha256"], str) or not protocol.DIGEST.fullmatch(value["source_sha256"]):
        raise Refusal("body source digest is invalid")
    protocol.revision(value["epoch"])
    return value


def pinned_headers(value):
    return {"X-Body-Id": value["body_id"], "X-Adapter-Id": value["adapter_id"],
            "X-Source-Sha256": value["source_sha256"]}


def http_call(origin, method, path, headers=None, content=None, timeout=15, maximum=protocol.MAX_BYTES):
    host, port = endpoint(origin)
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        request_headers = dict(headers or {})
        if content is not None:
            request_headers["Content-Type"] = "application/json"
        connection.request(method, path, body=content, headers=request_headers)
        response = connection.getresponse()
        length = response.getheader("Content-Length")
        if length is not None and (not length.isdigit() or int(length) > maximum):
            raise Refusal("body response exceeds its bounded size")
        body = response.read(maximum + 1)
        if len(body) > maximum:
            raise Refusal("body response exceeds its bounded size")
        if 300 <= response.status < 400:
            raise Refusal("body redirects are refused")
        return response.status, body
    finally:
        connection.close()


def read_journal(path):
    """The bounded local index holds 256 records; wire JSON keeps its 64 KiB cap."""
    content = protocol.read_bytes(path, maximum=MAX_CLIENT_JOURNAL)

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refusal("duplicate local client journal key")
            result[key] = value
        return result

    def nonfinite(_):
        raise Refusal("nonfinite local client journal value")

    try:
        return json.loads(content, object_pairs_hook=unique, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Refusal("invalid local client journal JSON") from exc


class BodyClient:
    def __init__(self, root, origin, timeout=15):
        endpoint(origin)
        self.timeout = protocol.finite(timeout)
        if not .01 <= self.timeout <= 30:
            raise Refusal("client timeout must be between .01 and 30 seconds")
        self.root = protocol.directory(root, create=True)
        self.origin = origin
        self._mutex = threading.RLock()
        self._closed = False
        self._fd = os.open(self.root / "client.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(self._fd).st_mode):
                raise Refusal("invalid client lock")
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise Refusal("another client process owns this journal") from exc
            if (self.root / "client.json").exists():
                self._load()
            else:
                if any(p.name != "client.lock" for p in self.root.iterdir()):
                    raise Refusal("new client journal requires an empty private directory")
                status, content = http_call(origin, "GET", "/identity", timeout=self.timeout)
                if status != 200:
                    raise Refusal("body identity was unavailable")
                remote = identity(protocol.decode(content))
                for name in ("requests", "responses", "events", "images"):
                    (self.root / name).mkdir(mode=0o700)
                self._save({"version": 1, "origin": origin, "client_id": "client-" + uuid.uuid4().hex,
                            "identity": remote, "lease": None, "commands": {}, "pending_command_ids": [], "sequence": 0})
        except Exception:
            os.close(self._fd)
            self._closed = True
            raise

    def close(self):
        with self._mutex:
            if not self._closed:
                os.close(self._fd)
                self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _load(self):
        if self._closed:
            raise Refusal("client is closed")
        m = read_journal(self.root / "client.json")
        protocol.fields(m, ("version", "origin", "client_id", "identity", "lease", "commands", "pending_command_ids", "sequence"),
                        "client journal")
        if type(m["version"]) is not int or m["version"] != 1 or m["origin"] != self.origin:
            raise Refusal("client endpoint or journal version changed")
        identity(m["identity"])
        protocol.identity(m["client_id"])
        if not isinstance(m["commands"], dict) or len(m["commands"]) > 256 or not isinstance(m["pending_command_ids"], list):
            raise Refusal("client journal budget or pending schema is invalid")
        expected_pending = []
        for token, record in m["commands"].items():
            protocol.fields(record, {"request_sha256", "state", "send_count"} |
                            ({"response_sha256"} if "response_sha256" in record else set()), "client command index")
            if type(record["send_count"]) is not int or record["send_count"] != 1:
                raise Refusal("client command must retain exactly one send intent")
            request, _ = self._request(m, token)
            if "response_sha256" in record:
                digest = record["response_sha256"]
                if not isinstance(digest, str) or not protocol.DIGEST.fullmatch(digest):
                    raise Refusal("client response digest is invalid")
                content = protocol.read_bytes(self.root / "responses" / (token + "-" + digest + ".json"))
                if protocol.sha(content) != digest:
                    raise Refusal("durable client response changed")
                value = self._envelope(m, request, content)
                if record["state"] != value["state"]:
                    raise Refusal("client indexed command state changed")
                terminal = self._terminal(value)
            else:
                if record["state"] != "unknown":
                    raise Refusal("command without a durable response cannot be resolved")
                terminal = False
            if not terminal:
                expected_pending.append(token)
        if (len(m["pending_command_ids"]) != len(set(m["pending_command_ids"])) or
                set(m["pending_command_ids"]) != set(expected_pending)):
            raise Refusal("client pending commands disagree with their durable responses")
        return m

    def _save(self, m):
        if len(protocol.encoded(m)) > MAX_CLIENT_JOURNAL:
            raise Refusal("client journal exceeds its 128 KiB capacity")
        protocol.persist(self.root / "client.json", m)

    def _event(self, m, kind, data):
        if type(m["sequence"]) is not int or not 0 <= m["sequence"] < 2048:
            raise Refusal("client event budget exhausted")
        m["sequence"] += 1
        protocol.create_file(self.root / "events" / f"{m['sequence']:06d}.json",
                             protocol.encoded({"sequence": m["sequence"], "kind": kind, "data": data}))
        self._save(m)

    def _request(self, m, token):
        protocol.identity(token)
        content = protocol.read_bytes(self.root / "requests" / (token + ".json"))
        if protocol.sha(content) != m["commands"][token]["request_sha256"]:
            raise Refusal("durable outgoing request changed")
        request = protocol.decode(content)
        if request["command_id"] != token or request["client_id"] != m["client_id"]:
            raise Refusal("durable command identity changed")
        return request, content

    def _pin(self, m, remote):
        identity(remote)
        for key in IDENTITY_KEYS - {"epoch"}:
            if remote[key] != m["identity"][key]:
                raise Refusal("body, adapter or source identity changed")

    def _blocked(self, m):
        if m["pending_command_ids"]:
            raise Uncertain(m["pending_command_ids"][0], "an unknown command blocks fresh commands and lease rotation")

    def acquire(self, duration_s=30):
        duration = protocol.finite(duration_s)
        if not .05 <= duration <= 30:
            raise Refusal("lease duration must be between .05 and 30 seconds")
        with self._mutex:
            m = self._load()
            self._blocked(m)
            status, content = http_call(self.origin, "GET", "/identity", pinned_headers(m["identity"]), timeout=self.timeout)
            if status != 200:
                raise Refusal("body identity could not be refreshed")
            remote = identity(protocol.decode(content))
            self._pin(m, remote)
            m["identity"] = remote
            m["lease"] = None
            self._save(m)
            request = {"client_id": m["client_id"], "expected_epoch": remote["epoch"], "duration_s": duration}
            status, content = http_call(self.origin, "POST", "/lease", pinned_headers(remote),
                                        protocol.encoded(request), self.timeout)
            result = protocol.decode(content)
            if status != 200:
                raise Refusal(result.get("reason", "lease acquisition refused"))
            protocol.fields(result, ("client_id", "lease_id", "epoch", "duration_s"), "lease")
            if (result["client_id"] != m["client_id"] or type(result["epoch"]) is not int or
                    result["epoch"] != remote["epoch"] or protocol.finite(result["duration_s"]) != duration or
                    not isinstance(result["lease_id"], str) or not protocol.UUID.fullmatch(result["lease_id"])):
                raise Refusal("lease response identity changed")
            m["lease"] = result
            self._event(m, "lease_acquired", result)
            return result

    def _envelope(self, m, request, content):
        value = protocol.decode(content)
        protocol.fields(value, ENVELOPE_KEYS, "command result envelope")
        for key in ("protocol", "adapter_id", "body_id", "source_sha256", "command_id"):
            if value[key] != request[key]:
                raise Refusal("command result identity changed")
        if (value["request_sha256"] != m["commands"][request["command_id"]]["request_sha256"] or
                value["receipt_scope"] != "retained_command_result" or
                (not isinstance(value["state"], str) or value["state"] not in {"completed", "refused", "unknown", "not_seen", "not_accepted"})):
            raise Refusal("command result digest, scope or state is invalid")
        protocol.revision(value["recorded_epoch"])
        if value["recorded_epoch"] != request["epoch"]:
            raise Refusal("historical command epoch changed")
        if value["reason"] is not None and not isinstance(value["reason"], str):
            raise Refusal("command reason must be text or null")
        result = value["result"]
        if result is not None and not isinstance(result, dict):
            raise Refusal("command result must be an object or null")
        if value["state"] == "completed":
            if not isinstance(result, dict):
                raise Refusal("completed command needs its typed result")
            operation = request["operation"]
            if operation == "observe":
                self._challenge(m, result)
            elif operation == "dispatch":
                if (result.get("proposal_id") != request["arguments"]["proposal_id"] or
                        (not isinstance(result.get("outcome"), str) or result["outcome"] not in {"executed", "refused", "unknown"})):
                    raise Refusal("dispatch result identity or outcome changed")
                if result.get("next_observation") is not None:
                    self._challenge(m, result["next_observation"])
            elif operation == "propose":
                if (not isinstance(result.get("proposal_id"), str) or
                        result.get("challenge_id") != request["arguments"]["challenge_id"]):
                    raise Refusal("proposal result identity changed")
                protocol.identity(result["proposal_id"])
            elif result.get("bench_id") != m["identity"]["body_id"]:
                raise Refusal("body result identity changed")
        return value

    @staticmethod
    def _terminal(value):
        lower_unknown = isinstance(value["result"], dict) and value["result"].get("outcome") == "unknown"
        return value["state"] in {"completed", "refused", "not_accepted"} and not lower_unknown

    def _challenge(self, m, challenge):
        protocol.fields(challenge, ("challenge_id", "session_id", "sequence", "observation_sha256",
                                   "observation", "task", "image_path"), "body challenge")
        protocol.identity(challenge["challenge_id"])
        packet = challenge["observation"]
        if (not isinstance(packet, dict) or not isinstance(challenge["image_path"], str) or
                protocol.sha(protocol.encoded(packet)) != challenge["observation_sha256"] or
                packet.get("bench_id") != m["identity"]["body_id"] or
                not isinstance(packet.get("image_sha256"), str) or not protocol.DIGEST.fullmatch(packet["image_sha256"]) or
                challenge["image_path"] != packet.get("image_path")):
            raise Refusal("body image challenge binding changed")
        return packet

    def _retain(self, m, token, value):
        content = protocol.encoded(value)
        digest = protocol.sha(content)
        path = self.root / "responses" / (token + "-" + digest + ".json")
        if path.exists():
            if protocol.read_bytes(path) != content:
                raise Refusal("retained command response changed")
        else:
            protocol.create_file(path, content)
        terminal = self._terminal(value)
        m["commands"][token].update(state=value["state"], response_sha256=digest)
        if terminal and token in m["pending_command_ids"]:
            m["pending_command_ids"].remove(token)
        self._event(m, "response_read", {"command_id": token, "state": value["state"], "response_sha256": digest,
                                        "historical": True})
        if not terminal:
            raise Uncertain(token, value["reason"] or "command outcome remains unknown")
        return value

    def _download(self, m, challenge):
        if challenge is None:
            return None
        packet = self._challenge(m, challenge)
        status, content = http_call(self.origin, "GET", "/images/" + challenge["challenge_id"], pinned_headers(m["identity"]),
                                    timeout=self.timeout, maximum=MAX_IMAGE)
        if status != 200 or protocol.sha(content) != packet["image_sha256"] or not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise Refusal("downloaded body image failed its exact PNG digest check")
        path = self.root / "images" / (challenge["challenge_id"] + "-" + packet["image_sha256"] + ".png")
        if path.exists():
            if protocol.read_bytes(path, maximum=MAX_IMAGE) != content:
                raise Refusal("client image changed")
        else:
            protocol.create_file(path, content)
        return {**challenge, "image_path": str(path)}

    def _result(self, m, operation, result):
        if operation == "observe":
            return self._download(m, result)
        return result

    def _command(self, operation, arguments):
        with self._mutex:
            m = self._load()
            self._blocked(m)
            if m["lease"] is None or len(m["commands"]) >= 256:
                raise Refusal("an acquired lease and remaining command budget are required")
            token = "command-" + uuid.uuid4().hex
            pinned = m["identity"]
            request = {"protocol": PROTOCOL, "adapter_id": pinned["adapter_id"], "body_id": pinned["body_id"],
                       "source_sha256": pinned["source_sha256"], "client_id": m["client_id"],
                       "lease_id": m["lease"]["lease_id"], "epoch": m["lease"]["epoch"], "command_id": token,
                       "operation": operation, "arguments": arguments}
            content = protocol.encoded(request)
            if len(content) > protocol.MAX_BYTES:
                raise Refusal("command exceeds bounded JSON size")
            protocol.create_file(self.root / "requests" / (token + ".json"), content)
            m["commands"][token] = {"request_sha256": protocol.sha(content), "state": "unknown", "send_count": 1}
            m["pending_command_ids"].append(token)
            self._event(m, "send_intent", {"command_id": token, "request_sha256": protocol.sha(content), "send_count": 1})
            try:
                _, reply = http_call(self.origin, "POST", "/commands", pinned_headers(pinned), content, self.timeout)
                value = self._envelope(m, request, reply)
            except (TimeoutError, OSError, http.client.HTTPException, Refusal) as exc:
                self._event(m, "transport_unknown", {"command_id": token, "reason": str(exc)})
                raise Uncertain(token, "reply is uncertain; reconcile exact command without resending") from exc
            value = self._retain(m, token, value)
            if value["state"] in {"refused", "not_accepted"}:
                raise Refusal(value["reason"] or "body command refused")
            return self._result(m, operation, value["result"])

    def start_job(self, job_id, zone):
        protocol.identity(job_id)
        protocol.validate_zone(zone)
        return self._command("start_job", {"job_id": job_id, "target_zone": zone})

    def observe(self):
        return self._command("observe", {})

    def propose(self, challenge_id, action, intent, target_x=None, target_y=None):
        protocol.identity(challenge_id)
        if action not in {"move", "measure", "begin_reset", "finish_reset"} or not isinstance(intent, str) or not 1 <= len(intent.strip()) <= 2000:
            raise Refusal("proposal needs a supported action and bounded intent")
        if action == "move":
            target_x, target_y = protocol.finite(target_x), protocol.finite(target_y)
        elif target_x is not None or target_y is not None:
            raise Refusal("only movement proposals accept targets")
        return self._command("propose", {"challenge_id": challenge_id, "action": action, "intent": intent,
                                         "target_x": target_x, "target_y": target_y})

    def dispatch(self, proposal_id):
        protocol.identity(proposal_id)
        return self._command("dispatch", {"proposal_id": proposal_id})

    def disturb(self, operation_id, force_x_n, steps):
        protocol.identity(operation_id)
        force = protocol.finite(force_x_n)
        if type(steps) is not int:
            raise Refusal("diagnostic steps must be an integer")
        return self._command("disturb", {"operation_id": operation_id, "force_x_n": force, "steps": steps})

    def reconcile(self, command_id=None):
        with self._mutex:
            m = self._load()
            if command_id is None:
                if not m["pending_command_ids"]:
                    raise Refusal("no unknown command requires reconciliation")
                command_id = m["pending_command_ids"][0]
            if command_id not in m["commands"]:
                raise Refusal("command is not owned by this client")
            request, _ = self._request(m, command_id)
            query = urlencode({"client_id": request["client_id"], "lease_id": request["lease_id"], "epoch": request["epoch"],
                               "request_sha256": m["commands"][command_id]["request_sha256"]})
            try:
                _, content = http_call(self.origin, "GET", "/commands/" + command_id + "?" + query,
                                        pinned_headers(m["identity"]), timeout=self.timeout)
                value = self._envelope(m, request, content)
            except (TimeoutError, OSError, http.client.HTTPException, Refusal) as exc:
                self._event(m, "reconciliation_unknown", {"command_id": command_id, "reason": str(exc)})
                raise Uncertain(command_id, "read-only reconciliation is unavailable or untrusted") from exc
            value = self._retain(m, command_id, value)
            if value["state"] == "completed":
                return {**value, "result": self._result(m, request["operation"], value["result"])}
            return value

    def status(self):
        with self._mutex:
            m = self._load()
            try:
                status, content = http_call(self.origin, "GET", "/state", pinned_headers(m["identity"]), timeout=self.timeout)
                remote = protocol.decode(content)
                if status != 200:
                    raise Refusal("body state was unavailable")
                self._pin(m, remote["identity"])
            except (TimeoutError, OSError, http.client.HTTPException, Refusal, KeyError) as exc:
                remote = {"state": "unavailable", "reason": str(exc)}
            return {"identity": m["identity"], "lease": m["lease"], "pending_command_ids": m["pending_command_ids"],
                    "server_state": remote}
