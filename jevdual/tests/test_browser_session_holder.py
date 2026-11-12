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

from tests.test_session_scenarios import fw, world  # noqa: F401 - scenario fixtures

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


async def _held(session: Path, inner: FakeOperations, *, idle_s: float = 60.0, clients=None):
    driver = FakeDriver()
    task = asyncio.create_task(bsh.serve(
        session, driver=driver, operations=bsh.PrepareOnce(inner),
        binding={"chrome_pid": 42, "window_id": 7, "tab_id": "tab-1", "target_id": "target-1"},
        chrome_alive=lambda: True, idle_s=idle_s, install_signals=False, clients=clients))
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
    """The holder's runtime lives outside the session directory (Sol #3), so publishing a staged
    replacement cannot strand it; the session finds it through the recorded runtime."""
    from jevdual.session import SessionState, _held_operations

    runtime, session = tmp_path / "rt", tmp_path / "session"
    runtime.mkdir(mode=0o700)
    session.mkdir()
    task, _ = await _held(runtime, FakeOperations())
    try:
        live = bsh.holder_live(runtime)
        record = {**{k: live[k] for k in ("boot", "pid", "start")}, "runtime": str(runtime)}
        state = SessionState(dir=str(session), app="Google Chrome (footwork)", pid=42, window_id=7, task="t",
                             mode="browser", browser_holder=record)
        held = _held_operations(state)
        assert isinstance(held, bsh.RemoteBrowserOperations) and held.runtime == runtime
        state.browser_holder = {**record, "start": "0.0"}
        assert _held_operations(state) is None
        assert "builds its own driver" in capsys.readouterr().err
        assert _held_operations(SessionState(dir=str(session), app="x", pid=1, window_id=1, task="t")) is None
    finally:
        await bsh.stop_async(runtime)
        await asyncio.wait_for(task, 5)


