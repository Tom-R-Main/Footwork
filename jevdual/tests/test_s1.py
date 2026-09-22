import asyncio
import dataclasses
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


# ---- bounded delegation (Q9) -----------------------------------------------------------------


class _CapturingPolicy(FakePolicy):
    def __init__(self, decision):
        super().__init__(decision)
        self.contexts = []

    async def decide(self, menu, ctx):
        self.contexts.append(ctx)
        return await super().decide(menu, ctx)


class _SubgoalVerifier:
    answer_expected = False

    def __init__(self, met: bool):
        self.met = met
        self.calls = []

    async def judge_subgoal(self, agent, menu, subgoal, stop_condition):
        self.calls.append((subgoal, stop_condition))
        return self.met, f"subgoal_met p={'0.91' if self.met else '0.20'}"


def _delegating_agent(state, **kw):
    from jevdual.s1 import Delegation

    agent = FakeAgent(state)
    agent.delegation = Delegation(goal="open the About page", stop_condition="the About page is shown", **kw)
    agent.delegations = []
    agent.messages = []
    agent._message_manager = SimpleNamespace(_add_context_message=lambda m: agent.messages.append(m))
    return agent


def test_only_when_delegated_is_idle_without_a_delegation_and_makes_no_call():
    state, _ = _fresh_state_and_link()
    agent = FakeAgent(state)
    s1 = JevS1(_RaisingPolicy(), arbiter=AlwaysAct(), only_when_delegated=True)
    assert asyncio.run(s1.decide(agent, state)) is None
    assert agent.s1_records[1].verdict.reason.startswith("idle")


def test_delegation_supplies_subgoal_allowed_ops_and_known_values_and_counts_steps():
    state, idx = _fresh_state_and_link()
    agent = _delegating_agent(state, allowed_operations=("click",), known_values=(("Email", "ada@example.com"),), budget=3)
    policy = _CapturingPolicy(_decision("click", idx))
    s1 = JevS1(policy, arbiter=AlwaysAct(), only_when_delegated=True)
    out = asyncio.run(s1.decide(agent, state))
    assert out is not None and out.action[0].model_dump(exclude_unset=True) == {"click": {"index": idx}}
    ctx = policy.contexts[0]
    assert ctx.subgoal == "open the About page" and ctx.allowed_operations == ("click",) and ctx.stop_condition
    assert dict(ctx.known_values) == {"Email": "ada@example.com"}
    assert agent.delegation.steps_taken == 1


def test_delegated_done_with_observed_support_ends_the_delegation_and_briefs_system_2():
    state, _ = _fresh_state_and_link()
    agent = _delegating_agent(state)
    verifier = _SubgoalVerifier(met=True)
    s1 = JevS1(FakePolicy(_decision("done")), arbiter=AlwaysAct(), only_when_delegated=True, verifier=verifier)
    assert asyncio.run(s1.decide(agent, state)) is None  # System 2 takes this step with the summary
    assert verifier.calls == [("open the About page", "the About page is shown")]
    assert agent.delegation is None and agent.delegations[0].status == "reached"
    assert agent.messages and "finished the subgoal" in agent.messages[0].content and "reached" in agent.messages[0].content


def test_delegated_done_without_support_ends_the_delegation_not_reached():
    state, _ = _fresh_state_and_link()
    agent = _delegating_agent(state)
    verifier = _SubgoalVerifier(met=False)
    s1 = JevS1(FakePolicy(_decision("done")), arbiter=AlwaysAct(), only_when_delegated=True, verifier=verifier)
    assert asyncio.run(s1.decide(agent, state)) is None
    assert agent.delegation is None and agent.delegations[0].status == "not_reached"
    assert agent.delegations[0].jev_calls == 2  # the menu call and the subgoal check
    assert "Control is back with you" in agent.messages[0].content


def test_any_escalation_inside_a_delegation_transfers_control_with_a_reason():
    class LowConfidence:
        def judge(self, decision, menu, ctx, agent):
            return Verdict("escalate", "operation_confidence: operation confidence 0.40 < 0.55")

    state, idx = _fresh_state_and_link()
    agent = _delegating_agent(state)
    s1 = JevS1(FakePolicy(_decision("click", idx)), arbiter=LowConfidence(), only_when_delegated=True)
    assert asyncio.run(s1.decide(agent, state)) is None
    assert agent.delegation is None and agent.delegations[0].status == "operation_confidence"
    assert agent.messages and "operation_confidence" in agent.messages[0].content


def test_delegated_questions_are_scoped_to_the_subgoal():
    from jevdual.policy import JevPolicy, StepContext

    state, _ = _fresh_state_and_link()
    from jevdual.menu import build_menu

    menu = build_menu(state)
    pol = JevPolicy(client=None)
    req = pol.build_request(menu, StepContext(task="whole task", subgoal="open the About page", stop_condition="the About page is shown"))
    op = req.questions["operation"]
    assert op.instructions["question"].endswith("advance `subgoal` from the current page?")
    assert op.instructions["stop_condition"] == "the About page is shown"
    assert "stop_condition" in op.criteria["done"]
    assert "stop_condition" in req.questions["goal_done"].instructions
    plain = pol.build_request(menu, StepContext(task="whole task"))
    assert "stop_condition" not in plain.questions["goal_done"].instructions


def test_delegation_budget_exhaustion_ends_it_without_a_call():
    state, _ = _fresh_state_and_link()
    agent = _delegating_agent(state, budget=2)
    agent.delegation.steps_taken = 2
    s1 = JevS1(_RaisingPolicy(), arbiter=AlwaysAct(), only_when_delegated=True)
    assert asyncio.run(s1.decide(agent, state)) is None
    assert agent.delegation is None and agent.delegations[0].status == "budget_exhausted"


def test_allowed_operations_filter_the_offered_operations():
    from jevdual.policy import JevPolicy, StepContext

    state, _ = _fresh_state_and_link()
    from jevdual.menu import build_menu

    menu = build_menu(state)
    pol = JevPolicy(client=None)
    everything = pol.offered_operations(menu, StepContext(task="t"))
    only_click = pol.offered_operations(menu, StepContext(task="t", allowed_operations=("click",)))
    assert "click" in only_click and "type" not in only_click and "done" in only_click
    assert set(only_click) < set(everything) or set(only_click) == set(everything)


# ---- correctness tranche after the 2026-09-22 audit -------------------------------------------


class _TwoStagePolicy:
    """First stage: flat, destructive-flagged, pending group; second stage: a confident target."""

    async def decide(self, menu, ctx):
        d = _decision("click", None)
        return dataclasses.replace(d, operation_confidence=0.2, nouls={"goal_done": 0.1, "stuck": 0.0, "destructive": 0.99}, two_stage=True, pending_group=(3, 4))

    async def decide_target(self, menu, ctx, operation, group):
        return dataclasses.replace(_decision("click", group[0]), operation_confidence=1.0, nouls={}, target_confidence=0.95)


def test_two_stage_target_keeps_the_first_stage_confidence_and_safety_signals():
    from jevdual.arbiter import Arbiter

    state, _ = _fresh_state_and_link()
    agent = FakeAgent(state)
    s1 = JevS1(_TwoStagePolicy(), arbiter=Arbiter.from_toml())
    assert asyncio.run(s1.decide(agent, state)) is None
    rec = agent.s1_records[1]
    assert rec.decision.operation_confidence == 0.2 and rec.decision.nouls["destructive"] == 0.99
    assert rec.decision.target == 3 and not rec.decision.two_stage
    assert rec.verdict.kind in ("escalate", "confirm")  # the flat, destructive first stage rules, not the 1.0 second stage


