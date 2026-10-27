"""Bind a local application's immutable lease to public simulated-controller commands."""

import argparse
import contextlib
import importlib.util
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


protocol = module("handoff_protocol", "order_protocol.py")
cases = module("handoff_cases", "episode_cases.py")
Refusal = protocol.Refusal
SELF = BASE / "app_handoff.py"
PYTHON = Path(os.environ.get("FOOTWORK_PYTHON", str(BASE / ".venv/bin/python")))
LEASE_KEYS = ("app_id", "lease_id", "order_id", "expected_revision", "work_order", "work_order_sha256",
              "app_dir", "workspace_dir", "run_dir", "controller_dir", "handoff_dir", "origin",
              "physical_completion_id", "completion_operation_id", "binding_operation_id")
RECORD_KEYS = ("version", "source_kind", "phase", "app_url", "app_id", "lease", "app_source_fingerprints",
               "scene_path", "scene_sha256", "case_sha256", "fingerprints", "dispatch_delay_s", "pace_s",
               "launch_id", "process", "operations", "created_at", "launch_state")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def origin(value):
    if not isinstance(value, str):
        raise Refusal("application origin must be an IPv4 loopback URL")
    parsed = urllib.parse.urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise Refusal("application origin has an invalid port") from exc
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username is not None or
            parsed.password is not None or port is None or not 1 <= port <= 65535 or
            parsed.path or parsed.query or parsed.fragment or value != f"http://127.0.0.1:{port}"):
        raise Refusal("application origin must be exact http://127.0.0.1:PORT without credentials or redirects")
    return value


def api(app_url, app_id, route):
    app_url = origin(app_url)
    protocol.identity(app_id)
    request = urllib.request.Request(app_url + route, headers={"Accept": "application/json", "Origin": app_url,
                                                               "X-Footwork-App-ID": app_id})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(request, timeout=3)
    except urllib.error.HTTPError as exc:
        response = exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Refusal("application readback is unavailable; no application effect is inferred") from exc
    with response:
        code = response.code
        if response.geturl() != request.full_url or code not in {200, 404}:
            raise Refusal("application HTTP status or redirect is unsupported")
        if response.headers.get_content_type() != "application/json":
            raise Refusal("application reply must be bounded JSON")
        value = protocol.decode(response.read(protocol.MAX_BYTES + 1))
    if not isinstance(value, dict) or value.get("app_id") != app_id:
        raise Refusal("application reply has a different immutable identity")
    if code == 404:
        if value.get("phase") != "unavailable":
            raise Refusal("missing application operation has unsupported semantics")
        return value
    return value


def route(kind, identity):
    return f"/api/{kind}/{urllib.parse.quote(protocol.identity(identity), safe='')}"


def fingerprints():
    return {name: protocol.sha(protocol.read_bytes(BASE / name)) for name in (
        "app_handoff.py", "order_protocol.py", "episode_cases.py", "episode_runner.py", "controller.py",
        "image_guided.py", "proposal.schema.json", "workcell.py", "scene.xml")}


def lease_schema(lease, health, app_url, app_id, lease_id):
    protocol.fields(lease, LEASE_KEYS, "application lease")
    if lease["app_id"] != app_id or health.get("app_id") != app_id or lease["lease_id"] != lease_id:
        raise Refusal("lease/application identity does not match the requested binding")
    if not isinstance(lease_id, str) or not protocol.UUID.fullmatch(lease_id):
        raise Refusal("lease identity must be an exact UUID")
    for key in ("order_id", "physical_completion_id", "completion_operation_id", "binding_operation_id"):
        protocol.identity(lease[key])
    protocol.revision(lease["expected_revision"])
    if lease["origin"] != app_url or health.get("origin") != app_url:
        raise Refusal("lease origin changed; restart the application on its original port")
    app_dir = protocol.directory(lease["app_dir"])
    if str(app_dir) != lease["app_dir"] or health.get("app_dir") != str(app_dir):
        raise Refusal("lease application directory is not canonical or bound to this application")
    if any(lease[key] != value for key, value in protocol.paths_for(app_dir, lease_id).items()):
        raise Refusal("lease workspace/controller/episode paths differ from assigned application paths")
    order = protocol.validate_work_order(lease["work_order"])
    if order["order_id"] != lease["order_id"] or protocol.sha(protocol.encoded(order)) != lease["work_order_sha256"]:
        raise Refusal("lease snapshot identity or canonical digest is invalid")
    return lease


