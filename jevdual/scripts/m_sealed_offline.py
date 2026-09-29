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

from evals.m_sealed import backend_metadata, cases, frozen_runtime, manifest, verify_seal


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--candidate")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    a.folder = a.folder.resolve()
    if a.out:
        a.out = a.out.resolve()
    rows = cases(a.folder)
    print(f"validated {len(rows)} cases in {len(rows) // 2} pairs; no judgments run")
    if not a.run:
        return
    if not a.candidate or not a.out:
        ap.error("--run requires --candidate and --out")
    if a.out.exists():
        ap.error("output must not exist; an interrupted measurement is not retried")
    seal = verify_seal(ROOT, a.folder.name)
    sha = frozen_runtime(ROOT, a.candidate)
    if seal["purpose"] == "challenge" and sha != seal["challenge_candidate"]:
        ap.error("the first challenge measurement must use its frozen candidate")
    a.out.mkdir(parents=True)
    meta = {
        "candidate": sha,
        "payload": manifest(ROOT, list(a.folder.glob("*.json"))),
        "replays": 3,
        "runtime": backend_metadata(),
    }
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

    async def measure():
        from typesafe_sdk import AsyncTypeSafeClient

        runner.load_keys()
        result = []

        def persist(row):
            result.append(row)
            (a.out / "results.json").write_text(json.dumps(result, indent=2))

        async with AsyncTypeSafeClient() as client:
            verifier = runner.Verifier(client)
            for case in rows:
                probe = case.get("repeat_probe")
                if probe:
                    why = runner.repeat_of(
                        case["records"], probe["op"], url=probe.get("url", ""), label=probe.get("label", "")
                    )
                    persist(
                        {
                            "id": case["id"],
                            "arm": "repeat_probe",
                            "expect": probe["expect"],
                            "got": "pause" if why else "allow",
                            "reason": why,
                        }
                    )
                for arm in ("default", "effect_evidence"):
                    for replay in range(3):
                        verdict = await runner.judge(verifier, case, evidence=arm == "effect_evidence")
                        persist(
                            {
                                "id": case["id"],
                                "category": case["category"],
                                "arm": arm,
                                "repeat": replay,
                                "expect": case["expect"],
                                "truth_status": case["truth_status"],
                                **verdict,
                            }
                        )
                print(f"{case['id']}: recorded both arms", flush=True)

    asyncio.run(measure())
    (a.out / "closed").write_text("One measurement; do not retry or tune on adoption cases.\n")


if __name__ == "__main__":
    main()
