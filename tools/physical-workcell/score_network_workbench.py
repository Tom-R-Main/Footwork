"""Post-trial checks independent of the browser planner and displayed verdicts."""

import argparse
import json
from pathlib import Path

import agent_bench
import bench
import body_client
import order_protocol as protocol
import qualify_bench
from score_network_body import private_fields

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]


def read(path):
    return protocol.decode(protocol.read_bytes(path))


def score(root):
    root = protocol.directory(root)
    host_root = root / "operator"
    frozen = read(root / "source-freeze.json")
    unchanged = all(protocol.sha(protocol.read_bytes(REPO / name)) == digest
                    for name, digest in frozen["files"].items())
    process_ledger = read(root / "process-ledger.json")
    public = read(root / "final-public.json")
    identity = read(root / "identity.json")
    native_root = root / "body" / "bench"
    native = bench.Bench(native_root).status()
    sqlite = qualify_bench.sqlite_score(native_root)
    client = body_client.read_journal(host_root / "client" / "client.json")
    agent_root = root / "body" / "agent"
    agent_manifest = read(agent_root / "agent.json")
    events = [read(path) for path in sorted((host_root / "link" / "events").glob("*.json"))]
    transport = {}
    for directory in (root / "body" / "commands").iterdir():
        record = read(directory / "intent.json")
        request = record["request"]
        content = protocol.read_bytes(directory / "result.json")
        result = protocol.decode(content)
        valid = (record["request_sha256"] == protocol.sha(protocol.encoded(request)) == result["request_sha256"] and
                 record["result_sha256"] == protocol.sha(content) and
                 directory.name == protocol.sha(request["command_id"].encode()) and
                 all(result[key] == request[key] for key in (
                     "protocol", "adapter_id", "body_id", "source_sha256", "command_id")))
        transport[request["command_id"]] = {"request": request, "result": result, "valid": valid}

    jobs = []
    previous_generation = 0
    initial_content = protocol.read_bytes(bench.body.state_path(native_root, 0))
    previous_time = qualify_bench.native_score(native_root, 0, protocol.sha(initial_content), bench.HOME_ZONE)["native_time_s"]
    for item in public["jobs"]:
        job_id = item["job_id"]
        job = native["jobs"].get(job_id)
        if not job or job["phase"] != "completed":
            jobs.append({"job_id": job_id, "passed": False})
            continue
        measurement, reset = job["measurement_receipt"], job["reset_receipt"]
        stage = qualify_bench.native_score(native_root, measurement["generation"],
                                          measurement["state_sha256"], job["target_zone"])
        home = qualify_bench.native_score(native_root, reset["generation"], reset["state_sha256"], bench.HOME_ZONE)
        rows = [row for row in sqlite["rows"] if row["job_id"] == job_id]
        ok = bool(item["status"] == "completed" and len(rows) == 1 and rows[0]["receipt"] == measurement and
                  item["measurement"] == agent_bench.public_response(measurement["measurement"]) and
                  stage["block_center_in_zone"] and home["block_center_in_zone"] and home["pusher_home"] and
                  stage["external_force_cleared"] and home["external_force_cleared"] and
                  reset["reset_contact_samples"] > 0 and reset["reset_native_steps"] > 0 and
                  reset["bench_id"] == measurement["bench_id"] == identity["body_id"] == native["bench_id"] and
                  job["started_generation"] == previous_generation and job["started_native_time_s"] == previous_time)
        jobs.append({"job_id": job_id, "passed": ok, "measurement_state": stage, "reset_state": home,
                     "measurement_receipt": measurement, "reset_receipt": reset,
                     "motion_count": job["moves"], "model_calls": item["call_count"]})
        previous_generation, previous_time = job["completed_generation"], job["completed_native_time_s"]

    calls = []
    for directory in sorted(path for path in (host_root / "calls").iterdir() if path.is_dir()):
        reservation = read(directory / "reservation.json")
        challenge = reservation["challenge"]
        digest = challenge["observation"]["image_sha256"]
        image_path = Path(challenge["image_path"])
        exact = (host_root / "client" in image_path.parents and
                 protocol.sha(protocol.read_bytes(image_path, maximum=1024 * 1024)) == digest and
                 protocol.sha(protocol.read_bytes(directory / "input.png", maximum=1024 * 1024)) == digest)
        image_requests = [e for e in events if e["kind"] == "received" and e.get("method") == "GET" and
                          e.get("path") == "/images/" + challenge["challenge_id"]]
        exact &= bool(image_requests)
        prompt = json.loads(protocol.read_bytes(directory / "prompt.txt").decode().split("\n", 1)[1])
        model = read(directory / "outcome.json")
        bound, one_send, action = False, False, None
        missing_dispatch = not (directory / "dispatch.json").exists()
        associated_dispatches = []
        if (directory / "proposal.json").exists():
            candidate = read(directory / "proposal.json")
            associated_dispatches = [t for t in transport.values() if t["request"]["operation"] == "dispatch" and
                                     t["request"]["arguments"]["proposal_id"] == candidate["proposal_id"]]
        withheld = missing_dispatch and model.get("outcome") == "cancelled" and not associated_dispatches
        if not missing_dispatch:
            proposal = read(directory / "proposal.json")
            decision = read(directory / "decision.json")["action"]
            action = decision["action"]
            pbytes = protocol.read_bytes(agent_root / "proposals" / (proposal["proposal_id"] + ".json"))
            rbytes = protocol.read_bytes(agent_root / "results" / (proposal["proposal_id"] + ".json"))
            lower_result = read(agent_root / "results" / (proposal["proposal_id"] + ".json"))
            bound = (protocol.sha(pbytes) == agent_manifest["proposals"][proposal["proposal_id"]] and
                     protocol.decode(pbytes) == proposal and
                     protocol.sha(rbytes) == agent_manifest["results"][proposal["proposal_id"]] and
                     agent_bench.public_response(lower_result) == read(directory / "dispatch.json") and
                     all(proposal[k] == decision[k] for k in ("action", "intent", "target_x", "target_y")) and
                     proposal["challenge_id"] == challenge["challenge_id"] and
                     proposal["observation_sha256"] == challenge["observation_sha256"])
            matches = [t for t in transport.values() if t["request"]["operation"] == "dispatch" and
                       t["request"]["arguments"]["proposal_id"] == proposal["proposal_id"]]
            bound &= len(matches) == 1 and matches[0]["valid"] and (
                matches[0]["result"]["result"] == agent_bench.public_response(lower_result))
            if len(matches) == 1:
                request = matches[0]["request"]
                token = request["command_id"]
                received = [e for e in events if e["kind"] == "received" and e.get("method") == "POST" and
                            e.get("command_id") == token]
                one_send = (len(received) == 1 and read(host_root / "client" / "requests" / (token + ".json")) == request and
                            client["commands"][token]["send_count"] == 1)
                if received:
                    sent = protocol.read_bytes(host_root / "link" / "requests" / f"{received[0]['sequence']:06d}.bin")
                    one_send &= protocol.decode(sent) == request and protocol.sha(sent) == received[0]["payload_sha256"]
        calls.append({"job_id": reservation["job_id"], "call": reservation["call"], "action": action,
                      "withheld": withheld, "exact_TCP_image": bool(exact),
                      "no_private_pose": not private_fields(reservation) and not private_fields(prompt),
                      "model_process_reaped": model.get("process_exit_observed", False),
                      "core_receipt_bound": bool(bound), "one_client_send_bound": bool(one_send),
                      "usage": model.get("usage")})

    boundaries = bool(calls and all(c["exact_TCP_image"] and c["no_private_pose"] and c["model_process_reaped"] and
                                   (c["withheld"] or c["core_receipt_bound"] and c["one_client_send_bound"]) for c in calls))
    ui = read(root / "ui-ledger.json")
    steps = {step["name"]: step for step in ui["steps"]}
    required = {"uncertain", "disconnected", "offline_receipt", "reconnected", "recovered", "resumed", "completed", "reloaded"}
    ui_ok = required <= steps.keys()
    recovery_token = None
    if ui_ok:
        visible_expectations = {"uncertain": "uncertain", "disconnected": "Body disconnected",
                                "offline_receipt": "Check receipt", "reconnected": "Body connected",
                                "recovered": "Receipt recovered", "resumed": "Running",
                                "completed": "Completed", "reloaded": "Completed"}
        for name, phrase in visible_expectations.items():
            ui_ok &= phrase.casefold() in steps[name]["visible_text"].casefold()
        uncertain = steps["uncertain"]["state"]
        recovery_token = uncertain["recovery"]["command_id"]
        ui_ok &= uncertain["recovery"]["state"] == "uncertain" and uncertain["runner_status"] != "running"
        ui_ok &= steps["disconnected"]["state"]["connection"]["state"] == "disconnected"
        for name in ("disconnected", "offline_receipt", "reconnected"):
            value = steps[name]["state"]
            ui_ok &= value["runner_status"] != "running" and value["recovery"]["command_id"] == recovery_token
            ui_ok &= value["recovery"]["state"] in {"uncertain", "blocked"}
            ui_ok &= steps[name]["client_commands"] == steps["uncertain"]["client_commands"]
        recovered = steps["recovered"]["state"]
        ui_ok &= recovered["recovery"]["state"] == "recovered" and recovered["runner_status"] != "running"
        ui_ok &= steps["recovered"]["client_commands"] == steps["uncertain"]["client_commands"]
        ui_ok &= steps["resumed"]["state"]["runner_status"] == "running"
        for name in required:
            ui_ok &= steps[name]["state"]["app_id"] == public["app_id"]
            ui_ok &= steps[name]["state"]["connection"]["body_id"] == identity["body_id"]
            ui_ok &= bool(steps[name]["visible_text"]) and bool(steps[name]["browser_action"])
        ui_ok &= steps["completed"]["state"]["jobs"] == steps["reloaded"]["state"]["jobs"]
        ui_ok &= steps["completed"]["client_commands"] == steps["reloaded"]["client_commands"]
    dropped = [e for e in events if e["kind"] == "dropped_after" and e.get("command_id") == recovery_token]
    reconciliation = [e for e in events if e["kind"] == "received" and e.get("method") == "GET" and
                      e.get("path", "").startswith("/commands/" + str(recovery_token) + "?")]
    received = [e for e in events if e["kind"] == "received" and e.get("method") == "POST" and
                e.get("command_id") == recovery_token]
    fault_ok = len(dropped) == len(received) == 1 and bool(reconciliation) and recovery_token in transport
    fault_ok &= bool(recovery_token in transport and transport[recovery_token]["result"]["state"] == "completed")
    passed = bool(unchanged and process_ledger["owned_processes_exited"] and not process_ledger.get("error") and
                  len(jobs) == sqlite["count"] == 2 and all(j["passed"] for j in jobs) and boundaries and ui_ok and
                  fault_ok and transport and all(t["valid"] for t in transport.values()) and
                  not client["pending_command_ids"] and native["state"] == "ready" and native["active_job"] is None)
    result = {"passed": passed, "source_commit": frozen["commit"], "source_unchanged": unchanged,
              "scope": "browser UI and actual image policy over loopback TCP simulation",
              "body_id": identity["body_id"], "completed_cycles": sum(j["passed"] for j in jobs),
              "browser_transitions_passed": bool(ui_ok), "model_boundaries_passed": boundaries,
              "lost_reply_reconciled_without_resend": bool(fault_ok),
              "transport_journal_bound": all(t["valid"] for t in transport.values()),
              "transport_command_count": len(transport), "calls": calls, "scores": jobs, "sqlite": sqlite,
              "ui_steps": sorted(steps), "owned_processes_exited": process_ledger["owned_processes_exited"]}
    protocol.create_file(root / "qualification-score.json", protocol.encoded(result))
    return {k: result[k] for k in ("passed", "completed_cycles", "browser_transitions_passed", "model_boundaries_passed",
                                  "lost_reply_reconciled_without_resend", "source_unchanged")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    print(json.dumps(score(parser.parse_args().root), sort_keys=True))


if __name__ == "__main__":
    main()