def app_binding(app_url, app_id, lease_id):
    health = api(app_url, app_id, "/api/health")
    if health.get("phase") != "ready" or not isinstance(health.get("source_fingerprints"), dict):
        raise Refusal("application health/source binding is unavailable")
    reply = api(app_url, app_id, route("leases", lease_id))
    protocol.fields(reply, ("app_id", "lease"), "lease readback")
    return health, lease_schema(reply["lease"], health, app_url, app_id, lease_id)


def input_file(path):
    path = Path(os.path.abspath(os.fspath(path)))
    protocol.directory(path.parent)
    if path != path.resolve(strict=True) or path.is_symlink():
        raise Refusal("scene/proposal source must be canonical, private and free of symlinks")
    return path


def bound_scene(path, expected_sha, lease):
    if not isinstance(expected_sha, str) or not protocol.DIGEST.fullmatch(expected_sha):
        raise Refusal("scene SHA256 must be exact lowercase hexadecimal")
    path = input_file(path)
    content = protocol.read_bytes(path)
    if protocol.sha(content) != expected_sha:
        raise Refusal("scene source differs from its bound digest")
    scene = protocol.decode(content)
    case = {"version": 1, "case_id": lease["lease_id"], "scene": scene, "max_actions": 8,
            "work_order": lease["work_order"]}
    try:
        cases.validate(case)
    except cases.CaseError as exc:
        raise Refusal(str(exc)) from exc
    return path, protocol.encoded(case)


def load(handoff):
    handoff = protocol.directory(handoff)
    record = protocol.decode(protocol.read_bytes(handoff / "handoff.json"))
    protocol.fields(record, RECORD_KEYS, "handoff journal")
    if (type(record["version"]) is not int or record["version"] != 1 or record["source_kind"] != "mujoco_simulation" or
            record["phase"] not in {"preparing", "prepared", "unknown", "stop_requested", "stopped"} or
            record["fingerprints"] != fingerprints()):
        raise Refusal("handoff source or phase changed; no implicit reset")
    health = {"app_id": record["app_id"], "app_dir": record["lease"]["app_dir"], "origin": record["app_url"]}
    lease_schema(record["lease"], health, origin(record["app_url"]), record["app_id"], record["lease"]["lease_id"])
    if record["lease"]["handoff_dir"] != str(handoff):
        raise Refusal("handoff journal belongs to another assigned directory")
    if (not isinstance(record["launch_id"], str) or not protocol.UUID.fullmatch(record["launch_id"]) or
            not isinstance(record["operations"], dict) or len(record["operations"]) > 32 or
            not 0 <= protocol.finite(record["dispatch_delay_s"]) <= 5 or
            not 0 <= protocol.finite(record["pace_s"]) <= .003):
        raise Refusal("handoff process/operation metadata is malformed")
    if record["process"] is not None:
        process = record["process"]
        protocol.fields(process, ("pid", "launch_id", "started_at", "incarnation"), "owned process identity")
        if (type(process["pid"]) is not int or process["pid"] <= 1 or process["launch_id"] != record["launch_id"] or
                protocol.finite(process["started_at"]) <= 0 or
                (process["incarnation"] is not None and (not isinstance(process["incarnation"], str) or
                                                         not protocol.UUID.fullmatch(process["incarnation"])))):
            raise Refusal("owned process identity is malformed")
    _, case_bytes = bound_scene(record["scene_path"], record["scene_sha256"], record["lease"])
    if protocol.sha(case_bytes) != record["case_sha256"]:
        raise Refusal("handoff scene/lease case changed")
    if (handoff / "case.json").exists() and protocol.read_bytes(handoff / "case.json") != case_bytes:
        raise Refusal("retained handoff case changed")
    if record["phase"] in {"prepared", "stop_requested", "stopped"} and not (handoff / "case.json").exists():
        raise Refusal("prepared case is unavailable")
    for operation_id, operation in record["operations"].items():
        protocol.identity(operation_id)
        protocol.fields(operation, ("proposal_sha256", "token", "decision", "phase"), "handoff operation")
        content = protocol.read_bytes(handoff / ("proposal-" + protocol.sha(operation_id.encode()) + ".json"))
        proposal = protocol.decode(content)
        if (protocol.sha(content) != operation["proposal_sha256"] or
                proposal.get("token") != operation["token"] or proposal.get("decision") != operation["decision"]):
            raise Refusal("handoff operation/request binding changed")
    return record


