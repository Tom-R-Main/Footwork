import asyncio
from types import SimpleNamespace

import pytest
from browser_use.agent.views import AgentOutput
from browser_use.tools.service import Tools
from jevdual.policy import Decision, PolicyError
from jevdual.s1 import AlwaysAct, JevS1, Verdict, literal_text_source

from tests.fixtures.replay import replay_state


def _decision(op, target=None, alternates=()):
    return Decision(op, 0.9, {op: 0.9}, target, 0.8 if target else None, {target: 0.8} if target else {}, tuple(alternates), {"goal_done": 0.1, "stuck": 0.0, "destructive": 0.0}, "jev-1.13.0", 50, 12.0)


class FakePolicy:
    def __init__(self, decision):
        self.decision = decision

    async def decide(self, menu, ctx):
        if isinstance(self.decision, Exception):
            raise self.decision
        return self.decision


class FakeAgent:
    def __init__(self, state, task="Open the About page"):
        am = Tools().registry.create_action_model()
        self.ActionModel = am
        self.AgentOutput = AgentOutput.type_with_custom_actions(am)
        self.task = task
        self.state = SimpleNamespace(n_steps=1)
        self.history = SimpleNamespace(history=[])
        self.browser_session = SimpleNamespace(_cached_browser_state_summary=state)


def replace_url(state, url):
    """A copy of a BrowserStateSummary at another URL (pydantic model_copy when available)."""
    try:
        return state.model_copy(update={"url": url})
    except AttributeError:
        import copy

        c = copy.copy(state)
        c.url = url
        return c


def _state_and_link():
    state = replay_state("modal-over-content")
    idx = next(i for i, n in state.dom_state.selector_map.items() if n.tag_name == "a")
    return state, idx


def test_act_path_bridges_click():
    state, idx = _state_and_link()
    agent = FakeAgent(state)
    s1 = JevS1(FakePolicy(_decision("click", idx)))
    out = asyncio.run(s1.decide(agent, state))
    assert out is not None and out.action[0].model_dump(exclude_unset=True) == {"click": {"index": idx}}
    rec = agent.s1_records[1]
    assert rec.verdict.kind == "act" and rec.proposed[0].name == "click" and rec.decision.target == idx


def test_escalate_on_policy_error_and_arbiter():
    state, idx = _state_and_link()
    agent = FakeAgent(state)
    assert asyncio.run(JevS1(FakePolicy(PolicyError("boom"))).decide(agent, state)) is None
    assert agent.s1_records[1].verdict.kind == "escalate"

    class Escalator:
        def judge(self, d, m, c, a):
            return Verdict("escalate", "needs reasoning")

    agent2 = FakeAgent(state)
    assert asyncio.run(JevS1(FakePolicy(_decision("click", idx)), arbiter=Escalator()).decide(agent2, state)) is None
    assert agent2.s1_records[1].verdict.reason == "needs reasoning"


def test_retry_alternate_uses_next_best():
    state, _ = _state_and_link()
    links = [i for i, n in state.dom_state.selector_map.items() if n.tag_name == "a"]
    if len(links) < 2:
        return

    class Retry:
        def judge(self, d, m, c, a):
            return Verdict("retry_alternate", "low target confidence")

    agent = FakeAgent(state)
    out = asyncio.run(JevS1(FakePolicy(_decision("click", links[0], alternates=(links[1],))), arbiter=Retry()).decide(agent, state))
    assert out.action[0].model_dump(exclude_unset=True) == {"click": {"index": links[1]}}


def test_stale_state_escalates():
    state, idx = _state_and_link()
    agent = FakeAgent(state)
    agent.browser_session._cached_browser_state_summary = object()
    assert asyncio.run(JevS1(FakePolicy(_decision("click", idx))).decide(agent, state)) is None
    assert "stale" in agent.s1_records[1].error


def test_literal_text_source():
    assert literal_text_source('Search for "lantern" now', None, None) == "lantern"
    assert literal_text_source("Search for lanterns", None, None) is None


