"""Browser ownership must survive platform discovery without widening attachment."""

from types import SimpleNamespace

import pytest
from jevdual import browser_driver as browser


def test_explicit_browser_is_resolved_and_must_be_executable(tmp_path, monkeypatch):
    binary = tmp_path / "chrome"
    binary.write_text("browser fixture")
    monkeypatch.setenv("FOOTWORK_CHROME_EXECUTABLE", str(binary))
    with pytest.raises(RuntimeError, match="executable"):
        browser.chrome_executable()
    binary.chmod(0o700)
    assert browser.chrome_executable() == str(binary.resolve())


def test_linux_discovers_chromium_without_a_mac_path(tmp_path, monkeypatch):
    binary = tmp_path / "chromium"
    binary.write_text("browser fixture")
    binary.chmod(0o700)
    monkeypatch.delenv("FOOTWORK_CHROME_EXECUTABLE", raising=False)
    monkeypatch.setattr(browser.sys, "platform", "linux")
    monkeypatch.setattr(browser, "_browser_candidates", lambda: [str(binary)])
    assert browser.chrome_executable() == str(binary)


def test_invalid_explicit_browser_never_falls_back(monkeypatch):
    monkeypatch.setenv("FOOTWORK_CHROME_EXECUTABLE", "/missing/explicit-browser")
    monkeypatch.setattr(browser, "_browser_candidates", lambda: pytest.fail("must not fall back"))
    with pytest.raises(RuntimeError, match="executable"):
        browser.chrome_executable()


def process(pid, args, exe="/test/chrome"):
    return SimpleNamespace(info={"pid": pid, "cmdline": args, "exe": exe, "uids": SimpleNamespace(real=42)})


def test_process_discovery_requires_exact_profile_port_executable_and_owner(monkeypatch):
    import psutil

    profile = f"--user-data-dir={browser.PROFILE_DIR}"
    port = f"--remote-debugging-port={browser.PORT}"
    candidates = [
        process(1, ["chrome", profile + "-other", port]),
        process(2, ["chrome", profile, port], exe="/other/chrome"),
        process(3, ["chrome", profile, port, "--type=renderer"]),
        process(4, ["chrome", profile, "--remote-debugging-port=1"]),
        process(5, ["chrome", profile, port]),
    ]
    candidates[4].info["uids"] = SimpleNamespace(real=99)
    monkeypatch.setattr(browser.os, "getuid", lambda: 42)
    monkeypatch.setattr(browser, "chrome_executable", lambda: "/test/chrome")
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: iter(candidates))
    assert browser.chrome_pid() is None
    candidates.append(process(6, ["chrome", profile, port]))
    assert browser.chrome_pid() == 6
    candidates.append(process(7, ["chrome", profile, port]))
    with pytest.raises(RuntimeError, match="multiple"):
        browser.chrome_pid()


