"""The operator session end to end: real ``footwork`` commands against a simulated Mac.

On 2026-09-25 three bugs were found by driving and none by the suite (docs/plans/legible-harness.md,
"Driving it myself"): ``s1 --act`` crashed on a Decision attribute, an installed-but-not-running app
surfaced as a window-discovery error, and a click went to whatever held the chosen id after the window
changed. Each is a scenario here, run through ``jevdual.cli.main`` with only the Driver, the TypeSafe
client, System 1's policy and the verifier's models replaced. A bug found by driving becomes a
scenario first (the typesafe-computer-use rule: fix the loop, not the scenario).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import ClassVar

import pytest

cd = pytest.importorskip("cua_driver")

from jevdual import cli
from jevdual.policy import Decision

from tests.fixtures.native_world import World


class _Client:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


class _Verifier:
    """Accepts when the last word of every requirement is on the window; the models are not under test."""

    def __init__(self, client):
        pass

    async def judge_destructive(self, task, targets, *, url, title):
        return [0.05 for _ in targets]

    async def verify(self, task, requirements, menu, answer, *, answer_expected, trajectory):
        unmet = {r: (0.05 if r.split()[-1] in menu.page_text else 0.95) for r in requirements}
        ok = all(p < 0.5 for p in unmet.values())
        return SimpleNamespace(
            band="accept" if ok else "reject",
            complete=0.95 if ok else 0.1,
            reason="all requirements on the window" if ok else "a requirement is not on the window",
            unmet=unmet,
            unmet_effective=unmet,
            unsupported_claims=[],
        )


class _Policy:
    """System 1 proposes the next label from a script, by the id it holds on the menu it was shown."""

    script: ClassVar[list[str]] = []

    def __init__(self, client):
        pass

    async def decide(self, menu, ctx):
        label = _Policy.script.pop(0)
        target = next(c.id for c in menu.candidates if c.label == label)
        return Decision(
            operation="click",
            operation_confidence=0.97,
            operation_probabilities={"click": 0.97},
            target=target,
            target_confidence=0.96,
            target_probabilities={target: 0.96},
            alternates=(),
            nouls={},
            model="fake",
            request_tokens=None,
            latency_ms=1.0,
        )


@pytest.fixture
def world(monkeypatch):
    w = World()
    import jevdual.keys
    import jevdual.policy
    import jevdual.verify
    import typesafe_sdk

    monkeypatch.setattr(cd.CuaDriver, "create", staticmethod(w.create))
    monkeypatch.setattr(typesafe_sdk, "AsyncTypeSafeClient", _Client)
    monkeypatch.setattr(jevdual.keys, "load_keys", lambda *a, **k: {"TYPESAFE_API_KEY": "test"})
    monkeypatch.setattr(jevdual.verify, "Verifier", _Verifier)
    monkeypatch.setattr(jevdual.policy, "JevPolicy", _Policy)
    return w


@pytest.fixture
def fw(tmp_path, capsys):
    """Run one footwork command in the test session; returns (exit code, stdout, stderr)."""
    session = str(tmp_path / "session")

    def run(*argv: str):
        extra = ["--settle", "0"] if argv[0] in ("do", "s1") else []
        code = cli.main([*argv, "--session", session, *extra])
        out = capsys.readouterr()
        return code, out.out, out.err

    run.session = tmp_path / "session"  # type: ignore[attr-defined]
    return run


def _state(fw) -> dict:
    return json.loads((fw.session / "session.json").read_text())


def _id(out: str, label: str) -> int:
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("[") and f"'{label}'" in s:
            return int(s[1 : s.index("]")])
    raise AssertionError(f"{label!r} not in the observation")


def test_a_calculator_job_from_start_to_a_verified_done(world, fw):
    code, out, _ = fw(
        "start", "Compute 48 times 13", "--app", "Calculator", "--require", "The display shows 624"
    )
    assert code == 0 and "bound Calculator" in out
    for label in ("All Clear", "4", "8", "Multiply", "1", "3", "Equals"):
        # a number is an id, so digits are chosen by the id the last observation printed for them
        target = str(_id(out, label)) if label.isdigit() else label
        code, out, err = fw("do", "click", target, "--no-judge")
        assert code == 0, err
    assert world.display() == "624"
    code, out, _ = fw("done", "624")
    assert code == 0 and "accepted" in out
    st = _state(fw)
    assert st["status"] == "done"
    # every press after the first changed the window, so each earlier action has a confirmed receipt
    receipts = [m for m in st["memory"] if "->" in m and "click(" in m]
    assert len(receipts) == 7 and all(m.endswith("-> confirmed") for m in receipts[1:])


def test_s1_act_dispatches_the_proposal(world, fw):
    # 2026-09-25: `s1 --act` read decision.text, which Decision does not have, and crashed
    fw("start", "Compute 7", "--app", "Calculator")
    _Policy.script = ["7"]
    code, out, err = fw("s1", "--act")
    assert code == 0, err
    assert "System 1 proposes: click" in out and world.presses == ["7"]


def test_an_installed_app_that_is_not_running_is_named_not_a_window_error(world, fw):
    world.apps = [("Calculator", 0, False)]
    code, _, err = fw("start", "Compute 7", "--app", "Calculator")
    assert code == 2 and "installed but not running" in err


def test_a_changed_window_refuses_the_chosen_id_and_nothing_is_pressed(world, fw):
    # 2026-09-25: an overlay opened between look and do; the click went to what now held id 37
    _, out, _ = fw("start", "Compute 7", "--app", "Calculator")
    seven = _id(out, "7")
    world.relabels[seven] = "sin"  # the person switched the calculator's mode
    code, out, err = fw("do", "click", str(seven), "--no-judge")
    assert code == 4 and "it was '7'" in err and "Nothing dispatched" in err
    assert world.presses == []


def test_delete_pauses_until_authorized_and_a_press_that_changes_nothing_says_so(world, fw):
    fw("start", "Clear the last digit", "--app", "Calculator")
    code, out, _ = fw("do", "click", "Delete", "--no-judge")
    assert code == 3 and "paused before dispatch" in out and world.presses == []
    code, out, _ = fw("do", "click", "Delete", "--no-judge", "--authorize", "Delete")
    assert code == 0 and world.presses == ["Delete"]
    # the display was 0 and is still 0: the Driver confirmed delivery, the window did not change.
    # `do` reobserves and prints the receipt itself; a later `look` has no pending action left
    assert "suspected no-op" in out and "reported the press as delivered" in out
    assert _state(fw)["memory"][-1].endswith("click(Delete) -> suspected_noop")
    assert "receipt:" not in fw("look")[1]


def test_background_only_sends_no_hotkey(world, fw):
    fw("start", "Save", "--app", "Calculator")
    # a chord may press any button on screen, and Calculator's backspace is labelled "Delete"
    code, out, _ = fw("do", "hotkey", "cmd", "s")
    assert code == 3 and "on button 'Delete' reachable by" in out
    code, out, _ = fw("do", "hotkey", "cmd", "s", "--authorize", "Delete")
    assert code == 0 and "not sent" in out and "requires_foreground" in out
    assert world.tool_calls == [] and world.presses == []


def test_a_driver_refusal_is_reported_and_the_receipt_follows_the_window(world, fw):
    fw("start", "Compute 8", "--app", "Calculator")
    _, out, _ = fw("look")
    world.refuse.add("8")
    code, out, _ = fw("do", "click", str(_id(out, "8")), "--no-judge")
    assert code == 0 and "driver says refused" in out and world.presses == []
    assert "receipt: Receipt for click(8): refused" in out
    assert _state(fw)["memory"] == ["step 1: click(8) -> refused"]
