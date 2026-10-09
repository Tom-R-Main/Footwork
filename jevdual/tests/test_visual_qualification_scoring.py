"""Qualification fails on unsafe, incomplete, dependent or simulated evidence."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from evals.visual_qualification.scoring import WORKFLOW_PHASES, binomial_upper_bound, summarize


@pytest.fixture
def protocol():
    return {"version": 1, "experiment": "VQ1", "roles": ["document_reference_match"],
            "arms": {"jev_text": {"model": "jev", "capability": "text"},
                     "visual": {"model": "visual-model", "capability": "image"}},
            "replays": 1, "seed": 1, "accept_p": .9, "reject_p": .1, "confidence": .95,
            "max_false_endorsement_rate": .01, "min_positive_coverage": .8,
            "min_ambiguous_abstention": .95, "max_p95_workflow_ratio": 1.1,
            "baseline_arm": "jev_text", "max_calls": 1000, "max_reserved_cost_usd": 100,
            "reservation_usd_per_attempt": .01, "deadline_s": 10}


def corpus_for(labels, groups=None, eligible=True):
    return SimpleNamespace(manifest={}, digest="a" * 64,
                           cases=[{"id": f"c{index}", "role": "document_reference_match",
                                   "source_group": groups[index] if groups else f"g{index}",
                                   "input": {}, "provenance": {}}
                                  for index in range(len(labels))],
                           labels={f"c{index}": label for index, label in enumerate(labels)},
                           eligibility={"eligible": eligible, "reasons": [] if eligible else ["synthetic"]})


def rows_for(corpus, protocol, scope="workflow"):
    rows = []
    for case in corpus.cases:
        label = corpus.labels[case["id"]]
        for arm, config in protocol["arms"].items():
            for replay in range(protocol["replays"]):
                rows.append({"case_id": case["id"], "arm": arm, "replay": replay,
                             "status": "valid", "p": .99 if label is True else .01 if label is False else .5,
                             "requested_model": config["model"], "returned_model": config["model"],
                             "request_sha256": "a" * 64, "evidence_sha256": "b" * 64,
                             "prompt_sha256": "c" * 64, "execution_authority": False,
                             "timing": {"scope": scope, "elapsed_ms": 100,
                                        "phases_ms": dict.fromkeys(WORKFLOW_PHASES, 1),
                                        "verified_outcome": True, "interventions": 0},
                             "cost": {"upper_usd": .01, "usage_known": True}})
    return rows


def family(corpus, protocol, rows, mode="provider"):
    return summarize(corpus, protocol, rows, mode=mode)["families"]["document_reference_match"]["visual"]


def test_exact_bound_general_and_empty():
    assert binomial_upper_bound(0, 0) is None
    assert binomial_upper_bound(0, 300) == pytest.approx(.0099360819444577)
    assert binomial_upper_bound(1, 2) == pytest.approx(.9746794344808963)
    assert binomial_upper_bound(2, 2) == 1
    assert binomial_upper_bound(100, 1000) > .1
    with pytest.raises(ValueError):
        binomial_upper_bound(-1, 3)


def test_independent_complete_provider_can_qualify_but_never_authorize(protocol):
    corpus = corpus_for([False] * 300 + [True] * 14 + [None] * 59)
    report = summarize(corpus, protocol, rows_for(corpus, protocol), mode="provider")
    result = report["families"]["document_reference_match"]["visual"]
    assert result["qualified"]
    assert not report["execution_authority"]
    assert result["negative"]["source_groups"] == 300
    assert result["calibration"]["denominator"] == 314
    assert sum(item["n"] for item in result["calibration"]["bins"]) == 314
    assert result["calibration"]["brier"] == pytest.approx(.0001)


@pytest.mark.parametrize("mode", ["mock", "import", "simulated"])
def test_simulated_or_imported_measurement_never_qualifies(protocol, mode):
    corpus = corpus_for([False] * 300 + [True, None])
    result = family(corpus, protocol, rows_for(corpus, protocol), mode)
    assert not result["qualified"]
    assert "provider_measurement_unavailable" in result["quality"]["reasons"]


def test_all_abstain_not_useful(protocol):
    corpus = corpus_for([False] * 300 + [True, None])
    rows = rows_for(corpus, protocol)
    for row in rows:
        row["status"], row["p"] = "refusal", None
    result = family(corpus, protocol, rows)
    assert not result["quality"]["qualified"]
    assert result["positive"]["coverage"] == 0
    assert result["ambiguous"]["epistemic_coverage"] == 1
    assert result["calibration"]["denominator"] == 0


def test_high_confident_wrong_and_ambiguous_endorsement(protocol):
    corpus = corpus_for([False] * 300 + [True, None])
    rows = rows_for(corpus, protocol)
    for row in rows:
        if row["arm"] == "visual" and row["case_id"] in ("c0", "c301"):
            row["p"] = .99
    result = family(corpus, protocol, rows)
    assert result["negative"]["endorsed_groups"] == 1
    assert "false_endorsement_bound" in result["quality"]["reasons"]
    assert result["ambiguous"]["endorsed_groups"] == 1
    assert "ambiguous_endorsements" in result["quality"]["reasons"]


def test_related_variants_and_replays_not_independent(protocol):
    protocol["replays"] = 3
    corpus = corpus_for([False] * 300 + [True, None], ["one-source"] * 300 + ["positive", "ambiguous"])
    rows = rows_for(corpus, protocol)
    result = family(corpus, protocol, rows)
    assert result["negative"]["source_groups"] == 1
    assert result["negative"]["one_sided_upper"] == pytest.approx(.95)
    assert not result["qualified"]
    rows[3]["p"] = .99
    assert family(corpus, protocol, rows)["negative"]["endorsed_groups"] == 1


@pytest.mark.parametrize("status,p,epistemic,safe", [
    ("valid", .01, 0, 1), ("valid", .5, 1, 1), ("refusal", None, 1, 1),
    ("invalidated", None, 0, 0), ("error", None, 0, 0), ("timeout", None, 0, 0),
])
def test_ambiguity_distinguishes_error_conservatism_and_epistemic(protocol, status, p, epistemic, safe):
    corpus = corpus_for([False, True, None])
    rows = rows_for(corpus, protocol)
    for row in rows:
        if row["case_id"] == "c2":
            row["status"], row["p"] = status, p
    result = family(corpus, protocol, rows)
    assert result["ambiguous"]["epistemic_abstention_groups"] == epistemic
    assert result["ambiguous"]["safe_nonendorsement_groups"] == safe
    if status not in ("valid", "refusal"):
        assert "measurement_errors" in result["quality"]["reasons"]


def test_missing_attempt_does_not_become_abstention(protocol):
    corpus = corpus_for([False, True, None])
    rows = rows_for(corpus, protocol)[:-1]
    report = summarize(corpus, protocol, rows, mode="provider")
    assert not report["complete"]
    assert report["missing_attempts"] == [{"case_id": "c2", "arm": "visual", "replay": 0}]
    result = report["families"]["document_reference_match"]["visual"]
    assert result["ambiguous"]["epistemic_coverage"] == 0
    assert "incomplete_schedule" in result["quality"]["reasons"]


def test_duplicate_and_outside_schedule_refused(protocol):
    corpus = corpus_for([False])
    rows = rows_for(corpus, protocol)
    with pytest.raises(ValueError, match="duplicate"):
        summarize(corpus, protocol, rows + [deepcopy(rows[0])], mode="provider")
    rows[0]["replay"] = 1
    with pytest.raises(ValueError, match="schedule"):
        summarize(corpus, protocol, rows, mode="provider")


@pytest.mark.parametrize("path,value", [
    (("p",), float("nan")), (("p",), float("inf")), (("p",), -1), (("p",), True),
    (("timing", "elapsed_ms"), float("nan")), (("timing", "elapsed_ms"), -1),
    (("timing", "phases_ms", "capture"), float("inf")), (("timing", "interventions"), True),
    (("cost", "upper_usd"), float("nan")), (("execution_authority",), True),
    (("requested_model",), "different"), (("returned_model",), "different"),
    (("request_sha256",), "bad"),
])
def test_invalid_attempt_refused_before_metrics(protocol, path, value):
    corpus = corpus_for([False])
    rows = rows_for(corpus, protocol)
    container = rows[0]
    for key in path[:-1]:
        container = container[key]
    container[path[-1]] = value
    with pytest.raises(ValueError):
        summarize(corpus, protocol, rows, mode="provider")


def test_stale_probability_refused(protocol):
    corpus = corpus_for([False])
    rows = rows_for(corpus, protocol)
    rows[0]["status"] = "invalidated"
    with pytest.raises(ValueError, match="probability"):
        summarize(corpus, protocol, rows, mode="provider")


@pytest.mark.parametrize("scope", ["evidence_replay", "mixed", "missing_phase"])
def test_replay_mixed_or_partial_workflow_not_speed_qualified(protocol, scope):
    corpus = corpus_for([False] * 300 + [True] * 14 + [None] * 59)
    rows = rows_for(corpus, protocol)
    if scope == "evidence_replay":
        for row in rows:
            row["timing"]["scope"] = "evidence_replay"
    elif scope == "mixed":
        rows[1]["timing"]["scope"] = "evidence_replay"
    else:
        del rows[1]["timing"]["phases_ms"]["readback"]
    result = family(corpus, protocol, rows)
    assert result["quality"]["qualified"]
    assert not result["speed"]["qualified"]
    assert "complete_workflow_measurements_unavailable" in result["speed"]["reasons"]


def test_attempts_failures_and_interventions_retained(protocol):
    corpus = corpus_for([False] * 300 + [True, None])
    rows = rows_for(corpus, protocol)
    rows[1]["timing"].update(elapsed_ms=10000, verified_outcome=False, interventions=2)
    result = family(corpus, protocol, rows)
    assert 10000 in result["timing"]["all_attempt_elapsed_ms"]
    assert result["timing"]["verified_successes"] == 301
    assert not result["speed"]["qualified"]
    assert "verified_completion_coverage" in result["speed"]["reasons"]
    assert "intervention_burden" in result["speed"]["reasons"]


def test_unknown_cost_is_explicit(protocol):
    corpus = corpus_for([False])
    rows = rows_for(corpus, protocol)
    rows[0]["cost"] = {"upper_usd": None, "usage_known": False}
    report = summarize(corpus, protocol, rows, mode="provider")
    assert report["cost"]["unknown_upper_attempts"] == 1
    assert report["cost"]["unknown_usage_attempts"] == 1
    assert report["cost"]["known_upper_usd_sum"] == .01


def test_extra_easy_successes_cannot_hide_paired_slowdown(protocol):
    corpus = corpus_for([False] * 300 + [True, None])
    rows = rows_for(corpus, protocol)
    for row in rows:
        common = int(row['case_id'][1:]) < 5
        if row['arm'] == 'jev_text':
            row['timing']['verified_outcome'] = common
            row['timing']['elapsed_ms'] = 100
        else:
            row['timing']['elapsed_ms'] = 1000 if common else 1
    result = family(corpus, protocol, rows)
    assert result['speed']['paired_p95_ratio'] == 10
    assert not result['speed']['qualified']
    assert 'paired_success_latency' in result['speed']['reasons']


def test_phase_cannot_exceed_measured_wall_time_on_import(protocol):
    corpus = corpus_for([False, True, None])
    rows = rows_for(corpus, protocol)
    rows[0]['timing']['phases_ms']['provider'] = 10_000
    with pytest.raises(ValueError, match='phase exceeds measured wall time'):
        summarize(corpus, protocol, rows, mode='provider')


def test_one_positive_and_one_ambiguity_cannot_qualify_coverage(protocol):
    corpus = corpus_for([False] * 300 + [True, None])
    result = family(corpus, protocol, rows_for(corpus, protocol))
    assert not result['quality']['qualified']
    assert 'positive_coverage_bound' in result['quality']['reasons']
    assert 'ambiguous_epistemic_bound' in result['quality']['reasons']
