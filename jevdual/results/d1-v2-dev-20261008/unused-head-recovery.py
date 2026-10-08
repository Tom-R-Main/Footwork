"""Post-hoc, offline replay of D1's unused target-head refusals.

Run with the existing environment: .venv/bin/python results/d1-v2-dev-20261008/unused-head-recovery.py
This creates only unused-head-recovery.json beside this script. It never creates
provider clients, reads credentials, or sends requests. Primary results stay intact.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "evals"))

import d1_compare as d
from jevdual.decisions import _parse


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main() -> None:
    prepared = {p.case["id"]: p for p in await d.prepared_cases()}
    rows = json.loads((RUN / "results.json").read_text())
    shared = {x["id"]: x for x in json.loads((RUN / "shared-inputs.json").read_text())}
    started = json.loads((RUN / "started.json").read_text())
    primary = json.loads((RUN / "summary.json").read_text())["roles"]["actions"]["decisions"]
    recovered = []
    for row in rows:
        if row["backend"] != "decisions" or row["role"] != "actions" or not row.get("error"):
            continue
        if row["error"]["code"] != "refusal":
            raise ValueError("Exploration only covers saved per-head refusals")
        p = prepared[row["id"]]
        original = shared[row["id"]]
        # ReplayClient will also compare the full rebuilt state/question hashes
        # when the unchanged JevPolicy asks for its original request below.
        if d.digest(p.state) != d.digest(original["state"]):
            raise ValueError("Original state projection changed")
        if d.digest(d.question_data(p.questions)) != d.digest(original["questions"]):
            raise ValueError("Original logical questions changed")
        if sha256_bytes(d.baseline_body(p)) != original["baseline_body_sha256"]:
            raise ValueError("Original baseline request changed")
        if sha256_bytes(d.candidate_body(p)) != original["candidate_body_sha256"]:
            raise ValueError("Original candidate request changed")

        raw = copy.deepcopy(row["native_response"])
        refused = {a["name"] for a in raw["answers"] if a["type"] == "refusal"}
        operation = next(a["choice"] for a in raw["answers"] if a["name"] == "operation")
        if operation in d.OPERATIONS or not refused or any(not n.endswith("_target") for n in refused):
            raise ValueError("A refused head may be required by the chosen operation")
        retained = {name: q for name, q in p.questions.items() if name not in refused}
        raw["answers"] = [a for a in raw["answers"] if a["name"] not in refused]
        # Validate the complete retained answer set, option distributions,
        # selected argmax, predicate values, native confidence and model/usage.
        batch = _parse(raw, d.translate_questions(retained), 0)
        response = d.bridge_response(batch, retained)
        # Use the original full captured request and original case/arbiter,
        # not a rebuilt smaller action menu or invented answers for refusals.
        output = await d.baseline_result(p, response)
        recovered.append(
            {
                "id": row["id"],
                "repeat": row["repeat"],
                "original_error": row["error"],
                "original_state_sha256": d.digest(p.state),
                "original_logical_questions_sha256": d.digest(d.question_data(p.questions)),
                "original_baseline_body_sha256": original["baseline_body_sha256"],
                "original_candidate_body_sha256": original["candidate_body_sha256"],
                "original_request_replay_verified": True,
                "removed_refused_names": sorted(refused),
                "retained_head_names": list(retained),
                "retained_heads_validated": True,
                "retained_native_answers": raw["answers"],
                "operation": output["operation"],
                "target_id": output["target_id"],
                "exact_pair_correct": d.correctness(p, output),
                "admitted": output["admitted"],
                "arbiter_kind": output["arbiter_kind"],
                "escalation_reason": output["reason"],
            }
        )
    if len(recovered) != 9 or not all(x["exact_pair_correct"] and not x["admitted"] for x in recovered):
        raise ValueError("Expected recovery result changed; inspect without modifying primary results")
    originals = [r for r in rows if r["role"] == "actions" and r["backend"] == "decisions"]
    correct = {(r["id"], r["repeat"]): bool(r.get("correct")) for r in originals}
    correct.update({(r["id"], r["repeat"]): r["exact_pair_correct"] for r in recovered})
    case_ids = {r["id"] for r in originals}
    result = {
        "classification": "post-hoc exploratory dependency-aware consumption; primary metrics unchanged",
        "measured_commit": started["commit"],
        "provider_requests": 0,
        "fabricated_answer_values": 0,
        "replay_source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                Path(__file__).resolve(),
                ROOT / "evals/d1_compare.py",
                ROOT / "python/jevdual/decisions.py",
                ROOT / "python/jevdual/policy.py",
                ROOT / "python/jevdual/arbiter.py",
            )
        },
        "input_sha256": {
            name: sha256(RUN / name)
            for name in ("results.json", "shared-inputs.json", "started.json", "summary.json")
        },
        "primary": {
            "correct_replays": primary["correct_replays"],
            "all_three_correct_cases": primary["all_three_correct_cases"],
            "errors": primary["errors"],
        },
        "exploratory": {
            "recovered_replays": len(recovered),
            "correct_replays": sum(correct.values()),
            "all_three_correct_cases": sum(all(correct[(i, n)] for n in range(d.REPLAYS)) for i in case_ids),
            "recovered_admitted_replays": sum(r["admitted"] for r in recovered),
        },
        "recovered": recovered,
        "limitation": "This changes refusal consumption after observing results. It is not preregistered validation, does not alter primary counts, and proves no live dispatch behavior.",
    }
    d.write_json(RUN / "unused-head-recovery.json", result)
    print(json.dumps(result["exploratory"], sort_keys=True))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    asyncio.run(main())
