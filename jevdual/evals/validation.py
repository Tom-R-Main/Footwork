"""Triage a live validation run: unreachable tasks, predicate suspects, consent outcomes, judge view.

    uv run python -m evals.validation results/<run>

Rules (docs/experiments/README.md): a task no arm passes in any repeat is *unreachable* and leaves
the paired comparison; a task the predicate fails but the judge passes on every arm is a *predicate
suspect* to inspect (the page may have drifted or the predicate may be wrong); a task the judge
marks impossible or captcha-blocked on every arm is *blocked*.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load(run_dir: Path) -> list[dict]:
    return json.loads((run_dir / "results.json").read_text())


def triage(rows: list[dict]) -> dict[str, list]:
    by_task: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(r)
    out: dict[str, list] = {
        "unreachable": [],
        "predicate_suspect": [],
        "blocked": [],
        "crashed": [],
        "reachable": [],
    }
    for task, rs in sorted(by_task.items()):
        judged = [r for r in rs if r.get("judge_verdict") is not None]
        if any(r["passed"] for r in rs):
            out["reachable"].append(task)
            continue
        if rs and all(r.get("error") for r in rs):
            out["crashed"].append((task, rs[0]["error"][:80]))
            continue
        if judged and all(r.get("judge_impossible") or r.get("judge_captcha") for r in judged):
            out["blocked"].append(
                (task, "; ".join(sorted({(r.get("judge_reason") or "")[:80] for r in judged})))
            )
            continue
        if judged and all(r["judge_verdict"] for r in judged):
            out["predicate_suspect"].append(
                (task, "; ".join(sorted({str(r.get("answer") or r.get("final_url") or "")[:80] for r in rs})))
            )
            continue
        out["unreachable"].append(
            (task, "; ".join(sorted({(r.get("judge_reason") or "no judge")[:80] for r in rs})))
        )
    return out


def consent_table(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if "consent" not in (r.get("tags") or []):
            continue
        out.append(
            {
                "task": r["task_id"],
                "arm": r["arm"],
                "passed": r["passed"],
                "paused": r.get("paused"),
                "done": r.get("is_done"),
                "success": r.get("success"),
            }
        )
    return sorted(out, key=lambda x: (x["task"], x["arm"]))


def render(run_dir: Path, rows: list[dict]) -> str:
    t = triage(rows)
    lines = [f"# Live validation triage: {run_dir.name}", ""]
    lines += [f"- reachable (some arm passed): {len(t['reachable'])}"]
    for key in ("predicate_suspect", "blocked", "unreachable", "crashed"):
        lines.append(f"- {key.replace('_', ' ')}: {len(t[key])}")
    for key, title in (
        ("predicate_suspect", "Predicate suspects (judge passes, predicate fails on every arm)"),
        ("blocked", "Blocked (judge: impossible or captcha on every arm)"),
        ("unreachable", "Unreachable (no arm passed)"),
        ("crashed", "Crashed on every arm"),
    ):
        if t[key]:
            lines += ["", f"## {title}", ""]
            lines += [f"- `{task}`: {note}" for task, note in t[key]]
    ct = consent_table(rows)
    if ct:
        lines += [
            "",
            "## Consent tasks",
            "",
            "| task | arm | pass | paused | done | success |",
            "|---|---|---|---|---|---|",
        ]
        lines += [
            f"| {c['task']} | {c['arm']} | {'yes' if c['passed'] else 'no'} | {c['paused']} | {c['done']} | {c['success']} |"
            for c in ct
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    text = render(run_dir, load(run_dir))
    (run_dir / "triage.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
