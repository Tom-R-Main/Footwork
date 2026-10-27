"""Post-trial native, SQLite and model-boundary scorer; never guides the policy."""
import argparse
import json
import math
import subprocess
from pathlib import Path

import agent_bench
import bench
import operator_runtime as runtime
import order_protocol as protocol
import qualify_bench

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
NAMES = ("bench_operator.py", "bench_operator.html", "operator_runtime.py", "codex_policy.py",
         "codex-policy.md", "codex-action.schema.json", "agent_bench.py", "bench.py", "measurement.py",
         "workcell.py", "image_guided.py", "episode_cases.py", "order_protocol.py", "scene.xml",
         "qualify_bench.py", "score_operator.py")


def freeze(root, commit):
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != commit:
        raise protocol.Refusal("qualification must start at the named source commit")
    files = {}
    for path in [*(BASE / name for name in NAMES), BASE.parent / "camera-capture-experiment" / "capture.py"]:
        relative = str(path.relative_to(REPO))
        content = protocol.read_bytes(path)
        if subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=REPO) != content:
            raise protocol.Refusal("measured source differs from its frozen commit")
        files[relative] = protocol.sha(content)
    runtime.initialize(root)
    root = protocol.directory(root)
    protocol.create_file(root / "source-freeze.json", protocol.encoded({"commit": commit, "files": files, "qualification_version": 2}))
    protocol.create_file(root / "initial.json", protocol.encoded(bench.Bench(root / "bench").status()))
    return {"source_commit": commit, "root": str(root)}


def private_fields(value):
    if isinstance(value, dict):
        return bool(agent_bench.DERIVED_LOCATION_FIELDS.intersection(value)) or any(private_fields(v) for v in value.values())
    return isinstance(value, list) and any(private_fields(v) for v in value)


def fault_score(root, calls):
    read = lambda path: protocol.decode(protocol.read_bytes(path))
    native, agent = read(root / "bench/bench.json"), read(root / "agent/agent.json")
    forces = []
    for path in (root / "bench/operations").glob("*.json"):
        content = protocol.read_bytes(path)
        value = protocol.decode(content)
        if value["request"].get("kind") == "disturb":
            receipt = value["receipt"]
            if native["operations"].get(receipt["operation_id"]) != protocol.sha(content):
                raise protocol.Refusal("force receipt differs from retained native operation")
            forces.append(value)
    if len(forces) != 1:
        return {"passed": False, "reason": "expected exactly one native force intervention"}
    force = forces[0]
    receipt = force["receipt"]
    stale = next((c for c in calls if c["job_id"] == receipt["job_id"] and c.get("outcome") == "refused" and
                  c.get("decision", {}).get("action") == "measure" and
                  c.get("reason") == "observation is stale or foreign; no requested effect dispatched"), None)
    if stale is None:
        return {"passed": False, "reason": "exact stale measurement refusal absent"}
    directory = Path(stale["call_dir"])
    proposal, dispatch = read(directory / "proposal.json"), read(directory / "dispatch.json")
    challenge = read(directory / "reservation.json")["challenge"]
    after = dispatch["next_observation"]["observation"]
    before = challenge["observation"]
    bound = proposal["challenge_id"] == challenge["challenge_id"] and proposal["observation_sha256"] == challenge["observation_sha256"]
    for kind, token, value in (("proposals", proposal["proposal_id"], proposal),
                               ("challenges", challenge["challenge_id"], challenge),
                               ("results", proposal["proposal_id"], dispatch)):
        content = protocol.read_bytes(root / "agent" / kind / (token + ".json"))
        bound &= agent[kind].get(token) == protocol.sha(content) and agent_bench.public_response(protocol.decode(content)) == value
    zone = challenge["task"]["zone"]
    before_state = qualify_bench.native_score(root / "bench", before["generation"], before["state_sha256"], zone)
    after_state = qualify_bench.native_score(root / "bench", receipt["generation"], receipt["state_sha256"], zone)
    displacement = math.dist(before_state["block_xyz"], after_state["block_xyz"])
    no_measurement_effect = proposal["operation_id"] not in native["operations"] and not (
        root / "bench/operations" / (protocol.sha(proposal["operation_id"].encode()) + ".json")).exists()
    fresh_move = next((c for c in calls if c["job_id"] == receipt["job_id"] and c["call"] > stale["call"] and
                       c.get("outcome") == "executed" and c.get("decision", {}).get("action") == "move"), None)
    fresh_binding = False
    if fresh_move:
        fresh = read(Path(fresh_move["call_dir"]) / "reservation.json")["challenge"]["observation"]
        fresh_binding = fresh == after and fresh_move["image_sha256"] == after["image_sha256"]
    passed = bool(bound and no_measurement_effect and fresh_binding and displacement > .02 and
                  before_state["block_center_in_zone"] and not after_state["block_center_in_zone"] and
                  receipt["generation"] == before["generation"] + 1 == after["generation"] and
                  receipt["state_sha256"] == after["state_sha256"] and
                  receipt["bench_id"] == before["bench_id"] == after["bench_id"] == native["bench_id"] and
                  receipt["job_id"] == before["job_id"] == after["job_id"] and
                  force["request"] == {"kind": "disturb", "force_x_n": -1.5, "steps": 80} and
                  receipt["force_x_n"] == -1.5 and receipt["forced_steps"] == 80 and receipt["native_steps"] == 580 and
                  after_state["external_force_cleared"] and after_state["native_time_s"] > before_state["native_time_s"])
    return {"passed": passed, "force": force, "displacement_m": displacement,
            "before": before_state, "after": after_state, "saved_proposal_id": proposal["proposal_id"],
            "immutable_chain_bound": bool(bound), "no_measurement_effect": no_measurement_effect,
            "fresh_model_move_bound_to_force_image": bool(fresh_binding), "stale_call": stale["call"]}


