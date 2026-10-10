import json

import httpx
import pytest
from jevdual.decisions import DecisionsError
from PIL import Image

from evals.d1_compare import BudgetExceeded
from evals.d3_browser import fixture
from evals.d4_target_grounding import (
    ARMS,
    MAX_BODY,
    MODEL,
    VisualBudget,
    VisualDecisions,
    build_fixture,
    load_cases,
    overlay_script,
    region_difference,
    sha,
    summarize,
    wire_body,
)


@pytest.mark.parametrize("variant", ["supported", "near_miss", "ambiguous"])
def test_control_preserves_original_d3_render_question_target(variant):
    assert build_fixture(0, variant) == fixture("toolbar_glyph", variant)


def test_layouts_change_only_render_and_preserve_question_and_proposal():
    baseline = build_fixture(0, "near_miss")
    for layout in (1, 2, 3):
        changed = build_fixture(layout, "near_miss")
        assert changed["html"] != baseline["html"]
        assert changed["question"] == baseline["question"]
        assert changed["target"] == baseline["target"] == "tool-b"
        assert "fixtureState.mode='rotate'" in changed["html"]
    with pytest.raises(ValueError):
        build_fixture(4, "near_miss")


def test_overlay_contains_geometry_and_id_without_semantic_truth():
    script = overlay_script({"target_id": "tool-b", "bounds": {"x": 180, "y": 100, "width": 60, "height": 60}})
    assert "tool-b" in script and '"x": 180' in script
    assert "aria-hidden" in script and "pointerEvents='none'" in script
    assert "crop" not in script.lower() and "rotate" not in script.lower()
    assert "expected" not in script


def test_arm_wire_differs_only_in_image_and_never_exposes_oracle(tmp_path):
    paths = []
    for i in range(3):
        path = tmp_path / f"{i}.png"
        Image.new("RGB", (20 + i, 20), (i * 30, 0, 0)).save(path)
        paths.append(path.name)
    case = {"text": "Observed toolbar and offered target tool-b.", "question": "Is tool-b Crop?",
        "expected": False, "oracle": {"secret_truth": "ROTATE"},
        "images_by_arm": dict(zip(ARMS, [[p] for p in paths], strict=True))}
    bodies = [json.loads(wire_body(case, arm, tmp_path)) for arm in ARMS]
    assert all(b["questions"] == bodies[0]["questions"] for b in bodies)
    assert all(b["input"][0]["content"][0] == bodies[0]["input"][0]["content"][0] for b in bodies)
    assert all("secret_truth" not in json.dumps(b) and "expected" not in json.dumps(b) for b in bodies)
    assert len({b["input"][0]["content"][1]["image_url"] for b in bodies}) == 3


def test_budget_unknown_usage_retains_charge_and_request_identity():
    budget = VisualBudget(5, 0.215917722)
    index = budget.reserve("decisions", b"{}")
    entry = budget.settle(index, None)
    assert not entry["usage_known"] and entry["charged_upper_usd"] == 0.0064
    assert entry["request_sha256"] == sha(b"{}")
    with pytest.raises(BudgetExceeded):
        budget.reserve("decisions", b"x" * (MAX_BODY + 1))
    with pytest.raises(BudgetExceeded):
        budget.reserve("jev", b"{}")


@pytest.mark.asyncio
async def test_transport_does_not_retry_error_or_expose_key():
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        return httpx.Response(400, json={"error": {"code": "invalid", "message": "key abc-secret"}})

    client = VisualDecisions("abc-secret", transport=httpx.MockTransport(handler))
    try:
        body = json.dumps({"model": MODEL, "questions": [{"name": "p", "type": "predicate", "instructions": "x"}]}).encode()
        with pytest.raises(DecisionsError) as caught:
            await client.call(body)
        assert caught.value.code == "http_400" and count == 1
        assert "abc-secret" not in json.dumps(caught.value.provider_error)
    finally:
        await client.aclose()


def test_summary_preserves_invalid_acceptance_and_wrong_effect():
    case = {"id": "G02", "expected": False}
    rows = []
    for repeat in range(3):
        row = {"id": "G02", "arm": "original_full", "band": "true", "correct": False,
            "request_ms": 100, "capture_to_judgment_estimate_ms": 150}
        if repeat == 0:
            row["execution"] = {"dispatched": True, "wrong_effect": True}
        rows.append(row)
    summary = summarize(rows, [case])
    assert summary["arms"]["original_full"]["invalid_confident_positive"] == ["G02"]
    assert summary["arms"]["original_full"]["wrong_effects"] == ["G02"]
    assert not summary["complete"]


def manifest_fixture(tmp_path):
    full, region = tmp_path / "full.png", tmp_path / "region.png"
    Image.new("RGB", (640, 360), "white").save(full)
    Image.new("RGB", (60, 60), "white").save(region)
    bounds = {"x": 80, "y": 100, "width": 60, "height": 60}
    cases = []
    for layout in range(4):
        for variant in ("supported", "near_miss", "ambiguous"):
            spec = build_fixture(layout, variant)
            arms = {}
            for arm in ARMS:
                path = region if arm == "target_region" else full
                arms[arm] = {"path": path.name, "sha256": sha(path.read_bytes()),
                    "dimensions": [60, 60] if arm == "target_region" else [640, 360], "scale": 1,
                    "clip": bounds if arm == "target_region" else {"x": 0, "y": 0, "width": 640, "height": 360}}
            arms["target_region"]["source_region_difference"] = region_difference(full, region, bounds)
            cases.append({"id": str(len(cases)), "layout": layout, "variant": variant,
                "expected": spec["oracle"]["expected"], "recipe": {"layout": layout, "variant": variant},
                "question": spec["question"], "text": "Observed toolbar", "proposal": {"bounds": bounds},
                "images_by_arm": {a: [v["path"]] for a,v in arms.items()},
                "capture": {"source_frame_sha256": arms["original_full"]["sha256"],
                    "source_html_sha256": sha(spec["html"].encode()), "arms": arms}})
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"cases": cases}))
    return path, cases


def test_manifest_checks_source_identity_exact_geometry_and_pixel_receipts(tmp_path):
    path, cases = manifest_fixture(tmp_path)
    assert len(load_cases(path)) == 12
    cases[0]["capture"]["arms"]["target_region"]["clip"] = {"x": 90, "y": 100, "width": 60, "height": 60}
    path.write_text(json.dumps({"cases": cases}))
    with pytest.raises(ValueError, match="clip"):
        load_cases(path)
    path, cases = manifest_fixture(tmp_path)
    cases[0]["capture"]["source_html_sha256"] = "wrong"
    path.write_text(json.dumps({"cases": cases}))
    with pytest.raises(ValueError, match="source render"):
        load_cases(path)
    path, cases = manifest_fixture(tmp_path)
    cases[0]["capture"]["arms"]["target_region"]["source_region_difference"]["different_pixels"] = 9
    path.write_text(json.dumps({"cases": cases}))
    with pytest.raises(ValueError, match="comparison receipt"):
        load_cases(path)
