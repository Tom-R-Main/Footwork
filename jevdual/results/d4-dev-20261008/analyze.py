"""Recount frozen D4 receipts without provider calls. Run from this directory."""

import json
from pathlib import Path

root = Path(__file__).resolve().parent
rows = json.loads((root / "results.json").read_text())
summary = json.loads((root / "summary.json").read_text())
analysis = {"attempts": len(rows), "arms": {}}
for arm, recorded in summary["arms"].items():
    selected = [r for r in rows if r["arm"] == arm]
    groups = {case: [r for r in selected if r["id"] == case] for case in sorted({r["id"] for r in selected})}
    correct = [case for case, replay in groups.items() if len(replay) == 3 and all(r["correct"] for r in replay)]
    invalid = [case for case, replay in groups.items() if replay[0]["expected"] is False and any(r["band"] == "true" for r in replay)]
    supported = [case for case in correct if groups[case][0]["expected"] is True]
    ambiguous = [r for r in selected if r["expected"] is None]
    wrong = [r["id"] for r in selected if r.get("execution", {}).get("wrong_effect")]
    assert correct == recorded["all_three_correct"]
    assert invalid == recorded["invalid_confident_positive"]
    assert supported == recorded["supported_all_three"]
    assert wrong == recorded["wrong_effects"]
    analysis["arms"][arm] = {
        "correct_replays": sum(r["correct"] for r in selected),
        "all_three_correct": correct,
        "invalid_accepted_cases": invalid,
        "supported_all_three": supported,
        "ambiguous_bands": {band: sum(r["band"] == band for r in ambiguous) for band in ("true", "false", "unknown")},
        "wrong_effects": wrong,
        "original_counterexample_probabilities": [r["probability"] for r in selected if r["id"] == "G02"],
        "input_tokens": sum(r["budget"]["input_tokens"] for r in selected),
        "cost_usd": sum(r["budget"]["charged_upper_usd"] for r in selected),
        "request_timing": recorded["request_timing"],
        "capture_to_judgment_estimate": recorded["capture_to_judgment_estimate"],
    }
assert len(rows) == 108 and all(r["budget"]["usage_known"] for r in rows)
assert len([r for r in rows if "execution" in r]) == 36
analysis["d4_cost_usd"] = sum(r["budget"]["charged_upper_usd"] for r in rows)
analysis["cumulative_reported_estimate_usd"] = 0.075117722 + analysis["d4_cost_usd"]
analysis["cumulative_upper_usd"] = 0.215917722 + analysis["d4_cost_usd"]
analysis["verdict"] = "inconclusive_original_failure_did_not_reproduce"
(root / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
print(json.dumps({k: v for k, v in analysis.items() if k != "arms"}, indent=2))
