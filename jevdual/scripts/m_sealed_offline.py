"""Validate without model calls; --run releases a sealed set for one measurement."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "python"), str(ROOT)]

from evals.m_sealed import cases, frozen_runtime, manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--candidate")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    rows = cases(a.folder)
    print(f"validated {len(rows)} cases in {len(rows) // 2} pairs; no judgments run")
    if not a.run:
        return
    if not a.candidate or not a.out:
        ap.error("--run requires --candidate and --out")
    if a.out.exists():
        ap.error("output must not exist; an interrupted measurement is not retried")
    sha = frozen_runtime(ROOT, a.candidate)
    a.out.mkdir(parents=True)
    meta = {"candidate": sha, "payload": manifest(ROOT, list(a.folder.glob("*.json"))), "replays": 3}
    (a.out / "started.json").write_text(json.dumps(meta, indent=2))
    import challenge_offline as runner

    original = runner.menu_of

    def menu_of(page):
        # Preserve author-specified observation completeness; no decision rule changes.
        return replace(
            original(page),
            omitted=page.get("omitted", {}),
            full_text=page.get("full_text", page.get("text", "")),
        )

    runner.menu_of = menu_of
    asyncio.run(runner.main(a.folder, 3, a.out / "results.json"))
    (a.out / "closed").write_text("One measurement; do not retry or tune on adoption cases.\n")


if __name__ == "__main__":
    main()
