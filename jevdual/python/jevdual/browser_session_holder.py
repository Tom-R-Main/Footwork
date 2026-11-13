"""One driver held for a ``start --browser`` session (app-adaptation step B1).

The driver keeps one DevTools connection per browser port for its own lifetime, and only a new
connection makes Chrome come forward. Its ``browser_prepare`` refuses in the background whatever is
already connected. A session that builds a driver per command therefore needs the browser in front
for every command. The holder builds the driver once, at ``start``, runs ``browser_prepare`` once
while the launch has the browser in front anyway, answers later ``prepare`` calls from that reply,
and serves the other browser operations through the same driver. Tab handles do not survive even
so: the driver issues new ones on every ``get_browser_state`` call (notebook BH2), so a session still
rebinds by page.

The holder owns no session state and decides nothing: each command still builds its own
``BrowserBridge`` and keeps every check it makes today; only the operations cross the socket. A lost
or late response is never reported as not sent.

Transport: a private Unix socket whose peer UID and PID are checked on both sides, plus a nonce from
the holder's private identity record. That identifies the session's own holder; it is not a security
boundary against code running as the same user.

Each holder has its own private runtime directory, outside the session directory, which the session
records with the holder's process identity; a replacement start retires the holder it replaces.
Sending operations carry the command's coordination claim, and the holder re-checks it immediately
before dispatch, so revoking a command's ownership fences the holder as it fences a command's own
driver (coordination.GuardedDriver).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import secrets
import signal
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from jevdual.effectors.base import BrowserRefusal, BrowserReply

HOLDER_FILE = "holder.json"
LOG_FILE = "holder.log"
MAX_REQUEST = 256 * 1024
MAX_RESPONSE = 16 * 1024 * 1024
REQUEST_TIMEOUT = 60.0
DEFAULT_IDLE_S = 1800.0
READY_TIMEOUT_S = 40.0

#: the operations served, with the exact keyword arguments each takes
OPERATIONS: dict[str, frozenset[str]] = {
    "prepare": frozenset({"pid", "window_id"}),
    "bind": frozenset({"pid", "window_id"}),
    "snapshot": frozenset({"target_id", "tab_id"}),
    "click": frozenset({"target_id", "tab_id", "ref", "input_route"}),
    "locate": frozenset({"target_id", "tab_id", "ref", "point"}),
    "type_text": frozenset({"target_id", "tab_id", "ref", "text", "replace"}),
    "navigate": frozenset({"target_id", "tab_id", "url"}),
}
#: fields a request may carry beyond its operation's own. A request without them is the request an
#: older holder already serves; one with them is rejected by a holder started before they existed.
OPTIONAL: dict[str, frozenset[str]] = {
    "click": frozenset({"filmed_point"}),
    "type_text": frozenset({"filmed_point"}),
}
#: operations that may have reached the page; a lost response to one of these is unknown, not unsent
SENDING = frozenset({"click", "type_text", "navigate"})
CONTROL = frozenset({"status", "stop"})
#: the coordination claim fields a sending request carries (coordination.Claim)
CLAIM_FIELDS = frozenset({"token", "owner", "reservation", "desktop"})
#: holder answers given before any driver call
NOT_SENT_CODES = frozenset({"holder_nonce_mismatch", "holder_request_invalid", "holder_peer_mismatch"})


def current_claim() -> dict[str, Any] | None:
    """The calling command's coordination claim, as a sending request carries it."""
    from jevdual import coordination

    claim = coordination._CURRENT.get()
    if claim is None:
        return None
    return {"token": claim.token, "owner": claim.owner, "reservation": claim.reservation or "",
            "desktop": claim.desktop}


def ownership_refusal(claim: Mapping[str, Any]) -> BrowserReply | None:
    """A not-sent refusal when the command's claim is no longer active, checked in the holder
    immediately before dispatch."""
    from jevdual.coordination import CoordinationError, check_ownership

    try:
        check_ownership(token=claim["token"], owner=claim["owner"], reservation=claim["reservation"] or None,
                        desktop=claim["desktop"])
    except CoordinationError as exc:
        message = f"{exc}; nothing was sent"
        return BrowserReply(status="refused", text=message, is_error=True, dispatched=False,
                            refusal=BrowserRefusal(code="ownership_revoked", message=message,
                                                   detail={"delivery": "not_sent", "retryable": False}))
    return None


