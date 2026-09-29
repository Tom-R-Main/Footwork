"""Offline challenge cases for the completion candidate (docs/experiments/M-challenge-brief.md): each case's
done judged by the verifier in two arms (the default decision, and effect evidence as `footwork done`
makes it with FOOTWORK_COMPLETION=effect_evidence), plus an optional direct probe of the repeat rule.

    uv run python scripts/challenge_offline.py evals/challenge/<set> [--repeats 3] [--out FILE]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jevdual.completion import effects, repeat_of
from jevdual.keys import load_keys
from jevdual.menu import Candidate, Menu
from jevdual.session import carried_checks
from jevdual.verify import Verifier


def menu_of(page: dict[str, Any]) -> Menu:
    cands = tuple(
        Candidate(**{**c, "operations": tuple(c.get("operations") or ())})
        for c in page.get("candidates") or []
    )
    text = str(page.get("text") or "")
    return Menu(
        url=str(page.get("url") or ""),
        title=str(page.get("title") or ""),
        page_text=text,
        candidates=cands,
        by_operation={},
        full_text=text,
    )


async def judge(v: Verifier, c: dict[str, Any], *, evidence: bool) -> dict[str, Any]:
    menu = menu_of(c["page"])
    trajectory = [
        {
            "surface": f"other surface {i + 1}",
            "actions": [m.split(": ", 1)[-1] for m in o.get("memory") or []],
        }
        for i, o in enumerate(c.get("context") or [])
    ]
    trajectory += [
        {"step": i + 1, "url": menu.url, "actions": [m.split(": ", 1)[-1]]}
        for i, m in enumerate((c.get("memory") or [])[-12:])
    ]
    trajectory += carried_checks(c.get("records") or [], menu)
    surfaces = [c, *(c.get("context") or [])]
    carried = tuple(
        str(x["text"]) for s in surfaces for x in (s.get("carries") or {}).values() if x.get("text")
    )
    kw: dict[str, Any] = {}
    answer = c.get("answer")
    if evidence:
        document = menu.title.split(" — ")[0] if c.get("mode") == "native" else ""
        ev = effects(c.get("records") or [], document=document, carries=c.get("carries") or {})
        for o in c.get("context") or []:
            ev += effects(o.get("records") or [], carries=o.get("carries") or {})
        kw["effects"] = tuple(ev)
        kw["answer_expected"] = bool(c.get("answer_expected"))
    else:
        kw["answer_expected"] = bool(c.get("answer_expected")) or bool(answer)
    r = await v.verify(
        c["task"],
        tuple(c.get("requirements") or ()),
        menu,
        answer,
        trajectory=trajectory or None,
        carried=carried,
        **kw,
    )
    return {"band": r.band, "complete": round(r.complete, 2), "reason": r.reason[:200]}


async def main(folder: Path, repeats: int, out: Path) -> int:
    load_keys()
    from typesafe_sdk import AsyncTypeSafeClient

    cases = [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]
    rows: list[dict[str, Any]] = []
    async with AsyncTypeSafeClient() as client:
        v = Verifier(client)
        for c in cases:
            probe = c.get("repeat_probe")
            if probe:
                why = repeat_of(
                    c.get("records") or [],
                    probe["op"],
                    url=probe.get("url", ""),
                    label=probe.get("label", ""),
                )
                got = "pause" if why else "allow"
                rows.append(
                    {
                        "id": c["id"],
                        "arm": "repeat_probe",
                        "expect": probe["expect"],
                        "got": got,
                        "reason": why,
                    }
                )
            if c.get("answer") is None and not c.get("page"):
                continue
            for arm in ("default", "effect_evidence"):
                for i in range(repeats):
                    d = await judge(v, c, evidence=arm == "effect_evidence")
                    rows.append(
                        {
                            "id": c["id"],
                            "category": c.get("category"),
                            "arm": arm,
                            "repeat": i,
                            "expect": c["expect"],
                            **d,
                        }
                    )
    out.write_text(json.dumps(rows, indent=1))
    print(f"{'case':34} {'expect':7} {'default':>8} {'evidence':>9}  probe")
    for c in cases:
        mine = [r for r in rows if r["id"] == c["id"]]
        acc = {
            a: sum(r.get("band") == "accept" for r in mine if r["arm"] == a)
            for a in ("default", "effect_evidence")
        }
        n = sum(1 for r in mine if r["arm"] == "default")
        probe = next((f"{r['got']} (expect {r['expect']})" for r in mine if r["arm"] == "repeat_probe"), "")
        print(
            f"{c['id'][:34]:34} {c['expect']:7} {acc['default']:>5}/{n} {acc['effect_evidence']:>6}/{n}  {probe}"
        )
    wrong = [
        c["id"]
        for c in cases
        if c["expect"] == "refuse"
        and any(
            r.get("band") == "accept" for r in rows if r["id"] == c["id"] and r["arm"] == "effect_evidence"
        )
    ]
    print(f"\nnegatives accepted under effect evidence: {wrong or 'none'}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.folder, a.repeats, a.out or a.folder / "results.json")))
