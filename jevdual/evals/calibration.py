"""Q1: how well do System 1's confidences and situation nouls predict a wrong step, on the labelled
annotation set (model labels agreed by two blinded passes, human-audited; see results/annotation).

    uv run python -m evals.calibration results/annotation/q1-s1-decisions.csv > results/annotation/q1-calibration.md

Rows with model_label right/wrong are used; unclear and disagree rows are excluded and counted.
Signals: op and target confidence (negated: low confidence should predict wrong) and the nouls.
Reports AUROC with bootstrap CIs, paired bootstrap differences against op confidence, and the
threshold sweep for the confidence floors (escalate when confidence < t): wrong steps caught
against right steps escalated, with the operating point the pre-registration names (false
escalation ≤ 20%).
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

from evals.metrics import auroc

CONF = ("s1_op_conf", "s1_target_conf")
NOULS = ("goal_done", "stuck", "needs_reasoning", "destructive")


def pairs_for(rows: list[dict], sig: str) -> list[tuple[float, bool]]:
    out = []
    for r in rows:
        v = r.get(sig)
        if v in (None, ""):
            continue
        x = float(v)
        if sig in CONF:
            x = -x
        out.append((x, r["model_label"] == "wrong"))
    return out


def boot_ci(
    rows: list[dict], sig: str, rng: random.Random, n: int = 1000
) -> tuple[float | None, float, float]:
    base = auroc(pairs_for(rows, sig))
    vals = []
    for _ in range(n):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        a = auroc(pairs_for(sample, sig))
        if a is not None:
            vals.append(a)
    vals.sort()
    if base is None or not vals:
        return None, 0.0, 0.0
    return base, vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def boot_diff(
    rows: list[dict], sig: str, ref: str, rng: random.Random, n: int = 1000
) -> tuple[float, float, float]:
    a0 = auroc(pairs_for(rows, sig)) or 0.0
    b0 = auroc(pairs_for(rows, ref)) or 0.0
    vals = []
    for _ in range(n):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        a, b = auroc(pairs_for(sample, sig)), auroc(pairs_for(sample, ref))
        if a is not None and b is not None:
            vals.append(a - b)
    vals.sort()
    if not vals:
        return a0 - b0, 0.0, 0.0
    return a0 - b0, vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def sweep(rows: list[dict], sig: str) -> list[dict]:
    out = []
    xs = [(float(r[sig]), r["model_label"] == "wrong") for r in rows if r.get(sig) not in (None, "")]
    wrong = sum(1 for _, w in xs if w)
    right = len(xs) - wrong
    for t10 in range(30, 100, 5):
        t = t10 / 100
        caught = sum(1 for x, w in xs if w and x < t)
        false_esc = sum(1 for x, w in xs if not w and x < t)
        out.append(
            {
                "t": t,
                "wrong_caught": caught / wrong if wrong else 0.0,
                "right_escalated": false_esc / right if right else 0.0,
                "escalated": (caught + false_esc) / len(xs) if xs else 0.0,
            }
        )
    return out


def report(rows: list[dict], title: str, rng: random.Random) -> list[str]:
    lines = [f"### {title}", ""]
    labelled = [r for r in rows if r["model_label"] in ("right", "wrong")]
    wrong = sum(1 for r in labelled if r["model_label"] == "wrong")
    lines.append(
        f"{len(labelled)} labelled rows ({wrong} wrong, {len(labelled) - wrong} right); excluded: {dict(Counter(r['model_label'] for r in rows if r['model_label'] not in ('right', 'wrong')))}"
    )
    lines += [
        "",
        "| signal | AUROC for a wrong step | 95% CI | n | AUROC − op confidence | 95% CI |",
        "|---|---|---|---|---|---|",
    ]
    for sig in (*CONF, *NOULS):
        base, lo, hi = boot_ci(labelled, sig, rng)
        n = len(pairs_for(labelled, sig))
        if base is None:
            lines.append(f"| {sig} | n/a | | {n} | | |")
            continue
        if sig == "s1_op_conf":
            lines.append(f"| {sig} | {base:.3f} | [{lo:.3f}, {hi:.3f}] | {n} | reference | |")
        else:
            d, dlo, dhi = boot_diff(labelled, sig, "s1_op_conf", rng)
            lines.append(
                f"| {sig} | {base:.3f} | [{lo:.3f}, {hi:.3f}] | {n} | {d:+.3f} | [{dlo:+.3f}, {dhi:+.3f}] |"
            )
    for sig in CONF:
        lines += [
            "",
            f"Threshold sweep, {sig} (escalate when below t):",
            "",
            "| t | wrong caught | right escalated | share escalated |",
            "|---|---|---|---|",
        ]
        best = None
        for s in sweep(labelled, sig):
            lines.append(
                f"| {s['t']:.2f} | {s['wrong_caught']:.0%} | {s['right_escalated']:.0%} | {s['escalated']:.0%} |"
            )
            if s["right_escalated"] <= 0.20 and (best is None or s["wrong_caught"] > best["wrong_caught"]):
                best = s
        if best:
            lines.append(
                f"\nOperating point (false escalation ≤ 20%): t = {best['t']:.2f}, catches {best['wrong_caught']:.0%} of wrong steps, escalates {best['right_escalated']:.0%} of right ones."
            )
    lines.append("")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    with Path(args.csv).open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    rng = random.Random(args.seed)
    lines = [
        "# Q1 calibration on the labelled annotation set",
        "",
        f"Source: `{args.csv}`; labels = `model_label` (two blinded passes agreeing).",
        "",
    ]
    lines += report(rows, "All System 1 decisions (acted and escalated)", rng)
    lines += report([r for r in rows if r["system"] == "s1"], "Steps System 1 acted on", rng)
    lines += report(
        [r for r in rows if r["system"] == "s2"], "Steps System 1 proposed and the arbiter escalated", rng
    )
    by_op: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_op[r["s1_operation"]].append(r)
    for op, sub in sorted(by_op.items(), key=lambda kv: -len(kv[1])):
        if len(sub) >= 40:
            lines += report(sub, f"Operation `{op}`", rng)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
