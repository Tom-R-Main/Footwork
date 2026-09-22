import asyncio
import os
from pathlib import Path

import pytest
from browser_use.tools.service import Tools
from jevdual.policy import Decision
from jevdual.tools import GoalParams, MicroLoopResult, register_act_toward_goal


def _decision(op, target=None, op_p=0.9, t_p=0.8, **nouls):
    return Decision(op, op_p, {op: op_p}, target, t_p if target is not None else None, {target: t_p} if target is not None else {}, (), {"goal_done": 0.1, "stuck": 0.0, "destructive": 0.0, **nouls}, "jev-1.13.0", 50, 10.0)


def test_registration_and_schema():
    tools = Tools()

    async def decide(menu, ctx):
        return _decision("done")

    register_act_toward_goal(tools, decide=decide)
    action = tools.registry.registry.actions["act_toward_goal"]
    assert set(action.param_model.model_fields) == {"goal", "max_steps"}
    assert GoalParams(goal="open pricing").max_steps == 10
    am = tools.registry.create_action_model()
    assert "ActTowardGoalActionModel" in repr(am.model_fields["root"].annotation)


def test_result_summary_shape():
    r = MicroLoopResult(status="reached", goal="open about", steps=[{"operation": "click", "label": "About", "executed": True}], final_url="http://s/about.html", reason="policy reports goal reached")
    assert "reached after 1 step(s)" in r.summary() and r.to_json()["status"] == "reached"


@pytest.mark.skipif(os.environ.get("JEVDUAL_BROWSER_TESTS") != "1", reason="set JEVDUAL_BROWSER_TESTS=1")
def test_micro_loop_end_to_end():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import spike_b1
    from browser_use.browser.profile import BrowserProfile
    from browser_use.browser.session import BrowserSession
    from jevdual.tools import run_micro_loop

    base, stop = spike_b1.serve()
    calls = {"n": 0}

    async def decide(menu, ctx):
        calls["n"] += 1
        if calls["n"] == 1:
            idx = next(c.id for c in menu.candidates if "About" in c.label)
            return _decision("click", idx)
        return _decision("done", goal_done=0.95)

    async def go():
        bs = BrowserSession(browser_profile=BrowserProfile(headless=True))
        await bs.start()
        try:
            await bs.navigate_to(base + "/")
            return await run_micro_loop("open the About page", bs, Tools(), decide=decide)
        finally:
            await bs.kill()

    try:
        r = asyncio.run(go())
    finally:
        stop()
    assert r.status == "reached" and r.final_url.endswith("/about.html") and r.steps[0]["executed"] and r.jev_calls == 2


@pytest.mark.skipif(os.environ.get("JEVDUAL_BROWSER_TESTS") != "1", reason="set JEVDUAL_BROWSER_TESTS=1")
def test_pause_keyword_halts_before_action():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import spike_b1
    from browser_use.browser.profile import BrowserProfile
    from browser_use.browser.session import BrowserSession
    from jevdual.tools import MicroLoopConfig, run_micro_loop

    base, stop = spike_b1.serve()

    async def decide(menu, ctx):
        idx = next(c.id for c in menu.candidates if "About" in c.label)
        return _decision("click", idx)

    async def go():
        bs = BrowserSession(browser_profile=BrowserProfile(headless=True))
        await bs.start()
        try:
            await bs.navigate_to(base + "/")
            return await run_micro_loop("open about", bs, Tools(), decide=decide, config=MicroLoopConfig(pause_before_keywords=("about",)))
        finally:
            await bs.kill()

    try:
        r = asyncio.run(go())
    finally:
        stop()
    assert r.status == "paused_before_action" and not r.steps[0]["executed"]


def test_delegate_subgoal_tool_starts_a_delegation_on_the_agent():
    import asyncio
    from types import SimpleNamespace

    from browser_use import Tools
    from jevdual.tools import register_delegation

    agent = SimpleNamespace(delegation=None, state=SimpleNamespace(n_steps=3))
    tools = Tools()
    register_delegation(tools, lambda: agent)
    assert "delegate_subgoal" in tools.registry.registry.actions
    params = {"goal": "add the backpack to the cart", "stop_condition": "cart badge shows 1", "allowed_operations": ["click"], "known_values": {}, "max_steps": 5}
    result = asyncio.run(tools.registry.execute_action("delegate_subgoal", params))
    assert result.error is None and "Delegated" in (result.extracted_content or "")
    assert agent.delegation.goal == "add the backpack to the cart" and agent.delegation.budget == 5 and agent.delegation.started_step == 3
    again = asyncio.run(tools.registry.execute_action("delegate_subgoal", params))
    assert again.error and "already active" in again.error


def test_delegate_subgoal_refuses_a_typing_assignment_without_values():
    import asyncio
    from types import SimpleNamespace

    from browser_use import Tools
    from jevdual.tools import register_delegation

    agent = SimpleNamespace(delegation=None, state=SimpleNamespace(n_steps=1))
    tools = Tools()
    register_delegation(tools, lambda: agent)
    r = asyncio.run(tools.registry.execute_action("delegate_subgoal", {"goal": "Sign in with username standard_user and the password provided", "stop_condition": "products page shown", "known_values": {}}))
    assert r.error and "known_values" in r.error and agent.delegation is None
    r2 = asyncio.run(tools.registry.execute_action("delegate_subgoal", {"goal": "Sign in with username standard_user and the password provided", "stop_condition": "products page shown", "known_values": {"username": "standard_user", "password": "<secret>pw</secret>"}}))
    assert r2.error is None and agent.delegation is not None


def test_delegate_subgoal_search_goals_need_a_value_or_a_quoted_query():
    import asyncio
    from types import SimpleNamespace

    from browser_use import Tools
    from jevdual.tools import register_delegation

    agent = SimpleNamespace(delegation=None, state=SimpleNamespace(n_steps=1))
    tools = Tools()
    register_delegation(tools, lambda: agent)
    r = asyncio.run(tools.registry.execute_action("delegate_subgoal", {"goal": "Search Wikipedia for Eiffel Tower and open its article", "stop_condition": "article shown"}))
    assert r.error and "value" in r.error and agent.delegation is None
    r2 = asyncio.run(tools.registry.execute_action("delegate_subgoal", {"goal": "Search Wikipedia for 'Eiffel Tower' and open its article", "stop_condition": "article shown"}))
    assert r2.error is None and agent.delegation is not None