def controller(record, command, *args):
    result = subprocess.run([str(PYTHON), str(BASE / "controller.py"), command, "--controller-dir",
                             record["lease"]["controller_dir"], *map(str, args)], capture_output=True, timeout=10, check=False)
    value = protocol.decode(result.stdout)
    if not isinstance(value, dict):
        raise Refusal("controller reply is malformed")
    return value


def controller_health(record):
    value = controller(record, "health")
    if (value.get("run_dir") != record["lease"]["run_dir"] or
            value.get("controller_dir") != record["lease"]["controller_dir"] or
            not isinstance(value.get("current_incarnation"), str) or not protocol.UUID.fullmatch(value["current_incarnation"])):
        raise Refusal("bound controller identity or availability is unconfirmed")
    binding = protocol.decode(protocol.read_bytes(Path(record["lease"]["controller_dir"]) / "controller-binding.json"))
    if binding.get("case_sha256") != record["case_sha256"] or binding.get("run_dir") != record["lease"]["run_dir"]:
        raise Refusal("controller belongs to a different immutable lease case")
    return value


def owned(record, health):
    process = record["process"]
    return (isinstance(process, dict) and process.get("launch_id") == record["launch_id"] and
            process.get("pid") == health.get("pid") and process.get("incarnation") == health.get("current_incarnation"))


def current_order(record):
    health, lease = app_binding(record["app_url"], record["app_id"], record["lease"]["lease_id"])
    if lease != record["lease"] or health["source_fingerprints"] != record["app_source_fingerprints"]:
        raise Refusal("application source or immutable lease changed")
    reply = api(record["app_url"], record["app_id"], route("orders", lease["order_id"]))
    protocol.fields(reply, ("app_id", "order"), "order readback")
    order = protocol.validate_order(reply["order"])
    snapshot = {key: order[key] for key in lease["work_order"]}
    supported = order["state"] == "open" and order["revision"] == lease["expected_revision"] and snapshot == lease["work_order"]
    return order, supported


def guard(record):
    try:
        order, supported = current_order(record)
        result = {"phase": "open" if supported else "withheld", "guard_current": supported,
                  "app_id": record["app_id"], "lease_id": record["lease"]["lease_id"],
                  "current_order_revision": order["revision"], "current_order_state": order["state"]}
    except (Refusal, OSError, KeyError, ValueError, TypeError):
        supported = False
        result = {"phase": "unknown", "guard_current": False, "reason": "current application binding/readback is unavailable"}
    if not supported:
        result.update(new_submissions_withheld=True, physical_effects_may_be_partial=True, rollback_claim=False)
        with contextlib.suppress(Refusal, OSError, subprocess.TimeoutExpired, KeyError, ValueError):
            health = controller_health(record)
            active = health.get("active_operation_id")
            if owned(record, health) and active in record["operations"]:
                result["controller_cancellation"] = controller(record, "cancel", "--operation-id", active,
                                                               "--expected-incarnation", health["current_incarnation"])
    return result


def public(record, handoff):
    return {"source_kind": "mujoco_simulation", "phase": record["phase"], "handoff_dir": str(handoff),
            "app_id": record["app_id"], "lease_id": record["lease"]["lease_id"],
            "order_id": record["lease"]["order_id"], "expected_revision": record["lease"]["expected_revision"],
            "run_dir": record["lease"]["run_dir"], "controller_dir": record["lease"]["controller_dir"],
            "physical_completion_id": record["lease"]["physical_completion_id"],
            "completion_operation_id": record["lease"]["completion_operation_id"]}


def controller_launch(handoff, launch_id):
    handoff = protocol.directory(handoff)
    with protocol.locked(handoff):
        record = load(handoff)
        if (record["phase"] != "preparing" or record["launch_state"] != "launch_requested" or
                record["launch_id"] != launch_id or record["process"] is not None):
            raise Refusal("controller launch already dispatched or has a different bound intent")
        record["process"] = {"pid": os.getpid(), "launch_id": launch_id, "started_at": time.time(), "incarnation": None}
        record["launch_state"] = "exec_requested"
        protocol.persist(handoff / "handoff.json", record)
        argv = [str(PYTHON), str(BASE / "controller.py"), "serve", "--run-dir", record["lease"]["run_dir"],
                "--controller-dir", record["lease"]["controller_dir"], "--dispatch-delay-s", str(record["dispatch_delay_s"]),
                "--pace-s", str(record["pace_s"])]
    os.execv(str(PYTHON), argv)


