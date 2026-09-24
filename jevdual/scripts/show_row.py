"""Print one annotation row the way the labellers saw it (task, page, full menu, System 1's choice).

uv run python scripts/show_row.py <task> <arm> <step>          e.g.  ls-cart-stop-unauthorized dual 1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    task, arm, step = sys.argv[1], sys.argv[2], int(sys.argv[3])
    # optional: a packets dir (results/annotation/q10/packets) and a run_id for runs with repeats
    packets_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else Path("results/annotation/packets")
    run_id = sys.argv[5] if len(sys.argv) > 5 else None
    for f in sorted(packets_dir.glob("*.json")):
        for row in json.loads(f.read_text()):
            parts = row["key"].split("|")
            if len(parts) == 4:
                _, t, a, s = parts
                rid = None
            else:  # run|run_id|step: runs with repeats
                _, rid, s = parts
                t, a = rid.rsplit("-", 2)[0], rid.rsplit("-", 2)[1]
            if t == task and a == arm and int(s) == step and (run_id is None or rid == run_id):
                print(f"TASK: {row['task']}\nPAGE: {row['page']}\n")
                print(
                    f"SYSTEM 1 CHOSE: {row['s1_operation']} on [{row['s1_target_id']}] {row['s1_target_label']!r}"
                    + (f"  value={row['value']!r}" if row.get("value") else "")
                )
                if row.get("window_text"):
                    print(f"WINDOW TEXT:\n{row['window_text'][:800]}\n")
                if row.get("prior_actions"):
                    print("PRIOR ACTIONS: " + "; ".join(row["prior_actions"]) + "\n")
                print(
                    f"  alternatives: {row.get('alternative_targets') or row.get('alternatives')}\n\nMENU ({len(row['menu'])} controls):"
                )
                for m in row["menu"]:
                    extra = " ".join(f"{k}={v!r}" for k, v in m.items() if k not in ("id", "label", "role"))
                    mark = " <== chosen" if str(m["id"]) == str(row["s1_target_id"]) else ""
                    print(f"  [{m['id']:>4}] {m.get('role', ''):10s} {m['label'][:70]!r} {extra}{mark}")
                return
    raise SystemExit(
        "row not found; rebuild packets with scripts/build_label_packets.py if results/annotation/packets is missing"
    )


if __name__ == "__main__":
    main()
