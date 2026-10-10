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
from pathlib import Path

import psutil
from capability_clean_install import isolated_environment
from capability_host_trial import ax_document_text, ax_reset_text
from capability_interrupt_trial import Server, destination_target
from capability_restart_trial import _rows, _wait_no_worker

PROJECT = Path(__file__).resolve().parents[2]
PREFIX, VALUE = "Invoice report\n", "17.25 USD"


def require(condition, message):
    if not condition:
        raise RuntimeError("Qualification gate failed: " + message)


class InstalledServer(Server):
    def __init__(
        self,
        python: Path,
        scope: Path,
        journal: Path,
        log: Path,
        cwd: Path,
        env: dict,
        configured: dict | None = None,
    ):
        self.log_stream = log.open("a")
        argv = [
            str(python),
            "-m",
            "jevdual.capability.cli",
            "server",
            "--scope",
            str(scope),
            "--journal",
            str(journal),
        ]
        if configured is not None:
            require(configured["command"] == str(python), "configured interpreter differs")
            require(configured["args"] == argv[1:], "configured arguments differ")
            argv = [configured["command"], *configured["args"]]
            env = {**env, **configured.get("env", {})}
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log_stream,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
        self.next_id, self._buf = 1, b""
        try:
            self.initialized = self.request(
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
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--host-config", type=Path)
    parser.add_argument("--isolation-root", type=Path)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    if not root.is_relative_to(PROJECT / "output"):
        parser.error("owned output directory required")
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    cwd = root / "outside-source"
    cwd.mkdir(mode=0o700)
    env = isolated_environment(args.isolation_root)
    env.pop("PYTHONPATH", None)
    env.pop("JEVDUAL_PURE_PY", None)
    env["PYTHONUNBUFFERED"] = "1"
    audit = root / "runtime-context"
    if args.isolation_root:
        audit.mkdir(mode=0o700)
        env["FOOTWORK_RUNTIME_AUDIT_DIR"] = str(audit)
    configured = (
        json.loads(args.host_config.read_text())["mcpServers"]["footwork"] if args.host_config else None
    )
    python = Path(os.path.abspath(args.python))
    probe = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import json,sys,os,psutil,importlib.metadata,jevdual,jevdual.capability.execution_worker as w;"
                "from jevdual._native import BACKEND;"
                'print(json.dumps({"artifact_version":importlib.metadata.version("jevdual"),"python":sys.executable,"prefix":sys.prefix,"kernel_executable":psutil.Process(os.getpid()).exe(),"kernel_argv0":psutil.Process(os.getpid()).cmdline()[0],"package":jevdual.__file__,"worker":w.__file__,"backend":BACKEND,"sys_path":sys.path}))'
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
    (root / "origin-probe.json").write_text(json.dumps(origins, indent=2) + "\n")
    require(origins["backend"] == "pure-python", "origins['backend'] == 'pure-python'")
    require(
        str(python.parent.parent) in origins["package"] and str(python.parent.parent) in origins["worker"],
        "str(python.parent.parent) in origins['package'] and str(python.parent.parent) in origins['worker']",
    )
    require(
        Path(origins["prefix"]) == python.parent.parent, "Path(origins['prefix']) == python.parent.parent"
    )
    require(
        not any(p.endswith("footwork/jevdual/python") for p in origins["sys_path"]),
        "not any((p.endswith('footwork/jevdual/python') for p in origins['sys_path']))",
    )
    scope = json.loads(args.scope.read_text())
    scope_path = root / "scope.json"
    scope_path.write_text(json.dumps(scope))
    scope_path.chmod(0o600)
    journal = args.journal.resolve() if args.journal else root / "operations.sqlite"
    require(
        journal.is_relative_to(PROJECT / "output") and not journal.exists(),
        "journal.is_relative_to(PROJECT / 'output') and (not journal.exists())",
    )
    dst = scope["destination"]
    ax_reset_text(dst["pid"], dst["document"], PREFIX)
    require(
        ax_document_text(dst["pid"], dst["document"]) == PREFIX,
        "ax_document_text(dst['pid'], dst['document']) == PREFIX",
    )
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
        client = InstalledServer(
            python, args.scope.resolve(), journal, root / "server-stderr.log", cwd, env, configured
        )
        require(
            client.initialized["serverInfo"]["version"] == origins["artifact_version"],
            "client.initialized['serverInfo']['version'] == origins['artifact_version']",
        )
        initialized = client.initialized
        catalog = client.request("tools/list", {})
        require(
            {t["name"] for t in catalog["tools"]} == {"bind", "observe", "act", "status", "report"},
            "{t['name'] for t in catalog['tools']} == {'bind', 'observe', 'act', 'status', 'report'}",
        )
        source = client.tool("bind", {"name": "source"})
        require(
            VALUE in json.dumps(source) and not source["is_error"],
            "VALUE in json.dumps(source) and (not source['is_error'])",
        )
        destination = client.tool("bind", {"name": "destination"})
        arguments = {
            "target": destination_target(destination),
            "text": VALUE,
            "client_token": "installed-once",
        }
        action = client.tool("act", arguments)
        require(action.get("disposition") == "applied", "action.get('disposition') == 'applied'")
        operation = action["operation_id"]
        claims = {
            "completion": "completed",
            "operations": [{"operation": operation, "disposition": "applied"}],
            "persistence": "not_checked",
        }
        report = client.tool("report", claims)
        require(report["validation"]["accepted"], "report['validation']['accepted']")
        client.stop()
        client = InstalledServer(
            python, args.scope.resolve(), journal, root / "server-stderr.log", cwd, env, configured
        )
        repeat = client.tool("act", arguments)
        require(
            repeat["operation_id"] == operation and repeat["disposition"] == "applied",
            "repeat['operation_id'] == operation and repeat['disposition'] == 'applied'",
        )
        client.stop()
        client = None
        require(_wait_no_worker(journal), "_wait_no_worker(journal)")
        require(
            worker_proofs
            and all(
                p["cmdline"][0] == origins["kernel_argv0"] and p["executable"] == origins["kernel_executable"]
                for p in worker_proofs
            ),
            "worker_proofs and all((p['cmdline'][0] == origins['kernel_argv0'] and p['executable'] == origins['kernel_executable'] for p in worker_proofs))",
        )
        text = ax_document_text(dst["pid"], dst["document"])
        require(
            text == PREFIX + VALUE and len(_rows(journal)) == 1,
            "text == PREFIX + VALUE and len(_rows(journal)) == 1",
        )
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
        require(validated["validation"]["accepted"], "validated['validation']['accepted']")
        actual_contexts = [json.loads(p.read_text()) for p in audit.glob("*.json")] if audit.exists() else []
        if args.isolation_root:
            require(
                {c["role"] for c in actual_contexts} == {"server", "worker"},
                "actual process contexts missing",
            )
            worker_pid = worker_proofs[0]["registration"]["pid"]
            require(
                any(c["role"] == "worker" and c["pid"] == worker_pid for c in actual_contexts),
                "worker diagnostic is not registered worker",
            )
            for context in actual_contexts:
                require(Path(context["prefix"]) == python.parent.parent, "actual prefix borrowed")
                require(
                    context["home"] == str(args.isolation_root.resolve() / "private-home"),
                    "actual home borrowed",
                )
                require(
                    context["user_site_disabled"]
                    and context["browser_telemetry_disabled"]
                    and context["browser_cloud_sync_disabled"],
                    "actual isolation policy missing",
                )
                require(
                    all(
                        Path(path).is_relative_to(python.parent.parent)
                        for paths in context["modules"].values()
                        if paths
                        for path in paths
                    ),
                    "actual module origin borrowed",
                )
                if context["cua_library"]:
                    require(
                        Path(context["cua_library"]).is_relative_to(python.parent.parent),
                        "SDK dylib borrowed",
                    )
            for role in ("server", "worker"):
                require(
                    any(
                        c["role"] == role
                        and c["modules"]["cua_driver"]
                        and c["modules"]["ApplicationServices"]
                        and c["cua_library"]
                        for c in actual_contexts
                    ),
                    "fully loaded actual native context missing",
                )
        result = {
            "passed": True,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True
            ).strip(),
            "origins": origins,
            "actual_runtime_contexts": actual_contexts,
            "emitted_configuration_checked": configured is not None,
            "initialized": initialized,
            "worker_proofs": worker_proofs,
            "action": action,
            "repeat": repeat,
            "report": validated,
            "oracle_actual": text,
            "owned_worker_finished": True,
            "limits": "Existing host OS/system frameworks/permissions. Fresh dependency/private-home qualification."
            if args.isolation_root
            else "Dependency isolation is not established by this native harness alone.",
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
        (root / "worker-observations.json").write_text(json.dumps(worker_proofs, indent=2) + "\n")
        watcher.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
