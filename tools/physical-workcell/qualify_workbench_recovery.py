"""SIM14 owned event-publication and active-planner SIGKILL browser trials."""
import argparse
import contextlib
import http.client
import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

import body_client
import order_protocol as protocol
import qualify_workbench_crashes as sim13
import qualify_workbench_restarts as previous

BASE, REPO = previous.BASE, previous.REPO
CASES = {"host-publication": "workbench", "host-planning": "workbench"}
SOURCES = list(dict.fromkeys(sim13.SOURCES + [BASE / name for name in (
    "crash_body.py", "qualify_workbench_crashes.py", "score_workbench_crashes.py",
    "test_workbench_crash_harness.py", "crash_operator.py", "qualify_workbench_recovery.py",
    "score_workbench_recovery.py", "test_workbench_recovery_trials.py", "planner_guard.py", "body_contract.py", "bench_body_contract.py", "persistent_body_client.py")]))
read, retain, get = previous.read, previous.retain, previous.get


descendants, indexed_command, HeldReplyRelay = sim13.descendants, sim13.indexed_command, sim13.HeldReplyRelay


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
    if action not in ("start-role", "finish") or (role == "workbench") != (action == "start-role"):
        raise protocol.Refusal("only explicit workbench restart or finish is allowed")
    sequence = max((int(p.name.split(".")[0]) for p in (root / "control").glob("*.request.json")), default=0) + 1
    value = validate_control({"sequence": sequence, "action": action, "role": role, "expect": None, "requested_time": time.time()})
    retain(root / "control" / f"{sequence:06d}.request.json", value)
    return value


def validate_planning_gate(root, gate):
    directory = protocol.directory(root / "operator/calls" / gate["call_directory"])
    intent, live = read(directory / "planner-intent.json"), read(directory / "planner-process.json")
    if live != gate["planner"] or intent["owner"] != live["owner"] or intent["host_pid"] != gate["pid"] or live["host_pid"] != gate["pid"]:
        raise protocol.Refusal("planning gate differs from exact persistent ownership")
    if live["process_exit_observed"] or live["group_closed"] or live["planner_pid"] != live["planner_pgid"]:
        raise protocol.Refusal("planning gate has no live independent planner")
    for pid in (live["guardian_pid"], live["planner_pid"]):
        os.kill(pid, 0)
    if os.getpgid(live["planner_pid"]) != live["planner_pgid"]:
        raise protocol.Refusal("live planner group differs from recorded ownership")
    if (directory / "planner-closure.json").exists():
        raise protocol.Refusal("planner was already closed before crash")
    return live


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
        first = role == "workbench" and not any(r["role"] == role for r in self.ledger["processes"])
        if not first:
            process = super().launch(role, initialize)
        else:
            log = (self.root / "workbench-01.log").open("xb")
            process = subprocess.Popen([str(BASE / ".venv/bin/python"), str(BASE / "crash_operator.py"),
                "--root", str(self.root / "operator"), "--port", str(self.browser_port), "--gate",
                "publication" if self.case == "host-publication" else "planning"], cwd=REPO,
                stdout=log, stderr=log, start_new_session=True)
            entry = {"role": role, "boot": 1, "pid": process.pid, "root": str(self.root / "operator"),
                "port": self.browser_port, "initialized": False, "log": "workbench-01.log"}
            self.processes.append((process, entry))
            self.logs.append(log)
            self.ledger["processes"].append(entry)
            self.active[role] = process
        entry = next(r for p, r in self.processes if p is process)
        entry["group"] = os.getpgid(process.pid)
        if entry["group"] != process.pid:
            raise protocol.Refusal("owned actor did not create its own process group")
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
            if key == "public" and (self.active.get("workbench") is None or
                self.boundary is None and (self.root / "operator/barrier.json").exists()):
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

    def crash_gate(self, gate):
        process = self.active["workbench"]
        if self.boundary or process.poll() is not None or gate["pid"] != process.pid or os.getpgid(process.pid) != process.pid:
            raise protocol.Refusal("gate does not match this exact live owned host")
        token = gate.get("command_id")
        if self.case == "host-publication":
            receiver = indexed_command(self.root, token)
            if receiver["intent"]["request_sha256"] != gate["request_sha256"] or not receiver["terminal"] or receiver["terminal"]["result"]["outcome"] != "executed":
                raise protocol.Refusal("publication gate lacks exact indexed executed dispatch")
        else:
            validate_planning_gate(self.root, gate)
        before_name, _ = self.snapshot("before", token)
        children = descendants(process.pid)
        entry = next(r for p, r in self.processes if p is process)
        if self.case == "host-planning":
            validate_planning_gate(self.root, gate)
        os.kill(process.pid, signal.SIGKILL)  # ONLY host; guardian must reap its independent child.
        process.wait(timeout=5)
        if process.returncode != -9:
            raise protocol.Refusal("owned host was not reaped with SIGKILL")
        entry.update(exit_observed=True, returncode=-9, stopped_time=time.time(), signal="SIGKILL",
            signal_target="host_pid_only", children_before=children)
        self.active["workbench"] = None
        offline_name, _ = self.snapshot("offline", token)
        self.boundary = {"case": self.case, "role": "workbench", "command_id": token,
            "request_sha256": gate.get("request_sha256"), "gate": gate, "pre_snapshot": before_name,
            "offline_snapshot": offline_name, "restored_snapshot": None, "process": dict(entry),
            "old_epoch": self.identity["epoch"], "new_epoch": None}
        self.stops["workbench"] = True
        protocol.persist(self.root / "crash-ledger.json", {"case": self.case, "boundaries": [self.boundary]})

    def control(self, command):
        validate_control(command)
        action, role = command["action"], command["role"]
        if action == "crash-role":
            raise protocol.Refusal("SIM14 crashes only through its exact automatic diagnostic gate")
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
            self.relay = HeldReplyRelay(self.body_origin, self.root / "relay", hold_first_dispatch=False).start()
            upstream = self.relay.origin
            log = (self.root / "initialization.log").open("xb")
            self.logs.append(log)
            init = subprocess.Popen([str(BASE / ".venv/bin/python"), str(BASE / "network_bench_operator.py"), "init",
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
                if not self.boundary and (self.root / "operator/barrier.json").exists():
                    self.crash_gate(read(self.root / "operator/barrier.json"))
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
