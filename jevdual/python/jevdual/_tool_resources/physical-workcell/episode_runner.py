"""SIM3 participant lifecycle, deterministic RGB comparator and private evaluator.

The evaluator is a separate parent-only role; its native evidence is never planner feedback.
"""

import argparse
import importlib.util
import json
import os
import sys
import time
import uuid
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("episode_vision", BASE / "image_guided.py")
vision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vision)
body = vision.body
Refusal = body.Refusal
OUTCOMES = {"completed", "unresolved", "failed"}


def fingerprint():
    return {"runner_sha256": body.sha(body.read_bytes(Path(__file__))), "vision": vision.fingerprint()}


def lifecycle(root):
    record = body.decoded(body.read_bytes(root / "episode.json"))
    if (not isinstance(record, dict) or record.get("version") != 1 or
            record.get("run_dir") != str(root) or record.get("fingerprint") != fingerprint()):
        raise Refusal("episode source or exact run binding changed")
    if (record.get("phase") not in {"initializing", "active", "setup_failed", "finished"} or
            record.get("participant") not in {"fresh_host", "deterministic_rgb"} or
            body.number(record.get("started_time_unix")) <= 0 or
            not isinstance(record.get("case_sha256"), str) or not body.DIGEST.fullmatch(record["case_sha256"])):
        raise Refusal("episode lifecycle record is malformed")
    source = body.read_bytes(Path(record["case_path"]))
    if body.sha(source) != record.get("case_sha256"):
        raise Refusal("episode case changed; implicit reset is forbidden")
    return record


def public_history(root):
    """Declared receipt history only: no native-state scoring or current checker call."""
    result = []
    for path in sorted(root.glob("vision-op-*.json")):
        record = body.decoded(body.read_bytes(path))
        proposal = record.get("proposal", {})
        result.append({"token": proposal.get("token"), "decision": proposal.get("decision"),
                       "generation": proposal.get("generation"), "phase": record.get("phase")})
    return result


def public_episode(root, record):
    result = {key: record[key] for key in ("episode_id", "participant", "phase", "case_sha256",
                                          "started_time_unix")}
    result.update(source_kind=body.SOURCE_KIND, run_dir=str(root))
    if "finish" in record:
        result["declaration"] = record["finish"]
        result["history"] = public_history(root)
    return result


def initialize(root, case_file, case_sha256, participant="fresh_host"):
    if participant not in {"fresh_host", "deterministic_rgb"}:
        raise Refusal("participant must be fresh_host or deterministic_rgb")
    if not isinstance(case_sha256, str) or not body.DIGEST.fullmatch(case_sha256):
        raise Refusal("case SHA256 must be exact lowercase hexadecimal")
    source = body.read_bytes(Path(case_file))
    if body.sha(source) != case_sha256:
        raise Refusal("case bytes do not match the bound digest")
    case_path = str(Path(os.path.abspath(case_file)))
    episode_path = root / "episode.json"
    if episode_path.exists() or episode_path.is_symlink():
        record = lifecycle(root)
        if (record["case_path"], record["case_sha256"], record["participant"]) != (
                case_path, case_sha256, participant):
            raise Refusal("run already belongs to another case or participant")
        if record["phase"] != "active":
            return public_episode(root, record)
    else:
        if any(path.name != "lock" for path in root.iterdir()):
            raise Refusal("unreceipted episode files exist; no implicit reset")
        record = {"version": 1, "episode_id": uuid.uuid4().hex, "run_dir": str(root),
                  "case_path": case_path, "case_sha256": case_sha256, "participant": participant,
                  "started_time_unix": time.time(), "phase": "initializing", "fingerprint": fingerprint()}
        body.create_file(episode_path, body.encoded(record))
        try:
            body.initialize_episode(root, case_path, case_sha256)
        except (Exception, KeyboardInterrupt):  # noqa: BLE001 - any partial setup stays counted
            record.update(phase="setup_failed", setup_failure="bound episode initialization failed")
            body.utils.persist(episode_path, record)
            return public_episode(root, record)
        record["phase"] = "active"
        body.utils.persist(episode_path, record)
    # Native observation is deliberately discarded. Only task intent and opaque identity leave init.
    manifest, order, _, _ = body.load(root)
    result = public_episode(root, record)
    result.update(generation=manifest["generation"], state_sha256=manifest["state_sha256"],
                  task_intent={key: order[key] for key in ("order_id", "project", "part_id", "target_zone")},
                  calibration_valid=body.case_for(root)["scene"]["camera_offset_x_m"] == 0)
    return result


