"""Owned SIGKILL browser trials; all model and product actions come from the UI."""
import argparse
import contextlib
import http.client
import json
import os
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import body_client
import order_protocol as protocol
import qualify_workbench_restarts as previous

BASE, REPO = previous.BASE, previous.REPO
CASES = {"host-inflight": "workbench", "body-native-gap": "body", "body-uncertain": "body", "host-uncertain": "workbench"}
SOURCES = list(dict.fromkeys(previous.SOURCES + [BASE / name for name in (
    "crash_body.py", "qualify_workbench_crashes.py", "score_workbench_crashes.py",
    "test_workbench_crash_harness.py")]))
read, retain, get = previous.read, previous.retain, previous.get


def descendants(pid):
    rows = subprocess.check_output(["ps", "-axo", "pid=,ppid=,pgid=,comm="], text=True)
    parsed = []
    for line in rows.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) == 4:
            parsed.append({"pid": int(parts[0]), "parent": int(parts[1]), "group": int(parts[2]), "command": parts[3]})
    selected, parents = [], {pid}
    while True:
        new = [row for row in parsed if row["parent"] in parents and row["pid"] not in parents]
        if not new:
            return selected
        selected.extend(new)
        parents.update(row["pid"] for row in new)


def indexed_command(root, token):
    protocol.identity(token)
    directory = root / "body" / "commands" / protocol.sha(token.encode())
    intent = read(directory / "intent.json")
    request = intent["request"]
    if request["command_id"] != token or intent["request_sha256"] != protocol.sha(protocol.encoded(request)):
        raise protocol.Refusal("receiver command digest differs from its exact identity")
    terminal = None
    valid = intent["result_sha256"] is None
    if intent["result_sha256"] is not None:
        content = protocol.read_bytes(directory / "result.json")
        terminal = protocol.decode(content)
        valid = (protocol.sha(content) == intent["result_sha256"] and
                 terminal["request_sha256"] == intent["request_sha256"] and
                 all(terminal[key] == request[key] for key in ("command_id", "body_id", "adapter_id", "source_sha256")))
    if not valid:
        raise protocol.Refusal("receiver terminal receipt is not indexed to its exact command")
    return {"intent": intent, "terminal": terminal, "digest_valid": valid}


