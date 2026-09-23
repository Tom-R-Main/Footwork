"""Labelling sheet for Q1: one row per S1-eligible step of every arm where S1 decided, with an empty ``label``
column (right / wrong) and a heuristic ``auto_label`` to be overwritten by a person.

    uv run python -m evals.labels results/<run>   ->   results/<run>/labels.csv

Heuristic: a step S1 acted on is ``wrong`` when its action errored, or the next step's arbiter says
stuck, no_effect or repeated_target, or the run ended unpassed within two steps; otherwise ``right``.
A step S1 escalated is labelled by whether S1's *proposal* would have been right, which the
heuristic cannot know, so those rows get ``unknown``.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from evals.metrics import Step, load_steps, reason_class

BAD_NEXT = {"stuck", "no_effect", "repeated_target"}


def rows_for(run_dir: Path) -> list[dict]:
    results = {(r["task_id"], r["arm"]): r for r in json.loads((run_dir / "results.json").read_text())}
    steps = [
        s for s in load_steps(run_dir) if s.op_choice is not None
    ]  # every arm where S1 decided (dual, s1_only, delegate)
    by_task: dict[str, list[Step]] = {}
    for s in steps:
        by_task.setdefault(f"{s.task_id}|{s.arm}", []).append(s)
    # url and proposal per step from traces
    detail: dict[tuple[str, int], dict] = {}
    for f in sorted((run_dir / "traces").glob("*.jsonl")):
        task_id = None
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "header":
                task_id = r["run_id"].rsplit("-", 2)[0]
                continue
            detail[(task_id or f.stem, r["step"])] = r
    out = []
    for key, ss in by_task.items():
        task_id = key.split("|", 1)[0]
        ss.sort(key=lambda s: s.step)
        arm = ss[0].arm
        passed = bool(results.get((task_id, arm), {}).get("passed"))
        last_step = max(s.step for s in ss)
        for i, s in enumerate(ss):
            nxt = ss[i + 1] if i + 1 < len(ss) else None
            d = detail.get((task_id, s.step), {})
            proposed = d.get("proposed") or []
            if s.system == "s1":
                bad = (
                    bool(s.result_error)
                    or (nxt is not None and reason_class(nxt.reason) in BAD_NEXT)
                    or (not passed and s.step >= last_step - 1)
                )
                auto = "wrong" if bad else "right"
            else:
                auto = "unknown"
            menu = {m["id"]: m for m in (d.get("menu") or [])}
            dec = d.get("decision") or {}
            tg = dec.get("target") or {}
            chosen = tg.get("choice")
            chosen_label = (
                (menu.get(int(chosen)) or {}).get("label")
                if chosen is not None and str(chosen).lstrip("-").isdigit()
                else None
            )
            alts = sorted(
                (
                    (float(p_), int(k))
                    for k, p_ in (tg.get("probabilities") or {}).items()
                    if str(k).lstrip("-").isdigit()
                ),
                reverse=True,
            )[:5]
            verify = d.get("verify") or {}
            unmet = verify.get("unmet_effective") or verify.get("unmet") or {}
            out.append(
                {
                    "task": task_id,
                    "arm": arm,
                    "step": s.step,
                    "system": s.system,
                    "url": d.get("url_after") or "",
                    "target_label": chosen_label or "",
                    "alternatives": "; ".join(
                        f"{sid}:{(menu.get(sid) or {}).get('label', '?')[:40]} ({p_:.2f})" for p_, sid in alts
                    ),
                    "menu_size": len(menu),
                    "verify_band": verify.get("band", ""),
                    "verify_complete": verify.get("complete", ""),
                    "verify_unmet_max": (max(unmet.values()) if unmet else ""),
                    "proposed": json.dumps(proposed),
                    "proposed_source": "s1"
                    if proposed
                    else "none (S1 decision only: see op_choice, target_label, alternatives)",
                    "executed": ",".join(s.executed),
                    "op_choice": s.op_choice,
                    "op_conf": s.op_conf,
                    "target_conf": s.target_conf,
                    "goal_done": s.nouls.get("goal_done"),
                    "stuck": s.nouls.get("stuck"),
                    "needs_reasoning": s.nouls.get("needs_reasoning"),
                    "destructive": s.nouls.get("destructive"),
                    "arbiter_reason": (s.reason or "")[:120],
                    "result_error": (s.result_error or "")[:80],
                    "next_reason": reason_class(nxt.reason) if nxt else "",
                    "run_passed": passed,
                    "auto_label": auto,
                    "label": "",
                    "note": "",
                }
            )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    rows = rows_for(run_dir)
    path = run_dir / "labels.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter

    print(f"{len(rows)} rows -> {path}; auto labels {dict(Counter(r['auto_label'] for r in rows))}")


if __name__ == "__main__":
    main()