def finish(root, outcome, explanation_file, explanation_sha256, interventions=None):
    if outcome not in OUTCOMES or (interventions is not None and (type(interventions) is not int or interventions < 0)):
        raise Refusal("outcome or declared intervention count is invalid")
    if not isinstance(explanation_sha256, str) or not body.DIGEST.fullmatch(explanation_sha256):
        raise Refusal("explanation SHA256 must be exact lowercase hexadecimal")
    content = body.read_bytes(Path(explanation_file))
    if body.sha(content) != explanation_sha256:
        raise Refusal("explanation bytes do not match the bound digest")
    try:
        explanation = content.decode("utf-8")
    except UnicodeError as exc:
        raise Refusal("explanation must be UTF-8 text") from exc
    if not explanation.strip():
        raise Refusal("participant explanation must be nonempty")
    record = lifecycle(root)
    declaration = {"outcome": outcome, "explanation_path": str(Path(os.path.abspath(explanation_file))),
                   "explanation_sha256": explanation_sha256, "explanation": explanation,
                   "interventions_declared": interventions}
    if "finish" in record:
        retained = {key: value for key, value in record["finish"].items() if key != "finished_time_unix"}
        if retained != declaration:
            raise Refusal("episode already has a different finish declaration")
        if body.read_bytes(root / "participant-explanation.txt") != content:
            raise Refusal("retained participant explanation changed")
        return public_episode(root, record)
    body.create_file(root / "participant-explanation.txt", content)
    declaration["finished_time_unix"] = time.time()
    record.update(phase="finished", finish=declaration)
    body.utils.persist(root / "episode.json", record)
    return public_episode(root, record)


def doctor():
    checks = {"native_runtime_pinned": body.mujoco.__version__ == body.PINNED_VERSION,
              "numpy_available": True, "renderer": False, "footwork_checker": False}
    try:
        model = body.mujoco.MjModel.from_xml_path(str(body.SCENE))
        data = body.mujoco.MjData(model)
        body.mujoco.mj_forward(model, data)
        with body.mujoco.Renderer(model, height=360, width=640) as renderer:
            renderer.update_scene(data, camera="overview")
            checks["renderer"] = renderer.render().shape == (360, 640, 3)
    except Exception:  # noqa: BLE001 - readiness reports unavailable dependencies without native details
        checks["renderer"] = False
    try:
        rc, _, _ = body.utils.run_process([str(body.FOOTWORK), "check-artifact", "--help"], 20)
        checks["footwork_checker"] = rc == 0
    except Exception:  # noqa: BLE001
        checks["footwork_checker"] = False
    return {"source_kind": body.SOURCE_KIND, "phase": "ready" if all(checks.values()) else "unavailable",
            "checks": checks, "mujoco_version": body.mujoco.__version__,
            "scope": "dependency readiness only; no episode, persisted state, action or camera acquisition"}


