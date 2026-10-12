"""Frozen owned-process restart trial; all product actions come from the browser.

run --root PATH --source-commit SHA
request --root PATH --action stop-role --role workbench --predicate planning --wait-s 40
request --root PATH --action start-role --role workbench
request --root PATH --action finish
Numbered control requests capture fresh expectations; mismatches never signal a PID.
"""
import argparse
import json
import signal
import subprocess
import threading
import time
from pathlib import Path

import body_client
import order_protocol as protocol
import qualify_network_workbench as previous

BASE, REPO = previous.BASE, previous.REPO
SOURCES = list(dict.fromkeys(previous.SOURCES + [BASE / "qualify_workbench_restarts.py", BASE / "score_workbench_restarts.py"]))


def retain(path, value):
    protocol.create_file(path, protocol.encoded(value))


def read(path):
    return body_client.read_journal(path)


def get(origin, path, pinned=None):
    status, content = body_client.http_call(origin, "GET", path, body_client.pinned_headers(pinned) if pinned else {}, timeout=1)
    if status != 200:
        raise protocol.Refusal("public read refused")
    return protocol.decode(content)


def expected(public):
    return {"app_id": public["app_id"], "body_id": public["connection"]["body_id"],
            "runner_status": public["runner_status"], "model_request_pending": public["model_request_pending"],
            "active_job_id": public["active_job_id"], "usage_calls": public["usage"]["calls"],
            "recovery_command_id": public["recovery"]["command_id"]}


def matches(public, predicate):
    if predicate == "planning":
        return public["model_request_pending"] is True and public["runner_status"] == "running"
    if predicate == "uncertain":
        return bool(public["recovery"]["command_id"] and public["runner_status"] == "blocked")
    return predicate == "none"


def validate_control(command):
    protocol.fields(command, ("sequence", "action", "role", "predicate", "expect", "requested_time"), "restart control")
    if type(command["sequence"]) is not int or not 1 <= command["sequence"] <= 4096:
        raise protocol.Refusal("control sequence must be a bounded positive integer")
    action, role, predicate = command["action"], command["role"], command["predicate"]
    if (not isinstance(action, str) or action not in {"stop-role", "start-role", "finish"} or
            role is not None and (not isinstance(role, str) or role not in {"body", "workbench"}) or
            not isinstance(predicate, str) or predicate not in {"planning", "uncertain", "none"} or
            action != "finish" and role is None or action == "finish" and role is not None or
            action == "stop-role" and (predicate == "none" or command["expect"] is None) or
            action != "stop-role" and predicate != "none"):
        raise protocol.Refusal("control action, role or predicate is invalid")
    protocol.finite(command["requested_time"])
    if command["expect"] is not None:
        protocol.fields(command["expect"], ("app_id", "body_id", "runner_status", "model_request_pending",
                        "active_job_id", "usage_calls", "recovery_command_id"), "public expectation")
        for key in ("app_id", "body_id"):
            protocol.identity(command["expect"][key])
        for key in ("active_job_id", "recovery_command_id"):
            if command["expect"][key] is not None:
                protocol.identity(command["expect"][key])
        if (type(command["expect"]["model_request_pending"]) is not bool or
                type(command["expect"]["usage_calls"]) is not int or not 0 <= command["expect"]["usage_calls"] <= 96 or
                not isinstance(command["expect"]["runner_status"], str)):
            raise protocol.Refusal("public expectation has invalid types")
    return command


def request(root, action, role=None, predicate="none", wait_s=0):
    root = protocol.directory(root)
    ready = read(root / "ready.json")
    if action not in {"stop-role", "start-role", "finish"} or role not in {None, "body", "workbench"}:
        raise protocol.Refusal("unsupported process control")
    if action != "finish" and role is None or action == "stop-role" and predicate not in {"planning", "uncertain"}:
        raise protocol.Refusal("stop requires an exact planning or uncertain predicate")
    wait_s = protocol.finite(wait_s)
    if not 0 <= wait_s <= 40:
        raise protocol.Refusal("predicate wait exceeds forty seconds")
    deadline = time.monotonic() + wait_s
    while True:
        public = None if action == "start-role" and role == "workbench" else get(ready["browser_origin"], "/api/state")
        if public is None or matches(public, predicate):
            break
        if time.monotonic() >= deadline:
            raise protocol.Refusal("public state does not match the requested interruption predicate")
        time.sleep(.05)
    paths = list((root / "control").glob("*.request.json"))
    sequence = max((int(path.name.split(".")[0]) for path in paths), default=0) + 1
    value = {"sequence": sequence, "action": action, "role": role, "predicate": predicate,
             "expect": expected(public) if public else None, "requested_time": time.time()}
    validate_control(value)
    retain(root / "control" / f"{sequence:06d}.request.json", value)
    return value


