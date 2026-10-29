"""Legacy URL rebinding cannot silently acquire durable execution authority."""

from __future__ import annotations

import asyncio
import copy
import json
import time
from types import SimpleNamespace

import pytest
from jevdual import browser_driver, cli, session
from jevdual.native import NativeBridge, NativeBridgeError
from jevdual.operator_evidence import EvidenceError, execution_record, validate_binding, validate_execution


def _no_browser(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("unqualified admission must not touch the browser")

    monkeypatch.setattr(browser_driver, "launch_chrome", forbidden)
    monkeypatch.setattr(browser_driver, "configured_driver", forbidden)
    monkeypatch.setattr(session, "_start_browser", forbidden)
    return calls


@pytest.mark.parametrize("url", ["http://127.0.0.1:8765/", "https://example.invalid/"])
def test_public_durable_browser_start_refuses_before_launch_or_navigation(tmp_path, monkeypatch, capsys, url):
    calls = _no_browser(monkeypatch)
    authority = tmp_path / "authority.db"
    directory = tmp_path / "session"
    result = cli.main(
        [
            "start",
            "Synthetic ticket",
            "--browser",
            "--url",
            url,
            "--authority",
            str(authority),
            "--session",
            str(directory),
        ]
    )
    assert result == 2
    refusal = json.loads(capsys.readouterr().err)
    assert refusal["code"] == "browser_authority_unqualified"
    assert refusal["dispatched"] is False
    assert "document_generation_bound_input" in refusal["missing_capabilities"]
    assert calls == []
    assert not authority.exists() and not directory.exists()


def test_existing_browser_metadata_cannot_enroll_by_adding_an_authority_path(tmp_path, monkeypatch, capsys):
    calls = _no_browser(monkeypatch)
    directory = tmp_path / "session"
    directory.mkdir()
    original = json.dumps({"mode": "browser", "authority": str(tmp_path / "authority.db")})
    metadata = directory / "session.json"
    metadata.write_text(original)
    result = cli.main(["look", "--session", str(directory)])
    assert result == 2
    assert json.loads(capsys.readouterr().err)["code"] == "browser_authority_unqualified"
    assert calls == [] and metadata.read_text() == original
    assert not (directory / "session.jsonl").exists()


def test_direct_bind_also_refuses_before_browser_driver_creation(tmp_path, monkeypatch):
    calls = _no_browser(monkeypatch)
    state = session.SessionState(
        dir=str(tmp_path),
        app="Chrome",
        pid=77,
        window_id=1,
        task="Synthetic ticket",
        mode="browser",
        authority=str(tmp_path / "authority.db"),
    )
    with pytest.raises(NativeBridgeError) as exc:
        asyncio.run(session.bind(state))
    assert exc.value.reason == "browser_authority_unqualified" and not exc.value.dispatched
    assert calls == []


def test_browser_claim_does_not_weaken_native_execution_binding():
    with pytest.raises(EvidenceError):
        validate_binding({"kind": "browser", "origin": "http://127.0.0.1:8765", "tab_id": "tab-1"})


SCOPE = {"url": "http://127.0.0.1:8765/form?run=1", "title": "nonce-123"}


def _snapshot(url=SCOPE["url"], *, title="Fixture nonce-123", bars=1, app="Google Chrome", sid="s1"):
    elements = [{"element_index": 0, "role": "AXWindow", "element_token": f"{sid}:0"}]
    for index in range(bars):
        elements.append(
            {
                "element_index": 1 + index * 10,
                "element_token": f"{sid}:{1 + index * 10}",
                "role": "AXTextField",
                "label": "Address and search bar",
                "value": url,
                "parent_index": 0,
            }
        )
    elements.append(
        {
            "element_index": 2,
            "element_token": f"{sid}:2",
            "role": "AXButton",
            "label": "Submit",
            "actions": ["AXPress"],
            "parent_index": 0,
        }
    )
    return {
        "snapshot_id": sid,
        "pid": 77,
        "window_id": 1,
        "app_name": app,
        "window_title": title,
        "elements_complete": True,
        "elements": elements,
        "tree_markdown": "",
    }


class NativeChromeDriver:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.inputs = []
        self.captures = []

    async def get_window_state(self, inp):
        self.captures.append(inp.include_screenshot)
        return self.snapshots.pop(0)

    async def click(self, inp):
        self.inputs.append("click")
        return SimpleNamespace(
            effect="confirmed", delivery=SimpleNamespace(mode="background", delivered_count=1)
        )

    async def call_tool(self, name, args):
        self.inputs.append(name)
        return SimpleNamespace(effect="confirmed")

    async def shutdown(self):
        pass


def _native(driver, monkeypatch):
    from jevdual.posture import ExecutionPolicy

    monkeypatch.setattr("jevdual.native.require_accessibility", lambda: None)
    monkeypatch.setattr(ExecutionPolicy, "locked", lambda _: False)
    return NativeBridge(driver, 77, 1, observation_guard=session._native_scope_guard(SCOPE))


@pytest.mark.parametrize("url", [SCOPE["url"], "127.0.0.1:8765/form?run=1"])
def test_native_chrome_scope_accepts_exact_url_and_only_scheme_omission(url, monkeypatch):
    driver = NativeChromeDriver([_snapshot(url), _snapshot(url, sid="s2")])
    bridge = _native(driver, monkeypatch)

    async def scenario():
        nm = await bridge.observe(screenshot_path="not-created.png")
        return await bridge.act(nm, "click", 2)

    assert asyncio.run(scenario()).effect == "confirmed"
    assert driver.inputs == ["click"]
    assert driver.captures == [False, False]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9999/form?run=1",
        "http://127.0.0.1:8765/other?run=1",
        "http://127.0.0.1:8765/form?run=2",
        "http://127.0.0.1:8765/form?run=1#changed",
        "https://127.0.0.1:8765/form?run=1",
        "https://example.invalid/form?run=1",
    ],
)
def test_native_internal_live_check_refuses_changed_scope_before_input(url, monkeypatch):
    driver = NativeChromeDriver([_snapshot(), _snapshot(url, sid="s2")])
    bridge = _native(driver, monkeypatch)

    async def scenario():
        nm = await bridge.observe()
        await bridge.act(nm, "click", 2)

    with pytest.raises(NativeBridgeError) as exc:
        asyncio.run(scenario())
    assert exc.value.reason == "native_scope_changed" and not exc.value.dispatched
    assert driver.inputs == [] and bridge.last is None