@pytest.mark.parametrize("new_launch", [True, False])
async def test_a_new_launch_gets_its_own_window_before_any_recovery_window(monkeypatch, new_launch):
    """BH4: recovering a window before a new launch's own window is on screen opened a second window
    on the same page, which the unique-page pin then refused. An existing browser recovers at once."""
    from types import SimpleNamespace

    from jevdual import browser_driver as browser

    opened: list[list[str]] = []
    first_list = [None]
    process = SimpleNamespace(poll=lambda: None, wait=lambda **_: 0, pid=42)
    monkeypatch.setattr(browser, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(browser, "_begin_chrome", lambda url: (42, process if new_launch else None))
    monkeypatch.setattr(browser, "chrome_pid", lambda: 42)
    monkeypatch.setattr(browser, "_incarnation", lambda pid: 1.0)
    monkeypatch.setattr(browser, "_stop_launch", lambda p: None)
    monkeypatch.setattr(browser, "RECOVERY_GRACE_S", 0.5)
    monkeypatch.setattr("jevdual.effectors.require_available", lambda kind: None)
    monkeypatch.setattr("jevdual.effectors.cua.list_windows_input", lambda **kw: kw)

    class Driver:
        async def list_windows(self, _):
            loop = asyncio.get_running_loop()
            first_list[0] = first_list[0] or loop.time()
            late = loop.time() - first_list[0] >= 0.2  # the launch's own window appears after 0.2 s
            on = late or bool(opened)
            window = SimpleNamespace(pid=42, window_id=7, bounds=SimpleNamespace(width=100, height=100))
            return SimpleNamespace(windows=[window] if on else [])

        async def shutdown(self):
            pass

    def spawn(args, **_):
        opened.append(args)
        return SimpleNamespace(pid=99, poll=lambda: 0, wait=lambda **_: 0)

    async def attach(self, **_):
        self.target_id, self.tab_id = "target", "tab"
        return {}

    monkeypatch.setattr(browser, "configured_driver", lambda pid: Driver())
    monkeypatch.setattr(browser.subprocess, "Popen", spawn)
    monkeypatch.setattr(browser.BrowserBridge, "attach", attach)
    await browser.bind_footwork_chrome("http://127.0.0.1:1/")
    if new_launch:
        assert opened == []
    else:
        assert len(opened) == 1 and "--new-window" in opened[0]


def test_devtools_clients_reads_the_client_ends_of_a_real_connection():
    """B2: a real loopback connection, read through lsof. The listening side is not a client."""
    import os
    import socket

    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    client = socket.create_connection(("127.0.0.1", port))
    accepted, _ = server.accept()
    try:
        clients = bsh.devtools_clients(port)
        assert clients == [{"pid": os.getpid(), "command": clients[0]["command"], "connections": 1}]
        assert bsh.second_client_refusal(clients) is None  # this process is the holder here
    finally:
        for s in (client, accepted, server):
            s.close()
    # with no connection lsof exits 1, which is no scan: the positive-evidence rule refuses
    assert bsh.second_client_refusal(bsh.devtools_clients(port)).refusal.code == "browser_client_check_unavailable"


def test_another_client_or_an_unreadable_check_refuses_before_sending():
    import os

    other = bsh.second_client_refusal([{"pid": os.getpid(), "command": "python", "connections": 1},
                                       {"pid": 4242, "command": "node", "connections": 2}])
    assert other.refused and other.dispatched is False and other.refusal.code == "browser_second_client"
    assert "node (pid 4242)" in other.text and other.refusal.delivery == "not_sent"
    unknown = bsh.second_client_refusal(None)
    assert unknown.refusal.code == "browser_client_check_unavailable" and unknown.dispatched is False


async def test_the_holder_refuses_sending_operations_while_another_client_is_connected(tmp_path):
    import os

    connected = [[{"pid": 4242, "command": "node", "connections": 1}]]
    inner = FakeOperations()
    task, _ = await _held(tmp_path, inner, clients=lambda: connected[0])
    try:
        bridge = BrowserBridge(bsh.HeldDriver(), 42, 7, operations=bsh.RemoteBrowserOperations(tmp_path))
        await bridge.attach()
        nm = await bridge.observe()  # observation is not refused
        eff = await bridge.act(nm, "click", 1)
        assert eff.effect == "refused" and eff.dispatched is False and eff.error_code == "browser_second_client"
        assert "click" not in [name for name, _ in inner.calls]
        connected[0] = [{"pid": os.getpid(), "command": "python", "connections": 1}]
        nm = await bridge.observe()
        eff = await bridge.act(nm, "click", 1)
        assert eff.effect == "confirmed"
        assert (await bsh.call(tmp_path, "status"))["status"]["refused_second_client"] == 1
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_an_exception_after_dispatch_is_unknown_even_when_it_is_a_value_error(tmp_path):
    """Sol #1: only parsing may answer "invalid" (read as not sent)."""
    class LateValueError(FakeOperations):
        async def click(self, **kw):
            self.calls.append(("click", kw))
            raise ValueError("raised after the event was dispatched")

    inner = LateValueError()
    task, _ = await _held(tmp_path, inner)
    try:
        reply = await bsh.RemoteBrowserOperations(tmp_path).click(target_id="t", tab_id="t", ref="r",
                                                                 input_route="dom_event")
        assert [n for n, _ in inner.calls] == ["click"]
        assert reply.dispatched is None and reply.refusal.code == "browser_holder_response_unknown"
        assert reply.refusal.delivery == "unknown"
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_a_revoked_claim_fences_the_holder_before_dispatch(tmp_path):
    """Sol #2: the holder re-checks the command's claim in the coordination registry before sending."""
    from jevdual.coordination import Coordinator

    inner = FakeOperations()
    task, _ = await _held(tmp_path, inner)
    registry = Coordinator()
    try:
        async with registry.claim("owner-a", ["app/test"]) as claim:
            fields = {"token": claim.token, "owner": claim.owner, "reservation": "", "desktop": claim.desktop}
            args = {"target_id": "t", "tab_id": "t", "ref": "r", "input_route": "dom_event"}
            live = await bsh.call(tmp_path, "click", args, claim=fields)
            assert live["ok"] and live["reply"]["status"] == "ok"
            registry.revoke(claim.token)
            fenced = bsh.reply_from_wire((await bsh.call(tmp_path, "click", args, claim=fields))["reply"])
            assert fenced.refusal.code == "ownership_revoked" and fenced.dispatched is False
        assert [n for n, _ in inner.calls] == ["click"]
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_a_revoked_command_sends_nothing_to_the_holder(tmp_path):
    from jevdual.coordination import CoordinationError, Coordinator, activated

    inner = FakeOperations()
    task, _ = await _held(tmp_path, inner)
    registry = Coordinator()
    try:
        async with registry.claim("owner-b", ["app/test"]) as claim:
            with activated(claim):
                registry.revoke(claim.token)
                with pytest.raises(CoordinationError):
                    await bsh.RemoteBrowserOperations(tmp_path).click(target_id="t", tab_id="t", ref="r",
                                                                     input_route="dom_event")
        assert inner.calls == []
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_a_cancelled_command_keeps_ownership_until_the_admitted_send_settles(tmp_path):
    """Sol #2: cancellation mid-request revokes further input and waits for the holder's answer."""
    from jevdual.coordination import CoordinationError, Coordinator, activated

    started, release = asyncio.Event(), asyncio.Event()

    class Slow(FakeOperations):
        async def click(self, **kw):
            started.set()
            await release.wait()
            return await super().click(**kw)

    inner = Slow()
    task, _ = await _held(tmp_path, inner)
    registry = Coordinator()
    try:
        async with registry.claim("owner-c", ["app/test"]) as claim:
            with activated(claim):
                request = asyncio.create_task(bsh.RemoteBrowserOperations(tmp_path).click(
                    target_id="t", tab_id="t", ref="r", input_route="dom_event"))
                await asyncio.wait_for(started.wait(), 5)
                request.cancel()
                await asyncio.sleep(0.2)
                assert not request.done()  # still owned while the holder is dispatching
                release.set()
                with pytest.raises(asyncio.CancelledError):
                    await request
            with pytest.raises(CoordinationError):
                claim.check()
        assert [n for n, _ in inner.calls] == ["click"]
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_a_cancelled_start_retires_the_holder_its_spawn_produced(monkeypatch):
    """Sol #4: the spawn thread outlives a cancelled caller; its holder must not be abandoned."""
    import threading

    gate = threading.Event()
    identity = {"pid": 4242, "boot": "b", "start": "1.0", "runtime": "/nonexistent/runtime"}
    retired = []

    def slow_spawn(*, url):
        gate.wait(5)
        return identity

    async def retire(runtime, *, expected=None, timeout_s=10.0):
        retired.append((str(runtime), expected))

    monkeypatch.setattr(bsh, "spawn", slow_spawn)
    monkeypatch.setattr(bsh, "retire", retire)
    starting = asyncio.create_task(bsh.spawn_owned(url=None))
    await asyncio.sleep(0.1)
    starting.cancel()
    await asyncio.sleep(0.1)
    assert not starting.done()
    gate.set()
    with pytest.raises(asyncio.CancelledError):
        await starting
    assert retired == [("/nonexistent/runtime", identity)]


@pytest.mark.parametrize(("returncode", "stdout", "code"), [
    (1, "", "browser_client_check_unavailable"),            # no rows, maybe an inspection error
    # an inspection error's partial output can show this holder and miss another client
    (1, "pSELF\ncpython\nn127.0.0.1:50001->127.0.0.1:9466\n", "browser_client_check_unavailable"),
    (2, "", "browser_client_check_unavailable"),            # lsof failed
    (0, "p4242\ncnode\nn127.0.0.1:50000->127.0.0.1:9466\n", "browser_second_client"),
    (0, ("pSELF\ncpython\nn127.0.0.1:50001->127.0.0.1:9466\n"
         "p4242\ncnode\nn127.0.0.1:50000->127.0.0.1:9466\n"), "browser_second_client"),
    (0, "pSELF\ncpython\nn127.0.0.1:50001->127.0.0.1:9466\n", None),
    (0, "pSELF\ncpython\nn127.0.0.1:9466->127.0.0.1:50001\n", "browser_client_check_unavailable"),
])
def test_the_client_scan_needs_positive_evidence(monkeypatch, returncode, stdout, code):
    """Sol #5: an empty or failed scan, or one without this holder's own connection, refuses."""
    import os
    import subprocess
    from types import SimpleNamespace

    out = stdout.replace("SELF", str(os.getpid()))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=returncode, stdout=out,
                                                                           stderr="lsof: an error"))
    refusal = bsh.second_client_refusal(bsh.devtools_clients(9466))
    assert (refusal.refusal.code if refusal else None) == code
    if refusal:
        assert refusal.dispatched is False


