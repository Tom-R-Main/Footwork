"""Network-only browser host with durable stage application and explicit recovery."""
import copy
import http.client
import threading
import time
import uuid
from pathlib import Path

import body_client
import order_protocol as protocol
import planner_guard
from workbench_link import WorkbenchLink

BASE = Path(__file__).resolve().parent
MAX_CALLS, MAX_TOTAL_CALLS, MAX_COMMANDS = 32, 96, 240
ZONES = {"A": {"x_min": .035, "x_max": .105, "y_min": -.025, "y_max": .025},
         "B": {"x_min": .045, "x_max": .115, "y_min": -.025, "y_max": .025}}


class _ProbePending(Exception):
    """Auxiliary read is unconfirmed; it cannot revoke or grant authority."""


class _BodyUnresolved(protocol.Refusal):
    """A public body read returned known unresolved effects."""


def sources():
    return {name: protocol.sha(protocol.read_bytes(BASE / name)) for name in (
        "network_operator_runtime.py", "network_bench_operator.py", "network_bench_operator.html",
        "workbench_link.py", "body_client.py", "persistent_body_client.py", "body_contract.py", "bench_body_contract.py",
        "body_protocol.py", "order_protocol.py", "codex_policy.py", "planner_guard.py", "codex-policy.md", "codex-action.schema.json")}


def initialize(root, body_origin, link_port=0):
    body_client.endpoint(body_origin)
    root = protocol.directory(root, create=True)
    with protocol.locked(root):
        if any(p.name != "app.lock" for p in root.iterdir()):
            raise protocol.Refusal("network workbench needs a new empty owned directory")
        link = WorkbenchLink(body_origin, root / "link", port=link_port).start()
        client = None
        try:
            client = body_client.BodyClient(root / "client", link.origin)
            pinned = client._load()["identity"]
            (root / "calls").mkdir(mode=0o700)
            (root / "events").mkdir(mode=0o700)
            manifest = {"version": 1, "app_id": uuid.uuid4().hex, "sources": sources(),
                "body_origin": body_origin, "link_origin": link.origin, "link_port": body_client.endpoint(link.origin)[1],
                "body_identity": pinned, "opened": False, "runner_status": "running", "active_job_id": None,
                "jobs": [], "stage": None, "applied_commands": [], "frame": None, "activity": [], "sequence": 0,
                "usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "reported_calls": 0},
                "connection": {"state": "connected", "body_id": pinned["body_id"], "adapter_id": pinned["adapter_id"],
                               "epoch": pinned["epoch"], "reason": "Pinned network body", "fault": None},
                "recovery": {"state": "none", "command_id": None, "operation": None, "reason": "No uncertain command"},
                "reason": "Ready for a network inspection"}
            protocol.create_file(root / "identity.json", protocol.encoded(
                {"app_id": manifest["app_id"], "sources": manifest["sources"], "body_identity": pinned}))
            protocol.persist(root / "operator.json", manifest)
            return manifest["app_id"]
        finally:
            if client:
                client.close()
            link.close()