def score(root):
    root = protocol.directory(root)
    read = lambda path: protocol.decode(protocol.read_bytes(path))
    frozen, initial = read(root / "source-freeze.json"), read(root / "initial.json")
    unchanged = all(protocol.sha(protocol.read_bytes(REPO / name)) == digest for name, digest in frozen["files"].items())
    operator = read(root / "operator.json")
    status = bench.Bench(root / "bench").status()
    database = qualify_bench.sqlite_score(root / "bench")
    scores, calls = [], []
    previous_generation, previous_time = initial["generation"], initial["native_time_s"]
    for item in operator["jobs"]:
        job = status["jobs"].get(item["id"])
        if not job or job["phase"] != "completed":
            scores.append({"job_id": item["id"], "passed": False, "reason": "cycle not completed"})
            continue
        measurement, reset = job["measurement_receipt"], job["reset_receipt"]
        stage = qualify_bench.native_score(root / "bench", measurement["generation"], measurement["state_sha256"], job["target_zone"])
        home = qualify_bench.native_score(root / "bench", reset["generation"], reset["state_sha256"], bench.HOME_ZONE)
        rows = [row for row in database["rows"] if row["job_id"] == item["id"]]
        passed = bool(item["status"] == "completed" and len(rows) == 1 and rows[0]["receipt"] == measurement and
                      item["measurement"] == agent_bench.public_response(measurement["measurement"]) and
                      stage["block_center_in_zone"] and home["block_center_in_zone"] and home["pusher_home"] and
                      stage["external_force_cleared"] and home["external_force_cleared"] and
                      reset["reset_contact_samples"] > 0 and reset["reset_native_steps"] > 0 and
                      reset["bench_id"] == measurement["bench_id"] == initial["bench_id"] == status["bench_id"] and
                      job["started_generation"] == previous_generation and job["started_native_time_s"] == previous_time)
        scores.append({"job_id": item["id"], "label": item["label"], "passed": passed,
                       "measurement_state": stage, "reset_state": home, "measurement": measurement,
                       "reset": reset, "motion_count": job["moves"], "model_calls": item["call_count"]})
        previous_generation, previous_time = job["completed_generation"], job["completed_native_time_s"]
    for directory in sorted(p for p in (root / "calls").iterdir() if p.is_dir()):
        reservation = read(directory / "reservation.json")
        record = {"job_id": reservation["job_id"], "call": reservation["call"], "call_dir": str(directory),
                  "image_sha256": reservation["challenge"]["observation"]["image_sha256"],
                  "input_has_no_private_pose": not private_fields(reservation)}
        if (directory / "outcome.json").exists():
            record["process"] = read(directory / "outcome.json")
        if (directory / "input.png").exists():
            record["exact_image"] = protocol.sha(protocol.read_bytes(directory / "input.png", maximum=1024 * 1024)) == record["image_sha256"]
            prompt = protocol.read_bytes(directory / "prompt.txt").decode().split("\n", 1)[1]
            record["input_has_no_private_pose"] &= not private_fields(json.loads(prompt))
        if (directory / "decision.json").exists():
            record["decision"] = read(directory / "decision.json")["action"]
        if (directory / "dispatch.json").exists():
            dispatch = read(directory / "dispatch.json")
            record.update(outcome=dispatch["outcome"], reason=dispatch.get("reason", ""))
        calls.append(record)
    disturbance_job = next((j["id"] for j in operator["jobs"] if j["disturbance_test"]), None)
    stale = next((c for c in calls if c["job_id"] == disturbance_job and c.get("outcome") == "refused" and
                  c.get("decision", {}).get("action") == "measure"), None)
    recovery = bool(stale and any(c["job_id"] == disturbance_job and c["call"] > stale["call"] and
                    c.get("outcome") == "executed" and c.get("decision", {}).get("action") == "move" for c in calls))
    model_boundaries = bool(calls and all(c.get("exact_image") and c["input_has_no_private_pose"] and
                              c.get("process", {}).get("process_exit_observed") for c in calls))
    fault = fault_score(root, calls)
    passed = bool(unchanged and len(scores) == database["count"] == 2 and all(s["passed"] for s in scores) and
                  status["state"] == "ready" and status["active_job"] is None and recovery and model_boundaries and fault["passed"])
    result = {"version": 1, "attempt": 1, "passed": passed, "source_commit": frozen["commit"],
              "source_unchanged": unchanged, "bench_id": status["bench_id"], "completed_cycles": sum(s["passed"] for s in scores),
              "qualification_version": frozen.get("qualification_version", 1),
              "stale_measure_refused": stale is not None, "fresh_model_move_after_refusal": recovery, "fault_chain": fault,
              "model_boundaries_passed": model_boundaries, "scores": scores, "sqlite": database, "calls": calls,
              "usage": operator["usage"], "current_status": status,
              "scope": "separate post-trial native/SQLite and retained model-boundary scoring; browser evidence recorded separately"}
    protocol.create_file(root / "qualification-score.json", protocol.encoded(result))
    return {k: result[k] for k in ("passed", "completed_cycles", "source_unchanged", "stale_measure_refused", "fresh_model_move_after_refusal")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "score"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    print(json.dumps(freeze(args.root, args.source_commit) if args.command == "freeze" else score(args.root), sort_keys=True))


if __name__ == "__main__":
    main()
