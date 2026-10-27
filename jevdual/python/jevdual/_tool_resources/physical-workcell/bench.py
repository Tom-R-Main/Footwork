"""Persistent image-guided MuJoCo bench: prepare, computer measurement, contact reset."""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import image_guided as vision
import measurement
import mujoco
import numpy as np
import order_protocol as protocol
import workcell as body

Refusal = body.Refusal
BASE = Path(__file__).resolve().parent
HOME_ZONE = {"x_min": -.16, "x_max": -.08, "y_min": -.03, "y_max": .03}
TARGET_BOUNDS = {"x_min": .02, "x_max": .12, "y_min": -.03, "y_max": .03}
MAX_MOVES_PER_JOB = 64
OBSERVATION_FIELDS = {"version", "source_kind", "bench_id", "job_id", "phase", "generation", "native_time_s",
                      "state_sha256", "image_path", "image_sha256", "calibration", "source_fingerprints"}


def fingerprints():
    return {**body.fingerprints(), "bench_sha256": body.sha(body.read_bytes(BASE / "bench.py")),
            "measurement_sha256": body.sha(body.read_bytes(BASE / "measurement.py")),
            "vision_sha256": body.sha(body.read_bytes(BASE / "image_guided.py")),
            "protocol_sha256": body.sha(body.read_bytes(BASE / "order_protocol.py")),
            "capture_utility_sha256": body.sha(body.read_bytes(BASE.parent / "camera-capture-experiment" / "capture.py"))}


def in_zone(xy, zone):
    return zone["x_min"] <= xy[0] <= zone["x_max"] and zone["y_min"] <= xy[1] <= zone["y_max"]


def validate_zone(zone):
    protocol.validate_zone(zone)
    if not (.02 <= zone["x_min"] < zone["x_max"] <= .12 and
            -.03 <= zone["y_min"] < zone["y_max"] <= .03 and
            zone["x_max"] - zone["x_min"] >= .04 and zone["y_max"] - zone["y_min"] >= .04):
        raise Refusal("job zone exceeds the qualified reachable center region")
    return dict(zone)


def initialize(root, diagnostic_enabled=False):
    root = protocol.directory(root, create=True)
    if type(diagnostic_enabled) is not bool:
        raise Refusal("diagnostic flag must be boolean")
    with protocol.locked(root):
        if any(path.name != "app.lock" for path in root.iterdir()):
            raise Refusal("bench initialization requires an empty owned directory")
        source = fingerprints()
        tree = ET.fromstring(body.read_bytes(body.SCENE))
        ET.SubElement(tree.find("worldbody"), "camera", {"name": "vision_top", "projection": "orthographic",
                      "fovy": "0.6", "pos": "0 0 1", "xyaxes": "1 0 0 0 1 0"})
        model_bytes = ET.tostring(tree, encoding="utf-8")
        body.create_file(root / "model.xml", model_bytes)
        for name in ("images", "operations", "requests", "jobs"):
            (root / name).mkdir(mode=0o700)
        model = mujoco.MjModel.from_xml_path(str(root / "model.xml"))
        data = mujoco.MjData(model)
        for _ in range(500):
            mujoco.mj_step(model, data)
        state_sha = body.save_state(root, model, data, 0)
        manifest = {"version": 1, "source_kind": body.SOURCE_KIND, "bench_id": uuid.uuid4().hex,
                    "source_fingerprints": source, "model_sha256": body.sha(model_bytes), "generation": 0,
                    "state_sha256": state_sha, "native_time_s": float(data.time), "diagnostic_enabled": diagnostic_enabled,
                    "active_job": None, "jobs": {}, "operations": {}, "busy": None}
        protocol.persist(root / "bench.json", manifest)
    return Bench(root).status()


