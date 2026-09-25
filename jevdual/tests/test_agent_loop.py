"""End-to-end agent-loop tests with a scripted System 2 (tests/fixtures/mock_llm.py) on pages served
by pytest-httpserver. No model calls; a headless browser is launched per test."""

from __future__ import annotations

from typing import Any

import pytest
from browser_use import BrowserProfile
from jevdual.agent import DualProcessAgent

from tests.fixtures.mock_llm import create_mock_llm, done, judgement, step

pytestmark = [pytest.mark.browser, pytest.mark.timeout(180)]

PAGE = "<html><body><h1>Account</h1><p>Balance: $12.00</p><a href='/delete-account'>Delete account</a></body></html>"


class EscalatingPolicy:
    """S1 that always escalates, with a verifier that always rejects System 2's done."""

    secrets = None

    def __init__(self, band: str = "reject") -> None:
        self.band = band
        self.judged: list[Any] = []

        class _Verifier:
            async def judge_done(inner, agent: Any, menu: Any, answer: str | None = None) -> tuple[str, str]:
                self.judged.append(answer)
                return band, "scripted verifier"

        self.verifier = _Verifier()

    async def decide(self, agent: Any, state: Any) -> None:
        return None


async def _run(httpserver, llm, *, policy=None, authorized=False, max_steps=6, use_judge=False, **agent_kw):
    httpserver.expect_request("/").respond_with_data(PAGE, content_type="text/html")
    httpserver.expect_request("/delete-account").respond_with_data(
        "<html><body>Deleted</body></html>", content_type="text/html"
    )
    agent = DualProcessAgent(
        task="Open the account page and report the balance.",
        llm=llm,
        browser_profile=BrowserProfile(headless=True),
        s1_policy=policy,
        authorized_destructive=authorized,
        use_judge=use_judge,
        calculate_cost=False,
        **agent_kw,
    )
    try:
        await agent.browser_session.start()
        await agent.browser_session.navigate_to(httpserver.url_for("/"))
        history = await agent.run(max_steps=max_steps)
    finally:
        await agent.close()
    # URLs the agent actually visited, from the per-step state (the focused tab after done can read as about:blank)
    urls = tuple(u for u in history.urls() if u)
    return agent, history, urls


async def test_gate_pauses_an_unauthorized_navigation_to_a_destructive_url(httpserver):
    llm = create_mock_llm([step({"navigate": {"url": httpserver.url_for("/delete-account")}})])
    agent, history, urls = await _run(httpserver, llm)
    assert agent.paused_before_action is not None and agent.paused_before_action["keyword"] == "delete"
    assert not any("delete-account" in u for u in urls)
    assert history.is_done() and history.is_successful() is False
    assert "Paused before a destructive action" in (history.final_result() or "")


async def test_gate_lets_an_authorized_task_through(httpserver):
    llm = create_mock_llm(
        [step({"navigate": {"url": httpserver.url_for("/delete-account")}}), done("deleted")]
    )
    agent, history, urls = await _run(httpserver, llm, authorized=True)
    assert agent.paused_before_action is None
    assert any(u.endswith("/delete-account") for u in urls)
    assert history.is_successful() is True


async def test_s2_done_is_rejected_twice_then_marked_unverified(httpserver):
    policy = EscalatingPolicy("reject")
    llm = create_mock_llm([done("Balance is $99.00"), done("Balance is $99.00"), done("Balance is $99.00")])
    agent, history, _ = await _run(httpserver, llm, policy=policy)
    assert agent.s2_done_rejections == 3
    assert len(policy.judged) == 3
    assert (history.final_result() or "").startswith("UNVERIFIED: Balance is $99.00")
    assert history.is_successful() is False
    # the two rejected dones became one-second waits, so the run took three steps
    assert len(history.history) == 3


async def test_s2_done_rejection_uses_typed_feedback_when_given(httpserver):
    """Q11 guarded_legible: the refused done's message comes from the verdict, with the refusals left."""
    from jevdual.verify import Verdict

    verdict = Verdict(band="reject", complete=0.2, unmet={"Balance reported": 0.9}, claims=[], reason="x")
    policy = EscalatingPolicy("reject")
    policy.verifier.last = verdict
    calls: list[tuple[object, int]] = []

    def feedback(v, left):
        calls.append((v, left))
        return "Missing: Balance reported"

    llm = create_mock_llm([done("Balance is $99.00"), done("Balance is $99.00"), done("Balance is $99.00")])
    _agent, history, _ = await _run(httpserver, llm, policy=policy, rejection_feedback=feedback)
    assert calls == [(verdict, 1), (verdict, 0)]
    assert (history.final_result() or "").startswith("UNVERIFIED")


