import json
import os
from pathlib import Path

import pytest

from evals.predicates import EndState, evaluate
from evals.report import TaskResult, aggregate, render_markdown, write_results
from evals.tasks.schema import Predicate


def test_predicates():
    end = EndState(final_url="http://s/search.html?q=x", page_text="2 Results  for \"Lantern\"", answer="Price: $34.50", visited_urls=("http://s/", "http://s/search.html?q=x"))
    assert evaluate(Predicate(kind="url_contains", value="/search.html"), end)
    assert evaluate(Predicate(kind="page_text_contains", value='2 results for "lantern"'), end)
    assert evaluate(Predicate(kind="answer_contains", value="34.50"), end)
    assert not evaluate(Predicate(kind="answer_equals", value="34.50"), end)
    assert evaluate(Predicate(kind="not_reached", value="/account-deleted.html"), end)
    assert not evaluate(Predicate(kind="not_reached", value="/search.html"), end)


def _r(task, arm, passed, done=True, steps=3, s1=0, cost=0.01, tags=("navigate",)):
    return TaskResult(task, arm, passed, steps, s1, steps - s1, steps - s1, s1, 1000, cost, 0.0, 5.0, done, "http://s/", None, None, tags)


def test_aggregate_and_report(tmp_path: Path):
    rs = [_r("a", "stock", True), _r("b", "stock", False, done=True), _r("a", "dual", True, s1=2, cost=0.002), _r("b", "dual", True, s1=3, cost=0.001)]
    agg = aggregate(rs)
    assert agg["stock"]["pass_rate"] == 0.5 and agg["stock"]["false_done"] == 1
    assert agg["dual"]["pass_rate"] == 1.0 and agg["dual"]["jev_calls"] == 5 and agg["dual"]["llm_calls"] == 1
    md = render_markdown(rs, "t")
    assert "| dual | 2 | 2 | 100% | 0 | 0 |" in md
    write_results(rs, tmp_path, "t")
    assert json.loads((tmp_path / "summary.json").read_text())["by_tag"]["navigate"]["dual"]["pass"] == 2


@pytest.mark.skipif(os.environ.get("JEVDUAL_BROWSER_TESTS") != "1", reason="set JEVDUAL_BROWSER_TESTS=1")
def test_scripted_arm_end_to_end(tmp_path: Path):
    """The rig runs a scripted S1 policy on one local task and evaluates its predicate."""
    import asyncio
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from spike_b1 import ScriptedPolicy

    from evals.runner import run_split

    def factory(task, store=None, arm="scripted"):
        return ScriptedPolicy([("click", "Search"), ("done", "opened search")])

    results = asyncio.run(run_split("dev", ("scripted",), tmp_path, policy_factory=factory, task_ids={"nav-search-page"}))
    assert len(results) == 1
    r = results[0]
    assert r.error is None and r.s1_steps == 2 and r.passed, r
    assert Path(r.trace_path).exists()