def test_destructive_gate_replaces_action_for_either_system():
    """The agent-level gate rewrites an index action whose target label is destructive into a failed done."""
    import asyncio
    from types import SimpleNamespace

    from browser_use.agent.views import AgentOutput
    from browser_use.tools.service import Tools
    from jevdual.agent import DualProcessAgent

    from tests.fixtures.replay import replay_state

    state = replay_state("modal-over-content")
    idx, node = next(iter(state.dom_state.selector_map.items()))
    node.ax_node = SimpleNamespace(name="Delete account", role="button")

    class Fake(DualProcessAgent):  # bypass Agent.__init__; only the gate is under test
        def __init__(self):
            am = Tools().registry.create_action_model()
            self.ActionModel = am
            self.AgentOutput = AgentOutput.type_with_custom_actions(am)
            self.state = SimpleNamespace(n_steps=3, last_model_output=self.AgentOutput(action=[am(click={"index": idx})]))
            self.browser_session = SimpleNamespace(_cached_browser_state_summary=state)
            self.step_systems = {3: "s2"}
            from jevdual.arbiter import ArbiterPolicy

            self.destructive_keywords = ArbiterPolicy.from_toml().destructive_keywords
            self.authorized_destructive = False
            self.paused_before_action = None
            self.s1_policy = None
            self.s2_verifications = []
            self.s2_done_rejections = 0
            self.max_done_rejections = 2
            self.executed = None

        async def _super_execute(self):
            self.executed = [a.model_dump(exclude_unset=True) for a in self.state.last_model_output.action]

    async def go(agent):
        # call the gate, then capture what would have been dispatched
        out = agent.state.last_model_output
        hit = agent._destructive_hit(list(out.action))
        assert hit is not None and hit[1] == "delete"
        import jevdual.agent as mod

        orig = mod.Agent._execute_actions
        mod.Agent._execute_actions = Fake._super_execute
        try:
            await DualProcessAgent._execute_actions(agent)
        finally:
            mod.Agent._execute_actions = orig

    agent = Fake()
    asyncio.run(go(agent))
    assert agent.paused_before_action["system"] == "s2" and agent.paused_before_action["keyword"] == "delete"
    assert agent.executed[0]["done"]["success"] is False and "Delete account" in agent.executed[0]["done"]["text"]


def test_redact_menu_scrubs_every_model_facing_string():
    from jevdual.menu import Candidate, Menu
    from jevdual.s1 import redact_menu
    from jevdual.secrets import SecretStore

    red = SecretStore({"password": "hunter2"}).redactor()
    m = Menu(url="http://s/account.html?user=ada&password=hunter2", title="hunter2 page", page_text="you typed hunter2",
             candidates=(Candidate(1, "hunter2", "a", ("click",), href="/x?p=hunter2", value="hunter2"),), by_operation={"click": ()})
    r = redact_menu(m, red)
    import json

    assert "hunter2" not in json.dumps({"u": r.url, "t": r.title, "p": r.page_text, "c": [c.to_state() for c in r.candidates]})
    assert r.candidates[0].id == 1


def test_gate_covers_index_less_actions():
    import asyncio
    from types import SimpleNamespace

    from browser_use.tools.service import Tools
    from jevdual.agent import DualProcessAgent
    from jevdual.arbiter import ArbiterPolicy

    am = Tools().registry.create_action_model()
    a = DualProcessAgent.__new__(DualProcessAgent)
    a.destructive_keywords = ArbiterPolicy.from_toml().destructive_keywords
    a.browser_session = SimpleNamespace(_cached_browser_state_summary=None, get_or_create_cdp_session=None)
    assert asyncio.run(a._destructive_hit_any([am(evaluate={"code": "document.querySelector('#del').click()"})]))[1] == "evaluate"
    assert asyncio.run(a._destructive_hit_any([am(navigate={"url": "http://s/delete-confirm.html"})]))[1] == "delete"
    assert asyncio.run(a._destructive_hit_any([am(navigate={"url": "http://s/about.html"})])) is None
    hit = asyncio.run(a._destructive_hit_any([am(send_keys={"keys": "Enter"})]))
    assert hit is not None and hit[1] == "enter"  # focus unknown: gate conservatively


