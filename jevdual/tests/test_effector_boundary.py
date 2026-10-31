"""CUA stays behind a lazy compatibility boundary without changing wire values."""

from __future__ import annotations

import ast
import asyncio
import builtins
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.effectors import EffectorUnavailable, browser_effector, cua, desktop_effector, require_available

ROOT = Path(__file__).resolve().parents[1]


def test_only_cua_adapter_imports_the_sdk():
    """Prevent a new caller from restoring the hard runtime import coupling."""
    source = ROOT / "python" / "jevdual"
    unexpected = []
    for path in source.rglob("*.py"):
        if path == source / "effectors" / "cua.py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = (
                [alias.name for alias in node.names] if isinstance(node, ast.Import)
                else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            )
            if any(name == "cua_driver" or name.startswith("cua_driver.") for name in names):
                unexpected.append(f"{path.relative_to(source)}:{node.lineno}")
    assert unexpected == []


def test_discovery_and_command_modules_do_not_load_optional_effectors():
    code = r'''
import contextlib, importlib, importlib.abc, importlib.util, io, json, sys
blocked = ("browser_use", "cdp_use", "cua_driver", "Quartz", "AppKit", "ApplicationServices", "jeepney", "mujoco")
class NoOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in blocked:
            raise ModuleNotFoundError("optional module blocked: " + fullname, name=fullname)
sys.meta_path.insert(0, NoOptional())
# Discovery can probe availability without importing. Model missing top-level
# packages there as well; raising from find_spec would model a broken finder.
find_spec = importlib.util.find_spec
importlib.util.find_spec = lambda name, *a, **kw: None if name.split(".", 1)[0] in blocked else find_spec(name, *a, **kw)
for name in ("cli", "agent_cli", "session", "native", "browser_driver", "linux_session", "linux_x11", "capability.backend", "capability.mcp_server", "effectors", "effectors.cua"):
    importlib.import_module("jevdual." + name)
from jevdual.cli import main
for command in ("catalog", "schema", "doctor"):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        status = main(["--json", command])
    assert status == 0, (command, status)
    assert isinstance(json.loads(out.getvalue()), dict), command
assert not any(name.split(".", 1)[0] in blocked for name in sys.modules)
print("discovery works with optional imports blocked")
'''
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "python"), "JEVDUAL_PURE_PY": "1"},
        cwd=ROOT, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "discovery works with optional imports blocked"


@pytest.mark.parametrize("kind", ["desktop", "browser"])
def test_missing_sdk_has_typed_no_send_error_before_factory_or_host(kind, monkeypatch):
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "cua_driver":
            raise ModuleNotFoundError("missing optional SDK", name=name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(EffectorUnavailable) as stopped:
        if kind == "desktop":
            desktop_effector()
        else:
            browser_effector(3, host_factory=lambda _: pytest.fail("host must not run"))
    assert stopped.value.kind == kind
    assert stopped.value.code == "effector_unavailable"
    assert stopped.value.distribution == "cua-driver"
    assert stopped.value.dispatched is False
    assert "matching full Footwork bundle" in stopped.value.install_hint
    assert "pip install" not in stopped.value.install_hint


@pytest.mark.parametrize("preflight", [False, True])
def test_broken_sdk_dependency_keeps_its_actual_error(monkeypatch, preflight):
    original = builtins.__import__
    failure = ModuleNotFoundError("missing native dependency", name="native_dependency")

    def broken(name, *args, **kwargs):
        if name == "cua_driver":
            raise failure
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken)
    with pytest.raises(ModuleNotFoundError) as stopped:
        if preflight:
            require_available("desktop")
        else:
            desktop_effector()
    assert stopped.value is failure


@pytest.mark.parametrize("helper,sdk_name", [
    (cua.list_apps_input, "ListAppsInput"),
    (cua.list_windows_input, "ListWindowsInput"),
    (cua.window_state_input, "GetWindowStateInput"),
    (cua.click_input, "ClickInput"),
    (cua.invoke_menu_input, "InvokeMenuInput"),
    (cua.verify_state_input, "VerifyStateInput"),
])
def test_compatibility_constructor_preserves_kwargs_and_original_record(helper, sdk_name, monkeypatch):
    fields = {"session": "fixture", "optional": None, "predicate": object()}
    record, seen = object(), []

    def constructor(**kwargs):
        seen.append(kwargs)
        return record

    monkeypatch.setitem(sys.modules, "cua_driver", SimpleNamespace(**{sdk_name: constructor}))
    assert helper(**fields) is record
    assert seen == [fields]
    assert seen[0]["predicate"] is fields["predicate"]


