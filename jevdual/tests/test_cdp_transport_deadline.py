"""CDP command deadlines include backpressure, and cancellation releases command custody."""

from __future__ import annotations

import asyncio
import json

import pytest
from jevdual.effectors.cdp.transport import CdpClosed, CdpConnection, CdpUnknownOutcome


class Socket:
    def __init__(self, *, block_send=False, send_delay=0):
        self.block_send = block_send
        self.send_delay = send_delay
        self.started = asyncio.Event()
        self.finished = asyncio.Event()
        self.inbox = asyncio.Queue()
        self.sent = []
        self.closed = False

    async def send(self, raw):
        self.started.set()
        self.sent.append(json.loads(raw))
        if self.block_send:
            await asyncio.Event().wait()
        await asyncio.sleep(self.send_delay)
        self.finished.set()

    def __aiter__(self):
        return self

    async def __anext__(self):
        raw = await self.inbox.get()
        if raw is None:
            raise StopAsyncIteration
        return raw

    async def close(self):
        self.closed = True
        self.inbox.put_nowait(None)


def test_command_deadline_bounds_blocked_send_and_retires_the_connection():
    async def run():
        socket = Socket(block_send=True)
        conn = CdpConnection(socket)
        try:
            # The independent watchdog exposes a transport whose own timer never starts.
            with pytest.raises(CdpUnknownOutcome) as unknown:
                await asyncio.wait_for(conn.send("Input.insertText", timeout=0.02), 0.2)
            assert unknown.value.dispatched is None
            assert conn.closed and not conn._pending
            with pytest.raises(CdpClosed):
                await conn.send("Input.insertText")
            assert len(socket.sent) == 1
            await conn.close()  # join the connection-owned cleanup, outside the command budget
            assert socket.closed
        finally:
            await conn.close()

    asyncio.run(run())


@pytest.mark.parametrize("url", [
    "ws://127.0.0.1:9222@attacker.example/devtools/browser/x",
    "ws://127.0.0.1:9222@127.0.0.1:9222/devtools/browser/x",
    "ws://user:password@127.0.0.1:9222/devtools/browser/x",
    "ws://127.0.0.1:0/devtools/browser/x",
    "ws://127.0.0.1:65536/devtools/browser/x",
    "ws://127.0.0.1:bad/devtools/browser/x",
    "ws://127.0.0.1/devtools/browser/x",
    "wss://127.0.0.1:9222/devtools/browser/x",
    "ws://127.0.0.2:9222/devtools/browser/x",
    "ws://127.0.0.1:9222/devtools/page/x",
    "ws://127.0.0.1:9222/devtools/browser/",
    "ws://127.0.0.1:9222/devtools/browser/x?host=elsewhere",
    "ws://127.0.0.1:9222/devtools/browser/x#fragment",
])
def test_invalid_endpoint_never_opens_a_connection(monkeypatch, url):
    import websockets.asyncio.client

    def forbidden(*args, **kwargs):
        pytest.fail("an invalid endpoint reached WebSocket connect")

    monkeypatch.setattr(websockets.asyncio.client, "connect", forbidden)
    with pytest.raises(CdpClosed):
        asyncio.run(CdpConnection.open(url))


def test_valid_loopback_browser_endpoint_reaches_connect(monkeypatch):
    import websockets.asyncio.client

    calls = []

    async def connect(url, **kwargs):
        calls.append((url, kwargs))
        return Socket()

    monkeypatch.setattr(websockets.asyncio.client, "connect", connect)

    async def run():
        conn = await CdpConnection.open("ws://127.0.0.1:9222/devtools/browser/x")
        await conn.close()

    asyncio.run(run())
    assert len(calls) == 1 and calls[0][1]["proxy"] is None


def test_sending_and_reply_wait_share_one_budget():
    async def run():
        socket = Socket(send_delay=0.2)
        conn = CdpConnection(socket)
        try:
            with pytest.raises(CdpUnknownOutcome):
                await asyncio.wait_for(conn.send("DOM.getDocument", timeout=0.5), 0.6)
            assert socket.finished.is_set() and not conn._pending
            # The fully sent command can still receive a late reply without becoming another send.
            socket.inbox.put_nowait(json.dumps({"id": 1, "result": {"late": True}}))
            await asyncio.sleep(0)
            assert len(socket.sent) == 1 and not conn.closed
        finally:
            await conn.close()

    asyncio.run(run())


def test_serialization_failure_does_not_admit_or_send_a_command():
    async def run():
        socket = Socket()
        conn = CdpConnection(socket)
        try:
            with pytest.raises(TypeError):
                await conn.send("Input.insertText", {"invalid": object()})
            assert not conn._pending and not conn.sent and not socket.sent and not conn.closed
        finally:
            await conn.close()

    asyncio.run(run())


def test_an_interrupted_send_retires_other_inflight_commands_as_unknown():
    async def run():
        socket = Socket()
        conn = CdpConnection(socket)
        waiting = asyncio.create_task(conn.send("DOM.getDocument"))
        try:
            await socket.finished.wait()
            socket.block_send = True
            socket.started.clear()
            interrupted = asyncio.create_task(conn.send("Input.insertText"))
            await socket.started.wait()
            interrupted.cancel()
            with pytest.raises(asyncio.CancelledError):
                await interrupted
            with pytest.raises(CdpUnknownOutcome):
                await asyncio.wait_for(waiting, 0.2)
            assert not conn._pending and len(socket.sent) == 2
        finally:
            await conn.close()

    asyncio.run(run())


def test_cancelling_a_close_waiter_does_not_cancel_owned_transport_cleanup():
    async def run():
        socket = Socket()
        entered, release = asyncio.Event(), asyncio.Event()

        async def close():
            entered.set()
            await release.wait()
            socket.inbox.put_nowait(None)

        socket.close = close
        conn = CdpConnection(socket)
        waiter = asyncio.create_task(conn.close())
        await entered.wait()
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert conn.closed and not conn._closing.cancelled()
        release.set()
        await conn.close()
        assert conn._closing.done() and conn._reader.done()

    asyncio.run(run())


@pytest.mark.parametrize("during_send", [True, False])
def test_cancellation_removes_pending_command_and_preserves_cancellation(during_send):
    async def run():
        socket = Socket(block_send=during_send)
        conn = CdpConnection(socket)
        command = asyncio.create_task(conn.send("Input.insertText"))
        try:
            await socket.started.wait()
            if not during_send:
                await socket.finished.wait()
            command.cancel()
            with pytest.raises(asyncio.CancelledError):
                await command
            assert not conn._pending
            assert conn.closed is during_send
            assert len(socket.sent) == 1
            if during_send:
                assert socket.closed
                with pytest.raises(CdpClosed):
                    await conn.send("Input.insertText")
            else:
                socket.inbox.put_nowait(json.dumps({"id": 1, "error": {"message": "late"}}))
                await asyncio.sleep(0)
                assert not conn._pending
        finally:
            await conn.close()

    asyncio.run(run())