async def test_s2_done_accepted_by_the_verifier_stands(httpserver):
    policy = EscalatingPolicy("accept")
    llm = create_mock_llm([done("Balance: $12.00")])
    agent, history, _ = await _run(httpserver, llm, policy=policy)
    assert agent.s2_done_rejections == 0 and history.is_successful() is True
    assert history.final_result() == "Balance: $12.00"


async def test_upstream_judge_verdict_is_recorded_on_the_history(httpserver):
    llm = create_mock_llm([done("Balance: $12.00"), judgement(False, failure_reason="scripted no")])
    _agent, history, _ = await _run(httpserver, llm, use_judge=True)
    j = history.judgement()
    assert j is not None and j["verdict"] is False and j["failure_reason"] == "scripted no"
    assert history.is_successful() is True  # the judge never overrides the agent's self-report
    assert llm.calls[-1]["output_format"] == "JudgementResult"


def test_is_authorized_scope_on_the_agent():
    from types import SimpleNamespace

    a = SimpleNamespace(authorized_destructive=True, authorized_actions=("finish",))
    assert DualProcessAgent.is_authorized(a, "Finish order") and not DualProcessAgent.is_authorized(
        a, "Delete account"
    )
    a2 = SimpleNamespace(authorized_destructive=True, authorized_actions=())
    assert DualProcessAgent.is_authorized(a2, "Delete account")  # task-wide, the old behaviour
    a3 = SimpleNamespace(authorized_destructive=False, authorized_actions=("finish",))
    assert not DualProcessAgent.is_authorized(a3, "Finish")


async def test_evaluate_pauses_at_once(httpserver):
    """The recoverable refusal was measured and removed (results/q8-consent.md): evaluate pauses on first use."""
    llm = create_mock_llm(
        [step({"evaluate": {"code": "document.title"}}), step({"evaluate": {"code": "document.title"}})]
    )
    agent, history, _ = await _run(httpserver, llm, max_steps=6)
    assert agent.evaluate_refusals == 0
    assert agent.paused_before_action is not None and agent.paused_before_action["keyword"] == "evaluate"
    names = [
        n
        for h in history.history
        for a in (h.model_output.action if h.model_output else [])
        for n in a.model_dump(exclude_unset=True)
    ]
    assert names == ["done"]


NOOP_PAGE = (
    "<html><body><h1>Shop</h1><button id='add' type='button'>Add to cart</button>"
    "<a href='/cart'>Cart</a></body></html>"
)


async def test_receipt_names_a_click_that_changed_nothing_and_reaches_the_driver(httpserver):
    """Q12: a click on a button with no handler is a suspected no-op; in deliver mode the receipt is
    appended to the step's result (what the driver reads next) and the verifier's trajectory line; in
    record mode it is in ``agent.receipts`` only."""
    httpserver.expect_request("/shop").respond_with_data(NOOP_PAGE, content_type="text/html")
    httpserver.expect_request("/cart").respond_with_data(
        "<html><body><h1>Cart</h1></body></html>", content_type="text/html"
    )
    for mode in ("deliver", "record"):
        # browser-use numbers backend nodes, not visible controls: the button is index 8 on this page
        # (probed with a bare BrowserSession); the assertion on the interacted node guards the guess
        llm = create_mock_llm([step({"click": {"index": 8}}), done("stopped", success=False)])
        agent = DualProcessAgent(
            task="Add the item to the cart.",
            llm=llm,
            browser_profile=BrowserProfile(headless=True),
            calculate_cost=False,
            receipts=mode,
        )
        try:
            await agent.browser_session.start()
            await agent.browser_session.navigate_to(httpserver.url_for("/shop"))
            history = await agent.run(max_steps=3)
        finally:
            await agent.close()
        first = history.history[0]
        clicked = (first.state.interacted_element or [None])[0]
        assert clicked is not None and clicked.node_name.upper() == "BUTTON", clicked
        receipt = agent.receipts[1]
        assert receipt.effect == "suspected_noop", receipt
        assert receipt.actions[0].startswith("click(")
        memory = first.result[-1].long_term_memory or ""
        if mode == "deliver":
            assert "suspected no-op" in memory and "text unchanged" in memory
            from jevdual.ledger import trajectory_from_agent

            assert trajectory_from_agent(agent)[0]["actions"][0].endswith("-> suspected_noop")
        else:
            assert "suspected no-op" not in memory
