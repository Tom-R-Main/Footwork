"""Merge two blinded labelling passes into the annotation set and build the human audit sheet.

    uv run python scripts/merge_labels.py results/annotation/q1-s1-decisions.csv results/annotation/labels-a results/annotation/labels-b

Each labels dir holds JSONL files with {"key", "label", "reason"} per row. Writes the CSV back with
label_a/reason_a/label_b/reason_b/model_label (the agreed label, else "disagree"), prints agreement, and
writes audit-sheet.csv: 20 random rows plus 20 rows where the passes disagree or both disagree with
auto_label, for a person to label blind (outcome columns removed).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

BLIND_DROP = (
    "executed",
    "executed_target",
    "url_after",
    "result_error",
    "next_reason",
    "verify_band",
    "verify_complete",
    "verify_unmet_max",
    "run_passed",
    "auto_label",
    "label_a",
    "reason_a",
    "label_b",
    "reason_b",
    "model_label",
)


def load(dir_: str) -> dict[str, dict]:
    out = {}
    for f in sorted(Path(dir_).glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            x = json.loads(line)
            out[x["key"]] = x
    return out


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("labels_a")
    ap.add_argument("labels_b")
    ap.add_argument("--seed", type=int, default=20260923)
    args = ap.parse_args()
    with open(args.csv, newline="") as fh:
        rows = list(csv.DictReader(fh))
    la, lb = load(args.labels_a), load(args.labels_b)
    missing = 0
    for r in rows:
        key = f"{r['run']}|{r['task']}|{r['arm']}|{r['step']}"
        a, b = la.get(key), lb.get(key)
        if a is None or b is None:
            missing += 1
        r["label_a"] = (a or {}).get("label", "")
        r["reason_a"] = (a or {}).get("reason", "")[:160]
        r["label_b"] = (b or {}).get("label", "")
        r["reason_b"] = (b or {}).get("reason", "")[:160]
        r["model_label"] = (
            r["label_a"]
            if r["label_a"] and r["label_a"] == r["label_b"]
            else ("disagree" if r["label_a"] and r["label_b"] else "")
        )
    fields = list(rows[0].keys())
    with open(args.csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    both = [r for r in rows if r["label_a"] and r["label_b"]]
    print(f"{len(rows)} rows, {len(both)} labelled by both passes, {missing} missing a pass")
    print(
        "pass A:",
        dict(Counter(r["label_a"] for r in both)),
        "| pass B:",
        dict(Counter(r["label_b"] for r in both)),
    )
    print(
        f"A vs B agreement: {sum(1 for r in both if r['label_a'] == r['label_b']) / len(both):.3f}, kappa {kappa([r['label_a'] for r in both], [r['label_b'] for r in both]):.3f}"
    )
    s1 = [
        r
        for r in both
        if r["system"] == "s1"
        and r["model_label"] in ("right", "wrong")
        and r["auto_label"] in ("right", "wrong")
    ]
    if s1:
        print(
            f"agreed model label vs heuristic auto_label on s1 rows (n={len(s1)}): agreement {sum(1 for r in s1 if r['model_label'] == r['auto_label']) / len(s1):.3f}, kappa {kappa([r['model_label'] for r in s1], [r['auto_label'] for r in s1]):.3f}"
        )
    print("model_label:", dict(Counter(r["model_label"] for r in rows)))
    rng = random.Random(args.seed)
    disagree = [
        r
        for r in both
        if r["model_label"] == "disagree"
        or (
            r["system"] == "s1"
            and r["model_label"] in ("right", "wrong")
            and r["auto_label"] in ("right", "wrong")
            and r["model_label"] != r["auto_label"]
        )
    ]
    rest = [r for r in both if r not in disagree]
    audit = rng.sample(disagree, min(20, len(disagree))) + rng.sample(rest, min(20, len(rest)))
    rng.shuffle(audit)
    out = Path(args.csv).parent / "audit-sheet.csv"
    keep = [f for f in fields if f not in BLIND_DROP]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[*keep, "audit_label", "audit_note"], lineterminator="\n")
        w.writeheader()
        for r in audit:
            w.writerow({**{k: r[k] for k in keep}, "audit_label": "", "audit_note": ""})
    print(f"audit sheet: {len(audit)} rows ({min(20, len(disagree))} disagreements) -> {out}")


if __name__ == "__main__":
    main()