#: how long a holder sent SIGTERM gets to exit before retirement reports it still running
TERM_GRACE_S = 5.0


class HolderRetireUnknown(RuntimeError):
    """It cannot be established that a holder has exited: its DevTools connection may be open."""

    def __init__(self, pid: int, reason: str) -> None:
        super().__init__(f"the browser holder (pid {pid}) {reason}")
        self.pid = pid


class HolderStillRunning(HolderRetireUnknown):
    """A holder asked to stop, then signalled, is still running."""

    def __init__(self, pid: int) -> None:
        super().__init__(pid, "did not exit")


class HolderUnavailable(RuntimeError):
    """The session's holder cannot be reached or is not the one the session recorded. Nothing was sent."""


def enabled() -> bool:
    return os.environ.get("FOOTWORK_BROWSER_HOLDER", "1") != "0"


def _base() -> Path:
    return Path(tempfile.gettempdir()) / f"fw-bh-{os.getuid()}"


def new_runtime() -> Path:
    """A fresh private runtime directory for one holder: its identity record and log."""
    base = _base()
    _private_socket_dir(base)
    runtime = base / secrets.token_hex(8)
    runtime.mkdir(mode=0o700)
    return runtime


def legacy_runtime(session_dir: Path) -> Path:
    """Where holders started before runtime directories were recorded kept their identity."""
    return Path(session_dir) / "browser-holder"


def socket_path(runtime: Path) -> Path:
    """A short private path: sockaddr_un allows about 104 bytes on macOS."""
    digest = hashlib.sha256(str(Path(runtime).resolve()).encode()).hexdigest()[:20]
    return _base() / f"{digest}.sock"


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def reply_to_wire(reply: BrowserReply) -> dict[str, Any]:
    row = {f.name: _plain(getattr(reply, f.name)) for f in fields(BrowserReply) if f.name != "refusal"}
    row["refusal"] = None if reply.refusal is None else _plain(asdict(reply.refusal))
    return row


def reply_from_wire(row: Mapping[str, Any]) -> BrowserReply:
    known = {f.name for f in fields(BrowserReply)}
    values = {k: v for k, v in row.items() if k in known}
    refusal = values.pop("refusal", None)
    values["evidence"] = tuple(values.get("evidence") or ())
    values["payload"] = dict(values.get("payload") or {})
    return BrowserReply(**values, refusal=BrowserRefusal(**refusal) if refusal else None)


def unknown_reply(operation: str, why: str) -> BrowserReply:
    """A reply for an operation whose outcome the client cannot know. Never a no-send certificate."""
    sending = operation in SENDING
    return BrowserReply(
        status="refused",
        text=f"browser holder response unknown: {why}",
        is_error=True,
        refusal=BrowserRefusal(
            code="browser_holder_response_unknown" if sending else "browser_holder_unavailable",
            message=f"browser holder response unknown: {why}",
            detail={"delivery": "unknown" if sending else "not_sent", "retryable": not sending},
        ),
        dispatched=None if sending else False,
    )


# ---------------------------------------------------------------- holder side