class HeldReplyRelay:
    """Diagnostic single-send relay; first executed dispatch waits for host kill."""

    def __init__(self, upstream, root, hold_first_dispatch=True):
        body_client.endpoint(upstream)
        self.upstream, self.root = upstream, protocol.directory(root, create=True)
        if any(self.root.iterdir()):
            raise protocol.Refusal("relay requires a new owned directory")
        (self.root / "requests").mkdir(mode=0o700)
        self.lock, self.release = threading.Lock(), threading.Event()
        self.sequence = self.active = self.peak = 0
        if type(hold_first_dispatch) is not bool:
            raise protocol.Refusal("relay hold selection must be an exact boolean")
        self.held = not hold_first_dispatch

    def start(self):
        owner = self

        class Server(ThreadingHTTPServer):
            daemon_threads = False
            block_on_close = True

            def __init__(self, address, handler):
                self.capacity = threading.BoundedSemaphore(8)
                super().__init__(address, handler)

            def process_request(self, request, address):
                if not self.capacity.acquire(False):
                    self.shutdown_request(request)
                    return
                try:
                    super().process_request(request, address)
                except BaseException:
                    self.capacity.release()
                    raise

            def process_request_thread(self, request, address):
                try:
                    super().process_request_thread(request, address)
                finally:
                    self.capacity.release()

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def forward(self):
                folder = None
                with owner.lock:
                    owner.active += 1
                    owner.peak = max(owner.peak, owner.active)
                try:
                    self.connection.settimeout(15)
                    parsed = urlsplit(self.path)
                    if (self.headers.get_all("Host") != [owner.origin.removeprefix("http://")] or
                            self.headers.get_all("Origin") or self.headers.get_all("Transfer-Encoding") or
                            parsed.scheme or parsed.netloc or parsed.fragment or not self.path.startswith("/")):
                        raise protocol.Refusal("relay requires exact closed loopback framing")
                    allowed_read = parsed.path in ("/identity", "/state") or parsed.path.startswith(("/commands/", "/images/"))
                    if self.command == "GET" and not allowed_read or self.command == "POST" and self.path not in ("/lease", "/commands"):
                        raise protocol.Refusal("unsupported relay route")
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) > 1 or lengths and (not lengths[0].isascii() or not lengths[0].isdigit() or int(lengths[0]) > protocol.MAX_BYTES):
                        raise protocol.Refusal("relay payload is not bounded")
                    length = int(lengths[0]) if lengths else 0
                    if self.command == "GET" and length or self.command == "POST" and (length < 1 or self.headers.get_all("Content-Type") != ["application/json"]):
                        raise protocol.Refusal("relay requires an exact bounded JSON body")
                    payload = self.rfile.read(length)
                    if len(payload) != length:
                        raise protocol.Refusal("relay body is incomplete")
                    headers = {key: value for key, value in self.headers.items() if key.lower() not in {"host", "connection", "content-length"}}
                    request = protocol.decode(payload) if self.path == "/commands" else None
                    with owner.lock:
                        if owner.sequence >= 4096:
                            raise protocol.Refusal("relay request budget exhausted")
                        owner.sequence += 1
                        folder = owner.root / "requests" / f"{owner.sequence:06d}"
                        folder.mkdir(mode=0o700)
                        sequence = owner.sequence
                    protocol.create_file(folder / "request.bin", payload)
                    retain(folder / "request.json", {"sequence": sequence, "method": self.command, "path": self.path,
                        "headers": headers, "payload_sha256": protocol.sha(payload), "started_time": time.time(),
                        "command_id": request["command_id"] if request else None, "upstream_sends": 1})
                    status, content = body_client.http_call(owner.upstream, self.command, self.path, headers,
                        payload if self.command == "POST" else None, timeout=15, maximum=body_client.MAX_IMAGE)
                    protocol.create_file(folder / "response.bin", content)
                    retain(folder / "response.json", {"status": status, "sha256": protocol.sha(content), "time": time.time()})
                    if request and request["operation"] == "dispatch" and status == 200:
                        result = protocol.decode(content)
                        with owner.lock:
                            hold = not owner.held and result["state"] == "completed" and result["result"]["outcome"] == "executed"
                            if hold:
                                owner.held = True
                        if hold:
                            retain(owner.root / "barrier.json", {"version": 1, "barrier": "body_receipt_before_link_reply",
                                "command_id": request["command_id"], "request_sha256": protocol.sha(payload),
                                "response_sha256": protocol.sha(content), "proposal_id": request["arguments"]["proposal_id"],
                                "body_id": request["body_id"], "epoch": request["epoch"], "relay_sequence": sequence, "time": time.time()})
                            if not owner.release.wait(10):
                                raise protocol.Refusal("held reply gate exceeded ten seconds without owned crash")
                    self.send_response(status)
                    self.send_header("Content-Type", "image/png" if self.path.startswith("/images/") else "application/json")
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(content)
                    retain(folder / "result.json", {"delivered": True, "time": time.time()})
                except (OSError, http.client.HTTPException, protocol.Refusal, ValueError, TypeError, KeyError) as exc:
                    if folder and not (folder / "result.json").exists():
                        retain(folder / "result.json", {"delivered": False, "error": str(exc), "time": time.time()})
                    self.close_connection = True
                finally:
                    self.close_connection = True
                    with owner.lock:
                        owner.active -= 1

        self.server = Server(("127.0.0.1", 0), Handler)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .05})
        self.thread.start()
        retain(self.root / "ready.json", {"origin": self.origin, "upstream": self.upstream})
        return self

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.thread.join(3)
        self.server.server_close()
        retain(self.root / "cleanup.json", {"active_workers": self.active, "peak_workers": self.peak,
               "server_thread_exited": not self.thread.is_alive(), "request_count": self.sequence})


def freeze(root, commit):
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != commit:
        raise protocol.Refusal("actual trial requires its committed source head")
    files = {}
    for path in SOURCES:
        name, content = str(path.relative_to(REPO)), protocol.read_bytes(path)
        if subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=REPO) != content:
            raise protocol.Refusal("source is not frozen: " + name)
        files[name] = protocol.sha(content)
    retain(root / "source-freeze.json", {"commit": commit, "files": files})


