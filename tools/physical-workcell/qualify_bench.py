"""Frozen SIM6 public-interface trial with separate native/SQLite scoring."""

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import time
import traceback
from pathlib import Path

import bench
import workcell as body

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
SOURCES = [BASE / name for name in (
    "bench.py", "measurement.py", "bench_runner.py", "qualify_bench.py", "workcell.py",
    "image_guided.py", "episode_cases.py", "order_protocol.py", "scene.xml")]
SOURCES.append(BASE.parent / "camera-capture-experiment" / "capture.py")


def retain(path, value):
    body.create_file(path, body.encoded(value))


def source_snapshot(commit):
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != commit:
        raise AssertionError("qualification must start at the named source commit")
    snapshot = {}
    for path in SOURCES:
        relative = str(path.relative_to(REPO))
        frozen = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=REPO)
        current = body.read_bytes(path)
        if frozen != current:
            raise AssertionError(f"source differs from named freeze: {relative}")
        snapshot[relative] = hashlib.sha256(current).hexdigest()
    return snapshot


def native_score(root, generation, state_sha256, zone):
    # Separate scorer only: never imported or invoked by the RGB host.
    content = body.read_bytes(body.state_path(root, generation))
    if body.sha(content) != state_sha256:
        raise AssertionError("scored state digest differs from receipt")
    state = body.decoded(content)
    model = body.mujoco.MjModel.from_xml_path(str(root / "model.xml"))
    data = body.mujoco.MjData(model)
    body.mujoco.mj_setState(model, data, body.np.asarray(state["values"]), body.mujoco.mjtState.mjSTATE_INTEGRATION)
    body.mujoco.mj_forward(model, data)
    block = data.xpos[model.body("block").id].tolist()
    pusher = data.xpos[model.body("pusher").id].tolist()
    return {"role": "independent_native_state_scorer", "generation": generation,
            "state_sha256": state_sha256, "native_time_s": float(data.time), "block_xyz": block,
            "pusher_xyz": pusher, "block_center_in_zone": bool(
                zone["x_min"] <= block[0] <= zone["x_max"] and
                zone["y_min"] <= block[1] <= zone["y_max"] and .02 <= block[2] <= .08),
            "pusher_home": abs(pusher[0] + .3) <= .005 and abs(pusher[1]) <= .005,
            "external_force_cleared": bool(not body.np.any(data.xfrc_applied))}


def sqlite_score(root):
    with sqlite3.connect((root / "measurements.sqlite").as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute("SELECT * FROM measurements ORDER BY job_id")]
    for row in rows:
        row["receipt"] = json.loads(row.pop("receipt_json"))
    return {"role": "independent_read_only_sqlite_scorer", "count": len(rows), "rows": rows}


def score_job(root, journal, result, expected_count, expected_bench_id):
    measurement = result["measurement"]["measurement_receipt"]
    reset = result["reset"]
    stage = native_score(root, measurement["generation"], measurement["state_sha256"],
                         {"x_min": .035, "x_max": .105, "y_min": -.025, "y_max": .025})
    home = native_score(root, reset["generation"], reset["state_sha256"], bench.HOME_ZONE)
    database = sqlite_score(root)
    row = next(row for row in database["rows"] if row["job_id"] == result["job_id"])
    assert row["receipt"] == measurement and database["count"] == expected_count
    assert stage["block_center_in_zone"] and home["block_center_in_zone"] and home["pusher_home"]
    assert stage["external_force_cleared"] and home["external_force_cleared"]
    assert measurement["bench_id"] == reset["bench_id"] == expected_bench_id
    assert home["native_time_s"] > stage["native_time_s"]
    events = [body.decoded(body.read_bytes(path)) for path in sorted(journal.glob("event-*.json"))]
    motions = [event for event in events if event["kind"] == "motion"]
    contact_reset = [event for event in motions if event["purpose"] == "contact_reset"]
    contact_samples = sum(event["receipt"]["pusher_block_contact_samples"] for event in contact_reset)
    assert contact_samples > 0
    steps = sum(event["receipt"]["native_steps"] for event in motions)
    assert steps > 0 and all(event["receipt"]["max_axis_actuator_force_n"] <= 4.00000001 for event in motions)
    assert measurement["worker_pid"] != os.getpid()
    if result["recovery"]:
        assert result["recovery"]["stale_refused"] == ["move", "measure"]
        assert result["recovery"]["rgb_displacement_m"] >= .02
        recovery_moves = [event for event in motions if event["purpose"] == "recover_unexpected_displacement"]
        assert recovery_moves and sum(e["receipt"]["pusher_block_contact_samples"] for e in recovery_moves) > 0
    observations = [event["packet"] for event in events if event["kind"] == "rgb_observation"]
    private_keys = {"block_xyz", "pusher_xyz", "qpos", "qvel", "native_pose"}
    assert all(not private_keys.intersection(packet) for packet in observations)
    return {"job_id": result["job_id"], "measurement_state": stage, "reset_state": home,
            "sqlite": database, "motion_count": len(motions), "native_motion_steps": steps,
            "reset_contact_samples": contact_samples, "recovery": result["recovery"],
            "planner_role": "frozen_deterministic_color_RGB_host", "passed": True}


