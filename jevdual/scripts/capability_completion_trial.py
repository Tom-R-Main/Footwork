"""A2 structured Codex output through the enforced readonly report adapter.

Uses A1's frozen native injection/oracle; leaves A1 results unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from capability_agent_restart_trial import (
    CASES,
    PREFIX,
    PROJECT,
    codex_command,
    codex_receipt,
    configuration,
    independent_result,
    write,
)
from capability_comparison_trial import prompt, retire_backends, run_host
from capability_host_trial import ax_document_text, ax_reset_text
from jevdual.capability.completion import (
    REPORT_SCHEMA,
    ReportError,
    unavailable_summary,
    validate_from_journal,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    from ApplicationServices import AXIsProcessTrusted
    from jevdual.posture import screen_locked

    if screen_locked() or not AXIsProcessTrusted():
        parser.error("existing Accessibility access and unlocked desktop required")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT).strip():
        parser.error("commit source before execution")
    root, scope_path = args.run_dir.resolve(), args.scope.resolve()
    if not root.is_relative_to(PROJECT / "output"):
        parser.error("run directory must be private project output")
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    scope = json.loads(scope_path.read_text())
    schema_path = root / "report-schema.json"
    write(schema_path, REPORT_SCHEMA)
    summary = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
        "scope_sha256": hashlib.sha256(scope_path.read_bytes()).hexdigest(),
        "sessions": [],
        "stop_reason": None,
        "limits": "Codex default subscription model; offered inventory and exact model unavailable. "
        "Only selected executed tools audited. Published summary enforced by adapter; interactive prose is not.",
    }
    try:
        for case in CASES:
            session = root / ("codex-" + case)
            session.mkdir(mode=0o700)
            dst = scope["destination"]
            ax_reset_text(dst["pid"], dst["document"], PREFIX)
            if ax_document_text(dst["pid"], dst["document"]) != PREFIX or screen_locked():
                raise RuntimeError("independent reset not qualified")
            _, config = configuration(session, scope_path, case)
            write(session / "mcp.json", config)
            command = codex_command(config["mcpServers"]["footwork"], session / "final.txt")
            command += [
                "-c",
                "features.apps=false",
                "-c",
                "include_apps_instructions=false",
                "-c",
                "features.skill_search=false",
                "-c",
                'mcp_servers.footwork.tools.report.approval_mode="approve"',
                "--output-schema",
                str(schema_path),
            ]
            task = prompt(scope)
            write(session / "command.json", command)
            (session / "prompt.txt").write_text(task)
            started = time.monotonic()
            code, timed_out = run_host(command, task, session)
            if not retire_backends(session):
                raise RuntimeError("owned backend retirement unqualified")
            receipt = codex_receipt(session)
            # A2 allows report in addition to A1's four tools. Re-audit from raw events.
            events = [
                json.loads(line) for line in (session / "transcript.jsonl").read_text().splitlines() if line
            ]
            items = [e.get("item", {}) for e in events if e.get("type") == "item.completed"]
            outside = [
                i.get("type")
                for i in items
                if i.get("type") not in ("agent_message", "reasoning", "mcp_tool_call", "error")
            ]
            outside += [
                i.get("tool")
                for i in items
                if i.get("type") == "mcp_tool_call"
                and (
                    i.get("server") != "footwork"
                    or i.get("tool") not in ("bind", "observe", "act", "status", "report")
                )
            ]
            receipt["executed_non_footwork"] = outside
            receipt["valid_environment"] = (
                not outside
                and not receipt["isolation_errors"]
                and bool(receipt["calls"])
                and bool(receipt["usage"])
            )
            receipt.update(independent_result(session, scope, case))
            try:
                raw = json.loads((session / "final.txt").read_text())
                validated = validate_from_journal(session / "operations.sqlite", scope["task"], raw)
            except (ReportError, OSError, ValueError):
                validated = unavailable_summary()
            write(session / "validated.json", validated)
            # This file is the ONLY host-facing result published by this adapter.
            (session / "published.txt").write_text(validated["trusted_summary"] + "\n")
            expected = "unknown" if case == "no_receipt" else "completed"
            adapter_pass = (
                validated["operation_completion"] == expected
                and "Current document state and disk persistence are not certified"
                in validated["trusted_summary"]
            )
            receipt.update(
                returncode=code,
                timed_out=timed_out,
                case=case,
                raw_report_accepted=validated["validation"]["accepted"],
                adapter_pass=adapter_pass,
                elapsed_seconds=time.monotonic() - started,
            )
            write(session / "receipt.json", receipt)
            row = {
                k: receipt[k]
                for k in (
                    "case",
                    "returncode",
                    "timed_out",
                    "execution_pass",
                    "valid_environment",
                    "raw_report_accepted",
                    "adapter_pass",
                    "usage",
                )
            }
            summary["sessions"].append(row)
            write(root / "summary.json", summary)
            print(json.dumps(row), flush=True)
            if (
                code
                or timed_out
                or not receipt["execution_pass"]
                or not receipt["valid_environment"]
                or not adapter_pass
            ):
                raise RuntimeError("qualified execution/adapter gate failed; no regrade or retry")
    except Exception as exc:
        summary["stop_reason"] = str(exc)
        write(root / "summary.json", summary)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