def expectation(public):
    return {"app_id": public["app_id"], "body_id": public["connection"]["body_id"],
            "epoch": public["connection"]["epoch"], "runner_status": public["runner_status"],
            "active_job_id": public["active_job_id"], "command_id": public["recovery"]["command_id"],
            "model_request_pending": public["model_request_pending"]}


def validate_control(value):
    protocol.fields(value, ("sequence", "action", "role", "expect", "requested_time"), "crash control")
    if type(value["sequence"]) is not int or not 1 <= value["sequence"] <= 64:
        raise protocol.Refusal("control sequence must be bounded")
    if value["action"] not in ("crash-role", "start-role", "finish") or value["role"] not in (None, "body", "workbench"):
        raise protocol.Refusal("unsupported owned crash action")
    if (value["action"] == "finish") != (value["role"] is None):
        raise protocol.Refusal("role must match this control action")
    protocol.finite(value["requested_time"])
    if value["action"] == "crash-role":
        protocol.fields(value["expect"], ("app_id", "body_id", "epoch", "runner_status", "active_job_id", "command_id", "model_request_pending"), "crash expectation")
        if value["expect"]["runner_status"] != "blocked" or value["expect"]["model_request_pending"] is not False:
            raise protocol.Refusal("crash requires the exact uncertain idle-model boundary")
        for key in ("app_id", "body_id", "active_job_id", "command_id"):
            protocol.identity(value["expect"][key])
        protocol.revision(value["expect"]["epoch"])
    elif value["expect"] is not None:
        raise protocol.Refusal("only crashes carry an exact fresh expectation")
    return value


def request(root, action, role=None):
    root = protocol.directory(root)
    ready = read(root / "ready.json")
    public = get(ready["browser_origin"], "/api/state") if action == "crash-role" else None
    expected = expectation(public) if public else None
    if action == "crash-role":
        if ready["case"] not in ("body-uncertain", "host-uncertain") or CASES[ready["case"]] != role:
            raise protocol.Refusal("manual crash does not match this uncertain scenario")
        receiver = indexed_command(root, expected["command_id"])
        if (not receiver["terminal"] or receiver["terminal"]["state"] != "completed" or
                receiver["terminal"].get("result", {}).get("outcome") != "executed"):
            raise protocol.Refusal("uncertain scenario requires an indexed completed receiver receipt")
    sequence = max((int(path.name.split(".")[0]) for path in (root / "control").glob("*.request.json")), default=0) + 1
    value = validate_control({"sequence": sequence, "action": action, "role": role, "expect": expected, "requested_time": time.time()})
    retain(root / "control" / f"{sequence:06d}.request.json", value)
    return value