def test_target_position_and_mode_keep_sdk_values(monkeypatch):
    target, position, mode = object(), object(), object()
    calls = []

    def window(**kwargs):
        calls.append(kwargs)
        return target

    def element(**kwargs):
        calls.append(kwargs)
        return position

    monkeypatch.setitem(sys.modules, "cua_driver", SimpleNamespace(
        ActionTarget=SimpleNamespace(WINDOW=window),
        ClickPosition=SimpleNamespace(ELEMENT=element),
        InputDeliveryMode=SimpleNamespace(BACKGROUND=mode),
    ))
    assert cua.window_target(pid=1, window_id=2) is target
    assert cua.element_position(element_token="snapshot:3") is position
    assert cua.background_delivery() is mode
    assert calls == [{"pid": 1, "window_id": 2}, {"element_token": "snapshot:3"}]


@pytest.mark.asyncio
async def test_desktop_factory_retains_driver_and_awaitable_shutdown(monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()
    seen = []

    class Driver:
        async def shutdown(self):
            entered.set()
            await release.wait()
            return "original shutdown result"

    driver = Driver()

    def create(**kwargs):
        seen.append(kwargs)
        return driver

    monkeypatch.setitem(sys.modules, "cua_driver", SimpleNamespace(CuaDriver=SimpleNamespace(create=create)))
    selected = desktop_effector()
    assert selected is driver
    assert seen == [{"embedded": True}]
    task = asyncio.create_task(selected.shutdown())
    await entered.wait()
    assert not task.done()
    release.set()
    assert await task == "original shutdown result"


@pytest.mark.asyncio
async def test_factory_does_not_consume_shutdown_cancellation(monkeypatch):
    entered = asyncio.Event()

    class Driver:
        async def shutdown(self):
            entered.set()
            await asyncio.Event().wait()

    monkeypatch.setitem(sys.modules, "cua_driver", SimpleNamespace(
        CuaDriver=SimpleNamespace(create=lambda **_: Driver()),
    ))
    driver = desktop_effector()
    task = asyncio.create_task(driver.shutdown())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_browser_factory_preserves_event_loop_authorization_options_and_driver(monkeypatch):
    driver, host = object(), object()
    seen = []
    standard = object()

    def host_factory(pid):
        seen.append(("host", pid))
        return lambda: host

    def create(options, authorization):
        seen.append(("create", options, authorization))
        return driver

    monkeypatch.setitem(sys.modules, "cua_driver", SimpleNamespace(
        _native=SimpleNamespace(uniffi_set_event_loop=lambda loop: seen.append(("loop", loop))),
        CuaDriver=SimpleNamespace(create_configured_with_authorization_host=create),
        SessionPermissionMode=SimpleNamespace(STANDARD=standard),
        RuntimeAuthorizationOptions=lambda **kwargs: kwargs,
        ConfiguredDriverOptions=lambda **kwargs: kwargs,
    ))
    assert browser_effector(12, host_factory=host_factory) is driver
    assert seen[0] == ("loop", asyncio.get_running_loop())
    assert seen[1] == ("host", 12)
    assert seen[2] == ("create", {
        "claude_code_compatibility": False,
        "authorization": {
            "allowed_modes": [standard], "compatibility_mode": standard,
            "compatibility_capability_manifest_path": None,
            "compatibility_bounded_manifest_path": None,
            "unrestricted_acknowledged": False,
            "max_session_ttl_seconds": 8 * 3600, "max_idle_ttl_seconds": 1800,
        },
    }, host)


@pytest.mark.parametrize("browser", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_start_without_sdk_preserves_existing_session_and_never_launches(
    browser, existing, tmp_path, monkeypatch, capsys
):
    from jevdual import browser_driver, carry, cli, grants, native
    from jevdual.session import SessionState

    directory = tmp_path / "session"
    original = {}
    if existing:
        directory.mkdir()
        SessionState(dir=str(directory), app="fixture", pid=1, window_id=2, task="retained").save()
        for name in ("session.jsonl", carry.CARRIES, carry.SNAPSHOTS, grants.GRANTS):
            (directory / name).write_bytes(b'{"fixture": "retained"}\n')
        original = {p.name: p.read_bytes() for p in directory.iterdir()}
    original_import = builtins.__import__
    launches = []

    def missing(name, *args, **kwargs):
        if name == "cua_driver":
            raise ModuleNotFoundError("missing optional SDK", name=name)
        return original_import(name, *args, **kwargs)

    def launch(*args):
        launches.append(args)
        raise RuntimeError("browser launch must follow the optional-effector check")

    monkeypatch.setattr(builtins, "__import__", missing)
    monkeypatch.setattr(native, "require_accessibility", lambda: None)
    monkeypatch.setattr(browser_driver, "_begin_chrome", launch)
    args = ["--json", "start", "replacement task", "--session", str(directory)]
    if browser:
        args.append("--browser")
    status = cli.main(args)
    output = capsys.readouterr().out
    for name, before in original.items():
        assert (directory / name).exists(), f"missing effector removed {name}"
        # The normal error handler may append a stop record, retaining history.
        if name == "session.jsonl":
            assert (directory / name).read_bytes().startswith(before)
        else:
            assert (directory / name).read_bytes() == before
    if not existing:
        assert not directory.exists()
    assert launches == []
    assert status == cli.EXIT_STOPPED
    assert "effector_unavailable" in output


@pytest.mark.parametrize("kind", ["desktop", "browser"])
def test_availability_preflight_does_not_construct_a_driver(kind, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("availability checks must not initialize a native runtime")

    monkeypatch.setitem(sys.modules, "cua_driver", SimpleNamespace(
        CuaDriver=SimpleNamespace(create=forbidden, create_configured_with_authorization_host=forbidden),
        _native=SimpleNamespace(uniffi_set_event_loop=forbidden),
    ))
    require_available(kind)


@pytest.mark.parametrize("entry", [
    "browser_launch", "browser_authorization_host", "run_keys", "run_output",
    "coexist_idle", "coexist_temporary_directory", "linux_probe_phase",
])
def test_missing_sdk_refuses_constructor_entry_before_external_side_effects(entry, tmp_path, monkeypatch):
    from jevdual import browser_driver, cli, coexist, keys, linux_session

    original_import = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "cua_driver":
            raise ModuleNotFoundError("missing optional SDK", name=name)
        return original_import(name, *args, **kwargs)

    def forbidden(*args, **kwargs):
        pytest.fail(f"{entry} reached an external side effect before missing-effector refusal")

    monkeypatch.setattr(builtins, "__import__", missing)
    phases = []
    if entry == "browser_launch":
        monkeypatch.setattr(browser_driver, "_begin_chrome", forbidden)
        action = lambda: asyncio.run(browser_driver.bind_footwork_chrome())
    elif entry == "browser_authorization_host":
        monkeypatch.setattr(browser_driver, "chrome_executable", forbidden)
        action = lambda: browser_driver._host_class(1)
    elif entry in ("run_keys", "run_output"):
        monkeypatch.setattr(keys, "load_keys", forbidden if entry == "run_keys" else lambda: {"TYPESAFE_API_KEY": True})
        monkeypatch.setattr(cli, "_out_dir", forbidden)
        args = SimpleNamespace(out=str(tmp_path / "must-not-create"))
        action = lambda: asyncio.run(cli.cmd_run(args))
    elif entry in ("coexist_idle", "coexist_temporary_directory"):
        monkeypatch.setattr(coexist, "require_idle", forbidden if entry == "coexist_idle" else lambda *_: None)
        monkeypatch.setattr(coexist.tempfile, "mkdtemp", forbidden)
        action = lambda: asyncio.run(coexist.run_case("C1"))
    else:
        action = lambda: asyncio.run(linux_session._target_probe(1, tmp_path / "document", phases.append))
    with pytest.raises(EffectorUnavailable):
        action()
    assert not (tmp_path / "must-not-create").exists()
    if entry == "linux_probe_phase":
        assert phases == ["import"]
