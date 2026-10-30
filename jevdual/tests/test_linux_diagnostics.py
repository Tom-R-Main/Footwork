"""Installed Linux prerequisites never substitute for a live desktop observation."""

from __future__ import annotations

import builtins
import json
import os
from types import SimpleNamespace

import pytest
from jevdual import agent_cli
from jevdual.capability import cli, setup


@pytest.fixture
def linux_packages(monkeypatch, tmp_path):
    monkeypatch.setattr(setup.sys, "platform", "linux")
    monkeypatch.setattr(setup.importlib.metadata, "requires", lambda name: ["cua-driver==0.38.0+footwork.d5373879"])
    monkeypatch.setattr(setup.importlib.metadata, "version", lambda name: "0.38.0+footwork.d5373879")
    monkeypatch.setattr(
        setup.importlib.metadata, "distribution",
        lambda name: SimpleNamespace(
            version="0.0.1" if name == "jevdual" else "0.38.0+footwork.d5373879",
            metadata={"Requires-Python": ">=3.11,<4.0"},
            locate_file=lambda value: tmp_path / "installed",
        ),
    )
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
        monkeypatch.delenv(name, raising=False)


def test_linux_session_environment_never_grants_access_or_leaks_values(linux_packages, monkeypatch):
    monkeypatch.setenv("DISPLAY", "private-display-value")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "private-bus-address")
    permissions = setup.permission_status()
    assert permissions["accessibility"] == "not_checked"
    assert permissions["screen_recording"] == "not_checked"
    assert permissions["session"] == {
        "x11_display_present": True, "dbus_session_present": True,
        "wayland_display_present": False, "connection": "not_checked",
    }
    serialized = json.dumps(permissions)
    assert "private-display-value" not in serialized and "private-bus-address" not in serialized


def test_installed_packages_are_separate_from_linux_runtime_qualification(linux_packages, monkeypatch):
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/example-not-a-live-bus")
    checked = setup.doctor()
    assert checked["supported"] is True
    assert checked["dependency_status"] == "met"
    assert checked["dependencies"]["cua-driver"]["compatible"] is True
    assert checked["runtime_qualification"] == "not_checked"
    assert checked["prerequisite_status"] == "blocked"
    assert checked["blockers"] == ["accessibility_not_checked"]
    assert "Mousepad" in checked["limitation"] and "Wayland" in checked["limitation"]
    assert "shared foreground" in checked["limitation"]


def test_linux_missing_x11_or_session_bus_remains_an_explicit_prerequisite(linux_packages, monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    checked = setup.doctor()
    assert set(checked["blockers"]) == {
        "accessibility_not_checked", "x11_display_not_configured", "session_bus_not_configured",
    }
    assert checked["permissions"]["session"]["wayland_display_present"] is True
    assert checked["dependency_status"] == "met"


def test_offline_linux_doctor_does_not_initialize_native_services(linux_packages, monkeypatch):
    original = builtins.__import__

    def no_native_import(name, *args, **kwargs):
        if name.startswith(("cua_driver", "jeepney", "jevdual.linux_ax")) or name in {"Quartz", "ApplicationServices"}:
            pytest.fail("offline doctor must not import native drivers or accessibility clients")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_native_import)
    monkeypatch.setattr(setup.ScopedBackend, "__init__", lambda *a, **k: pytest.fail("native backend startup"))
    assert setup.doctor()["runtime_qualification"] == "not_checked"


def test_linux_strict_doctor_refuses_unchecked_runtime_even_with_installed_packages(linux_packages, capsys):
    assert cli.main(["doctor", "--strict"]) == 1
    checked = json.loads(capsys.readouterr().out)
    assert checked["dependency_status"] == "met"
    assert "accessibility_not_checked" in checked["blockers"]
    assert cli.main(["doctor"]) == 0


def test_linux_scope_keeps_explicit_destination_and_platform_limitations(linux_packages, tmp_path):
    document = tmp_path / "explicit-target.txt"
    document.write_text("original\n")
    run = tmp_path / "job"
    result = setup.make_config(
        run, source_pid=os.getpid(), source_window=1, source_url="http://127.0.0.1:8000/",
        destination_pid=os.getpid(), destination_window=2, document=document,
    )
    scope = json.loads((run / "scope.json").read_text())
    assert scope["destination"]["document"] == str(document)
    assert "Mousepad" in result["limitation"]
    assert "TextEdit" not in result["limitation"]


def test_discovery_uses_host_route_labels_without_claiming_linux_readiness(linux_packages, monkeypatch):
    catalog = agent_cli.catalog()
    assert "Linux X11/AT-SPI" in catalog["surfaces"]["desktop"]["route"]
    assert "binding required" in catalog["surfaces"]["desktop"]["route"]
    assert "Mousepad" in catalog["capability"]["scope"]
    assert "unqualified" in catalog["capability"]["scope"]
    monkeypatch.setattr(setup.sys, "platform", "darwin")
    catalog = agent_cli.catalog()
    assert catalog["surfaces"]["desktop"]["route"] == "native macOS accessibility"
    assert catalog["capability"]["scope"] == "one configured browser-to-TextEdit job"
    monkeypatch.setattr(setup.sys, "platform", "freebsd")
    assert "unsupported" in agent_cli.catalog()["surfaces"]["desktop"]["route"]
    assert setup.permission_status()["accessibility"] == "unsupported"
