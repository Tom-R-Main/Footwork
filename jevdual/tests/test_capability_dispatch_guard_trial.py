"""Actual observed geometry is allowed to lag; it is never inferred from a move."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def trial(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "dispatch_guard_geometry", scripts / "capability_dispatch_guard_trial.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def clock(trial, monkeypatch):
    state = {"now": 0.0, "sleeps": []}
    monkeypatch.setattr(trial.time, "monotonic", lambda: state["now"])

    def sleep(duration):
        state["sleeps"].append(duration)
        state["now"] += duration

    monkeypatch.setattr(trial.time, "sleep", sleep)
    return state


def test_delayed_field_geometry_requires_an_actual_changed_observation(trial, clock):
    before = [152, 105, 656, 384]
    actual_after = [172, 105, 656, 384]
    frames = iter([before, before, actual_after])
    assert trial._wait_for_geometry(lambda: next(frames), before, timeout_s=0.1) == actual_after
    assert clock["sleeps"] and clock["now"] < 0.1


def test_unchanged_field_geometry_remains_invalid_at_bounded_deadline(trial, clock):
    before = [152, 105, 656, 384]
    with pytest.raises(trial.OracleError, match="actual field geometry"):
        trial._wait_for_geometry(lambda: before, before, timeout_s=0.1)
    assert clock["now"] == pytest.approx(0.1)
    assert all(0 < delay <= 0.025 for delay in clock["sleeps"])


def test_absent_geometry_is_not_inferred_from_the_requested_window_offset(trial, clock):
    before = [152, 105, 656, 384]
    with pytest.raises(trial.OracleError):
        trial._wait_for_geometry(lambda: None, before, timeout_s=0.05)
    assert clock["now"] == pytest.approx(0.05)


def test_changed_geometry_returned_after_deadline_is_not_qualified(trial, clock):
    before = [152, 105, 656, 384]

    def late_read():
        clock["now"] += 0.2
        return [172, 105, 656, 384]

    with pytest.raises(trial.OracleError, match="before deadline"):
        trial._wait_for_geometry(late_read, before, timeout_s=0.1)
    assert not clock["sleeps"]
