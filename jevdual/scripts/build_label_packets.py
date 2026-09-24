"""Build blinded labelling packets from the annotation set: task, page, full menu, System 1's choice and
alternatives; no executed action, no next-step reason, no outcome.

    uv run python scripts/build_label_packets.py results/annotation/q1-s1-decisions.csv results/annotation/packets --max-chars 110000
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("out_dir")
    ap.add_argument("--max-chars", type=int, default=110000)
    args = ap.parse_args()
    with open(args.csv, newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache: dict[str, dict[int, dict]] = {}
    packets: list[list[dict]] = [[]]
    size = 0
    for r in rows:
        f = glob.glob(f"results/{r['run']}/traces/{r['task']}-{r['arm']}-*.jsonl")[0]
        if f not in cache:
            recs = {}
            for line in Path(f).read_text().splitlines():
                x = json.loads(line)
                if x.get("kind") == "header":
                    continue
                recs[x["step"]] = x
            cache[f] = recs
        rec = cache[f][int(r["step"])]
        d = rec.get("decision") or {}
        op = d.get("operation") or {}
        tg = d.get("target") or {}
        menu = [
            {
                k: v
                for k, v in {
                    "id": m["id"],
                    "label": (m.get("label") or "")[:80],
                    "role": m.get("role"),
                    "section": m.get("section"),
                    "value": (m.get("value") or "")[:40] or None,
                    "input_type": m.get("input_type"),
                    "href": (m.get("href") or "")[:60] or None,
                    "offscreen": m.get("offscreen") or None,
                }.items()
                if v not in (None, "", False)
            }
            for m in (rec.get("menu") or [])
        ]
        # what S1 meant to type, if it typed: from its own proposal (the driver's action is not shown)
        value = None
        for a in rec.get("proposed") or []:
            if a.get("name") in ("input", "type"):
                value = (a.get("params") or {}).get("text")
        item = {
            "key": f"{r['run']}|{r['task']}|{r['arm']}|{r['step']}",
            "task": r["task_text"],
            "page": r["url"],
            "step_in_run": int(r["step"]),
            "menu": menu,
            "s1_operation": op.get("choice"),
            "s1_operation_confidence": op.get("confidence"),
            "s1_target_id": tg.get("choice"),
            "s1_target_label": r["s1_target"],
            "s1_target_confidence": tg.get("confidence"),
            "value": value
            if value is not None
            else ("<needs value>" if op.get("choice") == "type" else None),
            "alternatives": r["alternatives"],
        }
        s = len(json.dumps(item))
        if size + s > args.max_chars and packets[-1]:
            packets.append([])
            size = 0
        packets[-1].append(item)
        size += s
    for i, p in enumerate(packets):
        (out / f"packet-{i:02d}.json").write_text(json.dumps(p, separators=(",", ":")))
    print(f"{len(rows)} rows -> {len(packets)} packets in {out}: " + ", ".join(str(len(p)) for p in packets))


if __name__ == "__main__":
    main()
