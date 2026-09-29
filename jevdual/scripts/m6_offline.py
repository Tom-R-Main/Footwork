"""Notebook M6, offline: the verifier on the stored X3 session, one factor varied at a time.

uv run python scripts/m6_offline.py [--repeats 5]
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from challenge_offline import judge
from jevdual.keys import load_keys
from jevdual.verify import Verifier

RUN = ROOT / "results" / "m3-dev" / "A-r1" / "X3-unreserved-washers" / "web"


def base() -> dict:
    st = json.loads((RUN / "session.json").read_text())
    recs = [json.loads(ln) for ln in (RUN / "session.jsonl").read_text().splitlines() if ln.strip()]
    return {
        "task": st["task"],
        "requirements": list(st.get("requirements") or ()),
        "answer_expected": bool(st.get("answer_expected")),
        "answer": "60",
        "page": {
            "url": st["last_url"],
            "title": st["last_title"],
            "text": st["last_page_text"],
            "candidates": st["last_candidates"],
        },
        "mode": "browser",
        "records": recs,
        "carries": json.loads((RUN / "carries.json").read_text()),
        "memory": st["memory"],
        "context": [],
    }


def variants() -> dict[str, tuple[dict, bool]]:
    b = base()
    v1 = {**copy.deepcopy(b), "answer": "60 (Bin C2; Bin B7's 95 are reserved)"}
    v2 = {**copy.deepcopy(b), "requirements": ["The reported count is of washers that are not reserved"]}
    v4 = {**copy.deepcopy(b), "task": "On the parts stock page, report how many washers are in Bin C2."}
    return {
        "V0 as run": (b, False),
        "V1 answer states source and exclusion": (v1, False),
        "V2 qualifier as requirement": (v2, False),
        "V3 carried read as evidence": (b, True),
        "V4 control: no qualifier (changes the task)": (v4, False),
    }


async def main(repeats: int) -> None:
    load_keys()
    from typesafe_sdk import AsyncTypeSafeClient

    rows = []
    async with AsyncTypeSafeClient() as client:
        v = Verifier(client)
        for name, (case, evidence) in variants().items():
            for i in range(repeats):
                d = await judge(v, case, evidence=evidence)
                rows.append({"variant": name, "repeat": i, **d})
            got = [r for r in rows if r["variant"] == name]
            ps = ", ".join(f"{r['complete']:.2f}" for r in got)
            print(
                f"{name:46} accept {sum(r['band'] == 'accept' for r in got)}/{repeats}  complete p [{ps}]",
                flush=True,
            )
    (ROOT / "results" / "m6-offline-20260929.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=5)
    asyncio.run(main(ap.parse_args().repeats))
