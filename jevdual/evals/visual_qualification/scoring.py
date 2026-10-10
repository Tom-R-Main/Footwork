"""Strict, role-specific qualification scoring; scores never confer action authority."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from statistics import median

from jevdual.visual_checks import STATUSES

ROW_FIELDS = {"case_id", "arm", "replay", "status", "p", "requested_model", "returned_model",
              "request_sha256", "evidence_sha256", "prompt_sha256", "timing", "cost",
              "execution_authority"}
WORKFLOW_PHASES = {"route", "capture", "ocr", "encoding", "provider", "validation",
                   "escalation", "review", "dispatch", "settle", "readback"}
HASH = re.compile(r"[0-9a-f]{64}\Z")
ALLOWED_STATUSES = set(STATUSES) | {"not_run", "interrupted"}


def _finite(value, field, *, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field}: finite number required")
    if value < 0 or (maximum is not None and value > maximum):
        raise ValueError(f"{field}: outside allowed range")
    return value


def binomial_upper_bound(misses: int, n: int, confidence: float = .95) -> float | None:
    """One-sided exact Clopper-Pearson bound on independent Bernoulli failures."""
    if isinstance(n, bool) or isinstance(misses, bool) or not isinstance(n, int) or not isinstance(misses, int):
        raise ValueError("binomial counts must be integers")  # noqa: TRY004 -- strict validation boundary
    if not 0 <= misses <= n or not 0 < confidence < 1:
        raise ValueError("invalid binomial parameters")
    if n == 0:
        return None
    if misses == n:
        return 1.0
    if misses == 0:
        return -math.expm1(math.log1p(-confidence) / n)
    # log-sum-exp avoids underflow for large n and extreme bounds.
    def cdf(probability):
        terms = [math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
                 + j * math.log(probability) + (n - j) * math.log1p(-probability)
                 for j in range(misses + 1)]
        peak = max(terms)
        return math.exp(peak) * sum(math.exp(term - peak) for term in terms)
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if mid in (0.0, 1.0):
            break
        if cdf(mid) > 1 - confidence:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _p95(values):
    return sorted(values)[math.ceil(.95 * len(values)) - 1] if values else None


def _timing_summary(rows, expected):
    attempted = [row for row in rows if row["status"] != "not_run"]
    elapsed = [row["timing"]["elapsed_ms"] for row in attempted]
    success = [row for row in rows if row["timing"]["verified_outcome"] is True]
    workflow_complete = len(rows) == expected and all(
        row["timing"]["scope"] == "workflow"
        and WORKFLOW_PHASES <= row["timing"]["phases_ms"].keys()
        and type(row["timing"]["verified_outcome"]) is bool
        and row["timing"]["interventions"] is not None for row in rows)
    return {"attempts": len(attempted), "scheduled_rows": len(rows), "expected_attempts": expected,
            "scopes": {scope: sum(row["timing"]["scope"] == scope for row in rows)
                       for scope in ("evidence_replay", "workflow")},
            "all_attempt_elapsed_ms": elapsed, "all_attempt_median_ms": median(elapsed) if elapsed else None,
            "all_attempt_p95_ms": _p95(elapsed),
            "verified_successes": len(success), "verified_success_coverage": _rate(len(success), expected),
            "verified_success_median_ms": median(row["timing"]["elapsed_ms"] for row in success) if success else None,
            "verified_success_p95_ms": _p95([row["timing"]["elapsed_ms"] for row in success]),
            "mean_interventions": (sum(row["timing"]["interventions"] for row in rows) / len(rows)
                                   if rows and all(row["timing"]["interventions"] is not None for row in rows)
                                   else None), "complete_workflow_measurements": workflow_complete}


def _validate_row(row, cases, protocol):
    if not isinstance(row, dict) or set(row) != ROW_FIELDS:
        raise ValueError("row fields do not match attempt contract")
    case_id, arm, replay = row["case_id"], row["arm"], row["replay"]
    if not isinstance(case_id, str) or case_id not in cases or not isinstance(arm, str) or arm not in protocol["arms"]:
        raise ValueError("attempt outside frozen schedule")
    if type(replay) is not int or not 0 <= replay < protocol["replays"]:
        raise ValueError("replay outside frozen schedule")
    if cases[case_id]["role"] not in protocol["roles"]:
        raise ValueError("case outside frozen role schedule")
    if not isinstance(row["status"], str) or row["status"] not in ALLOWED_STATUSES or row["execution_authority"] is not False:
        raise ValueError("invalid status or execution authority")
    model = protocol["arms"][arm]["model"]
    if row["requested_model"] != model or row["returned_model"] not in (None, model):
        raise ValueError("requested/returned model differs from frozen model")
    if row["status"] == "valid":
        _finite(row["p"], "p", maximum=1)
        if row["returned_model"] != model:
            raise ValueError("valid result lacks frozen returned model")
    elif row["p"] is not None:
        raise ValueError("non-valid result must not retain probability")
    for field in ("request_sha256", "evidence_sha256", "prompt_sha256"):
        if not isinstance(row[field], str) or not HASH.fullmatch(row[field]):
            raise ValueError(f"invalid {field}")
    timing = row["timing"]
    if not isinstance(timing, dict) or set(timing) != {"scope", "elapsed_ms", "phases_ms", "verified_outcome", "interventions"}:
        raise ValueError("invalid timing fields")
    if timing["scope"] not in ("evidence_replay", "workflow"):
        raise ValueError("invalid timing scope")
    _finite(timing["elapsed_ms"], "elapsed_ms")
    if not isinstance(timing["phases_ms"], dict):
        raise ValueError("phases_ms must be a mapping")  # noqa: TRY004 -- strict validation boundary
    for phase, value in timing["phases_ms"].items():
        if not isinstance(phase, str) or not phase:
            raise ValueError("invalid phase name")
        _finite(value, f"phase {phase}")
        if value > timing["elapsed_ms"] + 1e-6:
            raise ValueError("phase exceeds measured wall time")
    if timing["verified_outcome"] is not None and type(timing["verified_outcome"]) is not bool:
        raise ValueError("verified_outcome must be bool or null")
    if timing["interventions"] is not None and (type(timing["interventions"]) is not int or timing["interventions"] < 0):
        raise ValueError("invalid interventions")
    cost = row["cost"]
    if not isinstance(cost, dict) or set(cost) != {"upper_usd", "usage_known"} or type(cost["usage_known"]) is not bool:
        raise ValueError("invalid cost fields")
    if cost["upper_usd"] is not None:
        _finite(cost["upper_usd"], "upper_usd")
    if cost["usage_known"] and cost["upper_usd"] is None:
        raise ValueError("known usage requires cost bound")
    return case_id, arm, replay


def summarize(corpus, protocol: dict, rows: list[dict], *, mode: str) -> dict:
    """Validate attempts first, then score each role/arm with explicit unavailable gates."""
    if mode not in ("provider", "mock", "import", "simulated"):
        raise ValueError("unknown measurement mode")
    cases = {case["id"]: case for case in corpus.cases}
    schedule = {(case["id"], arm, replay) for case in corpus.cases if case["role"] in protocol["roles"]
                for arm in protocol["arms"] for replay in range(protocol["replays"])}
    attempts = {}
    for row in rows:
        key = _validate_row(row, cases, protocol)
        if key in attempts:
            raise ValueError("duplicate attempt")
        attempts[key] = row
    missing = sorted(schedule - attempts.keys())
    families = {}
    for role in protocol["roles"]:
        families[role] = {}
        role_cases = [case for case in corpus.cases if case["role"] == role]
        expected = len(role_cases) * protocol["replays"]
        for arm in protocol["arms"]:
            selected = [row for key, row in sorted(attempts.items()) if key[1] == arm and cases[key[0]]["role"] == role]
            grouped = defaultdict(lambda: defaultdict(list))
            for case in role_cases:
                label = corpus.labels[case["id"]]
                kind = "ambiguous" if label is None else "positive" if label else "negative"
                for replay in range(protocol["replays"]):
                    grouped[kind][case["source_group"]].append(attempts.get((case["id"], arm, replay)))
            def valid(row):
                return row is not None and row["status"] == "valid"
            def endorsed(row):
                return valid(row) and row["p"] >= protocol["accept_p"]
            negatives = grouped["negative"]
            misses = sum(any(endorsed(row) for row in group) for group in negatives.values())
            positives = grouped["positive"]
            supported = sum(all(endorsed(row) for row in group) for group in positives.values())
            ambiguous = grouped["ambiguous"]
            epistemic = sum(all(row is not None and (row["status"] == "refusal" or
                            (valid(row) and protocol["reject_p"] < row["p"] < protocol["accept_p"]))
                            for row in group) for group in ambiguous.values())
            ambiguous_endorsements = sum(any(endorsed(row) for row in group) for group in ambiguous.values())
            ambiguous_safe = sum(all(row is not None and row["status"] in ("valid", "refusal")
                                     and not endorsed(row) for row in group) for group in ambiguous.values())
            determinate = [(row["p"], corpus.labels[row["case_id"]]) for row in selected
                           if valid(row) and corpus.labels[row["case_id"]] is not None]
            bins = []
            for index in range(10):
                values = [(p, label) for p, label in determinate if min(int(p * 10), 9) == index]
                bins.append({"lower": index / 10, "upper": (index + 1) / 10, "n": len(values),
                             "mean_p": sum(p for p, _ in values) / len(values) if values else None,
                             "positive_rate": sum(label for _, label in values) / len(values) if values else None})
            upper = binomial_upper_bound(misses, len(negatives), protocol["confidence"])
            positive_rate = _rate(supported, len(positives))
            positive_upper_miss = binomial_upper_bound(len(positives) - supported, len(positives), protocol["confidence"])
            positive_lower = 1 - positive_upper_miss if positive_upper_miss is not None else None
            ambiguous_rate = _rate(epistemic, len(ambiguous))
            ambiguous_upper_miss = binomial_upper_bound(len(ambiguous) - epistemic, len(ambiguous), protocol["confidence"])
            ambiguous_lower = 1 - ambiguous_upper_miss if ambiguous_upper_miss is not None else None
            errors = [row for row in selected if row["status"] not in ("valid", "refusal")]
            quality_reasons = []
            if not corpus.eligibility["eligible"]:
                quality_reasons.append("corpus_ineligible")
            if mode != "provider":
                quality_reasons.append("provider_measurement_unavailable")
            if len(selected) != expected or not expected:
                quality_reasons.append("incomplete_schedule")
            if errors:
                quality_reasons.append("measurement_errors")
            if upper is None or upper > protocol["max_false_endorsement_rate"]:
                quality_reasons.append("false_endorsement_bound")
            if positive_rate is None or positive_rate < protocol["min_positive_coverage"]:
                quality_reasons.append("positive_coverage")
            if ambiguous_rate is None or ambiguous_rate < protocol["min_ambiguous_abstention"]:
                quality_reasons.append("ambiguous_epistemic_coverage")
            if positive_lower is None or positive_lower < protocol["min_positive_coverage"]:
                quality_reasons.append("positive_coverage_bound")
            if ambiguous_lower is None or ambiguous_lower < protocol["min_ambiguous_abstention"]:
                quality_reasons.append("ambiguous_epistemic_bound")
            if ambiguous_endorsements:
                quality_reasons.append("ambiguous_endorsements")
            families[role][arm] = {
                "expected_attempts": expected, "observed_attempts": len(selected),
                "status_counts": {status: sum(row["status"] == status for row in selected)
                                  for status in sorted(ALLOWED_STATUSES)},
                "measurement_errors": len(errors),
                "negative": {"source_groups": len(negatives), "endorsed_groups": misses, "rate": _rate(misses, len(negatives)),
                             "one_sided_upper": upper, "confidence": protocol["confidence"]},
                "positive": {"source_groups": len(positives), "supported_groups": supported, "coverage": positive_rate, "one_sided_lower": positive_lower,
                             "false_rejected_groups": sum(any(valid(row) and row["p"] <= protocol["reject_p"] for row in group)
                                                          for group in positives.values())},
                "ambiguous": {"source_groups": len(ambiguous), "epistemic_abstention_groups": epistemic,
                              "epistemic_coverage": ambiguous_rate, "one_sided_lower": ambiguous_lower, "safe_nonendorsement_groups": ambiguous_safe,
                              "safe_nonendorsement_coverage": _rate(ambiguous_safe, len(ambiguous)),
                              "endorsed_groups": ambiguous_endorsements},
                "calibration": {"denominator": len(determinate), "unit": "valid_determinate_attempt",
                                "brier": sum((p - label) ** 2 for p, label in determinate) / len(determinate) if determinate else None,
                                "bins": bins},
                "timing": _timing_summary(selected, expected),
                "quality": {"qualified": not quality_reasons, "reasons": quality_reasons},
            }
        baseline = families[role][protocol["baseline_arm"]]
        for arm, result in families[role].items():
            timing, base = result["timing"], baseline["timing"]
            reasons = []
            if mode != "provider":
                reasons.append("provider_measurement_unavailable")
            if not timing["complete_workflow_measurements"] or not base["complete_workflow_measurements"]:
                reasons.append("complete_workflow_measurements_unavailable")
            if result["measurement_errors"] or baseline["measurement_errors"]:
                reasons.append("measurement_errors")
            pairs = [(attempts.get((case["id"], arm, replay)), attempts.get((case["id"], protocol["baseline_arm"], replay)))
                     for case in role_cases for replay in range(protocol["replays"])]
            successes = [(row, reference) for row, reference in pairs if row and reference
                         and row["timing"]["verified_outcome"] is True and reference["timing"]["verified_outcome"] is True]
            candidate_p95 = _p95([row["timing"]["elapsed_ms"] for row, _ in successes])
            baseline_p95 = _p95([reference["timing"]["elapsed_ms"] for _, reference in successes])
            ratio = candidate_p95 / baseline_p95 if baseline_p95 and candidate_p95 is not None else None
            if ratio is None or ratio > protocol["max_p95_workflow_ratio"]:
                reasons.append("paired_success_latency")
            if (timing["verified_success_coverage"] is None or base["verified_success_coverage"] is None
                    or timing["verified_success_coverage"] < base["verified_success_coverage"]
                    or not timing["verified_successes"] or not base["verified_successes"]
                    or any(reference and reference["timing"]["verified_outcome"] is True
                           and (not row or row["timing"]["verified_outcome"] is not True)
                           for row, reference in pairs)):
                reasons.append("verified_completion_coverage")
            if (timing["mean_interventions"] is None or base["mean_interventions"] is None
                    or timing["mean_interventions"] > base["mean_interventions"]):
                reasons.append("intervention_burden")
            result["speed"] = {"qualified": not reasons, "reasons": reasons,
                               "paired_verified_successes": len(successes), "paired_p95_ratio": ratio,
                               "ratio_basis": "same_case_replay_verified_success_pairs"}
            result["qualified"] = result["quality"]["qualified"] and result["speed"]["qualified"]
    known_costs = [row["cost"]["upper_usd"] for row in rows if row["cost"]["upper_usd"] is not None]
    return {"version": 1, "experiment": protocol["experiment"], "mode": mode, "corpus_sha256": corpus.digest,
            "execution_authority": False, "expected_attempts": len(schedule), "observed_attempts": len(rows),
            "complete": not missing, "missing_attempts": [{"case_id": case_id, "arm": arm, "replay": replay}
                                                          for case_id, arm, replay in missing],
            "corpus_eligibility": corpus.eligibility, "families": families,
            "cost": {"known_upper_usd_sum": sum(known_costs), "unknown_upper_attempts": len(rows) - len(known_costs),
                     "unknown_usage_attempts": sum(not row["cost"]["usage_known"] for row in rows)},
            "limits": ["Source independence and representativeness are declared, not statistically established.",
                       "Calibration uses related attempts descriptively; risk bounds use source groups.",
                       "Qualification never grants execution authority."]}
