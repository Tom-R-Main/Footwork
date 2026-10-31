"""Explicit owned CDP CLI. Restart retrieves state; it never recreates input authority."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="footwork browser cdp", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="launch a new owned headless browser and durable holder")
    start.add_argument("task")
    start.add_argument("--session", type=Path, required=True, help="fresh private directory; short absolute path")
    start.add_argument("--authority", type=Path, required=True, help="absolute durable authority database")
    start.add_argument("--url", required=True, help="initial page only; no navigation RPC")
    start.add_argument("--chrome", help="Chrome executable; otherwise use normal Chrome discovery")
    start.add_argument("--guard-command", type=Path, help="JSON argv file for a trusted judgment adapter; default Jev")
    for command in ("look", "click", "status", "recover", "stop"):
        selected = commands.add_parser(command)
        selected.add_argument("--session", type=Path, required=True)
        if command == "click":
            selected.add_argument("--ref", required=True, help="opaque ref from the last look; never reselected by label")
            selected.add_argument("--token", required=True, help="stable token for this intended activation")
        if command in ("status", "recover"):
            selected.add_argument("--token", help="inspect a retained operation by its original token")
    commands.add_parser("guide", help="installed, version-matched CDP loop and limitations")
    return parser


def discovery() -> dict:
    return {
        "profile": "owned-headless-cdp", "entrypoint": "footwork browser cdp",
        "commands": ["start", "look", "click", "status", "recover", "stop", "guide"],
        "requirements": ["Chrome", "psutil", "websockets", "configured Jev or judgment adapter", "absolute durable authority"],
        "desktop_required": False, "cua_required": False, "typing": "disabled: unresolved focus race",
        "activation": "dom_event_native_button: directly named plain main-document button[type=button] only",
        "completion": "unverified; acknowledgement is not business completion; unknown blocks new mutations",
        "restart": "same live holder or retained journal only; no implicit relaunch/adoption/rebinding",
        "install": "current package metadata still installs full dependencies; light metadata split is pending",
        "trust": "private socket and configured guard; not isolation from arbitrary code running as the same user",
    }


def guide() -> dict:
    from importlib.metadata import PackageNotFoundError, version

    try:
        installed = version("jevdual")
    except PackageNotFoundError:
        installed = "source-checkout"
    return {"package_version": installed, **discovery(), "loop": [
        "start TASK --session /short/fresh/dir --authority /absolute/authority.db --url URL",
        "look --session DIR; choose the exact opaque ref returned by this holder",
        "click --session DIR --ref REF --token STABLE_INTENT_TOKEN; read operation state and evidence",
        "status --session DIR --token TOKEN; repeat the exact click request only to retrieve its retained record",
        "recover --session DIR after holder loss: read-only recovery; no browser is launched",
        "stop --session DIR; retain the authority database and all unresolved operations",
    ], "guard_adapter": {
        "configuration": "--guard-command FILE containing JSON argv, absolute executable first; trusted policy code",
        "stdin": "footwork.browser.guard.request v1: digest, task, targets, url, title, binding",
        "stdout": "{producer:footwork.browser.guard,version:1,digest:<same>,probabilities:[p]}",
        "semantics": "same Authorizer keyword checks and destructive threshold; absent, malformed or failed judgment refuses",
    }, "limits": [
        "An acknowledged activation remains unknown/unverified without a qualified operation-specific completion reader.",
        "This tranche has no browser completion reader: recover preserves uncertainty, it cannot mark an effect completed.",
        "A new token cannot clear an unresolved admission, even across sessions sharing this authority database.",
        "No typing, trusted input, arbitrary evaluation, navigation RPC, grant bypass or raw CDP endpoint is exposed by this CLI.",
        "The owned Chrome still uses loopback CDP; private transport is not exclusive custody against same-user code.",
        "Initial URL loading can itself have website effects; it is setup outside the guarded click protocol.",
    ]}


def _config(path: Path) -> dict:
    from .browser_holder import CONFIG_FILE

    if not path.is_absolute() or path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError("session must be an absolute private directory")
    config_path = path / CONFIG_FILE
    if config_path.is_symlink() or config_path.stat().st_mode & 0o077:
        raise ValueError("session config must be private")
    if config_path.stat().st_size > 65536:
        raise ValueError("session config too large")
    config = json.loads(config_path.read_text())
    if config.get("version") != 1 or not Path(config["authority"]).is_absolute():
        raise ValueError("unsupported session config")
    return config


def _start(args) -> dict:
    from urllib.parse import urlsplit

    from .browser_driver import chrome_executable
    from .browser_holder import CONFIG_FILE, HOLDER_FILE

    if not args.session.is_absolute() or not args.authority.is_absolute():
        raise ValueError("session and authority paths must be absolute")
    if len(os.fsencode(args.session / "holder.sock")) > 100:
        raise ValueError("session path exceeds Unix socket bound; choose a shorter path")
    if urlsplit(args.url).scheme not in ("http", "https"):
        raise ValueError("initial URL must use http or https")
    command = None
    if args.guard_command:
        if args.guard_command.stat().st_size > 65536:
            raise ValueError("guard argv file too large")
        command = json.loads(args.guard_command.read_text())
        if (not isinstance(command, list) or not command or len(command) > 32
                or any(not isinstance(x, str) or not x for x in command)
                or not os.path.isabs(command[0])):
            raise ValueError("guard argv needs an absolute executable and string arguments")
    chrome = args.chrome or chrome_executable()
    args.session.mkdir(mode=0o700, parents=True, exist_ok=False)
    config = {"version": 1, "session_id": "cdp_" + uuid.uuid4().hex, "task": args.task,
              "chrome": chrome, "initial_url": args.url, "authority": str(args.authority), "guard_command": command}
    with (args.session / CONFIG_FILE).open("x") as stream:
        os.chmod(stream.name, 0o600)
        json.dump(config, stream, allow_nan=False)
    process = subprocess.Popen([sys.executable, "-m", "jevdual.browser_holder", "--session", str(args.session)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ValueError("holder failed before readiness; no browser authority was established")
        if (args.session / HOLDER_FILE).exists():
            result = asyncio.run(_remote(args.session, "status"))
            if result.get("ok"):
                return {"ok": True, "session_id": config["session_id"], "profile": discovery(), "holder": result}
        time.sleep(0.05)
    process.terminate()  # direct child, never a PID read from metadata
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
    raise ValueError("holder readiness timed out; inspect retained authority before another start")


async def _remote(session: Path, method: str, **fields) -> dict:
    from .browser_holder import request

    return await request(session, method, **fields)


def main(argv: list[str] | None = None) -> int:
    from .capability.journal import JournalError

    args = build_parser().parse_args(argv)
    try:
        if args.command == "guide":
            result = guide()
        elif args.command == "start":
            result = _start(args)
        else:
            config = _config(args.session)
            if args.command in ("status", "recover"):
                try:
                    result = asyncio.run(_remote(args.session, "status"))
                    if not result.get("ok"):
                        raise OSError("holder unavailable")
                except (OSError, ValueError, RuntimeError, TimeoutError):
                    from .browser_authority import BrowserAuthority, operation_record

                    with BrowserAuthority(Path(config["authority"])) as authority:
                        ops = [authority.reconcile(op.id) for op in authority.status(config["session_id"])]
                        result = {"ok": True, "holder": "unavailable; no relaunch attempted",
                                  "session_id": config["session_id"], "operations": [operation_record(op) for op in ops]}
                if args.token:
                    result["operations"] = [op for op in result["operations"] if op["client_token"] == args.token]
            else:
                fields = {"token": args.token, "ref": args.ref} if args.command == "click" else {}
                try:
                    result = asyncio.run(_remote(args.session, args.command, **fields))
                except (OSError, ValueError, RuntimeError, TimeoutError):
                    if args.command != "click":
                        raise
                    # A missing holder cannot renew mutation authority. Token replay is a
                    # read-only journal lookup, including after holder or browser death.
                    from .browser_authority import ROUTE, BrowserAuthority, operation_record

                    with BrowserAuthority(Path(config["authority"])) as authority:
                        prior = authority.by_request(config["session_id"], args.token,
                                                     {"ref": args.ref, "route": ROUTE})
                        if prior is None:
                            raise ValueError("no retained operation; holder unavailable") from None
                        result = {"ok": True, "replayed": True, "holder": "unavailable",
                                  "operation": operation_record(authority.reconcile(prior.id))}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0 if result.get("ok", True) else 3
    except (OSError, ValueError, RuntimeError, TimeoutError, JournalError) as exc:
        # Never echo untrusted guard/page content or exception payloads.
        print(json.dumps({"ok": False, "code": getattr(exc, "code", "browser_session_unavailable"),
                          "message": "request refused; inspect retained authority; no automatic retry",
                          "error_type": type(exc).__name__}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