class Operator:
    def __init__(self, root, policy, start_worker=True):
        self.root = protocol.directory(root)
        self.lock = threading.RLock()
        self.wake, self.cancel = threading.Event(), threading.Event()
        self.closing = self.in_model = self.transport_pending = False
        self.control_epoch = 0
        self.transport_epoch = 0
        self.saved_digest = None
        self.health_stop = threading.Event()
        self.health_serial = threading.Lock()
        self.body_ready = False
        self.policy = policy
        self.planner_owner = uuid.uuid4().hex
        self.owner = protocol.locked(self.root)
        self.owner.__enter__()
        self.link = self.client = None
        try:
            self.m = body_client.read_journal(self.root / "operator.json")
            self._identity()
            recovered_tail = self._recover_events()
            abandoned = self._recover_planners()
            self.link = WorkbenchLink(self.m["body_origin"], self.root / "link", port=self.m["link_port"]).start()
            if self.link.origin != self.m["link_origin"]:
                raise protocol.Refusal("retained network link origin changed")
            self.client = body_client.BodyClient(self.root / "client", self.link.origin, timeout=15)
            self._client_pin()
            if self.m["opened"]:
                self.m.update(runner_status="paused", reason="Restarted; inspect the retained stage before explicit Resume")
                active = self._job()
                if active and active["status"] == "running":
                    active.update(status="paused", error=self.m["reason"])
            self.m["opened"] = True
            self.m["planner_owner"] = self.planner_owner
            if self.m["stage"]:
                self._associate()
                self._uncertain("Restarted with a retained command stage; check its exact receipt")
            elif self._journal()["pending_command_ids"]:
                self._halt("Client has an unknown command without a host stage", blocked=True)
            if not self.link.state()["connected"]:
                self.m["connection"]["state"] = "disconnected"
                self.m["runner_status"] = "paused"
            self._save()
            if recovered_tail:
                self._event("journal_recovered", outcome=f"Retained {recovered_tail} audit event(s); no command replayed")
            if abandoned:
                self.m["reason"] = "Prior planner retired; explicit Resume obtains a fresh image"
                active = self._job()
                if active and active["status"] == "paused":
                    active["error"] = self.m["reason"]
                self._event("planner_retired", outcome=self.m["reason"], evidence={"calls": abandoned})
            self._refresh_health()
            self.health_worker = threading.Thread(target=self._health_loop, daemon=True, name="network-health")
            self.health_worker.start()
            self.worker = threading.Thread(target=self._loop, daemon=True, name="network-workbench")
            if start_worker:
                self.worker.start()
                self.wake.set()
        except Exception:
            if self.client:
                self.client.close()
            if self.link:
                self.link.close()
            self.owner.__exit__(None, None, None)
            raise

    def _identity(self):
        if self.saved_digest and protocol.sha(protocol.read_bytes(self.root / "operator.json", maximum=body_client.MAX_CLIENT_JOURNAL)) != self.saved_digest:
            raise protocol.Refusal("retained host state changed outside its owner")
        identity = protocol.decode(protocol.read_bytes(self.root / "identity.json"))
        if (type(self.m.get("version")) is not int or self.m["version"] != 1 or self.m["sources"] != sources() or
                identity != {k: self.m[k] for k in ("app_id", "sources", "body_identity")}):
            raise protocol.Refusal("workbench source or identity changed")
        if len(self.m["jobs"]) > 6 or len(self.m["applied_commands"]) > 256:
            raise protocol.Refusal("workbench journal capacity exceeded")

    def _journal(self):
        return body_client.read_journal(self.root / "client" / "client.json")

    def _recover_events(self):
        """Repair an audit index, never reconstruct effects from event text."""
        indexed = self.m["sequence"]
        if type(indexed) is not int or not 0 <= indexed <= 4096:
            raise protocol.Refusal("invalid workbench event sequence")
        directory = protocol.directory(self.root / "events")
        files = sorted(directory.iterdir())
        if len(files) > 4096 or indexed > len(files):
            raise protocol.Refusal("workbench event journal is incomplete or exceeds its bound")
        events = []
        for seq, path in enumerate(files, 1):
            if path.name != f"{seq:06d}.json":
                raise protocol.Refusal("workbench event sequence is not contiguous")
            value = protocol.decode(protocol.read_bytes(path))
            keys = {"seq", "time", "kind", "intent", "outcome"}
            if not isinstance(value, dict) or set(value) not in (keys, keys | {"evidence"}):
                raise protocol.Refusal("workbench event fields are invalid")
            if (type(value["seq"]) is not int or value["seq"] != seq or
                    not isinstance(value["kind"], str) or not 1 <= len(value["kind"]) <= 128 or
                    any(not isinstance(value[k], str) or len(value[k]) > 1000 for k in ("intent", "outcome"))):
                raise protocol.Refusal("workbench event identity is invalid")
            protocol.finite(value["time"])
            events.append(value)
        if self.m["activity"] != events[max(0, indexed - 24):indexed]:
            raise protocol.Refusal("workbench activity differs from its immutable event journal")
        self.m["sequence"] = len(events)
        self.m["activity"] = events[-24:]
        return len(events) - indexed

    def _recover_planners(self):
        """Consume reservations as budget, not authority, and wait for cleanup."""
        abandoned = []
        calls = protocol.directory(self.root / "calls")
        entries = sorted(calls.iterdir())
        if len(entries) > MAX_TOTAL_CALLS:
            raise protocol.Refusal("planner reservation budget exceeded")
        counts = {}
        for path in entries:
            path = protocol.directory(path)
            reservation = protocol.decode(protocol.read_bytes(path / "reservation.json"))
            keys = {"job_id", "call", "challenge", "history"}
            if not isinstance(reservation, dict) or set(reservation) not in (keys, keys | {"planner_owner"}):
                raise protocol.Refusal("planner reservation fields are invalid")
            job = self._job(reservation.get("job_id"))
            count = reservation.get("call")
            if job is None or type(count) is not int or not 1 <= count <= MAX_CALLS or path.name != f"{job['id']}-{count:02d}":
                raise protocol.Refusal("planner reservation identity is invalid")
            counts.setdefault(job["id"], set()).add(count)
            closure = planner_guard.recover(path)
            if closure and not (path / "outcome.json").exists():
                abandoned.append({"call": path.name, "reason": closure["reason"]})
        for job in self.m["jobs"]:
            reserved = counts.get(job["id"], set())
            maximum = max(reserved, default=0)
            if reserved != set(range(1, maximum + 1)) or job["call_count"] > maximum:
                raise protocol.Refusal("planner reservation sequence is inconsistent")
            self.m["usage"]["calls"] += maximum - job["call_count"]
            job["call_count"] = maximum
        if self.m["usage"]["calls"] > MAX_TOTAL_CALLS:
            raise protocol.Refusal("retained planner budget exceeded")
        return abandoned

    def _client_pin(self):
        current = self.client._load()["identity"]
        if any(current[k] != self.m["body_identity"][k] for k in body_client.IDENTITY_KEYS - {"epoch"}):
            raise protocol.Refusal("body or adapter identity changed")
        return current

    def _save(self):
        if len(protocol.encoded(self.m)) > body_client.MAX_CLIENT_JOURNAL:
            raise protocol.Refusal("local workbench journal exceeds its 128 KiB bound")
        protocol.persist(self.root / "operator.json", self.m)
        self.saved_digest = protocol.sha(protocol.encoded(self.m))

    def _event(self, kind, intent="", outcome="", evidence=None):
        if self.m["sequence"] >= 4096:
            raise protocol.Refusal("workbench event journal capacity exhausted")
        self.m["sequence"] += 1
        value = {"seq": self.m["sequence"], "time": time.time(), "kind": kind,
                 "intent": str(intent)[:1000], "outcome": str(outcome)[:1000]}
        if evidence is not None:
            value["evidence"] = evidence
        protocol.create_file(self.root / "events" / f"{value['seq']:06d}.json", protocol.encoded(value))
        self.m["activity"] = (self.m["activity"] + [value])[-24:]
        self._save()

    def _health_loop(self):
        while not self.health_stop.wait(1):
            with self.lock:
                skip = self.closing or self.transport_pending or not self.link.state()["connected"]
            if not skip:
                self._refresh_health()

    def _refresh_health(self):
        with self.health_serial:
            with self.lock:
                if self.closing or self.transport_pending or not self.link.state()["connected"]:
                    return False
                control_epoch = self.control_epoch
                transport_epoch = self.transport_epoch
                pinned = dict(self.m["body_identity"])
                pinned["epoch"] = self.m["connection"]["epoch"]
            remote_identity = pinned
            try:
                status, content = self._probe_read("/identity", {})
                if status != 200:
                    raise protocol.Refusal("pinned body identity could not be verified")
                remote_identity = body_client.identity(protocol.decode(content))
                if any(remote_identity[k] != pinned[k] for k in body_client.IDENTITY_KEYS - {"epoch"}):
                    raise protocol.Refusal("pinned body or adapter identity changed")
                status, content = self._probe_read("/state", body_client.pinned_headers(pinned))
                remote = protocol.decode(content)
                if status != 200 or remote["identity"] != remote_identity:
                    raise protocol.Refusal("pinned body state could not be verified")
                ready = remote.get("state") == "ready"
                error = None if ready else "Independent body has unresolved effects"
                connection = "connected"
                blocked = not ready
            except (TimeoutError, _ProbePending):
                ready, error, connection, blocked = False, "Health read delayed; fresh body proof is required before any command", "checking", False
            except protocol.Refusal as exc:
                ready, error, connection, blocked = False, str(exc), "unavailable", True
            except (OSError, http.client.HTTPException, ValueError, KeyError) as exc:
                ready, error, connection, blocked = False, str(exc), "unavailable", False
                remote_identity = pinned
            with self.lock:
                if (self.closing or self.transport_pending or control_epoch != self.control_epoch or
                        transport_epoch != self.transport_epoch or not self.link.state()["connected"]):
                    return False
                if connection in {"connected", "checking"} and remote_identity["epoch"] != self.m["connection"]["epoch"]:
                    self._body_epoch_changed(remote_identity["epoch"], ready, known_unknown=blocked)
                    if connection == "checking":
                        self.m["connection"].update(state="checking", reason=error)
                        self._save()
                    return ready
                old = self.m["connection"]["state"]
                self.body_ready = ready
                self.m["connection"].update(state=connection, reason=error or "Body identity verified by read-only TCP health", epoch=remote_identity["epoch"])
                if not ready and connection != "checking" and (old != connection or self.m["runner_status"] == "running"):
                    self.cancel.set()
                    self.control_epoch += 1
                    self._halt(error, blocked=blocked)
                self._save()
                return ready

    def _probe_read(self, path, headers):
        status, content = body_client.http_call(self.link.origin, "GET", path,
            {**headers, "X-Footwork-Health-Probe": "1"}, timeout=.8)
        if status == 504:
            pending = protocol.decode(content)
            if (isinstance(pending, dict) and type(pending.get("version")) is int and
                    pending == {"version": 1, "kind": "health_read_pending", "path": path}):
                raise _ProbePending()
            raise protocol.Refusal("health gateway returned an unverified pending response")
        return status, content

    def _retain(self, path, value):
        content = protocol.encoded(value)
        if path.exists():
            if protocol.read_bytes(path) != content:
                raise protocol.Refusal("retained host evidence differs from its exact result")
        else:
            protocol.create_file(path, content)

    def _job(self, job_id=None):
        return next((j for j in self.m["jobs"] if j["id"] == (job_id or self.m["active_job_id"])), None)

    def _halt(self, reason, blocked=False):
        self.m.update(runner_status="blocked" if blocked else "paused", reason=str(reason))
        job = self._job()
        if job and job["status"] != "completed":
            job.update(status="unknown" if blocked else "paused", error=str(reason))
        self._event("halt", outcome=reason)

    def _body_epoch_changed(self, epoch, ready, known_unknown=False):
        previous = self.m["connection"]["epoch"]
        reason = f"Body restarted from boot {previous} to {epoch}; check pending receipts and explicitly Resume for a fresh image"
        self.body_ready = ready
        self.m["connection"].update(state="connected", epoch=epoch, reason=reason)
        self.cancel.set()
        if self.m["stage"]:
            self._uncertain(reason)
        else:
            self.control_epoch += 1
            self._halt(reason, blocked=known_unknown)
        self._event("body_epoch_changed", outcome=f"{previous} -> {epoch}")

    def _uncertain(self, reason):
        stage = self.m["stage"]
        self.m["recovery"] = {"state": "uncertain" if stage and stage.get("command_id") else "blocked",
            "command_id": stage.get("command_id") if stage else None,
            "operation": stage["operation"] if stage else None, "reason": str(reason)}
        self.control_epoch += 1
        self._halt(reason, blocked=True)

    def _cache(self, challenge):
        packet = challenge["observation"]
        path = Path(challenge["image_path"])
        if (path.parent != self.root / "client" / "images" or packet["bench_id"] != self.m["body_identity"]["body_id"] or
                protocol.sha(protocol.read_bytes(path, maximum=body_client.MAX_IMAGE)) != packet["image_sha256"]):
            raise protocol.Refusal("camera frame is not an exact downloaded body image")
        self.m["frame"] = {"path": str(path), "sha256": packet["image_sha256"], "generation": packet["generation"]}

    def state(self):
        with self.lock:
            self._identity()
            frame = self.m["frame"]
            jobs = [{("job_id" if k == "id" else k): v for k, v in j.items() if k not in {"history", "disturbed"}}
                    for j in self.m["jobs"]]
            connection = dict(self.m["connection"])
            connection["fault"] = self.link.state()["fault"]
            stage = self.m["stage"]
            return copy.deepcopy({"app_id": self.m["app_id"], "simulation": True, "runner_status": self.m["runner_status"],
                "jobs": jobs, "active_job_id": self.m["active_job_id"], "model_request_pending": self.in_model,
                "transport_pending": self.transport_pending, "pending_operation": stage["operation"] if stage else None,
                "activity": self.m["activity"], "usage": {**self.m["usage"],
                    "token_usage_complete": self.m["usage"]["reported_calls"] == self.m["usage"]["calls"]},
                "readiness": {"ready": self.m["runner_status"] == "running" and connection["state"] == "connected", "reason": self.m["reason"]},
                "current_frame": {"available": frame is not None, "generation": frame["generation"] if frame else None,
                    "image_url": f"/api/frame?generation={frame['generation']}&sha256={frame['sha256']}" if frame else None},
                "connection": connection, "recovery": self.m["recovery"]})

    def frame(self, requested_url=None):
        with self.lock:
            self._identity()
            frame = self.m["frame"]
            if not frame or Path(frame["path"]).parent != self.root / "client" / "images":
                raise protocol.Refusal("no retained downloaded frame")
            url = f"/api/frame?generation={frame['generation']}&sha256={frame['sha256']}"
            if requested_url is not None and requested_url != url:
                raise protocol.Refusal("cached capture identity changed")
            content = protocol.read_bytes(Path(frame["path"]), maximum=body_client.MAX_IMAGE)
            if protocol.sha(content) != frame["sha256"]:
                raise protocol.Refusal("cached downloaded image changed")
            return content

    def enqueue(self, request):
        protocol.fields(request, ("job_id", "label", "target", "disturbance_test"), "inspection")
        protocol.identity(request["job_id"])
        if (not isinstance(request["label"], str) or not 1 <= len(request["label"].strip()) <= 120 or
                request["target"] not in ZONES or type(request["disturbance_test"]) is not bool or
                request["disturbance_test"] and request["target"] != "B"):
            raise protocol.Refusal("inspection needs a label, region A or B, and a bounded recovery test")
        with self.lock:
            self._identity()
            if self.closing or len(self.m["jobs"]) >= 6 or self._job(request["job_id"]):
                raise protocol.Refusal("inspection identity reused or queue capacity exhausted")
            self.m["jobs"].append({"id": request["job_id"], "label": request["label"].strip(), "target": request["target"],
                "disturbance_test": request["disturbance_test"], "disturbed": False, "status": "queued", "phase": None,
                "call_count": 0, "last_intent": "", "measurement": None, "reset": None, "error": None, "history": []})
            self._event("queued", request["label"], request["job_id"])
            self.wake.set()
            return self.state()

    def pause(self):
        self.cancel.set()
        with self.lock:
            self.control_epoch += 1
            if self.m["runner_status"] != "blocked":
                self.m["runner_status"] = "pausing" if self.in_model or self.transport_pending else "paused"
            self.m["reason"] = "Pause requested; a command already admitted by this host may finish within body bounds"
            self._event("pause", outcome=self.m["reason"])
            return self.state()

    def disconnect(self):
        self.cancel.set()
        self.link.set_connected(False)
        with self.lock:
            self.control_epoch += 1
            self.m["connection"].update(state="disconnected", reason="Diagnostic link disconnected; cached observations are retained")
            if self.m["runner_status"] != "blocked":
                self.m["runner_status"] = "paused"
            self._event("disconnect", outcome="Transport only; no body reset or replay")
            return self.state()

    def reconnect(self):
        with self.lock:
            if self.closing:
                raise protocol.Refusal("workbench is stopping")
            self._identity()
            self.control_epoch += 1
            self.cancel.set()
            self.link.set_connected(True)
            self.m["connection"].update(state="unavailable", reason="Checking the reconnected body identity")
            if self.m["runner_status"] != "blocked":
                self.m["runner_status"] = "paused"
            self._event("reconnect", outcome="No command sent or replayed")
        self._refresh_health()
        return self.state()

    def fault(self, request):
        protocol.fields(request, ("mode", "delay_s"), "diagnostic fault")
        delay = protocol.finite(request["delay_s"])
        if request["mode"] not in {"drop_after", "delay_after", "duplicate"} or not 0 <= delay <= 2:
            raise protocol.Refusal("unsupported bounded transport fault")
        with self.lock:
            self._identity()
            self.link.arm(request["mode"], operation="dispatch", delay_s=delay)
            self._event("fault_armed", outcome=request["mode"])
            return self.state()

    def _associate(self):
        stage = self.m["stage"]
        if not stage:
            return None
        journal = self.client._load()
        new = set(journal["commands"]) - set(stage["before_commands"])
        if len(new) != 1:
            return None
        token = next(iter(new))
        request, _ = self.client._request(journal, token)
        if (request["operation"] != stage["operation"] or request["arguments"] != stage["arguments"] or
                stage.get("command_id") not in (None, token)):
            raise protocol.Refusal("pending host stage disagrees with its unique client command")
        stage["command_id"] = token
        self._save()
        return token

    def _local_envelope(self, token):
        journal = self.client._load()
        record = journal["commands"][token]
        if "response_sha256" not in record:
            return None
        request, _ = self.client._request(journal, token)
        content = protocol.read_bytes(self.root / "client" / "responses" / (token + "-" + record["response_sha256"] + ".json"))
        return self.client._envelope(journal, request, content)

    def _rpc(self, operation, arguments, context):
        with self.lock:
            self._identity()
            if (self.closing or self.cancel.is_set() or self.m["runner_status"] != "running" or
                    self.m["connection"]["state"] not in {"connected", "checking"} or self.m["stage"] or
                    context.get("decision_epoch", self.control_epoch) != self.control_epoch):
                return None
            journal = self.client._load()
            if journal["pending_command_ids"]:
                self._halt("An unknown client command blocks fresh admission", blocked=True)
                return None
            if len(journal["commands"]) >= MAX_COMMANDS:
                self._halt("Conservative network-command budget exhausted")
                return None
            epoch = self.control_epoch
            known_body_epoch = self.m["connection"]["epoch"]
            self.transport_pending = True
            self.transport_epoch += 1
        try:
            _, verified, proof = self._public_status(include_proof=True)
            with self.lock:
                if epoch != self.control_epoch or self.cancel.is_set() or self.closing:
                    return None
                if verified["epoch"] != known_body_epoch:
                    self._body_epoch_changed(verified["epoch"], ready=True)
                    return None
                self.body_ready = True
                self.m["connection"].update(state="connected", reason="Fresh pinned ready proof verified before command admission")
                self._event("admission_proof", outcome=operation, evidence=proof)
            self.client.acquire(30)
            with self.lock:
                if epoch != self.control_epoch or self.cancel.is_set() or self.closing:
                    return None
                journal = self.client._load()
                if journal["identity"]["epoch"] != known_body_epoch:
                    self._body_epoch_changed(journal["identity"]["epoch"], ready=False)
                    return None
                self.m["connection"]["epoch"] = journal["identity"]["epoch"]
                self.m["stage"] = {"operation": operation, "arguments": arguments, "context": context,
                    "before_commands": list(journal["commands"]), "command_id": None, "control_epoch": epoch, "proof": proof}
                self._event("rpc_intent", outcome=operation)
            if operation == "start_job":
                result = self.client.start_job(arguments["job_id"], arguments["target_zone"])
            else:
                result = getattr(self.client, operation)(**arguments)
            with self.lock:
                token = self._associate()
                if token is None:
                    raise protocol.Refusal("RPC result has no uniquely indexed client command")
                envelope = self._local_envelope(token)
            self._apply(envelope, result)
            return result
        except body_client.Uncertain as exc:
            with self.lock:
                self._associate()
                self._uncertain(str(exc))
            return None
        except Exception as exc:  # noqa: BLE001 - preserve possibly accepted command stages.
            with self.lock:
                if self.m["stage"]:
                    token = self._associate()
                    envelope = self._local_envelope(token) if token else None
                    if envelope and envelope["state"] in {"refused", "not_accepted"}:
                        self._apply(envelope, None)
                    else:
                        self._uncertain(str(exc))
                else:
                    self.m["connection"].update(state="unavailable", reason=str(exc))
                    self.body_ready = False
                    self.cancel.set()
                    self.control_epoch += 1
                    self._halt(str(exc), blocked=isinstance(exc, _BodyUnresolved))
            return None
        finally:
            with self.lock:
                self.transport_pending = False
                if self.m["runner_status"] == "pausing":
                    self.m["runner_status"] = "paused"
                self._save()

    def _public_status(self, include_identity=False, include_proof=False):
        status = self.client.status()
        remote = status["server_state"]
        if remote.get("state") == "unknown":
            raise _BodyUnresolved("Independent body has unresolved effects; fresh commands are blocked")
        if remote.get("state") != "ready":
            raise protocol.Refusal("public network body state is unavailable or unresolved")
        pinned = self.m["body_identity"]
        if any(remote["identity"][k] != pinned[k] for k in body_client.IDENTITY_KEYS - {"epoch"}):
            raise protocol.Refusal("network status belongs to another pinned body")
        if include_proof:
            proof = {k: remote["identity"][k] for k in ("body_id", "adapter_id", "source_sha256", "epoch")}
            proof["state_sha256"] = protocol.sha(protocol.encoded(remote))
            return remote["bench"], remote["identity"], proof
        return (remote["bench"], remote["identity"]) if include_identity else remote["bench"]

    def _apply(self, envelope, result):
        with self.lock:
            stage = copy.deepcopy(self.m["stage"])
            if not stage or not envelope or stage["command_id"] != envelope["command_id"]:
                raise protocol.Refusal("exact host stage is missing for receipt application")
            token = stage["command_id"]
            if token in self.m["applied_commands"]:
                raise protocol.Refusal("host stage was already applied")
            context, operation = stage["context"], stage["operation"]
            original_job = self._job(context["job_id"])
            if original_job is None:
                raise protocol.Refusal("stage inspection identity is not owned by this queue")
            job = copy.deepcopy(original_job)
        # The only independent effect readback is the pinned public TCP status.
        public = self._public_status() if operation == "dispatch" and context["action"]["action"] in {"measure", "finish_reset"} and envelope["state"] == "completed" else None
        with self.lock:
            if self.m["stage"] != stage:
                raise protocol.Refusal("host stage changed while reading its proof")
            if envelope["state"] in {"refused", "not_accepted"}:
                if operation == "start_job":
                    self.m["active_job_id"] = None
                    job["status"] = "queued"
                self.m["applied_commands"].append(token)
                self.m["stage"] = None
                self._halt(envelope["reason"] or "Pinned command refused")
                return
            if envelope["state"] != "completed" or not isinstance(result, dict):
                raise protocol.Refusal("receipt is not a known completed RPC")
            if operation == "start_job":
                active = result.get("active_job")
                if result.get("bench_id") != self.m["body_identity"]["body_id"] or not active or active["job_id"] != job["id"]:
                    raise protocol.Refusal("started network job differs from requested inspection")
                self.m["active_job_id"] = job["id"]
                job.update(status="running", phase=active["phase"])
            elif operation == "observe":
                if result["observation"]["job_id"] != job["id"]:
                    raise protocol.Refusal("image is not bound to the active inspection")
                self._cache(result)
                job["phase"] = result["observation"]["phase"]
            elif operation == "propose":
                self._retain(Path(context["call_dir"]) / "proposal.json", result)
            elif operation == "disturb":
                if result.get("operation_id") != stage["arguments"]["operation_id"] or result.get("bench_id") != self.m["body_identity"]["body_id"]:
                    raise protocol.Refusal("disturbance receipt identity changed")
                job["disturbed"] = True
            else:
                self._apply_dispatch(job, stage, result, public)
            original_job.update(job)
            self.m["applied_commands"].append(token)
            self.m["stage"] = None
            self._event("rpc_applied", job["label"], operation + ": " + token)

    def _apply_dispatch(self, job, stage, result, public):
        context = stage["context"]
        action = context["action"]
        if result.get("proposal_id") != stage["arguments"]["proposal_id"] or result.get("outcome") not in {"executed", "refused"}:
            raise protocol.Refusal("dispatch lacks a known exact proposal outcome")
        self._retain(Path(context["call_dir"]) / "dispatch.json", result)
        job["history"] = (job["history"] + [{"action": action, "outcome": result["outcome"], "reason": result.get("reason", "")}])[-6:]
        job["last_intent"] = action["intent"]
        if result["outcome"] == "refused":
            return
        receipt = result.get("receipt", {})
        if receipt.get("bench_id") != self.m["body_identity"]["body_id"]:
            raise protocol.Refusal("effect receipt belongs to another body")
        name = action["action"]
        if name == "begin_reset":
            active = receipt.get("active_job")
            if not active or active["job_id"] != job["id"] or active["phase"] != "resetting":
                raise protocol.Refusal("reset-start proof differs from inspection")
            job["phase"] = "resetting"
        elif name == "measure":
            active = public["active_job"]
            saved = receipt.get("measurement_receipt")
            if not active or active["job_id"] != job["id"] or saved != active.get("measurement_receipt") or active["phase"] != "measured":
                raise protocol.Refusal("public body readback lacks the saved computer measurement")
            job.update(phase="measured", measurement=saved["measurement"])
        elif name == "finish_reset":
            completed = public["jobs"].get(job["id"])
            if (not completed or public["active_job"] is not None or completed["phase"] != "completed" or
                    completed["reset_receipt"] != receipt or receipt.get("job_id") != job["id"] or
                    receipt.get("block_home_verified") is not True or receipt.get("pusher_home_verified") is not True or
                    type(receipt.get("reset_contact_samples")) is not int or receipt["reset_contact_samples"] <= 0 or
                    type(receipt.get("reset_native_steps")) is not int or receipt["reset_native_steps"] <= 0 or
                    completed["measurement_receipt"]["bench_id"] != self.m["body_identity"]["body_id"]):
                raise protocol.Refusal("completion lacks public measurement and verified contact-reset proof")
            job.update(status="completed", phase="completed", measurement=completed["measurement_receipt"]["measurement"], reset=receipt, error=None)
            self.m["active_job_id"] = None

    def reconcile(self):
        with self.lock:
            self._identity()
            if self.transport_pending or self.in_model or self.m["connection"]["state"] not in {"connected", "checking"}:
                raise protocol.Refusal("reconnect and wait for owned work before checking its receipt")
            token = self._associate() if self.m["stage"] else None
            if not token:
                raise protocol.Refusal("no uniquely indexed pending host stage can be reconciled safely")
            stage = copy.deepcopy(self.m["stage"])
            self.transport_pending = True
            self.transport_epoch += 1
        try:
            envelope = self.client.reconcile(token)
            context = stage["context"]
            if context.get("call_dir"):
                self._retain(Path(context["call_dir"]) / "reconciliation.json", envelope)
            self._apply(envelope, envelope["result"])
            with self.lock:
                self.m.update(runner_status="paused", reason="Exact historical stage recovered; explicit Resume observes fresh evidence")
                active = self._job()
                if active and active["status"] != "completed":
                    active.update(status="paused", error=None)
                self.m["recovery"] = {"state": "recovered", "command_id": token, "operation": stage["operation"], "reason": self.m["reason"]}
                self._event("reconciled", outcome=token)
        except Exception as exc:  # Untrusted/missing receipt cannot settle effects.
            with self.lock:
                self._uncertain(str(exc))
            raise
        finally:
            with self.lock:
                self.transport_pending = False
        return self.state()

    def resume(self):
        with self.lock:
            self._identity()
            if self.closing or self.in_model or self.transport_pending or self.m["stage"] or self._journal()["pending_command_ids"]:
                raise protocol.Refusal("settle the exact pending stage and wait for owned work before Resume")
            if self.m["connection"]["state"] not in {"connected", "checking"}:
                raise protocol.Refusal("reconnect the pinned link before Resume")
            self.transport_pending = True
            self.transport_epoch += 1
            resume_epoch = self.control_epoch
        try:
            _, remote_identity = self._public_status(include_identity=True)
            with self.lock:
                if (resume_epoch != self.control_epoch or self.closing or
                        self.m["connection"]["state"] not in {"connected", "checking"}):
                    raise protocol.Refusal("control changed while Resume was reading body status")
                self.control_epoch += 1
                self.cancel.clear()
                self.body_ready = True
                self.m["connection"].update(state="connected", epoch=remote_identity["epoch"], reason="Current body boot verified for explicit Resume")
                self.m.update(runner_status="running", reason="Resumed; next decision receives a fresh TCP image")
                self.m["recovery"] = {"state": "none", "command_id": None, "operation": None, "reason": "No pending command"}
                self._event("resume")
                self.wake.set()
        finally:
            with self.lock:
                self.transport_pending = False
                if self.m["runner_status"] == "pausing":
                    self.m["runner_status"] = "paused"
                    self._save()
        return self.state()

    def close(self):
        self.cancel.set()
        self.health_stop.set()
        with self.lock:
            self.control_epoch += 1
            self.closing = True
            self.m.update(runner_status="pausing", reason="Waiting for owned model/transport work to exit")
            self._save()
            self.wake.set()
        if self.worker.is_alive():
            self.worker.join(35)
        if self.worker.is_alive() or self.transport_pending:
            raise protocol.Refusal("owned network worker has not exited; ownership retained")
        with self.lock:
            self.m.update(runner_status="stopped", reason="Stopped; independent network body retained")
            self._save()
        self.health_worker.join(4)
        if self.health_worker.is_alive():
            raise protocol.Refusal("owned health request has not exited")
        self.client.close()
        self.link.close()
        self.owner.__exit__(None, None, None)

    def _loop(self):
        while not self.closing:
            self.wake.wait(.5)
            self.wake.clear()
            while not self.closing:
                try:
                    if not self._step():
                        break
                except Exception as exc:  # noqa: BLE001 - model availability is not task success.
                    with self.lock:
                        if not self.closing:
                            if self.m["stage"]:
                                self._uncertain(str(exc))
                            else:
                                self._halt(str(exc))
                        else:
                            self._event("shutdown_work_exit", outcome=exc)
                    break

    def _step(self):
        with self.lock:
            self._identity()
            if self.closing or self.cancel.is_set() or self.m["runner_status"] != "running" or self.m["stage"]:
                return False
            if self.m["usage"]["calls"] >= MAX_TOTAL_CALLS:
                self._halt("Lifetime model-call budget exhausted")
                return False
            job = self._job() or next((j for j in self.m["jobs"] if j["status"] == "queued"), None)
            if not job:
                return False
            if job["call_count"] >= MAX_CALLS:
                self._halt("Inspection model-call budget exhausted")
                return False
            job_id = job["id"]
        if (self.m["active_job_id"] is None and
                self._rpc("start_job", {"job_id": job_id, "target_zone": ZONES[job["target"]]}, {"job_id": job_id}) is None):
            return False
        challenge = self._rpc("observe", {}, {"job_id": job_id})
        if challenge is None:
            return False
        with self.lock:
            if self.cancel.is_set() or self.m["runner_status"] != "running":
                return False
            job.update(status="running", phase=challenge["observation"]["phase"], error=None)
            job["call_count"] += 1
            self.m["usage"]["calls"] += 1
            call_dir = self.root / "calls" / f"{job_id}-{job['call_count']:02d}"
            call_dir.mkdir(mode=0o700)
            self._retain(call_dir / "reservation.json", {"job_id": job_id, "call": job["call_count"], "challenge": challenge,
                "history": job["history"][-6:], "planner_owner": self.planner_owner})
            call_epoch = self.control_epoch
            self.in_model = True
            self._event("inference", job["label"], str(job["call_count"]))
        try:
            action, metadata = self.policy(challenge, copy.deepcopy(job["history"][-6:]), call_dir, self.cancel)
            with self.lock:
                self._identity()
                if self.m.get("planner_owner") != self.planner_owner:
                    raise protocol.Refusal("planner owner changed before decision publication")
                self._retain(call_dir / "decision.json", {"action": action, "metadata": metadata})
        finally:
            with self.lock:
                self.in_model = False
                if self.m["runner_status"] == "pausing":
                    self.m["runner_status"] = "paused"
        with self.lock:
            usage = metadata.get("usage") or {}
            if all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")):
                self.m["usage"]["reported_calls"] += 1
                for key in ("input_tokens", "output_tokens"):
                    self.m["usage"][key] += usage[key]
            if call_epoch != self.control_epoch or self.cancel.is_set() or self.m["runner_status"] != "running":
                self._event("decision_withheld", outcome="Control changed before model result dispatch")
                return False
            protocol.fields(action, ("action", "target_x", "target_y", "intent"), "model action")
            job["last_intent"] = action["intent"]
            if action["action"] == "stop":
                self._halt(action["intent"])
                return False
            context = {"job_id": job_id, "call_dir": str(call_dir), "action": action, "decision_epoch": call_epoch}
        proposal = self._rpc("propose", {"challenge_id": challenge["challenge_id"], **action}, context)
        if proposal is None:
            return False
        if (job["disturbance_test"] and not job["disturbed"] and action["action"] == "measure" and
                self._rpc("disturb", {"operation_id": "disturb-" + uuid.uuid4().hex, "force_x_n": -1.5, "steps": 80}, context) is None):
            return False
        result = self._rpc("dispatch", {"proposal_id": proposal["proposal_id"]}, context)
        return result is not None and self.m["runner_status"] == "running"
