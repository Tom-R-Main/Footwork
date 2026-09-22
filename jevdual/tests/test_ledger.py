import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from jevdual.ledger import Ledger, trajectory_from_agent
from jevdual.menu import Menu
from jevdual.verify import ArbiterHook, Verifier
from typesafe_sdk import SystemOneResponse

FIXTURES = Path(__file__).parent / "fixtures" / "jev_responses"
REQS = ("Order was placed", "Confirmation names the customer")


def load(name: str) -> SystemOneResponse:
    return SystemOneResponse.model_validate(json.loads((FIXTURES / f"{name}.json").read_text()))


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def system_one(self, state, questions, *, model=None, **kwargs):
        self.calls.append({"state": state, "questions": questions})
        return self.responses.pop(0)


def menu():
    return Menu(url="http://s/confirm.html", title="Thanks", page_text="Thank you for your order", candidates=(), by_operation={})


def test_ledger_is_monotone_and_carries_met_requirements():
    led = Ledger()
    led.update({"a": 0.9, "b": 0.1})
    assert led.apply({"a": 0.5, "b": 0.95}) == {"a": 0.5, "b": 0.1}
    led.update({"a": 0.05, "b": 0.99})
    assert led.best_unmet == {"a": 0.05, "b": 0.1}
    assert set(led.met()) == {"a", "b"}


def test_verifier_uses_ledger_adjusted_unmet_for_the_band():
    # fixture: complete 0.55, unmet_0 0.06, unmet_1 0.88 -> reject on requirement 1 without a ledger
    v = Verifier(FakeClient(load("verify_reject_unmet")))
    verdict = asyncio.run(v.verify("Place the order", REQS, menu(), None))
    assert verdict.band == "reject" and verdict.unmet_effective == verdict.unmet

    led = Ledger()
    led.update({REQS[1]: 0.1})  # judged met at an earlier verification in this run
    v = Verifier(FakeClient(load("verify_reject_unmet")))
    verdict = asyncio.run(v.verify("Place the order", REQS, menu(), None, ledger=led))
    assert verdict.band == "verify"  # complete 0.55 is in the uncertain band, no longer a reject
    assert verdict.unmet[REQS[1]] == 0.88 and verdict.unmet_effective[REQS[1]] == 0.1
    assert "ledger carried 1 requirement(s)" in verdict.reason
    assert led.best_unmet[REQS[0]] == 0.06  # this call's verdicts were recorded too


def test_state_carries_the_trajectory_next_to_the_page():
    client = FakeClient(load("verify_accept"))
    v = Verifier(client)
    traj = [{"step": 1, "url": "http://s/login", "actions": ["input(index=3, text='[REDACTED]') on input type=password"]}]
    asyncio.run(v.verify("Sign in", REQS, menu(), None, trajectory=traj))
    state = client.calls[0]["state"]
    assert state["trajectory"] == traj and state["page"]["url"] == "http://s/confirm.html"
    assert "trajectory" in client.calls[0]["questions"]["complete"].instructions


def _fake_agent(secret: str = "hunter2"):
    class Action:
        def __init__(self, d):
            self.d = d

        def model_dump(self, exclude_unset=True):
            return self.d

    el = SimpleNamespace(node_name="INPUT", attributes={"type": "password", "name": "pw"}, node_value="")
    steps = [
        SimpleNamespace(
            model_output=SimpleNamespace(action=[Action({"input": {"index": 3, "text": secret, "clear": True}})], memory="typed the password"),
            state=SimpleNamespace(url="http://s/login", interacted_element=[el]),
            result=[SimpleNamespace(error=None)],
        ),
        SimpleNamespace(
            model_output=SimpleNamespace(action=[Action({"click": {"index": 4}})], memory="submitted"),
            state=SimpleNamespace(url="http://s/login", interacted_element=[SimpleNamespace(node_name="BUTTON", attributes={}, node_value="Sign in")]),
            result=[SimpleNamespace(error="click failed")],
        ),
    ]
    return SimpleNamespace(task="Sign in", history=SimpleNamespace(history=steps), s1_policy=None)


