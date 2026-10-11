"""Separate post-trial native/SQLite scoring; never supplies AI action guidance."""

import argparse
import json
import subprocess
from pathlib import Path

import bench
import qualify_bench
import workcell as body

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
SOURCES = [BASE / name for name in (
    "agent_bench.py", "score_agent_bench.py", "bench.py", "measurement.py", "workcell.py",
    "image_guided.py", "episode_cases.py", "order_protocol.py", "scene.xml", "qualify_bench.py")]
SOURCES.append(BASE.parent / "camera-capture-experiment" / "capture.py")


def freeze(root, commit):
    root = body.directory(root, create=True)
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != commit:
        raise body.Refusal("trial must start at the named source commit")
    files = {}
    for path in SOURCES:
        relative = str(path.relative_to(REPO))
        content = body.read_bytes(path)
        if subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=REPO) != content:
            raise body.Refusal("measured source differs from its frozen commit")
        files[relative] = body.sha(content)
    body.create_file(root / "source-freeze.json", body.encoded({"commit": commit, "files": files}))
    initial = bench.initialize(root / "bench", diagnostic_enabled=True)
    body.create_file(root / "initial.json", body.encoded(initial))
    return {"source_commit": commit, "bench_id": initial["bench_id"], "native_time_s": initial["native_time_s"]}


def score(root):
    root = body.directory(root)
    frozen = body.decoded(body.read_bytes(root / "source-freeze.json"))
    assert all(body.sha(body.read_bytes(REPO / name)) == digest for name, digest in frozen["files"].items())
    initial = body.decoded(body.read_bytes(root / "initial.json"))
    status = bench.Bench(root / "bench").status()
    database = qualify_bench.sqlite_score(root / "bench")
    passed = status["state"] == "ready" and status["active_job"] is None and len(status["jobs"]) == database["count"] == 2
    scores = []
    for index, name in enumerate(("ai-ordinary", "ai-disturbed")):
        job = status["jobs"].get(name)
        if job is None:
            passed = False
            continue
        measurement = job["measurement_receipt"]
        reset = job["reset_receipt"]
        stage = qualify_bench.native_score(root / "bench", measurement["generation"],
                                           measurement["state_sha256"], job["target_zone"])
        home = qualify_bench.native_score(root / "bench", reset["generation"], reset["state_sha256"], bench.HOME_ZONE)
        row = next(row for row in database["rows"] if row["job_id"] == name)
        previous_generation = 0 if index == 0 else status["jobs"]["ai-ordinary"]["completed_generation"]
        previous_time = initial["native_time_s"] if index == 0 else status["jobs"]["ai-ordinary"]["completed_native_time_s"]
        ok = bool(stage["block_center_in_zone"] and home["block_center_in_zone"] and home["pusher_home"] and
                  stage["external_force_cleared"] and home["external_force_cleared"] and
                  row["receipt"] == measurement and reset["reset_contact_samples"] > 0 and reset["reset_native_steps"] > 0 and
                  reset["bench_id"] == measurement["bench_id"] == initial["bench_id"] == status["bench_id"] and
                  job["started_generation"] == previous_generation and job["started_native_time_s"] == previous_time)
        scores.append({"job_id": name, "passed": ok, "measurement_state": stage, "reset_state": home,
                       "measurement": measurement, "reset": reset, "motion_count": job["moves"]})
        passed &= ok
    result = {"version": 1, "passed": passed, "source_commit": frozen["commit"], "source_unchanged": True,
              "bench_id": initial["bench_id"], "completed_cycles": len(scores), "scores": scores,
              "sqlite": database, "current_status": status, "attempt": 1,
              "scope": "native/SQLite post-trial scoring; AI image consumption/proposals are separately recorded in the session"}
    body.create_file(root / "native-sqlite-score.json", body.encoded(result))
    return {k: result[k] for k in ("passed", "completed_cycles", "source_unchanged", "bench_id")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "score"))
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    print(json.dumps(freeze(args.run_dir, args.source_commit) if args.command == "freeze" else score(args.run_dir), sort_keys=True))


if __name__ == "__main__":
    main()
