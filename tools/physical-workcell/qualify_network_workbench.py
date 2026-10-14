"""Own a frozen browser/model trial's processes; UI actions come from the browser."""

import argparse
import json
import signal
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import order_protocol as protocol
import qualify_network_body

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
SOURCES = qualify_network_body.SOURCES + [BASE / name for name in (
    "workbench_link.py", "network_operator_runtime.py", "network_bench_operator.py",
    "network_bench_operator.html", "qualify_network_workbench.py", "score_network_workbench.py",
    "score_network_body.py", "record_network_workbench.py")]


def retain(path, value):
    protocol.create_file(path, protocol.encoded(value))


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_json(origin, path, processes):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(origin + path, timeout=1) as response:
                return protocol.decode(response.read(protocol.MAX_BYTES + 1))
        except (OSError, ValueError):
            if any(process.poll() is not None for process in processes):
                raise protocol.Refusal("owned trial process exited during startup")
            time.sleep(.1)
    raise protocol.Refusal("owned trial endpoint did not become ready")


def freeze(root, commit):
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != commit:
        raise protocol.Refusal("start the trial at its committed source")
    files = {}
    for path in SOURCES:
        name = str(path.relative_to(REPO))
        content = protocol.read_bytes(path)
        if subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=REPO) != content:
            raise protocol.Refusal("source is not frozen: " + name)
        files[name] = protocol.sha(content)
    retain(root / "source-freeze.json", {"commit": commit, "files": files})


def run(root, commit):
    root = protocol.directory(root, create=True)
    freeze(root, commit)
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    processes, logs = [], []
    ledger = {"source_commit": commit, "planner": "actual_codex_cli_images_over_TCP",
              "simulation": True, "processes": [], "ready": False}

    def launch(name, arguments):
        log = (root / (name + ".log")).open("xb")
        logs.append(log)
        process = subprocess.Popen([str(BASE / ".venv/bin/python"), *arguments],
                                   cwd=REPO, stdout=log, stderr=log)
        processes.append(process)
        ledger["processes"].append({"role": name, "pid": process.pid})
        return process

    try:
        body_origin = f"http://127.0.0.1:{available_port()}"
        launch("body", [str(BASE / "body_network.py"), "--root", str(root / "body"),
                        "--port", body_origin.rsplit(":", 1)[1], "--initialize", "--diagnostic"])
        identity = wait_json(body_origin, "/identity", processes)
        retain(root / "identity.json", identity)
        browser_origin = f"http://127.0.0.1:{available_port()}"
        initialization = subprocess.run([
            str(BASE / ".venv/bin/python"), str(BASE / "network_bench_operator.py"), "init",
            "--root", str(root / "operator"), "--body-origin", body_origin],
            cwd=REPO, capture_output=True, timeout=30, check=False)
        protocol.create_file(root / "initialization.stdout", initialization.stdout)
        protocol.create_file(root / "initialization.stderr", initialization.stderr)
        if initialization.returncode:
            raise protocol.Refusal("network browser initialization failed; evidence retained")
        launch("workbench", [str(BASE / "network_bench_operator.py"), "serve", "--root", str(root / "operator"),
                             "--port", browser_origin.rsplit(":", 1)[1], "--backend", "codex"])
        initial = wait_json(browser_origin, "/api/state", processes)
        retain(root / "initial-public.json", initial)
        ledger.update(body_origin=body_origin, browser_origin=browser_origin, ready=True,
                      app_id=initial["app_id"], body_id=identity["body_id"])
        retain(root / "ready.json", ledger)
        print(json.dumps(ledger), flush=True)
        deadline = time.monotonic() + 1800
        while not stopped.is_set() and not (root / "stop-request.json").exists():
            if any(process.poll() is not None for process in processes):
                raise protocol.Refusal("owned trial process exited before requested cleanup")
            if time.monotonic() >= deadline:
                raise protocol.Refusal("browser qualification exceeded its 30-minute bound")
            stopped.wait(.2)
        retain(root / "final-public.json", wait_json(browser_origin, "/api/state", processes))
    except Exception as exc:
        ledger["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        # Stop planning first. The body remains available while the host settles shutdown.
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=40)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for record, process in zip(ledger["processes"], processes, strict=True):
            record.update(exit_observed=process.poll() is not None, returncode=process.returncode)
        for log in logs:
            log.close()
        ledger["owned_processes_exited"] = all(p.poll() is not None for p in processes)
        retain(root / "process-ledger.json", ledger)
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.source_commit)), flush=True)


if __name__ == "__main__":
    main()
