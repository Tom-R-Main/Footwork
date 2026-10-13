"""Independent SIM14 replay, interrupted-publication and orphan-planner scorer."""
import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import agent_bench
import body_client
import codex_policy
import order_protocol as protocol
import score_workbench_crashes as sim13
from qualify_workbench_recovery import BASE, CASES, REPO, read
from score_network_body import private_fields

require, indexed = sim13.require, sim13.indexed

def calls_score(root, public, transport, relay, gap_token, cancelled_directory=None):
    agent_root = root / "body/agent"
    manifest = read(agent_root / "agent.json")
    calls, proposal_ids, native_operations = [], set(), set()
    native_manifest = read(root / "body/bench/bench.json")
    for directory in sorted((root / "operator/calls").iterdir()):
        reservation = read(directory / "reservation.json")
        challenge = reservation["challenge"]
        image = challenge["observation"]["image_sha256"]
        core = indexed(agent_root, manifest, "challenges", challenge["challenge_id"])
        require({**agent_bench.public_response(core), "image_path": challenge["image_path"]} == challenge and
            protocol.sha(protocol.encoded(challenge["observation"])) == challenge["observation_sha256"], "model reservation differs from indexed camera challenge")
        image_path = Path(challenge["image_path"])
        require(image_path.parent == root / "operator/client/images" and
            protocol.sha(protocol.read_bytes(image_path, maximum=body_client.MAX_IMAGE)) == image and
            protocol.sha(protocol.read_bytes(directory / "input.png", maximum=body_client.MAX_IMAGE)) == image,
            "model did not receive its exact downloaded image")
        image_reads = [r for r in relay if r["request"]["method"] == "GET" and r["request"]["path"] == "/images/" + challenge["challenge_id"] and
            r["upstream"] and r["upstream"].get("status") == 200 and r["response"] and protocol.sha(r["response"]) == image]
        require(image_reads, "model image lacks actual TCP image reply")
        prompt_bytes = protocol.read_bytes(directory / "prompt.txt")
        prompt = json.loads(prompt_bytes.decode().split("\n", 1)[1])
        packet = challenge["observation"]
        expected = agent_bench.public_response({"current": {"job_id": packet["job_id"], "phase": packet["phase"],
            "generation": packet["generation"], "calibration": packet["calibration"], "task": challenge["task"]}, "recent_actions": reservation["history"][-12:]})
        require(prompt == expected and not private_fields(reservation) and not private_fields(prompt), "model received hidden pose or different task/history")
        if directory.name == cancelled_directory:
            request, intent = read(directory / "request.json"), read(directory / "planner-intent.json")
            live, closure = read(directory / "planner-process.json"), read(directory / "planner-closure.json")
            request_sha = protocol.sha(prompt_bytes + protocol.read_bytes(directory / "input.png", maximum=body_client.MAX_IMAGE) +
                protocol.read_bytes(directory / "instructions.md") + protocol.read_bytes(directory / "schema.json"))
            trace = protocol.read_bytes(directory / "events.jsonl", maximum=codex_policy.MAX_TRACE_BYTES)
            require(request["request_sha256"] == intent["request_sha256"] == live["request_sha256"] == closure["request_sha256"] == request_sha and
                request["image_sha256"] == image and request["tools_enabled"] is False and
                intent["owner"] == live["owner"] == closure["owner"] == reservation["planner_owner"] and
                closure["process_exit_observed"] is True and closure["group_closed"] is True and
                closure["guardian_pid"] == live["guardian_pid"] and closure["reason"] == "host liveness pipe closed" and
                request["cli_version"] == codex_policy.EXPECTED_CLI and
                protocol.read_bytes(directory / "instructions.md") == protocol.read_bytes(BASE / "codex-policy.md") and
                protocol.read_bytes(directory / "schema.json") == protocol.read_bytes(BASE / "codex-action.schema.json") and
                b'"thread.started"' in trace,
                "cancelled actual model reservation lacks exact guardian closure and image request proof")
            codex_policy.usage_from_events(trace)  # Also rejects any tool-bearing trace item.
            require(not any((directory / name).exists() for name in ("decision.json", "proposal.json", "dispatch.json")),
                "cancelled old planner result reached proposal or dispatch")
            calls.append({"job_id": reservation["job_id"], "call": reservation["call"],
                "cancelled": True, "image_sha256": image, "challenge_id": challenge["challenge_id"],
                "camera_generation": packet["generation"], "model_pid": live["planner_pid"], "passed": True})
            continue
        model, decision = read(directory / "outcome.json"), read(directory / "decision.json")
        chosen = codex_policy.validate_action(read(directory / "result.json"))
        request = read(directory / "request.json")
        request_sha = protocol.sha(prompt_bytes + protocol.read_bytes(directory / "input.png", maximum=body_client.MAX_IMAGE) +
            protocol.read_bytes(directory / "instructions.md") + protocol.read_bytes(directory / "schema.json"))
        trace = protocol.read_bytes(directory / "events.jsonl", maximum=codex_policy.MAX_TRACE_BYTES)
        trace_events = [json.loads(line) for line in trace.decode().splitlines() if line.strip()]
        messages = [event["item"]["text"] for event in trace_events if event.get("type") == "item.completed" and
            event.get("item", {}).get("type") == "agent_message"]
        require(model["provider"] == "codex_cli" and model.get("outcome") == "decision" and model["process_exit_observed"] is True and
            model["exit_code"] == 0 and decision["action"] == chosen and decision["metadata"] == model and
            messages and protocol.decode(messages[-1].encode()) == chosen and any(event.get("type") == "turn.completed" for event in trace_events) and
            model["cli_version"] == request["cli_version"] == codex_policy.EXPECTED_CLI and
            protocol.read_bytes(directory / "instructions.md") == protocol.read_bytes(BASE / "codex-policy.md") and
            protocol.read_bytes(directory / "schema.json") == protocol.read_bytes(BASE / "codex-action.schema.json") and
            request.get("tools_enabled") is False and request["request_sha256"] == model["request_sha256"] == request_sha and
            request["image_sha256"] == model["image_sha256"] == image and
            codex_policy.usage_from_events(trace) == model["usage"],
            "actual image-only Codex decision or process proof is incomplete")
        proposal = read(directory / "proposal.json")
        lower = indexed(agent_root, manifest, "proposals", proposal["proposal_id"])
        require(lower == proposal and proposal["challenge_id"] == challenge["challenge_id"] and
            proposal["observation_sha256"] == challenge["observation_sha256"] and
            all(proposal[key] == chosen[key] for key in ("action", "intent", "target_x", "target_y")), "AI decision/proposal/challenge binding differs")
        require(proposal["proposal_id"] not in proposal_ids, "two model calls share a proposal")
        proposal_ids.add(proposal["proposal_id"])
        dispatches = [(token, record) for token, record in transport.items() if record["request"]["operation"] == "dispatch" and
            record["request"]["arguments"]["proposal_id"] == proposal["proposal_id"]]
        require(len(dispatches) == 1, "model proposal has zero or multiple accepted dispatch commands")
        token, dispatch = dispatches[0]
        intent = indexed(agent_root, manifest, "intents", proposal["proposal_id"])
        require(intent["proposal_sha256"] == manifest["proposals"][proposal["proposal_id"]] and
            intent["challenge_sha256"] == manifest["challenges"][challenge["challenge_id"]] and intent["operation_id"] == proposal["operation_id"], "lower dispatch intent differs")
        if token == gap_token:
            require(not (directory / "dispatch.json").exists() and proposal["proposal_id"] not in manifest["results"] and
                dispatch["result"] is None, "missing native proof gained a terminal dispatch")
        else:
            result = indexed(agent_root, manifest, "results", proposal["proposal_id"])
            require(result["proposal_id"] == proposal["proposal_id"] and result["outcome"] in {"executed", "refused"} and
                agent_bench.public_response(result) == read(directory / "dispatch.json") == dispatch["result"]["result"], "dispatch lacks exact lower/native/host receipt")
            if result["outcome"] == "executed" and chosen["action"] != "begin_reset":
                operation = proposal["operation_id"]
                operation_bytes = protocol.read_bytes(root / "body/bench/operations" / (protocol.sha(operation.encode()) + ".json"))
                native_record = protocol.decode(operation_bytes)
                require(native_manifest["operations"].get(operation) == protocol.sha(operation_bytes) and
                    native_record["request"]["kind"] == chosen["action"] and native_record["request"]["observation"] == challenge["observation"] and
                    native_record["receipt"] == result["receipt"] and native_record["receipt"]["operation_id"] == operation,
                    "executed AI dispatch lacks its exact indexed native operation")
                if chosen["action"] == "move":
                    require(native_record["request"]["target_x"] == chosen["target_x"] and native_record["request"]["target_y"] == chosen["target_y"] and
                        native_record["receipt"]["native_steps"] > 0 and native_record["receipt"]["max_axis_actuator_force_n"] <= 4.00000001,
                        "native move differs from its bounded model target")
                native_operations.add(operation)
        calls.append({"job_id": reservation["job_id"], "call": reservation["call"], "action": chosen["action"],
            "command_id": token, "proposal_id": proposal["proposal_id"], "image_sha256": image,
            "challenge_id": challenge["challenge_id"], "camera_generation": packet["generation"],
            "native_gap": token == gap_token, "model_pid": model["pid"], "passed": True})
    require(calls and len(calls) == public["usage"]["calls"] == sum(j["call_count"] for j in public["jobs"]) and
        {(c["job_id"], c["call"]) for c in calls} == {(j["job_id"], n) for j in public["jobs"] for n in range(1, j["call_count"] + 1)},
        "reserved model calls are missing, duplicated or outside final scope")
    require(proposal_ids == {record["request"]["arguments"]["proposal_id"] for record in transport.values() if record["request"]["operation"] == "dispatch"},
        "accepted dispatch escaped actual image-model accounting")
    require(native_operations == set(native_manifest["operations"]), "native effect escaped actual model-dispatch accounting")
    return calls


