"""Independent stopped-evidence scorer for the four SIM13 hard-crash cases."""
import argparse
import json
import math
from pathlib import Path

import agent_bench
import bench
import body_client
import body_protocol as wire
import codex_policy
import order_protocol as protocol
import qualify_bench
from score_network_body import private_fields
from score_workbench_restarts import read

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
CASES = {"host-inflight", "body-native-gap", "body-uncertain", "host-uncertain"}


def require(condition, reason):
    if not condition:
        raise protocol.Refusal(reason)


def scoped(root, folder, limit):
    events = [read(path) for path in sorted((root / folder).glob("*.json"))]
    key = "seq" if folder == "operator/events" else "sequence"
    return [event for event in events if event[key] <= limit]


def indexed(root, manifest, kind, token):
    content = protocol.read_bytes(root / kind / (token + ".json"))
    require(manifest[kind].get(token) == protocol.sha(content), "lower indexed evidence digest differs")
    return protocol.decode(content)


def envelope_bound(request, value):
    protocol.fields(value, wire.ENVELOPE_FIELDS, "crash command receipt")
    return bool(value["state"] in {"completed", "refused", "not_accepted", "unknown"} and
        value["receipt_scope"] == "retained_command_result" and
        type(value["recorded_epoch"]) is int and value["recorded_epoch"] == request["epoch"] and
        value["request_sha256"] == protocol.sha(protocol.encoded(request)) and
        all(value[key] == request[key] for key in ("protocol", "adapter_id", "body_id", "source_sha256", "command_id")))


def command_identity(snapshot):
    return {token: {key: value[key] for key in ("request_sha256", "send_count", "operation")}
        for token, value in snapshot["client"]["commands"].items()}


def boundary_score(root, boundary, identity, transport, events):
    case, role, token = boundary["case"], boundary["role"], boundary["command_id"]
    require(case in CASES and role == ("body" if case.startswith("body") else "workbench"), "crash role or case changed")
    request = transport[token]["request"]
    require(request["operation"] == "dispatch" and boundary["request_sha256"] == protocol.sha(protocol.encoded(request)),
        "crash token is not its exact accepted dispatch")
    snapshots = [read(root / "snapshots" / boundary[name]) for name in ("pre_snapshot", "offline_snapshot", "restored_snapshot")]
    before, offline, restored = snapshots
    for snapshot in snapshots:
        require(snapshot["host"]["app_id"] == before["host"]["app_id"] and
            all(snapshot["host"]["body_identity"][key] == identity[key] for key in body_client.IDENTITY_KEYS - {"epoch"}),
            "crash changed stable application/body pins")
        stage = snapshot["host"]["stage"]
        require(stage and stage["operation"] == "dispatch" and stage["arguments"] == request["arguments"] and
            stage.get("command_id") in (None, token) and token not in stage["before_commands"] and
            token in snapshot["client"]["pending_command_ids"], "crash lost its original pending host/client stage")
        require(command_identity(snapshot) == command_identity(before) and snapshot["posts"] == before["posts"],
            "restart introduced a client command or POST")
        require(snapshot["client"]["lease"] == before["client"]["lease"], "unknown command rotated its historical lease")
    process = boundary["process"]
    require(process["exit_observed"] is True and process["returncode"] == -9 and process["group"] == process["pid"] and
        before["processes"][role] == process["pid"] and offline["processes"][role] is None and
        restored["processes"][role] not in (None, process["pid"]), "crash was not an observed owned SIGKILL and independent restart")
    require(process.get("children_before") == [] and process.get("children_after") == [], "crash gate has unaccounted owned children")
    require(before["public"] and before["public"]["model_request_pending"] is False,
        "selected command gate had an active planner")
    require(boundary["old_epoch"] == request["epoch"] and
        boundary["new_epoch"] == boundary["old_epoch"] + (role == "body") and
        restored["body_identity"]["epoch"] == boundary["new_epoch"], "restart boot epoch is not bound to crashed authority")
    public = restored["public"]
    require(public and public["runner_status"] == "blocked" and not public["model_request_pending"] and
        public["recovery"]["command_id"] == token, "restart was not visibly paused with the exact uncertain command")
    if case == "host-inflight":
        marker = boundary["gate"]
        require(marker == read(root / "relay/barrier.json") and marker["barrier"] == "body_receipt_before_link_reply" and
            marker["command_id"] == token and marker["request_sha256"] == boundary["request_sha256"] and
            marker["response_sha256"] == protocol.sha(protocol.encoded(transport[token]["result"])) and
            marker["proposal_id"] == request["arguments"]["proposal_id"] and marker["body_id"] == request["body_id"] and
            marker["epoch"] == request["epoch"], "held host reply is not its independently indexed body completion")
    elif case != "body-native-gap":
        require(boundary["gate"] is None and before["public"]["runner_status"] == "blocked" and
            before["public"]["recovery"]["command_id"] == token and before["body_command"]["terminal"] == transport[token]["result"],
            "already-uncertain crash did not have known independent body proof")
    future = [event for event in events if event["seq"] > restored["host"]["sequence"]]
    reconciled = next((event for event in future if event["kind"] == "reconciled" and event["outcome"] == token), None)
    resumed = next((event for event in future if event["kind"] == "resume"), None)
    if case == "body-native-gap":
        require(reconciled is None and resumed is None, "missing native proof was promoted to recovered or resumed")
    else:
        require(reconciled and resumed and reconciled["seq"] < resumed["seq"], "exact receipt must precede explicit Resume")
    return {"passed": True, "case": case, "role": role, "command_id": token,
        "request_sha256": boundary["request_sha256"], "old_epoch": boundary["old_epoch"],
        "new_epoch": boundary["new_epoch"], "restored_sequence": restored["host"]["sequence"],
        "reconciled_sequence": reconciled["seq"] if reconciled else None,
        "resume_sequence": resumed["seq"] if resumed else None, "snapshot_command_count": len(before["client"]["commands"])}


