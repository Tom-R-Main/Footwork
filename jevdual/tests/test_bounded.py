"""Package I: the bounded arm. System 1 finishes only a fixed action (a unique target, no composed
text, no authority needed) whose receipt comes back confirmed; after any mismatch System 2 owns every
step until one of its own steps is confirmed."""

from __future__ import annotations

import asyncio

import pytest
from jevdual.arbiter import Arbiter
from jevdual.policy import Decision

from tests import test_desktop as td
from tests.test_desktop import FakeDriver, FakeHook, SeqPolicy, _agent, _decision, _ids


@pytest.fixture
def snapshot():
    return td.json.loads(td.FIXTURE.read_text())


@pytest.fixture
def stub_sdk(monkeypatch):
    return td.stub_sdk.__wrapped__(monkeypatch)


class S2:
    """Clicks the queued labels in order; records the reason it was handed each step."""

    def __init__(self, ids, *labels):
        self.ids, self.labels, self.reasons = ids, list(labels), []

    async def step(self, agent, nm, reason, out):
        self.reasons.append(reason)
        await agent.execute(nm, "click", nm.menu.candidate(self.ids[self.labels.pop(0)]), None, out)


def _run(snapshot, policy, s2, **kw):
    kw.setdefault("arbiter", Arbiter.from_toml())
    kw.setdefault("verifier", FakeHook("accept", "ok"))
    return asyncio.run(
        _agent(kw.pop("driver", FakeDriver(snapshot)), policy, s2=s2, bounded=True, **kw).run()
    )


def test_a_fixed_confirmed_action_stays_with_system_one(snapshot, stub_sdk):
    ids = _ids(snapshot)
    s2 = S2(ids)
    run = _run(snapshot, SeqPolicy(_decision("click", ids["6"]), _decision("done")), s2)
    assert run.status == "done" and run.s2_steps == 0 and s2.reasons == []


def test_an_unconfirmed_receipt_hands_recovery_to_system_two_until_it_confirms(snapshot, stub_sdk):
    ids = _ids(snapshot)
    # System 1's click comes back unverifiable: System 2 owns the next step even though System 1 would
    # decide it confidently; System 2's confirmed click hands control back; System 1 finishes
    driver = FakeDriver(snapshot, click_effect="UNVERIFIABLE")
    s2 = S2(ids, "7")

    async def confirm_s2_clicks(inp, _orig=driver.click):
        r = await _orig(inp)
        r.effect.name = "CONFIRMED" if s2.reasons else "UNVERIFIABLE"
        return r

    driver.click = confirm_s2_clicks
    policy = SeqPolicy(_decision("click", ids["6"]), _decision("done"))
    run = _run(snapshot, policy, s2, driver=driver)
    assert run.status == "done", run.reason
    assert s2.reasons == ["bounded: System 2 owns recovery until one of its steps is confirmed"]
    assert [o.system for o in run.steps] == ["s1", "s2", "s1"]


def test_a_target_without_a_clear_margin_is_not_fixed(snapshot, stub_sdk):
    ids = _ids(snapshot)
    close = Decision(
        "click",
        0.9,
        {"click": 0.9},
        ids["6"],
        0.5,
        {ids["6"]: 0.5, ids["9"]: 0.45},
        (ids["9"],),
        {"goal_done": 0.05, "stuck": 0.02, "destructive": 0.01, "needs_reasoning": 0.03},
        "jev",
        120,
        15.0,
    )
    s2 = S2(ids, "6")
    _run(snapshot, SeqPolicy(close, _decision("done")), s2)
    assert s2.reasons and "target not unique" in s2.reasons[0]


def test_a_destructive_proposal_is_never_finished_by_system_one(snapshot, stub_sdk):
    ids = _ids(snapshot)
    s2 = S2(ids, "6")
    driver = FakeDriver(snapshot)
    # the arbiter's keyword rule pauses "Delete" before the bounded check: nothing is pressed
    run = _run(snapshot, SeqPolicy(_decision("click", ids["Delete"]), _decision("done")), s2, driver=driver)
    assert run.status == "paused" and not [c for c in driver.calls if c[0] == "click"]


def test_text_that_would_need_composing_goes_to_system_two(stub_sdk):
    from types import SimpleNamespace

    from jevdual.menu import Candidate, Menu

    field = Candidate(id=3, label="Email", role="textbox", operations=("type",), value="")
    nm = SimpleNamespace(
        menu=Menu(url="app://X", title="Form", page_text="Email", candidates=(field,), by_operation={}),
        values={},
    )
    agent = _agent(
        FakeDriver(td.json.loads(td.FIXTURE.read_text())),
        SeqPolicy(),
        task="Sign up for the newsletter",
        bounded=True,
    )
    typed = _decision("type", 3)
    why, text = asyncio.run(agent._bounded_check(nm, typed, field))
    assert why == "bounded: type would need composed text" and text is None
    agent.task = 'Sign up with email "grace@example.com"'  # the literal binds to the field it follows
    why, text = asyncio.run(agent._bounded_check(nm, typed, field))
    assert why is None and text == "grace@example.com"
    assert asyncio.run(agent._bounded_check(nm, _decision("scroll", 3), field))[0].startswith(
        "bounded: scroll"
    )