def devtools_clients(port: int) -> list[dict[str, Any]] | None:
    """Processes holding an established TCP connection to the browser's DevTools port, or None when
    the check cannot run. A client end reads ``local->127.0.0.1:<port>``; the browser's own ends read
    ``127.0.0.1:<port>->remote`` and are not clients."""
    import subprocess

    try:
        proc = subprocess.run(["lsof", "-nP", f"-iTCP@127.0.0.1:{port}", "-sTCP:ESTABLISHED", "-F", "pcn"],
                              capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        # 1 is also lsof's status for an inspection error, whose partial output could show this
        # holder's connection and miss another; with no match at all the positive-evidence rule
        # refuses anyway, so only a clean exit counts as a scan
        return None
    clients: dict[int, dict[str, Any]] = {}
    pid, command = None, ""
    for line in proc.stdout.splitlines():
        tag, value = line[:1], line[1:]
        if tag == "p":
            pid, command = int(value), ""
        elif tag == "c":
            command = value
        elif tag == "n" and pid is not None and "->" in value:
            remote = value.split("->", 1)[1]
            if remote.rsplit(":", 1)[-1] == str(port):
                clients.setdefault(pid, {"pid": pid, "command": command, "connections": 0})["connections"] += 1
    return list(clients.values())


def second_client_refusal(clients: list[dict[str, Any]] | None) -> BrowserReply | None:
    """A refusal when a process other than this holder is connected to the browser, or when that
    cannot be established. Nothing is sent: another client could change the page between this
    holder's observation and its input, and this holder could not tell.

    An empty or partial scan is not evidence of no other client, so the scan must also show this
    holder's own connection (its driver keeps one open); without it the check refuses. This is a
    check at one instant: a client that attaches after it is not seen."""
    foreign = [c for c in clients or () if c["pid"] != os.getpid()]
    if foreign:
        names = ", ".join(f"{c['command']} (pid {c['pid']})" for c in foreign[:4])
        code, message = "browser_second_client", f"another DevTools client is connected to this browser: {names}"
    elif clients is None:
        code, message = "browser_client_check_unavailable", "could not check for another DevTools client"
    elif not any(c["pid"] == os.getpid() for c in clients):
        code = "browser_client_check_unavailable"
        message = ("the client scan did not show this holder's own DevTools connection, so it cannot "
                   "show that no other client is connected")
    else:
        return None
    return BrowserReply(status="refused", text=message, is_error=True, dispatched=False,
                        refusal=BrowserRefusal(code=code, message=f"{message}; nothing was sent",
                                               detail={"delivery": "not_sent", "retryable": True,
                                                       "clients": clients}))


class PrepareOnce:
    """Driver operations whose successful ``prepare`` is kept and answered again for the same window.

    The attachment a prepare makes lives as long as the driver; repeating it in the background only
    meets the driver's static refusal. A refused or failed prepare is not kept.
    """

    def __init__(self, inner: Any):
        self.inner = inner
        self.prepared: dict[tuple[int, int], BrowserReply] = {}
        self.repeats = 0

    async def prepare(self, *, pid: int, window_id: int) -> BrowserReply:
        key = (pid, window_id)
        if key in self.prepared:
            self.repeats += 1
            return self.prepared[key]
        reply = await self.inner.prepare(pid=pid, window_id=window_id)
        if not reply.refused:
            self.prepared[key] = reply
        return reply

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


class Holder:
    def __init__(self, *, driver: Any, operations: PrepareOnce, identity: dict[str, Any], idle_s: float,
                 clients: Any = None):
        #: lists the DevTools clients before each sending operation (B2); None skips the check
        self.clients = clients
        self.refused_second_client = 0
        self.driver = driver
        self.operations = operations
        self.identity = identity
        self.idle_s = idle_s
        self.last_request = time.monotonic()
        self.served: dict[str, int] = {}
        self.lock = asyncio.Lock()
        self.stopping = asyncio.Event()

    async def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if request.get("nonce") != self.identity["nonce"]:
            return {"ok": False, "code": "holder_nonce_mismatch"}
        method = request.get("method")
        args = request.get("args") or {}
        claim = request.get("claim")
        if claim is not None and (not isinstance(claim, dict) or set(claim) != CLAIM_FIELDS):
            return {"ok": False, "code": "holder_request_invalid"}
        if method in CONTROL:
            if method == "stop":
                self.stopping.set()
            return {"ok": True, "status": self.status()}
        if method not in OPERATIONS or not isinstance(args, dict) or not (
                OPERATIONS[method] <= set(args) <= OPERATIONS[method] | OPTIONAL.get(method, frozenset())):
            return {"ok": False, "code": "holder_request_invalid"}
        self.last_request = time.monotonic()
        async with self.lock:
            refusal = None
            if method in SENDING and self.clients is not None:
                refusal = second_client_refusal(await asyncio.to_thread(self.clients))
            # last before dispatch: a claim revoked while the scan ran must not be acted for
            if refusal is None and method in SENDING and claim is not None:
                refusal = await asyncio.to_thread(ownership_refusal, claim)
            if refusal is not None:
                if refusal.refusal and refusal.refusal.code != "ownership_revoked":
                    self.refused_second_client += 1
                reply = refusal
            else:
                reply = await getattr(self.operations, method)(**args)
        self.served[method] = self.served.get(method, 0) + 1
        self.last_request = time.monotonic()
        return {"ok": True, "reply": reply_to_wire(reply)}

    def status(self) -> dict[str, Any]:
        return {
            "served": dict(self.served),
            "prepare_repeats_answered": self.operations.repeats,
            "refused_second_client": self.refused_second_client,
            "idle_s": round(time.monotonic() - self.last_request, 3),
            "chrome_pid": self.identity["chrome_pid"],
            "window_id": self.identity["window_id"],
        }

    async def serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        from jevdual.browser_holder import _peer_credentials

        result: dict[str, Any] | None = None
        request: Any = None
        # Only reading and parsing may answer "invalid", which the client reads as not sent. Once the
        # request is handed to handle(), any exception may follow a dispatch and is unknown.
        try:
            if _peer_credentials(writer)[1] != os.getuid():
                result = {"ok": False, "code": "holder_peer_mismatch"}
            else:
                raw = await asyncio.wait_for(reader.readuntil(b"\n"), 5.0)
                request = json.loads(raw)
                if not isinstance(request, dict):
                    result = {"ok": False, "code": "holder_request_invalid"}
        except (asyncio.LimitOverrunError, asyncio.IncompleteReadError, ValueError, TimeoutError):
            result = {"ok": False, "code": "holder_request_invalid"}
        except Exception as exc:  # noqa: BLE001 - nothing was handed to the driver yet
            result = {"ok": False, "code": "holder_request_invalid", "error": f"{type(exc).__name__}"[:100]}
        if result is None:
            try:
                result = await asyncio.wait_for(self.handle(request), REQUEST_TIMEOUT)
            except Exception as exc:  # noqa: BLE001 - an operation that raised may still have reached the page
                result = {"ok": False, "code": "holder_response_unknown",
                          "error": f"{type(exc).__name__}: {exc}"[:300]}
        try:
            encoded = json.dumps(result, separators=(",", ":"), default=str).encode() + b"\n"
            if len(encoded) > MAX_RESPONSE:
                encoded = b'{"ok":false,"code":"holder_response_too_large"}\n'
            writer.write(encoded)
            await asyncio.wait_for(writer.drain(), 5.0)
        except (OSError, TimeoutError):
            pass
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()


def _private_socket_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    row = path.lstat()
    if not path.is_dir() or path.is_symlink() or row.st_uid != os.getuid() or row.st_mode & 0o077:
        raise HolderUnavailable(f"{path} must be a private directory owned by this user")


async def _watch(holder: Holder, chrome_alive: Any) -> str:
    while not holder.stopping.is_set():
        if time.monotonic() - holder.last_request > holder.idle_s:
            return "idle"
        if not chrome_alive():
            return "browser_gone"
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(holder.stopping.wait(), 1.0)
    return "stopped"


async def serve(
    runtime: Path, *, driver: Any, operations: PrepareOnce, binding: Mapping[str, Any],
    chrome_alive: Any, idle_s: float, install_signals: bool = True, clients: Any = None,
) -> str:
    """Serve ``operations`` on the runtime's socket until stopped, idle, or the browser goes away."""
    from jevdual.browser_holder import _write_private, process_identity

    runtime = Path(runtime)
    _private_socket_dir(runtime)
    sock = socket_path(runtime)
    _private_socket_dir(sock.parent)
    if sock.exists():
        sock.unlink()  # this session's own path; spawn refuses while a live holder has it
    identity = {"version": 1, **process_identity(os.getpid()), "nonce": secrets.token_hex(32),
                "socket": str(sock), "runtime": str(runtime.resolve()), **binding}
    holder = Holder(driver=driver, operations=operations, identity=identity, idle_s=idle_s, clients=clients)
    server = await asyncio.start_unix_server(holder.serve, path=str(sock), limit=MAX_REQUEST)
    os.chmod(sock, 0o600)
    if install_signals:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, holder.stopping.set)
    _write_private(runtime / HOLDER_FILE, identity)
    reason = "error"
    try:
        reason = await _watch(holder, chrome_alive)
    finally:
        server.close()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(server.wait_closed(), 2)
        with contextlib.suppress(FileNotFoundError):
            sock.unlink()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(driver.shutdown(), 5)
        # last, once the driver's DevTools connection is closed: an in-process holder is retired
        # when its record is gone (a subprocess holder when its process has exited)
        with contextlib.suppress(FileNotFoundError):
            (runtime / HOLDER_FILE).unlink()
        print(json.dumps({"t": time.time(), "exit": reason, **holder.status()}), flush=True)
    return reason


