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


def row_key(r: dict) -> str:
    """Rows from runs with repeats carry the trace's run_id; older sets are keyed by task and arm."""
    mid = r.get("run_id") or f"{r['task']}|{r['arm']}"
    return f"{r['run']}|{mid}|{r['step']}"


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
        f = (
            f"results/{r['run']}/traces/{r['run_id']}.jsonl"
            if r.get("run_id")
            else glob.glob(f"results/{r['run']}/traces/{r['task']}-{r['arm']}-*.jsonl")[0]
        )
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
                    "has_value": m.get("has_value"),
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
        # what ran before this step in the same run (labels only, no outcomes of this step): a Calculator
        # digit is only judgeable against the keys already pressed
        prior = []
        for st in sorted(cache[f]):
            if st >= int(r["step"]):
                break
            rec_prev = cache[f][st]
            execd = rec_prev.get("executed") or []
            if not execd:
                if rec_prev.get("arbiter_reason"):
                    prior.append(f"(step {st}: no action; {str(rec_prev['arbiter_reason'])[:50]})")
                continue
            for a in execd:
                pr = a.get("params") or {}
                what = pr.get("label") or pr.get("keys") or pr.get("path") or pr.get("index", "")
                txt = f" text={pr['text']!r}" if pr.get("text") else ""
                eff = f" -> {pr['effect']}" if pr.get("effect") else ""
                err = " (error)" if rec_prev.get("result_error") else ""
                prior.append(f"{a.get('name')}({what}){txt}{eff}{err}")
        # what S1 proposed to type: native runs record the proposal; browser runs record S1's own proposal only
        value = None
        for a in rec.get("proposed") or []:
            if a.get("name") in ("input", "type"):
                value = (a.get("params") or {}).get("text")
        alt_labels = [x.rsplit(" (", 1)[0] for x in (r.get("alternatives") or "").split("; ") if x]
        item = {
            "key": row_key(r),
            "prior_actions": prior[-12:],
            "task": r["task_text"],
            "page": r["url"],
            "window_text": (rec.get("page_text") or "")[:1500] or None,
            "step_in_run": int(r["step"]),
            "menu": menu,
            "s1_operation": op.get("choice"),
            "s1_target_id": tg.get("choice"),
            "s1_target_label": r["s1_target"],
            "value": value
            if value is not None
            else ("<needs value>" if op.get("choice") in ("type", "append") else None),
            "alternative_targets": alt_labels[:5],
        }
        item = {k: v for k, v in item.items() if v not in (None, [], "")}
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