class Trial(previous.Trial):
    def __init__(self, root, commit, case, body_port=0, browser_port=0):
        if case not in CASES:
            raise protocol.Refusal("unsupported hard crash case")
        super().__init__(root, commit, body_port, browser_port)
        self.case, self.relay = case, None
        self.boundary = None
        self.ledger["case"] = case
        self.snapshot_sequence = 0

    def launch(self, role, initialize=False):
        if role != "body" or not initialize or self.case != "body-native-gap":
            process = super().launch(role, initialize)
        else:
            log = (self.root / "body-01.log").open("xb")
            process = subprocess.Popen([str(Path(os.environ.get("FOOTWORK_PYTHON", str(BASE / ".venv/bin/python")))), str(BASE / "crash_body.py"), "--root", str(self.root / "body"),
                "--port", str(self.body_port), "--initialize", "--diagnostic", "--gate", "after_native"], cwd=REPO,
                stdout=log, stderr=log, start_new_session=True)
            record = {"role": role, "boot": 1, "pid": process.pid, "root": str(self.root / "body"),
                      "port": self.body_port, "initialized": True, "log": "body-01.log"}
            self.processes.append((process, record))
            self.logs.append(log)
            self.ledger["processes"].append(record)
            self.active[role] = process
        record = next(entry for handle, entry in self.processes if handle is process)
        record["group"] = os.getpgid(process.pid)
        if record["group"] != process.pid:
            raise protocol.Refusal("owned trial process did not create its own group")
        return process

    def wait_public(self, origin, path):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                public = get(origin, path)
                if origin == self.body_origin:
                    pinned = read(self.root / "body" / "identity.json")
                    epoch = read(self.root / "body" / "service.json")["epoch"]
                    expected = {**pinned, "epoch": epoch}
                else:
                    expected = read(self.root / "operator" / "identity.json")
                if origin == self.body_origin and public != expected:
                    raise protocol.Refusal("endpoint identity does not match this owned body root and boot")
                if origin == self.browser_origin and public["app_id"] != expected["app_id"]:
                    raise protocol.Refusal("endpoint application does not match this owned workbench root")
                if any(process is not None and process.poll() is not None for process in self.active.values()):
                    raise protocol.Refusal("owned role exited while endpoint identity was being checked")
                return public
            except (OSError, http.client.HTTPException):
                if any(process is not None and process.poll() is not None for process in self.active.values()):
                    raise protocol.Refusal("owned role exited during readiness")
                time.sleep(.05)
        raise protocol.Refusal("owned endpoint readiness exceeded thirty seconds")

    def snapshot(self, label, token=None, body_reads=True):
        self.snapshot_sequence += 1
        value = {"label": label, "time": time.time(), "public": None, "body_identity": None, "body_state": None,
                 "processes": {role: p.pid if p is not None and p.poll() is None else None for role, p in self.active.items()}}
        for key, origin, path in (("public", self.browser_origin, "/api/state"),
                                  ("body_identity", self.body_origin, "/identity"), ("body_state", self.body_origin, "/state")):
            if key != "public" and not body_reads:
                continue
            try:
                value[key] = get(origin, path, self.identity if key == "body_state" else None)
            except (OSError, ValueError, http.client.HTTPException) as exc:
                value[key + "_error"] = str(exc)
        host = read(self.root / "operator" / "operator.json")
        client = body_client.read_journal(self.root / "operator" / "client" / "client.json")
        value["host"] = {key: host[key] for key in ("app_id", "body_identity", "stage", "frame", "runner_status", "sequence", "usage")}
        commands = {}
        for command_id, entry in client["commands"].items():
            content = protocol.read_bytes(self.root / "operator" / "client" / "requests" / (command_id + ".json"))
            if protocol.sha(content) != entry["request_sha256"]:
                raise protocol.Refusal("retained client request changed")
            commands[command_id] = {"request_sha256": entry["request_sha256"], "send_count": entry["send_count"],
                                    "state": entry["state"], "operation": protocol.decode(content)["operation"]}
        value["client"] = {"commands": commands, "pending_command_ids": client["pending_command_ids"],
                           "lease": client["lease"], "identity": client["identity"]}
        value["posts"] = []
        for path in sorted((self.root / "operator" / "link" / "events").glob("*.json")):
            event = read(path)
            if event["kind"] == "received" and event.get("method") == "POST" and event.get("command_id"):
                value["posts"].append({key: event[key] for key in ("sequence", "command_id", "payload_sha256")})
        value["body_command"] = indexed_command(self.root, token) if token else None
        name = f"{self.snapshot_sequence:06d}-{label}.json"
        retain(self.root / "snapshots" / name, value)
        return name, value

    def kill(self, role):
        process = self.active.get(role)
        record = next((entry for handle, entry in self.processes if handle is process), None)
        if (process is None or process.poll() is not None or record is None or record["pid"] != process.pid or
                record["role"] != role or record.get("group") != process.pid or os.getpgid(process.pid) != process.pid):
            raise protocol.Refusal("SIGKILL requires this trial's exact live owned process group")
        children = descendants(process.pid)
        if children:
            raise protocol.Refusal("crash gate still has a live child process; no planner may survive the boundary")
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
        if process.returncode != -signal.SIGKILL:
            raise protocol.Refusal("owned crash did not exit by SIGKILL")
        record.update(exit_observed=True, returncode=process.returncode, stopped_time=time.time(), signal="SIGKILL",
                      children_before=children, children_after=descendants(process.pid))
        self.active[role] = None
        return dict(record)

    def crash(self, role, token, gate=None, expected=None):
        if self.boundary or role != CASES[self.case]:
            raise protocol.Refusal("this case permits one exact owned hard crash")
        receiver = indexed_command(self.root, token)
        if receiver["intent"]["request"]["operation"] != "dispatch":
            raise protocol.Refusal("crash must be bound to a dispatch")
        if self.case != "body-native-gap" and (not receiver["terminal"] or receiver["terminal"]["state"] != "completed" or
                receiver["terminal"].get("result", {}).get("outcome") != "executed"):
            raise protocol.Refusal("recoverable crash requires a known indexed body result")
        if gate:
            if gate["command_id"] != token or gate["request_sha256"] != receiver["intent"]["request_sha256"]:
                raise protocol.Refusal("gate differs from exact accepted receiver command")
            if role == "body" and gate["pid"] != self.active[role].pid:
                raise protocol.Refusal("native gate belongs to another body process")
            if role == "workbench" and gate["response_sha256"] != receiver["intent"]["result_sha256"]:
                raise protocol.Refusal("held reply is not the receiver's indexed terminal result")
        before_name, before = self.snapshot("before", token, body_reads=gate is None)
        if expected is not None:
            public = get(self.browser_origin, "/api/state")
            if expectation(public) != expected or before["public"] is None or expectation(before["public"]) != expected:
                raise protocol.Refusal("uncertain state changed immediately before owned SIGKILL")
        process = self.kill(role)
        if self.relay:
            self.relay.release.set()
        # Wait only on the still-running host; never query a SIGSTOP/dead body.
        if role == "body":
            until = time.monotonic() + 20
            while time.monotonic() < until:
                public = get(self.browser_origin, "/api/state")
                if public["runner_status"] != "running" and public["recovery"]["command_id"] == token and not public["model_request_pending"]:
                    break
                time.sleep(.05)
            else:
                raise protocol.Refusal("surviving host did not retain the crashed command as uncertain")
        offline_name, _ = self.snapshot("offline", token, body_reads=False)
        self.boundary = {"case": self.case, "role": role, "command_id": token,
            "request_sha256": receiver["intent"]["request_sha256"], "gate": gate, "pre_snapshot": before_name,
            "offline_snapshot": offline_name, "restored_snapshot": None, "process": process,
            "old_epoch": receiver["intent"]["request"]["epoch"], "new_epoch": None}
        self.stops[role] = True
        protocol.persist(self.root / "crash-ledger.json", {"case": self.case, "boundaries": [self.boundary]})

    def control(self, command):
        validate_control(command)
        action, role = command["action"], command["role"]
        if action == "crash-role":
            if self.case not in ("body-uncertain", "host-uncertain"):
                raise protocol.Refusal("this scenario has an automatic gate, not a manual crash")
            self.crash(role, command["expect"]["command_id"], expected=command["expect"])
        elif action == "start-role":
            if not self.boundary or role != self.boundary["role"] or role not in self.stops or self.active.get(role) is not None:
                raise protocol.Refusal("restart requires this case's exact reaped role")
            self.launch(role)
            self.wait_public(self.body_origin if role == "body" else self.browser_origin, "/identity" if role == "body" else "/api/state")
            body_current = self.wait_public(self.body_origin, "/identity")
            if any(body_current[key] != self.identity[key] for key in body_client.IDENTITY_KEYS - {"epoch"}):
                raise protocol.Refusal("restarted endpoint belongs to another pinned body")
            until = time.monotonic() + 15
            while time.monotonic() < until:
                public = get(self.browser_origin, "/api/state")
                if (public["runner_status"] != "running" and public["recovery"]["command_id"] == self.boundary["command_id"] and
                        not public["model_request_pending"] and public["connection"]["epoch"] == body_current["epoch"] and
                        public["connection"]["body_id"] == self.identity["body_id"] and public["connection"]["adapter_id"] == self.identity["adapter_id"]):
                    break
                time.sleep(.05)
            else:
                raise protocol.Refusal("restart silently lost uncertainty or resumed planning")
            name, snapshot = self.snapshot("restored", self.boundary["command_id"])
            self.boundary.update(restored_snapshot=name, new_epoch=snapshot["body_identity"]["epoch"])
            self.stops.pop(role)
            protocol.persist(self.root / "crash-ledger.json", {"case": self.case, "boundaries": [self.boundary]})
        else:
            if not self.boundary or self.boundary["restored_snapshot"] is None:
                raise protocol.Refusal("finish requires the recorded crash and explicit restart")
            name, _ = self.snapshot("finished", self.boundary["command_id"])
            self.boundary["finished_snapshot"] = name
            protocol.persist(self.root / "crash-ledger.json", {"case": self.case, "boundaries": [self.boundary]})
        retain(self.root / "control" / f"{command['sequence']:06d}.result.json", {"request": command, "passed": True, "time": time.time()})
        return action == "finish"

    def run(self):
        freeze(self.root, self.commit)
        for name in ("control", "snapshots"):
            (self.root / name).mkdir(mode=0o700)
        self.body_port = self.body_port or previous.previous.available_port()
        self.browser_port = self.browser_port or previous.previous.available_port()
        if self.body_port == self.browser_port or any(type(port) is not int or not 1 <= port <= 65535 for port in (self.body_port, self.browser_port)):
            raise protocol.Refusal("body and browser ports must be distinct bounded owned endpoints")
        self.body_origin, self.browser_origin = f"http://127.0.0.1:{self.body_port}", f"http://127.0.0.1:{self.browser_port}"
        stopped = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
        signal.signal(signal.SIGINT, lambda *_: stopped.set())
        try:
            self.launch("body", initialize=True)
            self.identity = self.wait_public(self.body_origin, "/identity")
            retain(self.root / "identity.json", self.identity)
            upstream = self.body_origin
            self.relay = HeldReplyRelay(self.body_origin, self.root / "relay", hold_first_dispatch=self.case == "host-inflight").start()
            upstream = self.relay.origin
            log = (self.root / "initialization.log").open("xb")
            self.logs.append(log)
            init = subprocess.Popen([str(Path(os.environ.get("FOOTWORK_PYTHON", str(BASE / ".venv/bin/python")))), str(BASE / "network_bench_operator.py"), "init",
                "--root", str(self.root / "operator"), "--body-origin", upstream], cwd=REPO, stdout=log, stderr=log, start_new_session=True)
            record = {"role": "initialization", "pid": init.pid, "group": init.pid}
            self.processes.append((init, record))
            self.ledger["processes"].append(record)
            if init.wait(timeout=30):
                raise protocol.Refusal("owned workbench initialization failed")
            self.launch("workbench")
            public = self.wait_public(self.browser_origin, "/api/state")
            retain(self.root / "initial-public.json", public)
            self.ledger.update(ready=True, body_origin=self.body_origin, browser_origin=self.browser_origin,
                app_id=public["app_id"], body_id=self.identity["body_id"], case=self.case)
            retain(self.root / "ready.json", self.ledger)
            print(json.dumps(self.ledger), flush=True)
            deadline, handled, done = time.monotonic() + 1200, set(), False
            while not stopped.is_set() and not done:
                if time.monotonic() >= deadline:
                    raise protocol.Refusal("hard crash case exceeded its twenty-minute bound")
                if any(process is not None and process.poll() is not None for process in self.active.values()):
                    raise protocol.Refusal("owned role exited without its exact crash control")
                if not self.boundary and self.case in ("host-inflight", "body-native-gap"):
                    gate_path = self.root / ("relay" if self.case == "host-inflight" else "body") / "barrier.json"
                    if gate_path.exists():
                        gate = read(gate_path)
                        self.crash(CASES[self.case], gate["command_id"], gate)
                for path in sorted((self.root / "control").glob("*.request.json")):
                    if path.name in handled:
                        continue
                    command = read(path)
                    if path.name != f"{command['sequence']:06d}.request.json":
                        raise protocol.Refusal("control filename and sequence disagree")
                    handled.add(path.name)
                    done = self.control(command)
                    if done:
                        break
                stopped.wait(.05)
            retain(self.root / "final-public.json", get(self.browser_origin, "/api/state"))
        except BaseException as exc:
            self.ledger["error"] = type(exc).__name__ + ": " + str(exc)
            raise
        finally:
            for role in ("workbench",):
                if self.active.get(role) is not None and self.active[role].poll() is None:
                    with contextlib.suppress(OSError, protocol.Refusal, subprocess.SubprocessError):
                        self.stop(role)
            if self.relay:
                self.relay.close()
            if self.active.get("body") is not None and self.active["body"].poll() is None:
                with contextlib.suppress(OSError, protocol.Refusal, subprocess.SubprocessError):
                    self.stop("body")
            for process, record in self.processes:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                    self.ledger["cleanup_error"] = "a role required forced cleanup after its ordinary stop"
                record.update(exit_observed=process.poll() is not None, returncode=process.returncode)
            for log in self.logs:
                log.close()
            self.ledger["owned_processes_exited"] = all(process.poll() is not None for process, _ in self.processes)
            retain(self.root / "process-ledger.json", self.ledger)
        return self.ledger