def _threaded_holder(runtime: Path):
    """A holder serving on its own thread and loop, as a separate session's would."""
    import threading

    runtime.mkdir(mode=0o700)
    ready = threading.Event()

    def holder_thread():
        async def run():
            serving = asyncio.create_task(bsh.serve(
                runtime, driver=FakeDriver(), operations=bsh.PrepareOnce(FakeOperations()),
                binding={"chrome_pid": 42, "window_id": 7}, chrome_alive=lambda: True, idle_s=60,
                install_signals=False))
            while bsh.holder_live(runtime) is None:
                await asyncio.sleep(0.02)
            ready.set()
            await serving
        asyncio.run(run())

    thread = threading.Thread(target=holder_thread, daemon=True)
    thread.start()
    assert ready.wait(5)
    return thread


def _record_holder(cli, runtime: Path) -> None:
    import json

    saved = json.loads((cli.session / "session.json").read_text())
    live = bsh.holder_live(runtime)
    saved["browser_holder"] = {**{k: live[k] for k in ("boot", "pid", "start")}, "runtime": str(runtime)}
    (cli.session / "session.json").write_text(json.dumps(saved))


def test_a_replacement_start_retires_the_holder_of_the_session_it_replaces(world, fw, tmp_path):  # noqa: F811
    """Sol #3: a published replacement retires the previous session's holder."""

    from jevdual import browser_target  # noqa: F401 - imported for the scenario fixtures

    runtime = tmp_path / "old-rt"
    thread = _threaded_holder(runtime)
    assert fw("start", "Old native task", "--app", "Calculator")[0] == 0
    _record_holder(fw, runtime)
    code, out, err = fw("start", "New native task", "--app", "Calculator")
    assert code == 0, (out, err)
    thread.join(timeout=10)
    assert not thread.is_alive() and bsh.holder_live(runtime) is None