def baseline(root, case_file, case_sha256):
    initial = initialize(root, case_file, case_sha256, "deterministic_rgb")
    record = lifecycle(root)
    if "finish" in record:
        return initial
    outcome, explanation = "unresolved", "RGB feedback action budget exhausted."
    if initial["phase"] == "setup_failed":
        outcome, explanation = "failed", "Bound episode setup failed."
    else:
        # Budget is public controller policy, not private case geometry or native pose feedback.
        for index in range(8):
            try:
                packet = vision.view(root)
                if packet.get("calibration", {}).get("valid") is not True:
                    explanation = "Acquired RGB image has invalid calibration; no motion admitted."
                    break
                perception = packet.get("perception", {})
                if not isinstance(perception, dict) or perception.get("state") != "recognized":
                    explanation = "Acquired RGB image has unavailable or ambiguous part recognition."
                    break
                block_box = perception["block_box"]
                block = [body.number(value) for value in perception["block_center_xy"]]
                pusher = [body.number(value) for value in perception["pusher_center_xy"]]
                zone, margin = packet["task_intent"]["target_zone"], vision.SETTINGS["completion_margin_m"]
                complete = (zone["x_min"] + margin <= block[0] <= zone["x_max"] - margin and
                            zone["y_min"] + margin <= block[1] <= zone["y_max"] - margin)
                proposal = {"version": 1, "run_dir": str(root), "generation": packet["generation"],
                            "image_sha256": packet["image_sha256"], "token": f"rgb-{index:03d}",
                            "block_box": block_box, "decision": "complete" if complete else "move"}
                if not complete:
                    remaining = packet.get("action_budget", {}).get("remaining")
                    if type(remaining) is not int or index == 7 or remaining <= 1:
                        break
                    # Aim toward the region center using current RGB displacement. The initial
                    # gap is also RGB-derived; no prerecorded target sequence is used.
                    displacement = (zone["x_min"] + zone["x_max"]) / 2 - block[0]
                    gap = max(0.0, block[0] - pusher[0] - .055)
                    forward = min(vision.SETTINGS["max_forward_m"] - .005, displacement + gap)
                    x = min(body.CONTROLLER["x_max"] - .005, pusher[0] + forward)
                    if (x - pusher[0] < vision.SETTINGS["min_forward_m"] or
                            abs(block[1]) > max(abs(zone["y_min"]), abs(zone["y_max"])) or displacement <= 0):
                        explanation = "RGB placement requires a motion outside the bounded forward controller."
                        break
                    proposal["target"] = {"x": x, "y": 0.0}
                content = body.encoded(proposal)
                path = root / f"baseline-proposal-{index:03d}.json"
                body.create_file(path, content)
                result = vision.apply(root, str(path), body.sha(content))
                if result["phase"] == "staged":
                    outcome, explanation = "completed", "Fresh RGB completion proposal received a staged software receipt."
                    break
                if result["phase"] != "executed":
                    explanation = "RGB proposal has an unresolved effect receipt."
                    break
            except (Refusal, OSError, ValueError, KeyError, TypeError):
                explanation = "RGB view or bounded proposal was refused; retained evidence requires review."
                break
            except (Exception, KeyboardInterrupt):  # noqa: BLE001 - retain unexpected driver failures as attempted episodes
                outcome, explanation = "failed", "RGB episode driver failed before supported completion."
                record = lifecycle(root)
                record["driver_failure"] = True
                body.utils.persist(root / "episode.json", record)
                break
    content = (explanation + "\n").encode()
    path = root / "baseline-explanation.txt"
    body.create_file(path, content)
    return finish(root, outcome, str(path), body.sha(content), interventions=0)


def generation_predicate(root, order, generation, expected_sha):
    """Restore a verified historical integration vector in memory, never in the manifest."""
    if type(generation) is not int or not 0 <= generation <= 999999:
        raise Refusal("historical generation is invalid")
    content = body.read_bytes(body.state_path(root, generation))
    if body.sha(content) != expected_sha:
        raise Refusal("historical verdict state digest changed")
    state = body.decoded(content)
    body.fields(state, ("source_kind", "state_spec", "values"), "historical integration state")
    model = body.model_for(root, order)
    spec = body.mujoco.mjtState.mjSTATE_INTEGRATION
    if (state["source_kind"] != body.SOURCE_KIND or state["state_spec"] != int(spec) or
            not isinstance(state["values"], list) or len(state["values"]) != body.mujoco.mj_stateSize(model, spec)):
        raise Refusal("historical integration vector is malformed")
    values = np.array([body.number(value) for value in state["values"]], dtype=np.float64)
    data = body.mujoco.MjData(model)
    body.mujoco.mj_setState(model, data, values, spec)
    body.mujoco.mj_forward(model, data)
    return body.poses(model, data, order)["block_center_in_zone"]


