"""Burden by how the run ended, and per unit of progress (Q12; the Q11 measurement correction).

    uv run python -m evals.burden results/<run or pooled> [--vs guarded]

Q11 showed a raw request count favouring the arm whose runs died sooner: a gate pause at step 6
costs fewer requests than a 25-step grind, and neither is progress. Two views that do not:

* requests split by ``terminal_mode`` (done_claimed, done_stopped, unverified, paused, cap, error),
  per arm, so a burden difference can be read next to the way the runs ended;
* requests per checkpoint reached, over the tasks that declare checkpoints (multistep tasks), with a
  paired bootstrap interval against ``--vs`` in the same run directory. Progress counts the
  checkpoint URLs visited plus one for a passed predicate.

Repeats of a task are averaged before pairing, as in ``evals.paired``.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from evals.paired import bootstrap_mean_ci

MODES = ("done_claimed", "done_stopped", "unverified", "paused", "cap", "error")


def load(run_dir: Path) -> list[dict[str, Any]]:
    return json.loads((run_dir / "results.json").read_text())


def by_mode(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    """arm -> mode -> {runs, requests, mean_requests, verified}."""
    out: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[(r["arm"], r.get("terminal_mode") or "?")].append(r)
    for (arm, mode), rs in groups.items():
        req = [float(r.get("llm_requests", 0)) for r in rs]
        out[arm][mode] = {
            "runs": len(rs),
            "requests": sum(req),
            "mean_requests": statistics.mean(req) if req else 0.0,
            "verified": sum(1 for r in rs if r["passed"] and r.get("success") is True),
        }
    return out


def progress_rows(rows: list[dict[str, Any]], arm: str) -> dict[str, dict[str, float]]:
    """task -> {requests, progress} averaged over repeats, tasks with checkpoints only."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r["arm"] == arm and "checkpoints_reached" in r:
            groups[r["task_id"]].append(r)
    out = {}
    for t, rs in groups.items():
        prog = [float(r["checkpoints_reached"]) + (1.0 if r["passed"] else 0.0) for r in rs]
        out[t] = {
            "requests": statistics.mean(float(r.get("llm_requests", 0)) for r in rs),
            "progress": statistics.mean(prog),
        }
    return out


def per_progress(a: dict[str, dict[str, float]], b: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Requests per unit of progress, B against A, over the tasks both have with progress > 0 in A."""
    common = sorted(t for t in a if t in b)
    ratio_a = {t: a[t]["requests"] / a[t]["progress"] for t in common if a[t]["progress"] > 0}
    ratio_b = {t: b[t]["requests"] / b[t]["progress"] for t in common if b[t]["progress"] > 0}
    both = sorted(t for t in ratio_a if t in ratio_b)
    diffs = [ratio_b[t] - ratio_a[t] for t in both]
    lo, hi = bootstrap_mean_ci(diffs) if diffs else (0.0, 0.0)
    return {
        "tasks": len(both),
        "a_requests_per_progress": statistics.mean(ratio_a[t] for t in both) if both else 0.0,
        "b_requests_per_progress": statistics.mean(ratio_b[t] for t in both) if both else 0.0,
        "mean_diff": statistics.mean(diffs) if diffs else 0.0,
        "ci95": (lo, hi),
        "no_progress_a": sorted(t for t in common if a[t]["progress"] == 0),
        "no_progress_b": sorted(t for t in common if b[t]["progress"] == 0),
    }


def render(rows: list[dict[str, Any]], vs: str | None) -> str:
    modes = by_mode(rows)
    arms = sorted(modes)
    lines = [
        "# Burden by terminal mode\n",
        "| arm | " + " | ".join(MODES) + " |",
        "|---|" + "---|" * len(MODES),
    ]
    for arm in arms:
        cells = []
        for m in MODES:
            c = modes[arm].get(m)
            cells.append(f"{c['runs']:.0f} runs, {c['mean_requests']:.1f} req" if c else "")
        lines.append(f"| {arm} | " + " | ".join(cells) + " |")
    if vs:
        lines += ["", f"# Requests per unit of progress, paired against `{vs}` (tasks with checkpoints)\n"]
        a = progress_rows(rows, vs)
        lines.append("| arm | tasks | requests per progress (vs) | (arm) | mean Δ | 95% CI |")
        lines.append("|---|---|---|---|---|---|")
        for arm in arms:
            if arm == vs:
                continue
            p = per_progress(a, progress_rows(rows, arm))
            lo, hi = p["ci95"]
            lines.append(
                f"| {arm} | {p['tasks']} | {p['a_requests_per_progress']:.2f} | {p['b_requests_per_progress']:.2f} "
                f"| {p['mean_diff']:+.2f} | [{lo:+.2f}, {hi:+.2f}] |"
            )
            if p["no_progress_b"] or p["no_progress_a"]:
                lines.append(
                    f"  excluded, no progress: {vs} {p['no_progress_a']}; {arm} {p['no_progress_b']}"
                )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--vs", default=None)
    args = ap.parse_args()
    print(render(load(Path(args.run_dir)), args.vs))


if __name__ == "__main__":
    main()