def prepare(app_url, app_id, lease_id, scene_file, scene_sha256, dispatch_delay_s=0, pace_s=0):
    app_url = origin(app_url)
    health, lease = app_binding(app_url, app_id, lease_id)
    scene_path, case_bytes = bound_scene(scene_file, scene_sha256, lease)
    delay, pace = protocol.finite(dispatch_delay_s), protocol.finite(pace_s)
    if not 0 <= delay <= 5 or not 0 <= pace <= .003:
        raise Refusal("controller delay or pacing exceeds the frozen diagnostic bound")
    for key in ("workspace_dir", "run_dir", "controller_dir", "handoff_dir"):
        protocol.directory(lease[key], create=True)
    handoff = Path(lease["handoff_dir"])
    launch = False
    with protocol.locked(handoff):
        path = handoff / "handoff.json"
        if path.exists() or path.is_symlink():
            record = load(handoff)
            if (record["app_url"], record["app_id"], record["lease"], record["scene_path"], record["scene_sha256"],
                    record["dispatch_delay_s"], record["pace_s"]) != (app_url, app_id, lease, str(scene_path), scene_sha256, delay, pace):
                raise Refusal("handoff belongs to different lease, scene or controller arguments")
        else:
            if any(item.name != "app.lock" for item in handoff.iterdir()):
                raise Refusal("unreceipted handoff files exist; no implicit reset")
            record = {"version": 1, "source_kind": "mujoco_simulation", "phase": "preparing", "app_url": app_url,
                      "app_id": app_id, "lease": lease, "app_source_fingerprints": health["source_fingerprints"],
                      "scene_path": str(scene_path), "scene_sha256": scene_sha256, "case_sha256": protocol.sha(case_bytes),
                      "fingerprints": fingerprints(), "dispatch_delay_s": delay, "pace_s": pace,
                      "launch_id": uuid.uuid4().hex, "process": None, "operations": {}, "created_at": time.time(),
                      "launch_state": "not_dispatched"}
            if not guard(record)["guard_current"]:
                raise Refusal("leased order is changed, cancelled or unavailable before preparation")
            protocol.create_file(path, protocol.encoded(record))
            protocol.create_file(handoff / "case.json", case_bytes)
            initialized = subprocess.run([str(PYTHON), str(BASE / "episode_runner.py"), "init", "--run-dir", lease["run_dir"],
                                          "--case-file", str(handoff / "case.json"), "--case-sha256", record["case_sha256"]],
                                         capture_output=True, timeout=15, check=False)
            reply = protocol.decode(initialized.stdout)
            if initialized.returncode or reply.get("phase") != "active":
                record["phase"] = "unknown"
                protocol.persist(path, record)
                raise Refusal("bound episode preparation is unconfirmed; initialization is never replayed")
            record["launch_state"] = "launch_requested"
            protocol.persist(path, record)
            launch = True
    if launch:
        with (handoff / "controller.log").open("xb") as logfile:
            os.chmod(logfile.name, 0o600)
            child = subprocess.Popen([str(PYTHON), str(SELF), "_launch", "--handoff-dir", str(handoff),
                                      "--launch-id", record["launch_id"]], stdout=logfile, stderr=subprocess.STDOUT,
                                     start_new_session=True)
    else:
        child = None
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        record = load(handoff)
        if record["phase"] in {"unknown", "stopped", "stop_requested"}:
            return public(record, handoff)
        with contextlib.suppress(Refusal, OSError, subprocess.TimeoutExpired, KeyError):
            current = controller_health(record)
            process = record["process"]
            if (isinstance(process, dict) and process.get("pid") == current.get("pid") and
                    process.get("launch_id") == record["launch_id"] and
                    process.get("incarnation") in {None, current["current_incarnation"]}):
                with protocol.locked(handoff):
                    record = load(handoff)
                    process = record["process"]
                    if process["pid"] != current["pid"] or record["launch_state"] != "exec_requested":
                        raise Refusal("controller launch ownership changed during readiness")
                    process["incarnation"] = current["current_incarnation"]
                    record["phase"] = "prepared"
                    protocol.persist(handoff / "handoff.json", record)
                    return dict(public(record, handoff), controller=current, guard=guard(record), ownership="owned")
            return dict(public(record, handoff), phase="unknown", ownership="unconfirmed")
        if child is not None and child.poll() is not None:
            break
        time.sleep(.04)
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=4)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=4)
    with protocol.locked(handoff):
        record = load(handoff)
        record["phase"] = "unknown"
        protocol.persist(handoff / "handoff.json", record)
        return public(record, handoff)


