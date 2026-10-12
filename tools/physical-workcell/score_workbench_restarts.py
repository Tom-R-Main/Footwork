"""Independent post-stop restart proof plus the unchanged SIM10 native scorer."""
import argparse
import json
from pathlib import Path

import body_client
import order_protocol as protocol
import score_network_workbench as previous


def read(path):
    content = protocol.read_bytes(path, maximum=1024 * 1024)
    # Local aggregate ledgers may exceed the wire JSON limit. Reject duplicate keys.
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise protocol.Refusal("duplicate scorer ledger key")
            result[key] = value
        return result
    return json.loads(content, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(protocol.Refusal("nonfinite scorer ledger")))


def command_identity(snapshot):
    return {token: {key: record[key] for key in ("request_sha256", "send_count", "operation", "state")}
            for token, record in snapshot["client"]["commands"].items()}


def score(root):
    root = protocol.directory(root)
    processes = read(root / "process-ledger.json")
    if not processes.get("owned_processes_exited"):
        raise protocol.Refusal("independent native scoring requires all owned trial processes stopped")
    legacy = previous.score(root)
    ledger = read(root / "restart-ledger.json")
    identity, initial = read(root / "identity.json"), read(root / "initial-public.json")
    host_events = [read(path) for path in sorted((root / "operator" / "events").glob("*.json"))]
    link_events = [read(path) for path in sorted((root / "operator" / "link" / "events").glob("*.json"))]
    ui = read(root / "ui-ledger.json")
    visible = {}
    for role in ("workbench", "body"):
        for predicate in ("planning", "uncertain"):
            for phase in ("offline", "restored"):
                name = f"{role}-{predicate}-{phase}"
                text = protocol.read_bytes(root / "ui" / (name + ".txt"), maximum=16000).decode("utf-8").casefold()
                phrases = (["disconnected"] if role == "workbench" else ["body unavailable"]) if phase == "offline" else (
                    ["paused"] if predicate == "planning" else ["uncertain", "check receipt"])
                visible[name] = all(phrase in text for phrase in phrases)
    for name, phrase in (("body-uncertain-recovered", "receipt recovered"), ("body-uncertain-resumed", "running")):
        visible[name] = phrase in protocol.read_bytes(root / "ui" / (name + ".txt"), maximum=16000).decode("utf-8").casefold()
    client = body_client.read_journal(root / "operator" / "client" / "client.json")
    requests = {token: read(root / "operator" / "client" / "requests" / (token + ".json")) for token in client["commands"]}
    stops = {entry["request"]["sequence"]: entry for entry in ledger["boundaries"]
             if entry["request"]["action"] == "stop-role"}
    boundaries = []
    uncertain_tokens = []
    for start in ledger["boundaries"]:
        if start["request"]["action"] != "start-role":
            continue
        stop = stops.get(start["stopped_sequence"])
        if stop is None:
            raise protocol.Refusal("restart has no exact retained stop request")
        role, predicate = stop["request"]["role"], stop["request"]["predicate"]
        snapshots = [read(root / "snapshots" / entry[name]) for entry in (stop, start) for name in ("before", "after")]
        before, stopped, restarting, after = snapshots
        stable_ids = all(s["host"]["app_id"] == initial["app_id"] and
                         s["host"]["body_identity"]["body_id"] == identity["body_id"] and
                         s["host"]["body_identity"]["adapter_id"] == identity["adapter_id"] for s in snapshots)
        stable_commands = all(command_identity(s) == command_identity(before) and s["posts"] == before["posts"] for s in snapshots)
        public_before, public_after = before["public"], after["public"]
        paused = bool(public_after and public_after["runner_status"] in {"paused", "blocked"} and
                      public_after["model_request_pending"] is False)
        owned = bool(stop["process"]["exit_observed"] and stop["process"]["returncode"] == 0 and
                     stopped["processes"][role] is None and after["processes"][role] == start["pid"] and
                     stop["process"]["pid"] != start["pid"])
        epoch_before = before["body_identity"]["epoch"]
        epoch_after = after["body_identity"]["epoch"]
        epoch_ok = epoch_after == epoch_before + (1 if role == "body" else 0)
        identities_ok = all(s["body_identity"] is None or all(s["body_identity"][key] == identity[key]
                            for key in body_client.IDENTITY_KEYS - {"epoch"}) for s in snapshots)
        outage = True
        if role == "body":
            outage_public = restarting["public"]
            outage = bool(stopped["body_identity"] is None and restarting["body_identity"] is None and
                          outage_public and outage_public["connection"]["state"] == "unavailable" and
                          outage_public["runner_status"] != "running" and not outage_public["model_request_pending"])
        pending_ok, model_reaped = True, True
        token = public_before["recovery"]["command_id"]
        if predicate == "uncertain":
            uncertain_tokens.append(token)
            pending_ok = bool(token and all(s["host"]["stage"] and s["host"]["stage"]["command_id"] == token and
                            token in s["client"]["pending_command_ids"] for s in snapshots) and
                            public_after["recovery"]["command_id"] == token and public_after["runner_status"] == "blocked" and
                            requests[token]["operation"] == "dispatch")
        else:
            pending_ok = public_before["model_request_pending"] is True and public_before["runner_status"] == "running"
            job_id = public_before["active_job_id"]
            job = next(job for job in public_before["jobs"] if job["job_id"] == job_id)
            outcome = read(root / "operator" / "calls" / f"{job_id}-{job['call_count']:02d}" / "outcome.json")
            model_reaped = outcome.get("outcome") == "cancelled" and outcome.get("process_exit_observed") is True
        after_sequence = after["host"]["sequence"]
        future_events = [event for event in host_events if event["seq"] > after_sequence]
        resume = next((event for event in future_events if event["kind"] == "resume"), None)
        reconcile = next((event for event in future_events if event["kind"] == "reconciled" and event.get("outcome") == token), None)
        last_link = max((event["sequence"] for event in after["posts"]), default=0)
        future_posts = [event for event in link_events if event["kind"] == "received" and event.get("method") == "POST" and
                        event.get("command_id") and event["sequence"] > last_link]
        new_operations = [requests[event["command_id"]]["operation"] for event in future_posts]
        first_decision = next((i for i, operation in enumerate(new_operations) if operation in {"propose", "dispatch"}), None)
        fresh = bool(resume and first_decision is not None and "observe" in new_operations[:first_decision])
        receipt_ok = True
        if predicate == "uncertain":
            lookups = [event for event in link_events if event["kind"] == "received" and event.get("method") == "GET" and
                       event.get("path", "").startswith("/commands/" + token + "?") and event["sequence"] > last_link]
            response_path = root / "operator" / "client" / "responses" / (token + "-" + client["commands"][token]["response_sha256"] + ".json")
            receipt = read(response_path)
            ui_recovered = [step for step in ui["steps"] if step["state"]["recovery"]["state"] == "recovered" and
                            step["state"]["recovery"]["command_id"] == token and
                            step["state"]["runner_status"] != "running" and
                            step["client_commands"] == len(after["client"]["commands"])]
            receipt_ok = bool(ui_recovered and reconcile and resume and reconcile["seq"] < resume["seq"] and lookups and
                              receipt["state"] == "completed" and receipt["request_sha256"] == client["commands"][token]["request_sha256"] and
                              receipt["recorded_epoch"] == requests[token]["epoch"] and
                              len([event for event in link_events if event["kind"] == "received" and event.get("method") == "POST" and
                                   event.get("command_id") == token]) == 1 and client["commands"][token]["send_count"] == 1)
        ok = all((stop["passed"], start["passed"], stable_ids, stable_commands, paused, owned, epoch_ok,
                  identities_ok, outage, pending_ok, model_reaped, fresh, receipt_ok))
        boundaries.append({"role": role, "predicate": predicate, "passed": ok, "stop_sequence": stop["request"]["sequence"],
                           "start_sequence": start["request"]["sequence"], "command_id": token,
                           "stable_ids": stable_ids and identities_ok, "unchanged_sends": stable_commands,
                           "paused_after_restart": paused, "owned_process_reaped": owned, "epoch_bound": epoch_ok,
                           "outage_observed": outage, "pending_bound": pending_ok, "model_reaped": model_reaped,
                           "fresh_observation_after_explicit_resume": fresh, "historical_receipt_without_replay": receipt_ok})
    required = {("body", "planning"), ("body", "uncertain"), ("workbench", "planning"), ("workbench", "uncertain")}
    passed = bool(legacy["passed"] and required == {(b["role"], b["predicate"]) for b in boundaries} and
                  len(boundaries) == 4 and all(b["passed"] for b in boundaries) and all(visible.values()) and
                  len(uncertain_tokens) == len(set(uncertain_tokens)) == 2 and not processes.get("cleanup_error"))
    result = {"passed": passed, "legacy_qualification": legacy, "restart_boundaries": boundaries,
              "scope": "four graceful owned mid-job restarts; actual Codex browser; loopback simulation",
              "owned_processes_exited": processes["owned_processes_exited"], "visible_restart_states": visible}
    protocol.create_file(root / "restart-score.json", protocol.encoded(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    print(json.dumps(score(parser.parse_args().root), sort_keys=True))


if __name__ == "__main__":
    main()