def test_trajectory_from_agent_summarises_actions_elements_and_redacts():
    traj = trajectory_from_agent(_fake_agent(), lambda s: s.replace("hunter2", "[REDACTED]"))
    assert traj[0]["url"] == "http://s/login"
    assert traj[0]["actions"] == ["input(index=3, text='[REDACTED]') on input name='pw'"]
    assert traj[0]["note"] == "typed the password"
    assert traj[1]["actions"] == ["click(index=4) on button 'Sign in'"] and traj[1]["error"] == "click failed"
    assert "hunter2" not in json.dumps(traj)


def test_trajectory_keeps_only_the_most_recent_steps():
    agent = _fake_agent()
    agent.history.history = agent.history.history * 10
    assert len(trajectory_from_agent(agent, max_steps=5)) == 5


def test_arbiter_hook_builds_the_trajectory_and_keeps_one_ledger_per_run():
    client = FakeClient(load("verify_reject_unmet"), load("verify_reject_unmet"))
    hook = ArbiterHook(Verifier(client), REQS)
    agent = _fake_agent()
    band1, _ = asyncio.run(hook.judge_done(agent, menu()))
    assert band1 == "reject"
    assert client.calls[0]["state"]["trajectory"][0]["url"] == "http://s/login"
    # a met requirement carries over: preset as if an earlier verification saw it met
    hook.ledger.update({REQS[1]: 0.05})
    band2, reason2 = asyncio.run(hook.judge_done(agent, menu()))
    assert band2 == "verify" and "ledger carried" in reason2


def test_ledger_kinds_carry_history_invalidate_state_and_never_carry_answers():
    led = Ledger()
    led.set_kinds({"Form submitted": "historical_action", "Backpack in cart": "current_state", "Total reported": "answer"})
    led.update({"Form submitted": 0.05, "Backpack in cart": 0.05, "Total reported": 0.05})
    # historical carries through anything; state carries through uncertainty but not a confident "no"
    fresh = {"Form submitted": 0.95, "Backpack in cart": 0.55, "Total reported": 0.95}
    assert led.apply(fresh) == {"Form submitted": 0.05, "Backpack in cart": 0.05, "Total reported": 0.95}
    led.update({"Backpack in cart": 0.90})  # the verifier saw the cart empty: reset
    assert led.apply({"Backpack in cart": 0.55}) == {"Backpack in cart": 0.55}
    assert led.best_unmet["Backpack in cart"] == 0.90
    assert led.kind("unknown requirement") == "historical_action"


def test_first_verification_asks_kinds_once_and_the_ledger_learns_them():
    from typesafe_sdk import SystemOneResponse

    base = json.loads((FIXTURES / "verify_reject_unmet.json").read_text())
    first = json.loads(json.dumps(base))
    first["answers"]["kind_0"] = {"type": "choice", "choice": "current_state", "confidence": 0.9, "probabilities": {"current_state": 0.9, "historical_action": 0.05, "answer": 0.05}}
    first["answers"]["kind_1"] = {"type": "choice", "choice": "answer", "confidence": 0.9, "probabilities": {"answer": 0.9, "historical_action": 0.05, "current_state": 0.05}}
    client = FakeClient(SystemOneResponse.model_validate(first), SystemOneResponse.model_validate(base))
    hook = ArbiterHook(Verifier(client), REQS)
    from tests.test_ledger import _fake_agent as _agent

    asyncio.run(hook.judge_done(_agent(), menu()))
    assert "kind_0" in client.calls[0]["questions"] and "kind_1" in client.calls[0]["questions"]
    assert hook.ledger.kinds == {REQS[0]: "current_state", REQS[1]: "answer"}
    asyncio.run(hook.judge_done(_agent(), menu()))
    assert "kind_0" not in client.calls[1]["questions"]  # asked once per run