def freeze(root, commit):
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != commit:
        raise protocol.Refusal("trial requires its committed source head")
    files = {}
    for path in SOURCES:
        name = str(path.relative_to(REPO))
        content = protocol.read_bytes(path)
        if subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=REPO) != content:
            raise protocol.Refusal("source is not frozen: " + name)
        files[name] = protocol.sha(content)
    retain(root / "source-freeze.json", {"commit": commit, "files": files})


class Trial:
    def __init__(self, root, commit, body_port=0, browser_port=0):
        self.root, self.commit = protocol.directory(root, create=True), commit
        self.body_port, self.browser_port = body_port, browser_port
        self.action_performed = False
        self.processes, self.logs, self.active, self.stops = [], [], {}, {}
        self.ledger = {"source_commit": commit, "planner": "actual_codex_cli_images_over_TCP", "simulation": True,
                       "processes": [], "ready": False}
        self.restart_ledger = {"boundaries": []}

    def launch(self, role, initialize=False):
        boot = sum(record["role"] == role for record in self.ledger["processes"]) + 1
        if role == "body":
            args = [str(BASE / "body_network.py"), "--root", str(self.root / "body"), "--port", str(self.body_port)]
            if initialize:
                args += ["--initialize", "--diagnostic"]
        else:
            args = [str(BASE / "network_bench_operator.py"), "serve", "--root", str(self.root / "operator"),
                    "--port", str(self.browser_port), "--backend", "codex"]
        log_name = f"{role}-{boot:02d}.log"
        log = (self.root / log_name).open("xb")
        log_path = self.root / log_name
        log_path.chmod(0o600)
        process = subprocess.Popen([str(BASE / ".venv/bin/python"), *args], cwd=REPO, stdout=log, stderr=log,
                                   start_new_session=True)
        record = {"role": role, "boot": boot, "pid": process.pid, "root": str(self.root / ("body" if role == "body" else "operator")),
                  "port": self.body_port if role == "body" else self.browser_port, "initialized": initialize, "log": log_name}
        self.processes.append((process, record))
        self.logs.append(log)
        self.ledger["processes"].append(record)
        self.active[role] = process
        return process

    def stop(self, role):
        process = self.active.get(role)
        if process is None or process.poll() is not None:
            raise protocol.Refusal("requested role has no live owned process")
        record = next((record for proc, record in self.processes if proc is process), None)
        if record is None or record["role"] != role or record["pid"] != process.pid:
            raise protocol.Refusal("process handle is not registered to this trial role")
        process.terminate()
        try:
            process.wait(timeout=40)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait(timeout=5)
            self.ledger["error"] = "owned graceful stop exceeded forty seconds; forced cleanup is not qualification"
            raise protocol.Refusal(self.ledger["error"]) from exc
        self.active[role] = None
        record.update(exit_observed=True, returncode=process.returncode, stopped_time=time.time())
        return dict(record)

    def wait_public(self, origin, path):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                return get(origin, path)
            except (OSError, ValueError):
                if any(p is not None and p.poll() is not None for p in self.active.values()):
                    raise protocol.Refusal("owned role exited during readiness")
                time.sleep(.05)
        raise protocol.Refusal("owned endpoint readiness timed out")

    def snapshot(self, sequence, label):
        value = {"time": time.time(), "public": None, "body_identity": None, "body_state": None,
                 "processes": {role: p.pid if p is not None and p.poll() is None else None for role, p in self.active.items()}}
        for key, origin, path, pinned in (("public", self.browser_origin, "/api/state", None),
                                        ("body_identity", self.body_origin, "/identity", None),
                                        ("body_state", self.body_origin, "/state", self.identity)):
            try:
                value[key] = get(origin, path, pinned)
            except (OSError, ValueError) as exc:
                value[key + "_error"] = str(exc)
        host = read(self.root / "operator" / "operator.json")
        client = read(self.root / "operator" / "client" / "client.json")
        commands = {}
        for token, index in client["commands"].items():
            content = protocol.read_bytes(self.root / "operator" / "client" / "requests" / (token + ".json"))
            if protocol.sha(content) != index["request_sha256"]:
                raise protocol.Refusal("client immutable request changed during snapshot")
            commands[token] = {"request_sha256": index["request_sha256"], "send_count": index["send_count"],
                               "state": index["state"], "operation": protocol.decode(content)["operation"]}
        value["client"] = {"commands": commands, "pending_command_ids": client["pending_command_ids"],
                           "lease": client["lease"], "identity": client["identity"]}
        value["host"] = {key: host[key] for key in ("app_id", "body_identity", "stage", "frame", "runner_status", "sequence", "usage")}
        value["posts"] = []
        for path in sorted((self.root / "operator" / "link" / "events").glob("*.json")):
            event = read(path)
            if event["kind"] == "received" and event.get("method") == "POST" and event.get("command_id"):
                value["posts"].append({key: event[key] for key in ("sequence", "command_id", "payload_sha256")})
        name = f"{sequence:06d}-{label}.json"
        retain(self.root / "snapshots" / name, value)
        return name, value

    def control(self, command):
        validate_control(command)
        sequence, action, role = command["sequence"], command["action"], command["role"]
        result = {"request": command, "passed": False}
        before_name, before = self.snapshot(sequence, "before")
        result["before"] = before_name
        if command["expect"] is not None and (before["public"] is None or expected(before["public"]) != command["expect"]):
            raise protocol.Refusal("public state changed since this exact interruption was requested")
        if action == "stop-role":
            if role not in {"body", "workbench"} or not matches(before["public"], command["predicate"]):
                raise protocol.Refusal("interruption predicate no longer matches")
            fresh = get(self.browser_origin, "/api/state")
            if expected(fresh) != command["expect"] or not matches(fresh, command["predicate"]):
                raise protocol.Refusal("predicate changed immediately before owned process signal")
            self.action_performed = True
            result["process"] = self.stop(role)
            self.stops[role] = {"sequence": sequence, "predicate": command["predicate"]}
        elif action == "start-role":
            if role not in self.stops or self.active.get(role) is not None:
                raise protocol.Refusal("restart requires this trial's stopped role")
            self.action_performed = True
            process = self.launch(role)
            ready = self.wait_public(self.body_origin if role == "body" else self.browser_origin,
                                     "/identity" if role == "body" else "/api/state")
            result.update(stopped_sequence=self.stops[role]["sequence"], predicate=self.stops[role]["predicate"], pid=process.pid)
            # Give real health/epoch handling a bounded opportunity; never mutate host state.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                public = get(self.browser_origin, "/api/state")
                epoch_seen = role != "body" or public["connection"]["epoch"] == ready["epoch"]
                if public["runner_status"] != "running" and not public["model_request_pending"] and epoch_seen:
                    break
                time.sleep(.05)
            if public["runner_status"] == "running" or public["model_request_pending"] or not epoch_seen:
                raise protocol.Refusal("restarted body or workbench did not pause its old planning")
            self.stops.pop(role)
        elif action != "finish":
            raise protocol.Refusal("unsupported restart action")
        after_name, after = self.snapshot(sequence, "after")
        result.update(after=after_name, passed=True, action_performed=self.action_performed)
        self.restart_ledger["boundaries"].append(result)
        protocol.persist(self.root / "restart-ledger.json", self.restart_ledger)
        retain(self.root / "control" / f"{sequence:06d}.result.json", result)
        return action == "finish", after

    def run(self):
        freeze(self.root, self.commit)
        for name in ("control", "snapshots"):
            (self.root / name).mkdir(mode=0o700)
        self.body_port = self.body_port or previous.available_port()
        self.browser_port = self.browser_port or previous.available_port()
        if self.body_port == self.browser_port or any(type(port) is not int or not 1 <= port <= 65535 for port in (self.body_port, self.browser_port)):
            raise protocol.Refusal("body and browser need distinct bounded owned ports")
        self.body_origin, self.browser_origin = f"http://127.0.0.1:{self.body_port}", f"http://127.0.0.1:{self.browser_port}"
        stopped = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
        signal.signal(signal.SIGINT, lambda *_: stopped.set())
        try:
            self.launch("body", initialize=True)
            self.identity = self.wait_public(self.body_origin, "/identity")
            retain(self.root / "identity.json", self.identity)
            initialization = subprocess.Popen([str(BASE / ".venv/bin/python"), str(BASE / "network_bench_operator.py"), "init",
                "--root", str(self.root / "operator"), "--body-origin", self.body_origin], cwd=REPO,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            record = {"role": "initialization", "pid": initialization.pid}
            self.processes.append((initialization, record))
            self.ledger["processes"].append(record)
            try:
                stdout, stderr = initialization.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                initialization.kill()
                stdout, stderr = initialization.communicate(timeout=5)
                self.ledger["error"] = "initialization exceeded its bounded deadline"
            protocol.create_file(self.root / "initialization.stdout", stdout)
            protocol.create_file(self.root / "initialization.stderr", stderr)
            if initialization.returncode:
                raise protocol.Refusal("workbench initialization failed")
            self.launch("workbench")
            initial = self.wait_public(self.browser_origin, "/api/state")
            retain(self.root / "initial-public.json", initial)
            self.ledger.update(ready=True, body_origin=self.body_origin, browser_origin=self.browser_origin,
                               app_id=initial["app_id"], body_id=self.identity["body_id"])
            retain(self.root / "ready.json", self.ledger)
            print(json.dumps(self.ledger), flush=True)
            deadline, handled, finished = time.monotonic() + 3600, set(), False
            while not stopped.is_set() and not finished:
                if time.monotonic() >= deadline:
                    raise protocol.Refusal("restart qualification exceeded sixty minutes")
                if any(p is not None and p.poll() is not None for p in self.active.values()):
                    raise protocol.Refusal("owned process exited without a matching control request")
                for path in sorted((self.root / "control").glob("*.request.json")):
                    if path.name in handled:
                        continue
                    handled.add(path.name)
                    command = read(path)
                    if path.name != f"{command['sequence']:06d}.request.json":
                        raise protocol.Refusal("request file sequence disagrees with its exact payload")
                    self.action_performed = False
                    try:
                        finished, _ = self.control(command)
                    except protocol.Refusal as exc:
                        retain(self.root / "control" / path.name.replace("request", "result"),
                               {"request": command, "passed": False, "reason": str(exc), "action_performed": self.action_performed})
                        if self.action_performed or self.ledger.get("error"):
                            raise
                    if finished:
                        break
                stopped.wait(.05)
            retain(self.root / "final-public.json", get(self.browser_origin, "/api/state"))
        except Exception as exc:
            self.ledger["error"] = type(exc).__name__ + ": " + str(exc)
            raise
        finally:
            for role in ("workbench", "body"):
                if self.active.get(role) is not None and self.active[role].poll() is None:
                    try:
                        self.stop(role)
                    except (OSError, protocol.Refusal, subprocess.SubprocessError) as exc:
                        self.ledger["cleanup_error"] = str(exc)
            for process, record in self.processes:
                record.update(exit_observed=process.poll() is not None, returncode=process.poll())
            for log in self.logs:
                log.close()
            self.ledger["owned_processes_exited"] = all(process.poll() is not None for process, _ in self.processes)
            retain(self.root / "process-ledger.json", self.ledger)
        return self.ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--root", required=True, type=Path)
    run_parser.add_argument("--source-commit", required=True)
    run_parser.add_argument("--browser-port", type=int, default=0)
    run_parser.add_argument("--body-port", type=int, default=0)
    control = sub.add_parser("request")
    control.add_argument("--root", required=True, type=Path)
    control.add_argument("--action", required=True, choices=("stop-role", "start-role", "finish"))
    control.add_argument("--role", choices=("body", "workbench"))
    control.add_argument("--predicate", default="none", choices=("none", "planning", "uncertain"))
    control.add_argument("--wait-s", type=float, default=0)
    args = parser.parse_args()
    if args.mode == "run":
        root = protocol.directory(args.root, create=True)
        with protocol.locked(root):
            result = Trial(root, args.source_commit, args.body_port, args.browser_port).run()
    else:
        result = request(args.root, args.action, args.role, args.predicate, args.wait_s)
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