@pytest.mark.parametrize("durable", [False, True])
def test_the_replaced_sessions_holder_is_gone_before_the_replacement_binds(world, fw, tmp_path, monkeypatch,  # noqa: F811
                                                                          durable):
    """Sol re-review #2: the old holder's DevTools connection would make the new holder refuse its
    first navigation as a second client, so it is retired before the replacement starts."""
    from jevdual import session

    runtime = tmp_path / "old-rt"
    thread = _threaded_holder(runtime)
    assert fw("start", "Old native task", "--app", "Calculator")[0] == 0
    _record_holder(fw, runtime)
    seen = []

    async def start_new(args):
        seen.append(bsh.holder_live(runtime))
        return 2

    monkeypatch.setattr(session, "_start_new", start_new)
    args = ["start", "New task", "--app", "Calculator"]
    if durable:
        args += ["--authority", str(tmp_path / "authority.db")]
    fw(*args)
    assert seen == [None]
    thread.join(timeout=10)
    assert not thread.is_alive()


async def test_a_refused_first_navigation_refuses_the_start(tmp_path, monkeypatch, capsys):
    """Sol re-review #2: a start must not be published bound to whatever page the browser showed."""
    from types import SimpleNamespace

    from jevdual import browser_driver, session
    from jevdual.browser_driver import BrowserEffect

    class Bridge:
        pid, window_id, tab_id = 42, 7, "tab-1"
        observed = False

        async def navigate(self, url):
            return BrowserEffect("navigate", -1, url, "refused", summary="another DevTools client",
                                 error_code="browser_second_client", dispatched=False)

        async def observe(self):
            Bridge.observed = True
            raise AssertionError("a refused start must not observe")

    driver = FakeDriver()

    async def bind(url, *, policy=None, wrap_operations=None):
        return driver, Bridge()

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", bind)
    args = SimpleNamespace(mode=None, url="http://127.0.0.1:1/", task="t", require="", authorize="",
                           answer=None, pointer_motion="off", text=0)
    assert await session._start_browser(args, tmp_path) == 2
    assert "browser_second_client" in capsys.readouterr().err
    assert driver.shut and not Bridge.observed and not (tmp_path / "session.json").exists()


