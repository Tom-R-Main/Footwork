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

    def factory(task, store=None):
        return ScriptedPolicy([("click", "Search"), ("done", "opened search")])

    results = asyncio.run(run_split("dev", ("scripted",), tmp_path, policy_factory=factory, task_ids={"nav-search-page"}))
    assert len(results) == 1
    r = results[0]
    assert r.error is None and r.s1_steps == 2 and r.passed, r
    assert Path(r.trace_path).exists()
