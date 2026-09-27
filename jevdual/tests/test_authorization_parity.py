"""Package B (docs/notebook/2026-09-26-b-authorization-parity.md): a judgment that cannot answer
withholds the action on both surfaces; the same effect gets the same decision on every native route;
an operator's grant clears exactly the action it names."""

from __future__ import annotations

import asyncio
import math
from types import SimpleNamespace as NS

import pytest
from jevdual.agent import DualProcessAgent
from jevdual.arbiter import ArbiterPolicy
from jevdual.authorize import Authorizer, action_for
from jevdual.menu import Candidate, Menu

FLOOR = ArbiterPolicy().destructive_confirm


def _judge(result):
    async def judge(task, targets, *, url, title):
        if isinstance(result, Exception):
            raise result
        return result(targets) if callable(result) else result

    return judge


MALFORMED = {
    "raises": RuntimeError("synthetic unavailable judge"),
    "empty": [],
    "short": lambda targets: [0.1] * (len(targets) - 1),
    "nan": lambda targets: [math.nan] * len(targets),
    "text": lambda targets: ["high"] * len(targets),
}

# ---- B1, browser-use path


def _browser_agent(judge, targets=((1, "Continue", "form"), (2, "Back", "form"))):
    return NS(
        s1_policy=NS(verifier=NS(verifier=NS(judge_destructive=judge))),
        _click_targets=lambda actions: list(targets),
        browser_session=NS(_cached_browser_state_summary=NS(url="https://example.invalid/", title="form")),
        task="inspect the form",
        state=NS(n_steps=3),
        gate_policy=ArbiterPolicy(),
        gate_judgments=[],
    )


@pytest.mark.parametrize("case", sorted(MALFORMED))
def test_browser_judgment_that_cannot_answer_pauses(case):
    agent = _browser_agent(_judge(MALFORMED[case]))
    hit = asyncio.run(DualProcessAgent._destructive_judgment(agent, []))
    assert hit is not None, case
    label, reason, idx = hit
    assert "judgment unavailable" in reason and (label, idx) == ("Continue", 1)
    assert agent.gate_judgments[-1]["error"]


def test_browser_judgment_below_the_floor_still_allows():
    agent = _browser_agent(_judge(lambda targets: [0.05] * len(targets)))
    assert asyncio.run(DualProcessAgent._destructive_judgment(agent, [])) is None


def test_browser_enter_gets_the_same_judgment_as_a_click():
    """Secondary audit 2026-09-27: Enter was keyword-gated only; an innocuous submit label ("Continue")
    reached by Enter skipped the judgment a click on it gets."""
    from jevdual.agent import DualProcessAgent as A

    agent = _browser_agent(_judge(lambda targets: [0.95] * len(targets)), targets=())
    agent._active_element_label = lambda: asyncio.sleep(0, result="Card number | Continue")
    agent._enter_targets = lambda actions: A._enter_targets(agent, actions)
    enter = NS(model_dump=lambda exclude_unset=True: {"send_keys": {"keys": "Enter"}})
    hit = asyncio.run(DualProcessAgent._destructive_judgment(agent, [enter]))
    assert hit is not None and hit[0] == "Enter in Card number | Continue" and "p=0.95" in hit[1]
    # below the floor, Enter passes like a click would
    agent.s1_policy.verifier.verifier.judge_destructive = _judge(lambda targets: [0.05] * len(targets))
    assert asyncio.run(DualProcessAgent._destructive_judgment(agent, [enter])) is None


# ---- B1, native Authorizer


def _nm(*cands: Candidate) -> NS:
    return NS(
        menu=Menu(
            url="app://shop",
            title="Checkout",
            page_text="Review your order",
            candidates=cands,
            by_operation={},
        ),
        values={c.id: c.value for c in cands},
    )


SUBMIT = Candidate(id=1, label="Submit order", role="button", operations=("click",))
BACK = Candidate(id=2, label="Back", role="button", operations=("click",))


