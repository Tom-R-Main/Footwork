"""Structured capability entry points; host reports fail closed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .completion import ReportError, unavailable_summary, validate_from_journal

MAX_REPORT_BYTES = 65536


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="footwork-capability")
    sub = parser.add_subparsers(dest="command", required=True)
    server = sub.add_parser("server", help="Serve scoped capability tools over MCP stdio")
    server.add_argument("--scope", type=Path, required=True)
    server.add_argument("--journal", type=Path, required=True)
    report = sub.add_parser(
        "report", help="Validate structured operation claims; never publish raw model prose"
    )
    report.add_argument("--journal", type=Path, required=True)
    report.add_argument("--task", required=True)
    report.add_argument("--input", type=Path)
    report.add_argument(
        "--summary", action="store_true", help="Print only the trusted human-readable summary"
    )
    config = sub.add_parser("config", help="Create a private per-job run and ephemeral MCP configuration")
    config.add_argument("--run-dir", type=Path, required=True)
    config.add_argument("--source-pid", type=int, required=True)
    config.add_argument("--source-window", type=int, required=True)
    config.add_argument("--source-url", required=True)
    config.add_argument("--destination-pid", type=int, required=True)
    config.add_argument("--destination-window", type=int, required=True)
    config.add_argument("--document", type=Path, required=True)
    diagnostics = sub.add_parser(
        "doctor", help="Read prerequisites without requesting permissions or starting apps"
    )
    diagnostics.add_argument("--scope", type=Path)
    diagnostics.add_argument("--journal", type=Path)
    diagnostics.add_argument("--strict", action="store_true", help="Exit 1 when prerequisites are blocked")
    args = parser.parse_args(argv)
    if args.command == "server":
        from .mcp_server import main as serve

        return serve(["--scope", str(args.scope), "--journal", str(args.journal)])
    if args.command in ("doctor", "config"):
        from .contracts import CapabilityError
        from .setup import doctor, make_config

        try:
            if args.command == "doctor":
                result = doctor(args.scope, args.journal)
            else:
                result = make_config(
                    args.run_dir,
                    source_pid=args.source_pid,
                    source_window=args.source_window,
                    source_url=args.source_url,
                    destination_pid=args.destination_pid,
                    destination_window=args.destination_window,
                    document=args.document,
                )
            print(json.dumps(result, ensure_ascii=False))
            if args.command == "doctor" and args.strict and result["prerequisite_status"] == "blocked":
                return 1
            return 0
        except (OSError, ValueError, CapabilityError):
            print(
                json.dumps(
                    {
                        "error": "invalid_configuration",
                        "message": "Check scope arguments and use a new owned run directory.",
                    }
                )
            )
            return 2
    try:
        if args.input:
            with args.input.open("rb") as stream:
                raw = stream.read(MAX_REPORT_BYTES + 1)
        else:
            raw = sys.stdin.buffer.read(MAX_REPORT_BYTES + 1)
        if len(raw) > MAX_REPORT_BYTES:
            raise ReportError("Report exceeds input bound")
        value = json.loads(raw)
        validated = validate_from_journal(args.journal, args.task, value)
        code = 0 if validated["validation"]["accepted"] else 1
    except (ReportError, OSError, ValueError, RecursionError):
        validated, code = unavailable_summary(), 2
    print(validated["trusted_summary"] if args.summary else json.dumps(validated, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
