"""One real Jev call against a hand-built menu. Requires TYPESAFE_API_KEY; otherwise exits 0 with a note."""

from __future__ import annotations

import asyncio
import json
import os
import sys

from jevdual.menu import OPERATIONS, Candidate, Menu
from jevdual.policy import JevPolicy, StepContext


def menu() -> Menu:
    cands = (
        Candidate(1, "Home", "a", ("click",), href="/"),
        Candidate(2, "About", "a", ("click",), href="/about.html"),
        Candidate(3, "Search here", "input", ("type", "enter"), input_type="search", value=""),
        Candidate(4, "Delete account", "button", ("click",), section="Danger zone"),
    )
    by_op = {op: tuple(c for c in cands if op in c.operations) for op in OPERATIONS}
    return Menu(
        url="http://127.0.0.1/",
        title="Spike Home",
        page_text="Spike Home. About. Search here. Danger zone: Delete account.",
        candidates=cands,
        by_operation={k: v for k, v in by_op.items() if v},
    )


async def main() -> int:
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY not set; skipping live check")
        return 0
    from typesafe_sdk import AsyncTypeSafeClient

    async with AsyncTypeSafeClient() as client:
        policy = JevPolicy(client)
        d = await policy.decide(
            menu(), StepContext(task="Open the About page", requirements=("About page is open",))
        )
    print(json.dumps({k: v for k, v in d.__dict__.items() if k != "raw"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