class Bench:
    def __init__(self, root):
        self.root = protocol.directory(root)

    def _load(self, allow_busy=False):
        m = body.decoded(body.read_bytes(self.root / "bench.json"))
        if (not isinstance(m, dict) or (type(m.get("version")) is not int or m["version"] != 1) or m.get("source_kind") != body.SOURCE_KIND or
                m.get("source_fingerprints") != fingerprints() or type(m.get("generation")) is not int or
                not 0 <= m["generation"] <= 999999):
            raise Refusal("bench manifest or source fingerprint changed")
        if body.sha(body.read_bytes(self.root / "model.xml")) != m["model_sha256"]:
            raise Refusal("retained native model changed")
        content = body.read_bytes(body.state_path(self.root, m["generation"]))
        if body.sha(content) != m["state_sha256"]:
            raise Refusal("retained native state changed; implicit reset is forbidden")
        state = body.decoded(content)
        body.fields(state, ("source_kind", "state_spec", "values"), "native state")
        model = mujoco.MjModel.from_xml_path(str(self.root / "model.xml"))
        spec = mujoco.mjtState.mjSTATE_INTEGRATION
        if state["state_spec"] != int(spec) or state["source_kind"] != body.SOURCE_KIND:
            raise Refusal("native state specification changed")
        values = np.array([body.number(v) for v in state["values"]], dtype=float)
        if len(values) != mujoco.mj_stateSize(model, spec):
            raise Refusal("native state size changed")
        data = mujoco.MjData(model)
        mujoco.mj_setState(model, data, values, spec)
        mujoco.mj_forward(model, data)
        if data.time != m["native_time_s"]:
            raise Refusal("retained native time changed")
        if m["busy"] is not None and not allow_busy:
            raise Refusal("interrupted effect is unknown; new dispatch is blocked")
        if not allow_busy:
            self._verify_measurements(m)
        return m, model, data

    def _verify_measurements(self, m):
        jobs = list(m["jobs"].values()) + ([m["active_job"]] if m["active_job"] else [])
        for job in jobs:
            if "measurement_receipt" in job:
                recorded = measurement.read_result(self.root, job["measurement_operation_id"])
                if recorded != job["measurement_receipt"]:
                    raise Refusal("retained computer measurement changed")
                packet_path = self.root / "requests" / (body.sha(job["measurement_operation_id"].encode()) + ".json")
                packet = body.decoded(body.read_bytes(packet_path))
                if (packet["bench_id"] != m["bench_id"] or packet["job_id"] != job["job_id"] or
                        any(packet[k] != recorded[k] for k in ("generation", "state_sha256", "image_sha256"))):
                    raise Refusal("historical measurement packet binding changed")
                image_path = Path(packet["image_path"])
                if image_path.parent != self.root / "images":
                    raise Refusal("historical measurement image is not bench-owned")
                if body.sha(body.read_bytes(body.state_path(self.root, packet["generation"]))) != packet["state_sha256"]:
                    raise Refusal("historical measurement native state changed")
                if measurement.compute(packet, body.read_bytes(image_path)) != recorded["measurement"]:
                    raise Refusal("historical optical measurement changed")

    def _persist(self, m):
        protocol.persist(self.root / "bench.json", m)

    def _public(self, m):
        return {k: m[k] for k in ("version", "source_kind", "bench_id", "generation", "native_time_s",
                                 "source_fingerprints", "active_job", "jobs", "diagnostic_enabled")} | {
                                     "state": "unknown" if m["busy"] else "ready", "unresolved_effect": m["busy"]}

    def status(self):
        with protocol.locked(self.root):
            m, _, _ = self._load(allow_busy=True)
            public = self._public(m)
            try:
                self._verify_measurements(m)
            except (Refusal, OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
                public.update(state="unknown", unresolved_effect={"reason": str(exc), "kind": "measurement_integrity"})
            return public

    def start_job(self, job_id, target_zone):
        protocol.identity(job_id)
        zone = validate_zone(target_zone)
        with protocol.locked(self.root):
            m, _, _ = self._load()
            if m["active_job"] is not None or job_id in m["jobs"]:
                raise Refusal("one active job is allowed; job identity cannot be reused")
            job = {"job_id": job_id, "target_zone": zone, "phase": "prepare", "moves": 0,
                   "started_generation": m["generation"], "started_native_time_s": m["native_time_s"]}
            body.create_file(self.root / "jobs" / (body.sha(job_id.encode()) + ".json"), body.encoded(job))
            m["active_job"] = job
            self._persist(m)
            return self._public(m)

    def _observation(self, m, model, data):
        job = m["active_job"]
        zone = job["target_zone"] if job else HOME_ZONE
        marker = model.geom("inspection_zone")
        marker.pos[:2] = [(zone["x_min"] + zone["x_max"]) / 2, (zone["y_min"] + zone["y_max"]) / 2]
        marker.size[:2] = [(zone["x_max"] - zone["x_min"]) / 2, (zone["y_max"] - zone["y_min"]) / 2]
        mujoco.mj_forward(model, data)
        try:
            with mujoco.Renderer(model, height=360, width=640) as renderer:
                renderer.update_scene(data, camera="vision_top")
                content = body.png_bytes(renderer.render().copy())
        except Exception as exc:
            raise Refusal("native RGB renderer unavailable; no image was fabricated") from exc
        name = f"{m['generation']:06d}-{body.sha(body.encoded(job))[:16]}.png"
        image_path = self.root / "images" / name
        if image_path.exists() or image_path.is_symlink():
            if body.read_bytes(image_path) != content:
                raise Refusal("retained observation image changed")
        else:
            body.create_file(image_path, content)
        return {"version": 1, "source_kind": body.SOURCE_KIND, "bench_id": m["bench_id"],
                "job_id": job["job_id"] if job else None, "phase": job["phase"] if job else "idle",
                "generation": m["generation"], "native_time_s": m["native_time_s"], "state_sha256": m["state_sha256"],
                "image_path": str(image_path), "image_sha256": body.sha(content),
                "calibration": vision.calibration(), "source_fingerprints": m["source_fingerprints"]}

    def observe(self):
        with protocol.locked(self.root):
            return self._observation(*self._load())

    def _fresh(self, observation, loaded):
        body.fields(observation, OBSERVATION_FIELDS, "observation")
        if type(observation["generation"]) is not int or type(observation["version"]) is not int:
            raise Refusal("observation versions must be exact integers")
        current = self._observation(*loaded)
        if observation != current:
            raise Refusal("observation is stale or foreign; no requested effect dispatched")
        return current

    def _operation(self, m, operation_id, request):
        protocol.identity(operation_id)
        path = self.root / "operations" / (body.sha(operation_id.encode()) + ".json")
        if operation_id in m["operations"]:
            content = body.read_bytes(path)
            if body.sha(content) != m["operations"][operation_id]:
                raise Refusal("historical operation receipt changed")
            record = body.decoded(content)
            if record["request"] != request:
                raise Refusal("operation identity conflicts with its retained request")
            return record["receipt"]
        if path.exists() or path.is_symlink():
            raise Refusal("unresolved operation record exists")
        return None

    def _intent(self, m, operation_id, kind):
        m["busy"] = {"operation_id": operation_id, "kind": kind, "generation": m["generation"]}
        self._persist(m)

    def _finish(self, m, operation_id, request, receipt):
        content = body.encoded({"request": request, "receipt": receipt})
        body.create_file(self.root / "operations" / (body.sha(operation_id.encode()) + ".json"), content)
        m["operations"][operation_id] = body.sha(content)
        m["busy"] = None
        self._persist(m)
        return receipt

    def _advance(self, m, model, data):
        if m["generation"] >= 999999 or data.time <= m["native_time_s"]:
            raise Refusal("native time/generation did not advance")
        m["generation"] += 1
        m["state_sha256"] = body.save_state(self.root, model, data, m["generation"])
        m["native_time_s"] = float(data.time)
        block = data.xpos[model.body("block").id]
        if not (-.35 <= block[0] <= .35 and -.2 <= block[1] <= .2 and .02 <= block[2] <= .08):
            self._persist(m)
            raise Refusal("block left the bounded tabletop envelope; bench is unknown")

    def move(self, operation_id, observation, target_x, target_y):
        x, y = body.number(target_x), body.number(target_y)
        if not (-.32 <= x <= .18 and -.15 <= y <= .15):
            raise Refusal("pusher target exceeds native bounds")
        request = {"kind": "move", "observation": observation, "target_x": x, "target_y": y}
        with protocol.locked(self.root):
            loaded = self._load()
            m, model, data = loaded
            old = self._operation(m, operation_id, request)
            if old is not None:
                return old
            self._fresh(observation, loaded)
            job = m["active_job"]
            if job is None or job["phase"] not in {"prepare", "resetting"} or job["moves"] >= MAX_MOVES_PER_JOB:
                raise Refusal("job phase or motion budget does not allow motion")
            self._intent(m, operation_id, "move")
            native = body.motion(model, data, x, y)
            self._advance(m, model, data)
            job["moves"] += 1
            receipt = {"operation_id": operation_id, "kind": "move", "bench_id": m["bench_id"],
                       "job_id": job["job_id"], "generation": m["generation"], "native_time_s": m["native_time_s"],
                       "state_sha256": m["state_sha256"], "target_xy": [x, y], **native}
            return self._finish(m, operation_id, request, receipt)

    def _placement(self, m, model, data, packet, zone):
        _, located = measurement.image_and_location(body.read_bytes(Path(packet["image_path"])))
        image_center = vision.image_world_center(located["block"]["box"])
        block = data.xpos[model.body("block").id]
        if not in_zone(image_center, zone) or not in_zone(block[:2], zone) or not .02 <= block[2] <= .08:
            raise Refusal("fresh image and native placement do not satisfy the job region")

    def measure(self, operation_id, observation):
        request = {"kind": "measure", "observation": observation}
        with protocol.locked(self.root):
            loaded = self._load()
            m, model, data = loaded
            old = self._operation(m, operation_id, request)
            if old is not None:
                retained = measurement.read_result(self.root, operation_id)
                if retained != old["measurement_receipt"]:
                    raise Refusal("historical computer measurement changed")
                return old
            packet = self._fresh(observation, loaded)
            job = m["active_job"]
            if job is None or job["phase"] != "prepare":
                raise Refusal("measurement requires an active preparation phase")
            self._placement(m, model, data, packet, job["target_zone"])
            self._intent(m, operation_id, "measure")
            path = self.root / "requests" / (body.sha(operation_id.encode()) + ".json")
            content = body.encoded(packet)
            body.create_file(path, content)
            result = subprocess.run([sys.executable, str(BASE / "measurement.py"), "--root", str(self.root),
                                     "--operation-id", operation_id, "--packet-file", str(path),
                                     "--packet-sha256", body.sha(content)], capture_output=True, timeout=30, check=False)
            body.create_file(self.root / "requests" / (body.sha(operation_id.encode()) + ".worker.json"),
                             body.encoded({"returncode": result.returncode, "stdout": result.stdout.decode(),
                                           "stderr": result.stderr.decode()}))
            if result.returncode != 0:
                raise Refusal("computer measurement worker failed; dispatch outcome is unknown")
            recorded = measurement.read_result(self.root, operation_id)
            expected = {"operation_id": operation_id, "bench_id": m["bench_id"], "job_id": job["job_id"],
                        "generation": m["generation"], "image_sha256": packet["image_sha256"],
                        "state_sha256": m["state_sha256"]}
            if any(recorded.get(k) != value for k, value in expected.items()) or recorded["worker_pid"] == os.getpid():
                raise Refusal("independent measurement readback does not match the dispatched job")
            recomputed = measurement.compute(packet, body.read_bytes(Path(packet["image_path"])))
            if recorded["measurement"] != recomputed:
                raise Refusal("independent image measurement recomputation disagrees")
            job.update(phase="measured", measurement_operation_id=operation_id, measurement_receipt=recorded)
            receipt = {"operation_id": operation_id, "kind": "measure", **expected, "measurement_receipt": recorded}
            return self._finish(m, operation_id, request, receipt)

    def begin_reset(self, job_id):
        protocol.identity(job_id)
        with protocol.locked(self.root):
            m, _, _ = self._load()
            job = m["active_job"]
            if job is None or job["job_id"] != job_id or job["phase"] not in {"measured", "resetting"}:
                raise Refusal("reset requires the exact measured active job")
            if job["phase"] == "measured":
                job["reset_started_generation"] = m["generation"]
            job["phase"] = "resetting"
            self._persist(m)
            return self._public(m)

    def finish_reset(self, operation_id, observation):
        request = {"kind": "finish_reset", "observation": observation}
        with protocol.locked(self.root):
            loaded = self._load()
            m, model, data = loaded
            old = self._operation(m, operation_id, request)
            if old is not None:
                return old
            packet = self._fresh(observation, loaded)
            job = m["active_job"]
            if job is None or job["phase"] != "resetting":
                raise Refusal("reset completion requires the resetting phase")
            self._placement(m, model, data, packet, HOME_ZONE)
            pusher = data.xpos[model.body("pusher").id]
            _, located = measurement.image_and_location(body.read_bytes(Path(packet["image_path"])))
            image_pusher = vision.image_world_center(located["pusher"]["box"])
            if (abs(pusher[0] + .3) > .005 or abs(pusher[1]) > .005 or
                    abs(image_pusher[0] + .3) > .005 or abs(image_pusher[1]) > .005):
                raise Refusal("fresh image and native pusher must verify its home position")
            reset_native_steps, reset_contacts = 0, 0
            for token, digest in m["operations"].items():
                content = body.read_bytes(self.root / "operations" / (body.sha(token.encode()) + ".json"))
                if body.sha(content) != digest:
                    raise Refusal("reset operation history changed")
                record = body.decoded(content)
                receipt = record["receipt"]
                if (receipt.get("kind") == "move" and receipt.get("job_id") == job["job_id"] and
                        record["request"]["observation"]["phase"] == "resetting" and
                        receipt["generation"] > job["reset_started_generation"]):
                    reset_native_steps += receipt["native_steps"]
                    reset_contacts += receipt["pusher_block_contact_samples"]
            if reset_native_steps <= 0 or reset_contacts <= 0:
                raise Refusal("reset requires retained native contact-motion evidence")
            self._intent(m, operation_id, "finish_reset")
            receipt = {"operation_id": operation_id, "kind": "finish_reset", "bench_id": m["bench_id"],
                       "job_id": job["job_id"], "generation": m["generation"], "native_time_s": m["native_time_s"],
                       "state_sha256": m["state_sha256"], "image_sha256": packet["image_sha256"],
                       "block_home_verified": True, "pusher_home_verified": True,
                       "reset_native_steps": reset_native_steps, "reset_contact_samples": reset_contacts}
            job.update(phase="completed", reset_receipt=receipt, completed_generation=m["generation"],
                       completed_native_time_s=m["native_time_s"])
            m["jobs"][job["job_id"]] = job
            m["active_job"] = None
            return self._finish(m, operation_id, request, receipt)

    def disturb(self, operation_id, force_x_n, steps):
        force = body.number(force_x_n)
        if not 0 < abs(force) <= 2 or type(steps) is not int or not 1 <= steps <= 150:
            raise Refusal("diagnostic force or native step budget exceeds bounds")
        request = {"kind": "disturb", "force_x_n": force, "steps": steps}
        with protocol.locked(self.root):
            m, model, data = self._load()
            old = self._operation(m, operation_id, request)
            if old is not None:
                return old
            if not m["diagnostic_enabled"] or m["active_job"] is None or m["active_job"]["phase"] != "prepare":
                raise Refusal("diagnostic intervention requires explicit enabled preparation")
            self._intent(m, operation_id, "disturb")
            body_id = model.body("block").id
            for _ in range(steps):
                data.xfrc_applied[body_id, 0] = force
                mujoco.mj_step(model, data)
            data.xfrc_applied[body_id, :] = 0
            for _ in range(500):
                mujoco.mj_step(model, data)
            mujoco.mj_forward(model, data)
            self._advance(m, model, data)
            receipt = {"operation_id": operation_id, "kind": "diagnostic_external_force", "bench_id": m["bench_id"],
                       "job_id": m["active_job"]["job_id"], "generation": m["generation"],
                       "native_time_s": m["native_time_s"], "state_sha256": m["state_sha256"],
                       "force_x_n": force, "forced_steps": steps, "native_steps": steps + 500}
            return self._finish(m, operation_id, request, receipt)


def read_packet(path, expected_sha256):
    content = body.read_bytes(Path(path))
    if not body.DIGEST.fullmatch(expected_sha256) or body.sha(content) != expected_sha256:
        raise Refusal("observation file digest changed")
    return body.decoded(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--diagnostic-enabled", action="store_true")
    for name in ("status", "observe"):
        sub.add_parser(name)
    start = sub.add_parser("start")
    start.add_argument("--job-id", required=True)
    start.add_argument("--target-zone", required=True, help="JSON object with x_min/x_max/y_min/y_max")
    reset = sub.add_parser("begin-reset")
    reset.add_argument("--job-id", required=True)
    for name in ("move", "measure", "finish-reset"):
        command = sub.add_parser(name)
        command.add_argument("--operation-id", required=True)
        command.add_argument("--observation-file", required=True, type=Path)
        command.add_argument("--observation-sha256", required=True)
        if name == "move":
            command.add_argument("--target-x", required=True, type=float)
            command.add_argument("--target-y", required=True, type=float)
    disturb = sub.add_parser("disturb")
    disturb.add_argument("--operation-id", required=True)
    disturb.add_argument("--force-x-n", required=True, type=float)
    disturb.add_argument("--steps", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = initialize(args.root, args.diagnostic_enabled)
        else:
            bench = Bench(args.root)
            if args.command in {"status", "observe"}:
                result = getattr(bench, args.command)()
            elif args.command == "start":
                result = bench.start_job(args.job_id, body.decoded(args.target_zone.encode()))
            elif args.command == "begin-reset":
                result = bench.begin_reset(args.job_id)
            elif args.command == "disturb":
                result = bench.disturb(args.operation_id, args.force_x_n, args.steps)
            else:
                observation = read_packet(args.observation_file, args.observation_sha256)
                method = getattr(bench, args.command.replace("-", "_"))
                extra = (args.target_x, args.target_y) if args.command == "move" else ()
                result = method(args.operation_id, observation, *extra)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"state": "refused", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