def boundary_score(root, boundary, transport, events):
    before = read(root / "snapshots" / boundary["pre_snapshot"])
    restored = read(root / "snapshots" / boundary["restored_snapshot"])
    gate = boundary["gate"]
    require(boundary["process"]["returncode"] == -9 and boundary["process"]["signal_target"] == "host_pid_only" and
        gate["pid"] == boundary["process"]["pid"], "crash was not exact owned host-only SIGKILL")
    require(before["client"]["commands"] == restored["client"]["commands"] and
        before["posts"] == restored["posts"] and before["host"]["app_id"] == restored["host"]["app_id"] and
        before["body_identity"] == restored["body_identity"] and not restored["public"]["model_request_pending"] and
        restored["public"]["runner_status"] != "running", "restart changed commands/body or automatically resumed planning")
    resumes = [e for e in events if e["kind"] == "resume" and e["seq"] > restored["host"]["sequence"]]
    require(resumes, "explicit post-restart Resume is absent")
    resumed = resumes[0]
    if boundary["case"] == "host-publication":
        token = boundary["command_id"]
        event_path = root / "operator/events" / f"{gate['event_sequence']:06d}.json"
        orphan = read(event_path)
        require(protocol.sha(protocol.read_bytes(event_path)) == gate["event_sha256"] and
            orphan["kind"] == "rpc_applied" and orphan["outcome"] == "dispatch: " + token and
            gate["event_sequence"] == gate["manifest_sequence"] + 1 == before["host"]["sequence"] + 1 and
            restored["host"]["sequence"] >= gate["event_sequence"], "orphan event was replaced, lost or not indexed on restart")
        require(restored["public"]["recovery"]["command_id"] == token and transport[token]["result"]["state"] == "completed",
            "restart lost exact original command uncertainty")
        reconciled = [e for e in events if e["kind"] == "reconciled" and e["outcome"] == token and
            restored["host"]["sequence"] < e["seq"] < resumed["seq"]]
        exact = [read(p) for p in (root / "operator/calls").glob("*/reconciliation.json") if read(p)["command_id"] == token]
        reads = [r for r in sim13.relay_records(root) if r["request"]["method"] == "GET" and
            urlsplit(r["request"]["path"]).path == "/commands/" + token and
            restored["time"] <= r["request"]["started_time"] < resumed["time"]]
        expected_query = {key: [str(transport[token]["request"][key])] for key in ("client_id", "lease_id", "epoch")}
        expected_query["request_sha256"] = [protocol.sha(protocol.encoded(transport[token]["request"]))]
        require(reads and all(parse_qs(urlsplit(r["request"]["path"]).query) == expected_query for r in reads),
                "historical receipt lookup differs from original owner, lease, epoch or digest")
        require(len(exact) == 1 and exact[0] == transport[token]["result"] and reconciled and reads,
            "publication recovery did not read and apply exact receipt before Resume")
    else:
        directory = root / "operator/calls" / gate["call_directory"]
        closure = read(directory / "planner-closure.json")
        require(closure["owner"] == gate["planner"]["owner"] and closure["guardian_pid"] == gate["planner"]["guardian_pid"] and
            closure["process_exit_observed"] is True and closure["group_closed"] is True and
            not restored["public"]["recovery"]["command_id"], "orphan planner was not retired before restart")
    before_resume = [r for r in transport.values() if r["relay"]["request"]["started_time"] < resumed["time"]]
    require(len(before_resume) == len(restored["client"]["commands"]), "a successor action preceded explicit Resume")
    later = sorted((r for r in transport.values() if r["relay"]["request"]["started_time"] >= resumed["time"]),
                   key=lambda r: r["received"]["sequence"])
    require(later and later[0]["request"]["operation"] == "observe", "Resume did not first acquire fresh camera evidence")
    return {"passed": True, "original_commands_preserved": True, "resume_sequence": resumed["seq"],
        "fresh_challenge": later[0]["result"]["result"]["challenge_id"], "host_pid_only": True}