@pytest.mark.parametrize("case", sorted(MALFORMED))
def test_native_judgment_that_cannot_answer_pauses(case):
    nm = _nm(SUBMIT, BACK)
    auth = Authorizer(judge=_judge(MALFORMED[case]))
    reason = asyncio.run(auth.check(nm, action_for("click", nm, "s2", target=BACK), task="t"))
    assert reason is not None and "judgment unavailable" in reason, case


# ---- B2, the same effect on every native route


def _submit_judge(targets):
    return [0.9 if "submit" in t["label"].casefold() else 0.02 for t in targets]


def _routes(nm):
    return {
        "click": action_for("click", nm, "s2", target=SUBMIT),
        "menu": action_for("menu", nm, "s2", path=("Order", "Submit order")),
        "enter": action_for("enter", nm, "s2"),
        "hotkey return": action_for("hotkey", nm, "s2", keys=("return",)),
        "key return": action_for("key", nm, "s2", keys=("return",)),
    }


def test_every_route_to_a_judged_default_button_pauses():
    nm = _nm(SUBMIT, BACK)
    decisions = {
        name: asyncio.run(Authorizer(judge=_judge(_submit_judge)).check(nm, a, task="Review the order"))
        for name, a in _routes(nm).items()
    }
    assert all(decisions.values()), {k: v for k, v in decisions.items() if not v}


def test_authorizing_the_button_clears_every_route_to_it():
    nm = _nm(SUBMIT, BACK)
    for name, a in _routes(nm).items():
        auth = Authorizer(judge=_judge(_submit_judge), authorized_actions=("Submit order",))
        assert asyncio.run(auth.check(nm, a, task="Place the order")) is None, name


def test_a_key_on_a_window_of_harmless_buttons_does_not_pause():
    keys = [Candidate(id=i, label=str(i), role="button", operations=("click",)) for i in range(10)]
    nm = _nm(*keys)
    auth = Authorizer(judge=_judge(_submit_judge))
    assert asyncio.run(auth.check(nm, action_for("key", nm, "s2", keys=("5",)), task="t")) is None
    assert asyncio.run(auth.check(nm, action_for("enter", nm, "s2"), task="t")) is None


# ---- B3, a grant names one action


@pytest.mark.parametrize(
    ("grant", "label", "cleared"),
    [
        ("Delete", "Delete", True),
        ("Delete", "Delete account", False),
        ("Save", "Save", True),
        ("Save", "Don't Save", False),
        ("delete  ", "Delete", True),
        ("File > Move to Trash", "File > Move to Trash", True),
        ("Trash", "File > Move to Trash", False),
        ("menu:File > Move to Trash", "File > Move to Trash", True),
        ("click:File > Move to Trash", "File > Move to Trash", False),
    ],
)
def test_a_grant_clears_exactly_the_action_it_names(grant, label, cleared):
    route = "menu" if ">" in label else "click"
    assert Authorizer(authorized_actions=(grant,)).is_authorized(label, route=route) is cleared


def test_the_replace_grant_and_authorize_all_are_unchanged():
    assert Authorizer(authorized_actions=("replace",)).is_authorized("replace")
    assert Authorizer(authorize_all=True).is_authorized("Delete account")


def test_the_grant_a_pause_prints_clears_that_action():
    from jevdual.cli import _paused_label

    nm = _nm(SUBMIT, BACK)
    for name, a in _routes(nm).items():
        reason = asyncio.run(Authorizer(judge=_judge(_submit_judge)).check(nm, a, task="t"))
        grant = _paused_label(reason)
        assert grant == ("Order > Submit order" if name == "menu" else "Submit order"), (name, reason)
        again = Authorizer(judge=_judge(_submit_judge), authorized_actions=(grant,))
        assert asyncio.run(again.check(nm, a, task="t")) is None, (name, grant)
