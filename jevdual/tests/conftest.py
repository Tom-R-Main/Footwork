"""Suite-wide fixtures."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest


@pytest.fixture
def mac_native_contract(monkeypatch):
    """Opt into synthetic Cocoa/AX behavior without changing the runner's OS.

    Apply only to fixtures or tests that explicitly model a Mac. Real Linux
    route tests and unrelated process/filesystem code keep their host platform.
    """
    from jevdual import native, posture

    monkeypatch.setattr(native, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(posture, "sys", SimpleNamespace(platform="darwin"))


@pytest.fixture(autouse=True)
def _screen_unlocked(monkeypatch):
    """Tests never read the real login session: a locked screen (the machine idling during a long
    run) must not change what the suite asserts. The live tests read the real state."""
    if os.environ.get("FOOTWORK_LIVE") == "1":
        return
    from jevdual import posture

    monkeypatch.setattr(posture, "screen_locked", lambda: False)


@pytest.fixture(autouse=True)
def _native_accessibility_granted(monkeypatch):
    """Offline Driver doubles also replace the host permission boundary."""
    if os.environ.get("FOOTWORK_LIVE") == "1":
        return
    from jevdual import native

    monkeypatch.setattr(native, "accessibility_status", lambda: "granted")


@pytest.fixture(autouse=True)
def _isolated_coordination_registry(monkeypatch, tmp_path):
    """Offline ownership tests never reserve the user's real desktop registry."""
    if os.environ.get("FOOTWORK_LIVE") == "1":
        return
    from jevdual.coordination import Coordinator

    original = Coordinator.__init__

    def initialize(self, path=None):
        original(self, path if path is not None else tmp_path / "coordination.sqlite")

    monkeypatch.setattr(Coordinator, "__init__", initialize)
