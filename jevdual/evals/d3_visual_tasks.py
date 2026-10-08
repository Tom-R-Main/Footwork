"""D3 captured visual proposal pilot. Offline preflight by default; no runtime routing change."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import importlib
import importlib.metadata
import io
import json
import math
import random
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
from jevdual.decisions import ENDPOINT, MODEL, DecisionsError, _parse, _provider_error, _unique_object
from jevdual.policy import JEV_MODEL
from PIL import Image

from evals.d1_compare import Budget, BudgetExceeded, checkout_dirty, key, write_json

ROOT = Path(__file__).resolve().parents[1]
SEED = 10082028
REPLAYS = 3
ARMS = ("jev_text", "decisions_text", "decisions_combined")
MAX_BODY = 48_000
MAX_INPUT = 64_000
PRICES = {"jev": 0.042, "decisions": 0.10}
NAME = "proposal_supported"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class VisualBudget(Budget):
    """Own D3 bound:48k body and exactly one predicate per request."""

    def reserve(self, provider: str, body: bytes, question_count: int = 1) -> int:
        if provider not in PRICES or len(body) > MAX_BODY or question_count != 1:
            raise BudgetExceeded("D3 request exceeds frozen body/provider/question limit")
        amount = MAX_INPUT * PRICES[provider] / 1e6
        if self.committed + amount > self.cap + 1e-12:
            raise BudgetExceeded("pilot budget exhausted")
        self.entries.append(
            {
                "provider": provider,
                "reserved_usd": amount,
                "charged_upper_usd": amount,
                "usage_known": False,
                "input_tokens_upper": MAX_INPUT,
                "question_count": 1,
                "body_bytes": len(body),
                "request_sha256": sha(body),
            }
        )
        return len(self.entries) - 1


def question(case: dict) -> dict:
    item = case["question"]
    instructions = item if isinstance(item, str) else item["instructions"]
    return {"name": NAME, "type": "predicate", "instructions": instructions}


def band(probability: Any) -> str:
    if type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("invalid predicate probability")
    return "true" if probability >= 0.8 else "false" if probability <= 0.2 else "unknown"


def judged_correct(case: dict, native_band: str) -> bool:
    return (
        native_band in ("unknown", "refusal")
        if case["expected"] is None
        else (native_band == ("true" if case["expected"] else "false"))
    )


def image_receipts(case: dict) -> dict[str, dict]:
    capture = case.get("capture", {})
    receipts = {item["image"]: item for item in capture.get("observations", []) if "image" in item}
    for item in capture.get("images", []):
        receipts[item["path"]] = {
            "image": item["path"],
            "image_sha256": item["sha256"],
            "dimensions": item["dimensions"],
        }
    return receipts


def load_cases(path: Path) -> tuple[dict, list[dict]]:
    """Validate frozen independent metadata; never inject these labels into wire evidence."""
    path = path.resolve()
    manifest = json.loads(path.read_text())
    if isinstance(manifest, list):
        manifest = {"cases": manifest}
    cases = manifest["cases"]
    if len(cases) != 24 or len({c["id"] for c in cases}) != 24:
        raise ValueError("D3 requires24 unique frozen cases")
    families = {}
    surfaces = {"browser": 0, "native": 0}
    for case in cases:
        kind = (
            "browser"
            if case["surface"].startswith("browser")
            else "native"
            if case["surface"].startswith("native")
            else None
        )
        if kind is None:
            raise ValueError("unknown capture surface")
        surfaces[kind] += 1
        families.setdefault(case["family"], []).append(case)
        if case["expected"] is not None and type(case["expected"]) is not bool:
            raise ValueError("expected must be true/false/null")
        if not isinstance(case.get("text"), str) or not question(case)["instructions"]:
            raise ValueError("missing observed text/question")
        if not case.get("images"):
            raise ValueError("missing actual capture")
        receipts = image_receipts(case)
        for relative in case["images"]:
            image_path = (path.parent / relative).resolve()
            if not image_path.is_relative_to(path.parent) or image_path.suffix.lower() != ".png":
                raise ValueError("image must be a relative capture PNG")
            data = image_path.read_bytes()
            receipt = receipts.get(relative)
            if receipt is None or sha(data) != receipt.get("image_sha256"):
                raise ValueError("capture PNG hash mismatch/missing receipt")
            with Image.open(io.BytesIO(data)) as image:
                if image.format != "PNG" or list(image.size) != receipt.get("dimensions"):
                    raise ValueError("capture PNG dimension/type mismatch")
                if image.width > 900 or image.height > 600:
                    raise ValueError("capture exceeds frozen dimensions")
        for arm in ARMS:
            if len(wire_body(case, arm, path.parent)) > MAX_BODY:
                raise ValueError("request body exceeds48k frozen limit")
    if (
        surfaces != {"browser": 12, "native": 12}
        or len(families) != 6
        or any(len(v) != 4 for v in families.values())
    ):
        raise ValueError("frozen six-family surface counts changed")
    return manifest, cases


def wire_body(case: dict, arm: str, image_root: Path) -> bytes:
    """Only observed text, question and PNG bytes enter provider inputs."""
    if arm not in ARMS:
        raise ValueError("unknown D3 arm")
    if arm == "jev_text":
        from typesafe_sdk import Noul
        from typesafe_sdk._core.json import serialize

        return serialize(
            {
                "state": case["text"],
                "model": JEV_MODEL,
                "questions": {NAME: Noul(instructions=question(case)["instructions"])},
            }
        )
    input_data: Any = case["text"]
    if arm == "decisions_combined":
        content = [{"type": "input_text", "text": case["text"]}]
        for relative in case["images"]:
            image = base64.b64encode((image_root / relative).read_bytes()).decode("ascii")
            content.append({"type": "input_image", "image_url": "data:image/png;base64," + image})
        input_data = [{"role": "user", "content": content}]
    return json.dumps(
        {"model": MODEL, "input": input_data, "questions": [question(case)]},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()


class VisualDecisions:
    """D3 own48k pooled HTTP surface; strict shared parser, no retry/redirect."""

    def __init__(self, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None):
        self._key = api_key
        self._client = httpx.AsyncClient(
            transport=transport, timeout=60, follow_redirects=False, trust_env=False
        )

    async def call(self, body: bytes):
        if len(body) > MAX_BODY:
            raise DecisionsError("request_bound")
        spec = json.loads(body)
        if spec.get("model") != MODEL or len(spec.get("questions", [])) != 1:
            raise DecisionsError("request_contract")
        started = time.perf_counter()
        try:
            response = await self._client.post(
                ENDPOINT,
                content=body,
                headers={"Authorization": "Bearer " + self._key, "Content-Type": "application/json"},
            )
        except httpx.RequestError:
            raise DecisionsError("network") from None
        if not 200 <= response.status_code < 300:
            raise DecisionsError(
                f"http_{response.status_code}", provider_error=_provider_error(response.content, self._key)
            )
        try:
            raw = json.loads(response.content, object_pairs_hook=_unique_object)
        except (ValueError, UnicodeError):
            raise DecisionsError("invalid_json") from None
        return _parse(raw, spec["questions"], time.perf_counter() - started)

    async def aclose(self) -> None:
        await self._client.aclose()


def coverage(cases: list[dict]) -> dict:
    gaps = []
    positives = []
    for case in cases:
        conformance = case.get("conformance", {})
        verified = conformance.get("passed") is True or conformance.get("postcondition") is True
        if not verified:
            gaps.append(
                {
                    "id": case["id"],
                    "surface": case["surface"],
                    "family": case["family"],
                    "conformance": conformance,
                }
            )
        if case["expected"] is True:
            positives.append({"id": case["id"], "executable_path_verified": verified})
    return {
        "cases": len(cases),
        "conformance_gaps": gaps,
        "positive_paths": positives,
        "all_conformance_verified": not gaps,
        "scope": "authored captures and reconstructed one-step fixture checks; not an autonomous real-app journey",
    }


def capture_ms(case: dict) -> float | None:
    capture = case.get("capture", {})
    value = capture.get("phase_total_ms", capture.get("capture_ms"))
    return float(value) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def timing(values: list[float]) -> dict:
    if not values:
        return {}
    ordered = sorted(values)
    return {
        "n": len(values),
        "median_ms": statistics.median(ordered),
        "p95_ms": ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)],
    }


def summarize(rows: list[dict], cases: list[dict], expected_attempts: int = 216) -> dict:
    summary = {
        "complete": len(rows) == expected_attempts and not any(r.get("band") == "error" for r in rows),
        "attempts": len(rows),
        "expected_attempts": expected_attempts,
        "coverage": coverage(cases),
        "latency_scope": "captured evidence replay; capture+request is estimate; execution is reconstructed one-step",
        "arms": {},
    }
    for arm in ARMS:
        arm_rows = [r for r in rows if r["arm"] == arm]
        record = {
            "attempts": len(arm_rows),
            "correct_replays": sum(r.get("correct", False) for r in arm_rows),
            "refusals": sum(r.get("band") == "refusal" for r in arm_rows),
            "unknowns": sum(r.get("band") == "unknown" for r in arm_rows),
            "errors": sum(r.get("band") == "error" for r in arm_rows),
            "request_timing": timing([r["request_ms"] for r in arm_rows]),
            "capture_to_judgment_estimate": timing(
                [
                    r["capture_to_judgment_estimate_ms"]
                    for r in arm_rows
                    if r.get("capture_to_judgment_estimate_ms") is not None
                ]
            ),
            "all_three_correct": [],
            "positive": [],
            "negative": [],
            "ambiguous": [],
            "invalid_confident_positive": [],
            "execution": [],
            "ambiguous_safe_nonacceptance_replays": {"false": 0, "unknown": 0, "refusal": 0},
            "ambiguous_all_three_safe_nonacceptance": [],
            "unknown_usage_attempts": sum(
                not r.get("budget", {}).get("usage_known", False) for r in arm_rows
            ),
            "cost_upper_usd": sum(r.get("budget", {}).get("charged_upper_usd", 0) for r in arm_rows),
            "by_family": {},
            "by_surface": {},
        }
        for case in cases:
            mine = [r for r in arm_rows if r["id"] == case["id"]]
            all_three = len(mine) == REPLAYS and all(r.get("correct") for r in mine)
            label = (
                "ambiguous" if case["expected"] is None else "positive" if case["expected"] else "negative"
            )
            record[label].append(
                {"id": case["id"], "all_three_correct": all_three, "measured_replays": len(mine)}
            )
            if case["expected"] is None:
                for outcome in ("false", "unknown", "refusal"):
                    record["ambiguous_safe_nonacceptance_replays"][outcome] += sum(
                        r.get("band") == outcome for r in mine
                    )
                if len(mine) == REPLAYS and all(
                    r.get("band") in ("false", "unknown", "refusal") for r in mine
                ):
                    record["ambiguous_all_three_safe_nonacceptance"].append(case["id"])
            if all_three:
                record["all_three_correct"].append(case["id"])
            if case["expected"] is not True and any(r.get("band") == "true" for r in mine):
                record["invalid_confident_positive"].append(case["id"])
            for r in mine:
                if "execution" in r:
                    record["execution"].append({"id": case["id"], "band": r.get("band"), **r["execution"]})
            for grouping in ("family", "surface"):
                group = record["by_" + grouping].setdefault(
                    case[grouping], {"cases": 0, "all_three_correct": 0}
                )
                group["cases"] += 1
                group["all_three_correct"] += int(all_three)
        record["execution_timing"] = timing([r["execution_ms"] for r in arm_rows if "execution_ms" in r])
        record["wrong_effects"] = [
            r["id"]
            for r in arm_rows
            if r.get("execution", {}).get("wrong_effect") is True
            or (
                r.get("execution", {}).get("dispatched") is True
                and r.get("execution", {}).get("postcondition_observed") is False
            )
        ]
        record["execution_coverage_gaps"] = [
            r["id"] for r in arm_rows if r.get("execution", {}).get("coverage_error")
        ]
        for grouping in ("family", "surface"):
            for name, group in record["by_" + grouping].items():
                mine = [r for r in arm_rows if r[grouping] == name]
                group.update(
                    attempts=len(mine),
                    correct_replays=sum(r.get("correct", False) for r in mine),
                    errors=sum(r.get("band") == "error" for r in mine),
                    refusals=sum(r.get("band") == "refusal" for r in mine),
                    unknowns=sum(r.get("band") == "unknown" for r in mine),
                    request_timing=timing([r["request_ms"] for r in mine]),
                    execution_timing=timing([r["execution_ms"] for r in mine if "execution_ms" in r]),
                    capture_to_judgment_estimate=timing(
                        [
                            r["capture_to_judgment_estimate_ms"]
                            for r in mine
                            if r.get("capture_to_judgment_estimate_ms") is not None
                        ]
                    ),
                )
        summary["arms"][arm] = record
    return summary


def normalize_cases(cases: list[dict], prefix: str) -> list[dict]:
    result = []
    for original in cases:
        case = json.loads(json.dumps(original))
        case["images"] = [f"{prefix}/{relative}" for relative in case["images"]]
        for item in case.get("capture", {}).get("observations", []):
            if "image" in item:
                item["image"] = f"{prefix}/{item['image']}"
        for item in case.get("capture", {}).get("images", []):
            item["path"] = f"{prefix}/{item['path']}"
        if "expected" not in case:
            case["expected"] = case["oracle"]["expected"]
        result.append(case)
    return result


def capture_all(out: Path) -> None:
    if out.exists():
        raise ValueError("capture output must be fresh")
    out.mkdir(parents=True)
    cases, errors = [], []
    for surface in ("browser", "native"):
        module = importlib.import_module("evals.d3_" + surface)
        try:
            cases += normalize_cases(module.capture(out / surface), surface)
        except Exception as exc:  # noqa: BLE001 - coverage failures are preserved without secret error text
            errors.append({"surface": surface, "error_type": type(exc).__name__})
    write_json(
        out / "manifest.json",
        {
            "version": 1,
            "cases": cases,
            "capture_errors": errors,
            "scope": "authored controlled browser/native captures",
        },
    )
    write_json(out / "coverage.json", coverage(cases))
    print(json.dumps({"captured": len(cases), "surface_errors": errors}))


def committed_file(path: Path) -> bool:
    try:
        subprocess.check_output(
            ["git", "ls-files", "--error-unmatch", str(path.resolve())], cwd=ROOT, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return False
    return True


def execution_recipe(case: dict) -> dict:
    """Remove scoring labels from executor input; retain bound proposal and fixture setup recipe."""
    return {k: v for k, v in case.items() if k not in ("expected", "oracle", "conformance")}


async def replay(case: dict, accepted: bool, out: Path) -> dict:
    surface = "browser" if case["surface"].startswith("browser") else "native"
    module = importlib.import_module("evals.d3_" + surface)
    return await asyncio.to_thread(module.replay_case, execution_recipe(case), accepted, out)


def source_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


async def run(cases_path: Path, out: Path, prior_cost: float, cap: float = 5) -> None:
    from typesafe_sdk import AsyncTypeSafeClient, Noul, RetryPolicy

    if out.exists():
        raise ValueError("run output must be fresh")
    if await asyncio.to_thread(checkout_dirty):
        raise ValueError("commit measured code/captures before paid calls")
    manifest, cases = load_cases(cases_path)
    files = [cases_path, *(cases_path.parent / image for case in cases for image in case["images"])]
    if not all([await asyncio.to_thread(committed_file, path) for path in files]):
        raise ValueError("manifest and capture PNGs must be committed before paid calls")
    budget = VisualBudget(cap, prior_cost)
    # Validate all bodies before reading opaque credentials.
    bodies = {(case["id"], arm): wire_body(case, arm, cases_path.parent) for case in cases for arm in ARMS}
    candidate = VisualDecisions(key("OPENAI_API_KEY"))
    baseline = AsyncTypeSafeClient(
        api_key=key("TYPESAFE_API_KEY"), timeout=60, retry=RetryPolicy(max_retries=0)
    )
    out.mkdir(parents=True)
    write_json(
        out / "started.json",
        {
            "commit": await asyncio.to_thread(source_commit),
            "manifest_sha256": sha(cases_path.read_bytes()),
            "models": [JEV_MODEL, MODEL],
            "seed": SEED,
            "replays": REPLAYS,
            "bands": {"true": 0.8, "false": 0.2},
            "body_bound": MAX_BODY,
            "prices": PRICES,
            "versions": {
                name: importlib.metadata.version(name) for name in ("httpx", "typesafe-sdk", "pillow")
            },
            "prior_cost_upper_usd": prior_cost,
            "cap_usd": cap,
            "scope": coverage(cases)["scope"],
        },
    )
    write_json(out / "frozen-inputs.json", manifest)
    rows, halted = [], None
    rng = random.Random(SEED)
    schedule = []
    ordered = list(cases)
    rng.shuffle(ordered)
    for case in ordered:
        for repeat in range(REPLAYS):
            arms = list(ARMS)
            rng.shuffle(arms)
            schedule += [(case, repeat, arm) for arm in arms]
    try:
        for case, repeat, arm in schedule:
            body = bodies[(case["id"], arm)]
            try:
                index = budget.reserve("jev" if arm == "jev_text" else "decisions", body)
            except BudgetExceeded as exc:
                halted = str(exc)
                break
            write_json(out / "budget.json", budget.snapshot())
            row = {
                "id": case["id"],
                "family": case["family"],
                "surface": case["surface"],
                "arm": arm,
                "repeat": repeat,
                "expected": case["expected"],
                "request_sha256": sha(body),
                "evidence_sha256": sha(case["text"].encode()),
                "image_sha256": [image_receipts(case)[im]["image_sha256"] for im in case["images"]],
                "correct": False,
                "capture_ms": capture_ms(case),
            }
            started, input_tokens = time.perf_counter(), None
            try:
                if arm == "jev_text":
                    response = await baseline.system_one(
                        case["text"],
                        {NAME: Noul(instructions=question(case)["instructions"])},
                        model=JEV_MODEL,
                        retry=RetryPolicy(max_retries=0),
                    )
                    input_tokens = response.usage.input_tokens
                    row["native_response"], row["model"] = response.model_dump(mode="json"), response.model
                    probability = response.nouls[NAME].noul
                else:
                    response = await candidate.call(body)
                    input_tokens = response.input_tokens
                    row["native_response"], row["model"] = response.raw, response.model
                    probability = response.answers[NAME].probability
                row["probability"], row["band"] = probability, band(probability)
                row["correct"] = judged_correct(case, row["band"])
            except Exception as exc:  # noqa: BLE001 - retain every failed reservation without arbitrary exception text
                code = exc.code if isinstance(exc, DecisionsError) else None
                status = getattr(exc, "status", None)
                row["band"] = "refusal" if code == "refusal" else "error"
                row["error"] = {"type": type(exc).__name__, "code": code, "http_status": status}
                if code == "refusal":
                    row["correct"] = judged_correct(case, "refusal")
                input_tokens = getattr(exc, "input_tokens", input_tokens)
                raw = getattr(exc, "raw", None)
                if isinstance(raw, dict):
                    row["native_response"] = raw
                provider_error = getattr(exc, "provider_error", None)
                if isinstance(provider_error, dict):
                    row["provider_error"] = provider_error
                if status in (400, 401, 403, 404, 422) or code in {
                    f"http_{n}" for n in (400, 401, 403, 404, 422)
                }:
                    halted = "provider contract/account access failure"
            row["request_ms"] = (time.perf_counter() - started) * 1000
            row["capture_to_judgment_estimate_ms"] = (
                None if row["capture_ms"] is None else row["capture_ms"] + row["request_ms"]
            )
            try:
                row["budget"] = budget.settle(index, input_tokens)
            except BudgetExceeded as exc:
                row["budget"], halted = dict(budget.entries[index]), str(exc)
            # Judgment/cost durable before reconstructed execution; no oracle informs dispatch.
            rows.append(row)
            write_json(out / "results.json", rows)
            write_json(out / "budget.json", budget.snapshot())
            if repeat == 0 and not halted:
                execution_start = time.perf_counter()
                try:
                    row["execution"] = await replay(
                        case, row.get("band") == "true", out / "execution" / arm / case["id"]
                    )
                except Exception as exc:  # noqa: BLE001 - surface failure is coverage, not model error
                    row["execution"] = {"verified": False, "coverage_error": type(exc).__name__}
                row["execution_ms"] = (time.perf_counter() - execution_start) * 1000
            write_json(out / "results.json", rows)
            write_json(out / "summary.json", summarize(rows, cases))
            if len(rows) % 9 == 0 or halted:
                print(f"{len(rows)}/216 attempts;upper ${budget.committed:.6f}", flush=True)
            if halted:
                break
    finally:
        await candidate.aclose()
        await baseline.aclose()
        write_json(out / "budget.json", budget.snapshot())
        write_json(out / "results.json", rows)
        write_json(out / "summary.json", summarize(rows, cases))
        write_json(
            out / "closed.json",
            {
                "halted": halted,
                "attempts": len(rows),
                "scheduled": 216,
                "complete": summarize(rows, cases)["complete"],
            },
        )


def preflight(path: Path) -> dict:
    _, cases = load_cases(path)
    return {
        "offline": True,
        "cases": len(cases),
        "scheduled_attempts": len(cases) * len(ARMS) * REPLAYS,
        "body_max_bytes": max(len(wire_body(case, arm, path.parent)) for case in cases for arm in ARMS),
        "coverage": coverage(cases),
        "unknown_usage_upper_this_run": 72 * 64000 * (0.042 + 2 * 0.1) / 1e6,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--capture", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--prior-cost", type=float)
    parser.add_argument("--cap", type=float, default=5)
    args = parser.parse_args()
    if (args.capture or args.run) and (args.out is None or not args.out.resolve().is_relative_to(ROOT)):
        parser.error("capture/run require project-contained fresh --out")
    if args.capture:
        capture_all(args.out.resolve())
    elif args.cases is None:
        parser.error("preflight/run require --cases manifest")
    elif args.run:
        if args.prior_cost is None:
            parser.error("paid run requires explicit --prior-cost")
        asyncio.run(run(args.cases.resolve(), args.out.resolve(), args.prior_cost, args.cap))
    else:
        print(json.dumps(preflight(args.cases.resolve()), indent=2))


if __name__ == "__main__":
    main()