def submit(handoff, operation_id, proposal_file, proposal_sha256):
    protocol.identity(operation_id)
    proposal_path = input_file(proposal_file)
    content = protocol.read_bytes(proposal_path)
    if not isinstance(proposal_sha256, str) or protocol.sha(content) != proposal_sha256:
        raise Refusal("proposal bytes differ from their approved digest")
    proposal = protocol.decode(content)
    if not isinstance(proposal, dict):
        raise Refusal("proposal must be a JSON object")
    with protocol.locked(handoff):
        record = load(handoff)
        if operation_id in record["operations"]:
            operation = record["operations"][operation_id]
            if operation["proposal_sha256"] != proposal_sha256:
                raise Refusal("handoff operation ID belongs to different proposal bytes")
            return controller(record, "status", "--operation-id", operation_id)
        guarded = guard(record)
        if not guarded["guard_current"]:
            return guarded
        health = controller_health(record)
        if record["phase"] != "prepared" or not owned(record, health):
            raise Refusal("new submissions require the exact owned controller PID/incarnation")
        if (proposal.get("run_dir") != record["lease"]["run_dir"] or proposal.get("decision") not in {"move", "complete"}):
            raise Refusal("proposal has a different leased episode or unsupported decision")
        protocol.identity(proposal.get("token"))
        completion_id = record["lease"]["physical_completion_id"]
        if ((proposal["decision"] == "complete" and (operation_id != completion_id or proposal["token"] != completion_id)) or
                (proposal["decision"] == "move" and (operation_id == completion_id or proposal["token"] == completion_id))):
            raise Refusal("physical completion must use the lease's exact stable operation and token")
        if len(record["operations"]) >= 32:
            raise Refusal("handoff has reached its bounded request count")
        retained = handoff / ("proposal-" + protocol.sha(operation_id.encode()) + ".json")
        protocol.create_file(retained, content)
        record["operations"][operation_id] = {"proposal_sha256": proposal_sha256, "token": proposal["token"],
                                               "decision": proposal["decision"], "phase": "intent"}
        protocol.persist(handoff / "handoff.json", record)
        try:
            reply = controller(record, "submit", "--operation-id", operation_id, "--proposal-file", retained,
                               "--proposal-sha256", proposal_sha256, "--expected-incarnation", health["current_incarnation"])
        except (Refusal, OSError, subprocess.TimeoutExpired):
            reply = {"phase": "unknown", "operation_id": operation_id,
                     "reason": "submission reply unavailable; use exact operation status, never resubmit"}
        record["operations"][operation_id]["phase"] = reply.get("phase", "unknown")
        protocol.persist(handoff / "handoff.json", record)
        return reply


def reconcile(record):
    value = api(record["app_url"], record["app_id"], route("operations", record["lease"]["completion_operation_id"]))
    if value.get("phase") == "unavailable":
        return {"phase": "unknown", "app_id": record["app_id"], "lease_id": record["lease"]["lease_id"],
                "completion_operation_id": record["lease"]["completion_operation_id"], "application_effect_confirmed": False}
    protocol.fields(value, ("app_id", "receipt", "current_order", "historical"), "application operation readback")
    receipt = value["receipt"]
    protocol.fields(receipt, ("app_id", "order_id", "lease_id", "completion_operation_id", "physical_completion_id",
                              "leased_revision", "fulfilled_revision", "work_order_sha256", "state",
                              "committed_time_unix", "physical_proof"), "application fulfillment receipt")
    if (not isinstance(receipt, dict) or receipt.get("app_id") != record["app_id"] or
            receipt.get("order_id") != record["lease"]["order_id"] or
            receipt.get("lease_id") != record["lease"]["lease_id"] or
            receipt.get("completion_operation_id") != record["lease"]["completion_operation_id"] or
            receipt.get("physical_completion_id") != record["lease"]["physical_completion_id"] or
            type(receipt["leased_revision"]) is not int or receipt["leased_revision"] != record["lease"]["expected_revision"] or
            receipt.get("work_order_sha256") != record["lease"]["work_order_sha256"] or value["historical"] is not True or
            receipt["state"] != "fulfilled" or type(receipt["fulfilled_revision"]) is not int or
            receipt["fulfilled_revision"] != record["lease"]["expected_revision"] + 1 or
            protocol.finite(receipt["committed_time_unix"]) <= 0 or not isinstance(receipt["physical_proof"], dict) or
            receipt["physical_proof"].get("historical") is not True or
            receipt["physical_proof"].get("operation_id") != record["lease"]["physical_completion_id"]):
        raise Refusal("application effect readback has another app/order/lease/operation identity")
    current = protocol.validate_order(value["current_order"])
    if (current["order_id"] != record["lease"]["order_id"] or current["state"] != "fulfilled" or
            current["revision"] < receipt["fulfilled_revision"] or
            protocol.sha(protocol.encoded({key: current[key] for key in record["lease"]["work_order"]})) !=
            record["lease"]["work_order_sha256"]):
        raise Refusal("application current order does not support the immutable terminal fulfillment receipt")
    return dict(value, phase="fulfilled", application_effect_confirmed=True, physical_proof_scope="historical")


