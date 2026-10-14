"""Native MuJoCo body, bounded contact actions, and conditional local work-order result."""

import argparse
import contextlib
import hashlib
import importlib.util
import json
import math
import os
import re
import stat
import struct
import sys
import time
import zlib
from pathlib import Path

import mujoco
import numpy as np

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
SCENE = BASE / "scene.xml"
FOOTWORK = BASE.parents[1] / "jevdual" / ".venv" / "bin" / "footwork"
SPEC = importlib.util.spec_from_file_location("camera_utils", BASE.parent / "camera-capture-experiment" / "capture.py")
utils = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(utils)
CASE_SPEC = importlib.util.spec_from_file_location("episode_case_contract", BASE / "episode_cases.py")
cases = importlib.util.module_from_spec(CASE_SPEC)
CASE_SPEC.loader.exec_module(cases)
Refusal = utils.Refusal
PINNED_VERSION = "3.15.0"
SOURCE_KIND = "mujoco_simulation"
MAX_FILE = 1024 * 1024
CONTROLLER = {"timestep_s": 0.002, "speed_m_s": 0.15, "settle_s": 1.0,
              "force_limit_n_per_axis": 4.0, "wall_timeout_s": 10.0, "max_steps": 3000,
              "x_min": -0.32, "x_max": 0.18, "y_min": -0.15, "y_max": 0.15,
              "pusher_origin_x": -0.3, "block_z_min": 0.02, "block_z_max": 0.08}
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def read_bytes(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
                raise Refusal("retained file must be regular and within the 1 MiB limit")
            data = source.read(MAX_FILE + 1)
            after = os.fstat(source.fileno())
        if len(data) > MAX_FILE or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise Refusal("retained file changed or exceeded its size limit")
        return data
    except OSError as exc:
        raise Refusal("retained file is missing, symlinked or unreadable") from exc


def decoded(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refusal("duplicate JSON key")
            result[key] = value
        return result

    try:
        return json.loads(data, object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(Refusal("nonfinite JSON value")))
    except (ValueError, UnicodeError) as exc:
        raise Refusal("invalid retained JSON") from exc


def create_file(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as sink:
        sink.write(data)
        sink.flush()
        os.fsync(sink.fileno())


def directory(path, create=False):
    root = Path(os.path.abspath(os.fspath(path)))
    if root == OUTPUT or OUTPUT not in root.parents:
        raise Refusal("run must be a subdirectory of physical-workcell/output")
    current = OUTPUT
    for part in (None, *root.relative_to(OUTPUT).parts):
        if part is not None:
            current = current / part
        if create:
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                pass
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Refusal("run directories must be owned, private and free of symlinks")
    return root


def fields(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Refusal(f"{label} has invalid fields")


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise Refusal("coordinates and state values must be finite numbers")
    return float(value)


def order_schema(order):
    fields(order, ("version", "order_id", "project", "part_id", "target_zone"), "work order")
    if type(order["version"]) is not int or order["version"] != 1 or order["part_id"] != "block":
        raise Refusal("only version 1 block orders are supported")
    fields(order["project"], ("namespace", "project_id"), "project identity")
    for value in (order["order_id"], *order["project"].values()):
        if not isinstance(value, str) or not IDENTITY.fullmatch(value):
            raise Refusal("order and project identities must be exact bounded strings")
    zone = order["target_zone"]
    fields(zone, ("x_min", "x_max", "y_min", "y_max"), "target zone")
    for value in zone.values():
        number(value)
    if not (-0.35 <= zone["x_min"] < zone["x_max"] <= 0.35 and
            -0.2 <= zone["y_min"] < zone["y_max"] <= 0.2):
        raise Refusal("target zone must be a bounded nonempty tabletop rectangle")
    return order


def fingerprints():
    if mujoco.__version__ != PINNED_VERSION:
        raise Refusal("runtime must use pinned MuJoCo 3.15.0")
    return {"mujoco_version": mujoco.__version__, "model_sha256": sha(read_bytes(SCENE)),
            "implementation_sha256": sha(read_bytes(Path(__file__))),
            "case_validator_sha256": sha(read_bytes(BASE / "episode_cases.py")),
            "controller_sha256": sha(encoded(CONTROLLER)),
            "state_spec": int(mujoco.mjtState.mjSTATE_INTEGRATION)}


def state_path(root, generation):
    return root / f"state-{generation:06d}.json"


def save_state(root, model, data, generation):
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    values = np.empty(mujoco.mj_stateSize(model, spec), dtype=np.float64)
    mujoco.mj_getState(model, data, values, spec)
    if not np.isfinite(values).all():
        raise Refusal("native integration state contains nonfinite values")
    content = encoded({"source_kind": SOURCE_KIND, "state_spec": int(spec), "values": values.tolist()})
    create_file(state_path(root, generation), content)
    return sha(content)


def model_for(root, order):
    model = mujoco.MjModel.from_xml_path(str(root / "model.xml"))
    # This non-contact visual rectangle comes from the bound order, never changes dynamics.
    zone = order["target_zone"]
    marker = model.geom("inspection_zone")
    marker.pos[:2] = [(zone["x_min"] + zone["x_max"]) / 2, (zone["y_min"] + zone["y_max"]) / 2]
    marker.size[:2] = [(zone["x_max"] - zone["x_min"]) / 2, (zone["y_max"] - zone["y_min"]) / 2]
    return model


def load(root):
    manifest = decoded(read_bytes(root / "manifest.json"))
    if (not isinstance(manifest, dict) or type(manifest.get("version")) is not int or
            manifest["version"] != 1 or manifest.get("source_kind") != SOURCE_KIND):
        raise Refusal("workcell manifest is invalid")
    if not isinstance(manifest.get("phase"), str) or manifest["phase"] not in {"ready", "acting", "completing", "completed", "unknown"}:
        raise Refusal("workcell phase is invalid")
    generation = manifest.get("generation")
    if type(generation) is not int or not 0 <= generation <= 999999:
        raise Refusal("state generation is invalid")
    if manifest.get("fingerprints") != fingerprints():
        raise Refusal("model, controller, implementation or native runtime fingerprint changed")
    case_for(root, manifest)
    for key in ("state_sha256", "work_order_sha256"):
        if not isinstance(manifest.get(key), str) or not DIGEST.fullmatch(manifest[key]):
            raise Refusal("retained digest is invalid")
    if manifest["phase"] == "completed" and (not isinstance(manifest.get("result_sha256"), str) or not DIGEST.fullmatch(manifest["result_sha256"])):
        raise Refusal("software result digest is invalid")
    if sha(read_bytes(root / "model.xml")) != manifest["fingerprints"]["model_sha256"]:
        raise Refusal("retained model changed")
    order_bytes = read_bytes(root / "work-order.json")
    if sha(order_bytes) != manifest["work_order_sha256"]:
        raise Refusal("retained work order changed")
    original = manifest.get("work_order_path")
    if not isinstance(original, str) or not Path(original).is_absolute() or sha(read_bytes(Path(original))) != manifest["work_order_sha256"]:
        raise Refusal("original work order is missing or changed")
    order = order_schema(decoded(order_bytes))
    model = model_for(root, order)
    state_bytes = read_bytes(state_path(root, generation))
    if sha(state_bytes) != manifest["state_sha256"]:
        raise Refusal("retained integration state changed; implicit reset is forbidden")
    state = decoded(state_bytes)
    fields(state, ("source_kind", "state_spec", "values"), "integration state")
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    if state["source_kind"] != SOURCE_KIND or state["state_spec"] != int(spec) or not isinstance(state["values"], list):
        raise Refusal("integration state schema is invalid")
    if len(state["values"]) != mujoco.mj_stateSize(model, spec):
        raise Refusal("integration state length does not match native model")
    values = np.array([number(value) for value in state["values"]], dtype=np.float64)
    data = mujoco.MjData(model)
    mujoco.mj_setState(model, data, values, spec)
    mujoco.mj_forward(model, data)
    return manifest, order, model, data


def op_path(root, token):
    if not isinstance(token, str) or not utils.TOKEN.fullmatch(token):
        raise Refusal("operation token must be an exact bounded safe string")
    return root / f"op-{sha(token.encode())}.json"


def load_op(path):
    op = decoded(read_bytes(path))
    if not isinstance(op, dict) or not isinstance(op.get("phase"), str) or op["phase"] not in {"pending", "unknown", "executed", "staged"}:
        raise Refusal("operation record is malformed")
    if not isinstance(op.get("token"), str) or not utils.TOKEN.fullmatch(op["token"]) or not isinstance(op.get("request"), dict):
        raise Refusal("operation identity is malformed")
    if op.get("source_kind") != SOURCE_KIND or op_path(path.parent, op["token"]) != path:
        raise Refusal("operation source or token-file binding is invalid")
    request = op["request"]
    if request.get("kind") == "act":
        fields(request, ("kind", "expected_generation", "target_x", "target_y"), "motion request")
        if type(request["expected_generation"]) is not int or request["expected_generation"] < 0:
            raise Refusal("retained motion generation is invalid")
        number(request["target_x"])
        number(request["target_y"])
        if op["phase"] == "staged":
            raise Refusal("motion cannot be a software-staging receipt")
    elif request.get("kind") == "complete":
        fields(request, ("kind", "work_order_sha256"), "completion request")
        if not isinstance(request["work_order_sha256"], str) or not DIGEST.fullmatch(request["work_order_sha256"]) or op["phase"] == "executed":
            raise Refusal("retained completion receipt is invalid")
    else:
        raise Refusal("retained operation kind is invalid")
    return op


def unresolved(root, manifest):
    return manifest["phase"] in {"acting", "completing", "unknown"} or any(
        load_op(path)["phase"] in {"pending", "unknown"} for path in root.glob("op-*.json")
    )


def poses(model, data, order):
    block = data.xpos[model.body("block").id].copy()
    pusher = data.xpos[model.body("pusher").id].copy()
    zone = order["target_zone"]
    in_zone = (zone["x_min"] <= block[0] <= zone["x_max"] and zone["y_min"] <= block[1] <= zone["y_max"] and
               CONTROLLER["block_z_min"] <= block[2] <= CONTROLLER["block_z_max"])
    return {"block_xyz": block.tolist(), "pusher_xyz": pusher.tolist(), "block_center_in_zone": bool(in_zone)}


def artifact_check(root, expected_sha):
    rc, stdout, _ = utils.run_process([str(FOOTWORK), "check-artifact", str(root / "order.json"),
                                      "--expected-file", str(root / "expected-order.json"),
                                      "--expected-sha256", expected_sha], 20)
    result = decoded(stdout.encode())
    if not isinstance(result, dict) or type(result.get("ok")) is not bool or rc not in (0, 6) or result["ok"] != (rc == 0):
        raise Refusal("Footwork checker result is invalid")
    return result


def observation(root, loaded=None):
    manifest, order, model, data = loaded or load(root)
    uncertain = unresolved(root, manifest)
    state = poses(model, data, order)
    result = {"source_kind": SOURCE_KIND, "generation": manifest["generation"], "frame": "sim_world",
              "state_sha256": manifest["state_sha256"], "simulation_time_s": float(data.time),
              "phase": "unknown" if uncertain else manifest["phase"], "order_id": order["order_id"],
              "target_zone": order["target_zone"], **state,
              "state_authority": "retained_unresolved_operation" if uncertain else "current_persisted_simulator_state",
              "physical_condition_verified": state["block_center_in_zone"] and not uncertain,
              "claims": [] if uncertain else ["native_simulator_state_observation"]}
    if manifest["phase"] == "completed" and not uncertain:
        checked = artifact_check(root, manifest["result_sha256"])
        result.update(historical_software_outcome="staged", current_software_artifact_check=checked)
        if not checked["ok"]:
            result.update(phase="unknown", claims=[])
    return result


def case_for(root, manifest=None):
    manifest = manifest or decoded(read_bytes(root / "manifest.json"))
    binding = manifest.get("episode_case")
    if binding is None:
        return None
    fields(binding, ("case_id", "case_file", "case_sha256", "max_actions"), "retained episode binding")
    try:
        case, _, content = cases.load(binding["case_file"], binding["case_sha256"])
        retained = cases.read_bytes(root / "episode-case.json")
        if retained != content or binding["case_id"] != case["case_id"] or binding["max_actions"] != case["max_actions"]:
            raise Refusal("retained case binding or bytes changed")
        return case
    except cases.CaseError as exc:
        raise Refusal(str(exc)) from exc


def action_budget(root, manifest=None):
    manifest = manifest or decoded(read_bytes(root / "manifest.json"))
    case = case_for(root, manifest)
    admitted = sum(load_op(path)["request"]["kind"] in {"act", "complete"} for path in root.glob("op-*.json"))
    maximum = case["max_actions"] if case else None
    return {"max_actions": maximum, "admitted_dispatches": admitted,
            "remaining": None if maximum is None else max(0, maximum - admitted)}


def validate_episode_marker(root, binding):
    path = root / "episode.json"
    if not path.exists() and not path.is_symlink():
        return
    marker = decoded(read_bytes(path))
    fields(marker, ("version", "episode_id", "run_dir", "case_path", "case_sha256", "participant",
                    "started_time_unix", "phase", "fingerprint"), "episode initialization marker")
    if (type(marker["version"]) is not int or marker["version"] != 1 or marker["phase"] != "initializing" or
            marker["run_dir"] != str(root) or marker["case_path"] != binding["case_file"] or
            marker["case_sha256"] != binding["case_sha256"] or
            marker["participant"] not in {"fresh_host", "deterministic_rgb"} or
            not isinstance(marker["episode_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", marker["episode_id"])):
        raise Refusal("episode initialization marker is not bound to this case/run")
    if number(marker["started_time_unix"]) <= 0:
        raise Refusal("episode start time must be a positive finite timestamp")
    fields(marker["fingerprint"], ("runner_sha256", "vision"), "episode runner fingerprint")
    if not isinstance(marker["fingerprint"]["runner_sha256"], str) or not DIGEST.fullmatch(marker["fingerprint"]["runner_sha256"]) or not isinstance(marker["fingerprint"]["vision"], dict):
        raise Refusal("episode initialization fingerprint is invalid")


def initialize(root, work_order, work_order_sha256, *, episode_case=None, case_binding=None):
    if not DIGEST.fullmatch(work_order_sha256):
        raise Refusal("work-order SHA256 must be an exact lowercase digest")
    source = read_bytes(Path(work_order))
    if sha(source) != work_order_sha256:
        raise Refusal("work order no longer matches its bound digest")
    order = order_schema(decoded(source))
    original = str(Path(os.path.abspath(work_order)))
    if (root / "manifest.json").exists() or (root / "manifest.json").is_symlink():
        loaded = load(root)
        if (loaded[0]["work_order_sha256"] != work_order_sha256 or loaded[0]["work_order_path"] != original or
                loaded[0].get("episode_case") != case_binding):
            raise Refusal("run already belongs to another work order")
        return observation(root, loaded)
    allowed = {"lock", "episode.json", "episode-case.json", "episode-work-order.json"} if episode_case else {"lock"}
    if any(path.name not in allowed for path in root.iterdir()):
        raise Refusal("unreceipted run files exist; implicit initialization/reset is forbidden")
    fingerprint = fingerprints()
    create_file(root / "model.xml", read_bytes(SCENE))
    create_file(root / "work-order.json", source)
    model = model_for(root, order)
    data = mujoco.MjData(model)
    if episode_case is not None:
        # The caller-specified initial state is applied only on first initialization, never act/load.
        start = model.jnt_qposadr[model.joint("block_free").id]
        data.qpos[start:start + 2] = episode_case["scene"]["block_xy"]
    for _ in range(round(CONTROLLER["settle_s"] / CONTROLLER["timestep_s"])):
        mujoco.mj_step(model, data)
    mujoco.mj_forward(model, data)
    state_sha = save_state(root, model, data, 0)
    manifest = {"version": 1, "source_kind": SOURCE_KIND, "phase": "ready", "generation": 0,
                "work_order_path": original, "work_order_sha256": work_order_sha256,
                "fingerprints": fingerprint, "state_sha256": state_sha}
    if case_binding is not None:
        manifest["episode_case"] = case_binding
    utils.persist(root / "manifest.json", manifest)
    return observation(root)


def initialize_episode(root, case_file, case_sha256):
    try:
        case, source_path, content = cases.load(case_file, case_sha256)
    except cases.CaseError as exc:
        raise Refusal(str(exc)) from exc
    binding = {"case_id": case["case_id"], "case_file": str(source_path), "case_sha256": case_sha256,
               "max_actions": case["max_actions"]}
    order_path = root / "episode-work-order.json"
    order_bytes = encoded(case["work_order"])
    if (root / "manifest.json").exists() or (root / "manifest.json").is_symlink():
        return initialize(root, str(order_path), sha(order_bytes), episode_case=case, case_binding=binding)
    validate_episode_marker(root, binding)
    if any(path.name not in {"lock", "episode.json"} for path in root.iterdir()):
        raise Refusal("interrupted episode initialization has retained files; no implicit reset")
    create_file(root / "episode-case.json", content)
    create_file(order_path, order_bytes)
    return initialize(root, str(order_path), sha(order_bytes), episode_case=case, case_binding=binding)


def motion(model, data, target_x, target_y, *, motion_control=None):
    target = np.array([target_x - CONTROLLER["pusher_origin_x"], target_y])
    start = data.ctrl.copy()
    steps = max(1, math.ceil(float(np.linalg.norm(target - start)) / (CONTROLLER["speed_m_s"] * CONTROLLER["timestep_s"])))
    settle = round(CONTROLLER["settle_s"] / CONTROLLER["timestep_s"])
    if steps + settle > CONTROLLER["max_steps"]:
        raise Refusal("controller step budget exceeded")
    push_ids = {model.geom("block_geom").id, model.geom("pusher_geom").id}
    contacts, max_force = 0, 0.0
    started = time.monotonic()
    cancelled, advancing_steps, native_steps = False, 0, 0
    pace = number(motion_control.get("pace_s", 0)) if motion_control else 0
    if not 0 <= pace <= .003 or (motion_control and not callable(motion_control.get("cancel_requested"))):
        raise Refusal("motion cancellation/pacing hook is invalid")
    for step in range(steps + settle):
        if time.monotonic() - started > CONTROLLER["wall_timeout_s"]:
            raise Refusal("native motion exceeded bounded wall time")
        if motion_control and motion_control["cancel_requested"]():
            cancelled = True
            break
        data.ctrl[:] = start + (target - start) * min(1, (step + 1) / steps)
        advancing_steps = min(step + 1, steps)
        mujoco.mj_step(model, data)
        native_steps += 1
        if pace:
            time.sleep(pace)
        if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
            raise Refusal("native dynamics became nonfinite")
        max_force = max(max_force, float(np.max(np.abs(data.actuator_force))))
        if max_force > CONTROLLER["force_limit_n_per_axis"] + 1e-8:
            raise Refusal("native actuator exceeded its force envelope")
        contacts += sum({int(contact.geom1), int(contact.geom2)} == push_ids for contact in data.contact)
    steps_before_cancel = native_steps if cancelled else None
    if cancelled:
        # Hold the last actuator command. Never assign qpos/qvel or teleport a body.
        for _ in range(settle):
            if time.monotonic() - started > CONTROLLER["wall_timeout_s"]:
                raise Refusal("cancel settling exceeded bounded native wall time")
            mujoco.mj_step(model, data)
            native_steps += 1
            if pace:
                time.sleep(pace)
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                raise Refusal("native cancellation dynamics became nonfinite")
            max_force = max(max_force, float(np.max(np.abs(data.actuator_force))))
            if max_force > CONTROLLER["force_limit_n_per_axis"] + 1e-8:
                raise Refusal("native cancel settling exceeded its force envelope")
            contacts += sum({int(contact.geom1), int(contact.geom2)} == push_ids for contact in data.contact)
    mujoco.mj_forward(model, data)
    result = {"native_steps": native_steps, "pusher_block_contact_samples": contacts,
              "max_axis_actuator_force_n": max_force, "command_speed_limit_m_s": CONTROLLER["speed_m_s"]}
    if motion_control:
        start_dof = model.jnt_dofadr[model.joint("block_free").id]
        linear = float(np.max(np.abs(data.qvel[start_dof:start_dof + 3])))
        angular = float(np.max(np.abs(data.qvel[start_dof + 3:start_dof + 6])))
        pusher_velocity = max(abs(float(data.qvel[model.jnt_dofadr[model.joint(name).id]]))
                              for name in ("pusher_x", "pusher_y"))
        result.update(cancellation_requested=cancelled, target_trajectory_completed=advancing_steps == steps,
                      stop_verified=(linear <= .002 and angular <= .02 and pusher_velocity <= .002) if cancelled else None,
                      stop_evidence={"block_linear_velocity_max_m_s": linear,
                                     "block_angular_velocity_max_rad_s": angular,
                                     "pusher_velocity_max_m_s": pusher_velocity,
                                     "linear_velocity_limit_m_s": .002, "angular_velocity_limit_rad_s": .02,
                                     "held_actuator_command": data.ctrl.tolist(), "settle_steps": settle,
                                     "native_steps_before_cancel": steps_before_cancel} if cancelled else None)
    return result


def act(root, token, expected_generation, target_x, target_y, *, motion_control=None):
    x, y = number(target_x), number(target_y)
    if not CONTROLLER["x_min"] <= x <= CONTROLLER["x_max"] or not CONTROLLER["y_min"] <= y <= CONTROLLER["y_max"]:
        raise Refusal("pusher target is outside the admitted workspace")
    if type(expected_generation) is not int or expected_generation < 0:
        raise Refusal("expected generation must be a nonnegative integer")
    loaded = load(root)
    manifest, order, model, data = loaded
    request = {"kind": "act", "expected_generation": expected_generation, "target_x": x, "target_y": y}
    path = op_path(root, token)
    if path.exists() or path.is_symlink():
        op = load_op(path)
        if op["token"] != token or op["request"] != request:
            raise Refusal("token already belongs to different arguments")
        return {"source_kind": SOURCE_KIND, "operation": op, "observation": observation(root, loaded), "replayed": False}
    if unresolved(root, manifest) or manifest["phase"] == "completed":
        raise Refusal("unresolved or completed work order blocks further motion")
    if action_budget(root, manifest)["remaining"] == 0:
        raise Refusal("episode admitted-action budget is exhausted")
    if expected_generation != manifest["generation"]:
        raise Refusal("observation generation is stale; observe again")
    op = {"source_kind": SOURCE_KIND, "token": token, "request": request, "phase": "pending",
          "intent_time_unix": time.time(), "before_state_sha256": manifest["state_sha256"]}
    utils.persist(path, op)
    try:
        manifest["phase"] = "acting"
        utils.persist(root / "manifest.json", manifest)
        evidence = motion(model, data, x, y) if motion_control is None else motion(model, data, x, y, motion_control=motion_control)
        op["controller_evidence"] = evidence
        if evidence.get("cancellation_requested") and evidence.get("stop_verified") is not True:
            raise Refusal("native cancellation has no verified stop")
        generation = manifest["generation"] + 1
        state_sha = save_state(root, model, data, generation)
        manifest.update(phase="ready", generation=generation, state_sha256=state_sha)
        utils.persist(root / "manifest.json", manifest)
        op.update(phase="executed", historical_motion_outcome="executed", after_generation=generation,
                  after_state_sha256=state_sha, physical_readback=poses(model, data, order), controller_evidence=evidence)
        utils.persist(path, op)
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - all post-intent failures remain unresolved
        op.update(phase="unknown", historical_motion_outcome="unknown")
        manifest["phase"] = "unknown"
        with contextlib.suppress(OSError):
            utils.persist(path, op)
            utils.persist(root / "manifest.json", manifest)
    return {"source_kind": SOURCE_KIND, "operation": op, "observation": observation(root), "replayed": False}


def complete(root, token):
    loaded = load(root)
    manifest, order, model, data = loaded
    request = {"kind": "complete", "work_order_sha256": manifest["work_order_sha256"]}
    path = op_path(root, token)
    if path.exists() or path.is_symlink():
        op = load_op(path)
        if op["token"] != token or op["request"] != request:
            raise Refusal("token already belongs to another operation")
        return {"source_kind": SOURCE_KIND, "operation": op, "observation": observation(root, loaded), "replayed": False}
    if unresolved(root, manifest) or manifest["phase"] == "completed":
        raise Refusal("unresolved or already staged work order blocks another completion")
    if action_budget(root, manifest)["remaining"] == 0:
        raise Refusal("episode admitted-action budget is exhausted")
    physical = poses(model, data, order)
    if not physical["block_center_in_zone"]:
        raise Refusal("observed block center is not in the work-order zone; no software result was created")
    op = {"source_kind": SOURCE_KIND, "token": token, "request": request, "phase": "pending",
          "intent_time_unix": time.time(), "physical_readback": physical, "state_sha256": manifest["state_sha256"]}
    utils.persist(path, op)
    try:
        manifest["phase"] = "completing"
        utils.persist(root / "manifest.json", manifest)
        result = {"source_kind": SOURCE_KIND, "version": 1, "order_id": order["order_id"],
                  "project": order["project"], "part_id": "block", "state": "staged",
                  "physical_predicate": physical, "target_zone": order["target_zone"],
                  "simulator_generation": manifest["generation"], "simulator_state_sha256": manifest["state_sha256"],
                  "work_order_sha256": manifest["work_order_sha256"], "fingerprints": manifest["fingerprints"]}
        content = encoded(result)
        create_file(root / "expected-order.json", content)
        create_file(root / "order.json", content)
        result_sha = sha(content)
        checked = artifact_check(root, result_sha)
        if not checked["ok"]:
            raise Refusal("local software result failed exact byte verification")
        manifest.update(phase="completed", result_sha256=result_sha)
        utils.persist(root / "manifest.json", manifest)
        op.update(phase="staged", historical_software_outcome="staged", result_sha256=result_sha, artifact_check=checked)
        utils.persist(path, op)
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - partial computer publication cannot replay
        op.update(phase="unknown", historical_software_outcome="unknown")
        manifest["phase"] = "unknown"
        with contextlib.suppress(OSError):
            utils.persist(path, op)
            utils.persist(root / "manifest.json", manifest)
    return {"source_kind": SOURCE_KIND, "operation": op, "observation": observation(root), "replayed": False}


def png_bytes(image):
    height, width, channels = image.shape
    if channels != 3 or image.dtype != np.uint8:
        raise Refusal("native renderer did not return RGB bytes")

    def chunk(kind, content):
        return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content))

    rows = b"".join(b"\x00" + row.tobytes() for row in image)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def render(root):
    loaded = load(root)
    manifest, _, model, data = loaded
    if unresolved(root, manifest):
        raise Refusal("unresolved state cannot supply a current simulator image")
    path = root / f"render-{manifest['generation']:06d}.png"
    if path.exists() or path.is_symlink():
        raise Refusal("render already exists and will not be overwritten")
    try:
        with mujoco.Renderer(model, height=360, width=640) as renderer:
            renderer.update_scene(data, camera="overview")
            content = png_bytes(renderer.render())
    except Exception as exc:
        raise Refusal("native MuJoCo renderer unavailable; no image was fabricated") from exc
    create_file(path, content)
    return {"source_kind": SOURCE_KIND, "generation": manifest["generation"], "image_path": str(path),
            "image_sha256": sha(content), "simulator_state_sha256": manifest["state_sha256"], "width": 640, "height": 360}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "observe", "act", "complete", "render"):
        child = sub.add_parser(command)
        child.add_argument("--run-dir", required=True)
        if command == "init":
            child.add_argument("--work-order", required=True)
            child.add_argument("--work-order-sha256", required=True)
        if command in {"act", "complete"}:
            child.add_argument("--token", required=True)
        if command == "act":
            child.add_argument("--expected-generation", type=int, required=True)
            child.add_argument("--target-x", type=float, required=True)
            child.add_argument("--target-y", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        root = directory(args.run_dir, create=args.command == "init")
        with utils.locked(root):
            if args.command == "init":
                result = initialize(root, args.work_order, args.work_order_sha256)
            elif args.command == "act":
                result = act(root, args.token, args.expected_generation, args.target_x, args.target_y)
            elif args.command == "complete":
                result = complete(root, args.token)
            elif args.command == "render":
                result = render(root)
            else:
                result = observation(root)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        op = result.get("operation", {})
        observed = result.get("observation", result)
        return 2 if op.get("phase") in {"pending", "unknown"} or observed.get("phase") == "unknown" else 0
    except (Refusal, OSError, KeyError, TypeError, ValueError, AttributeError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else "local simulator input or retained state is malformed or unavailable"
        print(json.dumps({"source_kind": SOURCE_KIND, "phase": "refused", "reason": reason, "claims": []}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
