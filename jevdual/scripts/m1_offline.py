"""Notebook M1, offline: the done decision on stored Q19 held-back sessions before and after effect
evidence, and on negatives built from the same records (edited in memory; the files are not touched).
Q19 is closed: this is development use of its records, not a rescore.

    uv run python scripts/m1_offline.py [--repeats 3] [--out results/m1-offline-20260929.json]
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jevdual.completion import effects as build_effects
from jevdual.keys import load_keys
from jevdual.menu import Candidate, Menu
from jevdual.session import carried_checks, cross_context
from jevdual.verify import Verifier

OP = ROOT / "results" / "q19-heldout-operator"
MO = ROOT / "results" / "q19-heldout-model"


def load(d: Path) -> dict[str, Any]:
    state = json.loads((d / "session.json").read_text())
    recs = [json.loads(ln) for ln in (d / "session.jsonl").read_text().splitlines() if ln.strip()]
    carries = json.loads((d / "carries.json").read_text()) if (d / "carries.json").exists() else {}
    return {"dir": d, "state": state, "records": recs, "carries": carries}


def menu_of(state: dict[str, Any], page_text: str | None = None) -> Menu:
    text = state["last_page_text"] if page_text is None else page_text
    cands = tuple(
        Candidate(**{**c, "operations": tuple(c["operations"])}) for c in state.get("last_candidates") or []
    )
    return Menu(
        url=state["last_url"],
        title=state["last_title"],
        page_text=text,
        candidates=cands,
        by_operation={},
        full_text=text,
    )


def case(
    s: dict[str, Any],
    answer: str,
    *,
    context: list[dict[str, Any]] = (),
    page_text: str | None = None,
    expect: str,
) -> dict[str, Any]:
    return {"s": s, "answer": answer, "context": list(context), "page_text": page_text, "expect": expect}


def cases() -> dict[str, dict[str, Any]]:
    h02 = load(OP / "H02-one-reservation" / "web")
    h10 = load(MO / "H10-document-to-request" / "request")
    h10src = load(MO / "H10-document-to-request" / "source")
    h06 = load(MO / "H06-edit-one-document" / "doc")
    final06 = "Batch cobalt: 4\nKeep this line.\nBatch cobalt: 9"
    out = {
        "op/H02 heading": case(h02, "Scratch cancellation recorded", expect="accept"),
        "model/H10 values": case(h10, "QUIET-83 27", context=[h10src], expect="accept"),
        "model/H10 heading": case(h10, "Scratch request recorded", context=[h10src], expect="accept"),
        "model/H06 text": case(h06, final06, expect="accept"),
    }
    # negatives, each a copy of a positive's records with one thing wrong
    wrong = copy.deepcopy(h06)
    for r in wrong["records"]:
        rb = (r.get("action") or {}).get("save_readback")
        if rb:
            rb["path"] = rb["path"].replace("h06-labels.txt", "h06-neighbor.txt")
    out["neg wrong resource (H06 readback names the neighbour)"] = case(wrong, final06, expect="refuse")
    stale = copy.deepcopy(h06)
    last_t = max(float(r["t"]) for r in stale["records"])
    stale["records"].append(
        {
            "t": last_t + 1,
            "step": 9,
            "kind": "receipt",
            "action": {"op": "type", "line": "type(text area)"},
            "effect": "confirmed",
            "evidence": "'text area' now holds 'Batch amber: 4\\nKeep this line.\\nBatch cobalt: 9'",
        }
    )
    stale["state"]["memory"] = [*stale["state"]["memory"], "step 9: type(text area) -> confirmed"]
    out["neg stale (H06 edited after the save)"] = case(
        stale,
        final06,
        page_text="h06-labels.txt\nBatch amber: 4\nKeep this line.\nBatch cobalt: 9",
        expect="refuse",
    )
    dup = copy.deepcopy(h10)
    sub = next(r for r in dup["records"] if "cutting-done" in str(r.get("evidence")))
    dup["records"].append({**copy.deepcopy(sub), "t": float(sub["t"]) + 5, "step": int(sub["step"]) + 1})
    dup["state"]["memory"] = [*dup["state"]["memory"], "step 5: click(Submit cutting request) -> confirmed"]
    out["neg duplicated submission (H10)"] = case(dup, "QUIET-83 27", context=[h10src], expect="refuse")
    generic = copy.deepcopy(h10)
    for r in generic["records"]:
        if "cutting-done" in str(r.get("evidence")):
            r["evidence"] = "navigated to /q19h-cutting-done.html; 0 elements added, 6 removed, 0 changed"
    out["neg generic page, no submitted fields, no source (H10)"] = case(
        generic, "QUIET-83 27", expect="refuse"
    )
    out["neg unevidenced value (H10 'QUIET-84')"] = case(
        h10, "QUIET-84 27", context=[h10src], expect="refuse"
    )
    bare = copy.deepcopy(h02)
    bare["records"] = [r for r in bare["records"] if r.get("kind") != "receipt"]
    bare["state"]["memory"] = []
    out["neg success page with no record of the deletion (H02)"] = case(
        bare, "Scratch cancellation recorded", expect="refuse"
    )
    # M2: cases not examined before M2 was written
    h02m = load(MO / "H02-one-reservation" / "web")
    out["new+ model/H02 real run (deleted once, went back, paused)"] = case(
        h02m, "Scratch cancellation recorded", expect="accept"
    )
    h08 = load(OP / "H08-image-to-request" / "request")
    h08img = load(OP / "H08-image-to-request" / "image")
    out["new+ op/H08 heading"] = case(h08, "Scratch request recorded", context=[h08img], expect="accept")
    h06op = load(OP / "H06-edit-one-document" / "doc")
    out["new+ op/H06 'Saved.'"] = case(h06op, "Saved.", expect="accept")
    h07 = load(MO / "H07-header-to-document" / "doc")
    nosave = copy.deepcopy(h07)
    nosave["records"] = [r for r in nosave["records"] if not (r.get("action") or {}).get("save_readback")]
    nosave["state"]["memory"] = [m for m in nosave["state"]["memory"] if "cmd+s" not in m]
    out["new- model/H07 without its save"] = case(nosave, "SQLite format 3", expect="refuse")
    failed = copy.deepcopy(h06op)
    for r in failed["records"]:
        rb = (r.get("action") or {}).get("save_readback")
        if rb:
            rb["ok"] = False
            rb["detail"] = "the file on disk differs from the window's text"
    out["new- op/H06 save readback failed"] = case(failed, "Saved.", expect="refuse")
    return out


async def decide(v: Verifier, c: dict[str, Any], *, m1: bool) -> dict[str, Any]:
    s = c["s"]
    st = s["state"]
    menu = menu_of(st, c["page_text"])
    trajectory = [
        {"step": i + 1, "url": st["last_url"], "actions": [m.split(": ", 1)[-1]]}
        for i, m in enumerate(st["memory"][-12:])
    ]
    ctx = [e for o in c["context"] for e in cross_context(o["dir"])]
    trajectory = ctx + trajectory + carried_checks(s["records"], menu)
    carried = tuple(
        str(x["text"]) for o in [s, *c["context"]] for x in o["carries"].values() if x.get("text")
    )
    kw: dict[str, Any] = {"answer_expected": bool(st.get("answer_expected")) or not m1}
    if m1:
        document = st["last_title"].split(" — ")[0] if st.get("mode") == "native" else ""
        ev = build_effects(s["records"], document=document, carries=s["carries"])
        for o in c["context"]:
            ev += build_effects(o["records"], carries=o["carries"])
        kw["effects"] = tuple(ev)
    r = await v.verify(
        st["task"],
        tuple(st.get("requirements") or ()),
        menu,
        c["answer"],
        trajectory=trajectory,
        carried=carried,
        **kw,
    )
    return {"band": r.band, "complete": round(r.complete, 2), "reason": r.reason[:160]}


async def main(repeats: int, out: Path) -> None:
    load_keys()
    from typesafe_sdk import AsyncTypeSafeClient

    rows = []
    async with AsyncTypeSafeClient() as client:
        v = Verifier(client)
        for name, c in cases().items():
            for arm in ("before", "M2"):
                for i in range(repeats):
                    d = await decide(v, c, m1=arm == "M2")
                    rows.append({"case": name, "expect": c["expect"], "arm": arm, "repeat": i, **d})
                    print(f"{arm:6} {name}: {d['band']} ({d['reason'][:110]})", flush=True)
    out.write_text(json.dumps(rows, indent=1))
    print("\nsummary (accepts of repeats):")
    for name, c in cases().items():
        b = [r for r in rows if r["case"] == name]
        acc = {arm: sum(r["band"] == "accept" for r in b if r["arm"] == arm) for arm in ("before", "M2")}
        print(f"  [{c['expect']:6}] {name}: before {acc['before']}/{repeats}, M2 {acc['M2']}/{repeats}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "m2-offline-20260929.json")
    a = ap.parse_args()
    asyncio.run(main(a.repeats, a.out))
