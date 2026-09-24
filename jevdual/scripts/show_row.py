"""Print one annotation row the way the labellers saw it (task, page, full menu, System 1's choice).

uv run python scripts/show_row.py <task> <arm> <step>          e.g.  ls-cart-stop-unauthorized dual 1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    task, arm, step = sys.argv[1], sys.argv[2], int(sys.argv[3])
    for f in sorted(Path("results/annotation/packets").glob("*.json")):
        for row in json.loads(f.read_text()):
            _, t, a, s = row["key"].split("|")
            if t == task and a == arm and int(s) == step:
                print(f"TASK: {row['task']}\nPAGE: {row['page']}\n")
                print(
                    f"SYSTEM 1 CHOSE: {row['s1_operation']} on [{row['s1_target_id']}] {row['s1_target_label']!r}"
                    + (f"  value={row['value']!r}" if row.get("value") else "")
                )
                print(
                    f"  op confidence {row['s1_operation_confidence']}, target confidence {row['s1_target_confidence']}"
                )
                print(f"  alternatives: {row['alternatives']}\n\nMENU ({len(row['menu'])} controls):")
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
