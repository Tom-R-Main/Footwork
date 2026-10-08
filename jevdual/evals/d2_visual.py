"""D2 synthetic pixel information ablation. Offline by default; --run explicitly spends.

Authored capability fixtures, never live data or evidence of production adoption.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import importlib.metadata
import io
import json
import math
import random
import statistics
import subprocess
import time
from pathlib import Path

import httpx
from jevdual.decisions import (
    ENDPOINT,
    MODEL,
    DecisionsClient,
    DecisionsError,
    PredicateAnswer,
    PredicateQuestion,
    _parse,
    _provider_error,
    _unique_object,
    request_body,
    serialize_questions,
)
from jevdual.policy import JEV_MODEL
from PIL import Image, ImageDraw, ImageFont

from evals.d1_compare import Budget, BudgetExceeded, checkout_dirty, key, write_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals/visual/d2"
MAX_BODY = 24_000
REPLAYS = 3
SEED = 10082027
ARMS = ("jev_text", "decisions_text", "decisions_image", "decisions_combined")
SIZE = (480, 300)
DEFINITIONS = (
    ("checkbox", "Preferences panel. Control labelled Receive updates.",
     "Is the Receive updates checkbox checked?", "A check mark is visibly inside its square.",
     "Its square is empty."),
    ("radio", "Plan panel. Radio options Standard and Extended.",
     "Is Standard the selected radio option?", "The Standard circle has a filled center.",
     "The Standard circle is empty and Extended has a filled center."),
    ("color_status", "Service panel. Labels Service status and Status legend.",
     "Does the Service status indicator signify healthy according to the visible legend?",
     "The indicator matches the legend color for Healthy.", "It matches the legend color for Fault."),
    ("modal_occlusion", "Workspace panel. Controls Save and Cancel; a dialog may overlay the workspace.",
     "Is the Save button fully visible and unobscured?", "The full Save button is visible outside an overlay.",
     "An opaque dialog covers the Save button's position."),
    ("bar_height", "Chart panel. A vertical Load bar and a dashed threshold at 60.",
     "Does the Load bar rise above the 60 threshold line?", "The top of the Load bar is above the 60 line.",
     "The top of the Load bar is below the 60 line."),
    ("padlock", "Access panel. A padlock icon and the label Workspace access.",
     "Is the padlock closed?", "Both shackle ends are connected to the lock body.",
     "One shackle end is visibly raised free of the lock body."),
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render(category: str, expected: bool) -> bytes:
    """Pure fixture renderer: no state labels, paths or hidden metadata enter pixels."""
    image = Image.new("RGB", SIZE, "#eef1f5")
    d = ImageDraw.Draw(image)
    font, large = ImageFont.load_default(size=19), ImageFont.load_default(size=24)
    d.rounded_rectangle((18, 18, 462, 282), radius=10, fill="white", outline="#bec6cf", width=2)
    d.text((38, 35), "Workspace", fill="#172330", font=large)
    dark, blue = "#172330", "#2264c7"
    if category == "checkbox":
        d.text((38, 86), "Preferences", fill=dark, font=font)
        d.rectangle((44, 142, 75, 173), outline=dark, width=3)
        if expected:
            d.line((49, 156, 58, 166, 70, 148), fill=blue, width=5)
        d.text((94, 145), "Receive updates", fill=dark, font=font)
    elif category == "radio":
        d.text((38, 86), "Choose a plan", fill=dark, font=font)
        for idx, label in enumerate(("Standard", "Extended")):
            y = 135 + idx * 65
            d.ellipse((44, y, 76, y + 32), outline=dark, width=3)
            if expected == (idx == 0):
                d.ellipse((52, y + 8, 68, y + 24), fill=blue)
            d.text((95, y + 4), label, fill=dark, font=font)
    elif category == "color_status":
        green, red = "#168b4d", "#c73142"
        d.text((38, 100), "Service status", fill=dark, font=font)
        d.ellipse((310, 94, 352, 136), fill=green if expected else red)
        d.text((38, 166), "Status legend", fill=dark, font=font)
        for x, color, label in ((44, green, "Healthy"), (239, red, "Fault")):
            d.ellipse((x, 213, x + 24, 237), fill=color)
            d.text((x + 37, 213), label, fill=dark, font=font)
    elif category == "modal_occlusion":
        d.text((38, 90), "Document settings", fill=dark, font=font)
        d.rounded_rectangle((170, 176, 290, 220), radius=5, fill=blue)
        d.text((208, 186), "Save", fill="white", font=font)
        d.text((332, 186), "Cancel", fill=dark, font=font)
        if not expected:
            d.rectangle((100, 115, 340, 252), fill="#e3e7eb", outline=dark, width=3)
            d.text((133, 137), "Review changes", fill=dark, font=font)
            d.text((132, 201), "Dialog is open", fill=dark, font=font)
    elif category == "bar_height":
        d.text((38, 80), "Load", fill=dark, font=font)
        d.line((110, 107, 110, 248, 380, 248), fill=dark, width=2)
        top = 122 if expected else 210
        d.rectangle((190, top, 260, 246), fill=blue)
        for x in range(115, 381, 16):
            d.line((x, 170, x + 9, 170), fill="#bb4d10", width=2)
        d.text((385, 158), "60", fill=dark, font=font)
    elif category == "padlock":
        d.text((38, 92), "Workspace access", fill=dark, font=font)
        # Closed U: curved top and both legs connected. Open U is shifted and raised.
        box = (192, 113, 280, 201) if expected else (213, 88, 301, 176)
        d.arc(box, 180, 360, fill=dark, width=11)
        d.line((box[0], box[1] + 44, box[0], 196), fill=dark, width=11)
        d.line((box[2], box[1] + 44, box[2], 195 if expected else 167), fill=dark, width=11)
        d.rounded_rectangle((173, 187, 298, 254), radius=7, fill=blue)
        d.ellipse((229, 208, 243, 223), fill="white")
        d.rectangle((234, 220, 239, 238), fill="white")
    else:
        raise ValueError("unknown synthetic category")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False)
    return stream.getvalue()


def generate_manifest() -> dict:
    cases = []
    for category, text, question, true, false in DEFINITIONS:
        for expected in (True, False):
            idx = len(cases)
            data = render(category, expected)
            cases.append({"id": f"f{idx:02}", "file": f"f{idx:02}.png", "category": category,
                          "expected": expected, "text": text, "question": question,
                          "true": true, "false": false, "sha256": sha(data), "bytes": len(data),
                          "dimensions": list(SIZE), "label_source": "explicit renderer state"})
    return {"version": 1, "source": "evals/d2_visual.py deterministic synthetic UI renderer",
            "pillow_version": importlib.metadata.version("pillow"), "cases": cases}


def freeze_fixtures() -> None:
    """Create once offline; existing artifacts must match, never silently replace them."""
    manifest = generate_manifest()
    FIXTURES.mkdir(parents=True, exist_ok=True)
    target = FIXTURES / "manifest.json"
    if target.exists():
        if json.loads(target.read_text()) != manifest:
            raise ValueError("frozen manifest differs from deterministic renderer")
    else:
        write_json(target, manifest)
    for case in manifest["cases"]:
        path = FIXTURES / case["file"]
        data = render(case["category"], case["expected"])
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("frozen PNG differs from deterministic renderer")
        else:
            path.write_bytes(data)


def load_cases() -> list[dict]:
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    if manifest != generate_manifest():
        raise ValueError("manifest integrity mismatch")
    cases = manifest["cases"]
    for case in cases:
        data = (FIXTURES / case["file"]).read_bytes()
        if sha(data) != case["sha256"] or len(data) != case["bytes"]:
            raise ValueError("PNG integrity mismatch")
        with Image.open(io.BytesIO(data)) as image:
            if list(image.size) != case["dimensions"] or image.format != "PNG":
                raise ValueError("PNG dimensions or type mismatch")
            if image.info:
                raise ValueError("PNG must contain no metadata")
    return cases


def instructions(case: dict) -> str:
    return f"{case['question']}\nTrue: {case['true']}\nFalse: {case['false']}"


def predicate(case: dict) -> PredicateQuestion:
    return PredicateQuestion("visible_state", instructions(case))


def jev_spec(case: dict) -> tuple[str, dict]:
    from typesafe_sdk import Noul
    return case["text"], {"visible_state": Noul(instructions=instructions(case),
                                              criteria={"true": case["true"], "false": case["false"]})}


def jev_body(case: dict) -> bytes:
    from typesafe_sdk._core.json import serialize
    from typesafe_sdk._core.questions import normalize_questions
    state, questions = jev_spec(case)
    return serialize({"state": state, "model": JEV_MODEL, "questions": normalize_questions(questions)})


def image_body(case: dict, combined: bool) -> bytes:
    data = (FIXTURES / case["file"]).read_bytes()
    # Only pixels enter the image URL; local ID, path, oracle labels never leave this machine.
    content = [{"type": "input_text", "text": case["text"]}] if combined else []
    content.append({"type": "input_image", "image_url": "data:image/png;base64," +
                    base64.b64encode(data).decode("ascii")})
    body = json.dumps({"model": MODEL, "input": [{"role": "user", "content": content}],
                       "questions": serialize_questions([predicate(case)])},
                      ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    if len(body) > MAX_BODY:
        raise ValueError("image request exceeds frozen body limit")
    return body


def wire_body(case: dict, arm: str) -> bytes:
    if arm == "jev_text":
        body = jev_body(case)
    elif arm == "decisions_text":
        body = request_body(case["text"], [predicate(case)])
    elif arm in ("decisions_image", "decisions_combined"):
        body = image_body(case, arm == "decisions_combined")
    else:
        raise ValueError("unknown arm")
    if len(body) > MAX_BODY:
        raise ValueError("request exceeds frozen body limit")
    return body


class ImageDecisionsClient:
    """Eval-only pooled image client. Strict native parser; one dispatch, no retries."""
    def __init__(self, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None):
        self._key = api_key
        self._client = httpx.AsyncClient(transport=transport, timeout=60, follow_redirects=False, trust_env=False)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def decide(self, body: bytes):
        if len(body) > MAX_BODY:
            raise DecisionsError("request_too_large")
        started = time.perf_counter()
        try:
            response = await self._client.post(ENDPOINT, content=body,
                headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"})
        except httpx.RequestError:
            raise DecisionsError("network") from None
        if not 200 <= response.status_code < 300:
            raise DecisionsError(f"http_{response.status_code}",
                                 provider_error=_provider_error(response.content, self._key))
        try:
            raw = json.loads(response.content, object_pairs_hook=_unique_object)
        except (ValueError, UnicodeError):
            raise DecisionsError("invalid_json") from None
        return _parse(raw, json.loads(body)["questions"], time.perf_counter() - started)


def band(probability: float) -> str:
    if type(probability) not in (float, int) or not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("invalid native predicate")
    return "true" if probability >= .8 else "false" if probability <= .2 else "unknown"


def summarize(rows: list[dict], cases: list[dict], halted: str | None = None) -> dict:
    result = {"complete": len(rows) == len(cases) * REPLAYS * len(ARMS), "halted": halted,
              "scheduled": len(cases) * REPLAYS * len(ARMS), "attempts": len(rows), "arms": {}}
    for arm in ARMS:
        mine = [r for r in rows if r["arm"] == arm]
        groups = {case["id"]: [r for r in mine if r["id"] == case["id"]] for case in cases}
        successes = [name for name, group in groups.items()
                     if len(group) == REPLAYS and all(r["correct"] and not r.get("error") for r in group)]
        false_positives = [name for name, group in groups.items()
                          if group and not group[0]["expected"] and any(r.get("band") == "true" for r in group)]
        times = sorted(r["latency_ms"] for r in mine)
        result["arms"][arm] = {
            "attempts": len(mine), "all_three_correct_confident": len(successes), "successful_cases": successes,
            "negative_confident_true_any": false_positives,
            "errors": sum(bool(r.get("error")) for r in mine),
            "unknown": sum(r.get("band") == "unknown" for r in mine),
            "correct_confident_replays": sum(r["correct"] for r in mine),
            "unmeasured_or_error_cases": [name for name, group in groups.items()
                                          if len(group) != REPLAYS or any(r.get("error") for r in group)],
            "median_ms": statistics.median(times) if times else None,
            "p95_ms": times[math.ceil(len(times) * .95) - 1] if times else None,
        }
    a, b = result["arms"]["decisions_combined"], result["arms"]["decisions_text"]
    result["combined_gain_cases"] = a["all_three_correct_confident"] - b["all_three_correct_confident"]
    result["visual_rule_met"] = (result["complete"] and not a["unmeasured_or_error_cases"]
                                 and result["combined_gain_cases"] > 0 and not a["negative_confident_true_any"])
    result["interpretation"] = "authored information ablation; implementation wall latency; no calibration or adoption"
    return result


def schedule(cases: list[dict]) -> list[tuple[dict, int, str]]:
    rng, scheduled = random.Random(SEED), []
    pairs = [[c for c in cases if c["category"] == category] for category, *_ in DEFINITIONS]
    rng.shuffle(pairs)
    for pair in pairs:
        for repeat in range(REPLAYS):
            order = list(pair)
            rng.shuffle(order)
            for case in order:
                arms = list(ARMS)
                rng.shuffle(arms)
                scheduled.extend((case, repeat, arm) for arm in arms)
    return scheduled


def provenance(cases: list[dict]) -> dict:
    files = [Path(__file__).resolve(), ROOT / "python/jevdual/decisions.py", ROOT / "evals/d1_compare.py",
             FIXTURES / "manifest.json", *[FIXTURES / c["file"] for c in cases]]
    return {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_hashes": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in files},
            "source_guide": "https://developers.openai.com/api/docs/guides/decisions",
            "models": [JEV_MODEL, MODEL], "replays": REPLAYS, "seed": SEED, "concurrency": 1,
            "versions": {name: importlib.metadata.version(name) for name in ("pillow", "httpx", "typesafe-sdk")},
            "request_hashes": {c["id"]: {arm: sha(wire_body(c, arm)) for arm in ARMS} for c in cases},
            "predicate_bands": {"true_at_least": .8, "false_at_most": .2},
            "fixture_note": "synthetic development demonstration; identical sparse text across opposing pairs"}


async def measure(out: Path, cap: float, prior_cost: float) -> None:
    from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy
    if out.exists():
        raise ValueError("measurement output must be fresh")
    if checkout_dirty():
        raise ValueError("commit harness and fixtures before measuring")
    cases = load_cases()
    info = provenance(cases)
    budget = Budget(cap, prior_cost)
    # Construct clients before creating output; absence of a credential cannot leave a fake run.
    baseline = AsyncTypeSafeClient(api_key=key("TYPESAFE_API_KEY"), retry=RetryPolicy(max_retries=0), timeout=60)
    api_key = key("OPENAI_API_KEY")
    candidate, images = DecisionsClient(api_key, timeout=60), ImageDecisionsClient(api_key)
    out.mkdir(parents=True)
    write_json(out / "started.json", {**info, "prior_cost_upper_usd": prior_cost, "cap_usd": cap})
    write_json(out / "fixtures.json", cases)
    rows, halted = [], None
    try:
        for case, repeat, arm in schedule(cases):
            body = wire_body(case, arm)
            provider = "jev" if arm == "jev_text" else "decisions"
            try:
                reservation = budget.reserve(provider, body, 1)
            except BudgetExceeded:
                halted = "combined pilot budget exhausted"
                break
            write_json(out / "budget.json", budget.snapshot())
            row = {"id": case["id"], "category": case["category"], "expected": case["expected"],
                   "repeat": repeat, "arm": arm, "request_sha256": sha(body), "body_bytes": len(body),
                   "image_sha256": case["sha256"] if arm in ("decisions_image", "decisions_combined") else None,
                   "prompt_sha256": sha(instructions(case).encode()), "correct": False}
            started, tokens = time.perf_counter(), None
            try:
                if arm == "jev_text":
                    state, questions = jev_spec(case)
                    response = await baseline.system_one(state, questions, model=JEV_MODEL,
                                                         retry=RetryPolicy(max_retries=0), timeout=60)
                    tokens = response.usage.input_tokens
                    row["native_response"] = response.model_dump(mode="json")
                    row["native_model"] = response.model
                    probability = response.nouls["visible_state"].noul
                else:
                    response = await candidate.decide(case["text"], [predicate(case)]) if arm == "decisions_text" \
                        else await images.decide(body)
                    tokens = response.input_tokens
                    row["native_response"], row["native_model"] = response.raw, response.model
                    row["transport_latency_ms"] = round(response.latency_s * 1000, 2)
                    answer = response.answers["visible_state"]
                    if not isinstance(answer, PredicateAnswer):
                        raise DecisionsError("answer_type")
                    probability = answer.probability
                row["native_probability"] = probability
                row["band"] = band(probability)
                row["correct"] = row["band"] == ("true" if case["expected"] else "false")
            except Exception as exc:  # noqa: BLE001 - retain only safe bounded fields
                code = getattr(exc, "code", None) if isinstance(exc, DecisionsError) else None
                status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
                row["error"] = {"type": type(exc).__name__, "code": code,
                                "http_status": status if type(status) is int else None}
                if isinstance(exc, DecisionsError):
                    tokens = exc.input_tokens
                    if exc.raw is not None:
                        row["native_response"] = exc.raw
                    if exc.provider_error is not None:
                        row["error"]["provider_error"] = exc.provider_error
                if code in ("http_400", "http_401", "http_403", "http_404", "http_422") or status in (400, 401, 403, 404, 422):
                    halted = "HTTP contract or account request rejected"
            row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            try:
                row["budget"] = budget.settle(reservation, tokens)
            except BudgetExceeded:
                row["budget"] = dict(budget.entries[reservation])
                halted = "provider usage exceeded reservation"
            rows.append(row)
            write_json(out / "results.json", rows)
            write_json(out / "budget.json", budget.snapshot())
            write_json(out / "summary.json", summarize(rows, cases, halted))
            if len(rows) % 12 == 0 or halted:
                print(f"{len(rows)}/144 attempts; combined cost upper ${budget.committed:.5f}", flush=True)
            if halted:
                break
    finally:
        await baseline.aclose()
        await candidate.aclose()
        await images.aclose()
        write_json(out / "results.json", rows)
        write_json(out / "budget.json", budget.snapshot())
        write_json(out / "summary.json", summarize(rows, cases, halted))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--cap", type=float, default=5)
    parser.add_argument("--prior-cost", type=float)
    args = parser.parse_args()
    try:
        if args.run:
            if args.out is None or args.prior_cost is None:
                raise ValueError("--out and explicit --prior-cost are required for paid run")
            asyncio.run(measure(args.out, args.cap, args.prior_cost))
        else:
            freeze_fixtures()
            cases = load_cases()
            info = provenance(cases)
            if args.out:
                if args.out.exists():
                    raise ValueError("offline output must be fresh")
                args.out.mkdir(parents=True)
                write_json(args.out / "preflight.json", info)
            largest = max(len(wire_body(c, a)) for c in cases for a in ARMS)
            print(f"Offline D2 preflight: {len(cases)} fixtures; 144 attempts; maximum request {largest} bytes")
    except (ValueError, OSError, DecisionsError, BudgetExceeded):
        raise SystemExit("D2 failed safe preflight; no automatic retry; inspect frozen inputs and receipts") from None


if __name__ == "__main__":
    main()