async def run(runtime: Path, *, url: str | None, idle_s: float, page_accessibility: bool = False) -> int:
    from jevdual.browser_driver import _incarnation, bind_footwork_chrome, chrome_pid

    wrapped: list[PrepareOnce] = []

    def wrap(inner: Any) -> PrepareOnce:
        wrapped.append(PrepareOnce(inner))
        return wrapped[-1]

    driver, bridge = await bind_footwork_chrome(url, wrap_operations=wrap, page_accessibility=page_accessibility)
    pid = bridge.pid
    incarnation = _incarnation(pid)
    binding = {
        "chrome_pid": pid, "chrome_incarnation": repr(incarnation), "window_id": bridge.window_id,
        "tab_id": bridge.tab_id, "target_id": bridge.target_id,
        "launch_identity": getattr(bridge, "launch_identity", {}),
    }
    from jevdual.browser_driver import PORT

    await serve(runtime, driver=driver, operations=wrapped[-1], binding={**binding, "port": PORT},
                idle_s=idle_s, chrome_alive=lambda: chrome_pid() == pid and _incarnation(pid) == incarnation,
                clients=lambda: devtools_clients(PORT))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="hold one browser driver for a footwork session")
    parser.add_argument("--runtime", required=True, help="this holder's private runtime directory")
    parser.add_argument("--url")
    parser.add_argument("--idle", type=float, default=float(os.environ.get("FOOTWORK_BROWSER_HOLDER_IDLE_S", DEFAULT_IDLE_S)))
    parser.add_argument("--page-accessibility", action="store_true",
                        help="launch the browser with page accessibility forced (a filmed start)")
    args = parser.parse_args(argv)
    return asyncio.run(run(Path(args.runtime), url=args.url, idle_s=args.idle,
                           page_accessibility=args.page_accessibility))


