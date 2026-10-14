"""Independent, private Unix-socket controller for an initialized simulated episode."""

import argparse
import contextlib
import importlib.util
import json
import os
import signal
import socket
import stat
import sys
import threading
import time
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("controller_episode", BASE / "episode_runner.py")
episode = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(episode)
vision, body, Refusal = episode.vision, episode.body, episode.Refusal
MAX_RPC = 8192
TERMINAL = {"executed", "staged", "cancelled", "refused", "unknown"}


def operation_path(control, operation_id):
    body.op_path(control, operation_id)  # Shared exact safe-ID validation, no reservation.
    return control / f"goal-{body.sha(operation_id.encode())}.json"


def request_path(control, operation_id):
    operation_path(control, operation_id)
    return control / f"goal-request-{body.sha(operation_id.encode())}.json"


def socket_path(control, create=False):
    # Darwin's sockaddr_un is short. Keep the derived owned socket under the existing output.
    directory = body.directory(body.OUTPUT / ".s", create=create)
    path = directory / (body.sha(str(control).encode())[:20] + ".sock")
    if len(os.fsencode(path)) >= 104:
        raise Refusal("owned Unix socket path exceeds the platform bound")
    return path


def source_binding(root, control):
    record = episode.lifecycle(root)
    return {"version": 1, "source_kind": body.SOURCE_KIND, "run_dir": str(root),
            "controller_dir": str(control), "episode_id": record["episode_id"],
            "case_sha256": record["case_sha256"], "episode_fingerprint": record["fingerprint"],
            "controller_sha256": body.sha(body.read_bytes(Path(__file__))), "socket_path": str(socket_path(control))}


def receive(connection):
    connection.settimeout(2)
    content = b""
    while b"\n" not in content:
        chunk = connection.recv(min(4096, MAX_RPC + 1 - len(content)))
        if not chunk:
            raise Refusal("RPC ended before its newline-delimited request")
        content += chunk
        if len(content) > MAX_RPC:
            raise Refusal("RPC request exceeds its bounded size")
    line, extra = content.split(b"\n", 1)
    if extra:
        raise Refusal("one RPC connection accepts exactly one request")
    value = body.decoded(line)
    if not isinstance(value, dict):
        raise Refusal("RPC request must be an object")
    return value


