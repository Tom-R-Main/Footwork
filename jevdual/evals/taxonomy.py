"""Failure taxonomy for an eval run: classify every task from its trace, not from opinions.

Classes (first match wins):
  pass                  predicate met, no error
  crash                 the run raised (rig or browser)
  policy_error          a Jev call failed or returned invalid answers
  premature_done        S1 said done (or accepted verification) but the predicate is unmet
  needs_text            escalated because TYPE/SELECT had no composed text (S1-only has no S2)
  low_confidence        arbiter/floors stopped it on confidence
  destructive_paused    stopped before a destructive action (correct for not_reached tasks, else a miss)
  stuck_loop            repeated target / no-effect escalations or the same url for the last 4 steps
  budget_exhausted      ran out of steps with progress still happening
  wrong_target          last executed actions changed pages but never reached the predicate
  unclassified
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from jevdual.trace import read_trace


def classify(result: dict, steps) -> str:
    if result.get("passed"):
        return "pass"
    if result.get("error"):
        return "crash"
    if result.get("paused"):
        return "destructive_paused"
    reasons = [s.arbiter_reason or "" for s in steps]
    joined = " | ".join(reasons).lower()
    if any(s.result_error and "policy" in (s.result_error or "").lower() for s in steps) or "policy error" in joined:
        return "policy_error"
    if result.get("is_done"):
        return "premature_done"
    if "needs composed text" in joined:
        return "needs_text"
    if "confidence" in joined or "low_confidence" in joined:
        return "low_confidence"
    if "destructive" in joined or "confirm" in joined:
        return "destructive_paused"
    if "repeated target" in joined or "no_effect" in joined or "stuck" in joined:
        return "stuck_loop"
    urls = [s.url_after for s in steps if s.url_after]
    if len(urls) >= 4 and len(set(urls[-4:])) == 1:
        return "stuck_loop"
    if len(steps) >= (result.get("max_steps") or 20):
        return "budget_exhausted"
    if len(set(urls)) > 1:
        return "wrong_target"
    return "unclassified"


def main(run_dir: str) -> None:
    run = Path(run_dir)
    results = json.loads((run / "results.json").read_text())
    rows = []
    counts: Counter[str] = Counter()
    escalations: Counter[str] = Counter()
    ops: Counter[str] = Counter()
    for r in results:
        _header, steps = read_trace(r["trace_path"]) if r.get("trace_path") and Path(r["trace_path"]).exists() else (None, [])
        cls = classify(r, steps)
        counts[cls] += 1
        for s in steps:
            if s.arbiter_reason and s.system == "s1" and not s.executed:
                escalations[s.arbiter_reason.split(":")[0][:40]] += 1
            for a in s.executed:
                ops[a.name] += 1
        last = steps[-1] if steps else None
        rows.append((r["task_id"], r["arm"], cls, len(steps), r.get("final_url") or "", (last.arbiter_reason or "")[:60] if last else ""))
    lines = [f"# Failure taxonomy: {run.name}", "", "| class | count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in counts.most_common()]
    lines += ["", "## Per task", "", "| task | arm | class | steps | final url | last reason |", "|---|---|---|---|---|---|"]
    lines += [f"| {t} | {a} | {c} | {n} | {u} | {reason} |" for t, a, c, n, u, reason in rows]
    lines += ["", "## Escalation reasons (S1 steps not executed)", ""] + [f"- {k}: {v}" for k, v in escalations.most_common()]
    lines += ["", "## Executed actions", ""] + [f"- {k}: {v}" for k, v in ops.most_common()]
    text = "\n".join(lines) + "\n"
    (run / "taxonomy.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(sys.argv[1])
