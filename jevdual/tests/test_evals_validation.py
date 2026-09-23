from evals.validation import consent_table, triage


def _r(task, arm, passed, **kw):
    base = {
        "task_id": task,
        "arm": arm,
        "passed": passed,
        "error": None,
        "tags": [],
        "judge_verdict": None,
        "answer": None,
        "final_url": None,
    }
    base.update(kw)
    return base


def test_triage_classes():
    rows = [
        _r("ok", "stock", True),
        _r("ok", "dual", False),
        _r("suspect", "stock", False, judge_verdict=True, answer="1889"),
        _r("suspect", "dual", False, judge_verdict=True, answer="1889"),
        _r("blocked", "stock", False, judge_verdict=False, judge_captcha=True),
        _r("blocked", "dual", False, judge_verdict=False, judge_impossible=True),
        _r("gone", "stock", False, judge_verdict=False, judge_reason="404"),
        _r("gone", "dual", False, judge_verdict=False),
        _r("crash", "stock", False, error="TimeoutError"),
        _r("crash", "dual", False, error="TimeoutError"),
    ]
    t = triage(rows)
    assert t["reachable"] == ["ok"]
    assert [x[0] for x in t["predicate_suspect"]] == ["suspect"]
    assert [x[0] for x in t["blocked"]] == ["blocked"]
    assert [x[0] for x in t["unreachable"]] == ["gone"]
    assert [x[0] for x in t["crashed"]] == ["crash"]


def test_consent_table_filters_by_tag():
    rows = [
        _r("c", "dual", True, tags=["live", "consent"], paused=True, is_done=True, success=False),
        _r("n", "dual", True),
    ]
    ct = consent_table(rows)
    assert len(ct) == 1 and ct[0]["task"] == "c" and ct[0]["paused"] is True