def ui_score(root, boundary):
    steps = read(root / "ui-ledger.json")["steps"]
    named = {s["name"]: s for s in steps}
    required = ("crash-offline", "restored", "resumed", "completed")
    require(all(name in named for name in required) and len(named) == len(steps), "browser recovery evidence steps are missing or duplicated")
    offline, restored_step, resumed, completed = [named[name] for name in required]
    require(offline["offline"] and offline["state"] is None and "disconnected" in offline["visible_text"].lower(),
            "browser has no explicit visible offline evidence")
    restored = read(root / "snapshots" / boundary["restored_snapshot"])
    require(not restored_step["offline"] and restored_step["time"] >= restored["time"] and
        restored_step["state"]["runner_status"] != "running" and not restored_step["state"]["model_request_pending"] and
        any(word in restored_step["visible_text"].lower() for word in ("paused", "uncertain")), "browser did not show restored pause or uncertainty")
    require(not resumed["offline"] and resumed["state"]["runner_status"] == "running" and
        "running" in resumed["visible_text"].lower() and restored_step["time"] < resumed["time"] < completed["time"],
        "browser did not show ordered explicit resumed running state")
    require(not completed["offline"] and any(j["status"] == "completed" for j in completed["state"]["jobs"]) and
        "completed" in completed["visible_text"].lower(), "browser did not show completed measurement/reset")
    if boundary["case"] == "host-publication":
        require(restored_step["state"]["recovery"]["command_id"] == boundary["command_id"] and "recovered" in named,
                "browser did not show original command uncertainty and receipt recovery")
        recovered = named["recovered"]
        require(not recovered["offline"] and recovered["state"]["runner_status"] == "paused" and
            not recovered["state"]["recovery"]["command_id"] and "receipt recovered" in recovered["visible_text"].lower() and
            recovered["client_commands"] == restored_step["client_commands"] and restored_step["time"] < recovered["time"] < resumed["time"],
            "receipt recovery did not stay paused without new commands")
    return {"passed": True, "steps": [s["name"] for s in steps], "offline_then_paused": True}


