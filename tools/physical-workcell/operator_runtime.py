"""Serialized, durable model host for a local simulated bench operator."""
import copy
import threading
import time
import uuid
from pathlib import Path

import agent_bench as agent
import bench
import measurement
import order_protocol as protocol

BASE = Path(__file__).resolve().parent
MAX_CALLS = 32
MAX_TOTAL_CALLS = 96
ZONES = {"A": {"x_min": .035, "x_max": .105, "y_min": -.025, "y_max": .025},
         "B": {"x_min": .045, "x_max": .115, "y_min": -.025, "y_max": .025}}


def sources():
    return {**agent.sources(), **{name: protocol.sha(protocol.read_bytes(BASE / name))
            for name in ("operator_runtime.py", "bench_operator.py", "codex_policy.py", "bench_operator.html",
                         "codex-policy.md", "codex-action.schema.json")}}


def initialize(root):
    root = protocol.directory(root, create=True)
    with protocol.locked(root):
        if any(p.name != "app.lock" for p in root.iterdir()):
            raise protocol.Refusal("operator initialization requires a new empty directory")
        source = sources()
        status = bench.initialize(root / "bench", diagnostic_enabled=True)
        agent.initialize(root / "agent", root / "bench")
        (root / "calls").mkdir(mode=0o700)
        manifest = {"version": 1, "app_id": uuid.uuid4().hex, "bench_id": status["bench_id"],
                    "source_fingerprints": source, "opened": False, "runner_status": "running",
                    "active_job_id": None, "jobs": [], "activity": [], "sequence": 0,
                    "frame": None, "usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "reported_calls": 0},
                    "reason": "Ready for a simulated job"}
        protocol.create_file(root / "identity.json", protocol.encoded(
            {"app_id": manifest["app_id"], "bench_id": manifest["bench_id"], "source_fingerprints": source}))
        protocol.persist(root / "operator.json", manifest)
    return manifest["app_id"]


def validate_job(value):
    protocol.fields(value, ("job_id", "label", "target", "disturbance_test"), "job")
    protocol.identity(value["job_id"])
    if (not isinstance(value["label"], str) or not 1 <= len(value["label"].strip()) <= 120 or
            value["target"] not in ZONES or type(value["disturbance_test"]) is not bool):
        raise protocol.Refusal("job needs a short label, target A or B, and a boolean disturbance flag")
    if value["disturbance_test"] and value["target"] != "B":
        raise protocol.Refusal("the disturbance trial is limited to target B")


