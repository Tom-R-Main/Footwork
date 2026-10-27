"""Independent health-delay qualification layered on unchanged SIM10 scoring."""
import argparse
import json
from pathlib import Path

import body_client
import order_protocol as protocol
import score_network_workbench as previous

read = previous.read


def headers(record):
    return {key.lower(): value for key, value in record["headers"].items()}


def relay_records(root):
    records, valid = [], True
    for directory in sorted((root / "health-relay" / "requests").iterdir()):
        request = read(directory / "request.json")
        result = read(directory / "result.json")
        payload = protocol.read_bytes(directory / "request.bin")
        upstream, content = None, None
        if (directory / "upstream.json").exists():
            upstream = read(directory / "upstream.json")
            content = protocol.read_bytes(directory / "response.bin", maximum=body_client.MAX_IMAGE)
        valid &= (directory.name == f"{request['sequence']:06d}" and
                  request["payload_sha256"] == protocol.sha(payload) and request["upstream_sends"] == 1 and
                  upstream is not None and upstream["response_sha256"] == protocol.sha(content))
        if request["injected_delay_s"]:
            valid &= request["tagged_health"] and request["method"] == "GET" and request["path"] in ("/identity", "/state")
        elif request["method"] == "POST":
            valid &= not request["tagged_health"]
        records.append({"request": request, "result": result, "upstream": upstream, "content": content,
                        "payload": payload})
    valid &= bool(records) and [record["request"]["sequence"] for record in records] == list(range(1, len(records) + 1))
    return records, bool(valid)


def fresh_admissions(records, events, identity):
    proofs = [event for event in events if event["kind"] == "admission_proof"]
    commands = [record for record in records if record["request"]["method"] == "POST" and record["request"]["path"] == "/commands"]
    leases = [record for record in records if record["request"]["method"] == "POST" and record["request"]["path"] == "/lease"]
    states = [record for record in records if record["request"]["method"] == "GET" and record["request"]["path"] == "/state" and not record["request"]["tagged_health"]]
    reports, used = [], set()
    previous_command_finished = float("-inf")
    for command in commands:
        request, payload = command["request"], protocol.decode(command["payload"])
        candidates = [lease for lease in leases if lease["upstream"] and lease["upstream"]["http_status"] == 200 and
                      lease["upstream"]["finished_monotonic"] <= request["started_monotonic"] and
                      protocol.decode(lease["content"]).get("lease_id") == payload["lease_id"]]
        lease = candidates[-1] if candidates else None
        candidate_proofs = [event for event in proofs if event["time"] <= lease["request"]["started_wall"] and
                            event["outcome"] == payload["operation"]] if lease else []
        event = candidate_proofs[-1] if candidate_proofs else None
        proof = event.get("evidence", {}) if event else {}
        state_reads = [record for record in states if record["upstream"] and record["upstream"]["http_status"] == 200 and
                       record["upstream"]["wall"] <= event["time"] and record["request"]["started_monotonic"] > previous_command_finished and
                       protocol.sha(protocol.encoded(protocol.decode(record["content"]))) == proof.get("state_sha256")] if event else []
        state = max(state_reads, key=lambda record: record["request"]["started_monotonic"]) if state_reads else None
        remote = protocol.decode(state["content"]) if state else {}
        expected_headers = {key.lower(): value for key, value in body_client.pinned_headers(identity).items()}
        ready = bool(lease and event and state and event["seq"] not in used and remote.get("state") == "ready" and
                     remote.get("identity") == identity and proof.get("epoch") == identity["epoch"] and
                     all(proof.get(key) == identity[key] for key in ("body_id", "adapter_id", "source_sha256")) and
                     all(headers(state["request"]).get(key) == value for key, value in expected_headers.items()) and
                     protocol.decode(lease["payload"])["expected_epoch"] == identity["epoch"] == payload["epoch"] and
                     state["request"]["started_monotonic"] <= state["upstream"]["finished_monotonic"] <= lease["request"]["started_monotonic"] < request["started_monotonic"])
        if event:
            used.add(event["seq"])
        reports.append({"command_id": payload["command_id"], "operation": payload["operation"], "passed": ready,
                        "proof_event": event["seq"] if event else None,
                        "state_read_sequence": state["request"]["sequence"] if state else None,
                        "lease_sequence": lease["request"]["sequence"] if lease else None,
                        "command_sequence": request["sequence"]})
        if command["upstream"]:
            previous_command_finished = command["upstream"]["finished_monotonic"]
    return reports


