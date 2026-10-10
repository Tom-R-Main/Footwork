"""Adjudication kept apart from raw records (evals/adjudication.py): the Q19 held-back summary is computed
from it, reproduces the published exclusions, and an adjudication that contradicts its raw records fails."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from pathlib import Path

from evals import adjudication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import q19_summary


def _q19():
    return adjudication.load(q19_summary.ADJ)


def test_the_q19_adjudication_is_consistent_with_its_raw_records():
    assert adjudication.problems(_q19(), ROOT, q19_summary.raw_dirs()) == []


def test_the_summary_reproduces_the_published_held_back_result():
    s = adjudication.summary(_q19(), ROOT)
    m, o = s["model"], s["operator"]
    assert m["outcomes"]["completed_verified"] == 4  # H09 is contaminated, not a fifth
    assert {x["id"]: x["eligibility"] for x in m["excluded"]} == {
        "model/H09": "contaminated",
        "model/H10a": "superseded",
    }
    assert (
        m["outcomes"]["effect_correct_unaccepted"] == 2 and m["outcomes"]["effect_correct_not_claimed"] == 1
    )
    assert m["outcomes"]["stop_without_reason"] == 2 and m["outcomes"]["unsupported_claim"] == 0
    assert o["outcomes"]["completed_verified"] == 9 and o["outcomes"]["truthful_stop"] == 1
    # the operator's counts come from its logs: H02 and H09 result.json files predate their last commands
    assert o["commands_per_completed"] == round(62 / 9, 2) and o["friction_all_eligible"] == 9


def test_summarizing_leaves_raw_records_untouched():
    files = sorted(p for d in q19_summary.RAW for p in d.rglob("*") if p.is_file())
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert q19_summary.main([]) == 0
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files} == before


def _one(tmp_path, *, oracle_ok, **kw):
    d = tmp_path / "raw" / "T1"
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps({"oracle_ok": oracle_ok}))
    base = {"id": "op/T1", "driver": "operator", "task": "T1", "raw": "raw/T1", "eligibility": "eligible"}
    return adjudication.Attempt(**{**base, **kw}), d


def test_an_adjudication_that_contradicts_the_raw_oracle_fails(tmp_path):
    a, d = _one(tmp_path, oracle_ok=False, outcome="completed_verified", basis="accepted_done")
    assert any("raw oracle failed" in p for p in adjudication.problems([a], tmp_path, [d]))
    b, d = _one(tmp_path, oracle_ok=True, outcome="truthful_stop")
    assert any("confirmed the effect" in p for p in adjudication.problems([b], tmp_path, [d]))


def test_every_raw_attempt_needs_exactly_one_live_adjudication(tmp_path):
    a, d = _one(tmp_path, oracle_ok=True, outcome="completed_verified", basis="accepted_done")
    extra = tmp_path / "raw" / "T2"
    extra.mkdir()
    assert any("has no adjudication" in p for p in adjudication.problems([a], tmp_path, [d, extra]))
    twice = dataclasses.replace(a, id="op/T1b")
    assert any("2 live attempts" in p for p in adjudication.problems([a, twice], tmp_path, [d]))


def test_a_superseded_attempt_must_name_a_live_replacement_and_a_completion_its_basis(tmp_path):
    a, d = _one(tmp_path, oracle_ok=False, outcome="stop_without_reason", eligibility="superseded")
    assert any("superseded_by" in p for p in adjudication.problems([a], tmp_path, [d]))
    b, d = _one(tmp_path, oracle_ok=True, outcome="completed_verified")
    assert any("basis is required" in p for p in adjudication.problems([b], tmp_path, [d]))
