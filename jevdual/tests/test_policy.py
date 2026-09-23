"""Policy tests against recorded/synthesized SystemOneResponse objects. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jevdual import prompts
from jevdual.menu import OPERATIONS, Candidate, Menu, MenuBudget
from jevdual.policy import JEV_MODEL, NON_TARGETED, Decision, JevPolicy, PolicyError, StepContext
from jevdual.trace import DecisionRecord
from typesafe_sdk import SystemOneResponse, TypeSafeRateLimitError

FIXTURES = Path(__file__).parent / "fixtures" / "jev_responses"


# ---- helpers ------------------------------------------------------------------------------


def cand(id: int, label: str, role: str = "a", ops=("click",), **kw) -> Candidate:
    return Candidate(id=id, label=label, role=role, operations=tuple(ops), **kw)


def small_menu() -> Menu:
    cands = (
        cand(1, "Home", href="/"),
        cand(2, "About", href="/about.html"),
        cand(3, "Search here", role="input", ops=("type", "enter"), input_type="search", value=""),
        cand(4, "Topic", role="select", ops=("select",), options=("Billing", "Support")),
    )
    by_op = {op: tuple(c for c in cands if op in c.operations) for op in OPERATIONS}
    by_op = {op: v for op, v in by_op.items() if v}
    return Menu(
        url="http://site/",
        title="Home",
        page_text="Welcome. Search or browse.",
        candidates=cands,
        by_operation=by_op,
    )


def big_menu(n: int = 300) -> Menu:
    cands = tuple(cand(i, f"Link {i}", href=f"/p/{i}") for i in range(1, n + 1))
    return Menu(
        url="http://site/list",
        title="List",
        page_text="Many links",
        candidates=cands,
        by_operation={"click": cands},
    )


def ctx(**kw) -> StepContext:
    base = {"task": "Open the About page", "requirements": ("About page is open",), "recent_actions": ()}
    base.update(kw)
    return StepContext(**base)


def load_response(name: str) -> SystemOneResponse:
    return SystemOneResponse.model_validate(json.loads((FIXTURES / f"{name}.json").read_text()))


def synth_response(
    questions, picks: dict[str, str], nouls: dict[str, float] | None = None, *, model=JEV_MODEL
) -> SystemOneResponse:
    """Well-formed answers for every question: chosen option gets 0.7, rest share 0.3."""
    answers: dict[str, dict] = {}
    for key, q in questions.items():
        if q.type == "noul":
            answers[key] = {"type": "noul", "noul": (nouls or {}).get(key, 0.05)}
            continue
        opts = list(q.criteria)
        chosen = picks.get(key, opts[0])
        rest = [o for o in opts if o != chosen]
        probs = {o: (0.3 / len(rest) if rest else 0.0) for o in rest}
        probs[chosen] = 1.0 if not rest else 0.7
        answers[key] = {
            "type": "choice",
            "choice": chosen,
            "confidence": 0.7 if rest else 1.0,
            "probabilities": probs,
        }
    return SystemOneResponse.model_validate(
        {"model": model, "usage": {"input_tokens": 1234, "output_tokens": 0}, "answers": answers}
    )


class FakeClient:
    def __init__(self, responses=None, factory=None):
        self.responses = list(responses or [])
        self.factory = factory
        self.calls: list[dict] = []

    async def system_one(self, state, questions, *, model=None, **kwargs):
        self.calls.append({"state": state, "questions": questions, "model": model, "kwargs": kwargs})
        if self.factory is not None:
            return self.factory(questions)
        if not self.responses:
            raise AssertionError("FakeClient has no response left")
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


# ---- request shape ------------------------------------------------------------------------


def test_request_shape_small_menu():
    policy = JevPolicy(FakeClient())
    req = policy.build_request(small_menu(), ctx())
    assert req.offered == ("click", "type", "select", "enter") + NON_TARGETED
    expected = {"operation", "click_target", "type_target", "select_target", "enter_target", *prompts.NOULS}
    assert set(req.questions) == expected
    op = req.questions["operation"]
    assert set(op.criteria) == set(req.offered)
    assert op.instructions["task"] == "Open the About page"
    click = req.questions["click_target"]
    assert set(click.criteria) == {"1", "2"}
    assert click.criteria["2"] == {
        "id": 2,
        "label": "About",
        "role": "a",
        "operations": ["click"],
        "href": "/about.html",
    }
    assert req.questions["select_target"].criteria["4"]["options"] == ["Billing", "Support"]
    assert req.state["page"]["url"] == "http://site/" and req.state["requirements"] == ["About page is open"]
    assert (
        "omitted_elements" not in req.state and "tabs" not in req.state and "stored_secrets" not in req.state
    )
    assert req.estimated_tokens > 0


def test_state_optional_fields():
    m = small_menu()
    m = Menu(
        **{
            **m.__dict__,
            "omitted": {"offscreen": 12},
            "tabs": ({"id": 1, "title": "a"}, {"id": 2, "title": "b"}),
        }
    )
    req = JevPolicy(FakeClient()).build_request(m, ctx(secrets_names=("x_password",)))
    assert req.state["omitted_elements"] == {"offscreen": 12}
    assert len(req.state["tabs"]) == 2 and req.state["stored_secrets"] == ["x_password"]


def test_offered_ops_only_for_present_candidates():
    m = big_menu(5)  # click only
    req = JevPolicy(FakeClient()).build_request(m, ctx())
    assert req.offered == ("click",) + NON_TARGETED
    assert "type_target" not in req.questions


# ---- decide: one call, consumption, alternates ------------------------------------------------


async def test_decide_one_call_and_alternates():
    client = FakeClient([load_response("small_menu_click")])
    policy = JevPolicy(client)
    d = await policy.decide(small_menu(), ctx())
    assert len(client.calls) == 1 and client.calls[0]["model"] == JEV_MODEL
    assert "retry" in client.calls[0]["kwargs"]
    assert d.operation == "click" and d.target == 2
    assert d.target_probabilities == {1: 0.15, 2: 0.85}
    assert d.alternates == (1,)
    assert d.nouls["goal_done"] == 0.05 and d.nouls["destructive"] == 0.02
    assert d.request_tokens == 1834 and d.model == JEV_MODEL and d.latency_ms >= 0
    assert not d.two_stage


async def test_decide_non_targeted_done():
    d = await JevPolicy(FakeClient([load_response("small_menu_done")])).decide(small_menu(), ctx())
    assert d.operation == "done" and d.target is None and d.alternates == () and d.target_probabilities == {}
    assert d.nouls["goal_done"] == 0.93


def test_alternates_ordering_by_probability():
    probs = {7: 0.5, 9: 0.3, 3: 0.2}
    d = Decision("click", 0.5, {"click": 1.0}, 7, 0.5, probs, (), {}, JEV_MODEL, None, 0.0)
    from jevdual.policy import _alternates

    assert _alternates(probs, 7) == (9, 3)
    assert d.targeted


# ---- validation and retry -----------------------------------------------------------------------


async def test_invalid_choice_retries_once_then_raises():
    bad = load_response("invalid_choice")
    client = FakeClient([bad, bad])
    with pytest.raises(PolicyError) as ei:
        await JevPolicy(client).decide(small_menu(), ctx())
    assert len(client.calls) == 2 and not ei.value.retryable
    assert "not in options" in str(ei.value)


async def test_invalid_then_valid_recovers():
    client = FakeClient([load_response("invalid_choice"), load_response("small_menu_click")])
    d = await JevPolicy(client).decide(small_menu(), ctx())
    assert d.target == 2 and len(client.calls) == 2


async def test_probability_sum_and_argmax_checks():
    good = json.loads((FIXTURES / "small_menu_click.json").read_text())
    bad_sum = json.loads(json.dumps(good))
    bad_sum["answers"]["click_target"]["probabilities"] = {"1": 0.5, "2": 0.9}
    bad_argmax = json.loads(json.dumps(good))
    bad_argmax["answers"]["click_target"]["probabilities"] = {"1": 0.85, "2": 0.15}
    for payload, needle in ((bad_sum, "sum to"), (bad_argmax, "argmax")):
        r = SystemOneResponse.model_validate(payload)
        with pytest.raises(PolicyError) as ei:
            await JevPolicy(FakeClient([r, r])).decide(small_menu(), ctx())
        assert needle in str(ei.value)


async def test_sdk_errors_are_wrapped():
    import httpx2

    err = TypeSafeRateLimitError(429, {"error": "slow down"}, httpx2.Headers({"retry-after": "1"}))
    with pytest.raises(PolicyError) as ei:
        await JevPolicy(FakeClient([err])).decide(small_menu(), ctx())
    assert ei.value.retryable


# ---- grouping over 255 ---------------------------------------------------------------------------


def test_grouping_over_cap_emits_group_and_speculative_heads():
    m = big_menu(300)
    req = JevPolicy(FakeClient(), budget=MenuBudget(group_size=40)).build_request(
        m, ctx(task="Open link 287")
    )
    assert "click_target" not in req.questions and "click_group" in req.questions
    assert set(req.questions["click_group"].criteria) == {str(i) for i in range(8)}
    assert all(f"click_target_g{i}" in req.questions for i in range(8))
    assert req.group_heads == {"click": True} and req.two_stage_ops == ()
    covered = [int(k) for i in range(8) for k in req.questions[f"click_target_g{i}"].criteria]
    assert sorted(covered) == list(range(1, 301))
    print(f"\n300-element menu estimated tokens: {req.estimated_tokens}")


async def test_grouped_decide_consumes_only_chosen_group():
    m = big_menu(300)
    policy = JevPolicy(
        FakeClient(
            factory=lambda qs: synth_response(
                qs, {"operation": "click", "click_group": "7", "click_target_g7": "287"}
            )
        )
    )
    d = await policy.decide(m, ctx(task="Open link 287"))
    assert d.operation == "click" and d.target == 287 and not d.two_stage
    assert d.group_confidence == 0.7 and d.target_confidence == pytest.approx(0.7 * 0.7)
    assert set(d.target_probabilities) == set(range(281, 301))


async def test_two_stage_when_budget_forces_it():
    m = big_menu(300)
    # Pick a budget that admits state + the group question but not state + any per-group element head.
    from jevdual.policy import _estimate_tokens, _question_tokens

    probe = JevPolicy(FakeClient(), budget=MenuBudget(group_size=40)).build_request(
        m, ctx(task="Open link 287")
    )
    cpt = MenuBudget().chars_per_token
    floor = _estimate_tokens(probe.state, cpt) + _question_tokens(probe.questions["click_group"], cpt)
    heads = max(
        _question_tokens(q, cpt) for k, q in probe.questions.items() if k.startswith("click_target_g")
    )
    assert floor < _estimate_tokens(probe.state, cpt) + heads
    tight = MenuBudget(group_size=40, state_tokens=floor + 5)
    seen_questions = []

    def factory(qs):
        seen_questions.append(set(qs))
        if "click_target" in qs:  # second stage
            return synth_response(qs, {"click_target": "287"})
        return synth_response(qs, {"operation": "click", "click_group": "7"})

    policy = JevPolicy(FakeClient(factory=factory), budget=tight)
    d = await policy.decide(m, ctx(task="Open link 287"))
    assert d.two_stage and d.target is None and d.pending_group == tuple(range(281, 301))
    assert not any(k.startswith("click_target_g") for k in seen_questions[0])
    d2 = await policy.decide_target(m, ctx(task="Open link 287"), "click", d.pending_group)
    assert d2.target == 287 and seen_questions[1] == {"click_target"}


def test_budget_overflow_raises_when_menu_too_large():
    m = big_menu(300)
    with pytest.raises(PolicyError) as ei:
        JevPolicy(FakeClient(), budget=MenuBudget(state_tokens=500)).build_request(m, ctx())
    assert "budget" in str(ei.value)


# ---- trace ------------------------------------------------------------------------------------------


async def test_to_trace_round_trip():
    d = await JevPolicy(FakeClient([load_response("small_menu_click")])).decide(small_menu(), ctx())
    rec = d.to_trace(omitted_elements=3)
    assert isinstance(rec, DecisionRecord)
    dumped = DecisionRecord.model_validate(rec.model_dump(mode="json"))
    assert dumped.operation.choice == "click" and dumped.target.choice == "2"
    assert dumped.target.probabilities == {"1": 0.15, "2": 0.85}
    assert dumped.nouls["stuck"] == 0.1 and dumped.omitted_elements == 3 and dumped.model == JEV_MODEL


def test_prompts_are_literal_and_versioned():
    assert prompts.PROMPTS_VERSION
    assert set(prompts.NOULS) == {
        "goal_done",
        "stuck",
        "destructive",
        "login_required",
        "bot_check",
        "needs_reasoning",
    }
    for spec in prompts.NOULS.values():
        assert spec["instructions"].endswith("?") and spec["true"] and spec["false"]
    assert set(prompts.OPERATION_CRITERIA) == set(OPERATIONS) | set(NON_TARGETED)


async def test_decide_shrinks_the_menu_when_jev_refuses_the_request_as_too_large():
    import httpx
    from jevdual.policy import shrink_menu
    from typesafe_sdk import TypeSafeAPIError

    class RefusingOnce:
        def __init__(self, good):
            self.good = good
            self.calls = []

        async def system_one(self, state, questions, **kwargs):
            self.calls.append(state)
            if len(self.calls) == 1:
                raise TypeSafeAPIError(
                    400,
                    {"detail": {"error_type": "max_tokens_exceeded"}},
                    httpx.Headers(),
                    endpoint="POST /v1/systemone",
                )
            return self.good

    m = small_menu()
    client = RefusingOnce(load_response("small_menu_click"))
    d = await JevPolicy(client).decide(m, ctx())
    assert d.operation == "click"
    assert len(client.calls) == 2
    assert (
        len(client.calls[1]["page"]["text"]) <= max(500, len(client.calls[0]["page"]["text"]) // 2)
        or len(m.page_text) <= 500
    )
    s2 = shrink_menu(shrink_menu(m, 1), 2)
    assert s2.omitted["shrunk_level"] == 2 and len(s2.candidates) <= max(1, len(m.candidates) // 2)