def relay_records(root):
    records = []
    for directory in sorted((root / "relay" / "requests").iterdir()):
        request = read(directory / "request.json")
        payload = protocol.read_bytes(directory / "request.bin")
        require(directory.name == f"{request['sequence']:06d}" and request["payload_sha256"] == protocol.sha(payload) and
            request["upstream_sends"] == 1, "relay request bytes or actual-send evidence changed")
        upstream, response = None, None
        if (directory / "response.json").exists():
            upstream = read(directory / "response.json")
            if (directory / "response.bin").exists():
                response = protocol.read_bytes(directory / "response.bin", maximum=body_client.MAX_IMAGE)
                require(upstream["sha256"] == protocol.sha(response), "relay response digest differs")
        records.append({"request": request, "payload": payload, "upstream": upstream, "response": response})
    require(records and [r["request"]["sequence"] for r in records] == list(range(1, len(records) + 1)), "relay sequence is incomplete")
    return records


def transport_score(root, identity, client, link_events, relay, gap_token):
    result = {}
    received = [event for event in link_events if event["kind"] == "received" and event.get("method") == "POST" and event.get("command_id")]
    for token, index in client["commands"].items():
        content = protocol.read_bytes(root / "operator/client/requests" / (token + ".json"))
        request = wire.validate_command(protocol.decode(content))
        require(index["send_count"] == 1 and protocol.sha(content) == index["request_sha256"] and request["command_id"] == token and
            all(request[key] == identity[key] for key in ("protocol", "adapter_id", "body_id", "source_sha256")), "client request identity changed")
        matches = [e for e in received if e["command_id"] == token]
        relay_matches = [r for r in relay if r["request"]["method"] == "POST" and r["request"]["path"] == "/commands" and protocol.decode(r["payload"])["command_id"] == token]
        require(len(matches) == len(relay_matches) == 1, "command has zero or multiple actual wire sends")
        transmitted = protocol.read_bytes(root / "operator/link/requests" / f"{matches[0]['sequence']:06d}.bin")
        require(transmitted == content == relay_matches[0]["payload"] and matches[0]["payload_sha256"] == protocol.sha(content),
            "client/link/relay command bytes disagree")
        directory = root / "body/commands" / protocol.sha(token.encode())
        accepted = read(directory / "intent.json")
        require(accepted["request"] == request and accepted["request_sha256"] == protocol.sha(content), "independent body acceptance differs")
        terminal = None
        if accepted["result_sha256"] is not None:
            result_bytes = protocol.read_bytes(directory / "result.json")
            terminal = protocol.decode(result_bytes)
            require(protocol.sha(result_bytes) == accepted["result_sha256"] and envelope_bound(request, terminal), "body terminal receipt is not bound")
        else:
            require(token == gap_token and request["operation"] == "dispatch", "unexpected unresolved accepted body command")
        response = None
        if "response_sha256" in index:
            response_bytes = protocol.read_bytes(root / "operator/client/responses" / (token + "-" + index["response_sha256"] + ".json"))
            response = protocol.decode(response_bytes)
            require(protocol.sha(response_bytes) == index["response_sha256"] and envelope_bound(request, response), "client retained response changed")
        if token != gap_token:
            require(terminal and terminal["state"] == "completed" and response == terminal and token not in client["pending_command_ids"],
                "known command lacks exact terminal client/body receipt")
        else:
            require(token in client["pending_command_ids"] and (response is None or response["state"] == "unknown"), "native gap was incorrectly settled")
        result[token] = {"request": request, "result": terminal, "received": matches[0], "relay": relay_matches[0]}
    require(len(received) == len(result) and len(list((root / "body/commands").iterdir())) == len(result), "extra effect send/acceptance escaped client accounting")
    return result


