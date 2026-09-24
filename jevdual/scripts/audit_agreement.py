"""Agreement between the human audit labels and the model labels.

uv run python scripts/audit_agreement.py results/annotation/audit-sheet.csv results/annotation/q1-s1-decisions.csv
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main() -> None:
    audit_path, full_path = Path(sys.argv[1]), Path(sys.argv[2])
    with audit_path.open(newline="") as fh:
        audit = [r for r in csv.DictReader(fh) if (r.get("audit_label") or "").strip()]
    with full_path.open(newline="") as fh:
        full = {(r["run"], r["task"], r["arm"], r["step"]): r for r in csv.DictReader(fh)}
    if not audit:
        raise SystemExit("no audit labels filled in yet")
    pairs = [
        (r["audit_label"].strip().lower(), full[(r["run"], r["task"], r["arm"], r["step"])]) for r in audit
    ]
    print(f"{len(pairs)} audited rows")
    for name, pick in (
        ("pass A", lambda m: m["label_a"]),
        ("pass B", lambda m: m["label_b"]),
        ("agreed model label", lambda m: m["model_label"]),
    ):
        sub = [(h, pick(m)) for h, m in pairs if pick(m) in ("right", "wrong", "unclear")]
        agree = sum(1 for h, m in sub if h == m) / len(sub)
        print(
            f"  vs {name}: n={len(sub)} agreement {agree:.3f} kappa {kappa([h for h, _ in sub], [m for _, m in sub]):.3f}"
        )
    dis = [
        (h, m)
        for h, m in pairs
        if m["model_label"] in ("right", "wrong", "unclear") and h != m["model_label"]
    ]
    print(f"  human differs from the agreed label on {len(dis)} rows:")
    for h, m in dis:
        print(
            f"    {m['task']}|{m['arm']}|{m['step']} {m['s1_operation']} on {m['s1_target'][:30]!r}: human={h} model={m['model_label']} ({m['reason_a'][:70]})"
        )


if __name__ == "__main__":
    main()
