"""Fixture ownership/readiness regression checks; no live applications started."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def simulated_identity_timeout_api(monkeypatch):
    # Scope tests use fake PIDs: never send an AX RPC to an unrelated real process.
    if sys.platform == "darwin":
        import ApplicationServices
    else:
        # Linux CI has no PyObjC framework. Model only this suite's explicit AX
        # seam; unconfigured queries/actions must fail instead of granting access.
        ApplicationServices = ModuleType("ApplicationServices")

        def unconfigured(*args):
            raise AssertionError("synthetic AX call requires an explicit test response")

        for name in (
            "AXUIElementCreateApplication",
            "AXUIElementCreateSystemWide",
            "AXUIElementSetMessagingTimeout",
            "AXUIElementCopyAttributeValue",
            "AXUIElementPerformAction",
            "AXIsProcessTrusted",
        ):
            setattr(ApplicationServices, name, unconfigured)
        monkeypatch.setitem(sys.modules, "ApplicationServices", ApplicationServices)

    monkeypatch.setattr(
        ApplicationServices, "AXUIElementCreateApplication", lambda pid: SimpleNamespace(pid=pid)
    )
    monkeypatch.setattr(
        ApplicationServices, "AXUIElementCreateSystemWide", lambda: SimpleNamespace(systemwide=True)
    )
    monkeypatch.setattr(ApplicationServices, "AXUIElementSetMessagingTimeout", lambda *args: 0)


def fixture_module():
    path = Path(__file__).resolve().parents[1] / "scripts/capability_fixture.py"
    spec = importlib.util.spec_from_file_location("fixture_helper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Every test-local timing override must stay off the shared stdlib module,
    # including asyncio's event-loop clock and any background library threads.
    module.time = SimpleNamespace(monotonic=time.monotonic, sleep=time.sleep)
    return module


@pytest.mark.skipif(
    sys.platform != "darwin", reason="macOS Accessibility readiness gate requires ApplicationServices"
)
def test_locked_fixture_refuses_before_creating_files(monkeypatch, tmp_path):
    import ApplicationServices
    from jevdual import posture

    monkeypatch.setattr(posture, "screen_locked", lambda: True)
    monkeypatch.setattr(ApplicationServices, "AXIsProcessTrusted", lambda: True)
    root = tmp_path / "must-not-exist"
    monkeypatch.setattr(sys, "argv", ["fixture", "--run-dir", str(root)])
    with pytest.raises(SystemExit) as failure:
        fixture_module().main()
    assert failure.value.code == 2
    assert not root.exists()


@pytest.mark.asyncio
async def test_readiness_waits_only_for_missing_window_and_keeps_exact_identity(monkeypatch, tmp_path):
    import cua_driver
    from jevdual import ax

    module = fixture_module()
    document = tmp_path / "owned.txt"
    attempts, stopped = [], []

    class Driver:
        async def list_apps(self, _):
            return SimpleNamespace(apps=[SimpleNamespace(name="TextEdit", pid=43)])

        async def list_windows(self, args):
            return SimpleNamespace(windows=[SimpleNamespace(window_id=7 if args.pid == 42 else 8)])

        async def shutdown(self):
            stopped.append(True)

    def path(pid, window):
        attempts.append((pid, window))
        if len(attempts) == 1:
            raise ax.AXError("window_missing", "opening")
        return str(document)

    monkeypatch.setattr(cua_driver.CuaDriver, "create", lambda: Driver())
    monkeypatch.setattr(ax, "document_path", path)
    result = await module.scope_for(42, "http://127.0.0.1:1", document)
    assert result["destination"] == {"pid": 43, "window_id": 8, "document": str(document)}
    assert attempts == [(43, 8), (43, 8)]
    assert stopped == [True]


@pytest.mark.asyncio
async def test_readiness_does_not_swallow_other_ax_errors(monkeypatch, tmp_path):
    import cua_driver
    from jevdual import ax

    module = fixture_module()
    stopped = []

    class Driver:
        async def list_apps(self, _):
            return SimpleNamespace(apps=[SimpleNamespace(name="TextEdit", pid=43)])

        async def list_windows(self, args):
            return SimpleNamespace(windows=[SimpleNamespace(window_id=7)])

        async def shutdown(self):
            stopped.append(True)

    def path(*_):
        raise ax.AXError("permission_denied", "no access")

    monkeypatch.setattr(cua_driver.CuaDriver, "create", lambda: Driver())
    monkeypatch.setattr(ax, "document_path", path)
    with pytest.raises(ax.AXError, match="no access"):
        await module.scope_for(42, "http://127.0.0.1:1", tmp_path / "owned.txt")
    assert stopped == [True]


def test_cleanup_uses_ax_without_apple_events(monkeypatch, tmp_path):
    module = fixture_module()
    assert not hasattr(module, "script"), "fixture cleanup still invokes osascript/Automation"
    assert callable(module.close_owned_document)


def test_browser_startup_has_separate_bounded_phase():
    module = fixture_module()
    assert module.BROWSER_STARTUP_SECONDS == 180
    assert module.IDENTITY_SECONDS == 30
    assert callable(module.wait_browser_ready)


def test_missing_owned_document_is_unknown_not_closed(monkeypatch, tmp_path):
    module = fixture_module()
    import ApplicationServices

    monkeypatch.setattr(ApplicationServices, "AXUIElementSetMessagingTimeout", lambda *args: 0)

    monkeypatch.setattr(ApplicationServices, "AXUIElementCreateApplication", lambda pid: {})
    monkeypatch.setattr(ApplicationServices, "AXUIElementCopyAttributeValue", lambda el, key, _: (0, []))
    result = module.close_owned_document(43, tmp_path / "owned.txt")
    assert result["status"] == "unknown"
    assert result["reason"] == "document_not_observed"


def ax_world(monkeypatch, tmp_path, *, edited=False):
    import ApplicationServices

    module = fixture_module()
    monkeypatch.setattr(ApplicationServices, "AXUIElementSetMessagingTimeout", lambda *args: 0)
    document = tmp_path / "owned.txt"
    window = {"AXDocument": document.as_uri(), "AXRole": "AXWindow"}
    other = {"AXDocument": (tmp_path / "elsewhere" / "owned.txt").as_uri(), "AXRole": "AXWindow"}
    app = {"AXWindows": [window, other]}
    close = {"AXRole": "AXButton"}
    window["AXCloseButton"] = close
    window["AXChildren"] = []
    sheet = {"AXRole": "AXSheet", "AXParent": window, "AXChildren": []}
    discard = {"AXRole": "AXButton", "AXTitle": "Don't Save", "AXChildren": []}
    sheet["AXChildren"].extend(
        [
            discard,
            {"AXRole": "AXButton", "AXTitle": "Save", "AXChildren": []},
            {"AXRole": "AXButton", "AXTitle": "Cancel", "AXChildren": []},
        ]
    )
    pressed = []

    def action(el, _):
        pressed.append(el)
        if el is close:
            if edited:
                window["AXSheets"] = [sheet]
            else:
                app["AXWindows"].remove(window)
        elif el is discard:
            app["AXWindows"].remove(window)
        return 0

    monkeypatch.setattr(ApplicationServices, "AXUIElementCreateApplication", lambda pid: app)
    monkeypatch.setattr(
        ApplicationServices,
        "AXUIElementCopyAttributeValue",
        lambda el, key, _: (0, el[key]) if key in el else (-25205, None),
    )
    monkeypatch.setattr(ApplicationServices, "AXUIElementPerformAction", action)
    return module, document, app, window, other, close, sheet, discard, pressed


def test_linux_without_native_framework_runs_exact_owned_cleanup(monkeypatch, tmp_path):
    original = sys.modules["ApplicationServices"]
    with monkeypatch.context() as linux:
        linux.setattr(sys, "platform", "linux")
        linux.setitem(sys.modules, "ApplicationServices", None)  # Native import must fail.
        simulated_identity_timeout_api.__wrapped__(linux)
        api = sys.modules["ApplicationServices"]
        assert isinstance(api, ModuleType)
        assert api is not original
        with pytest.raises(AssertionError, match="explicit test response"):
            api.AXIsProcessTrusted()
        with pytest.raises(AssertionError, match="explicit test response"):
            api.AXUIElementPerformAction({}, "AXPress")
        module, document, app, _window, other, close, _sheet, _discard, pressed = ax_world(linux, tmp_path)
        result = module.close_owned_document(43, document)
        assert result["status"] == "confirmed"
        assert pressed == [close]
        assert app["AXWindows"] == [other]
    assert sys.modules["ApplicationServices"] is original


@pytest.mark.parametrize("edited", [False, True])
def test_exact_owned_ax_window_closes_and_preserves_same_name(monkeypatch, tmp_path, edited):
    module, document, app, _window, other, close, _sheet, discard, pressed = ax_world(
        monkeypatch, tmp_path, edited=edited
    )
    result = module.close_owned_document(43, document)
    assert result["status"] == "confirmed"
    assert app["AXWindows"] == [other]
    assert pressed == ([close, discard] if edited else [close])


def test_duplicate_exact_document_refuses_any_action(monkeypatch, tmp_path):
    module, document, app, window, *_ = ax_world(monkeypatch, tmp_path)
    app["AXWindows"].append(dict(window))
    result = module.close_owned_document(43, document)
    assert result["reason"] == "document_ambiguous"
    assert result["status"] == "error"


def test_identity_changed_before_close_refuses(monkeypatch, tmp_path):
    module, document, _app, window, other, _close, _sheet, _discard, pressed = ax_world(monkeypatch, tmp_path)
    original = module.owned_window
    calls = []

    def changed(*args):
        calls.append(True)
        if len(calls) == 2:
            window["AXDocument"] = other["AXDocument"]
        return original(*args)

    monkeypatch.setattr(module, "owned_window", changed)
    assert module.close_owned_document(43, document)["reason"] == "document_identity_changed"
    assert pressed == []


def test_ax_windows_unreadable_after_press_is_not_absence(monkeypatch, tmp_path):
    import ApplicationServices

    module, document, _app, _window, _other, _close, _sheet, _discard, pressed = ax_world(
        monkeypatch, tmp_path
    )
    original = ApplicationServices.AXUIElementCopyAttributeValue

    def attribute(el, key, arg):
        if key == "AXWindows" and pressed:
            return -25211, None
        return original(el, key, arg)

    monkeypatch.setattr(ApplicationServices, "AXUIElementCopyAttributeValue", attribute)
    assert module.close_owned_document(43, document)["status"] == "error"


@pytest.mark.parametrize(
    "problem", ["unattached", "two_sheets", "two_buttons", "foreign_sheet", "failed_press"]
)
def test_discard_refuses_unbound_or_ambiguous_targets(monkeypatch, tmp_path, problem):
    import ApplicationServices

    module, document, app, window, other, _close, sheet, discard, pressed = ax_world(
        monkeypatch, tmp_path, edited=True
    )
    if problem == "unattached":
        sheet["AXParent"] = other
    elif problem == "two_sheets":
        window["AXSheets"] = [sheet, dict(sheet)]
    elif problem == "two_buttons":
        sheet["AXChildren"].append(dict(discard))
    elif problem == "foreign_sheet":
        window["AXSheets"] = [{"AXRole": "AXSheet", "AXParent": other, "AXChildren": [discard]}]
    else:
        monkeypatch.setattr(ApplicationServices, "AXUIElementPerformAction", lambda *args: -25211)
    # Preserve pre-existing malicious AXSheets across the mocked close action.
    if problem in ("two_sheets", "foreign_sheet"):
        original_sheets = window["AXSheets"]
        monkeypatch.setattr(
            ApplicationServices,
            "AXUIElementPerformAction",
            lambda el, _: pressed.append(el) or window.update(AXSheets=original_sheets) or 0,
        )
    result = module.close_owned_document(43, document)
    assert result["status"] == "error"
    assert discard not in pressed
    assert other in app["AXWindows"]


def test_changed_document_remaining_window_is_not_confirmed_disappearance(monkeypatch, tmp_path):
    import ApplicationServices

    module, document, _app, window, other, _close, _sheet, _discard, _pressed = ax_world(
        monkeypatch, tmp_path
    )
    monkeypatch.setattr(
        ApplicationServices,
        "AXUIElementPerformAction",
        lambda *args: window.update(AXDocument=other["AXDocument"]) or 0,
    )
    assert module.close_owned_document(43, document)["reason"] == "document_identity_changed"


def fake_clock(monkeypatch, module, *, step=1):
    ticks = iter(range(10000))
    monkeypatch.setattr(
        module, "time", SimpleNamespace(monotonic=lambda: next(ticks) * step, sleep=lambda _: None)
    )


def test_fake_clock_preserves_process_wide_time_functions(monkeypatch):
    real_monotonic, real_sleep = time.monotonic, time.sleep
    module = fixture_module()
    fake_clock(monkeypatch, module, step=2)
    assert time.monotonic is real_monotonic
    assert time.sleep is real_sleep
    assert module.time is not time
    assert [module.time.monotonic() for _ in range(3)] == [0, 2, 4]


def test_browser_readiness_waits_for_private_profile_endpoint(monkeypatch, tmp_path):
    module = fixture_module()
    fake_clock(monkeypatch, module)
    profile = tmp_path / "chrome-profile"
    profile.mkdir()
    attempts = []
    browser = SimpleNamespace(pid=42, poll=lambda: None)

    def delay(_):
        attempts.append(True)
        if len(attempts) == 40:  # Beyond the old thirty-second combined phase.
            (profile / "DevToolsActivePort").write_text("1234\n/devtools/browser/owned\n")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return b'{"webSocketDebuggerUrl":"ws://127.0.0.1:1234/devtools/browser/owned"}'

    urls = []
    monkeypatch.setattr(module.time, "sleep", delay)
    monkeypatch.setattr(
        module,
        "build_opener",
        lambda _: SimpleNamespace(open=lambda url, timeout: urls.append(url) or Response()),
    )
    assert module.wait_browser_ready(browser, profile)["pid"] == 42
    assert len(attempts) == 40
    assert urls == ["http://127.0.0.1:1234/json/version"]


@pytest.mark.parametrize("exited,reason", [(True, "browser_exited"), (False, "startup_timeout")])
def test_browser_readiness_classifies_failure(monkeypatch, tmp_path, exited, reason):
    module = fixture_module()
    fake_clock(monkeypatch, module, step=60)
    with pytest.raises(module.FixtureFailure) as failure:
        module.wait_browser_ready(SimpleNamespace(pid=42, poll=lambda: 1 if exited else None), tmp_path)
    assert failure.value.phase == "browser_startup"
    assert failure.value.reason == reason
    assert failure.value.exit_code == 3


@pytest.mark.asyncio
async def test_identity_stays_strict_after_startup(monkeypatch, tmp_path):
    import cua_driver
    from jevdual import ax

    module = fixture_module()
    elapsed = [0]
    monkeypatch.setattr(module.time, "monotonic", lambda: elapsed[0])

    async def advance(_):
        elapsed[0] += 10

    monkeypatch.setattr(module.asyncio, "sleep", advance)

    class Driver:
        async def list_apps(self, _):
            return SimpleNamespace(apps=[SimpleNamespace(name="TextEdit", pid=43)])

        async def list_windows(self, args):
            return SimpleNamespace(windows=[SimpleNamespace(window_id=7), SimpleNamespace(window_id=8)])

        async def shutdown(self):
            pass

    monkeypatch.setattr(cua_driver.CuaDriver, "create", lambda: Driver())
    monkeypatch.setattr(ax, "document_path", lambda *args: str(tmp_path / "owned.txt"))
    with pytest.raises(module.FixtureFailure) as failure:
        await module.scope_for(42, "http://127.0.0.1:1", tmp_path / "owned.txt")
    assert failure.value.reason == "windows_not_unique"
    assert failure.value.exit_code == 4


def test_cleanup_ax_refusal_still_stops_owned_browser_listener(monkeypatch, tmp_path):
    module = fixture_module()
    calls = []

    async def pid():
        return 43

    monkeypatch.setattr(module, "textedit_pid", pid)
    monkeypatch.setattr(
        module, "close_owned_document", lambda *args: {"status": "error", "reason": "refused"}
    )
    browser = SimpleNamespace(
        pid=42,
        returncode=0,
        poll=lambda: None,
        terminate=lambda: calls.append("terminate"),
        wait=lambda timeout: calls.append("wait"),
    )
    http = SimpleNamespace(
        shutdown=lambda: calls.append("shutdown"), server_close=lambda: calls.append("close")
    )
    alive = iter([True, False])
    thread = SimpleNamespace(is_alive=lambda: next(alive), join=lambda timeout: calls.append("join"))
    logfile = SimpleNamespace(close=lambda: calls.append("log_close"))
    result = module.cleanup(browser, http, thread, logfile, tmp_path / "owned.txt", opened=True, pid=43)
    assert result["document"]["status"] == "error"
    assert result["browser"]["status"] == result["listener"]["status"] == "confirmed"
    assert calls == ["terminate", "wait", "shutdown", "close", "join", "log_close"]


def test_attached_delete_sheet_without_save_context_refuses(monkeypatch, tmp_path):
    module, document, _app, _window, _other, close, sheet, discard, pressed = ax_world(
        monkeypatch, tmp_path, edited=True
    )
    discard["AXTitle"] = "Delete"
    sheet["AXChildren"] = [discard]
    result = module.close_owned_document(43, document)
    assert result["reason"] == "sheet_not_save_prompt"
    assert pressed == [close]


@pytest.mark.parametrize(
    "stage,expected_code",
    [("popen", 3), ("startup", 3), ("open", 5), ("identity", 4), ("identity_hang", 4), ("interrupt", 130)],
)
def test_setup_failures_always_stop_owned_resources(monkeypatch, tmp_path, stage, expected_code):
    import ApplicationServices
    from jevdual import posture

    module = fixture_module()
    monkeypatch.setattr(posture, "screen_locked", lambda: False)
    monkeypatch.setattr(ApplicationServices, "AXIsProcessTrusted", lambda: True)
    root = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["fixture", "--run-dir", str(root)])
    calls = []
    alive = [False]
    http = SimpleNamespace(
        server_port=1234,
        serve_forever=lambda: None,
        shutdown=lambda: calls.append("listener_shutdown"),
        server_close=lambda: calls.append("listener_close"),
    )

    class Thread:
        def __init__(self, **kwargs):
            pass

        def start(self):
            alive[0] = True

        def is_alive(self):
            return alive[0]

        def join(self, timeout):
            alive[0] = False

    monkeypatch.setattr(module, "ThreadingHTTPServer", lambda *args: http)
    monkeypatch.setattr(module.threading, "Thread", Thread)
    browser = SimpleNamespace(
        pid=42,
        returncode=0,
        poll=lambda: None,
        terminate=lambda: calls.append("browser_terminate"),
        wait=lambda timeout: calls.append("browser_wait"),
    )

    def popen(*args, **kwargs):
        if stage == "popen":
            raise OSError("launch refused")
        return browser

    def ready(*args):
        if stage == "startup":
            raise module.FixtureFailure("browser_startup", "startup_timeout", 3)
        if stage == "interrupt":
            raise KeyboardInterrupt()
        return {"status": "ready", "pid": 42, "port": 1234}

    def open_document(*args, **kwargs):
        if stage == "open":
            raise subprocess.CalledProcessError(1, "open")

    async def identity(*args):
        raise module.FixtureFailure("identity", "windows_not_unique", 4)

    async def pid():
        return 43

    monkeypatch.setattr(module.subprocess, "Popen", popen)
    monkeypatch.setattr(module.subprocess, "run", open_document)
    monkeypatch.setattr(module, "wait_browser_ready", ready)
    cancelled = []
    if stage == "identity_hang":
        import asyncio

        import cua_driver

        class Driver:
            async def list_apps(self, _):
                try:
                    await asyncio.Future()
                finally:
                    cancelled.append(True)

            async def shutdown(self):
                pass

        monkeypatch.setattr(cua_driver.CuaDriver, "create", lambda: Driver())
        monkeypatch.setattr(module, "IDENTITY_SECONDS", 0.02)
    else:
        monkeypatch.setattr(module, "scope_for", identity)
    monkeypatch.setattr(module, "textedit_pid", pid)
    monkeypatch.setattr(
        module, "close_owned_document", lambda *args: {"status": "unknown", "reason": "not_observed"}
    )
    with pytest.raises(SystemExit) as failure:
        module.main()
    assert failure.value.code == expected_code
    status = json.loads((root / "fixture-status.json").read_text())
    cleanup = json.loads((root / "cleanup.json").read_text())
    assert status["exit_code"] == expected_code
    if stage == "identity_hang":
        assert status["reason"] == "sdk_timeout"
        assert cancelled == [True]
    assert not (root / "scope.json").exists()
    assert "listener_shutdown" in calls and "listener_close" in calls
    assert cleanup["listener"]["status"] == "confirmed"
    if stage != "popen":
        assert "browser_terminate" in calls and "browser_wait" in calls
        assert cleanup["browser"]["status"] == "confirmed"


def test_changed_textedit_pid_refuses_document_cleanup_and_still_stops_browser(monkeypatch, tmp_path):
    module = fixture_module()
    touched = []

    async def pid():
        return 99

    monkeypatch.setattr(module, "textedit_pid", pid)
    monkeypatch.setattr(module, "close_owned_document", lambda *args: touched.append(True))
    browser = SimpleNamespace(pid=42, returncode=0, poll=lambda: 0, wait=lambda timeout: None)
    result = module.cleanup(browser, None, None, None, tmp_path / "owned.txt", opened=True, pid=43)
    assert result["document"]["reason"] == "textedit_process_changed"
    assert not touched
    assert result["browser"]["status"] == "confirmed"


def test_unresponsive_ax_has_rpc_timeout_and_no_confirmed_cleanup(monkeypatch, tmp_path):
    import ApplicationServices

    module, document, *_ = ax_world(monkeypatch, tmp_path)
    timeouts = []
    monkeypatch.setattr(
        ApplicationServices,
        "AXUIElementSetMessagingTimeout",
        lambda el, timeout: timeouts.append(timeout) or 0,
    )
    monkeypatch.setattr(ApplicationServices, "AXUIElementCopyAttributeValue", lambda *args: (-25204, None))
    result = module.close_owned_document(43, document)
    assert result["status"] == "error"
    assert timeouts and all(0 < timeout <= 1 for timeout in timeouts)


def test_save_sheet_traversal_deadline_stops_before_discard(monkeypatch, tmp_path):
    module, document, _app, _window, _other, _close, sheet, discard, pressed = ax_world(
        monkeypatch, tmp_path, edited=True
    )
    ticks = iter([0] + [0.1] * 22 + [11] * 100)
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))
    sheet["AXChildren"] += [{"AXRole": "AXGroup", "AXChildren": []} for _ in range(100)]
    result = module.close_owned_document(43, document)
    assert result["status"] == "error"
    assert result["reason"] == "cleanup_deadline"
    assert discard not in pressed


def test_main_automatic_ax_cleanup_with_automation_denied(monkeypatch, tmp_path):
    import ApplicationServices
    from jevdual import posture

    root = tmp_path / "run"
    module, _document, app, window, other, _close, _sheet, _discard, _pressed = ax_world(monkeypatch, root)
    window["AXDocument"] = (root / "run-invoice.txt").as_uri()
    monkeypatch.setattr(posture, "screen_locked", lambda: False)
    monkeypatch.setattr(ApplicationServices, "AXIsProcessTrusted", lambda: True)
    monkeypatch.setattr(sys, "argv", ["fixture", "--run-dir", str(root)])
    stopped = []
    alive = [False]
    http = SimpleNamespace(
        server_port=1234,
        serve_forever=lambda: None,
        shutdown=lambda: stopped.append("http_shutdown"),
        server_close=lambda: stopped.append("http_close"),
    )

    class Thread:
        def __init__(self, **kwargs):
            pass

        def start(self):
            alive[0] = True

        def is_alive(self):
            return alive[0]

        def join(self, timeout):
            alive[0] = False

    browser = SimpleNamespace(
        pid=42,
        returncode=0,
        poll=lambda: None,
        terminate=lambda: stopped.append("browser"),
        wait=lambda timeout: None,
    )

    def run(command, **kwargs):
        if command[0] == "osascript":
            raise subprocess.CalledProcessError(1, command)  # Automation explicitly denied.
        return SimpleNamespace(stdout="")

    async def scope(*args):
        return {"destination": {"pid": 43}, "source": {"pid": 42}}

    async def pid():
        return 43

    def stop(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(module, "ThreadingHTTPServer", lambda *args: http)
    monkeypatch.setattr(module.threading, "Thread", Thread)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: browser)
    monkeypatch.setattr(module.subprocess, "run", run)
    monkeypatch.setattr(module, "scope_for", scope)
    if hasattr(module, "wait_browser_ready"):
        monkeypatch.setattr(module, "wait_browser_ready", lambda *args: {"status": "ready"})
        monkeypatch.setattr(module, "textedit_pid", pid)
    monkeypatch.setattr(module.time, "sleep", stop)
    module.main()
    assert app["AXWindows"] == [other], "Automation-denied old cleanup leaves the owned AX window open"
    assert "browser" in stopped and "http_shutdown" in stopped
    assert json.loads((root / "cleanup.json").read_text())["document"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_indefinite_sdk_enumeration_is_cancelled_then_owned_cleanup_runs(monkeypatch, tmp_path):
    import asyncio

    import cua_driver

    module = fixture_module()
    monkeypatch.setattr(module, "IDENTITY_SECONDS", 0.02)
    cancelled, shutdown = [], []

    class Driver:
        async def list_apps(self, _):
            try:
                await asyncio.Future()
            finally:
                cancelled.append(True)

        async def shutdown(self):
            shutdown.append(True)

    monkeypatch.setattr(cua_driver.CuaDriver, "create", lambda: Driver())
    with pytest.raises(module.FixtureFailure) as failure:
        await module.scope_for(42, "http://127.0.0.1:1", tmp_path / "owned.txt")
    assert failure.value.reason == "sdk_timeout"
    assert failure.value.exit_code == 4
    assert cancelled == [True] and shutdown == [True]
    stopped = []
    browser = SimpleNamespace(
        pid=42,
        returncode=0,
        poll=lambda: None,
        terminate=lambda: stopped.append("browser"),
        wait=lambda timeout: None,
    )
    http = SimpleNamespace(server_close=lambda: stopped.append("listener"))
    result = module.cleanup(browser, http, None, None, tmp_path / "owned.txt", opened=False, pid=None)
    assert result["browser"]["status"] == result["listener"]["status"] == "confirmed"
    assert stopped == ["browser", "listener"]
    assert not [
        task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()
    ]


@pytest.mark.asyncio
async def test_indefinite_driver_shutdown_is_cancelled(monkeypatch):
    import asyncio

    module = fixture_module()
    cancelled = []

    class Driver:
        async def shutdown(self):
            try:
                await asyncio.Future()
            finally:
                cancelled.append(True)

    with pytest.raises(module.FixtureFailure) as failure:
        await module.shutdown_driver(Driver(), "document_cleanup", module.time.monotonic() + 0.02)
    assert failure.value.reason == "sdk_timeout"
    assert cancelled == [True]
    assert not [
        task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()
    ]


@pytest.mark.asyncio
async def test_scope_sets_process_timeout_and_rejects_late_document_identity(monkeypatch, tmp_path):
    import ApplicationServices
    import cua_driver
    from jevdual import ax

    module = fixture_module()
    document = tmp_path / "owned.txt"
    elapsed, timeouts = [0], []
    monkeypatch.setattr(module.time, "monotonic", lambda: elapsed[0])
    monkeypatch.setattr(
        ApplicationServices,
        "AXUIElementSetMessagingTimeout",
        lambda app, timeout: timeouts.append((app.systemwide, timeout)) or 0,
    )

    class Driver:
        async def list_apps(self, _):
            return SimpleNamespace(apps=[SimpleNamespace(name="TextEdit", pid=43)])

        async def list_windows(self, args):
            return SimpleNamespace(windows=[SimpleNamespace(window_id=7)])

        async def shutdown(self):
            pass

    def path(*args):
        elapsed[0] = 31  # Synchronous native call returned beyond identity deadline.
        return str(document)

    monkeypatch.setattr(cua_driver.CuaDriver, "create", lambda: Driver())
    monkeypatch.setattr(ax, "document_path", path)
    with pytest.raises(module.FixtureFailure) as failure:
        await module.scope_for(42, "http://127.0.0.1:1", document)
    assert failure.value.reason == "identity_deadline"
    assert failure.value.exit_code == 4
    assert timeouts == [(True, 1.0), (True, 0)]


def test_cleanup_snapshots_actual_file_bytes_before_and_after_close(monkeypatch, tmp_path):
    import hashlib

    module = fixture_module()
    document = tmp_path / "owned.txt"
    before, after = b"actual on disk\n", b"different actual bytes\n"
    document.write_bytes(before)

    async def pid():
        return 43

    def close(*args):
        document.write_bytes(after)
        return {"status": "confirmed", "reason": "window_disappeared"}

    monkeypatch.setattr(module, "textedit_pid", pid)
    monkeypatch.setattr(module, "close_owned_document", close)
    result = module.cleanup(None, None, None, None, document, opened=True, pid=43)["document"]
    assert result["file_before"] == {
        "status": "observed",
        "size_bytes": len(before),
        "sha256": hashlib.sha256(before).hexdigest(),
    }
    assert result["file_after"] == {
        "status": "observed",
        "size_bytes": len(after),
        "sha256": hashlib.sha256(after).hexdigest(),
    }
    assert "text" not in result["file_before"]


@pytest.mark.parametrize("kind", ["missing", "symlink", "large", "fifo"])
def test_snapshot_refuses_unowned_or_unbounded_file_types(tmp_path, kind):
    import os

    module = fixture_module()
    document = tmp_path / "owned.txt"
    if kind == "symlink":
        target = tmp_path / "other.txt"
        target.write_text("unrelated")
        document.symlink_to(target)
    elif kind == "large":
        document.write_bytes(b"x" * (module.MAX_DOCUMENT_BYTES + 1))
    elif kind == "fifo":
        os.mkfifo(document)
    snapshot = module.document_snapshot(document)
    assert snapshot["status"] != "observed"
    assert "sha256" not in snapshot
    if kind == "missing":
        assert snapshot["status"] == "absent"
    elif kind in ("large", "fifo"):
        assert snapshot["status"] == "refused"


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_second_sigint_is_ignored_only_during_cleanup_and_handler_restored(
    monkeypatch, tmp_path, cleanup_fails
):
    import signal

    import ApplicationServices
    from jevdual import posture

    module = fixture_module()
    previous = signal.getsignal(signal.SIGINT)
    monkeypatch.setattr(posture, "screen_locked", lambda: False)
    monkeypatch.setattr(ApplicationServices, "AXIsProcessTrusted", lambda: True)
    monkeypatch.setattr(sys, "argv", ["fixture", "--run-dir", str(tmp_path / "run")])
    # Fail before owning a server; only the final-cleanup SIGINT guard is exercised.
    monkeypatch.setattr(module, "ThreadingHTTPServer", lambda *args: (_ for _ in ()).throw(OSError()))
    observed = []

    def cleanup(*args, **kwargs):
        observed.append(signal.getsignal(signal.SIGINT))
        signal.raise_signal(signal.SIGINT)  # Ignored: no second KeyboardInterrupt escapes.
        if cleanup_fails:
            raise RuntimeError("cleanup receipt fault")
        return {
            "document": {"status": "not_started"},
            "browser": {"status": "not_started"},
            "listener": {"status": "not_started"},
        }

    monkeypatch.setattr(module, "cleanup", cleanup)
    with pytest.raises(RuntimeError if cleanup_fails else SystemExit):
        module.main()
    assert observed == [signal.SIG_IGN]
    assert signal.getsignal(signal.SIGINT) == previous


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "identity_failure", "shutdown_failure", "setter_failure"])
async def test_identity_uses_global_ax_reference_and_resets_default_even_on_shutdown_failure(
    monkeypatch, tmp_path, outcome
):
    import ApplicationServices
    import cua_driver
    from jevdual import ax

    module = fixture_module()
    global_reference = object()
    calls = []
    document = tmp_path / "owned.txt"
    monkeypatch.setattr(ApplicationServices, "AXUIElementCreateSystemWide", lambda: global_reference)

    def timeout(element, seconds):
        assert element is global_reference  # An application-element timeout would not cover new references.
        calls.append(seconds)
        return -25202 if outcome == "setter_failure" and seconds else 0

    monkeypatch.setattr(ApplicationServices, "AXUIElementSetMessagingTimeout", timeout)

    class Driver:
        async def list_apps(self, _):
            return SimpleNamespace(apps=[SimpleNamespace(name="TextEdit", pid=43)])

        async def list_windows(self, args):
            return SimpleNamespace(windows=[SimpleNamespace(window_id=7)])

        async def shutdown(self):
            if outcome == "shutdown_failure":
                raise RuntimeError("SDK shutdown refused")

    def path(*args):
        if outcome == "identity_failure":
            raise ax.AXError("permission_denied", "AX lookup refused")
        return str(document)

    monkeypatch.setattr(cua_driver.CuaDriver, "create", lambda: Driver())
    monkeypatch.setattr(ax, "document_path", path)
    if outcome == "success":
        result = await module.scope_for(42, "http://127.0.0.1:1", document)
        assert result["destination"]["document"] == str(document)
    else:
        expected = (
            ax.AXError
            if outcome == "identity_failure"
            else RuntimeError
            if outcome == "shutdown_failure"
            else module.FixtureFailure
        )
        with pytest.raises(expected):
            await module.scope_for(42, "http://127.0.0.1:1", document)
    assert calls == [1.0, 0]


@pytest.mark.parametrize("stale_target", ["child", "window"])
def test_close_stale_observation_requires_fresh_readable_absence(monkeypatch, tmp_path, stale_target):
    import ApplicationServices

    module, document, app, window, other, close, _, _, pressed = ax_world(monkeypatch, tmp_path)
    child = {"AXRole": "AXGroup", "AXChildren": []}
    window["AXChildren"] = [child]
    original = ApplicationServices.AXUIElementCopyAttributeValue
    observations = []

    def press_close(element, _):
        pressed.append(element)
        return 0  # Closing is asynchronous; AX reference survives the press briefly.

    def attribute(element, key, arg):
        if key == "AXWindows":
            observations.append(list(app["AXWindows"]))
        stale = (
            (element is child and key == "AXRole")
            if stale_target == "child"
            else (element is window and key == "AXDocument")
        )
        if pressed and stale:
            app["AXWindows"].remove(window)
            return -25202, None
        return original(element, key, arg)

    monkeypatch.setattr(ApplicationServices, "AXUIElementPerformAction", press_close)
    monkeypatch.setattr(ApplicationServices, "AXUIElementCopyAttributeValue", attribute)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    result = module.close_owned_document(43, document)
    assert result["status"] == "confirmed", result
    assert result["reason"] == "window_disappeared"
    assert observations[-1] == [other]  # A new successful AXWindows read certifies absence.
    assert pressed == [close]  # Never press the stale reference again.


@pytest.mark.parametrize("fresh", ["persistent_invalid", "unreadable", "renamed", "reused"])
def test_close_stale_retry_refuses_unconfirmed_or_changed_identity(monkeypatch, tmp_path, fresh):
    import ApplicationServices

    module, document, app, window, other, close, _, _, pressed = ax_world(monkeypatch, tmp_path)
    child = {"AXRole": "AXGroup", "AXChildren": []}
    window["AXChildren"] = [child]
    original = ApplicationServices.AXUIElementCopyAttributeValue
    stale, invalid_reads, elapsed = [False], [0], [0]

    def clock():
        value = elapsed[0]
        elapsed[0] += 0.1
        return value

    monkeypatch.setattr(module.time, "monotonic", clock)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        ApplicationServices, "AXUIElementPerformAction", lambda el, _: pressed.append(el) or 0
    )

    def attribute(element, key, arg):
        if pressed and element is child and key == "AXRole":
            stale[0] = True
            invalid_reads[0] += 1
            if fresh == "renamed":
                window["AXDocument"] = other["AXDocument"]
            elif fresh == "reused":
                replacement = dict(window)
                replacement["AXCloseButton"] = {"AXRole": "AXButton", "different": True}
                app["AXWindows"] = [replacement, other]
            return -25202, None
        if stale[0] and fresh == "unreadable" and key == "AXWindows":
            return -25211, None
        return original(element, key, arg)

    monkeypatch.setattr(ApplicationServices, "AXUIElementCopyAttributeValue", attribute)
    result = module.close_owned_document(43, document)
    assert result["status"] != "confirmed"
    assert pressed == [close]
    assert other in app["AXWindows"]
    if fresh in ("renamed", "reused"):
        assert result["reason"] == "document_identity_changed"
    elif fresh == "unreadable":
        assert result["reason"] == "ax_attribute_refused:AXWindows:-25211"

    if fresh == "persistent_invalid":
        assert invalid_reads[0] > 1
        assert elapsed[0] < module.CLEANUP_SECONDS + 0.3


def test_invalid_element_before_close_never_retries_or_presses(monkeypatch, tmp_path):
    import ApplicationServices

    module, document, _, window, _, _, _, _, pressed = ax_world(monkeypatch, tmp_path)
    original = ApplicationServices.AXUIElementCopyAttributeValue
    invalid_reads = []

    def attribute(element, key, arg):
        if element is window and key == "AXDocument":
            invalid_reads.append(True)
            return -25202, None
        return original(element, key, arg)

    monkeypatch.setattr(ApplicationServices, "AXUIElementCopyAttributeValue", attribute)
    result = module.close_owned_document(43, document)
    assert result["status"] == "error"
    assert invalid_reads == [True] and not pressed


def test_invalid_axpress_is_not_observation_retry(monkeypatch, tmp_path):
    import ApplicationServices

    module, document, _, _, _, close, _, discard, pressed = ax_world(monkeypatch, tmp_path, edited=True)
    original = ApplicationServices.AXUIElementPerformAction

    def action(element, name):
        if element is discard:
            pressed.append(element)
            return -25202
        return original(element, name)

    monkeypatch.setattr(ApplicationServices, "AXUIElementPerformAction", action)
    result = module.close_owned_document(43, document)
    assert result["status"] == "error"
    assert result["reason"] == "ax_press_refused:-25202"
    assert pressed == [close, discard]
