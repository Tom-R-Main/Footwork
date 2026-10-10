"""Adjudication of experiment attempts, kept apart from the raw records it judges.

A raw record says what happened (a run's status, its oracle read, its logs). An adjudication says how the
attempt counts: whether it is eligible, contaminated or superseded by a rerun, which outcome class it
belongs to, and on what evidence. Summaries are computed from the adjudication and the raw logs together,
so a published exclusion cannot be undone by an aggregator that reads the raw rows alone (review of
2026-09-29: the model's results.json still labelled the contaminated H09 proven).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ELIGIBILITY = ("eligible", "contaminated", "superseded")
OUTCOMES = (
    "completed_verified",
    "effect_correct_unaccepted",
    "effect_correct_not_claimed",
    "truthful_stop",
    "stop_without_reason",
    "unsupported_claim",
)
BASES = ("accepted_done", "save_readback", "submission_receipt")
#: outcomes that assert the requested effect is present, and those that assert it is absent
EFFECT_PRESENT = {"completed_verified", "effect_correct_unaccepted", "effect_correct_not_claimed"}
EFFECT_ABSENT = {"truthful_stop", "stop_without_reason"}


@dataclass(frozen=True)
class Attempt:
    id: str
    driver: str
    task: str
    raw: str
    eligibility: str
    outcome: str
    basis: str | None = None
    superseded_by: str | None = None
    reason: str = ""
    evidence: tuple[str, ...] = field(default_factory=tuple)


def load(path: Path) -> list[Attempt]:
    out = []
    for a in yaml.safe_load(path.read_text())["attempts"]:
        out.append(
            Attempt(
                id=a["id"],
                driver=a["driver"],
                task=a["task"],
                raw=a["raw"],
                eligibility=a["eligibility"],
                outcome=a["outcome"],
                basis=a.get("basis"),
                superseded_by=a.get("superseded_by"),
                reason=a.get("reason", ""),
                evidence=tuple(a.get("evidence") or ()),
            )
        )
    return out


def raw_oracle(root: Path, attempt: Attempt) -> bool | None:
    """The oracle's first read for an attempt, from its raw record (None when there is none)."""
    d = root / attempt.raw
    if (d / "result.json").exists():  # operator: the first read is result.json, never result-later-N
        return bool(json.loads((d / "result.json").read_text())["oracle_ok"])
    rows = d.parent / "results.json"
    if rows.exists():
        for r in json.loads(rows.read_text()):
            if r["task"] == d.name:
                return bool(r["oracle_ok"])
    return None


def problems(attempts: list[Attempt], root: Path, raw_dirs: list[Path]) -> list[str]:
    """Everything that makes the adjudication inconsistent with itself or with the raw records."""
    out: list[str] = []
    ids = Counter(a.id for a in attempts)
    out += [f"duplicate id {i}" for i, n in ids.items() if n > 1]
    by_id = {a.id: a for a in attempts}
    covered = {(root / a.raw).resolve() for a in attempts}
    for d in raw_dirs:
        if d.resolve() not in covered:
            out.append(f"raw attempt {d} has no adjudication")
    for a in attempts:
        if not (root / a.raw).is_dir():
            out.append(f"{a.id}: raw record {a.raw} does not exist")
        if a.eligibility not in ELIGIBILITY:
            out.append(f"{a.id}: unknown eligibility {a.eligibility!r}")
        if a.outcome not in OUTCOMES:
            out.append(f"{a.id}: unknown outcome {a.outcome!r}")
        if (a.basis is not None) != (a.outcome == "completed_verified"):
            out.append(f"{a.id}: a basis is required for completed_verified and only there")
        if a.basis is not None and a.basis not in BASES:
            out.append(f"{a.id}: unknown basis {a.basis!r}")
        if a.eligibility == "superseded":
            r = by_id.get(a.superseded_by or "")
            if r is None or r.task != a.task or r.driver != a.driver or r.eligibility == "superseded":
                out.append(f"{a.id}: superseded_by must name a live attempt of the same task and driver")
        elif a.superseded_by:
            out.append(f"{a.id}: only a superseded attempt names a replacement")
        ok = raw_oracle(root, a)
        if ok is None:
            out.append(f"{a.id}: no oracle read in its raw record")
        elif a.outcome in EFFECT_PRESENT and not ok:
            out.append(f"{a.id}: {a.outcome} but the raw oracle failed")
        elif a.outcome in EFFECT_ABSENT and ok:
            out.append(f"{a.id}: {a.outcome} but the raw oracle confirmed the effect")
    live = Counter((a.driver, a.task) for a in attempts if a.eligibility != "superseded")
    out += [f"{d}/{t}: {n} live attempts, not one" for (d, t), n in live.items() if n != 1]
    return out


def operator_costs(task_dir: Path) -> dict[str, Any]:
    """Commands, wall time and friction from an operator task's logs (result.json can predate them)."""
    cmds = [json.loads(ln) for ln in (task_dir / "commands.jsonl").read_text().splitlines() if ln.strip()]
    fp = task_dir / "friction.jsonl"
    fr = [json.loads(ln) for ln in fp.read_text().splitlines() if ln.strip()] if fp.exists() else []
    start = json.loads((task_dir / "start.json").read_text())["t"]
    return {
        "commands": len(cmds),
        "wall_s": round((cmds[-1]["t"] if cmds else start) - start, 1),
        "friction": len(fr),
    }


def summary(attempts: list[Attempt], root: Path) -> dict[str, Any]:
    """Per driver: outcome counts over eligible attempts, the completion bases, what was excluded and why,
    and cost over eligible completed tasks (operator from its logs, model from its run rows)."""
    out: dict[str, Any] = {}
    for driver in sorted({a.driver for a in attempts}):
        mine = [a for a in attempts if a.driver == driver]
        eligible = [a for a in mine if a.eligibility == "eligible"]
        done = [a for a in eligible if a.outcome == "completed_verified"]
        s: dict[str, Any] = {
            "tasks": len({a.task for a in mine}),
            "eligible": len(eligible),
            "outcomes": {o: sum(1 for a in eligible if a.outcome == o) for o in OUTCOMES},
            "completed_basis": dict(Counter(a.basis for a in done)),
            "excluded": [
                {"id": a.id, "eligibility": a.eligibility, "reason": a.reason}
                for a in mine
                if a.eligibility != "eligible"
            ],
        }
        if driver == "operator":
            costs = [operator_costs(root / a.raw) for a in done]
            s["commands_per_completed"] = (
                round(sum(c["commands"] for c in costs) / len(costs), 2) if costs else None
            )
            s["friction_all_eligible"] = sum(operator_costs(root / a.raw)["friction"] for a in eligible)
        else:
            rows = {}
            for a in mine:
                p = (root / a.raw).parent / "results.json"
                for r in json.loads(p.read_text()):
                    rows[r["task"]] = r
            live = [rows[Path(a.raw).name] for a in mine if Path(a.raw).name in rows]
            s["steps_all_attempts"] = sum(r["steps"] for r in live)
            s["cost_usd_all_attempts"] = round(sum(r["cost_usd"] for r in live), 4)
        out[driver] = s
    return out
