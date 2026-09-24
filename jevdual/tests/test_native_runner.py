"""Native task schema, predicates and the runner over a fake Driver (no app is launched)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.desktop_s2 import ChatReply, NativeS2

from evals.native import runner as nr
from evals.native.predicates import NativeEndState, evaluate
from evals.native.schema import NativePredicate, NativeTask, load_tasks, parse_expect
from tests.test_desktop import FakeDriver, FakeHook, SeqPolicy, _decision, _ids

FIXTURE = Path(__file__).parent / "fixtures" / "native" / "calculator.json"
DEV = Path(__file__).parents[1] / "evals" / "native" / "tasks" / "dev.yaml"


def test_dev_split_loads_and_every_task_has_an_oracle():
    tasks = load_tasks(DEV)
    assert len(tasks) >= 7
    assert all(t.solve for t in tasks)
    assert all(t.bundle_id.startswith("com.apple.") for t in tasks)
    with pytest.raises(ValueError):
        NativeTask(
            id="x",
            task="do a thing now",
            app="A",
            bundle_id="b",
            tags=["click"],
            requirements=["r"],
            predicate=NativePredicate(kind="file_contains", value="v"),
            solve=["wait 0"],
        )


def test_predicates(tmp_path):
    (tmp_path / "a.txt").write_text("hello Second line.\n")
    end = NativeEndState(
        "12×11\n132", "the answer is 132", ("All Clear", "Equals"), True, tmp_path, "satisfied"
    )
    assert evaluate(NativePredicate(kind="window_text_contains", value="132"), end)
    assert evaluate(NativePredicate(kind="answer_contains", value="132"), end)
    assert not evaluate(NativePredicate(kind="answer_equals", value="132"), end)
    assert evaluate(NativePredicate(kind="file_contains", value="second line.", path="{tmp}/a.txt"), end)
    assert evaluate(NativePredicate(kind="file_exists", value="false", path="{tmp}/b.txt"), end)
    assert not evaluate(NativePredicate(kind="not_clicked", value="equals"), end)
    paused = NativeEndState("x", None, ("Cancel",), False, tmp_path, None)
    assert evaluate(NativePredicate(kind="not_clicked", value="Move to Trash"), paused)
    assert evaluate(NativePredicate(kind="expect", value="role=AXStaticText;label_contains=132"), end)
    assert not evaluate(NativePredicate(kind="expect", value="role=AXStaticText"), paused)
    assert parse_expect("role=AXStaticText; value_equals=72") == {
        "role": "AXStaticText",
        "value_equals": "72",
    }
    with pytest.raises(ValueError):
        parse_expect("colour=red")


class LaunchDriver(FakeDriver):
    """A fake Driver whose launch_app/list_apps/list_windows/kill_app exist."""

    def __init__(self, snapshot):
        super().__init__(snapshot)
        self.killed = []

    async def call_tool(self, name, args_json):
        if name == "launch_app":
            self.calls.append((name, json.loads(args_json)))
            return SimpleNamespace(text="launched", is_error=False, structured_json=json.dumps({"pid": 77}))
        if name == "kill_app":
            self.killed.append(json.loads(args_json)["pid"])
            return SimpleNamespace(text="killed", is_error=False)
        return await super().call_tool(name, args_json)

    async def list_apps(self, inp):
        return SimpleNamespace(apps=[SimpleNamespace(name="Calculator", pid=77)])

    async def list_windows(self, inp):
        return SimpleNamespace(
            windows=[
                SimpleNamespace(
                    window_id=5, title="Calculator", bounds=SimpleNamespace(width=300, height=400)
                )
            ]
        )


@pytest.fixture
def stub_sdk(monkeypatch):
    stub = SimpleNamespace(
        GetWindowStateInput=lambda **kw: kw,
        ClickInput=lambda **kw: kw,
        PressKeyInput=lambda **kw: kw,
        ListAppsInput=lambda: None,
        ListWindowsInput=lambda **kw: kw,
        ClickPosition=SimpleNamespace(ELEMENT=lambda element_token: ("element", element_token)),
        InputDeliveryMode=SimpleNamespace(BACKGROUND="background", FOREGROUND="foreground"),
        ActionTarget=SimpleNamespace(WINDOW=lambda pid, window_id: ("window", pid, window_id)),
    )
    monkeypatch.setitem(sys.modules, "cua_driver", stub)
    return stub


def _task(**kw):
    base = {
        "id": "calc-multiply",
        "task": "Clear the calculator, then compute 12 times 11 and leave the result on the display.",
        "app": "Calculator",
        "bundle_id": "com.apple.calculator",
        "tags": ["click"],
        "requirements": ["The display shows 132"],
        "predicate": {"kind": "window_text_contains", "value": "1,248"},  # the fixture's display
        "solve": ["click All Clear", "click 6", "click Equals"],
    }
    base.update(kw)
    return NativeTask(**base)


def test_oracle_replays_solve_and_grades(snapshot_json, stub_sdk, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    driver = LaunchDriver(snapshot_json)
    res = asyncio.run(nr.run_task(driver, _task(), "oracle", tmp_path / "out", None))
    assert res.passed and res.error is None and res.steps == 3
    assert driver.calls[0][0] == "launch_app" and driver.calls[0][1]["bundle_id"] == "com.apple.calculator"
    assert driver.killed == [77]
    assert "oracle" in res.tags
    trace = json.loads(Path(res.trace_path).read_text().splitlines()[0])
    assert trace["kind"] == "oracle" and [s["label"] for s in trace["steps"]] == ["All Clear", "6", "Equals"]


def test_oracle_reports_a_missing_label(snapshot_json, stub_sdk, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    res = asyncio.run(
        nr.run_task(LaunchDriver(snapshot_json), _task(solve=["click Nope"]), "oracle", tmp_path / "o", None)
    )
    assert not res.passed and res.error.startswith("oracle: no candidate")


@pytest.fixture
def snapshot_json():
    return json.loads(FIXTURE.read_text())


def _deps(policy, verifier=None, s2=None):
    from jevdual.arbiter import Arbiter

    return nr.Deps(
        policy_factory=lambda task: policy,
        verifier_factory=lambda task: verifier,
        s2_factory=lambda task, v: s2,
        arbiter_factory=Arbiter.from_toml,
        jev_model="jev-test",
        llm_model="muse-test",
    )


def test_s1_only_arm_writes_results_and_trace(snapshot_json, stub_sdk, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    ids = _ids(snapshot_json)
    policy = SeqPolicy(_decision("click", ids["6"]), _decision("done"))
    deps = _deps(policy, FakeHook("accept", "shows 1,248"))
    out = tmp_path / "out"
    res = asyncio.run(nr.run_task(LaunchDriver(snapshot_json), _task(), "s1_only", out, deps))
    assert (
        res.passed and res.is_done and res.s1_steps == 2 and res.jev_calls == 3
    )  # two decisions, one verification
    assert res.arm == "s1_only" and res.error is None and res.jev_cost_usd > 0
    lines = [json.loads(x) for x in Path(res.trace_path).read_text().splitlines()]
    assert (
        lines[0]["kind"] == "header" and lines[0]["backend"] == "cua-driver" and lines[0]["arm"] == "s1_only"
    )
    assert lines[1]["executed"][0]["params"]["label"] == "6"
    # results in the browser layout
    nr.write_results([res], out, "t")
    rows = json.loads((out / "results.json").read_text())
    assert rows[0]["task_id"] == "calc-multiply" and (out / "report.md").exists()


def test_guarded_arm_never_asks_system_one(snapshot_json, stub_sdk, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    ids = _ids(snapshot_json)
    policy = SeqPolicy()  # any S1 call would pop from an empty queue

    class Chat:
        def __init__(self):
            self.n = 0

        async def __call__(self, messages):
            self.n += 1
            body = (
                {"note": "six", "action": {"name": "click", "id": ids["6"]}}
                if self.n == 1
                else {"note": "ok", "action": {"name": "done", "answer": "", "success": True}}
            )
            return ChatReply(content=json.dumps(body), input_tokens=50, output_tokens=10)

    s2 = NativeS2(Chat())
    deps = _deps(policy, FakeHook("accept", "ok"), s2)
    res = asyncio.run(nr.run_task(LaunchDriver(snapshot_json), _task(), "guarded", tmp_path / "g", deps))
    assert res.passed and res.s2_steps == 2 and res.s1_steps == 0 and res.llm_calls == 2
    assert res.llm_tokens == 120 and res.llm_cost_usd > 0 and policy.calls == 0


def test_escalation_in_s1_only_is_an_error_row_not_a_crash(snapshot_json, stub_sdk, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    ids = _ids(snapshot_json)
    deps = _deps(SeqPolicy(_decision("click", ids["6"], tconf=0.1)))
    task = _task(predicate={"kind": "window_text_contains", "value": "999"})
    res = asyncio.run(nr.run_task(LaunchDriver(snapshot_json), task, "s1_only", tmp_path / "e", deps))
    assert not res.passed and res.error.startswith("escalated: target_confidence")


def test_launch_failure_is_a_crash_row(snapshot_json, stub_sdk, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(nr, "LAUNCH_TIMEOUT_S", 0.6)

    class NoWindow(LaunchDriver):
        async def list_windows(self, inp):
            return SimpleNamespace(windows=[])

    res = asyncio.run(nr.run_task(NoWindow(snapshot_json), _task(), "oracle", tmp_path / "c", None))
    assert not res.passed and res.error.startswith("crash: RuntimeError")
