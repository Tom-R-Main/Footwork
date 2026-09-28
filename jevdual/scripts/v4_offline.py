"""Notebook V4, offline: the verifier on Q13 task 1's destination window, with and without the other
surface's context, and on a tampered destination. Three Jev calls.

    uv run python scripts/v4_offline.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jevdual.keys import load_keys
from jevdual.menu import Candidate, Menu
from jevdual.verify import Verifier

TASK = (
    "Read the price of the first book on books.toscrape.com and add it as a new line at the end of the "
    "TextEdit document prices.txt, then save the document."
)
REQS = ("The document's last line is the first book's price", "The document was saved")
OWN = [
    {
        "step": 1,
        "url": "app://TextEdit",
        "actions": ["append(text area) text=@price (from browser https://books.toscrape.com/) -> confirmed"],
    },
    {"step": 2, "url": "app://TextEdit", "actions": ["hotkey(cmd+s) -> confirmed"]},
]
CONTEXT = [
    {
        "surface": "Google Chrome (footwork) https://books.toscrape.com/",
        "actions": ["navigate(https://books.toscrape.com/) -> confirmed: navigated to /"],
    },
    {
        "surface": "Google Chrome (footwork) https://books.toscrape.com/",
        "actions": [
            "read @price = '£51.77' at https://books.toscrape.com/ from text 'A Light in the Attic £51.77 In stock Add to basket' (the first book on the page)"
        ],
    },
]


def window(last: str) -> Menu:
    text = f"Price carried from the browser:\n{last}"
    area = Candidate(id=1, label="text area", role="textbox", operations=("type",), value=text)
    return Menu(
        url="app://TextEdit",
        title="prices.txt",
        page_text=text,
        candidates=(area,),
        by_operation={},
        full_text=text,
    )


async def main() -> None:
    load_keys()
    from typesafe_sdk import AsyncTypeSafeClient

    async with AsyncTypeSafeClient() as client:
        v = Verifier(client)
        cases = {
            "correct, with context": (window("£51.77"), CONTEXT + OWN),
            "correct, without context": (window("£51.77"), OWN),
            "tampered (£52.00), with context": (window("£52.00"), CONTEXT + OWN),
        }
        out = {}
        for name, (menu, traj) in cases.items():
            r = await v.verify(
                TASK, REQS, menu, "Added the first book's price as the last line and saved.", trajectory=traj
            )
            out[name] = {
                "band": r.band,
                "reason": r.reason[:200],
                "unmet": {k: round(x, 2) for k, x in r.unmet.items()},
            }
            print(f"{name}: {r.band} ({r.reason[:140]})")
    Path("results/v4-offline-20260928.json").write_text(json.dumps(out, indent=1))


asyncio.run(main())
