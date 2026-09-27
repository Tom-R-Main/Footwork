"""Package E (notebook V2): false acceptance and false rejection of done claims, measured apart.

Each case in ``evals/fixtures/claims_audit.yaml`` is a done on a synthetic page, labelled accept or
reject before scoring. Two layers are scored in both claim-check modes (``page``, Q12's; ``page_and_fields``,
the strict one):

- the claim check alone: does any sentence carry a fact found on the page (the verifier's no-fact rule);
- the full verifier (``Verifier.verify``: Jev's complete and unmet judgments, then the claim check),
  with ``--jev``, which calls the TypeSafe API.

    uv run python -m evals.claims_audit [--jev] [--out results/claims-audit-<date>]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import yaml
from jevdual.menu import Candidate, Menu
from jevdual.verify import Verifier, VerifyPolicy, check_claims, field_values

FIXTURE = Path(__file__).parent / "fixtures" / "claims_audit.yaml"
MODES = ("page", "page_and_fields")


def load() -> tuple[dict[str, Menu], list[dict[str, Any]]]:
    raw = yaml.safe_load(FIXTURE.read_text())
    menus = {}
    for name, p in raw["pages"].items():
        cands = tuple(
            Candidate(id=i + 1, label=f["label"], role="textbox", operations=("type",), value=str(f["value"]))
            for i, f in enumerate(p.get("fields") or [])
        )
        text = p["text"].strip()
        menus[name] = Menu(
            url=p["url"], title=p["title"], page_text=text, candidates=cands, by_operation={}, full_text=text
        )
    return menus, raw["cases"]


def claim_check_accepts(case: dict[str, Any], menu: Menu, mode: str) -> bool:
    """The deterministic layer: the verifier's no-fact rule passes when some sentence is evidence."""
    strict = mode == "page_and_fields"
    claims = check_claims(
        case["answer"],
        menu.full_text or menu.page_text,
        field_text=field_values(menu) if strict else "",
        strict=strict,
    )
    return any(c.is_evidence for c in claims) or (not case.get("answer_expected") and bool(claims))


async def verifier_accepts(client: Any, case: dict[str, Any], menu: Menu, mode: str) -> tuple[bool, str]:
    v = await Verifier(client, policy=VerifyPolicy(claim_evidence=mode)).verify(
        case["task"],
        tuple(case["requirements"]),
        menu,
        case["answer"],
        answer_expected=bool(case.get("answer_expected")),
    )
    return v.band == "accept", f"{v.band}: {v.reason}"[:200]


def score(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    acc = [r for r in rows if r["expect"] == "accept"]
    rej = [r for r in rows if r["expect"] == "reject"]
    return {
        "false_acceptance": f"{sum(r[key] for r in rej)}/{len(rej)}",
        "false_rejection": f"{sum(not r[key] for r in acc)}/{len(acc)}",
        "falsely_accepted": [r["id"] for r in rej if r[key]],
        "falsely_rejected": [r["id"] for r in acc if not r[key]],
    }


async def main(jev: bool, out: Path | None) -> None:
    menus, cases = load()
    rows: list[dict[str, Any]] = []
    client = None
    if jev:
        from jevdual.keys import load_keys
        from typesafe_sdk import AsyncTypeSafeClient

        load_keys()
        client = AsyncTypeSafeClient()
        await client.__aenter__()
    try:
        for case in cases:
            menu = menus[case["page"]]
            row: dict[str, Any] = {"id": case["id"], "expect": case["expect"]}
            for mode in MODES:
                row[f"claims_{mode}"] = claim_check_accepts(case, menu, mode)
                if client is not None:
                    row[f"verifier_{mode}"], row[f"why_{mode}"] = await verifier_accepts(
                        client, case, menu, mode
                    )
            rows.append(row)
    finally:
        if client is not None:
            await client.__aexit__(None, None, None)
    summary = {f"claims_{m}": score(rows, f"claims_{m}") for m in MODES}
    if jev:
        summary |= {f"verifier_{m}": score(rows, f"verifier_{m}") for m in MODES}
    print(json.dumps(summary, indent=1))
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1))
        (out / "summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", action="store_true", help="also score the full verifier (TypeSafe API calls)")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    asyncio.run(main(a.jev, a.out))
