"""A bounded Chrome DevTools Protocol client over one WebSocket.

Each command has an id, one reply and a deadline. A reply with ``error`` means Chrome received the
command and refused it (:class:`CdpError`). No reply, a send failure or a closed connection leaves the
command's outcome unknown (:class:`CdpUnknownOutcome`): it may have run, and nothing here resends it.
A command is never sent once the connection is known to be closed (:class:`CdpClosed`).
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
import math
import os
import socket
import struct
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

#: largest accepted message; a full accessibility tree of a large page fits well inside this
MAX_MESSAGE_BYTES = 64 * 1024 * 1024


class CdpError(RuntimeError):
    """Chrome received the command and answered with an error."""

    def __init__(self, method: str, code: Any, message: str):
        self.method = method
        self.code = code
        super().__init__(f"{method} failed ({code}): {message}")


class CdpClosed(RuntimeError):
    """The connection was already closed; the command was not sent."""

    dispatched = False


class CdpUnknownOutcome(RuntimeError):
    """The command may have reached Chrome, but no reply says what it did."""

    dispatched = None

    def __init__(self, method: str, reason: str):
        self.method = method
        super().__init__(f"{method}: {reason}; outcome unknown")


class CdpConnection:
    """One WebSocket to a browser endpoint. Replies are matched by id; events go to listeners."""

    def __init__(self, ws: Any):
        self._ws = ws
        self._ids = itertools.count(1)
        self._pending: dict[int, tuple[str, asyncio.Future]] = {}
        self._listeners: list[tuple[str, str | None, asyncio.Queue]] = []
        self._closed: str | None = None
        self._closing: asyncio.Task | None = None
        #: every method sent, in order, for the record and for tests; never parameters
        self.sent: list[str] = []
        self._reader = asyncio.create_task(self._read())

    @classmethod
    async def open(cls, url: str, *, timeout: float = 5.0) -> CdpConnection:
        try:
            endpoint = urlsplit(url)
            valid = (
                endpoint.scheme == "ws" and endpoint.hostname == "127.0.0.1"
                and endpoint.username is None and endpoint.password is None
                and endpoint.port is not None and 0 < endpoint.port < 65536
                and endpoint.path.startswith("/devtools/browser/")
                and len(endpoint.path) > len("/devtools/browser/")
                and not endpoint.query and not endpoint.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise CdpClosed("refusing a non-loopback DevTools endpoint or invalid browser endpoint")
        from websockets.asyncio.client import connect

        ws = await connect(
            url, open_timeout=timeout, proxy=None, compression=None, max_size=MAX_MESSAGE_BYTES,
            ping_interval=None,
        )
        return cls(ws)

    @classmethod
    async def open_unix(
        cls, path: Path, *, expected_pid: int, expected_uid: int, timeout: float = 5.0,
        max_message_bytes: int = MAX_MESSAGE_BYTES,
    ) -> CdpConnection:
        """One owned Unix connection, authenticated before its WebSocket handshake.

        Kernel credentials bind this socket to an already owned process. They do not
        grant task authority or isolate the caller from arbitrary same-user code.
        The fixed URI is WebSocket protocol metadata, never a TCP destination.
        """
        from websockets.asyncio.client import unix_connect

        path = Path(path)
        if (not path.is_absolute() or type(expected_pid) is not int or expected_pid <= 0
                or type(expected_uid) is not int or expected_uid < 0
                or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 60
                or type(max_message_bytes) is not int or not 0 < max_message_bytes <= MAX_MESSAGE_BYTES):
            raise CdpClosed("invalid owned Unix endpoint identity")
        raw = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        raw.setblocking(False)
        transferred = False
        try:
            async with asyncio.timeout(timeout):
                await asyncio.get_running_loop().sock_connect(raw, str(path))
                if hasattr(socket, "SO_PEERCRED"):
                    pid, uid, _ = struct.unpack("3i", raw.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                elif os.uname().sysname == "Darwin":
                    credentials = raw.getsockopt(0, 1, 128)  # LOCAL_PEERCRED / xucred
                    version, uid = struct.unpack_from("=II", credentials)
                    if version != 0:
                        raise CdpClosed("Unix peer identity unavailable")
                    pid = struct.unpack("=i", raw.getsockopt(0, 2, 4))[0]  # LOCAL_PEERPID
                else:
                    raise CdpClosed("Unix peer identity unavailable on this platform")
                if (pid, uid) != (expected_pid, expected_uid):
                    raise CdpClosed("Unix endpoint belongs to a different process or user")
                # The library takes this exact authenticated socket; it cannot reconnect
                # through path or proxy discovery while creating the WebSocket.
                ws = await unix_connect(
                    sock=raw, uri="ws://localhost/", open_timeout=timeout, proxy=None,
                    compression=None, max_size=max_message_bytes, ping_interval=None,
                )
                transferred = True
            connection = cls(ws)
            connection.unix_peer_identity = {"pid": pid, "uid": uid}
            return connection
        finally:
            if not transferred:
                raw.close()

    @property
    def closed(self) -> bool:
        return self._closed is not None

    async def send(
        self, method: str, params: dict[str, Any] | None = None, *, session_id: str | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        if self._closed is not None:
            raise CdpClosed(f"{method} not sent: connection closed ({self._closed})")
        id = next(self._ids)
        message: dict[str, Any] = {"id": id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        # Encode before admission: a serialization failure did not reach the socket.
        raw = json.dumps(message)
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[id] = (method, future)
        self.sent.append(method)
        sent = False
        try:
            # One total command budget covers socket backpressure and waiting for Chrome.
            async with asyncio.timeout(timeout):
                await self._ws.send(raw)
                sent = True
                return await asyncio.shield(future)
        except TimeoutError:
            if not sent:
                self._retire("command deadline interrupted a send")
            raise CdpUnknownOutcome(method, f"no reply within {timeout:g}s") from None
        except asyncio.CancelledError:
            if not sent:
                self._retire("cancellation interrupted a send")
            raise
        except (CdpError, CdpUnknownOutcome):
            raise
        except Exception as exc:
            if sent:
                raise
            self._retire(f"send failed ({type(exc).__name__})")
            raise CdpUnknownOutcome(method, f"send failed ({type(exc).__name__})") from exc
        finally:
            self._pending.pop(id, None)
            if not future.done():
                future.cancel()
            elif not future.cancelled():
                future.exception()  # a reply may have arrived while send was interrupted

    def _fail_pending(self, reason: str) -> None:
        for method, future in self._pending.values():
            if not future.done():
                future.set_exception(CdpUnknownOutcome(method, f"{reason} before a reply"))
                future.exception()  # retrieved here; the waiter re-raises it
        self._pending.clear()

    def _retire(self, reason: str) -> None:
        # WebSocket send cancellation can interrupt a fragmented message. Never reuse that socket.
        self._closed = reason
        self._fail_pending(reason)
        self._reader.cancel()
        if self._closing is None:
            self._closing = asyncio.create_task(self._close_transport())

    def listen(self, method: str, *, session_id: str | None = None) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._listeners.append((method, session_id, queue))
        return queue

    def unlisten(self, queue: asyncio.Queue) -> None:
        self._listeners = [entry for entry in self._listeners if entry[2] is not queue]

    async def _read(self) -> None:
        reason = "connection closed"
        try:
            async for raw in self._ws:
                try:
                    message = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                if not isinstance(message, dict):
                    continue
                if "id" in message:
                    method, future = self._pending.pop(message["id"], (None, None))
                    if future is None or future.done():
                        continue
                    error = message.get("error")
                    if isinstance(error, dict):
                        future.set_exception(CdpError(method, error.get("code"), str(error.get("message"))))
                    else:
                        result = message.get("result")
                        future.set_result(result if isinstance(result, dict) else {})
                elif isinstance(message.get("method"), str):
                    params = message.get("params")
                    for name, session, queue in self._listeners:
                        if name == message["method"] and session in (None, message.get("sessionId")):
                            queue.put_nowait(params if isinstance(params, dict) else {})
        except Exception as exc:  # noqa: BLE001 - any loss leaves in-flight commands unknown, never failed
            reason = f"connection lost ({type(exc).__name__})"
        finally:
            self._closed = self._closed or reason
            self._fail_pending(self._closed)

    async def _close_transport(self) -> None:
        try:
            # Cleanup has its own bound and cannot extend a command's deadline. This task is kept
            # by the connection and joined by close(), even when its initiating caller is cancelled.
            async with asyncio.timeout(1.0):
                await self._ws.close()
        except Exception:  # noqa: BLE001 - retire regardless of handshake failure
            transport = getattr(self._ws, "transport", None)
            if transport is not None:
                with contextlib.suppress(Exception):
                    transport.abort()
        finally:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader

    async def close(self) -> None:
        if self._closing is None:
            self._retire(self._closed or "closed by Footwork")
        await asyncio.shield(self._closing)
