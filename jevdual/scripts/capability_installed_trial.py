"""Qualify installed MCP and its actual detached worker on the owned native fixture.

The oracle/harness runs from source; product and child processes run from the
installed environment outside source, with PYTHONPATH removed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import uuid
from pathlib import Path

import psutil
from capability_host_trial import ax_document_text, ax_reset_text
from capability_interrupt_trial import Server, destination_target
from capability_restart_trial import _rows, _wait_no_worker

PROJECT = Path(__file__).resolve().parents[2]
PREFIX, VALUE = "Invoice report\n", "17.25 USD"


class InstalledServer(Server):
    def __init__(self, python: Path, scope: Path, journal: Path, log: Path, cwd: Path, env: dict):
        self.log_stream = log.open("a")
        self.proc = subprocess.Popen(
            [
                str(python),
                "-m",
                "jevdual.capability.cli",
                "server",
                "--scope",
                str(scope),
                "--journal",
                str(journal),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log_stream,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
        self.next_id, self._buf = 1, b""
        try:
            self.request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "installed-capability-check", "version": "1"},
                },
            )
            self.notify("notifications/initialized", {})
        except BaseException:
            self.stop()
            raise

    def stop(self):
        try:
            super().stop()
        finally:
            self.log_stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    if not root.is_relative_to(PROJECT / "output"):
        parser.error("owned output directory required")
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    cwd = root / "outside-source"
    cwd.mkdir(mode=0o700)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("JEVDUAL_PURE_PY", None)
    env["PYTHONUNBUFFERED"] = "1"
    python = args.python.absolute()
    probe = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import json,sys,jevdual,jevdual.capability.execution_worker as w;"
                "from jevdual._native import BACKEND;"
                'print(json.dumps({"python":sys.executable,"package":jevdual.__file__,"worker":w.__file__,"backend":BACKEND,"sys_path":sys.path}))'
            ),
        ],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    origins = json.loads(probe.stdout)
    assert origins["backend"] == "pure-python", origins
    assert str(python.parent.parent) in origins["package"] and str(python.parent.parent) in origins["worker"]
    assert not any(str(PROJECT / "jevdual/python") in p for p in origins["sys_path"])
    scope = json.loads(args.scope.read_text())
    scope["task"] = "installed-" + uuid.uuid4().hex
    scope_path = root / "scope.json"
    scope_path.write_text(json.dumps(scope))
    scope_path.chmod(0o600)
    journal = root / "operations.sqlite"
    dst = scope["destination"]
    ax_reset_text(dst["pid"], dst["document"], PREFIX)
    assert ax_document_text(dst["pid"], dst["document"]) == PREFIX
    worker_proofs = []
    done = threading.Event()

    def watch():
        seen = set()
        while not done.wait(0.005):
            for registration in Path(str(journal) + ".executions").glob("*/registration.json"):
                if registration in seen:
                    continue
                try:
                    record = json.loads(registration.read_text())
                    process = psutil.Process(record["pid"])
                    cmd = process.cmdline()
                    if (
                        "jevdual.capability.execution_worker" in cmd
                        and str(registration.parent / "packet.json") in cmd
                    ):
                        worker_proofs.append(
                            {"registration": record, "cmdline": cmd, "executable": process.exe()}
                        )
                        seen.add(registration)
                except (OSError, ValueError, psutil.Error):
                    continue

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    client = None
    try:
        client = InstalledServer(python, scope_path, journal, root / "server-stderr.log", cwd, env)
        catalog = client.request("tools/list", {})
        assert {t["name"] for t in catalog["tools"]} == {"bind", "observe", "act", "status", "report"}
        source = client.tool("bind", {"name": "source"})
        assert VALUE in json.dumps(source) and not source["is_error"]
        destination = client.tool("bind", {"name": "destination"})
        arguments = {
            "target": destination_target(destination),
            "text": VALUE,
            "client_token": "installed-once",
        }
        action = client.tool("act", arguments)
        assert action.get("disposition") == "applied", action
        operation = action["operation_id"]
        claims = {
            "completion": "completed",
            "operations": [{"operation": operation, "disposition": "applied"}],
            "persistence": "not_checked",
        }
        report = client.tool("report", claims)
        assert report["validation"]["accepted"]
        client.stop()
        client = InstalledServer(python, scope_path, journal, root / "server-stderr.log", cwd, env)
        repeat = client.tool("act", arguments)
        assert repeat["operation_id"] == operation and repeat["disposition"] == "applied"
        client.stop()
        client = None
        assert _wait_no_worker(journal)
        assert worker_proofs and all(p["cmdline"][0] == str(python) for p in worker_proofs), worker_proofs
        text = ax_document_text(dst["pid"], dst["document"])
        assert text == PREFIX + VALUE and len(_rows(journal)) == 1
        final = subprocess.run(
            [
                str(python),
                "-m",
                "jevdual.capability.cli",
                "report",
                "--task",
                scope["task"],
                "--journal",
                str(journal),
            ],
            input=json.dumps(claims),
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        validated = json.loads(final.stdout)
        assert validated["validation"]["accepted"]
        result = {
            "passed": True,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True
            ).strip(),
            "origins": origins,
            "worker_proofs": worker_proofs,
            "action": action,
            "repeat": repeat,
            "report": validated,
            "oracle_actual": text,
            "owned_worker_finished": True,
            "limits": "Wheel installed offline; dependencies reused from existing environment via an explicit owned .pth file.",
        }
        (root / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        print(
            json.dumps({"passed": True, "backend": origins["backend"], "installed_worker_observed": True}),
            flush=True,
        )
    finally:
        if client is not None:
            client.stop()
        done.set()
        watcher.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