def calls_score(root, public, transport, relay, gap_token):
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


def fresh_admissions(transport, relay, events):
    proofs = [event for event in events if event["kind"] == "admission_proof"]
    used, reports, previous_send = set(), [], float("-inf")
    for token, record in sorted(transport.items(), key=lambda item: item[1]["received"]["sequence"]):
        request = record["request"]
        sent_time = record["relay"]["request"]["started_time"]
        candidates = [event for event in proofs if event["seq"] not in used and event["outcome"] == request["operation"] and
            event["time"] <= sent_time]
        proof_event = candidates[-1] if candidates else None
        require(proof_event, "effect command lacks a distinct fresh admission proof event")
        proof = proof_event.get("evidence", {})
        states = []
        for entry in relay:
            sent, upstream = entry["request"], entry["upstream"]
            headers = {key.lower(): value for key, value in sent["headers"].items()}
            expected_headers = {key.lower(): value for key, value in body_client.pinned_headers(request).items()}
            if (sent["method"] == "GET" and sent["path"] == "/state" and "x-footwork-health-probe" not in headers and
                    all(headers.get(key) == value for key, value in expected_headers.items()) and
                    upstream and upstream.get("status") == 200 and entry["response"] and
                    sent["started_time"] > previous_send and upstream["time"] <= proof_event["time"]):
                value = protocol.decode(entry["response"])
                if protocol.sha(protocol.encoded(value)) == proof.get("state_sha256"):
                    states.append(value)
        require(states and any(state.get("state") == "ready" and
            all(state["identity"][key] == request[key] == proof.get(key) for key in ("body_id", "adapter_id", "source_sha256", "epoch")) for state in states),
            "cached auxiliary health or a different boot authorized command admission")
        leases = [entry for entry in relay if entry["request"]["method"] == "POST" and entry["request"]["path"] == "/lease" and
            entry["upstream"] and entry["upstream"]["status"] == 200 and entry["response"] and
            protocol.decode(entry["response"]).get("lease_id") == request["lease_id"]]
        require(len(leases) == 1 and proof_event["time"] <= leases[0]["request"]["started_time"] < record["relay"]["request"]["started_time"] and
            protocol.decode(leases[0]["payload"])["expected_epoch"] == request["epoch"], "command lease precedes proof or belongs to another boot")
        used.add(proof_event["seq"])
        reports.append({"command_id": token, "proof_event": proof_event["seq"], "passed": True})
        previous_send = sent_time
    return reports