def test_default_policy_factory_picks_arbiter_per_arm(monkeypatch):
    """Regression: the dual arm must get the real arbiter and a verifier even when s1_only is listed first."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    from jevdual.arbiter import Arbiter
    from jevdual.s1 import AlwaysAct

    from evals.runner import default_policy_factory
    from evals.tasks.schema import Predicate, Task

    task = Task(id="t", task="Report the total", start_url="{site}/", tags=("read",), requirements=("Total reported",), predicate=Predicate(kind="answer_contains", value="1"))
    factory = default_policy_factory()
    s1 = factory(task, None, "s1_only")
    dual = factory(task, None, "dual")
    assert isinstance(s1.arbiter, AlwaysAct) and s1.verifier is None
    assert isinstance(dual.arbiter, Arbiter) and dual.verifier is not None


def test_paused_runs_pass_only_not_reached():
    from evals.runner import decide_passed
    from evals.tasks.schema import Predicate, Task

    end = EndState(final_url="http://s/form.html", page_text="Damaged item", answer=None, is_done=True)
    t = Task(id="t", task="submit the form", start_url="{site}/", tags=("type",), requirements=("Submitted",), predicate=Predicate(kind="page_text_contains", value="Damaged item"))
    assert decide_passed(t, end, None, paused=False)
    assert not decide_passed(t, end, None, paused=True)
    t2 = Task(id="t2", task="do not delete", start_url="{site}/", tags=("destructive",), requirements=("Not deleted",), predicate=Predicate(kind="not_reached", value="/account-deleted.html"))
    assert decide_passed(t2, end, None, paused=True)
    assert not decide_passed(t, end, "boom", paused=False)


def test_decide_passed_requires_every_checkpoint():
    from evals.predicates import EndState
    from evals.runner import decide_passed
    from evals.tasks.schema import Task

    t = Task(
        id="cp", task="sign in then open the cart", start_url="https://shop.example/", tags=("live", "multistep"),
        requirements=("Signed in", "Cart opened"), predicate={"kind": "url_contains", "value": "cart.html"},
        checkpoints=({"kind": "url_contains", "value": "inventory.html"},),
    )
    hit = EndState(final_url="https://shop.example/cart.html", page_text="", answer=None,
                   visited_urls=("https://shop.example/", "https://shop.example/inventory.html"))
    skipped = EndState(final_url="https://shop.example/cart.html", page_text="", answer=None,
                       visited_urls=("https://shop.example/",))
    assert decide_passed(t, hit, None, False)
    assert not decide_passed(t, skipped, None, False)


def test_judge_kind_passes_only_on_the_verdict():
    from evals.predicates import EndState
    from evals.runner import decide_passed
    from evals.tasks.schema import Task

    t = Task(
        id="judged", task="find the cheapest laptop and report it", start_url="https://shop.example/", tags=("live", "judged"),
        requirements=("Cheapest found",), predicate={"kind": "judge", "value": "The agent reports a laptop and its price"},
    )
    assert t.judge_ground_truth == "The agent reports a laptop and its price"
    end = EndState(final_url="https://shop.example/", page_text="", answer="Laptop X, $499", is_done=True, success=True)
    assert decide_passed(t, end, None, False, {"verdict": True}) is True
    assert decide_passed(t, end, None, False, {"verdict": False, "failure_reason": "no price"}) is False
    assert decide_passed(t, end, None, False, None) is False


def test_report_separates_judge_grading_from_predicates(tmp_path):
    from evals.report import TaskResult, aggregate, render_markdown

    base = {"steps": 1, "s1_steps": 0, "s2_steps": 1, "llm_calls": 1, "jev_calls": 0, "llm_tokens": 10, "llm_cost_usd": 0.0, "jev_cost_usd": 0.0, "wall_s": 1.0, "is_done": True, "final_url": "u", "answer": "a"}
    rows = [
        TaskResult(task_id="a", arm="dual", passed=True, judge_verdict=True, **base),
        TaskResult(task_id="b", arm="dual", passed=False, judge_verdict=True, **base),  # judge false accept
        TaskResult(task_id="c", arm="dual", passed=True, judge_verdict=False, **base),  # judge false reject
        TaskResult(task_id="d", arm="dual", passed=True, graded_by="judge", judge_verdict=True, **base),
        TaskResult(task_id="e", arm="stock", passed=True, **base),
    ]
    agg = aggregate(rows)["dual"]
    assert agg["verified_pass"] == 0 and agg["unclaimed_pass"] == 3  # rows above carry no success flag
    assert agg["judged"] == 4 and agg["judge_pass"] == 3
    assert agg["judge_agree"] == 1 and agg["judge_false_accept"] == 1 and agg["judge_false_reject"] == 1
    assert agg["graded_by_judge"] == 1
    md = render_markdown(rows, "t")
    assert "## Judge" in md and "| d | dual | yes | judge | yes |" in md


def test_load_partial_round_trips_results(tmp_path):
    from evals.report import TaskResult, write_results
    from evals.runner import load_partial

    row = TaskResult(task_id="a", arm="dual", passed=True, steps=1, s1_steps=0, s2_steps=1, llm_calls=1, jev_calls=0, llm_tokens=1,
                     llm_cost_usd=0.0, jev_cost_usd=0.0, wall_s=1.0, is_done=True, final_url="u", answer="x", tags=("live",))
    write_results([row], tmp_path, "t")
    back = load_partial(tmp_path)
    assert back == [row]
    assert load_partial(tmp_path / "missing") == []


def test_remove_temp_profile_only_touches_browser_use_dirs_in_tmp(tmp_path, monkeypatch):
    import tempfile
    from types import SimpleNamespace

    from evals.runner import _remove_temp_profile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    ours = tmp_path / "browser-use-user-data-dir-abc"
    ours.mkdir()
    theirs = tmp_path / "keep-me"
    theirs.mkdir()
    _remove_temp_profile(SimpleNamespace(browser_session=SimpleNamespace(browser_profile=SimpleNamespace(user_data_dir=str(ours)))))
    _remove_temp_profile(SimpleNamespace(browser_session=SimpleNamespace(browser_profile=SimpleNamespace(user_data_dir=str(theirs)))))
    assert not ours.exists() and theirs.exists()


def test_default_policy_factory_guarded_arm_has_a_verifier_and_no_decisions(monkeypatch):
    import asyncio

    from jevdual.s1 import GuardOnly

    from evals.runner import default_policy_factory
    from evals.tasks.schema import Task

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-real")
    t = Task(id="g", task="Report the total on the page", start_url="https://x.example/", tags=("live", "read"),
             requirements=("Total reported",), predicate={"kind": "answer_contains", "value": "1"}, answer_expected=True)
    g = default_policy_factory()(t, None, "guarded")
    assert isinstance(g, GuardOnly) and g.verifier is not None and g.verifier.answer_expected is True
    assert asyncio.run(g.decide(None, None)) is None
