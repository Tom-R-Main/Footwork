"""M3 (docs/notebook/2026-09-29-model-completion.md): the three arms on the development tasks, per task and
arm: how runs ended, steps, submissions, and the checks M3 predicts.

    uv run python scripts/m3_summary.py [results/m3-dev]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(base: Path) -> int:
    rows = []
    for d in sorted(base.glob("*-r*")):
        arm = d.name.split("-r")[0]
        p = d / "results.json"
        for r in json.loads(p.read_text()) if p.exists() else []:
            subs = sum(len(v) for k, v in (r.get("gets") or {}).items() if "done" in k)
            rows.append({**r, "arm": arm, "rep": d.name, "submissions": subs})
    by = defaultdict(list)
    for r in rows:
        by[(r["task"], r["arm"])].append(r)
    for (task, arm), rs in sorted(by.items()):
        ends = ", ".join(
            f"{r['status']}/{'ok' if r['oracle_ok'] else 'no'}/{r['steps']}st/{r['submissions']}sub"
            for r in rs
        )
        print(f"{task:24} {arm}: {ends}")
        for r in rs:
            if r["status"] in ("stopped", "no_progress", "paused", "budget"):
                print(f"{'':27}{r['rep']}: {r['reason'][:150]}")
    x1 = {a: by[("X1-withdrawn-archive", a)] for a in "ABC"}
    x2 = {a: by[("X2-one-signup", a)] for a in "ABC"}
    x3 = {a: by[("X3-unreserved-washers", a)] for a in "ABC"}
    print("\nM3 checks:")
    for a in "BC":
        ok = sum(
            r["status"] == "stopped" and r["steps"] <= 8 and "withdrawn" in r["reason"].lower() for r in x1[a]
        )
        print(f"  X1 {a}: stopped within 8 steps naming the withdrawal {ok}/{len(x1[a])}")
    print(f"  X1 A: budget {sum(r['status'] == 'budget' for r in x1['A'])}/{len(x1['A'])}")
    for a in "ABC":
        print(
            f"  X2 {a}: duplicate submissions {sum(r['submissions'] > 1 for r in x2[a])}, "
            f"accepted done {sum(r['status'] == 'done' for r in x2[a])}/{len(x2[a])}, "
            f"oracle {sum(bool(r['oracle_ok']) for r in x2[a])}"
        )
        print(f"  X3 {a}: proven {sum(r['status'] == 'done' and r['oracle_ok'] for r in x3[a])}/{len(x3[a])}")
    np = [r for r in rows if r["status"] == "no_progress" and r["task"] != "X1-withdrawn-archive"]
    print(f"  no_progress on X2/X3: {len(np)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "m3-dev"))
