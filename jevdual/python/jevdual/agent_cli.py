"""Installed agent command router; execution success never implies a verified effect."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections.abc import Callable
from pathlib import Path

LEGACY = (
    "run",
    "menu",
    "apps",
    "start",
    "look",
    "inspect-target",
    "visual-check",
    "do",
    "s1",
    "done",
    "read",
    "check-file",
    "check-artifact",
    "grant",
    "snapshot-file",
    "status",
)
SESSION = {
    "look",
    "inspect-target",
    "visual-check",
    "do",
    "s1",
    "done",
    "read",
    "grant",
    "snapshot-file",
    "check-file",
    "status",
}


class RoutingError(ValueError):
    pass


def catalog() -> dict:
    from .tool_catalog import catalog as auxiliary

    desktop_route = {
        "darwin": "native macOS accessibility",
        "linux": "native Linux X11/AT-SPI; live target binding required",
    }.get(sys.platform, "native desktop unsupported on this platform")
    capability_scope = {
        "darwin": "one configured browser-to-TextEdit job",
        "linux": "one configured browser-to-Mousepad job on X11/AT-SPI; Wayland and shared foreground unqualified",
    }.get(sys.platform, "native capability unsupported on this platform")
    return {
        "schema_version": "1",
        "entrypoint": "footwork",
        "global_options": {
            "--json": "Prefix before the command; preserves exit status and does not certify effects"
        },
        "commands": list(LEGACY),
        "agent_commands": ["tools", "catalog", "schema", "doctor", "invoke", "capability", "mcp", "tool"],
        "surfaces": {
            "browser": {"commands": ["start", *sorted(SESSION)], "route": "dedicated Chrome / CUA DevTools"},
            "desktop": {"commands": list(LEGACY), "route": desktop_route},
        },
        "capability": {
            "commands": ["doctor", "config", "server", "report"],
            "scope": capability_scope,
        },
        "tools": auxiliary(),
        "effect_semantics": "Read action receipts and resource-bound readback; exit 0 alone is not completion proof",
    }


def _emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False))


def _help() -> None:
    print(
        "usage: footwork [--json] COMMAND ...\n\n"
        "Agent discovery: tools (or catalog), schema [COMMAND ...], doctor\n"
        "JSON input: invoke --input FILE (or - for stdin), request {command,args}\n"
        "Browser: browser start TASK --url URL --session DIR; browser look/do/read/done/status ...\n"
        "Desktop: desktop start TASK --app APP --session DIR; desktop look/do/read/done/status ...\n"
        "Scoped MCP: capability {config,server,report,doctor}; mcp --scope FILE --journal FILE\n"
        "Auxiliary tools: tool FAMILY COMMAND ... (or FAMILY COMMAND ...)\n"
        "Use footwork tools to discover families and prerequisites; schema COMMAND for arguments.\n"
        "Prefix --json for structured output; command completion is not effect verification.\n\n"
        "Legacy commands: " + ", ".join(LEGACY)
    )


def _surface_args(surface: str, args: list[str]) -> list[str]:
    if not args or args == ["--help"] or args == ["-h"]:
        print(f"usage: footwork {surface} COMMAND ...\nUse footwork schema {surface} COMMAND for arguments.")
        return []
    command = args[0]
    permitted = set(LEGACY) if surface == "desktop" else SESSION | {"start"}
    if command not in permitted:
        raise RoutingError(f"{command!r} is not supported by the {surface} route")
    if command == "start":
        if surface == "browser":
            if "--app" in args or any(a.startswith("--app=") for a in args):
                raise RoutingError("browser start uses its dedicated Chrome; --app is a desktop option")
            return [args[0], "--browser", *args[1:]]
        if "--browser" in args:
            raise RoutingError("desktop start cannot select the browser route")
        if (
            "--app" not in args
            and not any(a.startswith("--app=") for a in args)
            and not any(a in ("--help", "-h") for a in args)
        ):
            raise RoutingError("desktop start requires --app to select the intended app")
    if command in SESSION and not any(a in ("--help", "-h") for a in args):
        from .session import SessionState, session_dir

        session = None
        for index, token in enumerate(args):
            if token == "--session" and index + 1 < len(args):
                session = args[index + 1]
            elif token.startswith("--session="):
                session = token.split("=", 1)[1]
        path = session_dir(session)
        if (path / "session.json").exists():
            mode = SessionState.load(path).mode
            if mode != ("browser" if surface == "browser" else "native"):
                raise RoutingError(f"The selected session belongs to a different surface than {surface}")
    return args


def _invoke_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="footwork invoke", description="Run one bounded JSON request through the normal command router"
    )
    parser.add_argument(
        "--input", default="-", help="JSON file or - for stdin; object with command:string and args:string[]"
    )
    return parser


def _invocation(args: list[str]) -> list[str]:
    parsed = _invoke_parser().parse_args(args)
    if parsed.input == "-":
        raw = getattr(sys.stdin, "buffer", sys.stdin).read(65537)
        raw = raw.encode("utf-8") if isinstance(raw, str) else raw
    else:
        with Path(parsed.input).open("rb") as stream:
            raw = stream.read(65537)
    if len(raw) > 65536:
        raise RoutingError("Invocation exceeds 65536 bytes")
    try:
        request = json.loads(raw)
    except (ValueError, RecursionError):
        raise RoutingError("Invocation must be a JSON object with command and args") from None
    if (
        not isinstance(request, dict)
        or set(request) != {"command", "args"}
        or not isinstance(request["command"], str)
        or not request["command"]
        or request["command"].startswith("-")
        or request["command"] == "invoke"
        or not isinstance(request["args"], list)
        or len(request["args"]) > 256
        or not all(isinstance(arg, str) and "\0" not in arg for arg in request["args"])
    ):
        raise RoutingError("Invocation requires a non-recursive command and at most 256 string arguments")
    return [request["command"], *request["args"]]


def _schema(args: list[str]) -> dict:
    if not args:
        return {
            "catalog": catalog(),
            "envelope": {
                "schema_version": "1",
                "exit_code": "integer",
                "command_completed": "exit_code == 0",
                "effect_verification": "not_asserted",
                "output": "captured non-JSON stdout; empty when decoded into data",
                "diagnostics": "captured stderr",
                "data": "decoded JSON output when available",
            },
        }
    if args[0] in ("browser", "desktop"):
        if len(args) == 1:
            return catalog()["surfaces"][args[0]]
        args = args[1:]
    if args[0] in ("catalog", "tools"):
        return {"command": args, "arguments": [], "output": "capability catalog"}
    if args == ["tool"]:
        return {"command": args, "families": catalog()["tools"]}
    if args == ["schema"]:
        return {"command": args, "arguments": [{"name": "command", "nargs": "*", "required": False}]}
    from .tool_catalog import catalog as auxiliary

    family_args = args[1:] if args and args[0] == "tool" else args
    family = next((f for f in auxiliary() if f["name"] == family_args[0]), None) if family_args else None
    if family:
        if len(family_args) > 1:
            from .tool_catalog import command_schema

            result = command_schema(family_args[0], family_args[1])
            return {"command": family_args, "invocation": ["footwork", *family_args], **result}
        return family
    if args and args[0] in ("doctor", "capability", "mcp"):
        from .capability.cli import build_parser

        selected = (
            args[1:] if args[0] == "capability" else ["server" if args[0] == "mcp" else "doctor", *args[1:]]
        )
    else:
        from .cli import build_parser

        selected = args
    parser = _invoke_parser() if selected and selected[0] == "invoke" else build_parser()
    if selected and selected[0] == "invoke":
        selected = selected[1:]
    for token in selected:
        actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        if not actions or token not in actions[0].choices:
            raise RoutingError("Unknown command; use footwork tools")
        parser = actions[0].choices[token]
    options = []
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            continue
        options.append(
            {
                "name": a.dest,
                "flags": a.option_strings,
                "required": a.required,
                "nargs": a.nargs,
                "choices": list(a.choices) if a.choices is not None else None,
                "help": a.help,
                "default": a.default if isinstance(a.default, (str, int, float, bool, type(None))) else None,
            }
        )
    children = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    return {
        "command": args,
        "arguments": options,
        "subcommands": sorted(children[0].choices) if children else [],
    }


def _doctor(args: list[str]) -> int:
    from ._native import acceleration_status
    from .capability.cli import main as capability
    from .host_probe import probe
    from .tool_catalog import catalog as auxiliary

    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            code = capability(["doctor", *args])
    except SystemExit:
        print(captured.getvalue(), end="")
        raise
    try:
        result = json.loads(captured.getvalue())
    except ValueError:
        print(captured.getvalue(), end="")
    else:
        result["acceleration"] = acceleration_status()
        result["host_prerequisites"] = probe()
        result["tool_families"] = auxiliary()
        result["effect_verification"] = "not_asserted"
        _emit(result)
    return code


def _dispatch(args: list[str], legacy: Callable[[list[str]], int], json_mode: bool) -> int:
    if not args or args in (["--help"], ["-h"]):
        _help()
        return 0
    command, rest = args[0], args[1:]
    if command in ("tools", "catalog"):
        if rest:
            raise RoutingError("tools takes no arguments; use schema FAMILY for details")
        _emit(catalog())
        return 0
    if command == "schema":
        result = _schema(rest)
        _emit(result)
        return 2 if result.get("error") else 0
    if command in ("doctor", "capability", "mcp"):
        from .capability.cli import main as capability

        if command == "doctor":
            return _doctor(rest)
        routed = ["server", *rest] if command == "mcp" else rest
        if json_mode and routed and routed[0] == "server":
            raise RoutingError("MCP server owns stdout; run without --json to preserve its protocol")
        return capability(routed)
    if command in ("browser", "desktop"):
        routed = _surface_args(command, rest)
        return legacy(routed) if routed else 0
    from .tool_catalog import catalog as auxiliary
    from .tool_catalog import run_tool

    if command == "tool":
        if not rest:
            raise RoutingError("tool requires a family; use footwork tools")
        return run_tool(rest[0], rest[1:])
    if command in {f["name"] for f in auxiliary()}:
        return run_tool(command, rest)
    return legacy(args)


def _redact_arguments(text: str, args: list[str]) -> str:
    for index, arg in enumerate(args):
        value = (
            args[index + 1]
            if arg == "--secret" and index + 1 < len(args)
            else arg.removeprefix("--secret=")
            if arg.startswith("--secret=")
            else None
        )
        if value:
            # Argument errors may format the original token with !r; escaped
            # newlines/backslashes must not bypass the ordinary value scrub.
            text = text.replace(repr(value), "[REDACTED]")
            secret = value.split("=", 1)[1] if "=" in value else value
            if secret:
                text = text.replace(secret, "[REDACTED]")
    return text


def route(argv: list[str] | None, legacy: Callable[[list[str]], int]) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    json_mode = bool(args and args[0] == "--json")
    if json_mode:
        args = args[1:]
    json_mode = json_mode or bool(args and args[0] == "invoke")
    output, diagnostics = io.StringIO(), io.StringIO()
    with contextlib.ExitStack() as stack:
        if json_mode:
            stack.enter_context(contextlib.redirect_stdout(output))
            stack.enter_context(contextlib.redirect_stderr(diagnostics))
        try:
            if args and args[0] == "invoke":
                args = _invocation(args[1:])
            code = _dispatch(args, legacy, json_mode)
            code = int(code or 0)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
            if exc.code is not None and not isinstance(exc.code, int):
                print(_redact_arguments(str(exc.code), args), file=sys.stderr)
        except (RoutingError, OSError, ValueError, ImportError) as exc:
            print(f"footwork: {exc}", file=sys.stderr)
            code = 2
    if json_mode:
        stdout, stderr = output.getvalue(), diagnostics.getvalue()
        stdout = _redact_arguments(stdout, args)
        stderr = _redact_arguments(stderr, args)
        try:
            data = json.loads(stdout)
        except (ValueError, RecursionError):
            data = None
        else:
            stdout = ""
        _emit(
            {
                "schema_version": "1",
                "exit_code": code,
                "command_completed": code == 0,
                "effect_verification": "not_asserted",
                "output": stdout,
                "diagnostics": stderr,
                "data": data,
            }
        )
    return code
