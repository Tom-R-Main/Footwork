from evals.paired import bootstrap_mean_ci, compare


def _r(task, passed, steps, cost, unv=0):
    return {
        "task_id": task,
        "passed": passed,
        "steps": steps,
        "llm_calls": steps,
        "jev_calls": 0,
        "cost": cost,
        "wall_s": 10.0 * steps,
        "unverified": unv,
    }


def test_compare_pairs_on_common_tasks_and_reports_direction():
    a = {t["task_id"]: t for t in [_r("x", 1, 6, 0.02, 1), _r("y", 0, 8, 0.03, 1), _r("only_a", 1, 1, 0.0)]}
    b = {t["task_id"]: t for t in [_r("x", 1, 3, 0.01, 0), _r("y", 1, 4, 0.02, 0), _r("only_b", 1, 1, 0.0)]}
    res = compare(a, b)
    assert res["n"] == 2 and res["only_a"] == ["only_a"] and res["only_b"] == ["only_b"]
    assert res["fields"]["steps"]["mean_diff"] == -3.5 and res["fields"]["steps"]["b_better"] == 2
    assert res["fields"]["passed"]["b_better"] == 1 and res["fields"]["unverified"]["b_total"] == 0


def test_bootstrap_ci_brackets_the_mean():
    lo, hi = bootstrap_mean_ci([1.0, 2.0, 3.0, 4.0], n=500)
    assert lo <= 2.5 <= hi and lo >= 1.0 and hi <= 4.0