def selected_public(value):
    return {key: value[key] for key in ("app_id", "runner_status", "jobs", "connection", "recovery",
            "model_request_pending", "active_job_id", "current_frame")}


def record(root, name, text_file, action, screenshot=None):
    root = protocol.directory(root)
    protocol.identity(name)
    ready = read(root / "ready.json")
    text_path = Path(text_file).resolve()
    if root not in text_path.parents:
        raise protocol.Refusal("browser evidence must be retained inside its owned trial root")
    visible = protocol.read_bytes(text_path, maximum=16000).decode("utf-8")
    screenshot_path = Path(screenshot).resolve() if screenshot else None
    if screenshot_path and (root not in screenshot_path.parents or not screenshot_path.is_file()):
        raise protocol.Refusal("screenshot evidence must be owned by this trial")
    step = {"name": name, "time": time.time(), "browser_action": action, "visible_text": visible,
            "screenshot": str(screenshot_path) if screenshot_path else None, "offline": False, "cached_public": None}
    try:
        public = get(ready["browser_origin"], "/api/state")
        if public["app_id"] != ready["app_id"] or public["connection"]["body_id"] != ready["body_id"]:
            raise protocol.Refusal("browser evidence belongs to another application or body")
        client = body_client.read_journal(root / "operator" / "client" / "client.json")
        step.update(state=selected_public(public), client_commands=len(client["commands"]), pending_command_ids=client["pending_command_ids"])
    except (OSError, http.client.HTTPException) as exc:
        ledger = read(root / "crash-ledger.json")
        boundary = ledger["boundaries"][0]
        if boundary["role"] != "workbench" or boundary["restored_snapshot"] is not None:
            raise protocol.Refusal("offline evidence requires this trial's crashed, unrestored host") from exc
        snapshot_path = root / "snapshots" / boundary["offline_snapshot"]
        snapshot, before = read(snapshot_path), read(root / "snapshots" / boundary["pre_snapshot"])
        step.update(state=None, offline=True, fetch_error=str(exc), cached_public=selected_public(before["public"]) if before["public"] else None,
            pins={key: ready[key] for key in ("app_id", "body_id")},
            snapshot_provenance={"name": boundary["offline_snapshot"], "sha256": protocol.sha(protocol.read_bytes(snapshot_path))},
            client_commands=len(snapshot["client"]["commands"]), pending_command_ids=snapshot["client"]["pending_command_ids"])
    path = root / "ui-ledger.json"
    ledger = read(path) if path.exists() else {"steps": []}
    if any(item["name"] == name for item in ledger["steps"]):
        raise protocol.Refusal("browser evidence step already retained")
    ledger["steps"].append(step)
    if len(protocol.encoded(ledger)) > protocol.MAX_BYTES:
        raise protocol.Refusal("browser evidence aggregate exceeded its 64 KiB bound")
    protocol.persist(path, ledger)
    return {"name": name, "offline": step["offline"], "client_commands": step["client_commands"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    run = sub.add_parser("run")
    run.add_argument("--root", type=Path, required=True)
    run.add_argument("--source-commit", required=True)
    run.add_argument("--case", choices=tuple(CASES), required=True)
    run.add_argument("--body-port", type=int, default=0)
    run.add_argument("--browser-port", type=int, default=0)
    control = sub.add_parser("request")
    control.add_argument("--root", type=Path, required=True)
    control.add_argument("--action", choices=("crash-role", "start-role", "finish"), required=True)
    control.add_argument("--role", choices=("body", "workbench"))
    capture = sub.add_parser("record")
    capture.add_argument("--root", type=Path, required=True)
    capture.add_argument("--name", required=True)
    capture.add_argument("--text-file", type=Path, required=True)
    capture.add_argument("--action", required=True)
    capture.add_argument("--screenshot")
    args = parser.parse_args()
    if args.mode == "run":
        root = protocol.directory(args.root, create=True)
        with protocol.locked(root):
            value = Trial(root, args.source_commit, args.case, args.body_port, args.browser_port).run()
    elif args.mode == "request":
        value = request(args.root, args.action, args.role)
    else:
        value = record(args.root, args.name, args.text_file, args.action, args.screenshot)
    print(json.dumps(value), flush=True)


if __name__ == "__main__":
    main()