def native_gap_score(root, boundary, public, transport, calls, sqlite):
    token, marker = boundary["command_id"], boundary["gate"]
    require(marker and marker["barrier"] == "after_native" and marker == read(root / "body/barrier.json"), "native gap marker changed")
    request = transport[token]["request"]
    lower = read(root / "body/agent/agent.json")
    proposal = indexed(root / "body/agent", lower, "proposals", request["arguments"]["proposal_id"])
    native = read(root / "body/bench/bench.json")
    require(marker["pid"] == boundary["process"]["pid"] and marker["command_id"] == token and marker["request_sha256"] == boundary["request_sha256"] and
        marker["proposal_id"] == proposal["proposal_id"] and marker["operation_id"] == proposal["operation_id"] and marker["bench_id"] == request["body_id"] and
        marker["diagnostic_source_sha256"] == protocol.sha(protocol.read_bytes(BASE / "crash_body.py")) and
        native["generation"] == marker["manifest_generation"] and marker["native_generation"] == native["generation"] + 1 and
        native["busy"] == {"operation_id": proposal["operation_id"], "kind": "move", "generation": native["generation"]} and
        proposal["operation_id"] not in native["operations"] and proposal["proposal_id"] not in lower["results"], "native gap lacks exact accepted, unresolved lower operation proof")
    native_root = root / "body/bench"
    before = qualify_bench.native_score(native_root, native["generation"], native["state_sha256"], bench.HOME_ZONE)
    after = qualify_bench.native_score(native_root, marker["native_generation"], marker["native_state_sha256"], bench.HOME_ZONE)
    moved = max(math.dist(before["block_xyz"], after["block_xyz"]), math.dist(before["pusher_xyz"], after["pusher_xyz"]))
    require(marker["native_steps"] > 0 and after["native_time_s"] == marker["native_time_s"] > before["native_time_s"] and moved > 1e-6 and
        after["external_force_cleared"] and calls[-1]["native_gap"] and calls[-1]["action"] == "move" and
        sum(call["native_gap"] for call in calls) == 1 and native["generation"] == 0 and not native["operations"] and
        len(public["jobs"]) == 1 and public["jobs"][0]["status"] == "unknown" and public["runner_status"] == "blocked" and
        public["recovery"]["command_id"] == token and public["recovery"]["state"] in {"uncertain", "blocked"} and sqlite["count"] == 0 and
        all(j["phase"] != "completed" for j in native["jobs"].values()), "missing receipt gained completion or lacks physical progress evidence")
    return {"passed": True, "safely_blocked": True, "recovered": False, "marker": marker,
        "before": before, "after": after, "native_displacement_m": moved, "reason": "Advanced native state without indexed terminal proof remains unknown"}


def completed_job_score(root, public, identity, sqlite):
    native_root = root / "body/bench"
    native = bench.Bench(native_root).status()
    require(len(public["jobs"]) == sqlite["count"] == 1 and native["state"] == "ready" and native["active_job"] is None, "known case did not complete exactly one reusable cycle")
    item = public["jobs"][0]
    job = native["jobs"][item["job_id"]]
    measurement, reset = job["measurement_receipt"], job["reset_receipt"]
    stage = qualify_bench.native_score(native_root, measurement["generation"], measurement["state_sha256"], job["target_zone"])
    home = qualify_bench.native_score(native_root, reset["generation"], reset["state_sha256"], bench.HOME_ZONE)
    initial = qualify_bench.native_score(native_root, 0, protocol.sha(protocol.read_bytes(bench.body.state_path(native_root, 0))), bench.HOME_ZONE)
    operations = [protocol.decode(protocol.read_bytes(native_root / "operations" / (protocol.sha(token.encode()) + ".json"))) for token in read(native_root / "bench.json")["operations"]]
    moves = sorted((record for record in operations if record["receipt"].get("kind") == "move"), key=lambda record: record["receipt"]["generation"])
    reset_moves = [record for record in moves if record["request"]["observation"]["phase"] == "resetting" and
        record["receipt"]["generation"] > job["reset_started_generation"]]
    require([record["receipt"]["generation"] for record in moves] == list(range(1, native["generation"] + 1)) and
        sum(record["receipt"]["native_steps"] for record in reset_moves) == reset["reset_native_steps"] and
        sum(record["receipt"]["pusher_block_contact_samples"] for record in reset_moves) == reset["reset_contact_samples"],
        "native generation/contact reset proof is incomplete or not continuous")
    require(item["status"] == job["phase"] == "completed" and sqlite["rows"][0]["job_id"] == item["job_id"] and sqlite["rows"][0]["receipt"] == measurement and
        item["measurement"] == agent_bench.public_response(measurement["measurement"]) and item["reset"] == agent_bench.public_response(reset) and
        stage["block_center_in_zone"] and home["block_center_in_zone"] and home["pusher_home"] and stage["external_force_cleared"] and home["external_force_cleared"] and
        home["native_time_s"] > stage["native_time_s"] > initial["native_time_s"] and reset["reset_contact_samples"] > 0 and reset["reset_native_steps"] > 0 and
        reset["bench_id"] == measurement["bench_id"] == identity["body_id"] == native["bench_id"] and
        job["started_generation"] == 0 and job["started_native_time_s"] == initial["native_time_s"], "completed UI lacks independent measurement/native/reset continuity proof")
    return {"passed": True, "job_id": item["job_id"], "measurement_state": stage, "reset_state": home,
        "measurement_receipt": measurement, "reset_receipt": reset, "model_calls": item["call_count"]}


