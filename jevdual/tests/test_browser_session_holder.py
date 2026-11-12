"""The session browser holder (app-adaptation step B1): one driver held for a ``start --browser`` session.

These run the holder's real socket loop in-process against fake operations; no browser is launched.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from jevdual import browser_session_holder as bsh
from jevdual.browser_driver import BrowserBridge
from jevdual.effectors.base import BrowserRefusal, BrowserReply

URL = "https://example.invalid/form"
BOUND = {"status": "ok", "target_id": "target-1", "tabs": [{"tab_id": "tab-1", "active": True, "url": URL}]}
SNAPSHOT = {
    "status": "ok",
    "page": {"url": URL, "title": "Form"},
    "snapshot": {"id": "snap-1", "complete": True},
    "refs": [{"ref": "snap-1:1", "role": "button", "name": "Continue", "actions": ["click"]}],
}


class FakeOperations:
    def __init__(self, *, prepare_refuses: bool = False, click_raises: bool = False) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.prepare_refuses = prepare_refuses
        self.click_raises = click_raises

    async def prepare(self, **kw):
        self.calls.append(("prepare", kw))
        if self.prepare_refuses:
            return BrowserReply("refused", "background", True,
                                refusal=BrowserRefusal("background_unavailable", "in front"))
        return BrowserReply("ok", "prepared", False, {"status": "ok"})

    async def bind(self, **kw):
        self.calls.append(("bind", kw))
        return BrowserReply("ok", "", False, dict(BOUND))

    async def snapshot(self, **kw):
        self.calls.append(("snapshot", kw))
        return BrowserReply("ok", "", False, dict(SNAPSHOT))

    async def click(self, **kw):
        self.calls.append(("click", kw))
        if self.click_raises:
            raise RuntimeError("driver lost mid-click")
        return BrowserReply("ok", "clicked", False, {"status": "ok"}, effect="confirmed",
                            evidence=("state: checked",), escalation={"target": "x", "reason": "y"})

    async def type_text(self, **kw):
        self.calls.append(("type_text", kw))
        return BrowserReply("ok", "typed", False, {"status": "ok"})

    async def navigate(self, **kw):
        self.calls.append(("navigate", kw))
        return BrowserReply("ok", "navigated", False, {"status": "ok"})


class FakeDriver:
    def __init__(self) -> None:
        self.shut = False

    async def shutdown(self) -> None:
        self.shut = True


async def _held(session: Path, inner: FakeOperations, *, idle_s: float = 60.0):
    driver = FakeDriver()
    task = asyncio.create_task(bsh.serve(
        session, driver=driver, operations=bsh.PrepareOnce(inner),
        binding={"chrome_pid": 42, "window_id": 7, "tab_id": "tab-1", "target_id": "target-1"},
        chrome_alive=lambda: True, idle_s=idle_s, install_signals=False))
    for _ in range(100):
        if bsh.holder_live(session):
            return task, driver
        await asyncio.sleep(0.02)
    raise AssertionError("holder never became live")


def test_a_reply_crosses_the_wire_unchanged():
    reply = BrowserReply("refused", "t", True, {"a": {"b": [1, 2]}},
                         refusal=BrowserRefusal("code", "msg", {"delivery": "unknown", "retryable": False}),
                         hint="h", next_call={"tool": "x"}, dispatched=None, route="dom_event",
                         effect="partial", evidence=("one", "two"), escalation={"target": "t"})
    back = bsh.reply_from_wire(json.loads(json.dumps(bsh.reply_to_wire(reply))))
    assert back == reply
    assert back.refusal.delivery == "unknown" and back.refusal.retryable is False


async def test_one_held_driver_serves_every_command_and_answers_prepare_once(tmp_path):
    inner = FakeOperations()
    task, driver = await _held(tmp_path, inner)
    try:
        for _ in range(3):  # three commands, each with its own bridge, as each CLI process builds one
            bridge = BrowserBridge(bsh.HeldDriver(), 42, 7, operations=bsh.RemoteBrowserOperations(tmp_path))
            await bridge.attach(tab_id="tab-1")
            nm = await bridge.observe()
            eff = await bridge.act(nm, "click", 1)
            assert eff.effect == "confirmed" and eff.evidence == ("state: checked",)
            assert eff.escalation == {"target": "x", "reason": "y"}
        assert [name for name, _ in inner.calls].count("prepare") == 1
        assert [name for name, _ in inner.calls].count("click") == 3
        status = await bsh.call(tmp_path, "status")
        assert status["status"]["prepare_repeats_answered"] == 2
    finally:
        await bsh.stop_async(tmp_path)
        assert await asyncio.wait_for(task, 5) == "stopped"
    assert driver.shut and bsh.holder_live(tmp_path) is None
    assert not bsh.socket_path(tmp_path).exists()


async def test_a_refused_prepare_is_not_kept(tmp_path):
    inner = FakeOperations(prepare_refuses=True)
    task, _ = await _held(tmp_path, inner)
    try:
        ops = bsh.RemoteBrowserOperations(tmp_path)
        for _ in range(2):
            reply = await ops.prepare(pid=42, window_id=7)
            assert reply.refused and reply.refusal.code == "background_unavailable"
        assert [name for name, _ in inner.calls].count("prepare") == 2
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_a_holder_that_is_gone_has_sent_nothing(tmp_path):
    task, _ = await _held(tmp_path, FakeOperations())
    await bsh.stop_async(tmp_path)
    await asyncio.wait_for(task, 5)
    reply = await bsh.RemoteBrowserOperations(tmp_path).click(target_id="target-1", tab_id="tab-1",
                                                             ref="snap-1:1", input_route="dom_event")
    assert reply.refused and reply.dispatched is False
    assert reply.refusal.code == "browser_holder_unavailable" and reply.refusal.delivery == "not_sent"


async def test_an_operation_that_fails_inside_the_holder_is_unknown_not_unsent(tmp_path):
    task, _ = await _held(tmp_path, FakeOperations(click_raises=True))
    try:
        bridge = BrowserBridge(bsh.HeldDriver(), 42, 7, operations=bsh.RemoteBrowserOperations(tmp_path))
        await bridge.attach(tab_id="tab-1")
        nm = await bridge.observe()
        eff = await bridge.act(nm, "click", 1)
        assert eff.effect == "refused" and eff.dispatched is True
        assert eff.error_code == "browser_holder_response_unknown" and eff.delivery == "unknown"
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_a_request_without_the_holders_nonce_is_refused_before_any_driver_call(tmp_path):
    inner = FakeOperations()
    task, _ = await _held(tmp_path, inner)
    try:
        identity = bsh._read_identity(tmp_path)
        reader, writer = await asyncio.open_unix_connection(identity["socket"])
        writer.write(json.dumps({"nonce": "0" * 64, "method": "click",
                                 "args": {"target_id": "t", "tab_id": "t", "ref": "r", "input_route": "dom_event"}}
                                ).encode() + b"\n")
        await writer.drain()
        assert json.loads(await reader.readline()) == {"ok": False, "code": "holder_nonce_mismatch"}
        writer.close()
        assert inner.calls == []
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


@pytest.mark.parametrize("args", [{}, {"target_id": "t", "tab_id": "t", "ref": "r"},
                                  {"target_id": "t", "tab_id": "t", "ref": "r", "input_route": "x", "extra": 1}])
async def test_an_operation_with_other_arguments_is_refused(tmp_path, args):
    inner = FakeOperations()
    task, _ = await _held(tmp_path, inner)
    try:
        assert (await bsh.call(tmp_path, "click", args)) == {"ok": False, "code": "holder_request_invalid"}
        assert inner.calls == []
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_an_idle_holder_exits_and_releases_its_driver(tmp_path):
    task, driver = await _held(tmp_path, FakeOperations(), idle_s=0.2)
    assert await asyncio.wait_for(task, 5) == "idle"
    assert driver.shut and bsh.holder_live(tmp_path) is None


async def test_a_session_uses_only_the_holder_it_recorded(tmp_path, capsys):
    from jevdual.session import SessionState, _held_operations

    task, _ = await _held(tmp_path, FakeOperations())
    try:
        live = bsh.holder_live(tmp_path)
        state = SessionState(dir=str(tmp_path), app="Google Chrome (footwork)", pid=42, window_id=7, task="t",
                             mode="browser", browser_holder={k: live[k] for k in ("boot", "pid", "start")})
        assert isinstance(_held_operations(state), bsh.RemoteBrowserOperations)
        state.browser_holder = {**state.browser_holder, "start": "0.0"}
        assert _held_operations(state) is None
        assert "builds its own driver" in capsys.readouterr().err
        assert _held_operations(SessionState(dir=str(tmp_path), app="x", pid=1, window_id=1, task="t")) is None
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)