# ---- call economy and the guarded arm (Q9) ---------------------------------------------------


def _fresh_state_and_link():
    """Earlier tests in this file swap ax nodes on the cached replay fixture; start from a clean replay."""
    from tests.fixtures import replay as _replay

    for name in ("replay_state", "replay_serialized", "load_fixture"):
        fn = getattr(_replay, name, None)
        if fn is not None and hasattr(fn, "cache_clear"):
            fn.cache_clear()
    return _state_and_link()


class _RaisingPolicy:
    async def decide(self, menu, ctx):
        raise AssertionError("S1 must not be consulted on this step")


class _RaisingVerifier:
    answer_expected = True

    async def judge_done(self, agent, menu, answer=None):
        raise AssertionError("verification must not be called for an answer-less done on an answer task")


def test_answer_less_done_on_answer_task_is_vetoed_without_a_verification_call():
    state, _ = _fresh_state_and_link()
    agent = FakeAgent(state, task="Report the keeper's name")
    s1 = JevS1(FakePolicy(_decision("done")), arbiter=AlwaysAct(), verifier=_RaisingVerifier())
    assert asyncio.run(s1.decide(agent, state)) is None
    rec = agent.s1_records[1]
    assert rec.verdict.kind == "escalate" and "not verified" in rec.verdict.reason


def test_escalation_streak_hands_control_to_system_2_without_menu_calls():
    from jevdual.s1 import S1Record, Verdict

    state, _ = _fresh_state_and_link()
    agent = FakeAgent(state)
    agent.s1_records = {i: S1Record(step=i, decision=None, verdict=Verdict("escalate", "needs_reasoning: 0.9 >= 0.6")) for i in (1, 2, 3)}
    s1 = JevS1(_RaisingPolicy(), arbiter=AlwaysAct(), escalation_streak=3, s2_control_steps=2)
    agent.state.n_steps = 4
    assert asyncio.run(s1.decide(agent, state)) is None
    assert agent.s1_records[4].verdict.reason.startswith("s2_control: 3 consecutive escalations on 'needs_reasoning'")
    agent.state.n_steps = 5
    assert asyncio.run(s1.decide(agent, state)) is None  # still System 2's stretch, still no menu call
    assert "keeps control" in agent.s1_records[5].verdict.reason
    # the stretch is over at step 6: S1 is consulted again (the raising policy proves it)
    agent.state.n_steps = 6
    with pytest.raises(AssertionError, match="must not be consulted"):
        asyncio.run(s1.decide(agent, state))


def test_escalation_streak_ends_early_on_a_url_change():
    from jevdual.s1 import S1Record, Verdict

    state, _ = _fresh_state_and_link()
    agent = FakeAgent(state)
    agent.s1_records = {i: S1Record(step=i, decision=None, verdict=Verdict("escalate", "stuck: 0.9 >= 0.85")) for i in (1, 2, 3)}
    s1 = JevS1(_RaisingPolicy(), arbiter=AlwaysAct(), escalation_streak=3, s2_control_steps=5)
    agent.state.n_steps = 4
    assert asyncio.run(s1.decide(agent, state)) is None
    moved = replace_url(state, "http://s/elsewhere.html")
    agent.state.n_steps = 5
    with pytest.raises(AssertionError, match="must not be consulted"):
        asyncio.run(s1.decide(agent, moved))


def test_guard_only_never_decides_but_carries_the_verifier():
    from jevdual.s1 import GuardOnly

    state, _ = _fresh_state_and_link()
    v = _RaisingVerifier()
    g = GuardOnly(verifier=v, secrets=None)
    assert asyncio.run(g.decide(FakeAgent(state), state)) is None
    assert g.verifier is v