@pytest.mark.parametrize(
    "bars,url,title",
    [
        (0, SCOPE["url"], "nonce-123"),
        (2, SCOPE["url"], "nonce-123"),
        (1, None, "nonce-123"),
        (1, SCOPE["url"], "other-fixture"),
    ],
)
def test_native_scope_refuses_unavailable_ambiguous_or_wrong_fixture(bars, url, title, monkeypatch):
    driver = NativeChromeDriver([_snapshot(url, bars=bars, title=title)])
    with pytest.raises(NativeBridgeError):
        asyncio.run(_native(driver, monkeypatch).observe())
    assert driver.inputs == []


@pytest.mark.parametrize("operation", ["key", "hotkey", "menu"])
def test_native_non_element_actions_recheck_scope_before_input(operation, monkeypatch):
    driver = NativeChromeDriver([_snapshot(), _snapshot("http://127.0.0.1:9999/", sid="s2")])
    bridge = _native(driver, monkeypatch)

    async def scenario():
        nm = await bridge.observe()
        if operation == "key":
            await bridge.key(nm, "return")
        elif operation == "hotkey":
            await bridge.hotkey(nm, ["cmd", "s"])
        else:
            await bridge.menu(nm, ["File", "Save"])

    with pytest.raises(NativeBridgeError):
        asyncio.run(scenario())
    assert driver.inputs == []


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8765/",
        "http://localhost:8765/",
        "http://example.invalid/",
        "http://user:password@127.0.0.1:8765/",
        "http://127.0.0.1:8765/#fragment",
        "http://127.0.0.1:0/",
        " http://127.0.0.1:8765/",
        "http://127.0.\t0.1:8765/",
    ],
)
def test_native_scope_configuration_rejects_unsupported_urls(url):
    with pytest.raises(NativeBridgeError):
        session._native_scope_guard({"url": url, "title": "nonce"})


def test_capsule_projection_cannot_change_admitted_native_url_scope(tmp_path):
    from jevdual.session_operations import SessionOperations, native_resource

    binding = {"boot": "boot", "pid": 77, "start": "1", "window_id": 1}
    with SessionOperations(tmp_path / "authority.db") as ops:
        op = ops.admit(
            session_id="session",
            token="click-1",
            request={"words": ["click", "Submit"], "native_scope": SCOPE},
            resource=native_resource(binding),
            observation="obs1",
            target="2",
            move="click",
            authorization_basis="policy",
            projection={"binding": binding, "native_scope": SCOPE},
        )
        ops.start(op.id)
        capsule = execution_record(
            op,
            binding=binding,
            started_at=time.time(),
            ended_at=time.time(),
            producer_evidence={
                "name": "footwork.native",
                "version": 1,
                "delivery_basis": "sdk_delivery_count",
                "delivered_count": 1,
            },
            dispatched=True,
            effect="confirmed",
            phase="sent",
            projection={"native_scope": SCOPE},
        )
        changed = copy.deepcopy(capsule)
        changed["projection"]["native_scope"]["url"] = "http://127.0.0.1:9999/"
        with pytest.raises(EvidenceError, match="native scope"):
            validate_execution(changed, op, binding=binding)


