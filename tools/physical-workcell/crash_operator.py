"""Diagnostic-only host barriers; external trial owner sends SIGKILL."""
import argparse
import os
import signal
import threading
import time
from pathlib import Path

import body_client
import network_bench_operator as app
import order_protocol as protocol


def publication_gate(root, pid, path, content):
    if path.parent != root / "events":
        return None
    event = protocol.decode(content)
    if event.get("kind") != "rpc_applied" or not event.get("outcome", "").startswith("dispatch: "):
        return None
    token = event["outcome"].split(": ", 1)[1]
    host = body_client.read_journal(root / "operator.json")
    client = body_client.read_journal(root / "client/client.json")
    stage = host["stage"]
    if not stage or stage["operation"] != "dispatch" or stage["command_id"] != token or client["commands"][token]["state"] != "completed":
        raise protocol.Refusal("publication gate requires the original completed dispatch and retained host stage")
    if stage["context"]["action"]["action"] != "move":
        return None
    digest = client["commands"][token]["response_sha256"]
    reply = protocol.read_bytes(root / "client/responses" / (token + "-" + digest + ".json"))
    envelope = protocol.decode(reply)
    if protocol.sha(reply) != digest or envelope["command_id"] != token or envelope["request_sha256"] != client["commands"][token]["request_sha256"]:
        raise protocol.Refusal("publication gate reply differs from exact client digest")
    if envelope["result"]["outcome"] != "executed":
        return None
    if event["seq"] != host["sequence"] + 1:
        raise protocol.Refusal("publication gate is not immediately ahead of the retained manifest")
    return {"version": 1, "barrier": "rpc_applied_event_before_manifest", "pid": pid,
            "command_id": token, "request_sha256": client["commands"][token]["request_sha256"],
            "event_sequence": event["seq"], "event_sha256": protocol.sha(content),
            "manifest_sequence": host["sequence"], "manifest_sha256": protocol.sha(protocol.read_bytes(root / "operator.json")),
            "diagnostic_sha256": protocol.sha(protocol.read_bytes(Path(__file__).resolve())), "time": time.time()}


def install_publication(root):
    original = protocol.create_file
    used = False

    def create(path, content):
        nonlocal used
        original(path, content)
        if not used:
            marker = publication_gate(root, os.getpid(), Path(path), content)
            if marker:
                used = True
                original(root / "barrier.json", protocol.encoded(marker))
                os.kill(os.getpid(), signal.SIGSTOP)
    protocol.create_file = create


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--gate", choices=("publication", "planning"), required=True)
    args = parser.parse_args()
    root = protocol.directory(args.root)
    if (root / "barrier.json").exists():
        raise protocol.Refusal("diagnostic barrier requires an unused operator root")
    if args.gate == "publication":
        install_publication(root)
    else:
        install_planning(root)
    from codex_policy import decide
    app.serve(root, args.port, decide)


def install_planning(root):
    def watch():
        until = time.monotonic() + 1200
        while time.monotonic() < until:
            for path in sorted((root / "calls").glob("*/planner-process.json")):
                live = body_client.read_journal(path)
                if live.get("host_pid") != os.getpid() or live.get("process_exit_observed") or not live.get("planner_pid"):
                    continue
                if (path.parent / "planner-closure.json").exists():
                    continue
                trace = path.parent / "events.jsonl"
                if not trace.exists() or b'"thread.started"' not in protocol.read_bytes(trace, maximum=16 * 1024 * 1024):
                    continue
                try:
                    os.kill(live["guardian_pid"], 0)
                    os.kill(live["planner_pid"], 0)
                except ProcessLookupError:
                    continue
                marker = {"version": 1, "barrier": "actual_codex_planning_with_live_guardian", "pid": os.getpid(),
                    "command_id": None, "request_sha256": live["request_sha256"],
                    "call_directory": path.parent.name, "planner": live, "diagnostic_sha256": protocol.sha(protocol.read_bytes(Path(__file__).resolve())), "time": time.time()}
                protocol.create_file(root / "barrier.json", protocol.encoded(marker))
                os.kill(os.getpid(), signal.SIGSTOP)
                return
            time.sleep(.025)
    threading.Thread(target=watch, daemon=True, name="diagnostic-planner-barrier").start()


if __name__ == "__main__":
    main()
