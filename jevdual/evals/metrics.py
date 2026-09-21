"""Q6/Q1 metrics over trace files: escalation from S1-eligible steps, confidence distribution,
reliability (ECE) and AUROC. No dependencies beyond the standard library.

    uv run python -m evals.metrics results/<live run> [--baseline results/<fixture run>]

A step is *S1-eligible* when the trace holds a Jev decision for it (the S1 policy was consulted);
it *escalated* when that step still ran on System 2. Stock steps have no decision and are ignored.
Calibration needs labels (step right or wrong); ``reliability`` and ``auroc`` take (score, label)
pairs and are used once Q6's labels exist.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Step:
    task_id: str
    arm: str
    step: int
    system: str
    op_choice: str | None
    op_conf: float | None
    target_conf: float | None
    nouls: dict[str, float]
    reason: str | None
    executed: list[str]
    is_done: bool
    result_error: str | None


def load_steps(run_dir: Path) -> list[Step]:
    out: list[Step] = []
    for f in sorted((run_dir / "traces").glob("*.jsonl")):
        arm = None
        task_id = None
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "header":
                arm = r["arm"]
                task_id = r["run_id"].rsplit("-", 2)[0]
                continue
            d = r.get("decision") or {}
            op = d.get("operation") or {}
            tg = d.get("target") or {}
            out.append(
                Step(
                    task_id=task_id or f.stem,
                    arm=arm or "?",
                    step=r["step"],
                    system=r["system"],
                    op_choice=op.get("choice"),
                    op_conf=op.get("confidence") if d else None,
                    target_conf=tg.get("confidence") if tg else None,
                    nouls=d.get("nouls") or {},
                    reason=r.get("arbiter_reason"),
                    executed=[a["name"] for a in r.get("executed") or []],
                    is_done=bool(r.get("is_done")),
                    result_error=r.get("result_error"),
                )
            )
    return out


def reason_class(reason: str | None) -> str:
    if not reason:
        return "none"
    head = reason.split(":", 1)[0].strip()
    return head or "none"


@dataclass
class EscalationSummary:
    arm: str
    steps: int
    s1_eligible: int
    escalated: int
    acted: int
    by_reason: dict[str, int] = field(default_factory=dict)
    conf_below_095: int = 0
    conf_below_055: int = 0
    conf_missing: int = 0
    noul_binding: dict[str, int] = field(default_factory=dict)

    @property
    def escalation_rate(self) -> float:
        return self.escalated / self.s1_eligible if self.s1_eligible else 0.0

    @property
    def frac_conf_below_095(self) -> float:
        n = self.s1_eligible - self.conf_missing
        return self.conf_below_095 / n if n else 0.0


NOUL_FLOORS = {"goal_done": 0.85, "stuck": 0.85, "needs_reasoning": 0.6, "destructive": 0.5}


def escalation_summary(steps: list[Step], arm: str = "dual") -> EscalationSummary:
    rows = [s for s in steps if s.arm == arm]
    eligible = [s for s in rows if s.op_choice is not None]
    esc = [s for s in eligible if s.system == "s2"]
    summary = EscalationSummary(arm=arm, steps=len(rows), s1_eligible=len(eligible), escalated=len(esc), acted=len(eligible) - len(esc))
    summary.by_reason = dict(Counter(reason_class(s.reason) for s in esc).most_common())
    for s in eligible:
        if s.op_conf is None:
            summary.conf_missing += 1
            continue
        if s.op_conf < 0.95:
            summary.conf_below_095 += 1
        if s.op_conf < 0.55:
            summary.conf_below_055 += 1
    binding: Counter[str] = Counter()
    for s in eligible:
        for name, floor in NOUL_FLOORS.items():
            if s.nouls.get(name, 0.0) >= floor:
                binding[name] += 1
    summary.noul_binding = dict(binding)
    return summary


def reliability(pairs: list[tuple[float, bool]], bins: int = 10) -> dict[str, Any]:
    """Reliability diagram bins and expected calibration error for (probability, label) pairs."""
    buckets: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for p, y in pairs:
        b = min(int(p * bins), bins - 1)
        buckets[b].append((p, y))
    n = len(pairs)
    rows = []
    ece = 0.0
    for b in range(bins):
        items = buckets.get(b, [])
        if not items:
            continue
        conf = sum(p for p, _ in items) / len(items)
        acc = sum(1 for _, y in items if y) / len(items)
        ece += abs(conf - acc) * len(items) / n
        rows.append({"bin": b, "lo": b / bins, "hi": (b + 1) / bins, "n": len(items), "confidence": conf, "accuracy": acc})
    return {"bins": rows, "ece": ece, "n": n}


def auroc(pairs: list[tuple[float, bool]]) -> float | None:
    """Rank-based AUROC (Mann-Whitney), ties counted half. None when one class is empty."""
    pos = [p for p, y in pairs if y]
    neg = [p for p, y in pairs if not y]
    if not pos or not neg:
        return None
    ranked = sorted(pairs, key=lambda t: t[0])
    ranks: dict[int, float] = {}
    i = 0
    while i < len(ranked):
        j = i
        while j + 1 < len(ranked) and ranked[j + 1][0] == ranked[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    rank_sum_pos = sum(r for k, r in ranks.items() if ranked[k][1])
    return (rank_sum_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


SIGNALS = ("op_conf", "target_conf", "goal_done", "stuck", "needs_reasoning", "destructive")


def signals_from_labels(csv_path: Path, *, use_auto: bool = True) -> dict[str, Any]:
    """AUROC of each arbitration signal for predicting a WRONG S1 step, from a labels.csv
    (evals.labels). Uses the human ``label`` column where filled, else ``auto_label`` when
    ``use_auto``; rows labelled unknown are skipped. Higher confidence should mean fewer wrong steps,
    so confidence signals are negated before scoring; nouls are scored as-is."""
    import csv

    rows = list(csv.DictReader(csv_path.open()))
    labelled = []
    for r in rows:
        lab = (r.get("label") or "").strip().lower() or ((r.get("auto_label") or "").strip().lower() if use_auto else "")
        if lab in ("right", "wrong"):
            labelled.append((r, lab == "wrong"))
    out: dict[str, Any] = {"n": len(labelled), "wrong": sum(1 for _, w in labelled if w), "auroc": {}, "source": {}}
    out["source"] = {"human": sum(1 for r, _ in labelled if (r.get("label") or "").strip()), "auto": sum(1 for r, _ in labelled if not (r.get("label") or "").strip())}
    for sig in SIGNALS:
        pairs = []
        for r, wrong in labelled:
            v = r.get(sig)
            if v in (None, ""):
                continue
            x = float(v)
            if sig in ("op_conf", "target_conf"):
                x = -x
            pairs.append((x, wrong))
        out["auroc"][sig] = {"auroc": auroc(pairs), "n": len(pairs)}
    return out


def render(summary: EscalationSummary, baseline: EscalationSummary | None = None) -> str:
    def row(s: EscalationSummary, label: str) -> str:
        return (
            f"| {label} | {s.steps} | {s.s1_eligible} | {s.escalated} | {s.escalation_rate:.0%} | "
            f"{s.frac_conf_below_095:.0%} | {s.conf_below_055} | {s.conf_missing} |"
        )

    lines = [
        "| run | dual steps | S1-eligible | escalated | escalation rate | op conf < 0.95 | op conf < 0.55 | no confidence |",
        "|---|---|---|---|---|---|---|---|",
        row(summary, "this run"),
    ]
    if baseline is not None:
        lines.append(row(baseline, "baseline"))
        if baseline.escalation_rate:
            lines.append(f"\nEscalation rate ratio (this / baseline): {summary.escalation_rate / baseline.escalation_rate:.2f}")
    lines += ["", "Escalations by arbiter reason:", ""]
    lines += [f"- {k}: {v}" for k, v in summary.by_reason.items()]
    lines += ["", "Nouls at or above their floors (S1-eligible steps):", ""]
    lines += [f"- {k}: {v}" for k, v in sorted(summary.noul_binding.items())] or ["- none"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--baseline")
    ap.add_argument("--arm", default="dual")
    ap.add_argument("--labels", help="labels.csv from evals.labels: print AUROC per signal for predicting a wrong step")
    args = ap.parse_args()
    summary = escalation_summary(load_steps(Path(args.run_dir)), args.arm)
    base = escalation_summary(load_steps(Path(args.baseline)), args.arm) if args.baseline else None
    print(render(summary, base))
    if args.labels:
        sig = signals_from_labels(Path(args.labels))
        print(f"Labelled steps: {sig['n']} ({sig['wrong']} wrong; labels from human {sig['source']['human']}, heuristic {sig['source']['auto']})")
        print("| signal | AUROC for a wrong step | n |", "|---|---|---|", sep="\n")
        for name, v in sig["auroc"].items():
            a = "n/a" if v["auroc"] is None else f"{v['auroc']:.2f}"
            print(f"| {name} | {a} | {v['n']} |")


if __name__ == "__main__":
    main()
