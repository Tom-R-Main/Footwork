"""Fixture ownership/readiness regression checks; no live applications started."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def fixture_module():
    path = Path(__file__).resolve().parents[1] / "scripts/capability_fixture.py"
    spec = importlib.util.spec_from_file_location("fixture_helper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