@pytest.mark.asyncio
async def test_attachment_requires_fingerprint_and_same_process_incarnation(monkeypatch):
    import json
    import sys

    import psutil

    class Host:
        pass

    fake = SimpleNamespace(
        DriverAuthorizationHost=Host,
        DriverAuthorizationAction=SimpleNamespace(ALLOW="allow", DENY="deny"),
        DriverAuthorizationDecision=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setitem(sys.modules, "cua_driver", fake)
    monkeypatch.setattr(browser, "chrome_executable", lambda: "/test/chrome")
    monkeypatch.setattr(browser, "chrome_pid", lambda: 12)
    start = [1.0]
    monkeypatch.setattr(psutil, "Process", lambda pid: SimpleNamespace(create_time=lambda: start[0]))
    host = browser._host_class(12)()

    async def decision(resource):
        return (await host.authorize(SimpleNamespace(
            resource_json=json.dumps(resource), human_summary="fixture", request_digest="request"
        ))).action

    resource = {"pid": 12, "endpoint_owner_pid": 12, "process_fingerprint": {"executable": "/test/chrome"}}
    assert await decision(resource) == "allow"
    assert await decision({"pid": 12}) == "deny"
    assert await decision({**resource, "endpoint_owner_pid": 13}) == "deny"
    assert await decision([]) == "deny"
    start[0] = 2.0
    assert await decision(resource) == "deny"


@pytest.fixture
def browser_world(monkeypatch, tmp_path):
    """Owned process metadata and SDK replies; no real browser or desktop."""
    import sys

    import psutil

    state = SimpleNamespace(pid=12, incarnation=1.0, windows=[], commands=[], children=[],
                            attached=[], shutdowns=0, spawn_error=None, helper_status=0)
    monkeypatch.setattr(browser, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(browser, "PROFILE_DIR", tmp_path / "profile")
    monkeypatch.setattr(browser, "chrome_executable", lambda: "/test/chrome")
    monkeypatch.setattr(browser.os, "getuid", lambda: 42)

    def processes(attrs):
        return iter([] if state.pid is None else [process(state.pid, [
            "/test/chrome", f"--user-data-dir={browser.PROFILE_DIR}",
            f"--remote-debugging-port={browser.PORT}",
        ])])

    monkeypatch.setattr(psutil, "process_iter", processes)
    monkeypatch.setattr(psutil, "Process", lambda pid: SimpleNamespace(create_time=lambda: state.incarnation))

    class Child:
        pid = 13
        returncode = None
        terminated = False
        killed = False
        waited = False

        def poll(self):
            return self.returncode

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def kill(self):
            self.killed = True
            self.returncode = -9

        def wait(self, timeout=None):
            self.waited = True
            return self.returncode

    def spawn(command, **kwargs):
        state.commands.append(command)
        if state.spawn_error:
            raise state.spawn_error
        child = Child()
        child.returncode = state.helper_status
        state.children.append(child)
        state.on_spawn()
        return child

    state.on_spawn = lambda: state.windows.append(SimpleNamespace(
        window_id=91, pid=12, is_on_screen=True, bounds=SimpleNamespace(width=1200, height=900)))
    monkeypatch.setattr(browser.subprocess, "Popen", spawn)
    monkeypatch.setattr(browser.subprocess, "run", lambda *a, **k: pytest.fail("macOS open used on Linux"))

    class Driver:
        async def list_windows(self, request):
            assert request.pid == state.pid
            return SimpleNamespace(windows=list(state.windows))

        async def shutdown(self):
            state.shutdowns += 1

    class Bridge:
        def __init__(self, driver, pid, window_id, *, policy):
            self.pid, self.window_id = pid, window_id

        async def attach(self):
            state.attached.append((self.pid, self.window_id))

    state.driver = Driver()
    monkeypatch.setattr(browser, "configured_driver", lambda pid: state.driver)
    monkeypatch.setattr(browser, "BrowserBridge", Bridge)
    monkeypatch.setitem(sys.modules, "cua_driver", SimpleNamespace(ListWindowsInput=lambda **kw: SimpleNamespace(**kw)))
    return state


@pytest.mark.asyncio
async def test_linux_zero_window_recovers_exact_owned_profile(browser_world):
    state = browser_world
    driver, bridge = await browser.bind_footwork_chrome("http://127.0.0.1:8765/")
    assert driver is state.driver and bridge.window_id == 91
    assert state.attached == [(12, 91)]
    assert len(state.commands) == 1
    command = state.commands[0]
    assert command[0] == "/test/chrome"
    assert f"--user-data-dir={browser.PROFILE_DIR}" in command
    assert f"--remote-debugging-port={browser.PORT}" in command
    assert command[-2:] == ["--new-window", "http://127.0.0.1:8765/"]
    assert not state.children[0].terminated
    assert state.shutdowns == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["incarnation", "pid"])
async def test_recovery_refuses_replaced_browser(browser_world, change):
    state = browser_world
    original = state.on_spawn

    def replaced():
        original()
        setattr(state, change, 99)

    state.on_spawn = replaced
    with pytest.raises(RuntimeError, match="identity changed"):
        await browser.bind_footwork_chrome()
    assert state.attached == [] and state.shutdowns == 1
    assert all(not child.terminated for child in state.children)


@pytest.mark.asyncio
async def test_recovery_failed_spawn_keeps_persistent_browser(browser_world):
    state = browser_world
    state.spawn_error = OSError("synthetic spawn failure")
    with pytest.raises(OSError, match="spawn failure"):
        await browser.bind_footwork_chrome()
    assert state.pid == 12 and state.children == []
    assert state.attached == [] and state.shutdowns == 1


@pytest.mark.asyncio
async def test_recovery_early_helper_failure_is_not_success(browser_world):
    state = browser_world
    state.helper_status = 7
    with pytest.raises(RuntimeError, match="helper failed"):
        await browser.bind_footwork_chrome()
    assert state.pid == 12 and state.attached == [] and state.shutdowns == 1
    assert state.children[0].waited and not state.children[0].terminated


@pytest.mark.asyncio
async def test_recovery_missing_window_has_one_deadline(browser_world):
    import time

    state = browser_world
    state.on_spawn = lambda: None
    start = time.monotonic()
    with pytest.raises(TimeoutError):
        await browser.bind_footwork_chrome(startup_timeout_s=0.02)
    assert time.monotonic() - start < 1
    assert state.pid == 12 and state.attached == [] and state.shutdowns == 1
    assert len(state.commands) == 1
    assert not state.children[0].terminated


@pytest.mark.asyncio
async def test_recovery_cancellation_reaps_only_helper(browser_world):
    import asyncio

    state = browser_world
    state.helper_status = None
    task = asyncio.create_task(browser.bind_footwork_chrome())
    while not state.children:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert state.children[0].terminated and state.children[0].waited
    assert state.pid == 12 and state.attached == [] and state.shutdowns == 1


@pytest.mark.asyncio
async def test_new_browser_cancellation_reaps_owned_launch(browser_world):
    import asyncio

    state = browser_world
    state.pid = None
    state.helper_status = None
    state.on_spawn = lambda: setattr(state, "pid", 13)
    task = asyncio.create_task(browser.bind_footwork_chrome())
    while not state.children:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(state.children) == 1 and state.children[0].terminated and state.children[0].waited
    assert state.attached == [] and state.shutdowns == 0


def test_new_browser_early_exit_is_not_adopted(browser_world):
    state = browser_world
    state.pid = None
    state.helper_status = 0
    state.on_spawn = lambda: setattr(state, "pid", 13)
    with pytest.raises(RuntimeError, match="exited before"):
        browser.launch_chrome(settle_s=0)
    assert state.children[0].waited and not state.children[0].terminated


def test_new_browser_readiness_uses_monotonic_time(browser_world, monkeypatch):
    state = browser_world
    state.pid = None
    state.helper_status = None
    state.on_spawn = lambda: setattr(state, "pid", 13)
    monkeypatch.setattr(browser.time, "time", lambda: pytest.fail("wall clock used for readiness"))
    assert browser.launch_chrome(settle_s=0) == 13
    assert not state.children[0].terminated


@pytest.mark.asyncio
async def test_bind_refuses_unrelated_window(browser_world):
    state = browser_world
    state.on_spawn()
    state.windows[0].pid = 99
    with pytest.raises(RuntimeError, match="unqualified browser window"):
        await browser.bind_footwork_chrome()
    assert state.attached == [] and state.commands == [] and state.shutdowns == 1


@pytest.mark.asyncio
async def test_existing_window_binding_retains_incarnation_through_attach(browser_world, monkeypatch):
    state = browser_world
    state.on_spawn()

    async def replaced(self):
        state.incarnation += 1

    monkeypatch.setattr(browser.BrowserBridge, "attach", replaced)
    with pytest.raises(RuntimeError, match="identity changed"):
        await browser.bind_footwork_chrome()
    assert state.commands == [] and state.shutdowns == 1


@pytest.mark.asyncio
async def test_window_discovery_is_inside_startup_deadline(browser_world, monkeypatch):
    import asyncio

    state = browser_world

    async def never_ready(request):
        await asyncio.Event().wait()

    monkeypatch.setattr(state.driver, "list_windows", never_ready)
    with pytest.raises(TimeoutError):
        await browser.bind_footwork_chrome(startup_timeout_s=0.02)
    assert state.commands == [] and state.shutdowns == 1 and state.pid == 12


@pytest.mark.asyncio
async def test_mac_recovery_preserves_open_route(browser_world, monkeypatch):
    state = browser_world
    monkeypatch.setattr(browser, "sys", SimpleNamespace(platform="darwin"))
    await browser.bind_footwork_chrome()
    assert state.commands[0][:4] == ["open", "-na", "Google Chrome", "--args"]
    assert state.attached == [(12, 91)]


@pytest.mark.asyncio
async def test_recovery_waits_for_window_after_successful_helper_exit(browser_world, monkeypatch):
    state = browser_world
    make_window = state.on_spawn
    state.on_spawn = lambda: None
    calls = []

    async def delayed(request):
        calls.append(request.pid)
        if len(calls) == 3:
            make_window()
        return SimpleNamespace(windows=list(state.windows))

    monkeypatch.setattr(state.driver, "list_windows", delayed)
    await browser.bind_footwork_chrome()
    assert calls == [12, 12, 12]
    assert len(state.commands) == 1 and state.attached == [(12, 91)]


@pytest.mark.asyncio
async def test_expired_startup_never_spawns(browser_world):
    state = browser_world
    with pytest.raises(TimeoutError, match="deadline"):
        await browser.bind_footwork_chrome(startup_timeout_s=0)
    assert state.commands == [] and state.attached == []


def test_wrapper_path_cannot_qualify_different_live_executable(monkeypatch):
    import psutil

    monkeypatch.setattr(browser, "chrome_executable", lambda: "/usr/bin/chromium")
    monkeypatch.setattr(browser.os, "getuid", lambda: 42)
    candidate = process(12, ["/usr/bin/chromium", f"--user-data-dir={browser.PROFILE_DIR}",
                             f"--remote-debugging-port={browser.PORT}"], "/usr/lib/chromium/chromium")
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: iter([candidate]))
    assert browser.chrome_pid() is None


def test_cleanup_reaps_real_owned_child():
    import subprocess
    import sys

    child = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(30)"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        browser._stop_child(child)
        assert child.poll() is not None
        assert child.wait(timeout=0) == child.returncode
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=1)
