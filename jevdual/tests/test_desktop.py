"""NativeAgent loop over a fake Driver: act, done, escalate, confirm, refused, type and secrets."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.arbiter import Arbiter
from jevdual.desktop import NativeAgent, NativeRun
from jevdual.native import NativeBridge
from jevdual.policy import Decision, PolicyError
from jevdual.s1 import AlwaysAct
from jevdual.secrets import SecretStore
from jevdual.trace import TraceWriter, read_trace

FIXTURE = Path(__file__).parent / "fixtures" / "native" / "calculator.json"


def _decision(op, target=None, *, conf=0.9, tconf=0.8, nouls=None, alternates=()):
    return Decision(
        op,
        conf,
        {op: conf},
        target,
        tconf if target is not None else None,
        {target: tconf} if target is not None else {},
        tuple(alternates),
        nouls or {"goal_done": 0.05, "stuck": 0.02, "destructive": 0.01, "needs_reasoning": 0.03},
        "jev-1.13.0",
        120,
        15.0,
    )


class SeqPolicy:
    """Returns the queued decisions in order; a PolicyError instance is raised."""

    def __init__(self, *decisions):
        self.queue = list(decisions)
        self.calls = 0

    async def decide(self, menu, ctx):
        self.calls += 1
        d = self.queue.pop(0)
        if isinstance(d, Exception):
            raise d
        return d


class FakeVerdict:
    def __init__(self, band, reason, answer=None):
        self.band = band
        self.reason = reason
        self.supported_answer = answer

    def to_trace(self):
        return {"band": self.band, "reason": self.reason}


class FakeHook:
    """Looks like ArbiterHook: has .verifier.verify and .ledger."""

    def __init__(self, band="accept", reason="ok"):
        self.ledger = None
        self.last = None
        self.calls = []
        hook = self

        class V:
            async def verify(self_, task, requirements, menu, answer, **kw):
                hook.calls.append({"task": task, "trajectory": kw.get("trajectory")})
                return FakeVerdict(band, reason)

        self.verifier = V()


class FakeDriver:
    def __init__(self, snapshot, *, click_effect="CONFIRMED", refuse_labels=()):
        self.snapshot = dict(snapshot)
        self.calls = []
        self.click_effect = click_effect
        self.refuse_labels = set(refuse_labels)
        self.n = 0

    async def get_window_state(self, inp):
        self.n += 1
        snap = dict(self.snapshot)
        snap["snapshot_id"] = f"s{self.n:08x}"
        snap["elements"] = [
            {**e, "element_token": f"s{self.n:08x}:{e['element_index']}"} for e in self.snapshot["elements"]
        ]
        self.calls.append(("get_window_state", None))
        return snap

    async def click(self, inp):
        self.calls.append(("click", inp))
        token = inp["position"][1]
        idx = int(token.split(":")[1])
        el = next(e for e in self.snapshot["elements"] if e["element_index"] == idx)
        if el.get("label") in self.refuse_labels:
            raise RuntimeError("tool='click', message='AX action failed', error_code='ax_failed'")
        return SimpleNamespace(
            effect=SimpleNamespace(name=self.click_effect),
            route=SimpleNamespace(name="ACCESSIBILITY"),
            evidence=None,
            summary=f"pressed {el.get('label')}",
        )

    async def call_tool(self, name, args_json):
        self.calls.append((name, json.loads(args_json)))
        return SimpleNamespace(
            action=SimpleNamespace(
                effect=SimpleNamespace(name="CONFIRMED"),
                route=SimpleNamespace(name="ACCESSIBILITY"),
                evidence=[SimpleNamespace(kind=SimpleNamespace(name="VALUE_READBACK"), detail="read back")],
                summary="set",
            ),
            text="",
            is_error=False,
            error_code=None,
        )


@pytest.fixture
def stub_sdk(monkeypatch):
    stub = SimpleNamespace(
        GetWindowStateInput=lambda **kw: kw,
        ClickInput=lambda **kw: kw,
        ClickPosition=SimpleNamespace(ELEMENT=lambda element_token: ("element", element_token)),
        InputDeliveryMode=SimpleNamespace(BACKGROUND="background", FOREGROUND="foreground"),
        ActionTarget=SimpleNamespace(WINDOW=lambda pid, window_id: ("window", pid, window_id)),
    )
    monkeypatch.setitem(sys.modules, "cua_driver", stub)
    return stub


@pytest.fixture
def snapshot():
    return json.loads(FIXTURE.read_text())


def _ids(snapshot):
    """Button ids by label (the menu bar carries look-alike AXMenuItems the menu excludes)."""
    return {
        e["label"]: e["element_index"]
        for e in snapshot["elements"]
        if e.get("label") and e["role"] == "AXButton"
    }


def _agent(driver, policy, **kw):
    bridge = NativeBridge(driver, pid=1, window_id=2)
    kw.setdefault("task", "Compute 6 times 7")
    kw.setdefault("text_source", lambda task, target, menu: None)
    return NativeAgent(bridge, policy, **kw)


def test_s1_acts_then_done_is_verified(snapshot, stub_sdk, tmp_path):
    ids = _ids(snapshot)
    policy = SeqPolicy(_decision("click", ids["6"]), _decision("click", ids["Equals"]), _decision("done"))
    hook = FakeHook("accept", "display shows 42")
    trace = TraceWriter(tmp_path / "t.jsonl")
    agent = _agent(
        driver := FakeDriver(snapshot), policy, verifier=hook, trace=trace, run_id="calc-s1_only-1"
    )
    run: NativeRun = asyncio.run(agent.run())
    trace.close()
    assert run.status == "done" and run.s1_steps == 3  # two clicks and the verified done
    assert [n for n, _ in driver.calls if n == "click"] == ["click", "click"]
    assert hook.calls and hook.calls[0]["trajectory"][0]["actions"] == [f"click({ids['6']})"]
    _, steps = read_trace(tmp_path / "t.jsonl")
    assert [s.system for s in steps] == ["s1", "s1", "s1"]
    assert steps[0].executed[0].name == "click" and steps[0].executed[0].params["effect"] == "confirmed"
    assert steps[2].is_done and steps[2].verify == {"band": "accept", "reason": "display shows 42"}
    assert steps[0].menu and all(m.role == "button" for m in steps[0].menu if m.label == "6")
    assert steps[0].timings.dom_ms is not None and steps[0].timings.jev_ms == 15.0


def test_done_rejected_escalates_and_s1_only_stops(snapshot, stub_sdk):
    policy = SeqPolicy(_decision("done"))
    hook = FakeHook("reject", "nothing computed")
    run = asyncio.run(_agent(FakeDriver(snapshot), policy, verifier=hook).run())
    assert run.status == "escalated" and "verification reject" in run.reason
    assert run.steps[0].verdict.kind == "escalate" and not run.steps[0].executed


def test_arbiter_floors_escalate_and_policy_error_escalates(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.2))
    run = asyncio.run(_agent(FakeDriver(snapshot), policy, arbiter=Arbiter.from_toml()).run())
    assert run.status == "escalated" and run.reason.startswith("target_confidence")
    run = asyncio.run(_agent(FakeDriver(snapshot), SeqPolicy(PolicyError("boom"))).run())
    assert run.status == "escalated" and run.steps[0].error == "policy: boom"


def test_gate_pauses_before_a_destructive_click(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(_decision("click", ids["All Clear"]))

    def gate(nm, target):
        return "keyword 'clear'" if "Clear" in target.label else None

    driver = FakeDriver(snapshot)
    run = asyncio.run(_agent(driver, policy, gate=gate).run())
    assert run.status == "paused" and run.reason.startswith("destructive")
    assert not [n for n, _ in driver.calls if n == "click"]


def test_refused_effect_is_recorded_and_run_continues(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(
        _decision("click", ids["All Clear"]), _decision("click", ids["6"]), _decision("blocked")
    )
    driver = FakeDriver(snapshot, refuse_labels={"All Clear"})
    run = asyncio.run(_agent(driver, policy).run())
    assert run.status == "blocked"
    first = run.steps[0]
    assert first.effect.effect == "refused" and first.error.startswith("driver refused")
    assert first.executed[0].params["effect"] == "refused"
    assert run.steps[1].effect.effect == "confirmed"
    assert "not dispatched" not in (run.steps[0].memory_line or "")
    assert agent_memory_mentions(run, "refused")


def agent_memory_mentions(run, word):
    return any(word in (s.memory_line or "") or word in str(s.effect) for s in run.steps)


def test_type_uses_literal_and_secret_values(stub_sdk):
    snap = {
        "snapshot_id": "s1",
        "pid": 1,
        "window_id": 2,
        "app_name": "Demo",
        "window_title": "Sign in",
        "elements_complete": True,
        "tree_markdown": "",
        "elements": [
            {"element_index": 0, "role": "AXWindow", "label": "Sign in", "actions": ["AXRaise"]},
            {
                "element_index": 1,
                "role": "AXTextField",
                "label": "Username",
                "value": "",
                "parent_index": 0,
                "enabled": True,
            },
            {
                "element_index": 2,
                "role": "AXSecureTextField",
                "label": "Password",
                "value": "",
                "parent_index": 0,
                "enabled": True,
            },
        ],
    }
    store = SecretStore({"app://Demo": {"password": "hunter2secret"}})
    policy = SeqPolicy(_decision("type", 1), _decision("type", 2), _decision("blocked"))

    def text_source(task, target, menu):
        return "tom" if target.label == "Username" else "<secret>password</secret>"

    driver = FakeDriver(snap)
    agent = _agent(driver, policy, task='Sign in as "tom"', text_source=text_source, secrets=store)
    run = asyncio.run(agent.run())
    set_calls = [a for n, a in driver.calls if n == "set_value"]
    assert [c["value"] for c in set_calls] == ["tom", "hunter2secret"]
    # the trace never carries the secret value
    assert run.steps[1].executed[0].params["text"] != "hunter2secret"
    assert "hunter2secret" not in " ".join(agent.memory)


def test_secret_not_allowed_for_app_escalates(stub_sdk):
    snap = {
        "snapshot_id": "s1",
        "pid": 1,
        "window_id": 2,
        "app_name": "Other",
        "window_title": "x",
        "elements_complete": True,
        "tree_markdown": "",
        "elements": [
            {"element_index": 0, "role": "AXWindow", "label": "x", "actions": ["AXRaise"]},
            {
                "element_index": 1,
                "role": "AXSecureTextField",
                "label": "Password",
                "value": "",
                "parent_index": 0,
                "enabled": True,
            },
        ],
    }
    store = SecretStore({"app://Demo": {"password": "hunter2secret"}})
    policy = SeqPolicy(_decision("type", 1))
    agent = _agent(
        FakeDriver(snap), policy, text_source=lambda t, c, m: "<secret>password</secret>", secrets=store
    )
    run = asyncio.run(agent.run())
    assert run.status == "escalated" and "not allowed" in run.reason


def test_escalation_hands_the_step_to_system_two(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(_decision("click", ids["6"], tconf=0.1), _decision("done"))
    seen = []

    class S2:
        async def step(self, agent, nm, reason, out):
            seen.append(reason)
            target = nm.menu.candidate(ids["7"])
            await agent.execute(nm, "click", target, None, out)

    hook = FakeHook("accept", "ok")
    driver = FakeDriver(snapshot)
    run = asyncio.run(_agent(driver, policy, arbiter=Arbiter.from_toml(), s2=S2(), verifier=hook).run())
    assert run.status == "done" and run.s2_steps == 1 and seen and seen[0].startswith("target_confidence")
    assert run.steps[0].system == "s2" and run.steps[0].executed[0].params["index"] == ids["7"]
    assert agent_memory_mentions(run, "confirmed")


def test_always_act_and_budget(snapshot, stub_sdk):
    ids = _ids(snapshot)
    policy = SeqPolicy(*[_decision("click", ids["6"]) for _ in range(3)])
    run = asyncio.run(_agent(FakeDriver(snapshot), policy, arbiter=AlwaysAct(), max_steps=3).run())
    assert run.status == "budget_exhausted" and run.s1_steps == 3
