"""Frozen actual-model network trial; native-state scoring is post-trial only."""

import argparse
import json
import socket
import subprocess
import threading
import time
import traceback
import urllib.request
from pathlib import Path

import agent_bench
import body_client
import codex_policy
import network_fault_proxy
import order_protocol as protocol

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
SOURCES = [BASE / name for name in (
    "body_protocol.py", "body_contract.py", "bench_body_contract.py", "persistent_body_client.py",
    "body_network.py", "body_client.py", "network_fault_proxy.py", "planner_guard.py",
    "qualify_network_body.py", "score_network_body.py", "codex_policy.py", "codex-policy.md",
    "codex-action.schema.json", "agent_bench.py", "bench.py", "measurement.py", "workcell.py",
    "image_guided.py", "episode_cases.py", "order_protocol.py", "scene.xml", "qualify_bench.py")]
SOURCES.append(BASE.parent / "camera-capture-experiment" / "capture.py")
ZONES = ({"x_min": .035, "x_max": .105, "y_min": -.025, "y_max": .025},
         {"x_min": .045, "x_max": .115, "y_min": -.025, "y_max": .025})


def retain(path, value):
    protocol.create_file(path, protocol.encoded(value))


def freeze(root, commit):
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != commit:
        raise protocol.Refusal("trial must start at named source commit")
    files = {}
    for path in SOURCES:
        name = str(path.relative_to(REPO))
        content = protocol.read_bytes(path)
        if subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=REPO) != content:
            raise protocol.Refusal("source differs from named commit: " + name)
        files[name] = protocol.sha(content)
    retain(root / "source-freeze.json", {"commit": commit, "files": files})


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run(root, commit):
    root = protocol.directory(root, create=True)
    freeze(root, commit)
    port = available_port()
    origin = f"http://127.0.0.1:{port}"
    log = (root / "service.log").open("xb")
    process = subprocess.Popen([str(BASE / ".venv/bin/python"), str(BASE / "body_network.py"),
                               "--root", str(root / "body"), "--port", str(port),
                               "--initialize", "--diagnostic"], stdout=log, stderr=log)
    proxy, client = None, None
    ledger = {"attempt": 1, "planner": "actual_codex_cli_images_over_TCP", "jobs": [],
              "faults": [], "service_pid": process.pid, "body_origin": origin, "passed": False}
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                with urllib.request.urlopen(origin + "/identity", timeout=1) as response:
                    identity = protocol.decode(response.read(protocol.MAX_BYTES + 1))
                break
            except (OSError, ValueError):
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("body service failed to start")
                time.sleep(.1)
        retain(root / "identity.json", identity)
        proxy = network_fault_proxy.FaultProxy(origin, root / "proxy")
        proxy.start()
        client = body_client.BodyClient(root / "client", proxy.origin, timeout=15)
        client.acquire()
        retain(root / "initial-public.json", client.status())
        (root / "calls").mkdir(mode=0o700)
        injected = set()
        for index, zone in enumerate(ZONES, 1):
            job_id = f"network-ai-{index}"
            history = []
            client.acquire()
            client.start_job(job_id, zone)
            entry = {"job_id": job_id, "calls": 0, "completed": False}
            ledger["jobs"].append(entry)
            for number in range(1, 33):
                client.acquire()
                challenge = client.observe()
                directory = root / "calls" / f"job-{index}-call-{number:03d}"
                directory.mkdir(mode=0o700)
                retain(directory / "reservation.json", {"job_id": job_id, "call": number,
                                                        "challenge": challenge, "history": history[-6:]})
                action, metadata = codex_policy.decide(challenge, history[-6:], directory, threading.Event())
                retain(directory / "decision.json", {"action": action, "metadata": metadata})
                entry["calls"] += 1
                if action["action"] == "stop":
                    raise RuntimeError("model stopped: " + action["intent"])
                client.acquire()
                proposal = client.propose(challenge["challenge_id"], action["action"], action["intent"],
                                          action["target_x"], action["target_y"])
                retain(directory / "proposal.json", proposal)
                mode = None
                if action["action"] == "move":
                    for candidate in ("drop_after", "duplicate", "delay_after"):
                        if candidate not in injected:
                            mode = candidate
                            injected.add(mode)
                            proxy.arm(mode, operation="dispatch", delay_s=.2)
                            break
                try:
                    outcome = client.dispatch(proposal["proposal_id"])
                except body_client.Uncertain as exc:
                    # Only read the original command's result. Never send dispatch again.
                    reconciliation = client.reconcile(exc.command_id)
                    retain(directory / "reconciliation.json", reconciliation)
                    if reconciliation["state"] != "completed":
                        raise RuntimeError("dispatch remains unresolved") from exc
                    outcome = reconciliation["result"]
                    ledger["faults"].append({"mode": mode, "command_id": exc.command_id,
                                             "reconciled_state": reconciliation["state"],
                                             "read_only": True, "call": str(directory.relative_to(root))})
                if mode and mode != "drop_after":
                    ledger["faults"].append({"mode": mode, "call": str(directory.relative_to(root))})
                outcome = agent_bench.public_response(outcome)
                retain(directory / "dispatch.json", outcome)
                history.append({"action": action, "outcome": outcome["outcome"],
                                "reason": outcome.get("reason", "")})
                if outcome["outcome"] == "unknown":
                    raise RuntimeError("local guard returned unknown")
                print(json.dumps({"job": job_id, "call": number, "action": action["action"],
                                  "outcome": outcome["outcome"], "fault": mode}), flush=True)
                if action["action"] == "finish_reset" and outcome["outcome"] == "executed":
                    entry["completed"] = True
                    break
            if not entry["completed"]:
                raise RuntimeError("model job exhausted 32-call bound")
        retain(root / "final-public.json", client.status())
        ledger["passed"] = len(ledger["jobs"]) == 2 and all(job["completed"] for job in ledger["jobs"])
    except Exception as exc:
        ledger["error"] = type(exc).__name__ + ": " + str(exc)
        (root / "failure.txt").write_text(traceback.format_exc())
        raise
    finally:
        if client and hasattr(client, "close"):
            client.close()
        if proxy:
            proxy.close()
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()
        ledger["service_exit_observed"] = process.poll() is not None
        retain(root / "attempt.json", ledger)
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    run(args.root, args.source_commit)


if __name__ == "__main__":
    main()