def score(root):
    root = protocol.directory(root)
    frozen, ready = read(root / "source-freeze.json"), read(root / "ready.json")
    case = ready["case"]
    require(case in CASES and frozen["files"] and all(protocol.sha(protocol.read_bytes(REPO / path)) == digest
        for path, digest in frozen["files"].items()), "case invalid or frozen measured source changed")
    process = read(root / "process-ledger.json")
    boundary = read(root / "crash-ledger.json")["boundaries"][0]
    require(process["owned_processes_exited"] and not process.get("error") and not process.get("cleanup_error"), "owned actors not cleaned up")
    for actor in process["processes"]:
        require(actor["exit_observed"] and actor["returncode"] == (-9 if actor["pid"] == boundary["process"]["pid"] else 0),
                "an owned actor exited unexpectedly")
    public, identity = read(root / "final-public.json"), read(root / "identity.json")
    cutoff = public["activity"][-1]["seq"]
    events = sim13.scoped(root, "operator/events", cutoff)
    require([e["seq"] for e in events] == list(range(1, cutoff + 1)) and public["app_id"] == ready["app_id"] and
        public["connection"]["body_id"] == identity["body_id"] == ready["body_id"], "journal is not contiguous or identity changed")
    client = body_client.read_journal(root / "operator/client/client.json")
    require(len(client["commands"]) <= 240 and public["usage"]["calls"] <= 32, "declared case budget exceeded")
    relay = sim13.relay_records(root)
    link_events = [read(p) for p in sorted((root / "operator/link/events").glob("*.json"))]
    transport = sim13.transport_score(root, identity, client, link_events, relay, None)
    crash = boundary_score(root, boundary, transport, events)
    cancelled = boundary["gate"]["call_directory"] if case == "host-planning" else None
    calls = calls_score(root, public, transport, relay, None, cancelled)
    restored = read(root / "snapshots" / boundary["restored_snapshot"])
    fresh = calls[restored["host"]["usage"]["calls"]]
    require(not fresh.get("cancelled") and fresh["challenge_id"] == crash["fresh_challenge"] and
        fresh["challenge_id"] != calls[restored["host"]["usage"]["calls"] - 1]["challenge_id"] and
        fresh["camera_generation"] >= calls[restored["host"]["usage"]["calls"] - 1]["camera_generation"],
        "first resumed model did not use a fresh post-crash camera generation")
    admissions = sim13.fresh_admissions(transport, relay, events)
    sqlite = sim13.measurement_score(root / "body/bench")
    native = sim13.completed_job_score(root, public, identity, sqlite)
    ui = ui_score(root, boundary)
    cleanup = read(root / "relay/cleanup.json")
    require(cleanup["server_thread_exited"] and cleanup["active_workers"] == 0, "relay workers survived scoring")
    result = {"version": 1, "passed": True, "case": case, "source_commit": frozen["commit"], "event_cutoff": cutoff,
        "source_unchanged": True, "completed_cycles": 1, "single_wire_post_every_command": True,
        "transport_command_count": len(transport), "calls": calls, "cancelled_calls": sum(bool(c.get("cancelled")) for c in calls),
        "crash": crash, "browser": ui, "admissions": admissions, "native": native, "sqlite": sqlite,
        "owned_processes_exited": True, "scope": "selected event publication and active-planning host SIGKILL; loopback simulation"}
    protocol.create_file(root / "recovery-score.json", protocol.encoded(result))
    return {k: result[k] for k in ("passed", "case", "completed_cycles", "single_wire_post_every_command", "cancelled_calls")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(score(args.root)))


if __name__ == "__main__":
    main()