def measurement_score(native_root, native_gap=False):
    database = native_root / "measurements.sqlite"
    if native_gap and not database.exists():
        require(not database.is_symlink(), "absent gap database cannot be a dangling symlink")
        return {"role": "independent_read_only_sqlite_scorer", "count": 0, "rows": [],
            "database_created": False, "reason": "Native gap occurred before the first computer measurement"}
    return qualify_bench.sqlite_score(native_root)


def ui_score(root, case, boundary, public, client):
    steps = {step["name"]: step for step in read(root / "ui-ledger.json")["steps"]}
    names = {"crash-offline", "crash-restored"} | ({"crash-blocked", "crash-still-blocked"} if case == "body-native-gap" else
        {"crash-recovered", "crash-resumed", "crash-completed"})
    require(names <= steps.keys(), "actual browser crash/recovery stages are missing")
    for name in names:
        step = steps[name]
        state = step["state"]
        require(step["visible_text"] and step["browser_action"], "browser evidence is empty")
        if name == "crash-offline" and case.startswith("host"):
            require(state is None and step.get("offline") is True and
                any(phrase in step["visible_text"].casefold() for phrase in ("disconnected", "failed to fetch")),
                "dead host browser state was falsely presented as live")
            before = read(root / "snapshots" / boundary["pre_snapshot"])
            selected = {key: before["public"][key] for key in ("app_id", "runner_status", "jobs", "connection", "recovery",
                "model_request_pending", "active_job_id", "current_frame")}
            offline_path = root / "snapshots" / boundary["offline_snapshot"]
            require(step["cached_public"] == selected and step["pins"] == {"app_id": public["app_id"], "body_id": public["connection"]["body_id"]} and
                step["snapshot_provenance"] == {"name": boundary["offline_snapshot"], "sha256": protocol.sha(protocol.read_bytes(offline_path))},
                "offline browser cache has another provenance")
        else:
            require(state and state["app_id"] == public["app_id"] and state["connection"]["body_id"] == public["connection"]["body_id"],
                "browser state belongs to another application")
    token = boundary["command_id"]
    restored = steps["crash-restored"]["state"]
    require(restored["runner_status"] == "blocked" and restored["recovery"]["command_id"] == token and
        "uncertain" in steps["crash-restored"]["visible_text"].casefold(), "browser did not show the exact pending crash result")
    count = steps["crash-restored"]["client_commands"]
    if case == "body-native-gap":
        for name in ("crash-blocked", "crash-still-blocked"):
            state = steps[name]["state"]
            require(state["runner_status"] == "blocked" and state["recovery"]["command_id"] == token and
                steps[name]["client_commands"] == count and "uncertain" in steps[name]["visible_text"].casefold(), "missing proof was released by browser controls")
        require(len(client["commands"]) == count, "native gap admitted a successor command")
    else:
        recovered, resumed, completed = (steps[name] for name in ("crash-recovered", "crash-resumed", "crash-completed"))
        require(recovered["state"]["runner_status"] == "paused" and recovered["state"]["recovery"]["state"] == "recovered" and
            recovered["state"]["recovery"]["command_id"] == token and recovered["client_commands"] == count and
            "receipt recovered" in recovered["visible_text"].casefold() and resumed["state"]["runner_status"] == "running" and
            "running" in resumed["visible_text"].casefold() and completed["state"]["jobs"] == public["jobs"] and
            completed["client_commands"] == len(client["commands"]) and "completed" in completed["visible_text"].casefold(), "browser recovery did not remain paused until explicit Resume")
    return {"passed": True, "required_names": sorted(names)}


