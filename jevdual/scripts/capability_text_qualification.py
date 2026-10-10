"""Six fresh-host developmental text-repair cases. Plan-only unless --execute.

Uses the qualified isolated host/relay and independent AX oracle. No C1 retry,
reference edits, installations or permission changes. Requires committed source.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import sqlite3
import subprocess
import time
from pathlib import Path

from capability_comparison_trial import (
    config_for,
    host_command,
    parse_transcript,
    prompt,
    retire_backends,
    run_host,
)
from capability_host_trial import OracleError, ax_document_text, ax_reset_text

CASES = (
    ("newline-ended", "Invoice report\n", "Invoice report\n17.25 USD"),
    ("no-newline", "Invoice report", "Invoice report\n17.25 USD"),
    ("empty", "", "17.25 USD"),
    ("preserved-whitespace", "Invoice report\n\tkept  \n\n", "Invoice report\n\tkept  \n\n17.25 USD"),
    ("intentional-blank-line", "Invoice report", "Invoice report\n\n17.25 USD"),
    ("whitespace-only", " \t\n\n", " \t\n\n17.25 USD"),
)
CEILING = 8.0


def task_prompt(scope: dict, case_id: str) -> str:
    request = prompt(scope)
    if case_id == "intentional-blank-line":
        original = (
            "If the document is nonempty and does not end with a newline, separate the append "
            "with one newline; otherwise insert the total directly at the end."
        )
        assert original in request, "shared task wording changed; requalify this prompt"
        request = request.replace(
            original,
            "Put the total on a new line, separated from the existing "
            "text by exactly one intentionally blank line.",
        )
    return request


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--prior-cost", type=float, default=0.0)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[2]
    root = args.run_dir.resolve()
    if not root.is_relative_to(project / "output"):
        parser.error("output must stay inside this project's private output")
    if not args.execute:
        print(json.dumps({"developmental": True, "cases": CASES, "execute": False}, indent=2))
        return
    if args.scope is None or not math.isfinite(args.prior_cost) or not 0 <= args.prior_cost < CEILING:
        parser.error("execution requires scope and a finite prior cost below the $8 ceiling")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=project, text=True).strip():
        parser.error("commit source first; paid qualification requires a clean worktree")
    from ApplicationServices import AXIsProcessTrusted
    from jevdual.posture import screen_locked

    if screen_locked() or not AXIsProcessTrusted():
        parser.error("unlocked desktop and existing Accessibility permission required")
    scope_path = args.scope.resolve()
    scope = json.loads(scope_path.read_text())
    dst = scope["destination"]
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    (root / "cases.json").write_text(json.dumps(CASES, indent=2))
    paths = [Path(__file__).resolve(), project / "jevdual/uv.lock"]
    paths += sorted((project / "jevdual/python/jevdual/capability").glob("*.py"))
    paths += [project / f"jevdual/python/jevdual/{name}.py" for name in ("ax", "native")]
    paths += [
        Path(__file__).with_name(name)
        for name in (
            "capability_comparison_trial.py",
            "capability_comparison_relay.py",
            "capability_host_trial.py",
        )
    ]
    summary = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip(),
        "developmental": True,
        "C1_retry": False,
        "module_hashes": {
            str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
        },
        "scope_sha256": hashlib.sha256(scope_path.read_bytes()).hexdigest(),
        "sessions": [],
        "cost_usd": 0.0,
        "prior_cost_usd": args.prior_cost,
        "budget_upper_bound_usd": args.prior_cost,
        "stop_reason": None,
        "claim_review_pending": True,
    }
    for case_id, prefix, expected in CASES:
        # CLI caps are soft at turn boundaries; reserve twice the requested $1.
        if summary["budget_upper_bound_usd"] + 2 > CEILING:
            summary["stop_reason"] = "aggregate_budget_reserve"
            break
        session = root / case_id
        session.mkdir(mode=0o700)
        ax_reset_text(dst["pid"], dst["document"], prefix)
        if screen_locked() or ax_document_text(dst["pid"], dst["document"]) != prefix:
            summary["stop_reason"] = "fixture_prerequisite"
            break
        task = {"stratum": "clean", "prefix": prefix, "stale_prefix": prefix}
        cfg, tools, disallowed = config_for("footwork", session, scope_path, {}, "", task)
        config = session / "mcp.json"
        config.write_text(json.dumps(cfg, indent=2))
        command = host_command(config, tools, disallowed)
        (session / "command.json").write_text(json.dumps(command, indent=2))
        request = task_prompt(scope, case_id)
        (session / "prompt.txt").write_text(request)
        start = time.monotonic()
        code, timed_out = run_host(command, request, session)
        retired = retire_backends(session)
        receipt = parse_transcript(session / "transcript.jsonl", tools, list(cfg["mcpServers"]))
        actual, oracle_error, journal = None, None, []
        try:
            if not retired:
                raise RuntimeError("owned backend retirement unqualified")
            first = ax_document_text(dst["pid"], dst["document"])
            time.sleep(0.2)
            actual = ax_document_text(dst["pid"], dst["document"])
            if actual != first:
                raise RuntimeError("post-teardown independent AX reads differ")
            with contextlib.closing(
                sqlite3.connect(f"file:{session / 'operations.sqlite'}?mode=ro", uri=True)
            ) as db:
                db.row_factory = sqlite3.Row
                journal = [dict(row) for row in db.execute("SELECT id,state,disposition FROM operations")]
        except (OracleError, RuntimeError, sqlite3.Error) as exc:
            oracle_error = type(exc).__name__ + ": " + str(exc)[:160]
        receipt.update(
            {
                "case": case_id,
                "returncode": code,
                "timed_out": timed_out,
                "elapsed_seconds": time.monotonic() - start,
                "backends_retired": retired,
                "oracle_actual": actual,
                "oracle_expected": expected,
                "oracle_exact": actual == expected,
                "oracle_error": oracle_error,
                "journal": journal,
                "one_applied": len(journal) == 1 and journal[0]["disposition"] == "applied",
            }
        )
        receipt["harness_invalid"] = oracle_error is not None or not receipt["valid_environment"]
        (session / "receipt.json").write_text(json.dumps(receipt, indent=2))
        cost = receipt["cost_usd"]
        if not isinstance(cost, (float, int)) or not math.isfinite(cost) or cost < 0:
            summary["budget_upper_bound_usd"] += 2
            summary["stop_reason"] = "cost_unavailable"
        else:
            summary["cost_usd"] += cost
            summary["budget_upper_bound_usd"] += cost
        summary["sessions"].append(
            {
                key: receipt[key]
                for key in ("case", "oracle_exact", "one_applied", "harness_invalid", "cost_usd")
            }
        )
        if receipt["harness_invalid"]:
            summary["stop_reason"] = "invalid_environment_or_oracle"
        elif not receipt["oracle_exact"] or not receipt["one_applied"]:
            summary["stop_reason"] = "development_failure"
        (root / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary["sessions"][-1]), flush=True)
        if summary["stop_reason"]:
            break
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        json.dumps(
            {
                "sessions": len(summary["sessions"]),
                "cost_usd": summary["cost_usd"],
                "stop_reason": summary["stop_reason"],
                "claim_review_pending": True,
            }
        )
    )


if __name__ == "__main__":
    main()