# ---------------------------------------------------------------- client side


def _read_identity(runtime: Path) -> dict[str, Any]:
    from jevdual.browser_holder import HolderRefused, _read_private

    try:
        return _read_private(Path(runtime) / HOLDER_FILE)
    except (FileNotFoundError, HolderRefused, ValueError) as exc:
        raise HolderUnavailable(f"no live browser holder record: {exc}") from exc


def _check_alive(identity: Mapping[str, Any]) -> None:
    from jevdual.browser_holder import process_identity

    try:
        current = process_identity(int(identity["pid"]))
    except Exception as exc:
        raise HolderUnavailable("the session's browser holder has exited") from exc
    if any(identity.get(k) != current[k] for k in ("boot", "pid", "start")):
        raise HolderUnavailable("the session's browser holder process changed identity")


async def call(runtime: Path, method: str, args: Mapping[str, Any] | None = None, *,
               claim: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """One request to a holder. Raises HolderUnavailable only when nothing was sent."""
    from jevdual.browser_holder import _peer_credentials

    identity = _read_identity(runtime)
    _check_alive(identity)
    request: dict[str, Any] = {"nonce": identity["nonce"], "method": method, "args": dict(args or {})}
    if claim is not None:
        request["claim"] = dict(claim)
    raw = json.dumps(request, separators=(",", ":")).encode() + b"\n"
    if len(raw) > MAX_REQUEST:
        raise HolderUnavailable("the browser request exceeds the holder's request bound")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(identity["socket"], limit=MAX_RESPONSE), 5.0)
    except (OSError, TimeoutError) as exc:
        raise HolderUnavailable("the session's browser holder socket is unavailable") from exc
    try:
        peer_pid, peer_uid = _peer_credentials(writer)
        if peer_uid != os.getuid() or peer_pid != identity["pid"]:
            raise HolderUnavailable("the browser holder socket belongs to another process")
        writer.write(raw)
        await asyncio.wait_for(writer.drain(), 5.0)
        response = await asyncio.wait_for(reader.readuntil(b"\n"), REQUEST_TIMEOUT + 5)
        value = json.loads(response)
        if not isinstance(value, dict):
            raise TypeError("response is not an object")
        return value
    except HolderUnavailable:
        raise
    except (OSError, TimeoutError, ValueError, TypeError, asyncio.IncompleteReadError, asyncio.LimitOverrunError) as exc:
        return {"ok": False, "code": "holder_response_unknown", "error": f"{type(exc).__name__}"}
    finally:
        writer.close()
        with contextlib.suppress(OSError):
            await writer.wait_closed()


