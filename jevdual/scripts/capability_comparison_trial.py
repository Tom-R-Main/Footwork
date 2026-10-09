"""Frozen C1 runner: paired fresh hosts, real raw tools, exact independent AX oracle.

Use --plan to save the fixed schedule without model calls. --execute requires
an existing owned fixture and the qualified pinned runtime. No measured trial is
retried. Full transcript/journal/relay evidence remains private in project output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from capability_baseline_probe import NATIVE_TOOLS, native_manifest, raw_parameters
from capability_host_trial import ax_document_text, ax_reset_text

MODEL = "claude-opus-5-5"
EFFORT = "high"
SESSION_CAP = 1.0
TOTAL_CAP = 30.0
TIMEOUT = 180
RAW_BROWSER = ("list_pages", "take_snapshot")
RELAY = Path(__file__).with_name("capability_comparison_relay.py").resolve()
PREFIXES = ("Invoice report\n", "Invoice report", "", "Invoice report\n\tkept  \n\n")
TASKS = [
    {
        "id": f"{mode}-{i + 1}",
        "stratum": mode,
        "prefix": prefix,
        "value": "17.25 USD",
        "stale_prefix": prefix + "External note: preserve this edit.\n",
    }
    for mode, prefixes in (("clean", PREFIXES), ("interrupted", PREFIXES), ("stale", PREFIXES[:2]))
    for i, prefix in enumerate(prefixes)
]


def schedule() -> list[dict[str, Any]]:
    blocks = []
    for repeat in range(3):
        offset = repeat * 4 % len(TASKS)
        for task in TASKS[offset:] + TASKS[:offset]:
            order = ("footwork", "raw") if len(blocks) % 4 in (0, 3) else ("raw", "footwork")
            blocks.append({"block": len(blocks) + 1, "repeat": repeat + 1, "task": task, "order": order})
    return blocks


def expected_text(prefix: str, value: str) -> str:
    return prefix + ("" if not prefix or prefix.endswith("\n") else "\n") + value


def prompt(scope: dict[str, Any]) -> str:
    dst = scope["destination"]
    return (
        "Read the invoice total shown on the source page and append exactly that total — nothing else — "
        "to the destination document. Preserve every existing character. If the document is nonempty "
        "and does not end with a newline, separate the append with one newline; otherwise insert the "
        "total directly at the end. Tell me when it is done and how you know.\n"
        f"Source page: {scope['source']['url']}\n"
        f"Destination: TextEdit document {dst['document']}; pid {dst['pid']}, window_id {dst['window_id']}.\n"
        "Use only the supplied MCP tools."
    )


def config_for(
    arm: str, root: Path, scope_path: Path, runtime: dict, browser_url: str, task: dict
) -> tuple[dict, list[str], list[str]]:
    scope = json.loads(scope_path.read_text())
    destination = scope["destination"]
    relay_dir = root / "relay"
    relay_dir.mkdir(mode=0o700)
    cfg: dict[str, Any] = {
        "mode": task["stratum"],
        "prefix": task["prefix"],
        "stale_prefix": task["stale_prefix"],
        "oracle": {"kind": "ax", "pid": destination["pid"], "document": destination["document"]},
    }
    if arm == "footwork":
        journal = root / "operations.sqlite"
        cfg.update(
            {
                "argv": [
                    sys.executable,
                    "-m",
                    "jevdual.capability.mcp_server",
                    "--scope",
                    str(scope_path),
                    "--journal",
                    str(journal),
                ],
                "journal": str(journal),
                "mutation_tools": ["act"],
                "observation_tools": ["observe"],
            }
        )
        servers = {
            "footwork": {
                "command": sys.executable,
                "args": [str(RELAY), "--config", str(relay_dir / "config.json")],
            }
        }
        tools = [f"mcp__footwork__{t}" for t in ("bind", "observe", "act", "status")]
        disallowed = []
    else:
        manifest = root / "native-manifest.yaml"
        manifest.write_text(native_manifest(destination))
        (root / "native-policy.yaml").write_text(f"allow:\n  tools: [{', '.join(NATIVE_TOOLS)}]\n")
        params = raw_parameters(runtime, manifest, browser_url)
        cfg.update(
            {
                "argv": [params["native"].command, *params["native"].args],
                # Only trusted overrides; never serialize inherited environment/secrets.
                "env": {
                    k: v
                    for k, v in params["native"].env.items()
                    if k.startswith("CUA_DRIVER_")
                    and k
                    in {
                        "CUA_DRIVER_PERMISSION_MODE",
                        "CUA_DRIVER_CAPABILITY_MANIFEST_FILE",
                        "CUA_DRIVER_CAPABILITY_MANIFEST_APPROVED",
                        "CUA_DRIVER_POLICY_FILE",
                    }
                },
                "mutation_tools": ["set_value", "type_text"],
                "observation_tools": ["get_window_state"],
            }
        )
        chrome = params["chrome"]
        servers = {
            "chrome": {"command": chrome.command, "args": chrome.args + ["--workspace", str(root)]},
            "native": {
                "command": sys.executable,
                "args": [str(RELAY), "--config", str(relay_dir / "config.json")],
            },
        }
        tools = [*[f"mcp__chrome__{t}" for t in RAW_BROWSER], *[f"mcp__native__{t}" for t in NATIVE_TOOLS]]
        # Host removes out-of-scope browser capabilities, preserving raw schemas.
        catalog = json.loads(Path(runtime["catalog_path"]).read_text())["tools"]
        disallowed = [f"mcp__chrome__{t['name']}" for t in catalog if t["name"] not in RAW_BROWSER]
    (relay_dir / "config.json").write_text(json.dumps(cfg, indent=2))
    return {"mcpServers": servers}, tools, disallowed


def host_command(config: Path, tools: list[str], disallowed: list[str]) -> list[str]:
    cmd = [
        "/Users/thomasmain/.local/bin/claude",
        "-p",
        "--strict-mcp-config",
        "--mcp-config",
        str(config),
        "--setting-sources",
        "",
        "--settings",
        json.dumps({"disableAllHooks": True}),
        "--tools",
        "",
        "--allowedTools",
        ",".join(tools),
        "--disable-slash-commands",
        "--model",
        MODEL,
        "--effort",
        EFFORT,
        "--max-budget-usd",
        str(SESSION_CAP),
        "--no-session-persistence",
        "--output-format",
        "stream-json",
        "--verbose",
    ]
    if disallowed:
        cmd += ["--disallowedTools", ",".join(disallowed)]
    return cmd


def parse_transcript(path: Path, offered: list[str], servers: list[str]) -> dict[str, Any]:
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    calls = [
        block["name"]
        for e in events
        for block in (e.get("message") or {}).get("content") or []
        if block.get("type") == "tool_use"
    ]
    environment = (
        sorted(init.get("tools", [])) == sorted(offered)
        and sorted(s["name"] for s in init.get("mcp_servers", [])) == sorted(servers)
        and init.get("model") == MODEL
    )
    return {
        "valid_environment": environment,
        "tools_offered": init.get("tools"),
        "mcp_servers": init.get("mcp_servers"),
        "model": init.get("model"),
        "host_version": init.get("claude_code_version"),
        "calls": calls,
        "out_of_arm": [c for c in calls if c not in offered],
        "final": result.get("result"),
        "result_is_error": result.get("is_error", True),
        "result_subtype": result.get("subtype"),
        "cost_usd": result.get("total_cost_usd"),
        "model_usage": result.get("modelUsage"),
        "claim_review": None,
    }


def run_host(cmd: list[str], task_prompt: str, root: Path) -> tuple[int, bool]:
    with (
        tempfile.TemporaryDirectory(prefix="footwork-c1-") as cwd,
        (root / "transcript.jsonl").open("w") as out,
        (root / "host-stderr.log").open("w") as err,
    ):
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=out, stderr=err, text=True, cwd=cwd, start_new_session=True
        )
        try:
            proc.communicate(task_prompt, timeout=TIMEOUT)
            return proc.returncode, False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
            return proc.returncode, True


def relay_events(root: Path) -> list[dict]:
    path = root / "relay/events.jsonl"
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--browser-url")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--development-blocks", type=int, default=0)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[2]
    root = args.run_dir.resolve()
    if not root.is_relative_to(project / "output"):
        parser.error("output must stay inside this project's private output directory")
    if args.plan:
        root.mkdir(parents=True, mode=0o700, exist_ok=False)
        (root / "schedule.json").write_text(json.dumps(schedule(), indent=2))
        print(
            json.dumps(
                {"sessions": 60, "blocks": 30, "session_cap_usd": SESSION_CAP, "total_cap_usd": TOTAL_CAP}
            )
        )
        return
    if not args.execute:
        print("Dry run: use --plan for the fixed schedule, or --execute for the qualified fixture.")
        return
    if not all((args.scope, args.runtime, args.catalog, args.browser_url)):
        parser.error("execution requires --scope --runtime --catalog --browser-url")
    from ApplicationServices import AXIsProcessTrusted
    from jevdual.posture import screen_locked

    if screen_locked() or not AXIsProcessTrusted():
        parser.error("unlocked desktop and existing Accessibility permission required")
    scope_path = args.scope.resolve()
    scope = json.loads(scope_path.read_text())
    runtime = json.loads(args.runtime.read_text())
    runtime["catalog_path"] = str(args.catalog.resolve())
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    blocks = schedule()
    if args.development_blocks:
        if not 1 <= args.development_blocks <= 3:
            parser.error("development probes limited to 1–3 blocks; never reported as C1")
        # One clean, one interrupted, one stale pair in development.
        blocks = [
            next(b for b in blocks if b["task"]["stratum"] == stratum)
            for stratum in ("clean", "interrupted", "stale")
        ][: args.development_blocks]
    (root / "schedule.json").write_text(json.dumps(blocks, indent=2))
    measured = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip()
    summary: dict[str, Any] = {
        "commit": measured,
        "development": bool(args.development_blocks),
        "sessions": [],
        "total_cost_usd": 0.0,
        "stop_reason": None,
        "relay_sha256": hashlib.sha256(RELAY.read_bytes()).hexdigest(),
    }
    destination = scope["destination"]
    for block in blocks:
        if summary["total_cost_usd"] + 2 * SESSION_CAP > TOTAL_CAP:
            summary["stop_reason"] = "aggregate_budget_reserve"
            break
        for arm in block["order"]:
            task = block["task"]
            session = root / f"b{block['block']:02}-{arm}"
            session.mkdir(mode=0o700)
            ax_reset_text(destination["pid"], destination["document"], task["prefix"])
            if (
                screen_locked()
                or ax_document_text(destination["pid"], destination["document"]) != task["prefix"]
            ):
                summary["stop_reason"] = "fixture_prerequisite"
                break
            cfg, tools, disallowed = config_for(arm, session, scope_path, runtime, args.browser_url, task)
            config = session / "mcp.json"
            config.write_text(json.dumps(cfg, indent=2))
            cmd = host_command(config, tools, disallowed)
            (session / "command.json").write_text(json.dumps(cmd))
            task_prompt = prompt(scope)
            (session / "prompt.txt").write_text(task_prompt)
            start = time.monotonic()
            code, timed_out = run_host(cmd, task_prompt, session)
            evidence = parse_transcript(session / "transcript.jsonl", tools, list(cfg["mcpServers"]))
            events = relay_events(session)
            treatment = any(
                e["kind"] == ("dropped" if task["stratum"] == "interrupted" else "stale_injected")
                for e in events
            )
            invalid = any(e["kind"] == "invalid" for e in events)
            actual = ax_document_text(destination["pid"], destination["document"])
            preserved = task["stale_prefix"] if task["stratum"] == "stale" and treatment else task["prefix"]
            expected = expected_text(preserved, task["value"])
            evidence.update(
                {
                    "arm": arm,
                    "block": block["block"],
                    "task_id": task["id"],
                    "stratum": task["stratum"],
                    "returncode": code,
                    "timed_out": timed_out,
                    "elapsed_seconds": time.monotonic() - start,
                    "oracle_exact": actual == expected,
                    "oracle_unchanged": actual == preserved,
                    "oracle_actual": actual,
                    "oracle_expected": expected,
                    "treatment_applied": treatment,
                    "harness_invalid": invalid
                    or not evidence["valid_environment"]
                    or (task["stratum"] != "clean" and not treatment),
                    "relay_events": events,
                }
            )
            (session / "receipt.json").write_text(json.dumps(evidence, indent=2))
            summary["sessions"].append(
                {
                    "path": session.name,
                    "arm": arm,
                    "stratum": task["stratum"],
                    "oracle_exact": evidence["oracle_exact"],
                    "harness_invalid": evidence["harness_invalid"],
                    "cost_usd": evidence["cost_usd"],
                }
            )
            cost = evidence["cost_usd"]
            if not isinstance(cost, (int, float)) or cost < 0:
                summary["stop_reason"] = "cost_unavailable"
            else:
                summary["total_cost_usd"] += cost
            (root / "summary.json").write_text(json.dumps(summary, indent=2))
            print(json.dumps(summary["sessions"][-1]), flush=True)
            if evidence["harness_invalid"] and args.development_blocks:
                summary["stop_reason"] = "development_harness_invalid"
            if summary["stop_reason"]:
                break
        if summary["stop_reason"]:
            break
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        json.dumps(
            {
                "sessions": len(summary["sessions"]),
                "cost_usd": summary["total_cost_usd"],
                "stop_reason": summary["stop_reason"],
                "claim_review_pending": True,
            }
        )
    )


if __name__ == "__main__":
    main()
