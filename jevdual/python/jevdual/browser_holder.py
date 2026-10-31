"""Bounded local custody for the owned browser and its durable operation journal.

Only this process holds the browser handle, CDP connection, current refs and journal lock. Clients
can reconnect to this holder; they cannot adopt a browser or restart an uncertain activation. The
private Unix socket and peer UID identify a local session transport, not an authorization grant or
a security boundary against arbitrary code running as the same user. Guard admission is mandatory.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import fcntl
import json
import os
import secrets
import signal
import socket
import stat
import struct
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .effectors.base import BrowserReply
from .effectors.cdp import launch
from .effectors.cdp.click import ROUTE
from .effectors.cdp.operations import CdpBrowserOperations, RefBinding
from .platform_identity import boot_identity

CONFIG_FILE = "browser.json"
HOLDER_FILE = "holder.json"
SOCKET_FILE = "holder.sock"
MAX_REQUEST = 64 * 1024
MAX_RESPONSE = 1024 * 1024
REQUEST_TIMEOUT = 30.0
METHODS = frozenset({"look", "click", "status", "stop"})


class HolderRefused(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "code": code, "message": message, "dispatched": False}


def _private_directory(directory: Path) -> None:
    row = directory.lstat()
    if not stat.S_ISDIR(row.st_mode) or row.st_uid != os.getuid() or row.st_mode & 0o077:
        raise HolderRefused("browser_session_unavailable", "the browser session must be an owned private directory")
    # sockaddr_un has a smaller bound on macOS than Linux. Refuse before launch, not after Chrome
    # has started; no alternate shared socket or stale-socket removal is attempted.
    if len(os.fsencode(directory / SOCKET_FILE)) > 100:
        raise HolderRefused("browser_session_unavailable", "the browser session path is too long for its Unix socket")


def _read_private(path: Path, *, limit: int = MAX_REQUEST) -> dict[str, Any]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        row = os.fstat(stream.fileno())
        if not stat.S_ISREG(row.st_mode) or row.st_uid != os.getuid() or row.st_mode & 0o077:
            raise HolderRefused("browser_session_unavailable", "browser session files must be owned private regular files")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise HolderRefused("browser_request_invalid", "browser session metadata exceeds its read bound")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise HolderRefused("browser_request_invalid", "browser session metadata must be an object")
    return value


def _write_private(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}-{secrets.token_hex(8)}")
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
            json.dump(value, stream, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def process_identity(pid: int) -> dict[str, Any]:
    import psutil

    process = psutil.Process(pid)
    if process.status() == psutil.STATUS_ZOMBIE:
        raise HolderRefused("browser_holder_unavailable", "the browser holder has exited")
    return {"boot": boot_identity(), "pid": pid, "start": repr(process.create_time())}


def _config(directory: Path) -> dict[str, Any]:
    _private_directory(directory)
    config = _read_private(directory / CONFIG_FILE)
    if (config.get("version") != 1 or type(config.get("version")) is not int
            or not isinstance(config.get("session_id"), str) or not 1 <= len(config["session_id"]) <= 128
            or not isinstance(config.get("task"), str) or not 1 <= len(config["task"]) <= 16384
            or not isinstance(config.get("chrome"), str) or not Path(config["chrome"]).is_absolute()
            or not isinstance(config.get("authority"), str) or not Path(config["authority"]).is_absolute()
            or not isinstance(config.get("initial_url"), str)):
        raise HolderRefused("browser_request_invalid", "invalid browser holder configuration")
    parsed = urlsplit(config["initial_url"])
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise HolderRefused("browser_request_invalid", "initial browser URL requires HTTP(S) without credentials")
    command = config.get("guard_command")
    if command is not None and (not isinstance(command, list) or not command
                                or not all(isinstance(arg, str) and arg for arg in command)):
        raise HolderRefused("browser_request_invalid", "guard_command must be a nonempty argument list or null")
    return config


def _peer_credentials(writer: asyncio.StreamWriter) -> tuple[int, int]:
    peer = writer.get_extra_info("socket")
    if peer is None:
        raise HolderRefused("browser_peer_unavailable", "the browser socket peer could not be identified")
    if hasattr(socket, "SO_PEERCRED"):
        pid, uid, _ = struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        return pid, uid
    # Darwin LOCAL_PEERCRED gives xucred: uint version, uid_t uid, short ngroups, gid_t groups[16].
    if os.uname().sysname == "Darwin":
        credentials = peer.getsockopt(0, 1, 128)
        version, uid = struct.unpack_from("=II", credentials)
        if version == 0:
            pid = struct.unpack("=i", peer.getsockopt(0, 2, 4))[0]
            return pid, uid
    raise HolderRefused("browser_peer_unavailable", "peer UID checking is unavailable on this platform")


def _reply(reply: BrowserReply) -> dict[str, Any]:
    return {"status": reply.status, "dispatched": reply.dispatched, "route": reply.route,
            "code": reply.refusal.code if reply.refusal else None}


def _binding(chrome: launch.OwnedChrome, binding: RefBinding) -> dict[str, Any]:
    if binding.button is None:
        raise HolderRefused("browser_mutation_unqualified", "the observed control is outside the native-button subset")
    return {"boot": boot_identity(), "pid": chrome.pid, "start": repr(chrome.incarnation),
            "browser_context": binding.context_id, "target": binding.target_id,
            "cdp_session": binding.session_id, "frame": binding.frame_id, "loader": binding.loader_id,
            "backend_node": binding.backend_node_id, "execution_context": binding.execution_context_id,
            "document_token": binding.document_token, "fingerprint": binding.button.fingerprint_json}


class BrowserHolder:
    """One serial command stream. Dependency parameters also let unit tests prove the send boundary."""

    def __init__(self, config: dict[str, Any], authority, chrome, operations, tab: str, authorize):
        self.config = config
        self.authority = authority
        self.chrome = chrome
        self.operations = operations
        self.tab = tab
        self.authorize = authorize
        self.snapshot: dict[str, Any] | None = None
        self.lock = asyncio.Lock()
        self.stopping = asyncio.Event()
        self.closed = False
        self.nonce = secrets.token_hex(32)

    def _result(self, **payload) -> dict[str, Any]:
        return {"ok": True, "session_id": self.config["session_id"], **payload}

    def _operation(self, operation, *, replayed: bool = False) -> dict[str, Any]:
        from .browser_authority import operation_record

        return self._result(operation=operation_record(operation), replayed=replayed)

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        from .capability.journal import Busy, JournalError, TokenConflict

        try:
            if not isinstance(request, dict) or request.get("nonce") != self.nonce:
                raise HolderRefused("browser_session_mismatch", "browser session authentication failed")
            if request.get("session_id") != self.config["session_id"]:
                raise HolderRefused("browser_session_mismatch", "the requested browser session does not match")
            method = request.get("method")
            if not isinstance(method, str) or method not in METHODS:
                raise HolderRefused("browser_method_unavailable", "only look, click, status and stop are available")
            expected = {"nonce", "session_id", "method"} | ({"token", "ref"} if method == "click" else set())
            if set(request) != expected:
                raise HolderRefused("browser_request_invalid", "unexpected or missing browser request fields")
            async with self.lock:
                if self.closed:
                    raise HolderRefused("browser_holder_unavailable", "the browser holder is stopping")
                if method == "look":
                    reply = await self.operations.snapshot(target_id=self.operations.browser_id, tab_id=self.tab)
                    if reply.refused:
                        return _error(reply.refusal.code or "browser_observation_unavailable", reply.text)
                    self.snapshot = dict(reply.payload)
                    return self._result(snapshot=self.snapshot)
                if method == "click":
                    return await self._click(request)
                if method == "status":
                    from .browser_authority import operation_record

                    return self._result(operations=[operation_record(self.authority.reconcile(op.id)) for op in
                                                   self.authority.status(self.config["session_id"])])
                cleanup = await self.close()
                self.stopping.set()
                return self._result(cleanup=cleanup)
        except HolderRefused as exc:
            return _error(exc.code, str(exc))
        except TokenConflict as exc:
            return _error("client_token_conflict", str(exc))
        except Busy as exc:
            return _error("browser_operation_unresolved", str(exc))
        except JournalError:
            return _error("browser_authority_unavailable", "browser authority could not admit this request")

    async def _click(self, request: dict[str, Any]) -> dict[str, Any]:
        from .browser_authority import guard_digest

        token, ref = request["token"], request["ref"]
        if (not isinstance(token, str) or not 1 <= len(token) <= 256
                or not isinstance(ref, str) or not 1 <= len(ref) <= 256):
            raise HolderRefused("browser_request_invalid", "click requires bounded ref and client token strings")
        canonical = {"ref": ref, "route": ROUTE}
        prior = self.authority.by_request(self.config["session_id"], token, canonical)
        if prior is not None:
            return self._operation(prior, replayed=True)
        self.authority.assert_available()
        if self.snapshot is None:
            raise HolderRefused("browser_observation_required", "observe this browser before proposing an activation")
        admitted = None

        async def admission(binding: RefBinding) -> None:
            nonlocal admitted
            record = _binding(self.chrome, binding)
            digest = guard_digest(self.config["session_id"], canonical, record)
            try:
                guard = await self.authorize(self.config, record, self.snapshot, ref, digest)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                raise HolderRefused(getattr(exc, "code", "browser_guard_unavailable"),
                                    "the configured guard did not authorize this activation") from exc
            admitted = self.authority.admit_click(session_id=self.config["session_id"], token=token,
                                                 request=canonical, binding=record, guard=guard)
            admitted = self.authority.start(admitted.id)

        try:
            reply = await self.operations.click(target_id=self.operations.browser_id, tab_id=self.tab,
                                                ref=ref, input_route="dom_event", admission=admission)
            if admitted is None:
                return _error(reply.refusal.code if reply.refusal else "browser_not_admitted", reply.text)
            operation = self.authority.record_reply(admitted.id, _reply(reply))
            return self._operation(operation)
        except BaseException as exc:
            if admitted is None:
                raise
            # No post-admission exception is a no-send certificate. Even cancellation retains
            # uncertainty. Reconciliation inspects only retained execution evidence, never the DOM.
            try:
                operation = self.authority.mark_unknown(admitted.id)
                result = self._operation(operation)
            except Exception:  # noqa: BLE001 - any retention loss after admission is uncertain
                # Retention failure is not evidence of non-delivery. Never let it reach the
                # outer pre-admission JournalError handler, or claim that unknown was persisted.
                result = {"ok": False, "code": "browser_retention_unverified", "dispatched": None,
                          "retryable": False, "operation_id": admitted.id, "completion": "unverified"}
            if isinstance(exc, asyncio.CancelledError):
                raise
            return result

    async def close(self) -> dict[str, Any]:
        if self.closed:
            return {"status": "already_stopped"}
        self.closed = True
        try:
            await self.operations.close()
        finally:
            try:
                await asyncio.to_thread(launch.stop, self.chrome)
            except Exception:  # noqa: BLE001 - cleanup failure must remain explicitly unverified
                return {"status": "unverified", "code": "browser_cleanup_unverified"}
        return {"status": "bounded_owned_processes_stopped", "complete_tree_inventory": False}

    async def serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            if _peer_credentials(writer)[1] != os.getuid():
                raise HolderRefused("browser_peer_mismatch", "the browser socket peer has a different UID")
            try:
                raw = await asyncio.wait_for(reader.readuntil(b"\n"), 5.0)
            except (asyncio.LimitOverrunError, asyncio.IncompleteReadError, TimeoutError) as exc:
                raise HolderRefused("browser_request_invalid", "the browser request exceeded its size or time bound") from exc
            if len(raw) > MAX_REQUEST:
                raise HolderRefused("browser_request_invalid", "the browser request exceeds 64 KiB")
            try:
                value = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HolderRefused("browser_request_invalid", "the browser request is not JSON") from exc
            result = await asyncio.wait_for(self.handle(value), REQUEST_TIMEOUT)
        except HolderRefused as exc:
            result = _error(exc.code, str(exc))
        except TimeoutError:
            # The operation may have been admitted. Do not issue a generic not-sent certificate.
            result = {"ok": False, "code": "browser_response_unknown", "dispatched": None, "retryable": False}
        except Exception:  # noqa: BLE001 - an unclassified holder loss is never a no-send certificate
            result = {"ok": False, "code": "browser_response_unknown", "dispatched": None, "retryable": False}
        try:
            encoded = json.dumps(result, separators=(",", ":")).encode() + b"\n"
            if len(encoded) > MAX_RESPONSE:
                encoded = b'{"ok":false,"code":"browser_response_too_large","dispatched":null}\n'
            writer.write(encoded)
            await asyncio.wait_for(writer.drain(), 5.0)
        except (OSError, TimeoutError):
            pass  # a lost client response never redispatches or settles its operation
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()


async def request(directory: Path, method: str, **fields: Any) -> dict[str, Any]:
    """Call an already live holder. No implicit launch, adoption, retry or stale-file cleanup."""
    directory = Path(directory).absolute()
    _private_directory(directory)
    config = _config(directory)
    descriptor = _read_private(directory / HOLDER_FILE)
    expected = {"version", "boot", "pid", "start", "nonce", "session_id", "socket"}
    if (set(descriptor) != expected or type(descriptor.get("version")) is not int or descriptor.get("version") != 1
            or descriptor.get("session_id") != config["session_id"]
            or type(descriptor.get("pid")) is not int or descriptor["pid"] <= 0
            or not isinstance(descriptor.get("nonce"), str) or len(descriptor["nonce"]) != 64
            or descriptor.get("socket") != str(directory / SOCKET_FILE)):
        raise HolderRefused("browser_holder_unavailable", "invalid browser holder identity record")
    try:
        current = process_identity(descriptor["pid"])
    except Exception as exc:
        raise HolderRefused("browser_holder_unavailable", "the original browser holder is unavailable") from exc
    if any(descriptor[key] != current[key] for key in ("boot", "pid", "start")):
        raise HolderRefused("browser_holder_unavailable", "the browser holder process identity changed")
    if method not in METHODS or set(fields) != ({"token", "ref"} if method == "click" else set()):
        raise HolderRefused("browser_request_invalid", "unsupported browser method or request fields")
    raw = json.dumps({"nonce": descriptor["nonce"], "session_id": config["session_id"],
                      "method": method, **fields}, separators=(",", ":")).encode() + b"\n"
    if len(raw) > MAX_REQUEST:
        raise HolderRefused("browser_request_invalid", "the browser request exceeds 64 KiB")
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_unix_connection(descriptor["socket"],
                                                                           limit=MAX_RESPONSE), 5.0)
    except (OSError, TimeoutError) as exc:
        raise HolderRefused("browser_holder_unavailable", "the original browser holder socket is unavailable") from exc
    try:
        # Verify the connected peer too: a replaced socket cannot borrow the descriptor's identity.
        peer_pid, peer_uid = _peer_credentials(writer)
        if peer_uid != os.getuid() or peer_pid != descriptor["pid"]:
            raise HolderRefused("browser_peer_mismatch", "the browser holder socket belongs to another process")
        current = process_identity(peer_pid)
        if any(descriptor[key] != current[key] for key in ("boot", "pid", "start")):
            raise HolderRefused("browser_holder_unavailable", "the connected browser holder changed incarnation")
        writer.write(raw)
        await asyncio.wait_for(writer.drain(), 5.0)
        response = await asyncio.wait_for(reader.readuntil(b"\n"), REQUEST_TIMEOUT + 2)
        if len(response) > MAX_RESPONSE:
            raise ValueError("response too large")
        value = json.loads(response)
        if not isinstance(value, dict):
            raise TypeError("response is not an object")
        return value
    except (OSError, TimeoutError, ValueError, TypeError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        return {"ok": False, "code": "browser_response_unknown", "dispatched": None, "retryable": False}
    finally:
        writer.close()
        with contextlib.suppress(OSError):
            await writer.wait_closed()


class _StartupStopped(Exception):
    """The stop latch interrupted readiness, before a holder was published."""


async def _retain_launch(task: asyncio.Task, stopping: asyncio.Event):
    """A launch thread cannot be cancelled. Retain its eventual handle before propagating cancel.

    ``launch`` has its own bounded readiness and failed-launch cleanup. Cancelling ``to_thread``
    would discard the only returned cleanup authority while Chrome continues running in the thread.
    """
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
            stopping.set()
    return task.result(), cancelled


async def _during_startup(stopping: asyncio.Event, action: Callable[[], Awaitable[Any]]) -> Any:
    """Interrupt only readiness work after the browser handle is already retained by ``run``."""
    if stopping.is_set():
        raise _StartupStopped
    work = asyncio.create_task(action())
    stopped = asyncio.create_task(stopping.wait())
    try:
        await asyncio.wait((work, stopped), return_when=asyncio.FIRST_COMPLETED)
        if stopping.is_set():
            raise _StartupStopped
        return work.result()
    finally:
        for task in (work, stopped):
            if not task.done():
                task.cancel()
        await asyncio.gather(work, stopped, return_exceptions=True)


async def run(directory: Path) -> None:
    from .browser_authority import BrowserAuthority
    from .browser_guard import authorize

    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    previous_handlers = {}
    fd = chrome = holder = operations = server = authority = None
    try:
        # Signals latch shutdown from the beginning, including while the launch thread owns a
        # browser handle which has not yet returned to this coroutine. They never cancel that thread.
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[sig] = signal.getsignal(sig)
            loop.add_signal_handler(sig, stopping.set)
        await asyncio.sleep(0)
        if stopping.is_set():
            return
        directory = Path(directory).absolute()
        config = _config(directory)
        if (directory / HOLDER_FILE).exists() or (directory / SOCKET_FILE).exists():
            raise HolderRefused("browser_holder_exists", "a holder record already exists; no implicit restart is allowed")
        fd = os.open(directory / "holder.lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # The sole journal owner must be acquired before creating a custodial process.
        authority = BrowserAuthority(Path(config["authority"]))
        authority.assert_available()
        await asyncio.sleep(0)
        if stopping.is_set():
            return
        acquisition = asyncio.create_task(asyncio.to_thread(launch.launch, config["chrome"],
                                                            directory / f"profile-{secrets.token_hex(8)}"))
        chrome, cancelled = await _retain_launch(acquisition, stopping)
        if cancelled:
            raise asyncio.CancelledError
        if stopping.is_set():
            return

        async def connect_owned() -> None:
            nonlocal operations
            # Retain the acquired connection before returning from a cancellable readiness task.
            operations = await CdpBrowserOperations.connect(chrome)

        async def initialize() -> str:
            bound = await operations.bind(pid=chrome.pid, window_id=0)
            if bound.refused:
                raise HolderRefused("browser_binding_unavailable", "the owned browser could not be bound")
            tab = bound.payload["tabs"][0]["tab_id"]
            cdp_session, _ = await operations._session(operations.browser_id, tab)
            await operations.conn.send("Page.enable", session_id=cdp_session)
            loaded = operations.conn.listen("Page.loadEventFired", session_id=cdp_session)
            try:
                navigation = await operations.conn.send("Page.navigate", {"url": config["initial_url"]},
                                                        session_id=cdp_session)
                if navigation.get("errorText"):
                    raise HolderRefused("browser_navigation_failed", "the initial browser URL could not be loaded")
                await asyncio.wait_for(loaded.get(), 15.0)
            finally:
                operations.conn.unlisten(loaded)
            return tab

        try:
            await _during_startup(stopping, connect_owned)
            tab = await _during_startup(stopping, initialize)
            holder = BrowserHolder(config, authority, chrome, operations, tab, authorize)
            holder.stopping = stopping
            server = await asyncio.start_unix_server(holder.serve, path=str(directory / SOCKET_FILE),
                                                     limit=MAX_REQUEST)
            os.chmod(directory / SOCKET_FILE, 0o600)
            # Let an already-delivered stop callback run before publishing readiness. No await is
            # allowed between this latch check and writing the descriptor.
            await asyncio.sleep(0)
            if stopping.is_set():
                return
            descriptor = {"version": 1, **process_identity(os.getpid()), "nonce": holder.nonce,
                          "session_id": config["session_id"], "socket": str(directory / SOCKET_FILE)}
            _write_private(directory / HOLDER_FILE, descriptor)
            async with server:
                await stopping.wait()
        except _StartupStopped:
            pass
    finally:
        try:
            if server is not None:
                server.close()
                await server.wait_closed()
            if holder is not None:
                # Serialize shutdown with a pending admission/activation. Signals never create a
                # second cleanup path racing the original operation.
                async with holder.lock:
                    await holder.close()
            else:
                try:
                    if operations is not None:
                        await operations.close()
                finally:
                    if chrome is not None:
                        await asyncio.to_thread(launch.stop, chrome)
        finally:
            if authority is not None:
                authority.close()
            if fd is not None:
                os.close(fd)
            for sig, previous in previous_handlers.items():
                loop.remove_signal_handler(sig)
                signal.signal(sig, previous)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        asyncio.run(run(args.session))
    except Exception as exc:  # noqa: BLE001 - startup emits a bounded sanitized diagnostic
        # Startup is before mutation admission; never print configuration or guard output.
        print(json.dumps(_error(getattr(exc, "code", "browser_holder_unavailable"),
                                "the browser holder could not start")))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
