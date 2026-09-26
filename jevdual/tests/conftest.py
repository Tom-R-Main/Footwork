"""Suite-wide fixtures."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _screen_unlocked(monkeypatch):
    """Tests never read the real login session: a locked screen (the machine idling during a long
    run) must not change what the suite asserts. The live tests read the real state."""
    if os.environ.get("FOOTWORK_LIVE") == "1":
        return
    from jevdual import posture

    monkeypatch.setattr(posture, "screen_locked", lambda: False)
