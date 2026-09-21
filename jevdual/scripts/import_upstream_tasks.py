"""Import browser-use's judge-graded tasks into a jevdual task file.

Sources (pinned submodule, MIT):
- ``tests/agent_tasks/*.yaml``: ``task`` + ``judge_context`` criteria.
- ``tests/mind2web_data/processed.json``: Mind2Web tasks (``confirmed_task`` + one reference action
  path). Only sites in ``HOSTS`` are imported, so every task has a real https start page.

All imported tasks use the ``judge`` predicate: the criteria become the upstream judge's ground truth
and the row is reported as graded-by-judge, never mixed into predicate pass rates. Mind2Web tasks
carry dates and inventory that drift; the judge's ``impossible_task`` flag and the "no arm passes"
rule handle those.

    uv run python scripts/import_upstream_tasks.py --mind2web 40 --seed 7 > evals/tasks/live-upstream.yaml
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "browser-use" / "tests"
HOSTS = {
    "united": "https://www.united.com/",
    "budget": "https://www.budget.com/",
    "newegg": "https://www.newegg.com/",
    "spothero": "https://spothero.com/",
    "uniqlo": "https://www.uniqlo.com/us/en/",
    "resy": "https://resy.com/",
    "yelp": "https://www.yelp.com/",
    "kayak": "https://www.kayak.com/",
    "gamestop": "https://www.gamestop.com/",
    "imdb": "https://www.imdb.com/",
    "espn": "https://www.espn.com/",
    "exploretock": "https://www.exploretock.com/",
    "ticketcenter": "https://www.ticketcenter.com/",
    "amtrak": "https://www.amtrak.com/",
    "carmax": "https://www.carmax.com/",
    "cabelas": "https://www.cabelas.com/",
    "target": "https://www.target.com/",
    "ikea": "https://www.ikea.com/us/en/",
    "qatarairways": "https://www.qatarairways.com/",
    "underarmour": "https://www.underarmour.com/",
    "rottentomatoes": "https://www.rottentomatoes.com/",
    "goodreads": "https://www.goodreads.com/",
    "discogs": "https://www.discogs.com/",
    "ryanair": "https://www.ryanair.com/",
    "eventbrite": "https://www.eventbrite.com/",
    "foxsports": "https://www.foxsports.com/",
    "nfl": "https://www.nfl.com/",
    "ultimate-guitar": "https://www.ultimate-guitar.com/",
    "seatgeek": "https://seatgeek.com/",
    "soundcloud": "https://soundcloud.com/",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def first_host(text: str) -> str | None:
    m = re.search(r"\b([a-z0-9-]+\.(?:com|org|io|ai|net))\b", text.lower())
    return f"https://{m.group(1)}/" if m else None


def agent_tasks() -> list[dict]:
    out = []
    for f in sorted((ROOT / "agent_tasks").glob("*.yaml")):
        d = yaml.safe_load(f.read_text())
        start = first_host(d["task"]) or "https://duckduckgo.com/"
        criteria = "; ".join(d.get("judge_context") or ["The agent must solve the task"])
        out.append(
            {
                "id": "up-" + slug(d.get("name") or f.stem),
                "task": d["task"].strip(),
                "start_url": start,
                "tags": ["live", "judged", "upstream"],
                "requirements": [c.strip() for c in (d.get("judge_context") or ["Task solved"])][:6],
                "predicate": {"kind": "judge", "value": criteria},
                "source": f"browser-use/tests/agent_tasks/{f.name}",
            }
        )
    return out


def mind2web(n: int, seed: int) -> list[dict]:
    data = json.loads((ROOT / "mind2web_data" / "processed.json").read_text())
    rows = [d for d in data if d["website"] in HOSTS and 3 <= len(d["action_reprs"]) <= 12]
    rng = random.Random(seed)
    rng.shuffle(rows)
    # round-robin across sites so no single site dominates
    by_site: dict[str, list[dict]] = {}
    for d in rows:
        by_site.setdefault(d["website"], []).append(d)
    picked: list[dict] = []
    while len(picked) < n and any(by_site.values()):
        for site in sorted(by_site):
            if by_site[site] and len(picked) < n:
                picked.append(by_site[site].pop())
    out = []
    for d in picked:
        path = "; ".join(d["action_reprs"])
        out.append(
            {
                "id": "m2w-" + d["website"] + "-" + d["id"][:8],
                "task": d["confirmed_task"].strip(),
                "start_url": HOSTS[d["website"]],
                # no URL checkpoints exist for these, so they do not carry the multistep tag (Q4 needs checkpoints)
                "tags": ["live", "judged", "mind2web"],
                "requirements": [d["confirmed_task"].strip()[:120]],
                "predicate": {
                    "kind": "judge",
                    "value": (
                        f"Task: {d['confirmed_task'].strip()} Domain: {d['domain']}/{d['subdomain']}. "
                        f"One valid reference path (other paths are acceptable): {path}. "
                        "Success means the final page or answer reflects the completed task; "
                        "a page that changed since the reference was recorded is not a failure by itself."
                    ),
                },
                "source": f"mind2web:{d['id']}",
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mind2web", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    tasks = agent_tasks() + mind2web(args.mind2web, args.seed)
    doc = {"split": "live-upstream", "tasks": tasks}
    sys.stdout.write(
        "# Generated by scripts/import_upstream_tasks.py from the pinned browser-use submodule (MIT).\n"
        "# Judge-graded: every predicate is `judge`; rows report as graded-by-judge, never as predicate passes.\n"
    )
    yaml.safe_dump(doc, sys.stdout, sort_keys=False, allow_unicode=True, width=200)


if __name__ == "__main__":
    main()