class Controller:
    def __init__(self, root, control, dispatch_delay_s=0, pace_s=0):
        self.root, self.control = root, control
        self.dispatch_delay_s, self.pace_s = body.number(dispatch_delay_s), body.number(pace_s)
        if not 0 <= self.dispatch_delay_s <= 5 or not 0 <= self.pace_s <= .003:
            raise Refusal("dispatch delay or native pacing exceeds the diagnostic bound")
        if root == control or root in control.parents or control in root.parents:
            raise Refusal("controller directory must be separate from the episode directory")
        socket_path(control, create=True)
        self.binding = source_binding(root, control)
        binding_file = control / "controller-binding.json"
        if binding_file.exists() or binding_file.is_symlink():
            if body.decoded(body.read_bytes(binding_file)) != self.binding:
                raise Refusal("controller source, case or run binding changed")
        else:
            if any(path.name != "lock" for path in control.iterdir()):
                raise Refusal("unreceipted controller files exist; no implicit reset")
            body.create_file(binding_file, body.encoded(self.binding))
        self.incarnation = uuid.uuid4().hex
        self.mutex = threading.RLock()
        self.shutdown = threading.Event()
        self.cancel_event = threading.Event()
        self.worker = None
        self.active_id = None
        self.blocked = False
        self.current_problem = None
        self.goals = {}
        for path in sorted(control.glob("goal-*.json")):
            if path.name.startswith("goal-request-"):
                continue
            goal = self.load_goal(path)
            if goal["phase"] in {"accepted", "running", "unknown"}:
                self.reconcile(goal)
            self.goals[goal["operation_id"]] = goal
            self.blocked |= goal["phase"] == "unknown"
        try:
            loaded = body.load(root)
            self.blocked |= body.unresolved(root, loaded[0]) or vision.wrapper_unresolved(root)
        except (Refusal, OSError, KeyError, TypeError, ValueError):
            self.current_problem = "current state or lower evidence is unavailable; historical goals remain retained"
        self.incarnation_record = {"version": 1, "current_incarnation": self.incarnation,
                                   "pid": os.getpid(), "started_at": time.time(), "phase": "serving",
                                   "binding": self.binding, "dispatch_delay_s": self.dispatch_delay_s,
                                   "pace_s": self.pace_s}
        body.create_file(control / f"incarnation-{self.incarnation}.json", body.encoded(self.incarnation_record))
        body.utils.persist(control / "controller-current.json", self.incarnation_record)

    def validate_current(self):
        if (source_binding(self.root, self.control) != self.binding or
                body.decoded(body.read_bytes(self.control / "controller-binding.json")) != self.binding):
            raise Refusal("controller source, episode or case binding changed")

    def load_goal(self, path):
        goal = body.decoded(body.read_bytes(path))
        if (not isinstance(goal, dict) or goal.get("version") != 1 or
                goal.get("binding") != self.binding or goal.get("phase") not in TERMINAL | {"accepted", "running"} or
                operation_path(self.control, goal.get("operation_id")) != path):
            raise Refusal("controller goal identity, phase or binding is invalid")
        content = body.read_bytes(request_path(self.control, goal["operation_id"]))
        if (body.sha(content) != goal.get("proposal_sha256") or body.decoded(content) != goal.get("proposal") or
                goal["proposal"] != vision.schema(goal["proposal"], self.root)):
            raise Refusal("controller accepted proposal bytes changed")
        return goal

    def persist_goal(self, goal):
        body.utils.persist(operation_path(self.control, goal["operation_id"]), goal)

    def terminal_receipt(self, goal):
        path = vision.proposal_path(self.root, goal["proposal"]["token"])
        receipt = vision.load_proposal_record(path)
        if (receipt["proposal"] != goal["proposal"] or receipt["proposal_sha256"] != goal["proposal_sha256"] or
                receipt["phase"] not in {"executed", "staged"}):
            raise Refusal("lower receipt is not an exact terminal result for this accepted goal")
        # load_proposal_record checks native request, source/case/frame and retained state identity.
        native = body.load_op(body.op_path(self.root, "vision-" + body.sha(goal["proposal"]["token"].encode())))
        generation = native.get("after_generation", goal["proposal"]["generation"])
        state_sha = native.get("after_state_sha256", native.get("state_sha256"))
        order_bytes = body.read_bytes(self.root / "work-order.json")
        if (body.sha(order_bytes) != receipt["binding"]["work_order_sha256"] or
                body.sha(body.read_bytes(self.root / "model.xml")) != body.fingerprints()["model_sha256"]):
            raise Refusal("historical work-order or model source changed")
        order = body.order_schema(body.decoded(order_bytes))
        episode.generation_predicate(self.root, order, generation, state_sha)
        return receipt

    def set_terminal(self, goal, receipt):
        public = vision.public_receipt(receipt)
        stats = receipt.get("contact_statistics", {})
        if stats.get("cancellation_requested"):
            if stats.get("stop_verified") is not True:
                raise Refusal("cancelled motion lacks verified lower-layer stop evidence")
            goal.update(phase="cancelled", cancellation_stage="during_motion",
                        stop_evidence={"stop_verified": True, "state_retained": True,
                                       "method": "native_velocity_after_held_command_settle",
                                       "retained_generation": receipt["after_generation"],
                                       "retained_state_sha256": receipt["after_state_sha256"], **stats["stop_evidence"]})
        else:
            goal["phase"] = receipt["phase"]
        if "reason" in goal:
            goal["prior_reason"] = goal.pop("reason")
        goal.update(receipt=public, finished_at=time.time())

    def reconcile(self, goal):
        try:
            receipt = self.terminal_receipt(goal)
            self.set_terminal(goal, receipt)
            goal["reconciled"] = True
        except (Refusal, OSError, KeyError, TypeError, ValueError):
            goal.update(phase="unknown", reason="no exact terminal image/native receipt; unfinished work will not replay",
                        finished_at=time.time(), reconciled=False)
        self.persist_goal(goal)

    def health(self):
        self.validate_current()
        health = ("stopping" if self.shutdown.is_set() else "unknown" if self.current_problem else
                  "blocked" if self.blocked else "busy" if self.active_id else "ready")
        current = {}
        if health == "ready":
            try:
                loaded = body.load(self.root)
                manifest = loaded[0]
                if body.unresolved(self.root, manifest) or vision.wrapper_unresolved(self.root):
                    health = "blocked"
                elif manifest["phase"] == "completed":
                    current["current_software_artifact_check"] = body.artifact_check(self.root, manifest["result_sha256"])
                    if not current["current_software_artifact_check"]["ok"]:
                        health = "blocked"
            except (Refusal, OSError, KeyError, TypeError, ValueError):
                self.current_problem = "current state or lower evidence is unavailable; historical goals remain retained"
                health = "unknown"
        if self.current_problem:
            current["current_health_reason"] = self.current_problem
        return {"source_kind": body.SOURCE_KIND, "phase": health, "current_health": health,
                "current_incarnation": self.incarnation, "active_operation_id": self.active_id,
                "run_dir": str(self.root), "controller_dir": str(self.control), "pid": os.getpid(), **current}

    def public_goal(self, goal):
        result = self.health()
        result.update(phase=goal["phase"], operation_id=goal["operation_id"],
                      accepted_incarnation=goal["accepted_incarnation"], cancel_requested=goal["cancel_requested"],
                      historical_outcome=goal["phase"] if goal["phase"] in TERMINAL else None,
                      accepted_at=goal["accepted_at"], proposal_sha256=goal["proposal_sha256"],
                      image_generation=goal["proposal"]["generation"], replayed=False)
        for key in ("receipt", "reason", "prior_reason", "finished_at", "stop_evidence", "cancellation_stage", "reconciled"):
            if key in goal:
                result[key] = goal[key]
        return result

    def require_incarnation(self, request):
        if request.get("expected_incarnation") != self.incarnation:
            raise Refusal("expected controller incarnation is stale or missing; read health before an effect request")

    def submit(self, request):
        self.require_incarnation(request)
        operation_id = request["operation_id"]
        operation_path(self.control, operation_id)
        proposal_sha = request["proposal_sha256"]
        if not isinstance(proposal_sha, str) or not body.DIGEST.fullmatch(proposal_sha):
            raise Refusal("proposal SHA256 must be exact lowercase hexadecimal")
        content = body.read_bytes(Path(request["proposal_file"]))
        if body.sha(content) != proposal_sha:
            raise Refusal("proposal bytes differ from their bound digest")
        proposal = vision.schema(body.decoded(content), self.root)
        if operation_id in self.goals:
            goal = self.goals[operation_id]
            if goal["proposal"] != proposal or goal["proposal_sha256"] != proposal_sha:
                raise Refusal("operation ID belongs to different accepted proposal bytes")
            return self.public_goal(goal)
        if self.health()["current_health"] != "ready":
            raise Refusal("controller has active, unresolved or stopping work; no new goal admitted")
        # One controller ID owns a lower token, even when a goal was cancelled before dispatch.
        if any(goal["proposal"]["token"] == proposal["token"] for goal in self.goals.values()):
            raise Refusal("proposal token already belongs to another controller operation")
        if vision.proposal_path(self.root, proposal["token"]).exists():
            raise Refusal("proposal token has pre-existing lower history; choose a new operation")
        retained = request_path(self.control, operation_id)
        body.create_file(retained, content)
        goal = {"version": 1, "operation_id": operation_id, "proposal": proposal, "proposal_sha256": proposal_sha,
                "binding": self.binding, "accepted_incarnation": self.incarnation, "accepted_at": time.time(),
                "phase": "accepted", "cancel_requested": False}
        body.create_file(operation_path(self.control, operation_id), body.encoded(goal))
        # Persist uses file fsync + directory fsync, covering the request and goal directory
        # entries before acceptance is acknowledged. This is not power-loss qualification.
        self.persist_goal(goal)
        self.goals[operation_id] = goal
        self.active_id = operation_id
        self.cancel_event.clear()
        reply = self.public_goal(goal)
        self.worker = threading.Thread(target=self.execute, args=(goal,), name="native-controller-operation", daemon=False)
        self.worker.start()
        return reply

    def no_dispatch_cancel(self, goal):
        goal.update(phase="cancelled", finished_at=time.time(), cancellation_stage="before_dispatch",
                    stop_evidence={"stop_verified": True, "state_retained": True, "method": "no_dispatch"})
        self.persist_goal(goal)

    def execute(self, goal):
        try:
            self.cancel_event.wait(self.dispatch_delay_s)
            with self.mutex:
                if self.cancel_event.is_set():
                    self.no_dispatch_cancel(goal)
                    return
                self.validate_current()
                goal.update(phase="running", dispatch_intent_at=time.time())
                self.persist_goal(goal)
            # The service owns the episode lock. Native work runs here; renderer remains main-thread only.
            vision.apply(self.root, str(request_path(self.control, goal["operation_id"])), goal["proposal_sha256"],
                         motion_control={"cancel_requested": self.cancel_event.is_set, "pace_s": self.pace_s})
            receipt = self.terminal_receipt(goal)
            with self.mutex:
                self.set_terminal(goal, receipt)
                self.persist_goal(goal)
        except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001 - durable dispatched uncertainty cannot be replayed
            with self.mutex:
                lower = vision.proposal_path(self.root, goal["proposal"]["token"])
                native = body.op_path(self.root, "vision-" + body.sha(goal["proposal"]["token"].encode()))
                dispatched = lower.exists() or native.exists()
                goal.update(phase="unknown" if dispatched or not isinstance(exc, Refusal) else "refused",
                            reason="lower effect is unresolved" if dispatched else "proposal refused before a lower effect",
                            finished_at=time.time())
                self.blocked |= goal["phase"] == "unknown"
                self.persist_goal(goal)
        finally:
            with self.mutex:
                self.active_id = None

    def cancel(self, request):
        self.require_incarnation(request)
        goal = self.goals.get(request["operation_id"])
        if goal is None:
            raise Refusal("controller operation ID is unknown")
        if goal["phase"] not in TERMINAL:
            goal["cancel_requested"] = True
            goal["cancel_requested_at"] = time.time()
            self.persist_goal(goal)
            self.cancel_event.set()
        return self.public_goal(goal)

    def handle(self, request):
        with self.mutex:
            self.validate_current()
            command = request.get("command")
            fields = {"health": ("command",), "observe": ("command",),
                      "status": ("command", "operation_id"),
                      "cancel": ("command", "operation_id", "expected_incarnation"),
                      "submit": ("command", "operation_id", "proposal_file", "proposal_sha256", "expected_incarnation")}
            if command not in fields:
                raise Refusal("unknown controller command")
            body.fields(request, fields[command], "controller RPC")
            if command == "health":
                return self.health()
            if command == "observe":
                reply = self.health()
                if reply["current_health"] != "ready":
                    return reply
                reply.update(phase="ready", observation=vision.view(self.root))
                return reply
            if command == "submit":
                return self.submit(request)
            operation_path(self.control, request["operation_id"])
            if command == "cancel":
                return self.cancel(request)
            goal = self.goals.get(request["operation_id"])
            if goal is None:
                raise Refusal("controller operation ID is unknown")
            return self.public_goal(goal)

    def request_shutdown(self, *_):
        self.shutdown.set()
        with self.mutex:
            if self.active_id:
                goal = self.goals[self.active_id]
                if goal["phase"] not in TERMINAL:
                    goal["cancel_requested"] = True
                    goal["cancel_requested_at"] = time.time()
                    self.persist_goal(goal)
                    self.cancel_event.set()

    def abort_unfinished_worker(self):
        # Do not unwind either ownership scope while a live worker can still write.
        # Existing accepted/running intent is already durable if this best-effort update fails.
        acquired = self.mutex.acquire(timeout=.1)
        try:
            if acquired:
                with contextlib.suppress(OSError, Refusal):
                    if self.active_id:
                        goal = self.goals[self.active_id]
                        if goal["phase"] not in TERMINAL:
                            goal.update(phase="unknown", reason="controller shutdown deadline exceeded; result is unresolved",
                                        finished_at=time.time())
                            self.persist_goal(goal)
                    self.incarnation_record.update(phase="unknown", shutdown_timeout_at=time.time(),
                                                   reason="native worker exceeded bounded shutdown; process abort")
                    body.utils.persist(self.control / "controller-current.json", self.incarnation_record)
                    body.utils.persist(self.control / f"incarnation-{self.incarnation}.json", self.incarnation_record)
        finally:
            if acquired:
                self.mutex.release()
            # Whole-process exit ends the worker before the kernel releases the episode/control
            # locks. No stopped claim or socket cleanup is made; restart reconciles exact receipts.
            os._exit(2)

    def serve(self):
        path = socket_path(self.control)
        if path.exists() or path.is_symlink():
            info = path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise Refusal("owned socket path is not an owned Unix socket")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.settimeout(.2)
                try:
                    probe.connect(str(path))
                except (ConnectionRefusedError, FileNotFoundError):
                    path.unlink()
                else:
                    raise Refusal("another live controller occupies the owned socket path")
        prior = {sig: signal.signal(sig, self.request_shutdown) for sig in (signal.SIGTERM, signal.SIGINT)}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(path))
            os.chmod(path, 0o600)
            server.listen(8)
            server.settimeout(.1)
            try:
                while not self.shutdown.is_set():
                    try:
                        connection, _ = server.accept()
                    except TimeoutError:
                        continue
                    with connection:
                        try:
                            reply = self.handle(receive(connection))
                        except (Refusal, OSError, KeyError, ValueError, TypeError) as exc:
                            reply = {"source_kind": body.SOURCE_KIND, "phase": "refused",
                                     "reason": str(exc) if isinstance(exc, Refusal) else
                                     "controller request or bound evidence is invalid or unavailable",
                                     "current_incarnation": self.incarnation}
                        with contextlib.suppress(OSError):
                            connection.sendall(body.encoded(reply).replace(b"\n", b" ") + b"\n")
            finally:
                self.request_shutdown()
                if self.worker:
                    self.worker.join(15)
                    if self.worker.is_alive():
                        self.abort_unfinished_worker()
                path.unlink(missing_ok=True)
                self.incarnation_record.update(phase="stopped", stopped_at=time.time())
                body.utils.persist(self.control / "controller-current.json", self.incarnation_record)
                body.utils.persist(self.control / f"incarnation-{self.incarnation}.json", self.incarnation_record)
                for sig, handler in prior.items():
                    signal.signal(sig, handler)


