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
from typing import Any

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
        #: every method sent, in order, for the record and for tests; never parameters
        self.sent: list[str] = []
        self._reader = asyncio.create_task(self._read())

    @classmethod
    async def open(cls, url: str, *, timeout: float = 5.0) -> CdpConnection:
        from websockets.asyncio.client import connect

        if not url.startswith("ws://127.0.0.1:"):
            raise CdpClosed(f"refusing a non-loopback DevTools endpoint: {url[:80]}")
        ws = await connect(
            url, open_timeout=timeout, proxy=None, compression=None, max_size=MAX_MESSAGE_BYTES,
            ping_interval=None,
        )
        return cls(ws)

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
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[id] = (method, future)
        message: dict[str, Any] = {"id": id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        self.sent.append(method)
        try:
            await self._ws.send(json.dumps(message))
        except Exception as exc:
            self._pending.pop(id, None)
            raise CdpUnknownOutcome(method, f"send failed ({type(exc).__name__})") from exc
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout)
        except TimeoutError:
            self._pending.pop(id, None)
            raise CdpUnknownOutcome(method, f"no reply within {timeout:g}s") from None

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
            self._closed = reason
            for method, future in self._pending.values():
                if not future.done():
                    future.set_exception(CdpUnknownOutcome(method, f"{reason} before a reply"))
                    future.exception()  # retrieved here; the waiter re-raises it
            self._pending.clear()

    async def close(self) -> None:
        if self._closed is None:
            self._closed = "closed by Footwork"
        try:
            await self._ws.close()
        finally:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader
