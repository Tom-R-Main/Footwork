from types import SimpleNamespace

import pytest
from jevdual.arbiter import DEFAULT_POLICY_PATH, RULES, Arbiter, ArbiterPolicy, match_destructive_keyword
from jevdual.menu import Candidate, Menu
from jevdual.policy import Decision, StepContext
from jevdual.s1 import Verdict


def menu(url="http://s/", cands=None, text="hello world " * 40, title="Home"):
    cands = tuple(
        cands or (Candidate(id=3, label="About", role="a", operations=("click",), href="/about.html"),)
    )
    return Menu(url=url, title=title, page_text=text, candidates=cands, by_operation={})


def decision(op="click", target=3, op_conf=0.9, t_conf=0.8, probs=None, alternates=(), **nouls):
    base = {
        "goal_done": 0.1,
        "stuck": 0.0,
        "destructive": 0.0,
        "needs_reasoning": 0.1,
        "login_required": 0.0,
        "bot_check": 0.0,
    }
    base.update(nouls)
    tp = probs if probs is not None else ({target: t_conf} if target is not None else {})
    return Decision(
        op,
        op_conf,
        {op: op_conf},
        target,
        t_conf if target is not None else None,
        tp,
        tuple(alternates),
        base,
        "jev-1.13.0",
        50,
        10.0,
    )


class FakeAgent:
    def __init__(self, systems=None):
        self.step_systems = systems or {}
        self.s1_records = {}
        self.state = SimpleNamespace(n_steps=1)


def ctx(step=1):
    return StepContext(task="Open the About page", step=step)


def judge(arb, d, m=None, step=1, agent=None):
    return arb.judge(d, m or menu(), ctx(step), agent or FakeAgent())


def test_act_baseline():
    arb = Arbiter()
    v = judge(arb, decision())
    assert v.kind == "act" and v.reason.startswith("act:") and arb.stats["act"] == 1


def test_done_escalates_or_uses_hook():
    assert judge(Arbiter(), decision("done", None)).kind == "escalate"
    hook = Arbiter(on_done=lambda d, m, c, a: Verdict("act", "verified"))
    assert judge(hook, decision("done", None)).reason == "verified"


def test_blocked_reasons():
    v = judge(Arbiter(), decision("blocked", None, login_required=0.7))
    assert v.kind == "escalate" and "login_required 0.70" in v.reason
    v = judge(Arbiter(), decision("blocked", None, bot_check=0.9))
    assert "bot_check" in v.reason
    assert "no offered operation" in judge(Arbiter(), decision("blocked", None)).reason
    assert judge(Arbiter(), decision("click", 3, login_required=0.7)).kind == "act"  # only with blocked


def test_back_on_first_step():
    assert judge(Arbiter(), decision("back", None), step=1).reason.startswith("back_on_first_step")
    assert judge(Arbiter(), decision("back", None), step=2).kind == "act"


def test_goal_done():
    v = judge(Arbiter(), decision(goal_done=0.91))
    assert v.kind == "escalate" and "goal_done 0.91 >= 0.85" in v.reason
    assert judge(Arbiter(), decision(goal_done=0.5)).kind == "act"


def test_destructive_noul_and_keyword():
    assert judge(Arbiter(), decision(destructive=0.6)).kind == "confirm"
    m = menu(cands=[Candidate(id=3, label="Delete account", role="button", operations=("click",))])
    v = judge(Arbiter(), decision(), m)
    assert v.kind == "confirm" and "keyword 'delete'" in v.reason
    m = menu(cands=[Candidate(id=3, label="Postal code", role="input", operations=("type", "click"))])
    assert judge(Arbiter(), decision("type", 3), m).kind == "act"


def test_keyword_matcher():
    kws = ArbiterPolicy().destructive_keywords
    assert match_destructive_keyword("postal_code", kws) is None
    assert match_destructive_keyword("deposit", kws) is None
    assert match_destructive_keyword("Removed items", kws) is None
    assert match_destructive_keyword("Delete account", kws) == "delete"
    assert match_destructive_keyword("删除账户", kws) == "删除"
    assert match_destructive_keyword("Buy now!", kws) == "buy now"


def test_needs_reasoning():
    assert "needs_reasoning 0.70" in judge(Arbiter(), decision(needs_reasoning=0.7)).reason
    assert judge(Arbiter(), decision(needs_reasoning=0.5)).kind == "act"


def test_stuck_only_after_step_two():
    assert judge(Arbiter(), decision(stuck=0.9), step=2).kind == "act"
    v = judge(Arbiter(), decision(stuck=0.9), step=3)
    assert v.kind == "escalate" and "stuck 0.90" in v.reason


def test_head_disagreement():
    v = judge(Arbiter(), decision("click", None, probs={}))
    assert v.reason.startswith("head_disagreement")
    assert judge(Arbiter(), decision("scroll_page", None, probs={})).kind == "act"


def test_repeated_target():
    arb = Arbiter()
    # page text changes each step so the no_effect rule stays quiet; only the target repeats
    for s in range(1, 4):
        assert judge(arb, decision(), menu(text=f"page {s} " * 40), step=s).kind == "act"
    v = judge(arb, decision(), menu(text="page 4 " * 40), step=4)
    assert v.kind == "escalate" and v.reason.startswith("repeated_target")
    other = judge(arb, decision(), menu(url="http://s/other", text="other " * 40), step=5)
    assert other.kind == "act"


def test_s1_streak():
    agent = FakeAgent({s: "s1" for s in range(1, 9)})
    v = judge(Arbiter(), decision(), step=9, agent=agent)
    assert v.kind == "escalate" and v.reason.startswith("s1_streak")
    agent = FakeAgent({s: "s1" for s in range(1, 8)})
    assert judge(Arbiter(), decision(), step=8, agent=agent).kind == "act"
    agent = FakeAgent({**{s: "s1" for s in range(1, 9)}, 5: "s2"})
    assert judge(Arbiter(), decision(), step=9, agent=agent).kind == "act"


def test_no_effect_two_steps():
    arb = Arbiter()
    same = menu()
    assert judge(arb, decision(), same, step=1).kind == "act"
    assert judge(arb, decision(), same, step=2).kind == "act"  # first no-effect
    v = judge(arb, decision(), same, step=3)  # second consecutive no-effect
    assert v.kind == "escalate" and v.reason.startswith("no_effect")
    changed = menu(url="http://s/about.html", title="About", text="about " * 40)
    assert judge(arb, decision(), changed, step=4).kind == "act"


def test_operation_confidence_floor():
    v = judge(Arbiter(), decision(op_conf=0.4))
    assert v.kind == "escalate" and "operation confidence 0.40" in v.reason
    assert judge(Arbiter(), decision(op_conf=0.55)).kind == "act"


def test_target_confidence_retry_then_escalate():
    m = menu(
        cands=[
            Candidate(id=3, label="About", role="a", operations=("click",)),
            Candidate(id=4, label="Docs", role="a", operations=("click",)),
        ]
    )
    d = decision(target=3, t_conf=0.3, probs={3: 0.4, 4: 0.35}, alternates=(4,))
    v = judge(Arbiter(), d, m)
    assert v.kind == "retry_alternate" and "alternate 4" in v.reason
    far = decision(target=3, t_conf=0.3, probs={3: 0.6, 4: 0.2}, alternates=(4,))
    assert judge(Arbiter(), far, m).reason.startswith("target_confidence")
    arb = Arbiter()
    assert judge(arb, decision(target=4), m, step=1).kind == "act"  # 4 tried at this url
    assert judge(arb, d, m, step=2).reason.startswith("target_confidence")  # alternate already tried
    assert judge(Arbiter(), decision(target=3, t_conf=0.3), m).reason.startswith(
        "target_confidence"
    )  # no alternate


def test_from_toml_round_trips_every_field():
    loaded = ArbiterPolicy.from_toml()
    assert loaded == ArbiterPolicy()
    import tomllib

    keys = set(tomllib.loads(DEFAULT_POLICY_PATH.read_text()))
    from dataclasses import fields

    assert keys == {f.name for f in fields(ArbiterPolicy)}
    arb = Arbiter.from_toml()
    assert arb.policy.s1_streak_max == 8


def test_from_toml_rejects_unknown(tmp_path):
    p = tmp_path / "a.toml"
    p.write_text("bogus = 1\n")
    with pytest.raises(ValueError):
        ArbiterPolicy.from_toml(p)


def test_stats_and_summary():
    arb = Arbiter()
    agent = FakeAgent()
    judge(arb, decision(), step=1, agent=agent)
    judge(arb, decision(goal_done=0.95), step=2, agent=agent)
    agent.s1_records[3] = SimpleNamespace(
        verdict=Verdict("escalate", "policy error: boom"), error="policy: boom"
    )
    text = arb.summary_for_s2(agent, n=8)
    assert "step 1: click [3] 'About' -> act" in text
    assert "step 2: click [3] 'About' -> escalate (goal_done" in text
    assert "step 3: escalated (policy error: boom); error: policy: boom" in text
    assert arb.stats["act"] == 1 and arb.stats["goal_done"] == 1
    assert set(arb.stats) <= set(RULES)


def test_authorized_task_skips_the_confirm_rules_and_delegation_lowers_the_operation_floor():
    # a fresh arbiter per case: its no-effect and repeat-target state is per run
    m = menu(cands=(Candidate(id=1, label="Submit order", role="button", operations=("click",)),))
    hot = decision("click", 1, destructive=0.75)
    assert judge(Arbiter.from_toml(), hot, m).kind == "confirm"
    authorized = FakeAgent()
    authorized.authorized_destructive = True
    assert judge(Arbiter.from_toml(), hot, m, agent=authorized).kind == "act"
    flat = decision("click", 1, op_conf=0.48)
    assert judge(Arbiter.from_toml(), flat, m).kind == "escalate"
    delegated = FakeAgent()
    delegated.delegation = object()
    assert judge(Arbiter.from_toml(), flat, m, agent=delegated).kind == "act"


def test_contextual_keywords_are_destructive_only_in_a_durable_context():
    from jevdual.arbiter import ArbiterPolicy, destructive_match

    p = ArbiterPolicy.from_toml()
    assert destructive_match("Remove", "https://www.saucedemo.com/cart.html Swag Labs cart", p) is None
    assert destructive_match("Remove", "https://site/account/settings Account settings", p) == "remove"
    assert destructive_match("Delete account", "https://www.saucedemo.com/cart.html", p) == "delete"
    assert destructive_match("Cancel", "Cancel subscription billing", p) == "cancel"
    assert destructive_match("Cancel", "search dialog", p) is None


def test_arbiter_confirm_rule_uses_the_menu_context_for_contextual_keywords():
    remove_in_cart = menu(
        url="https://www.saucedemo.com/cart.html",
        title="Swag Labs",
        cands=(Candidate(id=1, label="Remove", role="button", operations=("click",)),),
    )
    remove_in_account = menu(
        url="https://site/account",
        title="Account settings",
        cands=(Candidate(id=1, label="Remove", role="button", operations=("click",)),),
    )
    d = decision("click", 1)
    assert judge(Arbiter.from_toml(), d, remove_in_cart).kind == "act"
    assert judge(Arbiter.from_toml(), d, remove_in_account).kind == "confirm"