def stop(handoff):
    with protocol.locked(handoff):
        record = load(handoff)
        health = controller_health(record)
        if not owned(record, health):
            raise Refusal("stop refuses an unowned or unconfirmed controller PID/incarnation")
        pid = health["pid"]
        if type(pid) is not int or pid <= 1:
            raise Refusal("owned controller PID is invalid")
        record["phase"] = "stop_requested"
        protocol.persist(handoff / "handoff.json", record)
        os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 20
    gone = False
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            gone = True
            break
        time.sleep(.05)
    with protocol.locked(handoff):
        record = load(handoff)
        record["phase"] = "stopped" if gone else "unknown"
        protocol.persist(handoff / "handoff.json", record)
        return dict(public(record, handoff), process_termination_observed=gone, native_stop_verified=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    child = sub.add_parser("prepare")
    for key in ("app-url", "expected-app-id", "lease-id", "scene-file", "scene-sha256"):
        child.add_argument("--" + key, required=True)
    child.add_argument("--dispatch-delay-s", type=float, default=0)
    child.add_argument("--pace-s", type=float, default=0)
    for command in ("observe", "submit", "status", "guard", "reconcile", "stop", "_launch"):
        child = sub.add_parser(command)
        child.add_argument("--handoff-dir", required=True)
        if command == "submit":
            for key in ("operation-id", "proposal-file", "proposal-sha256"):
                child.add_argument("--" + key, required=True)
        if command == "status":
            child.add_argument("--operation-id")
        if command == "_launch":
            child.add_argument("--launch-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            value = prepare(args.app_url, args.expected_app_id, args.lease_id, args.scene_file,
                            args.scene_sha256, args.dispatch_delay_s, args.pace_s)
        else:
            handoff = protocol.directory(args.handoff_dir)
            if args.command == "_launch":
                controller_launch(handoff, args.launch_id)
                return 2
            if args.command == "submit":
                value = submit(handoff, args.operation_id, args.proposal_file, args.proposal_sha256)
            elif args.command == "stop":
                value = stop(handoff)
            else:
                with protocol.locked(handoff):
                    record = load(handoff)
                    if args.command == "reconcile":
                        value = reconcile(record)
                    elif args.command == "guard":
                        value = guard(record)
                    elif args.command == "observe":
                        checked = guard(record)
                        value = controller(record, "observe") if checked["guard_current"] else checked
                    elif args.operation_id:
                        if args.operation_id not in record["operations"]:
                            raise Refusal("operation is not retained by this handoff")
                        value = controller(record, "status", "--operation-id", args.operation_id)
                        value["application_guard"] = guard(record)
                    else:
                        value = dict(public(record, handoff), guard=guard(record))
                        with contextlib.suppress(Refusal, OSError, subprocess.TimeoutExpired):
                            health = controller_health(record)
                            value.update(controller=health, ownership="owned" if owned(record, health) else "unavailable")
        print(json.dumps(value, sort_keys=True, indent=2, allow_nan=False))
        return 2 if value.get("phase") in {"refused", "unknown", "withheld", "unavailable", "blocked"} else 0
    except (Refusal, cases.CaseError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, (Refusal, cases.CaseError)) else "handoff or its bound process/readback is unavailable"
        print(json.dumps({"phase": "refused", "reason": reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