class RemoteBrowserOperations:
    """``BrowserOperations`` served by a session's holder, under the calling command's ownership."""

    def __init__(self, runtime: Path):
        self.runtime = Path(runtime)

    async def _op(self, name: str, **args: Any) -> BrowserReply:
        from jevdual import coordination

        claim = None
        if name in SENDING:
            coordination.checkpoint()  # as GuardedDriver does before a command's own non-read-only call
            claim = current_claim()
        task = asyncio.ensure_future(call(self.runtime, name, args, claim=claim))
        try:
            value = await asyncio.shield(task)
        except asyncio.CancelledError:
            # The holder may already be dispatching. Fence further input and keep this command's
            # ownership until the admitted request settles (coordination.owned_thread).
            owner = coordination._CURRENT.get()
            if owner is not None and name in SENDING:
                owner.registry.revoke(owner.token)
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except Exception:  # noqa: BLE001 - consume the request's failure, keep the cancellation
                    break
            with contextlib.suppress(Exception):
                task.result()
            raise
        except HolderUnavailable as exc:  # raised only before anything was written to the socket
            return BrowserReply(status="refused", text=str(exc), is_error=True, dispatched=False,
                                refusal=BrowserRefusal(code="browser_holder_unavailable", message=str(exc),
                                                       detail={"delivery": "not_sent", "retryable": True}))
        if value.get("ok") and isinstance(value.get("reply"), dict):
            return reply_from_wire(value["reply"])
        code = str(value.get("code") or "holder_response_unknown")
        if code in NOT_SENT_CODES:
            # refused by the holder before any driver call
            return BrowserReply(status="refused", text=code, is_error=True, dispatched=False,
                                refusal=BrowserRefusal(code=code, message=code,
                                                       detail={"delivery": "not_sent", "retryable": False}))
        return unknown_reply(name, code)

    async def prepare(self, *, pid: int, window_id: int) -> BrowserReply:
        return await self._op("prepare", pid=pid, window_id=window_id)

    async def bind(self, *, pid: int, window_id: int) -> BrowserReply:
        return await self._op("bind", pid=pid, window_id=window_id)

    async def snapshot(self, *, target_id: str, tab_id: str | None) -> BrowserReply:
        return await self._op("snapshot", target_id=target_id, tab_id=tab_id)

    @staticmethod
    def _older_holder(reply: BrowserReply, what: str) -> BrowserReply:
        """A holder checks a request's exact fields; one started by an older build does not know a
        field added since. Say so, and that nothing was sent."""
        if reply.refusal is None or reply.refusal.code != "holder_request_invalid":
            return reply
        message = (f"this session's browser holder does not serve this {what} request (an older build "
                   "started it); start a new session")
        return BrowserReply(status="refused", text=message, is_error=True, dispatched=False,
                            refusal=BrowserRefusal(code="holder_request_invalid", message=message,
                                                   detail={"delivery": "not_sent", "retryable": False}))

    @staticmethod
    def _filmed(filmed_point: Any) -> dict[str, Any]:
        """The optional field, only when there is a point: an unfilmed request stays the one every
        holder serves."""
        return {} if filmed_point is None else {"filmed_point": [float(filmed_point[0]), float(filmed_point[1])]}

    async def click(
        self, *, target_id: str, tab_id: str | None, ref: str, input_route: str, filmed_point: Any = None
    ) -> BrowserReply:
        reply = await self._op("click", target_id=target_id, tab_id=tab_id, ref=ref, input_route=input_route,
                               **self._filmed(filmed_point))
        return reply if filmed_point is None else self._older_holder(reply, "filmed click")

    async def locate(self, *, target_id: str, tab_id: str | None, ref: str, point: Any = None) -> BrowserReply:
        reply = await self._op("locate", target_id=target_id, tab_id=tab_id, ref=ref,
                               point=None if point is None else [float(point[0]), float(point[1])])
        # an older holder knows no locate, or one without a point
        return self._older_holder(reply, "locate")

    async def type_text(
        self, *, target_id: str, tab_id: str | None, ref: str, text: str, replace: bool, filmed_point: Any = None
    ) -> BrowserReply:
        reply = await self._op("type_text", target_id=target_id, tab_id=tab_id, ref=ref, text=text, replace=replace,
                               **self._filmed(filmed_point))
        return reply if filmed_point is None else self._older_holder(reply, "filmed type")

    async def navigate(self, *, target_id: str, tab_id: str | None, url: str) -> BrowserReply:
        return await self._op("navigate", target_id=target_id, tab_id=tab_id, url=url)