def run(root, commit):
    source = source_snapshot(commit)
    root = body.directory(root, create=True)
    retain(root / "source-freeze.json", {"commit": commit, "files": source})
    bench_root = root / "bench"
    initialized = bench.initialize(bench_root, diagnostic_enabled=True)
    retain(root / "initialized.json", initialized)
    scores, attempts = [], []
    try:
        for index, name in enumerate(("ordinary", "disturbed"), 1):
            journal = root / (name + "-journal")
            command = [str(BASE / ".venv/bin/python"), str(BASE / "bench_runner.py"),
                       "--bench-dir", str(bench_root), "--journal-dir", str(journal), "--job-id", name]
            if name == "disturbed":
                command.append("--disturb")
            before = bench.Bench(bench_root).status()
            started = time.monotonic()
            process = subprocess.run(command, capture_output=True, timeout=240, check=False)
            body.create_file(root / (name + ".stdout.json"), process.stdout)
            body.create_file(root / (name + ".stderr.log"), process.stderr)
            attempt = {"job_id": name, "attempt": 1, "returncode": process.returncode,
                       "elapsed_s": time.monotonic() - started, "before": before,
                       "all_caller_and_worker_processes_synchronous": True}
            attempts.append(attempt)
            retain(root / (name + "-attempt.json"), attempt)
            if process.returncode != 0:
                raise AssertionError(f"{name} failed; original stderr/stdout and partial journal retained")
            result = body.decoded(process.stdout)
            after = bench.Bench(bench_root).status()
            assert after["bench_id"] == initialized["bench_id"] and after["active_job"] is None
            assert after["generation"] > before["generation"] and after["native_time_s"] > before["native_time_s"]
            current_job = after["jobs"][name]
            assert current_job["started_generation"] == before["generation"]
            assert current_job["started_native_time_s"] == before["native_time_s"]
            score = score_job(bench_root, journal, result, index, initialized["bench_id"])
            score["continuity"] = {"before": before, "after": after}
            scores.append(score)
            retain(root / (name + "-score.json"), score)
        unchanged = source_snapshot(commit) == source
        assert unchanged
        summary = {"version": 1, "source_commit": commit, "source_unchanged": unchanged,
                   "bench_id": initialized["bench_id"], "successful_cycles": len(scores), "required_cycles": 2,
                   "attempts": attempts, "scores": scores, "passed": True,
                   "limits": "deterministic RGB policy; axial force disturbance; simulation; no hardware or model trial"}
    except Exception as exc:
        summary = {"version": 1, "source_commit": commit, "passed": False, "attempts": attempts,
                   "scores": scores, "error": str(exc), "traceback": traceback.format_exc()}
        retain(root / "qualification.json", summary)
        raise
    retain(root / "qualification.json", summary)
    return {key: summary[key] for key in ("passed", "source_commit", "bench_id", "successful_cycles", "source_unchanged")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.source_commit), sort_keys=True))


if __name__ == "__main__":
    main()
