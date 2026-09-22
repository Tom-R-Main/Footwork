"""Paired comparison of one arm across two runs (or two arms in one run), task by task.

    uv run python -m evals.paired results/<before> results/<after> --arm dual
    uv run python -m evals.paired results/<run> --arm dual --vs stock

Reports per-task differences in pass, steps, LLM calls, cost and wall time with a paired bootstrap
95% interval on the mean difference (docs/experiments/README.md: paired, with intervals). Tasks
present in only one side are listed and excluded.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path
from typing import Any

FIELDS = ("passed", "steps", "llm_calls", "jev_calls", "cost", "wall_s", "unverified")


def _rows(run_dir: Path, arm: str) -> dict[str, dict[str, Any]]:
    out = {}
    for r in json.loads((run_dir / "results.json").read_text()):
        if r["arm"] != arm:
            continue
        r = dict(r)
        r["cost"] = float(r.get("llm_cost_usd", 0.0)) + float(r.get("jev_cost_usd", 0.0))
        r["unverified"] = 1 if str(r.get("answer") or "").startswith("UNVERIFIED") else 0
        r["passed"] = 1 if r["passed"] else 0
        out[r["task_id"]] = r
    return out


def bootstrap_mean_ci(diffs: list[float], n: int = 4000, seed: int = 7) -> tuple[float, float]:
    rng = random.Random(seed)
    means = []
    for _ in range(n):
        sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def compare(a: dict[str, dict], b: dict[str, dict]) -> dict[str, Any]:
    common = sorted(set(a) & set(b))
    out: dict[str, Any] = {"n": len(common), "only_a": sorted(set(a) - set(b)), "only_b": sorted(set(b) - set(a)), "fields": {}}
    for f in FIELDS:
        diffs = [float(b[t][f]) - float(a[t][f]) for t in common]
        if not diffs:
            continue
        lo, hi = bootstrap_mean_ci(diffs) if len(diffs) > 1 else (diffs[0], diffs[0])
        out["fields"][f] = {
            "a_total": sum(float(a[t][f]) for t in common),
            "b_total": sum(float(b[t][f]) for t in common),
            "mean_diff": statistics.mean(diffs),
            "ci95": (lo, hi),
            "b_better": sum(1 for d in diffs if (d > 0 if f == "passed" else d < 0)),
            "a_better": sum(1 for d in diffs if (d < 0 if f == "passed" else d > 0)),
        }
    return out


def render(res: dict[str, Any], label_a: str, label_b: str) -> str:
    lines = [f"Paired on {res['n']} tasks: A = {label_a}, B = {label_b}", ""]
    if res["only_a"] or res["only_b"]:
        lines += [f"only in A: {res['only_a']}", f"only in B: {res['only_b']}", ""]
    lines += ["| field | A total | B total | mean B−A per task | 95% CI | tasks B better | tasks A better |", "|---|---|---|---|---|---|---|"]
    for f, v in res["fields"].items():
        lo, hi = v["ci95"]
        lines.append(f"| {f} | {v['a_total']:.3f} | {v['b_total']:.3f} | {v['mean_diff']:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {v['b_better']} | {v['a_better']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_a")
    ap.add_argument("run_b", nargs="?")
    ap.add_argument("--arm", default="dual")
    ap.add_argument("--vs", help="compare --arm against this arm within run_a instead of across runs")
    args = ap.parse_args()
    a = _rows(Path(args.run_a), args.vs or args.arm)
    if args.vs:
        b = _rows(Path(args.run_a), args.arm)
        la, lb = f"{args.vs} ({Path(args.run_a).name})", f"{args.arm} ({Path(args.run_a).name})"
    else:
        b = _rows(Path(args.run_b), args.arm)
        la, lb = f"{args.arm} ({Path(args.run_a).name})", f"{args.arm} ({Path(args.run_b).name})"
    print(render(compare(a, b), la, lb))


if __name__ == "__main__":
    main()
