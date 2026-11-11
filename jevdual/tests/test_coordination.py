"""Cross-process arbitration, cancellation fencing and command/readback boundaries."""
from __future__ import annotations

import asyncio
import json
import multiprocessing
import os
import signal
import threading
from types import SimpleNamespace

import pytest
from jevdual.coordination import (
    CoordinationError,
    Coordinator,
    activated,
    app_resource,
    checkpoint,
    guard_driver,
    owned_thread,
)
from jevdual.session import SessionState, run_command


def _holder(path, owner, resources, acquired, release):
    async def run():
        async with Coordinator(path).claim(owner, resources, timeout=4):
            acquired.set()
            await asyncio.to_thread(release.wait, 5)
    asyncio.run(run())


def _session_writer(path, directory, acquired, release):
    # A real fresh CLI process using the common registry, without a driver.
    import jevdual.coordination as module
    original = module.Coordinator
    module.Coordinator = lambda: original(path)

    async def write(args):
        state = SessionState.load(directory)
        acquired.set()
        await asyncio.to_thread(release.wait, 5)
        state.step += 1
        state.save()
        return 0

    args = SimpleNamespace(_session_command=True, cmd="look", session=str(directory), fn=write)
    assert asyncio.run(run_command(args)) == 0


def test_cross_process_conflicts_serialize_and_independent_apps_overlap(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    path = tmp_path / "registry.sqlite"
    processes = []
    releases = []
    acquired = []
    try:
        for owner, resources in [("one", ["app/editor"]), ("two", ["app/editor/window/2"]),
                                 ("three", ["app/browser/window/3"])]:
            ready, release = ctx.Event(), ctx.Event()
            process = ctx.Process(target=_holder, args=(path, owner, resources, ready, release))
            process.start()
            processes.append(process)
            releases.append(release)
            acquired.append(ready)
            if owner == "one":
                assert ready.wait(5)
        assert acquired[2].wait(5)
        assert not acquired[1].wait(.15)
        status = Coordinator(path).status()["requests"]
        assert {r["state"] for r in status} == {"active", "waiting"}
        releases[0].set()
        assert acquired[1].wait(5)
    finally:
        for release in releases:
            release.set()
        for process in processes:
            process.join(8)
            if process.is_alive():
                process.kill()
                process.join()
            assert process.exitcode == 0


def test_real_session_writers_do_not_lose_updates(tmp_path):
    directory = tmp_path / "session"
    directory.mkdir()
    SessionState(str(directory), "Editor", 77, 1, "task").save()
    ctx = multiprocessing.get_context("spawn")
    path = tmp_path / "registry.sqlite"
    ready1, ready2, release1, release2 = (ctx.Event() for _ in range(4))
    processes = [ctx.Process(target=_session_writer, args=(path, directory, ready1, release1)),
                 ctx.Process(target=_session_writer, args=(path, directory, ready2, release2))]
    try:
        processes[0].start()
        assert ready1.wait(5)
        processes[1].start()
        assert not ready2.wait(.15)
        release1.set()
        assert ready2.wait(5)
        release2.set()
    finally:
        release1.set()
        release2.set()
        for process in processes:
            if process.pid:
                process.join(8)
                if process.is_alive():
                    process.kill()
                    process.join()
                assert process.exitcode == 0
    assert SessionState.load(directory).step == 2


async def test_reservation_survives_command_gaps_and_fences_stale_cleanup(tmp_path):
    store = Coordinator(tmp_path / "registry.sqlite")
    async with store.claim("film", ["desktop", "app/editor"]) as claim:
        token = store.reserve(claim, claim.resources)
    # Reopen the store, as another CLI process would.
    store = Coordinator(store.path)
    for resources in (["desktop"], ["app/editor/window/2"]):
        with pytest.raises(CoordinationError, match="busy"):
            async with store.claim("other", resources, timeout=0):
                pytest.fail("reservation failed")
    async with store.claim("other", ["app/browser/window/3"], timeout=0):
        pass
    async with store.claim("film", ["desktop"], reservation=token, timeout=0):
        pass
    store.revoke(token)
    async with store.claim("new film", ["desktop", "app/editor"]) as claim:
        newer = store.reserve(claim, claim.resources)
    store.revoke(token)
    assert next(r for r in store.status()["reservations"] if r["token"] == newer)["state"] == "active"
    with pytest.raises(CoordinationError, match="reservation unavailable"):
        async with store.claim("film", ["desktop"], reservation=token, timeout=0):
            pytest.fail("revoked film resumed")


async def test_cancelled_request_retains_conflicting_ownership_until_cleanup(tmp_path):
    store = Coordinator(tmp_path / "registry.sqlite")
    events = []

    class Driver:
        async def call_tool(self, name, *args):
            events.append(name)
        async def shutdown(self):
            events.append("shutdown")

    async with store.claim("one", ["desktop"]) as claim:
        with activated(claim):
            driver = guard_driver(Driver())
            await driver.call_tool("type_text", "{}")
            store.revoke(claim.token)
            with pytest.raises(CoordinationError):
                await driver.call_tool("type_text", "{}")
            await driver.call_tool("get_browser_state", "{}")
            await driver.shutdown()
        with pytest.raises(CoordinationError, match="busy"):
            async with store.claim("two", ["desktop"], timeout=0):
                pytest.fail("cleanup overlap")
    async with store.claim("two", ["desktop"], timeout=0):
        pass
    assert events == ["type_text", "get_browser_state", "shutdown"]


async def test_canceled_waiter_never_dispatches(tmp_path):
    store = Coordinator(tmp_path / "registry.sqlite")
    async with store.claim("one", ["desktop"]):
        waiter = asyncio.create_task(store.claim("two", ["desktop"]).__aenter__())
        for _ in range(100):
            waiting = [r for r in store.status()["requests"] if r["state"] == "waiting"]
            if waiting:
                break
            await asyncio.sleep(.01)
        assert waiting
        store.revoke(waiting[0]["token"])
        with pytest.raises(CoordinationError, match="canceled"):
            await waiter
    assert store.status()["requests"] == []


async def test_session_resource_is_global_across_desktops(tmp_path, monkeypatch):
    store = Coordinator(tmp_path / "registry.sqlite")
    monkeypatch.setenv("DISPLAY", ":1")
    async with store.claim("one", ["session/one"]):
        monkeypatch.setenv("DISPLAY", ":2")
        with pytest.raises(CoordinationError, match="busy"):
            async with store.claim("two", ["session/one"], timeout=0):
                pytest.fail("same session has two writers")
        async with store.claim("two", ["desktop"], timeout=0):
            pass


async def test_thread_cancellation_waits_for_input_cleanup(tmp_path):
    store = Coordinator(tmp_path / "registry.sqlite")
    started, finish = threading.Event(), threading.Event()
    cleaned = []

    def worker():
        started.set()
        finish.wait(5)
        cleaned.append(True)

    async def run():
        async with store.claim("one", ["desktop"]) as claim:
            with activated(claim):
                await owned_thread(worker)

    task = asyncio.create_task(run())
    assert await asyncio.to_thread(started.wait, 3)
    task.cancel()
    await asyncio.sleep(.03)
    assert not task.done()
    with pytest.raises(CoordinationError, match="busy"):
        async with store.claim("two", ["desktop"], timeout=0):
            pytest.fail("thread abandoned")
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cleaned == [True]
    async with store.claim("two", ["desktop"], timeout=0):
        pass


def test_process_death_releases_command_but_not_persistent_reservation(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    path = tmp_path / "registry.sqlite"
    ready, release = ctx.Event(), ctx.Event()
    process = ctx.Process(target=_holder, args=(path, "one", ["app/editor"], ready, release))
    process.start()
    try:
        assert ready.wait(5)
        os.kill(process.pid, signal.SIGKILL)
        process.join(5)
        store = Coordinator(path)
        assert store.status()["requests"] == []
    finally:
        if process.is_alive():
            process.kill()
            process.join()


async def test_readback_is_inside_app_and_desktop_ownership(tmp_path):
    store = Coordinator()
    directory = tmp_path / "session"
    directory.mkdir()
    SessionState(str(directory), "Editor", 77, 1, "task", posture="foreground_permitted").save()
    phases = []

    async def action(args):
        checkpoint()
        phases.append("dispatch")
        with pytest.raises(CoordinationError):
            async with store.claim("other", [app_resource("Editor")], timeout=0):
                pytest.fail("another command changed readback")
        with pytest.raises(CoordinationError):
            async with store.claim("other", ["desktop"], timeout=0):
                pytest.fail("idle check is not exclusion")
        phases.append("readback")
        return 0

    args = SimpleNamespace(_session_command=True, cmd="do", session=str(directory), fn=action)
    assert await run_command(args) == 0
    assert phases == ["dispatch", "readback"]
    assert store.status()["requests"] == []


async def test_explicit_control_reservation_and_observe_only(tmp_path, capsys):
    from jevdual.cli import build_parser
    from jevdual.coordination_cli import command

    directory = tmp_path / "session"
    directory.mkdir()
    state = SessionState(str(directory), "Editor", 77, 1, "task", last_page_text="saved text")
    state.save()
    parser = build_parser()
    assert await command(parser.parse_args(["control", "reserve", "--session", str(directory)])) == 0
    token = json.loads(capsys.readouterr().out)["token"]
    assert SessionState.load(directory).coordination_token == token
    assert await command(parser.parse_args(["control", "observe", "--session", str(directory)])) == 0
    assert json.loads(capsys.readouterr().out)["live"] is False
    assert await command(parser.parse_args(["control", "yield", token])) == 0
    capsys.readouterr()
    assert await command(parser.parse_args(["control", "reserve", "--session", str(directory)])) == 0
    newer = json.loads(capsys.readouterr().out)["token"]
    assert newer != token


def test_hard_killed_desktop_owner_requires_explicit_input_recovery(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    path = tmp_path / "registry.sqlite"
    ready, release = ctx.Event(), ctx.Event()
    process = ctx.Process(target=_holder, args=(path, "one", ["desktop"], ready, release))
    process.start()
    try:
        assert ready.wait(5)
        os.kill(process.pid, signal.SIGKILL)
        process.join(5)
        store = Coordinator(path)
        row, = store.status()["requests"]
        assert row["state"] == "orphaned"

        async def blocked():
            with pytest.raises(CoordinationError, match="busy"):
                async with store.claim("two", ["desktop"], timeout=0):
                    pytest.fail("orphaned pointer owner silently released")
        asyncio.run(blocked())
        store.recover(row["token"])
        assert store.status()["requests"] == []
    finally:
        if process.is_alive():
            process.kill()
            process.join()


async def test_reservation_cancel_stops_drag_and_releases_owned_button(tmp_path):
    from jevdual.drag import DragPlan, Sample, play_drag

    store = Coordinator(tmp_path / "registry.sqlite")
    events = []
    async with store.claim("film", ["desktop"]) as claim:
        class Clock:
            t = 0
            def now(self):
                return self.t
            def sleep_until(self, t):
                self.t = t

        class Poster:
            def location(self):
                return (0, 0)
            def foreign_input(self):
                return None
            def down(self, *point):
                events.append("down")
                store.revoke(claim.token)
            def drag(self, *point):
                events.append("drag")
            def up(self, *point):
                events.append("up")
            def escape(self):
                events.append("escape")
        plan = DragPlan((0, 0), (20, 0), (Sample(0, 0, 0), Sample(.01, 20, 0)), "test", 20)
        with activated(claim):
            result = play_drag(plan, Poster(), Clock())
        assert result.outcome == "aborted:cancelled"
        assert events == ["down", "escape", "up"]


async def test_restart_claims_new_app_instead_of_prior_session_app(tmp_path):
    directory = tmp_path / "session"
    directory.mkdir()
    SessionState(str(directory), "Old app", 77, 1, "old task").save()
    seen = []

    async def start(args):
        seen.extend(args._coordination_claim.resources)
        return 0
    args = SimpleNamespace(_session_command=True, cmd="start", session=str(directory),
                           app="New app", mode="background_only", fn=start)
    assert await run_command(args) == 0
    assert seen == [app_resource("New app")]


async def test_different_authority_databases_share_the_same_app_coordinator(tmp_path):
    store = Coordinator()
    directory = tmp_path / "session"
    directory.mkdir()
    SessionState(str(directory), "Editor", 77, 1, "task", authority=str(tmp_path / "first.db")).save()

    async def action(args):
        assert args._authority_owned
        with pytest.raises(CoordinationError, match="busy"):
            async with store.claim("other-authority", [app_resource("Editor")], timeout=0):
                pytest.fail("authority path bypassed app coordination")
        return 0
    args = SimpleNamespace(_session_command=True, cmd="do", session=str(directory), fn=action)
    assert await run_command(args) == 0


def test_chrome_native_barrier_conflicts_with_each_browser_window():
    from jevdual.coordination import conflicts

    broad = app_resource("Chrome")
    first = app_resource("Google Chrome (footwork)", window="77/1")
    second = app_resource("Google Chrome", window="77/2")
    assert conflicts([broad], [first]) and conflicts([broad], [second])
    assert not conflicts([first], [second])


async def test_headed_browser_start_owns_desktop_even_for_background_page_posture(tmp_path):
    seen = []

    async def start(args):
        seen.extend(args._coordination_claim.resources)
        return 0
    args = SimpleNamespace(_session_command=True, cmd="start", session=str(tmp_path / "session"),
                           browser=True, mode="background_only", fn=start)
    assert await run_command(args) == 0
    assert set(seen) == {"desktop", app_resource("Google Chrome")}