def client(control, request):
    binding = body.decoded(body.read_bytes(control / "controller-binding.json"))
    path = socket_path(control)
    if binding.get("controller_dir") != str(control) or binding.get("socket_path") != str(path):
        raise Refusal("client controller/socket binding is invalid")
    info = path.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Refusal("controller socket must be owned and private")
    content = json.dumps(request, sort_keys=True, allow_nan=False).encode() + b"\n"
    if len(content) > MAX_RPC:
        raise Refusal("client request exceeds its bounded size")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(str(path))
        connection.sendall(content)
        response = b""
        while b"\n" not in response:
            chunk = connection.recv(4096)
            if not chunk or len(response) + len(chunk) > body.MAX_FILE:
                raise Refusal("controller reply missing or outside its bounded size")
            response += chunk
    return body.decoded(response.split(b"\n", 1)[0])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("serve", "health", "observe", "submit", "status", "cancel"):
        child = commands.add_parser(command)
        child.add_argument("--controller-dir", required=True)
        if command == "serve":
            child.add_argument("--run-dir", required=True)
            child.add_argument("--dispatch-delay-s", type=float, default=0)
            child.add_argument("--pace-s", type=float, default=0)
        if command in {"submit", "status", "cancel"}:
            child.add_argument("--operation-id", required=True)
        if command in {"submit", "cancel"}:
            child.add_argument("--expected-incarnation", required=True)
        if command == "submit":
            child.add_argument("--proposal-file", required=True)
            child.add_argument("--proposal-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        control = body.directory(args.controller_dir, create=args.command == "serve")
        if args.command == "serve":
            root = body.directory(args.run_dir)
            with body.utils.locked(control), body.utils.locked(root):
                Controller(root, control, args.dispatch_delay_s, args.pace_s).serve()
            return 0
        request = {key: value for key, value in vars(args).items() if key != "controller_dir"}
        result = client(control, request)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 2 if result.get("phase") in {"refused", "unknown", "blocked"} else 0
    except (Refusal, OSError, ValueError, TypeError, KeyError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else "controller or its retained binding is unavailable"
        print(json.dumps({"source_kind": body.SOURCE_KIND, "phase": "refused", "reason": reason}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
