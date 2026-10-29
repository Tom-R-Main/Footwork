"""The SDK's foreground intent and exact native key checks form one boundary."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from jevdual.native import NativeBridge
from jevdual.posture import ExecutionPolicy

from tests.test_posture import Activity, FakeAX, FakeDriver, _ok, _refused, doc_snapshot


class GuardedActivity(Activity):
    def __init__(self):
        super().__init__()
        self.current = 77
        self.stale_guard = True

    def frontmost_pid(self):
        return self.current

    def activate(self, pid):
        self.activated.append(pid)
        self.current = 77 if pid == 1 and self.stale_guard else pid
        return True


class IntentDriver(FakeDriver):
    def __init__(self, activity, result=None):
        super().__init__(doc_snapshot(""))
        self.activity = activity
        self.result = result

    async def call_tool(self, name, arguments):
        args = json.loads(arguments)
        self.calls.append((name, args))
        assert name == "bring_to_front"
        assert args == {"pid": 1, "window_id": 2, "session": "owned-intent"}
        if isinstance(self.result, Exception):
            raise self.result
        if self.result is not None:
            return self.result
        self.activity.stale_guard = False
        return SimpleNamespace(action=None, is_error=False, error_code=None, structured_json=None)


def exercise(result=None, *, mode="foreground_permitted", clear_guard=False):
    activity, ax = GuardedActivity(), FakeAX("")
    if clear_guard:
        activity.stale_guard = False
    driver = IntentDriver(activity, result)
    bridge = NativeBridge(
        driver, 1, 2, ax=ax, session="owned-intent", policy=ExecutionPolicy(mode, activity=activity)
    )

    async def invoke():
        return await bridge.menu(await bridge.observe(), ["File", "Open"])

    return asyncio.run(invoke()), driver, activity, ax


def test_foreground_intent_ends_same_process_guard_before_native_activation():
    effect, driver, activity, ax = exercise()
    assert effect.dispatched and ax.pressed == (["File", "Open"],)
    assert driver.names() == ["bring_to_front"]
    assert activity.stale_guard is False


@pytest.mark.parametrize(
    "result",
    [
        _refused("exact activation refused"),
        _ok(effect="REFUSED"),
        RuntimeError("foreground intent unavailable"),
        SimpleNamespace(
            action=None,
            is_error=False,
            error_code=None,
            structured_json=json.dumps({"pid": 1, "window_id": 999, "activated": True}),
        ),
    ],
)
def test_refused_or_wrong_window_intent_stops_before_native_input(result):
    effect, driver, activity, ax = exercise(result)
    assert not effect.dispatched
    assert driver.names() == ["bring_to_front"]
    assert activity.activated == [] and ax.pressed == ()


def test_unknown_intent_ack_requires_actual_exact_foreground_check():
    effect, _, _, ax = exercise(_ok())  # No cancellation; native activation remains ineffective.
    assert not effect.dispatched and effect.error_code == "not_key"
    assert ax.pressed == ()


def test_posture_refusal_precedes_foreground_intent():
    effect, driver, activity, ax = exercise(mode="background_only")
    assert not effect.dispatched and driver.names() == []
    assert activity.activated == [] and ax.pressed == ()


def test_exact_verified_activation_code_is_success_metadata_not_an_error():
    payload = {
        "status": "activated",
        "code": "bring_to_front_exact_window_verified",
        "request_accepted": True,
        "pid": 1,
        "window_id": 2,
        "exact_window_effect": {"verified": True},
        "observed": {"focused_window_id": 2, "frontmost_pid": 1},
    }
    result = SimpleNamespace(
        action=None, is_error=False, error_code=payload["code"], structured_json=json.dumps(payload)
    )
    effect, _driver, _, ax = exercise(result, clear_guard=True)
    assert effect.dispatched and ax.pressed == (["File", "Open"],)