async def test_the_holder_rechecks_ownership_after_the_client_scan(tmp_path):
    """Sol re-review #1: a claim revoked while the client scan runs is not acted for."""
    import os

    from jevdual.coordination import Coordinator

    registry = Coordinator()
    pending = {}

    def scan():
        registry.revoke(pending["token"])  # revoked mid-scan
        return [{"pid": os.getpid(), "command": "python", "connections": 1}]

    inner = FakeOperations()
    task, _ = await _held(tmp_path, inner, clients=scan)
    try:
        async with registry.claim("owner-d", ["app/test"]) as claim:
            pending["token"] = claim.token
            fields = {"token": claim.token, "owner": claim.owner, "reservation": "", "desktop": claim.desktop}
            args = {"target_id": "t", "tab_id": "t", "ref": "r", "input_route": "dom_event"}
            fenced = bsh.reply_from_wire((await bsh.call(tmp_path, "click", args, claim=fields))["reply"])
            assert fenced.refusal.code == "ownership_revoked" and fenced.dispatched is False
        assert inner.calls == []
    finally:
        await bsh.stop_async(tmp_path)
        await asyncio.wait_for(task, 5)


async def test_retirement_waits_until_the_driver_has_shut_down(tmp_path):
    """Sol re-review #4: the old driver's DevTools connection is closed before retire returns."""
    class SlowDriver(FakeDriver):
        async def shutdown(self):
            await asyncio.sleep(0.5)
            self.shut = True

    driver = SlowDriver()
    task = asyncio.create_task(bsh.serve(
        tmp_path, driver=driver, operations=bsh.PrepareOnce(FakeOperations()),
        binding={"chrome_pid": 42, "window_id": 7}, chrome_alive=lambda: True, idle_s=60,
        install_signals=False))
    for _ in range(100):
        if bsh.holder_live(tmp_path):
            break
        await asyncio.sleep(0.02)
    await bsh.retire(tmp_path)
    assert driver.shut
    await asyncio.wait_for(task, 5)


def test_a_subprocess_holder_is_retired_only_once_its_process_has_exited(tmp_path, monkeypatch):
    """Sol re-review #4: a missing record is not proof that another process has exited."""
    import subprocess
    import time

    from jevdual.browser_holder import process_identity

    child = subprocess.Popen(["sleep", "30"])
    try:
        record = {**process_identity(child.pid), "nonce": "n"}
        state = {"record": True}
        monkeypatch.setattr(bsh, "holder_live", lambda runtime: record if state["record"] else None)

        async def stop(runtime, method, *a, **k):
            state["record"] = False  # the record goes; the process lingers until SIGTERM
            return {"ok": True}

        monkeypatch.setattr(bsh, "call", stop)
        started = time.monotonic()
        asyncio.run(bsh.retire(tmp_path, timeout_s=0.5))
        assert child.poll() is not None  # it was terminated, not taken as gone
        assert time.monotonic() - started >= 0.5
    finally:
        child.kill()
        child.wait()


