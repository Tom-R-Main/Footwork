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


async def _run(httpserver, llm, *, policy=None, authorized=False, max_steps=6, use_judge=False):
    httpserver.expect_request("/").respond_with_data(PAGE, content_type="text/html")
    httpserver.expect_request("/delete-account").respond_with_data("<html><body>Deleted</body></html>", content_type="text/html")
    agent = DualProcessAgent(
        task="Open the account page and report the balance.",
        llm=llm,
        browser_profile=BrowserProfile(headless=True),
        s1_policy=policy,
        authorized_destructive=authorized,
        use_judge=use_judge,
        calculate_cost=False,
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
    llm = create_mock_llm([step({"navigate": {"url": httpserver.url_for("/delete-account")}}), done("deleted")])
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