def evaluate(root):
    record = lifecycle(root)
    declared = record.get("finish", {})
    result = {"role": "parent_only_evaluator", "source_kind": body.SOURCE_KIND,
              "episode_id": record["episode_id"], "case_sha256": record["case_sha256"],
              "participant": record["participant"], "attempted": 1, "declared_outcome": declared.get("outcome"),
              "elapsed_s": (declared["finished_time_unix"] - record["started_time_unix"]) if declared else None,
              "interventions_declared": declared.get("interventions_declared"),
              "finished": bool(declared), "setup_failed": (record.get("setup_failure") is not None or
                                                           record["phase"] == "initializing"),
              "qualified_completion": False, "physical_condition": False, "current_software_ok": False,
              "action_count": 0, "motion_executed_count": 0, "contact_motion_count": 0,
              "driver_failed": record.get("driver_failure") is True, "refused_completion_count": 0,
              "historical_software_staged": False,
              "visual_completion_attempts": 0, "visual_positive_count": 0, "visual_false_positive_count": 0,
              "visual_verdicts": [], "evidence_errors": []}
    try:
        manifest, order, model, data = body.load(root)
        result["physical_condition"] = body.poses(model, data, order)["block_center_in_zone"]
        if manifest["phase"] == "completed":
            result["current_software_ok"] = body.artifact_check(root, manifest["result_sha256"])["ok"]
        native_motion = []
        native_staged = []
        for path in sorted(root.glob("op-*.json")):
            op = body.load_op(path)
            result["action_count"] += 1
            result["driver_failed"] |= op["phase"] in {"pending", "unknown"}
            if op["request"]["kind"] == "act":
                if op["phase"] == "executed":
                    generation_predicate(root, order, op["after_generation"], op["after_state_sha256"])
                    native_motion.append(op)
            elif (op["phase"] == "staged" and op.get("result_sha256") == manifest.get("result_sha256") and
                    generation_predicate(root, order, manifest["generation"], op["state_sha256"])):
                native_staged.append(op)
        result["motion_executed_count"] = len(native_motion)
        result["contact_motion_count"] = sum(
            op.get("controller_evidence", {}).get("pusher_block_contact_samples", 0) > 0 for op in native_motion)
        # Validate wrapper/native history independently of participant declarations.
        vision_staged = []
        for path in sorted(root.glob("vision-op-*.json")):
            receipt = vision.load_proposal_record(path)
            result["driver_failed"] |= receipt["phase"] in {"pending", "unknown"}
            if receipt["phase"] == "staged":
                vision_staged.append(receipt)
        result["historical_software_staged"] = bool(native_staged and vision_staged)
        for path in sorted(root.glob("vision-verdict-*.json")):
            try:
                verdict = body.decoded(body.read_bytes(path))
                scored = score_verdict(root, order, verdict, path, record)
                result["visual_verdicts"].append(scored)
                result["visual_completion_attempts"] += 1
                result["visual_positive_count"] += int(scored["visual_positive"])
                result["visual_false_positive_count"] += int(scored["visual_false_positive"])
                result["refused_completion_count"] += int(not scored["visual_positive"])
            except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
                result["evidence_errors"].append(str(exc))
        supported_visual_staging = any(
            scored["visual_positive"] and scored["bound_native_condition"] and
            any(scored["token"] == receipt["proposal"]["token"] and
                scored["generation"] == receipt["proposal"]["generation"] for receipt in vision_staged)
            for scored in result["visual_verdicts"])
        result["qualified_completion"] = bool(
            result["physical_condition"] and result["current_software_ok"] and
            result["historical_software_staged"] and supported_visual_staging and
            not body.unresolved(root, manifest) and not vision.wrapper_unresolved(root) and
            not result["evidence_errors"])
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        result["evidence_errors"].append(str(exc))
    result["incorrect_completion_claim"] = declared.get("outcome") == "completed" and not result["qualified_completion"]
    result["completed"] = int(declared.get("outcome") == "completed" and result["qualified_completion"])
    result["unresolved"] = int(not result["completed"] and not result["setup_failed"] and declared.get("outcome") != "failed")
    result["failed"] = int(result["setup_failed"] or declared.get("outcome") == "failed")
    return result


