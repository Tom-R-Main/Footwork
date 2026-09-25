"""The coexistence suite's own judging (Q15): what counts as a pass, as the agent's fault, or as someone
at the machine. The live cases themselves are in tests/live."""

from __future__ import annotations

import pytest
from jevdual import coexist
from jevdual.coexist import CaseResult, Watch


def test_a_case_passes_only_with_every_check_and_no_error_or_contamination():
    r = CaseResult("C0")
    assert not r.passed  # no checks is not a pass
    r.check("a", True)
    r.check("b", True)
    assert r.passed
    r.check("c", False, got="x")
    assert not r.passed and r.details["c"] == {"got": "x"}
    ok = CaseResult("C0", checks={"a": True}, contaminated="someone")
    assert not ok.passed
    assert not CaseResult("C0", checks={"a": True}, error="boom").passed


@pytest.fixture
def machine(monkeypatch):
    state = {"pointer": (10.0, 10.0), "keys": 100, "front": 5}
    monkeypatch.setattr(coexist, "pointer", lambda: state["pointer"])
    monkeypatch.setattr(coexist, "keydown_count", lambda: state["keys"])
    monkeypatch.setattr(coexist, "frontmost_pid", lambda: state["front"])
    return state


def test_pointer_moved_outside_agent_steps_is_contamination(machine):
    w = Watch()
    machine["pointer"] = (200.0, 10.0)
    r = CaseResult("C0", checks={"a": True})
    w.close(r, posted_keys=0)
    assert r.contaminated and "pointer" in r.contaminated and not r.passed
    assert r.checks["pointer_untouched_by_agent"] is True


def test_pointer_moved_inside_an_agent_step_is_the_agents_failure(machine):
    w = Watch()
    machine["pointer"] = (200.0, 10.0)
    r = CaseResult("C0", checks={"a": True})
    r.details["agent_pointer_moves"] = [{"step": "scroll", "from": (10, 10), "to": (200, 10)}]
    w.close(r, posted_keys=0)
    assert r.contaminated is None and r.checks["pointer_untouched_by_agent"] is False and not r.passed


def test_unexplained_key_downs_are_contamination(machine):
    w = Watch()
    machine["keys"] = 100 + 12 + 1 + 3  # the person's 12, the agent's 1, and 3 nobody sent
    r = CaseResult("C0", checks={"a": True})
    w.close(r, posted_keys=12, agent_keys=1)
    assert r.contaminated and "3 key-downs" in r.contaminated


def test_front_changes_are_recorded(machine):
    import time

    w = Watch()
    time.sleep(0.08)
    machine["front"] = 9
    time.sleep(0.08)
    r = CaseResult("C0", checks={"a": True})
    w.close(r, posted_keys=0)
    assert w.front_pids() == {5, 9}
