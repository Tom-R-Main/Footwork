import json
from pathlib import Path

from evals.metrics import Step, auroc, escalation_summary, load_steps, reliability, render


def _write_trace(d: Path, run_id: str, arm: str, steps: list[dict]) -> None:
    (d / "traces").mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"kind": "header", "run_id": run_id, "arm": arm, "task": "t"})]
    for s in steps:
        lines.append(json.dumps({"run_id": run_id, **s}))
    (d / "traces" / f"{run_id}.jsonl").write_text("\n".join(lines) + "\n")


def _dec(op_conf: float, nouls: dict | None = None) -> dict:
    return {"operation": {"choice": "click", "confidence": op_conf, "probabilities": {}}, "target": None, "nouls": nouls or {}}


def test_escalation_summary_counts_only_s1_eligible_steps(tmp_path: Path):
    _write_trace(
        tmp_path, "task-a-dual-1", "dual",
        [
            {"step": 1, "system": "s1", "decision": _dec(1.0), "arbiter_reason": "act: operation 1.00", "executed": [{"name": "click"}]},
            {"step": 2, "system": "s2", "decision": _dec(0.47), "arbiter_reason": "operation_confidence: 0.47 < 0.55", "executed": []},
            {"step": 3, "system": "s2", "decision": _dec(0.9, {"needs_reasoning": 0.9}), "arbiter_reason": "needs_reasoning: 0.9 >= 0.6", "executed": []},
            {"step": 4, "system": "s2", "decision": None, "arbiter_reason": None, "executed": []},  # no decision: not eligible
        ],
    )
    _write_trace(tmp_path, "task-a-stock-1", "stock", [{"step": 1, "system": "s2", "decision": None, "executed": []}])
    steps = load_steps(tmp_path)
    assert {s.arm for s in steps} == {"dual", "stock"}
    assert steps[0].task_id == "task-a"
    s = escalation_summary(steps, "dual")
    assert (s.steps, s.s1_eligible, s.escalated, s.acted) == (4, 3, 2, 1)
    assert abs(s.escalation_rate - 2 / 3) < 1e-9
    assert s.by_reason == {"operation_confidence": 1, "needs_reasoning": 1}
    assert s.conf_below_095 == 2 and s.conf_below_055 == 1
    assert s.noul_binding == {"needs_reasoning": 1}
    md = render(s, escalation_summary(steps, "dual"))
    assert "Escalation rate ratio (this / baseline): 1.00" in md


def test_reliability_and_ece():
    perfect = [(0.95, True)] * 19 + [(0.95, False)] + [(0.05, False)] * 19 + [(0.05, True)]
    r = reliability(perfect, bins=10)
    assert r["n"] == 40 and len(r["bins"]) == 2
    assert r["ece"] < 0.01
    overconfident = [(0.99, False)] * 10
    assert reliability(overconfident)["ece"] > 0.98


def test_auroc_known_values():
    assert auroc([(0.9, True), (0.8, True), (0.2, False), (0.1, False)]) == 1.0
    assert auroc([(0.1, True), (0.2, True), (0.8, False), (0.9, False)]) == 0.0
    assert auroc([(0.5, True), (0.5, False)]) == 0.5
    assert auroc([(0.5, True)]) is None


def test_step_dataclass_defaults():
    s = Step("t", "dual", 1, "s1", "click", 1.0, 1.0, {}, "act", ["click"], False, None)
    assert s.op_conf == 1.0
