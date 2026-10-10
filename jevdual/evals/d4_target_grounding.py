"""D4 target-grounding repair pilot; no provider calls without explicit --run."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import io
import json
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from jevdual.decisions import ENDPOINT, MODEL, DecisionsError, _parse, _provider_error, _unique_object
from PIL import Image, ImageChops

from evals.d1_compare import Budget, BudgetExceeded, checkout_dirty, key, write_json
from evals.d3_browser import REFERENCE, SIZE, _evaluate, _observe, fixture, guard, proposal_for, utc_now
from evals.d3_visual_tasks import band, committed_file, source_commit, timing

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("original_full", "marked_full", "target_region")
VARIANTS = ("supported", "near_miss", "ambiguous")
SEED = 10082029
REPLAYS = 3
MAX_BODY = 48_000
NAME = "proposal_supported"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_fixture(layout: int, variant: str) -> dict:
    if layout not in range(4) or variant not in VARIANTS:
        raise ValueError("Unknown frozen D4 fixture")
    spec = fixture("toolbar_glyph", variant)
    if layout == 1:
        spec["html"] = spec["html"].replace("left:80px", "left:SWAPpx").replace(
            "left:180px", "left:80px").replace("left:SWAPpx", "left:180px")
    elif layout == 2:
        spec["html"] = spec["html"].replace("width:60px;height:60px", "width:90px;height:90px").replace(
            'width="32" height="32"', 'width="48" height="48"')
    elif layout == 3:
        spec["html"] = spec["html"].replace(
            'M8 2v22h22M2 8h22v22', 'M7 2v23h23M2 7h23v23M12 12h8v8h-8z').replace(
            'M25 10A11 11 0 1 0 25 23M25 10V2M25 10H17',
            'M26 11A10 10 0 1 0 25 24M26 11l-9 -1M26 11l-1 -9')
    return spec


def overlay_script(proposal: dict) -> str:
    """Inspector annotation contains only target identity and observed geometry."""
    target = json.dumps(proposal["target_id"])
    bounds = json.dumps(proposal["bounds"])
    return f"""(() => {{const r={bounds};const id={target};const d=document.createElement('div');
      d.id='d4-inspector';d.setAttribute('aria-hidden','true');d.style.position='absolute';
      d.style.pointerEvents='none';d.style.zIndex='100';d.style.left=r.x+'px';
      d.style.top=r.y+'px';d.style.width=r.width+'px';d.style.height=r.height+'px';
      d.style.boxSizing='border-box';d.style.outline='3px solid #d000c0';
      const label=document.createElement('span');label.textContent=id;
      label.style='position:absolute;left:0;top:-23px;background:#fff;color:#900080;font:14px Arial';
      d.appendChild(label);document.body.appendChild(d);}})()"""


def region_difference(source: Path, region: Path, bounds: dict) -> dict:
    """Read-only raster comparison; separate CDP clips can differ in antialiasing."""
    box = (bounds["x"], bounds["y"], bounds["x"] + bounds["width"], bounds["y"] + bounds["height"])
    with Image.open(source) as full, Image.open(region) as target:
        a, b = full.convert("RGB").crop(box), target.convert("RGB")
        diff = ImageChops.difference(a, b)
        pixels = list(diff.get_flattened_data())
        return {"different_pixels": sum(p != (0, 0, 0) for p in pixels), "pixels": len(pixels),
                "max_channel_delta": max(max(p) for p in pixels),
                "rmse": (sum(v*v for p in pixels for v in p) / (len(pixels)*3)) ** 0.5}


def _screenshot(backend: Any, out: Path, name: str, bounds: dict | None = None) -> dict:
    started = time.perf_counter()
    captured_at = utc_now()
    clip = bounds or {"x": 0, "y": 0, "width": SIZE[0], "height": SIZE[1]}
    data = base64.b64decode(backend._call("Page.captureScreenshot", {
        "format": "png", "clip": {**clip, "scale": 1}, "captureBeyondViewport": False})["data"])
    captured_ms = (time.perf_counter() - started) * 1000
    encoded = time.perf_counter()
    path = out / (name + ".png")
    path.write_bytes(data)
    return {"path": path.name, "sha256": sha(data), "clip": clip, "scale": 1,
            "captured_at": captured_at, "browser_target_id": backend.target_id, "process_id": backend.pid,
            "dimensions": list(Image.open(io.BytesIO(data)).size),
            "capture_ms": captured_ms, "encode_ms": (time.perf_counter() - encoded) * 1000,
            "method": "direct CDP Page.captureScreenshot; unmodified PNG"}


def capture(out: Path) -> list[dict]:
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError("D4 capture requires fresh directory")
    out.mkdir(parents=True)
    sys.path.insert(0, str(REFERENCE))
    from arc_cua.backends.chrome import ChromeBackend

    profile = out / "chrome-profile"
    profile.mkdir()
    cases = []
    try:
        with ChromeBackend.launch(headless=True, user_data_dir=str(profile), window_size=SIZE) as backend:
            backend._call("Emulation.setDeviceMetricsOverride", {
                "width": SIZE[0], "height": SIZE[1], "deviceScaleFactor": 1, "mobile": False})
            for layout in range(4):
                for variant in VARIANTS:
                    number = len(cases)
                    spec = build_fixture(layout, variant)
                    source = out / f"fixture-{number:02}.html"
                    source.write_text(spec["html"])
                    setup = time.perf_counter()
                    backend.navigate(source.as_uri(), quiet_s=0.05)
                    setup_ms = (time.perf_counter() - setup) * 1000
                    observation = _observe(backend, out, f"case-{number:02}-original")
                    proposal = proposal_for(spec, [observation], variant)
                    target_region = _screenshot(backend, out, f"case-{number:02}-region", proposal["bounds"])
                    target_region["source_region_difference"] = region_difference(
                        out / observation["image"], out / target_region["path"], proposal["bounds"])
                    annotation = time.perf_counter()
                    _evaluate(backend, overlay_script(proposal))
                    annotation_ms = (time.perf_counter() - annotation) * 1000
                    marked = _screenshot(backend, out, f"case-{number:02}-marked")
                    _evaluate(backend, "document.getElementById('d4-inspector').remove()")
                    original = {"path": observation["image"], "sha256": observation["image_sha256"],
                        "dimensions": observation["dimensions"], "clip": {"x": 0, "y": 0, "width": SIZE[0], "height": SIZE[1]},
                        "scale": 1, "capture_ms": observation["phases_ms"]["capture"],
                        "encode_ms": observation["phases_ms"]["encode"], "method": "unmodified full-frame CDP PNG"}
                    arms = {"original_full": original, "marked_full": marked, "target_region": target_region}
                    for item in arms.values():
                        item.update(source_frame_sha256=observation["image_sha256"],
                                    source_observation_revision=observation["revision"],
                                    offered_target_id=proposal["target_id"])
                    visible = {k: observation[k] for k in ("captured_at", "revision", "dom", "ax")}
                    text = json.dumps({"observations_in_time_order": [visible],
                        "current_revision": observation["revision"], "offered_proposal": proposal}, sort_keys=True)
                    case = {"id": f"G{number+1:02}", "layout": layout, "variant": variant,
                        "expected": spec["oracle"]["expected"], "surface": "browser_fixture",
                        "question": spec["question"], "text": text, "proposal": proposal,
                        "oracle": spec["oracle"], "recipe": {"layout": layout, "variant": variant},
                        "images_by_arm": {arm: [item["path"]] for arm, item in arms.items()},
                        "capture": {"observation": observation, "source_frame_sha256": observation["image_sha256"],
                            "source_html_sha256": sha(spec["html"].encode()), "arms": arms,
                            "setup_ms": setup_ms, "annotation_ms": annotation_ms,
                            "extraction_ms": observation["phases_ms"]["extraction"],
                            "transform": "DOM target-ID/bbox inspector; direct CDP target clip; no bitmap editing"}}
                    cases.append(case)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    write_json(out / "manifest.json", {"cases": cases, "seed": SEED, "scope": "authored browser target grounding"})
    return cases


def replay_case(case: dict, accepted: bool, out: Path) -> dict:
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError("D4 replay requires fresh directory")
    out.mkdir(parents=True)
    sys.path.insert(0, str(REFERENCE))
    from arc_cua.backends.chrome import ChromeBackend

    profile = out / "chrome-profile"
    profile.mkdir()
    started = time.perf_counter()
    spec = build_fixture(**case["recipe"])
    source = out / "fixture.html"
    source.write_text(spec["html"])
    try:
        with ChromeBackend.launch(headless=True, user_data_dir=str(profile), window_size=SIZE) as backend:
            backend._call("Emulation.setDeviceMetricsOverride", {
                "width": SIZE[0], "height": SIZE[1], "deviceScaleFactor": 1, "mobile": False})
            backend.navigate(source.as_uri(), quiet_s=0.05)
            current = _observe(backend, out, "current")
            setup_ms = (time.perf_counter() - started) * 1000
            validation = time.perf_counter()
            original = case["capture"]["observation"]
            proposal = dict(case["proposal"])
            scope_matches = proposal["browser_target_id"] == original["target_id"]
            proposal["browser_target_id"] = current["target_id"]
            allowed, reason = guard({"proposal": proposal}, current)
            content_matches = current["revision"] == original["revision"]
            if not scope_matches or not content_matches:
                allowed, reason = False, "scope_or_content_mismatch"
            if not accepted:
                allowed, reason = False, "model_not_confidently_true"
            validation_ms = (time.perf_counter() - validation) * 1000
            before = _evaluate(backend, "window.fixtureState")
            dispatch_ms = 0.0
            if allowed:
                dispatch = time.perf_counter()
                for event in ("mousePressed", "mouseReleased"):
                    backend._call("Input.dispatchMouseEvent", {"type": event, "x": proposal["x"],
                                  "y": proposal["y"], "button": "left", "clickCount": 1})
                dispatch_ms = (time.perf_counter() - dispatch) * 1000
            read = time.perf_counter()
            after = _evaluate(backend, "window.fixtureState")
            goal_met = after.get("mode") == "crop"
            result = {"accepted_by_model": accepted, "dispatched": allowed, "guard_reason": reason,
                "goal_met": goal_met, "wrong_effect": allowed and before != after and not goal_met,
                "before": before, "after": after, "content_matches": content_matches,
                "current_observation": current, "phases_ms": {"setup_capture": setup_ms,
                    "validation": validation_ms, "dispatch": dispatch_ms,
                    "readback": (time.perf_counter() - read) * 1000, "total": (time.perf_counter() - started) * 1000}}
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    write_json(out / "receipt.json", result)
    return result


class VisualBudget(Budget):
    def reserve(self, provider: str, body: bytes, question_count: int = 1) -> int:
        if provider != "decisions" or len(body) > MAX_BODY or question_count != 1:
            raise BudgetExceeded("D4 frozen request bound")
        amount = 64_000 * 0.1 / 1e6
        if self.committed + amount > self.cap + 1e-12:
            raise BudgetExceeded("pilot budget exhausted")
        self.entries.append({"provider": provider, "reserved_usd": amount, "charged_upper_usd": amount,
            "usage_known": False, "input_tokens_upper": 64_000, "question_count": 1,
            "body_bytes": len(body), "request_sha256": sha(body)})
        return len(self.entries) - 1


class VisualDecisions:
    def __init__(self, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None):
        self._key = api_key
        self._client = httpx.AsyncClient(transport=transport, timeout=60, follow_redirects=False, trust_env=False)
        self.last_phases_ms = {}

    async def call(self, body: bytes):
        self.last_phases_ms = {}
        if len(body) > MAX_BODY:
            raise DecisionsError("request_bound")
        spec = json.loads(body)
        if spec.get("model") != MODEL or len(spec.get("questions", [])) != 1:
            raise DecisionsError("request_contract")
        started = time.perf_counter()
        try:
            response = await self._client.post(ENDPOINT, content=body,
                headers={"Authorization": "Bearer " + self._key, "Content-Type": "application/json"})
        except httpx.RequestError:
            self.last_phases_ms["http"] = (time.perf_counter() - started) * 1000
            raise DecisionsError("network") from None
        self.last_phases_ms["http"] = (time.perf_counter() - started) * 1000
        if not 200 <= response.status_code < 300:
            raise DecisionsError(f"http_{response.status_code}", provider_error=_provider_error(response.content, self._key))
        parsing = time.perf_counter()
        try:
            raw = json.loads(response.content, object_pairs_hook=_unique_object)
        except (ValueError, UnicodeError):
            raise DecisionsError("invalid_json") from None
        finally:
            self.last_phases_ms["json_parse"] = (time.perf_counter() - parsing) * 1000
        validation = time.perf_counter()
        try:
            return _parse(raw, spec["questions"], time.perf_counter() - started)
        finally:
            self.last_phases_ms["response_validation"] = (time.perf_counter() - validation) * 1000

    async def aclose(self):
        await self._client.aclose()


def wire_body(case: dict, arm: str, root: Path) -> bytes:
    if arm not in ARMS:
        raise ValueError("Unknown D4 arm")
    contents = [{"type": "input_text", "text": case["text"]}]
    for relative in case["images_by_arm"][arm]:
        contents.append({"type": "input_image", "image_url": "data:image/png;base64," +
                         base64.b64encode((root / relative).read_bytes()).decode()})
    return json.dumps({"model": MODEL, "input": [{"role": "user", "content": contents}],
        "questions": [{"name": NAME, "type": "predicate", "instructions": case["question"]}]},
        separators=(",", ":"), ensure_ascii=False).encode()


def load_cases(path: Path) -> list[dict]:
    cases = json.loads(path.read_text())["cases"]
    if len(cases) != 12 or len({c["id"] for c in cases}) != 12:
        raise ValueError("D4 requires12 unique cases")
    if {(c["layout"], c["variant"]) for c in cases} != {(i, v) for i in range(4) for v in VARIANTS}:
        raise ValueError("D4 frozen layout/variant count")
    for case in cases:
        if case["expected"] is not None and type(case["expected"]) is not bool:
            raise ValueError("invalid expected metadata")
        if case["capture"]["source_frame_sha256"] != case["capture"]["arms"]["original_full"]["sha256"]:
            raise ValueError("source frame mismatch")
        if case["capture"]["source_html_sha256"] != sha(build_fixture(**case["recipe"])["html"].encode()):
            raise ValueError("frozen source render mismatch")
        bounds = case["proposal"]["bounds"]
        if bounds["x"] < 0 or bounds["y"] < 0 or bounds["width"] <= 0 or bounds["height"] <= 0 or bounds["x"] + bounds["width"] > SIZE[0] or bounds["y"] + bounds["height"] > SIZE[1]:
            raise ValueError("target bounds outside source frame")
        for arm in ARMS:
            item = case["capture"]["arms"][arm]
            image = (path.parent / item["path"]).resolve()
            if not image.is_relative_to(path.parent.resolve()) or sha(image.read_bytes()) != item["sha256"]:
                raise ValueError("image scope/hash mismatch")
            with Image.open(image) as png:
                if png.format != "PNG" or list(png.size) != item["dimensions"] or png.width > 900 or png.height > 600:
                    raise ValueError("image dimension/type mismatch")
            if arm == "target_region" and item["clip"] != case["proposal"]["bounds"]:
                raise ValueError("target clip mismatch")
            expected_size = [int(bounds["width"]), int(bounds["height"])] if arm == "target_region" else list(SIZE)
            if item["dimensions"] != expected_size or item["scale"] != 1:
                raise ValueError("frozen arm geometry mismatch")
            if case["images_by_arm"][arm] != [item["path"]] or len(wire_body(case, arm, path.parent)) > MAX_BODY:
                raise ValueError("arm image/body mismatch")
        measured_difference = region_difference(
            path.parent / case["capture"]["arms"]["original_full"]["path"],
            path.parent / case["capture"]["arms"]["target_region"]["path"], bounds)
        if case["capture"]["arms"]["target_region"]["source_region_difference"] != measured_difference:
            raise ValueError("source/region comparison receipt mismatch")
    return cases


def summarize(rows: list[dict], cases: list[dict]) -> dict:
    result = {"attempts": len(rows), "scheduled": 108,
        "complete": len(rows) == 108 and not any(r["band"] == "error" for r in rows), "arms": {}}
    for arm in ARMS:
        mine = [r for r in rows if r["arm"] == arm]
        record = {"correct_replays": sum(r["correct"] for r in mine),
            "all_three_correct": [], "supported_all_three": [], "invalid_confident_positive": [],
            "ambiguous_all_three": [], "ambiguous_conservative_false_replays": 0,
            "wrong_effects": [r["id"] for r in mine if r.get("execution", {}).get("wrong_effect")],
            "coverage_errors": [r["id"] for r in mine if r.get("execution", {}).get("coverage_error")
                                or r.get("execution", {}).get("content_matches") is False],
            "errors": sum(r["band"] == "error" for r in mine), "refusals": sum(r["band"] == "refusal" for r in mine),
            "request_timing": timing([r["request_ms"] for r in mine]),
            "capture_to_judgment_estimate": timing([r["capture_to_judgment_estimate_ms"] for r in mine]),
            "execution_timing": timing([r["execution_ms"] for r in mine if "execution_ms" in r])}
        for case in cases:
            group = [r for r in mine if r["id"] == case["id"]]
            all_correct = len(group) == REPLAYS and all(r["correct"] for r in group)
            if all_correct:
                record["all_three_correct"].append(case["id"])
                if case["expected"] is True:
                    record["supported_all_three"].append(case["id"])
                if case["expected"] is None:
                    record["ambiguous_all_three"].append(case["id"])
            if case["expected"] is not True and any(r["band"] == "true" for r in group):
                record["invalid_confident_positive"].append(case["id"])
            if case["expected"] is None:
                record["ambiguous_conservative_false_replays"] += sum(r["band"] == "false" for r in group)
        result["arms"][arm] = record
    return result


def preflight(path: Path) -> dict:
    cases = load_cases(path)
    return {"cases": len(cases), "scheduled": 108, "offline": True,
        "body_max_bytes": max(len(wire_body(c, a, path.parent)) for c in cases for a in ARMS),
        "unknown_usage_upper_this_run": 108 * 0.0064}


async def run(path: Path, out: Path, prior_cost: float, cap: float = 5):
    if out.exists() or not out.resolve().is_relative_to(ROOT):
        raise ValueError("D4 run requires fresh project-contained directory")
    if checkout_dirty():
        raise ValueError("Commit measured code/captures before calls")
    cases = load_cases(path)
    files = [path, *(path.parent / c["capture"]["arms"][a]["path"] for c in cases for a in ARMS)]
    if not all(committed_file(p) for p in files):
        raise ValueError("Capture manifest/PNGs must be committed")
    bodies = {(c["id"], a): wire_body(c, a, path.parent) for c in cases for a in ARMS}
    budget = VisualBudget(cap, prior_cost)
    client = VisualDecisions(key("OPENAI_API_KEY"))
    out.mkdir(parents=True)
    write_json(out / "started.json", {"commit": source_commit(), "manifest_sha256": sha(path.read_bytes()),
        "seed": SEED, "prior_cost_upper_usd": prior_cost, "cap_usd": cap, "model": MODEL})
    write_json(out / "frozen-inputs.json", {"cases": cases})
    order = list(cases)
    rng = random.Random(SEED)
    rng.shuffle(order)
    rows, halted = [], None
    try:
        for case in order:
            for repeat in range(REPLAYS):
                arms = list(ARMS)
                rng.shuffle(arms)
                for arm in arms:
                    body = bodies[(case["id"], arm)]
                    try:
                        index = budget.reserve("decisions", body)
                    except BudgetExceeded as exc:
                        halted = str(exc)
                        break
                    write_json(out / "budget.json", budget.snapshot())
                    row = {"id": case["id"], "layout": case["layout"], "variant": case["variant"],
                        "arm": arm, "repeat": repeat, "expected": case["expected"],
                        "request_sha256": sha(body), "evidence_sha256": sha(case["text"].encode()),
                        "image_sha256": case["capture"]["arms"][arm]["sha256"],
                        "source_frame_sha256": case["capture"]["source_frame_sha256"], "correct": False}
                    started, usage = time.perf_counter(), None
                    try:
                        response = await client.call(body)
                        usage = response.input_tokens
                        p = response.answers[NAME].probability
                        row.update(native_response=response.raw, model=response.model, probability=p, band=band(p))
                    except Exception as exc:  # noqa: BLE001 - sanitized contract receipts only
                        code = exc.code if isinstance(exc, DecisionsError) else None
                        row["band"] = "refusal" if code == "refusal" else "error"
                        row["error"] = {"type": type(exc).__name__, "code": code}
                        usage = getattr(exc, "input_tokens", None)
                        for attr in ("raw", "provider_error"):
                            value = getattr(exc, attr, None)
                            if isinstance(value, dict):
                                row["native_response" if attr == "raw" else attr] = value
                        if code in {f"http_{n}" for n in (400, 401, 403, 404, 422)}:
                            halted = "provider contract/account failure"
                    row["correct"] = row["band"] in ("unknown", "refusal") if case["expected"] is None else row["band"] == ("true" if case["expected"] else "false")
                    row["request_ms"] = (time.perf_counter() - started) * 1000
                    row["request_phases_ms"] = dict(client.last_phases_ms)
                    receipt = case["capture"]["arms"][arm]
                    original = case["capture"]["arms"]["original_full"]
                    row["capture_phases_ms"] = {
                        "source_capture": original["capture_ms"], "source_encode": original["encode_ms"],
                        "extraction": case["capture"]["extraction_ms"],
                        "derived_capture": receipt["capture_ms"] if arm != "original_full" else 0.0,
                        "derived_encode": receipt["encode_ms"] if arm != "original_full" else 0.0,
                        "annotation": case["capture"]["annotation_ms"] if arm == "marked_full" else 0.0,
                    }
                    row["capture_ms"] = sum(row["capture_phases_ms"].values())
                    row["capture_to_judgment_estimate_ms"] = row["capture_ms"] + row["request_ms"]
                    try:
                        row["budget"] = budget.settle(index, usage)
                    except BudgetExceeded as exc:
                        row["budget"], halted = dict(budget.entries[index]), str(exc)
                    rows.append(row)
                    write_json(out / "results.json", rows)
                    write_json(out / "budget.json", budget.snapshot())
                    if repeat == 0 and not halted:
                        execution = time.perf_counter()
                        try:
                            recipe = {k: v for k, v in case.items() if k not in ("expected", "oracle")}
                            row["execution"] = await asyncio.to_thread(replay_case, recipe, row["band"] == "true", out / "execution" / arm / case["id"])
                        except Exception as exc:  # noqa: BLE001 - coverage failures preserved
                            row["execution"] = {"coverage_error": type(exc).__name__}
                        row["execution_ms"] = (time.perf_counter() - execution) * 1000
                    write_json(out / "results.json", rows)
                    write_json(out / "summary.json", summarize(rows, cases))
                    if len(rows) % 9 == 0:
                        print(f"{len(rows)}/108 attempts; upper ${budget.committed:.6f}", flush=True)
                    if halted:
                        break
                if halted:
                    break
            if halted:
                break
    finally:
        await client.aclose()
        write_json(out / "results.json", rows)
        write_json(out / "budget.json", budget.snapshot())
        write_json(out / "summary.json", summarize(rows, cases))
        write_json(out / "closed.json", {"attempts": len(rows), "halted": halted, "scheduled": 108})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--capture", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--prior-cost", type=float)
    parser.add_argument("--cap", type=float, default=5)
    args = parser.parse_args()
    if args.capture:
        if args.out is None or not args.out.resolve().is_relative_to(ROOT):
            parser.error("Capture needs project-contained --out")
        print(json.dumps({"captured": len(capture(args.out))}))
    else:
        if args.cases is None:
            parser.error("Provide frozen --cases manifest")
        if args.run:
            if args.out is None or args.prior_cost is None:
                parser.error("Run needs --out and explicit --prior-cost")
            asyncio.run(run(args.cases.resolve(), args.out, args.prior_cost, args.cap))
        else:
            print(json.dumps(preflight(args.cases.resolve()), indent=2))


if __name__ == "__main__":
    main()
