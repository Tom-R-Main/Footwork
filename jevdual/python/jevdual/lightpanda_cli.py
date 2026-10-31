"""One fresh owned Lightpanda connection, read-only content, then bounded cleanup."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import math
import shutil
import signal
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


class ReadRefused(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _timeout(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 1 <= number <= 60:
        raise argparse.ArgumentTypeError("timeout must be between 1 and 60 seconds")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="footwork browser lightpanda", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    read = sub.add_parser("read", help="read one URL with a fresh owned engine; sends no Footwork input")
    read.add_argument("url")
    read.add_argument("--executable", help="pinned prebuilt engine; otherwise FOOTWORK_LIGHTPANDA_EXECUTABLE or PATH")
    read.add_argument("--work-dir", type=Path, help="fresh short absolute engine directory; default private temporary storage")
    read.add_argument("--timeout", type=_timeout, default=30.0, help="overall capture deadline, excluding bounded cleanup")
    sub.add_parser("guide", help="installed read-only scope, engine pin and cleanup contract")
    selected = sub.add_parser("artifact", help="show the external pinned artifact; never downloads or builds")
    selected.add_argument("--platform", choices=("darwin-arm64", "linux-x86_64"))
    return parser


def discovery() -> dict:
    return {
        "profile": "lightpanda-readonly", "entrypoint": "footwork browser lightpanda",
        "commands": ["read", "guide", "artifact"], "engine": "lightpanda",
        "requirements": ["pinned prebuilt Lightpanda executable", "psutil", "websockets", "Unix peer process identity"],
        "desktop_required": False, "cua_required": False, "model_required": False,
        "observation": "bounded DOM semantics; no layout, visibility, screenshot or accessibility-equivalence claim",
        "typing": "disabled", "input": "unavailable; no mutation authority or consumable action refs",
        "completion": "not_asserted; observation is not task completion",
        "lifetime": "one fresh process and one connection per read; no session adoption or reconnect",
        "budgets": {"browser_connections": 1, "websocket_message_bytes": 4 * 1024 * 1024,
                    "dom_nodes": 10_000, "records": 256, "text_characters": 32_768,
                    "observation_bytes": 262_144},
        "install": "external pinned engine; current Footwork metadata still declares full dependencies; light split pending",
        "network": "initial URL setup executes website code; read-only describes Footwork input, not website-side effects",
    }


def prerequisites() -> dict:
    from .effectors.lightpanda.artifacts import artifact, executable

    pin = artifact()
    binary = executable()
    match = False
    if pin["available"] and binary is not None:
        try:
            from .effectors.lightpanda.launch import _digest_executable

            if binary.stat().st_size == pin["bytes"]:
                _digest_executable(binary, pin["sha256"])
                match = True
        except (OSError, RuntimeError):
            pass
    return {**discovery(), "artifact": pin, "prerequisite_presence": {
        "engine_found": binary is not None, "engine_matches_pin": match,
        "psutil": importlib.util.find_spec("psutil") is not None,
        "websockets": importlib.util.find_spec("websockets") is not None,
    }, "runtime_qualification": "not_checked"}


def guide() -> dict:
    from importlib.metadata import PackageNotFoundError, version

    from .effectors.lightpanda.artifacts import artifact

    try:
        package_version = version("jevdual")
    except PackageNotFoundError:
        package_version = "source-checkout"
    return {"package_version": package_version, **discovery(), "artifact": artifact(), "loop": [
        "artifact: obtain the named external binary through your provisioner and verify its recorded SHA256",
        "read URL --executable /absolute/lightpanda: load one page and return a bounded semantic observation",
        "inspect observation limits and cleanup independently; a later read starts a new browser",
    ], "limits": [
        "No click, typing, navigation-after-setup, raw JavaScript, raw CDP or durable mutation command is exposed.",
        "No Jev guard is bypassed: no input mutation can be admitted in this profile.",
        "Input/editable values, embedded frames and unqualified layout/visibility are withheld by the observer.",
        "The load event is the setup boundary; complete network idle and future asynchronous content are not asserted.",
        "Document metadata and content are sampled over an interval; the result grants no later input authority.",
        "Cleanup uses the original child handle and bounded process inventory; forced death/orphan absence is not guaranteed.",
        "The private Unix endpoint and peer checks are not isolation from arbitrary same-user code.",
    ]}


def _validate_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        valid = (len(url) <= 8192 and parsed.scheme in ("http", "https") and parsed.hostname
                 and not parsed.username and not parsed.password)
    except ValueError:
        valid = False
    if not valid:
        raise ReadRefused("lightpanda_url_invalid", "provide an HTTP(S) URL without embedded credentials")


async def _capture(args, state: dict) -> None:
    from .effectors.lightpanda import launch
    from .effectors.lightpanda.artifacts import artifact, executable
    from .effectors.lightpanda.observation import LightpandaObservation

    _validate_url(args.url)
    pin, binary = artifact(), executable(args.executable)
    if not pin["available"]:
        raise ReadRefused("lightpanda_platform_unqualified", pin["reason"])
    if binary is None:
        raise ReadRefused("lightpanda_binary_unavailable", "provision the pinned external engine; no source-build fallback")
    try:
        if binary.stat().st_size != pin["bytes"]:
            raise ReadRefused("lightpanda_digest_mismatch", "the engine size does not match its selected artifact")
    except OSError as exc:
        raise ReadRefused("lightpanda_binary_unavailable", "the selected external engine is unavailable") from exc
    temporary = None
    if args.work_dir is not None:
        if not args.work_dir.is_absolute():
            raise ReadRefused("lightpanda_path_invalid", "work directory must be a fresh short absolute path")
        directory = args.work_dir.resolve()
    else:
        temporary = Path(tempfile.mkdtemp(prefix="fw-lp-", dir="/tmp")).resolve()
        directory = temporary / "engine"
    state["work_dir"] = str(directory)
    owned = conn = None
    state["cleanup"] = {"status": "not_started"}
    try:
        try:
            owned = launch.start(str(binary), directory, expected_sha256=pin["sha256"])
        except BaseException as exc:
            if getattr(exc, "process_started", False):
                state["process_started"] = True
                state["cleanup"] = getattr(exc, "owned_cleanup", {
                    "status": "unverified", "code": "lightpanda_cleanup_unverified",
                })
            raise
        state["process_started"] = True
        state["engine_identity"] = owned.identity()
        conn = await launch.connect(owned, timeout=min(args.timeout, 15.0))
        reader = LightpandaObservation(conn, owned.identity())
        await reader.open(args.url, timeout=min(args.timeout, 15.0))
        if not owned.alive():
            raise ReadRefused("lightpanda_identity_changed", "owned engine changed before capture")
        observation = await reader.snapshot()
        if not owned.alive():
            raise ReadRefused("lightpanda_identity_changed", "owned engine changed during capture")
        state["observation"] = observation
    finally:
        if conn is not None:
            state["protocol_methods"] = list(conn.sent)
        connection_error = None
        try:
            if conn is not None:
                await conn.close()
        except BaseException as exc:  # noqa: BLE001 - retain cancellation until the owned process is stopped
            connection_error = exc
        finally:
            if owned is not None:
                try:
                    launch.stop(owned)
                    state["cleanup"] = {"status": "bounded_owned_processes_stopped", "complete_tree_inventory": False}
                except Exception:  # noqa: BLE001 - cleanup cannot attest absence when its inventory failed
                    state["cleanup"] = {"status": "unverified", "code": "lightpanda_cleanup_unverified"}
        if temporary is not None:
            if state["cleanup"]["status"] in ("not_started", "bounded_owned_processes_stopped"):
                shutil.rmtree(temporary)
                state.pop("work_dir", None)
            else:
                state["retained_work_dir"] = str(temporary)
        if connection_error is not None:
            raise connection_error


async def _run(args) -> tuple[dict, int]:
    state: dict = {"cleanup": {"status": "not_started"}, "process_started": False}
    interrupted: list[int] = []
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    previous = {}

    def stop(sig):
        interrupted.append(sig)
        task.cancel()

    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.getsignal(sig)
            loop.add_signal_handler(sig, stop, sig)
        try:
            await asyncio.wait_for(_capture(args, state), timeout=args.timeout)
            ok = state["cleanup"]["status"] == "bounded_owned_processes_stopped"
            code, exit_code = (None, 0) if ok else ("lightpanda_cleanup_unverified", 3)
        except TimeoutError:
            ok, code, exit_code = False, "lightpanda_timeout", 3
        except asyncio.CancelledError:
            ok, code, exit_code = False, "lightpanda_interrupted", 128 + (interrupted[-1] if interrupted else signal.SIGINT)
        except Exception as exc:  # noqa: BLE001 - never echo arbitrary page or protocol error text
            ok, code, exit_code = False, getattr(exc, "code", "lightpanda_observation_unavailable"), 3
        messages = {
            "lightpanda_timeout": "Capture deadline expired; read cleanup separately. No automatic retry.",
            "lightpanda_interrupted": "Read interrupted; read cleanup separately. No input route was available.",
            "lightpanda_binary_unavailable": "Provision the pinned external engine shown by artifact; no source-build fallback.",
            "lightpanda_digest_mismatch": "Engine bytes do not match the selected artifact pin; nothing was launched.",
            "lightpanda_cleanup_unverified": "Capture and cleanup are separate; owned-process cleanup is unverified.",
        }
        return {"schema_version": "1", "profile": "lightpanda-readonly", "ok": ok,
                "code": code, "capture_completed": "observation" in state, **state,
                "message": "Bounded DOM observation captured." if ok else messages.get(code, "Read unavailable; inspect code and cleanup. No automatic fallback."),
                "input": {"supported": False, "dispatched": False}, "completion": "not_asserted",
                "network_effects": "not_asserted", "retryable": False}, exit_code
    finally:
        for sig, handler in previous.items():
            loop.remove_signal_handler(sig)
            signal.signal(sig, handler)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "guide":
        result, code = guide(), 0
    elif args.command == "artifact":
        from .effectors.lightpanda.artifacts import artifact

        result = artifact(args.platform)
        code = 0 if result["available"] else 3
    else:
        from .effectors.lightpanda.artifacts import artifact

        if not artifact()["available"]:
            print(json.dumps({"schema_version": "1", "profile": "lightpanda-readonly", "ok": False,
                              "code": "lightpanda_platform_unqualified", "capture_completed": False,
                              "cleanup": {"status": "not_started"}, "input": {"supported": False, "dispatched": False},
                              "completion": "not_asserted", "network_effects": "not_asserted",
                              "message": "No qualified external artifact for this platform; no source-build fallback.",
                              "retryable": False}))
            return 3
        result, code = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
