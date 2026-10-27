"""Independent post-trial native, SQLite, model-input and network receipt checks."""

import argparse
import json
from pathlib import Path

import agent_bench
import bench
import body_client
import order_protocol as protocol
import qualify_bench

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]


def read(path):
    return protocol.decode(protocol.read_bytes(path))


def private_fields(value):
    if isinstance(value, dict):
        return bool(set(value) & (agent_bench.DERIVED_LOCATION_FIELDS | {"qpos", "qvel", "values"})) or any(
            private_fields(item) for item in value.values())
    if isinstance(value, list):
        return any(private_fields(item) for item in value)
    return False


def score(root):
    root = protocol.directory(root)
    frozen = read(root / "source-freeze.json")
    unchanged = all(protocol.sha(protocol.read_bytes(REPO / name)) == digest for name, digest in frozen["files"].items())
    attempt = read(root / "attempt.json")
    identity = read(root / "identity.json")
    native_root = root / "body" / "bench"
    status = bench.Bench(native_root).status()
    initial_content = protocol.read_bytes(bench.body.state_path(native_root, 0))
    initial = qualify_bench.native_score(native_root, 0, protocol.sha(initial_content), bench.HOME_ZONE)
    database = qualify_bench.sqlite_score(native_root)
    agent_root = root / "body" / "agent"
    agent_manifest = read(agent_root / "agent.json")
    client_manifest = body_client.read_journal(root / "client" / "client.json")
    proxy_events = [read(path) for path in sorted((root / "proxy" / "events").glob("*.json"))]
    transport = []
    for directory in (root / "body" / "commands").iterdir():
        record = read(directory / "intent.json")
        request = record["request"]
        content = protocol.read_bytes(directory / "result.json")
        result = protocol.decode(content)
        valid = (record["request_sha256"] == protocol.sha(protocol.encoded(request)) == result["request_sha256"] and
                 record["result_sha256"] == protocol.sha(content) and
                 directory.name == protocol.sha(request["command_id"].encode()) and
                 all(result[key] == request[key] for key in ("protocol", "adapter_id", "body_id", "source_sha256", "command_id")))
        transport.append({"request": request, "result": result, "valid": valid})
    jobs, calls = [], []
    previous_generation, previous_time = 0, initial["native_time_s"]
    for item in attempt["jobs"]:
        job = status["jobs"].get(item["job_id"])
        if not job or job["phase"] != "completed":
            jobs.append({"job_id": item["job_id"], "passed": False})
            continue
        measurement, reset = job["measurement_receipt"], job["reset_receipt"]
        stage = qualify_bench.native_score(native_root, measurement["generation"], measurement["state_sha256"], job["target_zone"])
        home = qualify_bench.native_score(native_root, reset["generation"], reset["state_sha256"], bench.HOME_ZONE)
        rows = [row for row in database["rows"] if row["job_id"] == item["job_id"]]
        ok = bool(item["completed"] and len(rows) == 1 and rows[0]["receipt"] == measurement and
                  stage["block_center_in_zone"] and home["block_center_in_zone"] and home["pusher_home"] and
                  stage["external_force_cleared"] and home["external_force_cleared"] and
                  reset["reset_contact_samples"] > 0 and reset["reset_native_steps"] > 0 and
                  reset["bench_id"] == measurement["bench_id"] == identity["body_id"] == status["bench_id"] and
                  job["started_generation"] == previous_generation and
                  job["started_native_time_s"] == previous_time)
        jobs.append({"job_id": item["job_id"], "passed": ok, "measurement_state": stage,
                     "reset_state": home, "measurement_receipt": measurement, "reset_receipt": reset,
                     "motion_count": job["moves"], "model_calls": item["calls"]})
        previous_generation, previous_time = job["completed_generation"], job["completed_native_time_s"]
    for directory in sorted((root / "calls").iterdir()):
        reservation = read(directory / "reservation.json")
        challenge = reservation["challenge"]
        image_sha = challenge["observation"]["image_sha256"]
        image_path = Path(challenge["image_path"])
        downloaded = root / "client" in image_path.parents
        exact = downloaded and protocol.sha(protocol.read_bytes(image_path, maximum=1024 * 1024)) == image_sha
        exact &= protocol.sha(protocol.read_bytes(directory / "input.png", maximum=1024 * 1024)) == image_sha
        image_requests = [event for event in proxy_events if event["kind"] == "received" and
                          event.get("path") == "/images/" + challenge["challenge_id"] and event.get("method") == "GET"]
        exact &= len(image_requests) == 1
        prompt = json.loads(protocol.read_bytes(directory / "prompt.txt").decode().split("\n", 1)[1])
        proposal = read(directory / "proposal.json")
        content = protocol.read_bytes(agent_root / "proposals" / (proposal["proposal_id"] + ".json"))
        lower_proposal = protocol.decode(content)
        bound = protocol.sha(content) == agent_manifest["proposals"][proposal["proposal_id"]] and lower_proposal == proposal
        content = protocol.read_bytes(agent_root / "results" / (proposal["proposal_id"] + ".json"))
        lower_result = protocol.decode(content)
        bound &= protocol.sha(content) == agent_manifest["results"][proposal["proposal_id"]]
        bound &= agent_bench.public_response(lower_result) == read(directory / "dispatch.json")
        decision = read(directory / "decision.json")["action"]
        bound &= all(proposal[key] == decision[key] for key in ("action", "intent", "target_x", "target_y"))
        bound &= proposal["challenge_id"] == challenge["challenge_id"] and proposal["observation_sha256"] == challenge["observation_sha256"]
        dispatch_commands = [t for t in transport if t["request"]["operation"] == "dispatch" and
                             t["request"]["arguments"]["proposal_id"] == proposal["proposal_id"]]
        bound &= len(dispatch_commands) == 1 and dispatch_commands[0]["valid"] and (
            dispatch_commands[0]["result"]["result"] == agent_bench.public_response(lower_result))
        network_bound = False
        if len(dispatch_commands) == 1:
            request = dispatch_commands[0]["request"]
            command_id = request["command_id"]
            received = [event for event in proxy_events if event["kind"] == "received" and event.get("command_id") == command_id]
            local_request = read(root / "client" / "requests" / (command_id + ".json"))
            network_bound = len(received) == 1 and local_request == request and client_manifest["commands"][command_id]["send_count"] == 1
            if received:
                sent = protocol.read_bytes(root / "proxy" / "requests" / f"{received[0]['sequence']:06d}.bin")
                network_bound &= protocol.decode(sent) == request and protocol.sha(sent) == received[0]["payload_sha256"]
        model = read(directory / "outcome.json")
        reconciled = None
        if (directory / "reconciliation.json").exists():
            reconciled = read(directory / "reconciliation.json")
            bound &= reconciled["state"] == "completed" and reconciled["result"] == agent_bench.public_response(lower_result)
            bound &= len(dispatch_commands) == 1 and dispatch_commands[0]["result"] == reconciled
        calls.append({"job_id": reservation["job_id"], "call": reservation["call"], "exact_TCP_image": bool(exact),
                      "no_private_pose": not private_fields(reservation) and not private_fields(prompt),
                      "model_process_reaped": model.get("process_exit_observed", False), "core_receipt_bound": bool(bound),
                      "one_client_send_bound": bool(network_bound),
                      "action": decision["action"], "outcome": lower_result["outcome"],
                      "usage": model.get("usage"), "reconciled_command_id": reconciled["command_id"] if reconciled else None})
    model_ok = bool(calls and all(c["exact_TCP_image"] and c["no_private_pose"] and c["model_process_reaped"] and
                                c["core_receipt_bound"] and c["one_client_send_bound"] for c in calls))
    faults_ok = any(f["mode"] == "drop_after" and f.get("read_only") and f["reconciled_state"] == "completed" for f in attempt["faults"])
    passed = bool(unchanged and attempt["passed"] and attempt["service_exit_observed"] and
                  len(jobs) == database["count"] == 2 and all(j["passed"] for j in jobs) and model_ok and faults_ok and
                  transport and all(t["valid"] for t in transport) and not client_manifest["pending_command_ids"] and
                  status["state"] == "ready" and status["active_job"] is None)
    result = {"passed": passed, "source_unchanged": unchanged, "source_commit": frozen["commit"],
              "scope": "loopback TCP simulation, actual Codex image policy, independent post-trial native/SQLite checks",
              "body_id": identity["body_id"], "completed_cycles": sum(j["passed"] for j in jobs),
              "model_boundaries_passed": model_ok, "lost_reply_reconciled": faults_ok,
              "transport_journal_bound": all(t["valid"] for t in transport), "transport_command_count": len(transport),
              "scores": jobs, "sqlite": database, "calls": calls, "faults": attempt["faults"]}
    protocol.create_file(root / "qualification-score.json", protocol.encoded(result))
    return {key: result[key] for key in ("passed", "source_unchanged", "completed_cycles", "model_boundaries_passed", "lost_reply_reconciled")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    print(json.dumps(score(parser.parse_args().root), sort_keys=True))


if __name__ == "__main__":
    main()