def score_verdict(root, order, verdict, path, record):
    # The exact packet schema is owned by image_guided; no final-state substitution is allowed.
    proposal = verdict["proposal"]
    if (proposal["decision"] != "complete" or
            path.name != "vision-verdict-" + body.sha(proposal["token"].encode()) + ".json" or
            verdict["binding"] != body.decoded(body.read_bytes(root / "vision-binding.json"))):
        raise Refusal("visual verdict identity or case/source binding is invalid")
    if verdict.get("case_binding") != verdict["binding"].get("case_binding"):
        raise Refusal("visual verdict case binding changed")
    image_path, view_path = vision.image_paths(root, proposal["generation"])
    view = body.decoded(body.read_bytes(view_path))
    if (verdict["state_sha256"] != view["state_sha256"] or
            verdict["generation"] != proposal["generation"] or
            proposal["image_sha256"] != view["image_sha256"] or
            body.sha(body.read_bytes(image_path)) != proposal["image_sha256"]):
        raise Refusal("visual verdict image/generation/state binding changed")
    if verdict.get("case_sha256", record["case_sha256"]) != record["case_sha256"]:
        raise Refusal("visual verdict case digest changed")
    actual = generation_predicate(root, order, proposal["generation"], verdict["state_sha256"])
    if verdict.get("before_oracle") is not True or type(verdict.get("visual_verdict")) not in (bool, type(None)):
        raise Refusal("visual verdict must durably precede the native oracle")
    if verdict["image_sha256"] != proposal["image_sha256"]:
        raise Refusal("visual verdict image digest changed")
    content = body.read_bytes(root / ("vision-request-" + body.sha(proposal["token"].encode()) + ".json"))
    if body.sha(content) != verdict["proposal_sha256"] or body.decoded(content) != proposal:
        raise Refusal("visual verdict proposal bytes changed")
    positive = verdict["visual_verdict"] is True
    return {"token": proposal["token"], "generation": proposal["generation"],
            "visual_positive": positive, "bound_native_condition": actual,
            "visual_false_positive": positive and not actual, "reason": verdict.get("reason")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    for command in ("init", "baseline", "finish", "evaluate"):
        child = sub.add_parser(command)
        child.add_argument("--run-dir", required=True)
        if command in {"init", "baseline"}:
            child.add_argument("--case-file", required=True)
            child.add_argument("--case-sha256", required=True)
        elif command == "finish":
            child.add_argument("--outcome", choices=sorted(OUTCOMES), required=True)
            child.add_argument("--explanation", required=True)
            child.add_argument("--explanation-sha256", required=True)
            child.add_argument("--interventions", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor()
        else:
            root = body.directory(args.run_dir, create=args.command in {"init", "baseline"})
            with body.utils.locked(root):
                if args.command == "init":
                    result = initialize(root, args.case_file, args.case_sha256)
                elif args.command == "baseline":
                    result = baseline(root, args.case_file, args.case_sha256)
                elif args.command == "finish":
                    result = finish(root, args.outcome, args.explanation, args.explanation_sha256, args.interventions)
                else:
                    result = evaluate(root)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 2 if result.get("phase") in {"unavailable", "setup_failed"} else 0
    except (Refusal, OSError, KeyError, TypeError, ValueError, AttributeError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else "episode input or retained evidence is malformed or unavailable"
        print(json.dumps({"source_kind": body.SOURCE_KIND, "phase": "refused", "reason": reason}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