def score(root):
    root = protocol.directory(root)
    base = previous.score(root)
    records, relay_valid = relay_records(root)
    identity = read(root / "identity.json")
    events = [read(path) for path in sorted((root / "operator" / "events").glob("*.json"))]
    admissions = fresh_admissions(records, events, identity)
    long_reads = []
    natural_delays = []
    for record in records:
        request, upstream, result = record["request"], record["upstream"], record["result"]
        if request["tagged_health"] and upstream:
            decoded = protocol.decode(record["content"])
            healthy = (decoded == identity if request["path"] == "/identity" else
                       decoded.get("identity") == identity and decoded.get("state") == "ready")
            if healthy and upstream["http_status"] == 200 and upstream["upstream_elapsed_s"] >= .8:
                natural_delays.append({"sequence": request["sequence"], "path": request["path"],
                                       "upstream_elapsed_s": upstream["upstream_elapsed_s"]})
            if (request["injected_delay_s"] == 1.2 and upstream["http_status"] == 200 and healthy and
                    result.get("completed") and result.get("delivered") and not result.get("delay_interrupted") and
                    result["delay_elapsed_s"] >= 1.2):
                long_reads.append({"sequence": request["sequence"], "path": request["path"],
                                   "upstream_elapsed_s": upstream["upstream_elapsed_s"],
                                   "injected_elapsed_s": result["delay_elapsed_s"]})
    ui = read(root / "ui-ledger.json")
    steps = {step["name"]: step for step in ui["steps"]}
    checking = steps.get("healthy_checking")
    checking_ok = bool(checking and checking["state"]["runner_status"] == "running" and
                       checking["state"]["connection"]["state"] == "checking" and checking["state"]["active_job_id"] and
                       checking["state"]["recovery"]["state"] == "none" and
                       ("checking" in checking["visible_text"].casefold() or "waiting" in checking["visible_text"].casefold()) and
                       any(job["status"] == "running" for job in checking["state"]["jobs"]))
    allowed_halt = steps.get("uncertain", {}).get("state", {}).get("recovery", {}).get("reason")
    unexpected_halts = [event for event in events if event["kind"] == "halt" and event["outcome"] != allowed_halt]
    model_outcomes = [read(path) for path in sorted((root / "operator" / "calls").glob("*/outcome.json"))]
    cancelled = [index + 1 for index, outcome in enumerate(model_outcomes) if outcome.get("outcome") == "cancelled"]
    cleanup = read(root / "health-relay" / "cleanup.json")
    process = read(root / "process-ledger.json")
    link_events = [read(path) for path in sorted((root / "operator" / "link" / "events").glob("*.json"))]
    closed = next((event for event in reversed(link_events) if event["kind"] == "closed"), None)
    # A clean host exit also requires its gateway close() to join the bounded readers.
    readers_exited = bool(closed and cleanup["server_thread_exited"] and cleanup["active_workers"] == 0 and
                          cleanup["peak_workers"] <= cleanup["worker_bound"] == 8 and
                          process["owned_processes_exited"] and
                          all(item["exit_observed"] and item["returncode"] == 0 for item in process["processes"]))
    readers_exited &= bool(closed and closed.get("health_readers_alive") == 0 and
                           0 <= closed.get("health_readers_peak", 3) <= 2)
    passed = bool(base["passed"] and relay_valid and len(long_reads) >= 3 and admissions and
                  all(report["passed"] for report in admissions) and checking_ok and not unexpected_halts and
                  not cancelled and readers_exited)
    result = {"passed": passed, "base_qualification": base, "relay_evidence_valid": relay_valid,
              "healthy_injected_long_read_count": len(long_reads), "healthy_injected_long_reads": long_reads[:64],
              "genuine_upstream_long_read_count": len(natural_delays), "genuine_upstream_long_reads": natural_delays[:64],
              "fresh_admission_proofs": admissions, "fresh_proof_every_rpc": bool(admissions and all(r["passed"] for r in admissions)),
              "soft_checking_visible_while_running": checking_ok, "unexpected_halts": unexpected_halts,
              "cancelled_model_calls": cancelled, "owned_readers_exited": readers_exited,
              "relay_cleanup": cleanup, "scope": "same-Mac loopback simulation; 1.2s diagnostic auxiliary read delay"}
    retain = protocol.create_file
    retain(root / "health-qualification-score.json", protocol.encoded(result))
    return {key: result[key] for key in ("passed", "fresh_proof_every_rpc", "soft_checking_visible_while_running", "owned_readers_exited")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    print(json.dumps(score(parser.parse_args().root), sort_keys=True))


if __name__ == "__main__":
    main()