class HeldDriver:
    """Stands in for the driver a command would otherwise own: the holder owns the real one."""

    held = True

    async def shutdown(self) -> None:
        return None


def holder_live(runtime: Path) -> dict[str, Any] | None:
    try:
        identity = _read_identity(runtime)
        _check_alive(identity)
        return identity
    except HolderUnavailable:
        return None


def spawn(*, url: str | None, page_accessibility: bool = False) -> dict[str, Any]:
    """Start a holder in a new runtime directory and wait until it has bound the browser.

    Returns its identity record, which names its runtime. Raises when it does not become ready, after
    terminating the process it started. ``page_accessibility`` is passed to the holder's launch of the
    browser (a filmed start); without it the holder's command is as it was."""
    import subprocess

    runtime = new_runtime()
    # the release launcher runs isolated (-I); the holder runs the same way from the same interpreter
    command = [sys.executable, *(["-I"] if sys.flags.isolated else []), "-m", "jevdual.browser_session_holder",
               "--runtime", str(runtime)]
    if url:
        command += ["--url", url]
    if page_accessibility:
        command += ["--page-accessibility"]
    log = (runtime / LOG_FILE).open("ab")
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                               start_new_session=True, env=os.environ.copy())
    deadline = time.monotonic() + READY_TIMEOUT_S
    try:
        while time.monotonic() < deadline:
            identity = holder_live(runtime)
            if identity is not None and identity.get("pid") == process.pid:
                return identity
            if process.poll() is not None:
                break
            time.sleep(0.1)
    finally:
        log.close()
    if process.poll() is None:
        process.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=10)
    tail = (runtime / LOG_FILE).read_text(errors="replace")[-600:]
    raise HolderUnavailable(f"the browser holder did not become ready: {tail.strip()}")


async def _settle(task: asyncio.Future[Any]) -> None:
    """Wait for ``task`` to finish however often the waiter is cancelled meanwhile."""
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
        except Exception:  # noqa: BLE001 - the caller reads the task's own outcome
            break


async def spawn_owned(*, url: str | None, page_accessibility: bool = False) -> dict[str, Any]:
    """``spawn`` that a cancelled caller cannot abandon: on cancellation, however repeated, it
    waits for the spawn to finish and for the holder it produced to be retired, then re-raises."""
    task = asyncio.ensure_future(asyncio.to_thread(spawn, url=url, page_accessibility=page_accessibility))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await _settle(task)
        identity = None
        with contextlib.suppress(Exception):
            identity = task.result()
        if identity is not None:
            cleanup = asyncio.ensure_future(retire(Path(identity["runtime"]), expected=identity))
            await _settle(cleanup)
            if not cleanup.cancelled():
                cleanup.exception()  # retrieved: a survivor was signalled; cancellation still wins
        raise