class Operator:
    def __init__(self, root, policy, *, start_worker=True):
        self.root = protocol.directory(root)
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.cancel = threading.Event()
        self.closing = False
        self.in_model = False
        self.control_epoch = 0
        self.saved_digest = None
        self.policy = policy
        self.owner = protocol.locked(self.root)
        self.owner.__enter__()
        try:
            self.m = protocol.decode(protocol.read_bytes(self.root / "operator.json"))
            self._identity()
            self.body = bench.Bench(self.root / "bench")
            self.agent = agent.AgentBench(self.root / "agent")
            health_error = None
            try:
                self._healthy()
            except Exception as exc:  # noqa: BLE001 - preserve unknown startup evidence.
                health_error = str(exc)
            if self.m["opened"]:
                self.m["runner_status"] = "paused"
                self.m["reason"] = "Restarted; inspect retained state and explicitly resume"
                for job in self.m["jobs"]:
                    if job["status"] == "running":
                        job["status"] = "paused"
                        job["error"] = "Restarted during an unfinished job; no action replayed"
            if health_error:
                self.m.update(runner_status="blocked", reason=health_error)
                for job in self.m["jobs"]:
                    if job["id"] == self.m["active_job_id"]:
                        job.update(status="unknown", error=health_error)
            self.m["opened"] = True
            if self.m["frame"] is None and not health_error:
                self._cache(self.agent.observe())
            self._save()
            self.worker = threading.Thread(target=self._loop, name="bench-operator", daemon=True)
            if start_worker:
                self.worker.start()
                self.wake.set()
        except Exception:
            self.owner.__exit__(None, None, None)
            raise

    def _identity(self):
        if self.saved_digest and protocol.sha(protocol.read_bytes(self.root / "operator.json")) != self.saved_digest:
            raise protocol.Refusal("retained operator state changed outside its owner")
        identity = protocol.decode(protocol.read_bytes(self.root / "identity.json"))
        if identity != {key: self.m[key] for key in ("app_id", "bench_id", "source_fingerprints")}:
            raise protocol.Refusal("persistent operator identity changed")
        protocol.fields(self.m, ("version", "app_id", "bench_id", "source_fingerprints", "opened",
                        "runner_status", "active_job_id", "jobs", "activity", "sequence", "frame", "usage", "reason"), "operator manifest")
        if (type(self.m["version"]) is not int or self.m["version"] != 1 or
                not isinstance(self.m["app_id"], str) or not protocol.UUID.fullmatch(self.m["app_id"]) or
                self.m["source_fingerprints"] != sources()):
            raise protocol.Refusal("operator identity or measured source changed")
        if not isinstance(self.m["jobs"], list) or len(self.m["jobs"]) > 6:
            raise protocol.Refusal("operator job budget exceeded")

    def _healthy(self, allow_completed=False):
        self._identity()
        state = self.agent.status()
        if state["bench_id"] != self.m["bench_id"] or state["bench"]["state"] != "ready" or state["unresolved_proposals"]:
            raise protocol.Refusal("native or agent outcome is unknown; operator intervention required")
        active = state["bench"]["active_job"]
        expected = self.m["active_job_id"]
        if ((active is not None and active["job_id"] != expected) or
                (expected is not None and active is None and
                 (not allow_completed or expected not in state["bench"]["jobs"]))):
            raise protocol.Refusal("active physical job differs from the operator job")
        for job in self.m["jobs"]:
            if job["status"] == "completed":
                completed = state["bench"]["jobs"].get(job["id"])
                if (not completed or completed["phase"] != "completed" or
                        completed["reset_receipt"].get("block_home_verified") is not True or
                        completed["reset_receipt"].get("pusher_home_verified") is not True or
                        job["measurement"] != agent.public_response(completed["measurement_receipt"]["measurement"])):
                    raise protocol.Refusal("displayed completion lacks retained native and computer proof")
        return state["bench"]

    def _save(self):
        protocol.persist(self.root / "operator.json", self.m)
        self.saved_digest = protocol.sha(protocol.encoded(self.m))

    def _event(self, kind, intent="", outcome=""):
        self.m["sequence"] += 1
        value = {"seq": self.m["sequence"], "time": time.time(), "kind": kind,
                 "intent": str(intent)[:2000], "outcome": str(outcome)[:1000]}
        protocol.create_file(self.root / "calls" / f"event-{value['seq']:06d}.json", protocol.encoded(value))
        self.m["activity"] = (self.m["activity"] + [value])[-24:]
        self._save()

    def _cache(self, challenge):
        packet = challenge["observation"]
        path = Path(challenge["image_path"])
        if path.parent != self.root / "bench" / "images":
            raise protocol.Refusal("camera frame is not bench-owned")
        if protocol.sha(protocol.read_bytes(path, maximum=8 * 1024 * 1024)) != packet["image_sha256"]:
            raise protocol.Refusal("camera frame bytes changed")
        self.m["frame"] = {"path": str(path), "sha256": packet["image_sha256"], "generation": packet["generation"]}

    def state(self):
        with self.lock:
            self._identity()
            try:
                self._healthy()
            except Exception as exc:  # noqa: BLE001 - report changed native evidence as blocked.
                if self.m["runner_status"] != "blocked":
                    self._halt(str(exc), "blocked")
            frame = self.m["frame"]
            jobs = [{("job_id" if key == "id" else key): value for key, value in job.items()
                     if key not in {"history", "disturbed"}} for job in self.m["jobs"]]
            return copy.deepcopy({"app_id": self.m["app_id"], "simulation": True,
                "runner_status": self.m["runner_status"], "jobs": jobs,
                "model_request_pending": self.in_model,
                "active_job_id": self.m["active_job_id"], "activity": self.m["activity"],
                "usage": {**self.m["usage"], "token_usage_complete": self.m["usage"]["reported_calls"] == self.m["usage"]["calls"]}, "readiness": {"ready": self.m["runner_status"] == "running", "reason": self.m["reason"]},
                "current_frame": {"generation": frame["generation"] if frame else None,
                                  "image_url": f"/api/frame?generation={frame['generation']}&sha256={frame['sha256']}" if frame else None,
                                  "available": frame is not None}})

    def frame(self, requested_url=None):
        with self.lock:
            self._identity()
            frame = self.m["frame"]
            if not frame or Path(frame["path"]).parent != self.root / "bench" / "images":
                raise protocol.Refusal("no owned camera frame")
            expected_url = f"/api/frame?generation={frame['generation']}&sha256={frame['sha256']}"
            if requested_url is not None and requested_url != expected_url:
                raise protocol.Refusal("requested capture is no longer the current cached image")
            data = protocol.read_bytes(Path(frame["path"]), maximum=8 * 1024 * 1024)
            if protocol.sha(data) != frame["sha256"]:
                raise protocol.Refusal("cached camera frame changed")
            return data

    def enqueue(self, request):
        validate_job(request)
        with self.lock:
            self._identity()
            if self.closing or len(self.m["jobs"]) >= 6 or any(j["id"] == request["job_id"] for j in self.m["jobs"]):
                raise protocol.Refusal("job identity reused or operator queue budget exhausted")
            self.m["jobs"].append({"id": request["job_id"], "label": request["label"].strip(),
                "target": request["target"], "disturbance_test": request["disturbance_test"],
                "disturbed": False, "status": "queued", "phase": None, "call_count": 0,
                "last_intent": "", "measurement": None, "error": None, "history": []})
            self._event("queued", request["label"], request["job_id"])
            self.wake.set()
            return self.state()

    def pause(self):
        # Set immediately, even if a native action currently owns the action-boundary lock.
        self.cancel.set()
        with self.lock:
            self.control_epoch += 1
            if self.m["runner_status"] != "blocked":
                self.m["runner_status"] = "pausing" if self.in_model else "paused"
                self.m["reason"] = "Paused; an in-flight native action may finish before the next boundary"
            for job in self.m["jobs"]:
                if job["id"] == self.m["active_job_id"] and job["status"] == "running":
                    job["status"] = "paused"
            self._event("pause", outcome=self.m["reason"])
            return self.state()

    def resume(self):
        with self.lock:
            if self.closing or self.cancel.is_set() and self.in_model:
                raise protocol.Refusal("wait for the cancelled model call to exit before resuming")
            try:
                self._healthy()
            except Exception as exc:
                self.m.update(runner_status="blocked", reason=str(exc))
                self._save()
                raise
            self.cancel.clear()
            self.m.update(runner_status="running", reason="Ready for the next action boundary")
            self._event("resume")
            self.wake.set()
            return self.state()

    def close(self):
        self.cancel.set()
        with self.lock:
            self.control_epoch += 1
            self.closing = True
            self.m.update(runner_status="pausing", reason="Stopping; waiting for the owned worker to exit")
            self._save()
            self.wake.set()
        if self.worker.is_alive():
            self.worker.join(timeout=35)
        if self.worker.is_alive():
            raise protocol.Refusal("owned worker has not exited; ownership lock retained")
        with self.lock:
            self.m.update(runner_status="stopped", reason="Operator stopped; retained bench has not been reset")
            self._save()
        self.owner.__exit__(None, None, None)

    def _loop(self):
        while not self.closing:
            self.wake.wait(.5)
            self.wake.clear()
            while not self.closing:
                with self.lock:
                    if self.m["runner_status"] != "running" or self.cancel.is_set():
                        break
                try:
                    if not self._step():
                        break
                except Exception as exc:  # noqa: BLE001 - retain model and native failures.
                    with self.lock:
                        if self.closing:
                            self._event("shutdown_model_exit", outcome=str(exc))
                            break
                        try:
                            self._healthy()
                            state = "paused"
                        except Exception:  # noqa: BLE001 - uncertainty cannot authorize resume.
                            state = "blocked"
                        self._halt(str(exc), state)

    def _halt(self, reason, state="paused"):
        self.m.update(runner_status=state, reason=str(reason))
        job = next((j for j in self.m["jobs"] if j["id"] == self.m["active_job_id"]), None)
        if state == "blocked":
            for previous in self.m["jobs"]:
                if previous["status"] == "completed":
                    previous.update(status="unknown", error="Retained completion evidence could not be validated")
        if job:
            job.update(status="unknown" if state == "blocked" else "paused", error=str(reason))
        self._event("halt", outcome=reason)

    def _step(self):
        with self.lock:
            if self.closing or self.m["runner_status"] != "running" or self.cancel.is_set():
                return False
            self._healthy()
            if self.m["usage"]["calls"] >= MAX_TOTAL_CALLS:
                self._halt("Operator lifetime model-call budget exhausted")
                return False
            job = next((j for j in self.m["jobs"] if j["id"] == self.m["active_job_id"]), None)
            if job is None:
                job = next((j for j in self.m["jobs"] if j["status"] == "queued"), None)
                if job is None:
                    return False
                # Durable start intention precedes changing the native bench.
                self.m["active_job_id"] = job["id"]
                job["status"] = "running"
                self._event("start_intent", job["label"], job["id"])
                self.body.start_job(job["id"], ZONES[job["target"]])
            if job["call_count"] >= MAX_CALLS:
                self._halt("Model call budget exhausted")
                return False
            challenge = agent.public_response(self.agent.observe())
            self._cache(challenge)
            job.update(status="running", phase=challenge["observation"]["phase"], error=None)
            job["call_count"] += 1
            self.m["usage"]["calls"] += 1
            call_dir = self.root / "calls" / f"{job['id']}-{job['call_count']:02d}"
            call_dir.mkdir(mode=0o700)
            protocol.create_file(call_dir / "reservation.json", protocol.encoded({"job_id": job["id"],
                "call": job["call_count"], "challenge": challenge, "history": job["history"][-6:]}))
            self._event("inference", job["label"], f"Model call {job['call_count']} reserved")
            self.in_model = True
            call_epoch = self.control_epoch
        try:
            action, metadata = self.policy(challenge, copy.deepcopy(job["history"][-6:]), call_dir, self.cancel)
            protocol.create_file(call_dir / "decision.json", protocol.encoded({"action": action, "metadata": metadata}))
        finally:
            with self.lock:
                self.in_model = False
        with self.lock:
            usage = metadata.get("usage")
            if isinstance(usage, dict) and all(type(usage.get(key)) is int and usage[key] >= 0 for key in ("input_tokens", "output_tokens")):
                self.m["usage"]["reported_calls"] += 1
            for key in ("input_tokens", "output_tokens"):
                tokens = (metadata.get("usage") or {}).get(key, 0)
                if type(tokens) is int and tokens >= 0:
                    self.m["usage"][key] += tokens
            if (call_epoch != self.control_epoch or self.cancel.is_set() or
                    self.m["runner_status"] != "running" or self.closing):
                if self.m["runner_status"] == "pausing":
                    self.m["runner_status"] = "paused"
                self._event("decision_withheld", outcome="Paused model reply was not dispatched")
                return False
            self._healthy()
            protocol.fields(action, ("action", "target_x", "target_y", "intent"), "model action")
            job["last_intent"] = action["intent"]
            if action["action"] == "stop":
                self._halt(action["intent"])
                return False
            proposal = self.agent.propose(challenge["challenge_id"], action["action"], action["intent"],
                                          action["target_x"], action["target_y"])
            protocol.create_file(call_dir / "proposal.json", protocol.encoded(proposal))
            if job["disturbance_test"] and not job["disturbed"] and action["action"] == "measure":
                job["disturbed"] = True
                self._event("disturbance_intent", outcome="Bounded external-force test before saved proposal dispatch")
                self.body.disturb("disturb-" + uuid.uuid4().hex, -1.5, 80)
            result = agent.public_response(self.agent.dispatch(proposal["proposal_id"]))
            protocol.create_file(call_dir / "dispatch.json", protocol.encoded(result))
            job["history"].append({"action": action, "outcome": result["outcome"], "reason": result.get("reason", "")})
            job["history"] = job["history"][-6:]
            self._event("dispatch", action["intent"], result["outcome"] + ": " + result.get("reason", action["action"]))
            if result["outcome"] == "unknown" or result.get("next_observation") is None:
                self._halt(result.get("reason", "Unknown outcome or observation unavailable"), "blocked")
                return False
            self._cache(result["next_observation"])
            status = self._healthy(allow_completed=action["action"] == "finish_reset" and result["outcome"] == "executed")
            active = status["active_job"]
            if active:
                job["phase"] = active["phase"]
                if "measurement_receipt" in active:
                    job["measurement"] = agent.public_response(active["measurement_receipt"]["measurement"])
            if action["action"] == "finish_reset" and result["outcome"] == "executed":
                completed = status["jobs"].get(job["id"])
                receipt = result.get("receipt", {})
                if (not completed or completed["phase"] != "completed" or active is not None or
                        receipt != completed["reset_receipt"] or receipt.get("job_id") != job["id"] or
                        receipt.get("block_home_verified") is not True or receipt.get("pusher_home_verified") is not True):
                    raise protocol.Refusal("completion is missing independent bench reset evidence")
                saved = measurement.read_result(self.root / "bench", completed["measurement_operation_id"])
                if saved != completed["measurement_receipt"]:
                    raise protocol.Refusal("completion is missing the durable computer measurement")
                job.update(status="completed", phase="completed", measurement=agent.public_response(saved["measurement"]), error=None)
                self.m["active_job_id"] = None
                self._event("completed", job["label"], "Saved measurement and contact reset verified")
            self._save()
            return True
