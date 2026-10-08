"""One explicitly registered diagnostic of D1's rejected request; no automatic retry."""

import asyncio
import hashlib
import json
import subprocess

from jevdual.decisions import DecisionsClient, DecisionsError, request_body

from evals.d1_compare import ROOT, Budget, checkout_dirty, key, write_json


async def main() -> None:
    prior = ROOT / "results/d1-dev-20261008"
    out = ROOT / "results/d1-diagnostic-20261008"
    if await asyncio.to_thread(checkout_dirty) or out.exists():
        raise ValueError("requires clean committed code and fresh diagnostic output")
    original = next(i for i in json.loads((prior / "shared-inputs.json").read_text()) if i["id"] == "R1-A12")
    evidence = json.dumps(original["state"], ensure_ascii=False, sort_keys=True)
    questions = original["candidate_questions"]
    body = request_body(evidence, questions)
    if hashlib.sha256(body).hexdigest() != original["candidate_body_sha256"]:
        raise ValueError("diagnostic differs from frozen rejected request")
    prior_upper = json.loads((prior / "budget.json").read_text())["reserved_or_usage_upper_usd"]
    budget = Budget(5, prior_upper)
    reservation = budget.reserve("decisions", body, len(questions))
    commit = (await asyncio.to_thread(subprocess.check_output, ["git", "rev-parse", "HEAD"], text=True)).strip()
    out.mkdir()
    write_json(out / "started.json", {
        "commit": commit,
        "source": str(prior.relative_to(ROOT)), "case": "R1-A12",
        "request_sha256": hashlib.sha256(body).hexdigest(), "no_retries": True,
    })
    write_json(out / "budget.json", budget.snapshot())
    tokens = None
    row = {"case": "R1-A12", "contract_valid": False}
    try:
        result = await DecisionsClient(key("OPENAI_API_KEY")).decide(evidence, questions)
        tokens = result.input_tokens
        row.update(contract_valid=True, native_response=result.raw)
    except DecisionsError as error:
        tokens = error.input_tokens
        row["error"] = {"code": error.code, "provider_error": error.provider_error}
    finally:
        try:
            row["accounting"] = budget.settle(reservation, tokens)
        finally:
            write_json(out / "result.json", row)
            write_json(out / "budget.json", budget.snapshot())
    print(json.dumps({"contract_valid": row["contract_valid"], "error": row.get("error"),
                      "cost_upper_usd": budget.committed}))


if __name__ == "__main__":
    asyncio.run(main())