async def test_spawn_cleanup_survives_repeated_cancellation(monkeypatch):
    """Sol re-review #5: a second cancellation during retirement does not abandon it."""
    import threading

    gate = threading.Event()
    identity = {"pid": 4242, "boot": "b", "start": "1.0", "runtime": "/nonexistent/runtime"}
    entered, finished = asyncio.Event(), []

    def slow_spawn(*, url):
        gate.wait(5)
        return identity

    async def retire(runtime, *, expected=None, timeout_s=10.0):
        entered.set()
        await asyncio.sleep(0.3)
        finished.append(str(runtime))

    monkeypatch.setattr(bsh, "spawn", slow_spawn)
    monkeypatch.setattr(bsh, "retire", retire)
    starting = asyncio.create_task(bsh.spawn_owned(url=None))
    await asyncio.sleep(0.1)
    starting.cancel()
    gate.set()
    await asyncio.wait_for(entered.wait(), 5)
    starting.cancel()  # again, while retiring
    with pytest.raises(asyncio.CancelledError):
        await starting
    assert finished == ["/nonexistent/runtime"]


def _identity_of(pid: int) -> dict:
    from jevdual.browser_holder import process_identity

    return {**process_identity(pid), "runtime": "/nonexistent"}


def test_a_holder_whose_record_is_gone_is_still_waited_for(tmp_path, monkeypatch):
    """Sol round 3 #1: a recorded identity is waited for even after its record is removed."""
    import subprocess

    child = subprocess.Popen(["sleep", "30"])
    try:
        monkeypatch.setattr(bsh, "holder_live", lambda runtime: None)
        asyncio.run(bsh.retire(tmp_path, expected=_identity_of(child.pid), timeout_s=0.3))
        assert child.poll() is not None  # it was waited for and terminated, not taken as gone
    finally:
        child.kill()
        child.wait()


def test_a_reused_pid_is_not_retired(tmp_path, monkeypatch):
    import subprocess

    child = subprocess.Popen(["sleep", "30"])
    try:
        monkeypatch.setattr(bsh, "holder_live", lambda runtime: None)
        stale = {**_identity_of(child.pid), "start": "0.0"}  # same PID, another process start
        assert asyncio.run(bsh.retire(tmp_path, expected=stale, timeout_s=0.3)) is None
        assert child.poll() is None
    finally:
        child.kill()
        child.wait()


def test_a_holder_that_survives_sigterm_is_reported_still_running(tmp_path, monkeypatch):
    """Sol round 3 #2: a timeout is not a completed retirement."""
    import subprocess
    import sys
    import time

    code = ("import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "print('ready', flush=True); time.sleep(30)")
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE)
    try:
        assert child.stdout.readline().strip() == b"ready"
        monkeypatch.setattr(bsh, "holder_live", lambda runtime: None)
        monkeypatch.setattr(bsh, "TERM_GRACE_S", 0.3)
        with pytest.raises(bsh.HolderStillRunning):
            asyncio.run(bsh.retire(tmp_path, expected=_identity_of(child.pid), timeout_s=0.3))
        time.sleep(0.1)
        assert child.poll() is None
    finally:
        child.kill()
        child.wait()


def test_a_replacement_start_refuses_while_the_replaced_holder_may_be_connected(world, fw, tmp_path,  # noqa: F811
                                                                              monkeypatch):
    """Sol round 3 #2: a holder that did not stop blocks the replacement before it binds."""
    from jevdual import session

    runtime = tmp_path / "old-rt"
    thread = _threaded_holder(runtime)
    assert fw("start", "Old native task", "--app", "Calculator")[0] == 0
    _record_holder(fw, runtime)
    before = (fw.session / "session.json").read_bytes()
    started = []

    async def survives(runtime, *, expected=None, timeout_s=10.0):
        raise bsh.HolderStillRunning(int(expected["pid"]))

    async def start_new(args):
        started.append(args)
        return 0

    monkeypatch.setattr(bsh, "retire", survives)
    monkeypatch.setattr(session, "_start_new", start_new)
    code, out, err = fw("start", "New task", "--app", "Calculator")
    assert code == 2 and "did not stop" in err, (out, err)
    assert started == [] and (fw.session / "session.json").read_bytes() == before
    monkeypatch.undo()
    asyncio.run(bsh.retire(runtime))
    thread.join(timeout=10)