def score(root):
    root = protocol.directory(root)
    frozen, ready = read(root / "source-freeze.json"), read(root / "ready.json")
    case = ready["case"]
    require(case in CASES and frozen["files"] and all(protocol.sha(protocol.read_bytes(REPO / path)) == digest for path, digest in frozen["files"].items()), "measured source changed or case is invalid")
    process = read(root / "process-ledger.json")
    require(process["owned_processes_exited"] is True and not process.get("error") and not process.get("cleanup_error"), "owned processes have not exited before native scoring")
    public, identity = read(root / "final-public.json"), read(root / "identity.json")
    crash = read(root / "crash-ledger.json")
    require(crash["case"] == case and len(crash["boundaries"]) == 1 and crash["boundaries"][0]["case"] == case, "case requires one exact crash boundary")
    boundary = crash["boundaries"][0]
    for item in process["processes"]:
        require(item["exit_observed"] is True and item["returncode"] == (-9 if item["pid"] == boundary["process"]["pid"] else 0), "owned actor exited unexpectedly or was not reaped")
    cutoff = public["activity"][-1]["seq"]
    events = scoped(root, "operator/events", cutoff)
    require(events and events[-1]["seq"] == cutoff and public["app_id"] == ready["app_id"] and public["connection"]["body_id"] == identity["body_id"] == ready["body_id"], "final scoring scope/identity changed")
    client = body_client.read_journal(root / "operator/client/client.json")
    require(len(client["commands"]) <= 240 and public["usage"]["calls"] <= 32, "declared single-case budget exceeded")
    relay = relay_records(root)
    link_events = [read(path) for path in sorted((root / "operator/link/events").glob("*.json"))]
    gap_token = boundary["command_id"] if case == "body-native-gap" else None
    transport = transport_score(root, identity, client, link_events, relay, gap_token)
    crash_result = boundary_score(root, boundary, identity, transport, events)
    calls = calls_score(root, public, transport, relay, gap_token)
    admissions = fresh_admissions(transport, relay, events)
    sqlite = measurement_score(root / "body/bench", native_gap=bool(gap_token))
    native = native_gap_score(root, boundary, public, transport, calls, sqlite) if gap_token else completed_job_score(root, public, identity, sqlite)
    ui = ui_score(root, case, boundary, public, client)
    original = transport[boundary["command_id"]]
    if not gap_token:
        reconciliations = [read(path) for path in (root / "operator/calls").glob("*/reconciliation.json")]
        bound_receipts = [value for value in reconciliations if value["command_id"] == boundary["command_id"]]
        require(original["result"]["state"] == "completed" and len(bound_receipts) == 1 and bound_receipts[0] == original["result"],
            "known crash has no exact historical receipt application")
        restored = read(root / "snapshots" / boundary["restored_snapshot"])
        resumes = [event for event in events if event["kind"] == "resume" and event["seq"] == crash_result["resume_sequence"]]
        before_resume = [record for record in transport.values() if record["relay"]["request"]["started_time"] < resumes[0]["time"]]
        require(len(before_resume) == len(restored["client"]["commands"]), "successor command preceded receipt and explicit Resume")
        later = sorted((record for record in transport.values() if record["relay"]["request"]["started_time"] >= resumes[0]["time"]), key=lambda record: record["received"]["sequence"])
        next_call = restored["host"]["usage"]["calls"]
        require(later and later[0]["request"]["operation"] == "observe" and next_call < len(calls) and
            calls[next_call]["challenge_id"] == later[0]["result"]["result"]["challenge_id"] and
            calls[next_call]["camera_generation"] > calls[next_call - 1]["camera_generation"],
            "Resume did not bind its first new decision to fresh post-crash TCP evidence")
    cleanup = read(root / "relay/cleanup.json")
    require(cleanup["server_thread_exited"] and cleanup["active_workers"] == 0, "owned relay workers survived scoring")
    result = {"version": 1, "passed": True, "case": case, "source_commit": frozen["commit"], "source_unchanged": True,
        "event_cutoff": cutoff, "body_id": identity["body_id"], "completed_cycles": 0 if gap_token else 1,
        "safely_blocked": bool(gap_token), "crash": crash_result, "native": native, "calls": calls,
        "admissions": admissions, "transport_command_count": len(transport), "single_wire_post_every_command": True,
        "browser": ui, "sqlite": sqlite, "owned_processes_exited": True,
        "scope": "selected process SIGKILL boundaries; actual image-only Codex browser; loopback simulation; no arbitrary power-loss guarantee"}
    protocol.create_file(root / "hard-crash-score.json", protocol.encoded(result))
    return {key: result[key] for key in ("passed", "case", "completed_cycles", "safely_blocked", "source_unchanged", "single_wire_post_every_command")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    print(json.dumps(score(parser.parse_args().root), sort_keys=True))


if __name__ == "__main__":
    main()
