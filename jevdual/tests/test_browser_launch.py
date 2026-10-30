"""Browser ownership must survive platform discovery without widening attachment."""

import asyncio
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
def recovery(monkeypatch):
    closed, killed, spawned = [], [], []

    class Driver:
        def __init__(self):
            self.windows = []

        async def list_windows(self, _):
            return SimpleNamespace(windows=self.windows)

        async def shutdown(self):
            closed.append(True)

    class Process:
        pid = 99
        status = None

        def poll(self):
            return self.status

        def wait(self, **_):
            self.status = 0
            return 0

    driver, helper = Driver(), Process()
    monkeypatch.setattr(browser, 'sys', SimpleNamespace(platform='linux'))
    monkeypatch.setattr(browser, '_begin_chrome', lambda *_: (42, None))
    monkeypatch.setattr(browser, '_incarnation', lambda pid: 1.0)
    monkeypatch.setattr(browser, '_recovery_flags', lambda pid, incarnation: [])
    monkeypatch.setattr(browser, 'chrome_pid', lambda: 42)
    monkeypatch.setattr(browser, 'chrome_executable', lambda: '/qualified/chromium')
    monkeypatch.setattr(browser, 'configured_driver', lambda pid: driver)
    monkeypatch.setattr(browser.os, 'killpg', lambda pid, sig: killed.append(pid))

    def spawn(args, **_):
        spawned.append(args)
        return helper

    async def attach(self):
        self.target_id, self.tab_id = 'target', 'tab'

    monkeypatch.setattr(browser.subprocess, 'Popen', spawn)
    monkeypatch.setattr(browser.BrowserBridge, 'attach', attach)
    return SimpleNamespace(driver=driver, helper=helper, closed=closed, killed=killed, spawned=spawned)


@pytest.mark.asyncio
@pytest.mark.parametrize('new', [False, True])
async def test_cancelled_bind_reaps_only_new_owned_processes(monkeypatch, recovery, new):
    began = asyncio.Event()

    async def blocked(_):
        began.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(recovery.driver, 'list_windows', blocked)
    if new:
        recovery.helper.pid = 42
        monkeypatch.setattr(browser, '_begin_chrome', lambda *_: (42, recovery.helper))
    task = asyncio.create_task(browser.bind_footwork_chrome())
    await began.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert recovery.closed == [True]
    assert recovery.killed == ([42] if new else [])


@pytest.mark.asyncio
async def test_failed_window_helper_does_not_kill_persistent_browser(recovery):
    recovery.helper.status = 7
    with pytest.raises(RuntimeError, match='helper exited'):
        await browser.bind_footwork_chrome()
    assert recovery.closed == [True] and recovery.killed == []
    assert recovery.spawned[0][0] == '/qualified/chromium'
    assert f'--remote-debugging-port={browser.PORT}' in recovery.spawned[0]


@pytest.mark.asyncio
async def test_failed_spawn_closes_driver_without_killing_reused_browser(monkeypatch, recovery):
    def fail(*_, **__):
        raise FileNotFoundError('new-window executable unavailable')
    monkeypatch.setattr(browser.subprocess, 'Popen', fail)
    with pytest.raises(FileNotFoundError):
        await browser.bind_footwork_chrome()
    assert recovery.closed == [True] and recovery.killed == []


@pytest.mark.asyncio
async def test_wrong_window_pid_is_never_attached(recovery):
    recovery.driver.windows = [SimpleNamespace(pid=999)]
    with pytest.raises(RuntimeError, match='unrelated browser'):
        await browser.bind_footwork_chrome()
    assert recovery.closed == [True] and recovery.spawned == []


@pytest.mark.asyncio
async def test_changed_browser_incarnation_refuses_before_recovery(monkeypatch, recovery):
    values = iter([1.0, 2.0])
    monkeypatch.setattr(browser, '_incarnation', lambda pid: next(values))
    with pytest.raises(RuntimeError, match='changed identity'):
        await browser.bind_footwork_chrome()
    assert not recovery.spawned and not recovery.killed


@pytest.mark.asyncio
async def test_cancelled_recovery_helper_is_reaped_but_persistent_root_survives(monkeypatch, recovery):
    second = asyncio.Event()
    calls = 0

    async def windows(_):
        nonlocal calls
        calls += 1
        if calls > 1:
            second.set()
            await asyncio.Event().wait()
        return SimpleNamespace(windows=[])

    monkeypatch.setattr(recovery.driver, 'list_windows', windows)
    task = asyncio.create_task(browser.bind_footwork_chrome())
    await second.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert recovery.killed == [99] and recovery.closed == [True]


def test_early_browser_exit_has_no_discovered_process_cleanup_authority(monkeypatch, recovery):
    recovery.helper.status = 1
    monkeypatch.setattr(browser, '_begin_chrome', lambda *_: (99, recovery.helper))
    monkeypatch.setattr(browser, 'chrome_pid', lambda: None)
    with pytest.raises(RuntimeError, match='exited'):
        browser.launch_chrome(settle_s=0)
    assert recovery.killed == []


@pytest.mark.parametrize('flags,expected', [([], []), (['--disable-gpu'], []),
                                         (['--no-sandbox', '--other-untrusted-flag'], ['--no-sandbox'])])
def test_recovery_only_preserves_the_exact_roots_explicit_sandbox_mode(monkeypatch, flags, expected):
    from contextlib import nullcontext

    import psutil

    monkeypatch.setattr(browser, 'chrome_pid', lambda: 42)
    monkeypatch.setattr(psutil, 'Process', lambda pid: SimpleNamespace(
        oneshot=nullcontext, create_time=lambda: 1.0, cmdline=lambda: flags))
    assert browser._recovery_flags(42, 1.0) == expected
    with pytest.raises(RuntimeError, match='identity changed'):
        browser._recovery_flags(42, 2.0)