def test_every_handback_inside_a_delegation_closes_it_with_a_status():
    state, idx = _fresh_state_and_link()
    # stale snapshot -> bridge/freshness handback
    agent = _delegating_agent(state)
    agent.browser_session._cached_browser_state_summary = object()
    s1 = JevS1(FakePolicy(_decision("click", idx)), arbiter=AlwaysAct(), only_when_delegated=True)
    assert asyncio.run(s1.decide(agent, state)) is None
    assert agent.delegation is None and agent.delegations[0].status == "stale_state"
    # typing with no known value inside an assignment -> needs_values, never the task literal
    state2, _ = _fresh_state_and_link()
    from jevdual.menu import build_menu

    field = next(c for c in build_menu(state2).candidates if "type" in c.operations)
    agent2 = _delegating_agent(state2)
    agent2.task = 'Open the About page and search for "lighthouse"'
    s1b = JevS1(FakePolicy(_decision("type", field.id)), arbiter=AlwaysAct(), only_when_delegated=True)
    assert asyncio.run(s1b.decide(agent2, state2)) is None
    assert agent2.delegation is None and agent2.delegations[0].status == "needs_values"
    assert "known_values" in agent2.messages[0].content


def test_scoped_authorisation_lets_the_named_action_through_and_pauses_the_rest():
    from jevdual.arbiter import Arbiter

    from tests.test_arbiter import Candidate as C
    from tests.test_arbiter import decision as dec
    from tests.test_arbiter import menu as mk

    class Scoped:
        authorized_destructive = True
        authorized_actions = ("finish", "checkout")

        def __init__(self):
            self.s1_records = {}

        def is_authorized(self, text):
            low = (text or "").casefold()
            return any(k in low for k in self.authorized_actions)

    finish = mk(cands=(C(id=1, label="Finish", role="button", operations=("click",)),))
    delete = mk(cands=(C(id=1, label="Delete account", role="button", operations=("click",)),))
    hot = dec("click", 1, destructive=0.8)
    from tests.test_arbiter import ctx as mkctx

    assert Arbiter.from_toml().judge(hot, finish, mkctx(), Scoped()).kind == "act"
    assert Arbiter.from_toml().judge(hot, delete, mkctx(), Scoped()).kind == "confirm"


def test_s1_record_keeps_a_redacted_menu_snapshot():
    state, idx = _fresh_state_and_link()
    agent = FakeAgent(state)
    s1 = JevS1(FakePolicy(_decision("click", idx)), arbiter=AlwaysAct())
    asyncio.run(s1.decide(agent, state))
    rec = agent.s1_records[1]
    assert rec.menu and any(m["id"] == idx for m in rec.menu)
    assert set(rec.menu[0]) == {"id", "label", "role", "section", "value", "input_type", "href", "offscreen"}


def test_delegated_typing_takes_a_literal_from_the_assignment_but_not_from_the_task():
    from jevdual.menu import build_menu

    from tests.fixtures import replay as _replay

    for name in ("replay_state", "replay_serialized", "load_fixture"):
        fn = getattr(_replay, name, None)
        if fn is not None and hasattr(fn, "cache_clear"):
            fn.cache_clear()
    state = _replay.replay_state("wikipedia-python")  # its text field is a search box, not an identity field
    field = next(c for c in build_menu(state).candidates if "type" in c.operations)
    assert field.label == "Search Wikipedia"
    agent = _delegating_agent(state)
    agent.task = 'Find the "Sauce Labs Bike Light" price after signing in.'
    agent.delegation.goal = 'Search the catalog for "brass lantern" and open the result'
    s1 = JevS1(FakePolicy(_decision("type", field.id)), arbiter=AlwaysAct(), only_when_delegated=True)
    out = asyncio.run(s1.decide(agent, state))
    assert out is not None and out.action[0].model_dump(exclude_unset=True)["input"]["text"] == "brass lantern"
    assert agent.delegation is not None and agent.delegation.steps_taken == 1