@pytest.mark.parametrize("observed_app", ["Google Chrome", "Safari"])
def test_explicit_pid_does_not_choose_the_first_chrome_instance(tmp_path, monkeypatch, capsys, observed_app):
    import cua_driver
    from jevdual.posture import ExecutionPolicy

    snapshots = [_snapshot(app=observed_app), _snapshot(app=observed_app, sid="s2")]
    for snapshot in snapshots:
        snapshot.update(pid=222, window_id=333)
    driver = NativeChromeDriver(snapshots)
    selected = []

    async def forbidden_apps(inp):
        raise AssertionError("explicit PID must not enumerate another app instance")

    async def windows(inp):
        selected.append(inp.pid)
        assert inp.pid == 222
        return SimpleNamespace(
            windows=[
                SimpleNamespace(
                    window_id=333, title="Fixture nonce-123", bounds=SimpleNamespace(width=400, height=300)
                )
            ]
        )

    monkeypatch.setattr(driver, "list_apps", forbidden_apps, raising=False)
    monkeypatch.setattr(driver, "list_windows", windows, raising=False)
    monkeypatch.setattr(cua_driver.CuaDriver, "create", staticmethod(lambda *, embedded=False: driver))
    monkeypatch.setattr("jevdual.native.require_accessibility", lambda: None)
    monkeypatch.setattr(ExecutionPolicy, "locked", lambda _: False)
    monkeypatch.setattr(
        "jevdual.session_operations.native_identity",
        lambda pid, window_id: {"boot": "boot", "pid": pid, "start": "start", "window_id": window_id},
    )
    directory = tmp_path / "session"
    result = cli.main(
        [
            "start",
            "Owned browser",
            "--app",
            "Google Chrome",
            "--pid",
            "222",
            "--window",
            "nonce-123",
            "--authority",
            str(tmp_path / "authority.db"),
            "--session",
            str(directory),
        ]
    )
    output = capsys.readouterr()
    assert selected == [222] and driver.inputs == []
    if observed_app == "Google Chrome":
        assert result == 0, (output.out, output.err)
        metadata = json.loads((directory / "session.json").read_text())
        assert metadata["pid"] == 222 and metadata["window_id"] == 333
        assert metadata["native_binding"]["pid"] == 222
    else:
        assert result != 0
        assert not (directory / "session.json").exists()


@pytest.mark.parametrize("pid", ["0", "-1"])
def test_invalid_explicit_pid_refuses_before_native_driver_creation(pid, tmp_path, monkeypatch, capsys):
    import cua_driver

    def forbidden(**kwargs):
        raise AssertionError("invalid PID must not create a driver")

    monkeypatch.setattr(cua_driver.CuaDriver, "create", staticmethod(forbidden))
    result = cli.main(["start", "Owned app", "--pid", pid, "--session", str(tmp_path / "session")])
    assert result == 2
    assert "positive native process ID" in capsys.readouterr().err


def test_missing_explicit_pid_window_does_not_fall_back(tmp_path, monkeypatch, capsys):
    import cua_driver

    class Driver:
        async def list_windows(self, inp):
            assert inp.pid == 222
            return SimpleNamespace(windows=[])

        async def shutdown(self):
            pass

    monkeypatch.setattr(cua_driver.CuaDriver, "create", staticmethod(lambda *, embedded=False: Driver()))
    monkeypatch.setattr("jevdual.native.require_accessibility", lambda: None)
    result = cli.main(
        [
            "start",
            "Owned app",
            "--app",
            "Google Chrome",
            "--pid",
            "222",
            "--window",
            "nonce-123",
            "--session",
            str(tmp_path / "session"),
        ]
    )
    assert result == 2
    assert "pid 222 has no on-screen window" in capsys.readouterr().err
    assert not (tmp_path / "session" / "session.json").exists()


@pytest.mark.parametrize("changed", [False, True])
def test_native_key_foreground_fallback_rechecks_scope_after_background_refusal(changed, monkeypatch):
    from jevdual.native import AMBIGUITY

    third = _snapshot("http://127.0.0.1:9999/" if changed else SCOPE["url"], sid="s3")
    driver = NativeChromeDriver([_snapshot(), _snapshot(sid="s2"), third])
    calls, inputs = [], []

    async def key_tool(name, args_json):
        arguments = json.loads(args_json)
        calls.append(arguments["delivery_mode"])
        if arguments["delivery_mode"] == "background":
            return SimpleNamespace(
                action=SimpleNamespace(
                    effect="REFUSED", delivery=SimpleNamespace(mode="BACKGROUND", delivered_count=0)
                ),
                is_error=True,
                text=f"Background input refused ({AMBIGUITY})",
                error_code=AMBIGUITY,
            )
        inputs.append("foreground-key")
        return SimpleNamespace(
            effect="CONFIRMED", delivery=SimpleNamespace(mode="FOREGROUND", delivered_count=1)
        )

    monkeypatch.setattr(driver, "call_tool", key_tool)
    bridge = _native(driver, monkeypatch)
    bridge.policy = SimpleNamespace(
        locked=lambda: False,
        permits=lambda *args, **kwargs: None,
        before_foreground=dict,
        after_foreground=lambda before: {"restored": True},
        _activity=lambda: SimpleNamespace(frontmost_pid=lambda: 0),
    )

    async def scenario():
        nm = await bridge.observe()
        return await bridge.key(nm, "return")

    result = asyncio.run(scenario())
    if changed:
        assert result.dispatched is False and result.error_code == "native_scope_changed"
        assert calls == ["background"] and inputs == []
    else:
        assert result.dispatched and result.delivered_count == 1
        assert calls == ["background", "foreground"] and inputs == ["foreground-key"]