def recorded_runtime(record: Mapping[str, Any], session_dir: Path) -> Path:
    """The runtime directory a session's holder record names (older records kept it in the session)."""
    return Path(record["runtime"]) if record.get("runtime") else legacy_runtime(session_dir)


async def retire(runtime: Path, *, expected: Mapping[str, Any] | None = None,
                 timeout_s: float = 10.0) -> dict[str, Any] | None:
    """Stop a holder and wait, bounded, until its process has exited.

    With ``expected`` (the identity a session recorded) only that process is stopped, and it is
    waited for even when its record is already gone (it removes the record as it exits). Every field
    of ``expected`` is kept: a holder that differs in any is another holder and is left alone. If it
    does not exit after asking, it is sent SIGTERM, checked against the same full identity first.
    Returns its last status, if it answered. Raises HolderRetireUnknown when its exit cannot be
    established: still running after SIGTERM (HolderStillRunning), a process it cannot inspect, or an
    incomplete identity with a process on its PID."""
    keys = ("boot", "pid", "start")
    live = holder_live(runtime)
    if expected is None:
        if live is None:
            return None
        target: dict[str, Any] = {k: live[k] for k in keys}
    else:
        given = {k: expected[k] for k in keys if expected.get(k) not in (None, "")}
        if "pid" not in given:
            raise HolderRetireUnknown(0, "has no recorded PID")
        if len(given) == len(keys):
            target = given
        elif live is not None and all(live.get(k) == v for k, v in given.items()):
            target = {k: live[k] for k in keys}  # its own live record completes the identity
        else:
            import psutil

            if not psutil.pid_exists(int(given["pid"])):
                return None
            raise HolderRetireUnknown(int(given["pid"]), "has an incomplete recorded identity and its PID is in use")
    pid = int(target["pid"])
    own = pid == os.getpid()  # a holder in this very process: the offline tests
    answering = live is not None and all(live.get(k) == target.get(k) for k in keys)
    if own and not answering:
        return None  # an in-process holder is gone once its record is

    def same() -> bool:
        return not _exited(pid, target)

    def running() -> bool:
        if not own:
            return same()
        current = holder_live(runtime)
        return current is not None and current.get("nonce") == live.get("nonce")

    if not running():
        return None
    status = None
    if answering:
        with contextlib.suppress(HolderUnavailable):
            status = await call(runtime, "stop")
    for signalled in (False, True):
        deadline = time.monotonic() + (timeout_s if not signalled else TERM_GRACE_S)
        while time.monotonic() < deadline:
            if not running():
                return status
            await asyncio.sleep(0.1)
        if not signalled and not own and same():
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGTERM)
    if running():
        raise HolderStillRunning(pid)
    return status


def _exited(pid: int, target: Mapping[str, Any]) -> bool:
    """True when the process ``target`` names is gone (exited, a zombie, or its PID reused); False
    while it runs. Raises HolderRetireUnknown when the process cannot be inspected."""
    import psutil

    from jevdual.browser_holder import HolderRefused, process_identity

    try:
        current = process_identity(pid)
    except (psutil.NoSuchProcess, HolderRefused):  # exited, or a zombie
        return True
    except Exception as exc:  # no evidence either way
        raise HolderRetireUnknown(pid, f"could not be inspected ({type(exc).__name__})") from exc
    return not all(target.get(k) == current[k] for k in ("boot", "pid", "start"))


async def retire_settled(runtime: Path, *, expected: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """``retire`` that cancellation cannot interrupt: it finishes, then the cancellation is raised."""
    task = asyncio.ensure_future(retire(runtime, expected=expected))
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:  # noqa: BLE001 - read from the task below
            break
    if cancelled:
        raise asyncio.CancelledError
    return task.result()


async def stop_async(runtime: Path) -> dict[str, Any] | None:
    """Ask a holder to stop and wait for it to exit."""
    return await retire(runtime)


if __name__ == "__main__":
    raise SystemExit(main())
