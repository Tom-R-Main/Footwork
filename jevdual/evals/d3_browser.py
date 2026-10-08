"""D3 authored browser fixtures, captured with local arc-cua and real Chrome.

No provider calls. DOM/AX observation is separate from fixture oracle state.
Only a newly launched headless Chrome profile is used. Evidence is not a claim
of real product/browser-journey acceptance.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REFERENCE = Path("/Volumes/External SSD/referencerepos/arc-cua/src")
SIZE = (640, 360)
VARIANTS = ("supported", "near_miss", "ambiguous", "text_control")
FAMILIES = ("toolbar_glyph", "map_containment", "target_freshness")

OBSERVATION_JS = """(() => ({
  rendered_text: document.body.innerText,
  elements: Array.from(document.querySelectorAll('button,canvas,[role]')).map(e=>{
    const r=e.getBoundingClientRect();
    return {target_id:e.id, role:e.getAttribute('role') || e.tagName.toLowerCase(),
      name:e.getAttribute('aria-label') || e.innerText || '',
      disabled:!!e.disabled, hidden: r.width===0 || r.height===0,
      bounds:{x:r.x,y:r.y,width:r.width,height:r.height}};
  }).filter(e=>!e.hidden)
}))()"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def point_in_polygon(point: tuple[float, float], polygon: list[list[int]]) -> bool:
    """Ray crossing; authored fixture centers never lie on polygon edges."""
    x, y = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        ax, ay = previous
        bx, by = current
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
        previous = current
    return inside


def expected_label(variant: str) -> bool | None:
    return None if variant == "ambiguous" else variant != "near_miss"


def _shell(body: str, script: str) -> str:
    return """<!doctype html><html><head><meta charset="utf-8"><title>Visual task</title>
    <style>html,body{margin:0;width:640px;height:360px;overflow:hidden;background:#fff;
    color:#111;font:14px Arial}h1{font-size:18px;margin:20px}p{margin:20px}
    button{background:#eee;border:2px solid #111;position:absolute;cursor:pointer;
    box-sizing:border-box}canvas{position:absolute;left:0;top:70px}
    #receipt{position:absolute;left:20px;top:310px;margin:0}</style></head><body>""" + body + "<p id='receipt'>No action yet</p><script>" + script + "</script></body></html>"


def fixture(family: str, variant: str) -> dict[str, Any]:
    """Generate HTML and an evaluation-only oracle, never mixed into observation."""
    if family not in FAMILIES or variant not in VARIANTS:
        raise ValueError("Unknown D3 browser fixture")
    if family == "toolbar_glyph":
        crop = '<path d="M8 2v22h22M2 8h22v22" fill="none" stroke="#111" stroke-width="3"/>'
        rotate = '<path d="M25 10A11 11 0 1 0 25 23M25 10V2M25 10H17" fill="none" stroke="#111" stroke-width="3"/>'
        unclear = '<path d="M5 15h20" stroke="#111" stroke-width="3"/>'
        glyph = unclear if variant == "ambiguous" else crop
        a_name = ' aria-label="Crop"' if variant == "text_control" else ""
        b_name = ' aria-label="Rotate"' if variant == "text_control" else ""
        body = '<h1>Image editor</h1><p>Choose the crop tool.</p>'
        body += f'<button id="tool-a"{a_name} style="left:80px;top:100px;width:60px;height:60px"><svg aria-hidden="true" width="32" height="32" viewBox="0 0 32 32">{glyph}</svg></button>'
        body += f'<button id="tool-b"{b_name} style="left:180px;top:100px;width:60px;height:60px"><svg aria-hidden="true" width="32" height="32" viewBox="0 0 32 32">{rotate}</svg></button>'
        script = "window.fixtureState={mode:'none'};document.getElementById('tool-a').onclick=()=>{fixtureState.mode='crop';document.getElementById('receipt').textContent='Crop mode active'};document.getElementById('tool-b').onclick=()=>{fixtureState.mode='rotate';document.getElementById('receipt').textContent='Rotate mode active'};"
        target = "tool-b" if variant == "near_miss" else "tool-a"
        question = f"Does the visible evidence support clicking supplied target {target} to activate Crop? True only when its visible icon or accessible label identifies Crop. False when it identifies a different tool. If its meaning cannot be resolved, remain uncertain."
        return {"html": _shell(body, script), "target": target, "question": question,
                "oracle": {"expected": expected_label(variant), "intended_mode": "crop",
                           "target_modes": {"tool-a": "crop", "tool-b": "rotate"},
                           "ambiguous_icon": variant == "ambiguous"}}
    if family == "map_containment":
        polygon = [[80, 40], [260, 40], [280, 190], [70, 190]]
        points = {"marker-a": [150, 110], "marker-b": [360, 130]}
        if variant == "ambiguous":
            polygon = []
        body = '<h1>Delivery map</h1><p>Choose a marker inside the shaded delivery zone.</p><canvas id="map" width="640" height="220"></canvas>'
        for target, (x, y) in points.items():
            label = f' aria-label="{target}: {"inside" if target == "marker-a" else "outside"} delivery zone"' if variant == "text_control" else f' aria-label="{target}"'
            body += f'<button id="{target}"{label} style="left:{x-10}px;top:{y+60}px;width:20px;height:20px;border-radius:50%;background:#111;color:#fff"></button>'
        drawing = "const c=document.getElementById('map').getContext('2d');c.strokeStyle='#ddd';for(let x=0;x<640;x+=40){c.beginPath();c.moveTo(x,0);c.lineTo(x,220);c.stroke()}for(let y=0;y<220;y+=40){c.beginPath();c.moveTo(0,y);c.lineTo(640,y);c.stroke()}"
        if polygon:
            drawing += "c.beginPath();c.moveTo(80,40);c.lineTo(260,40);c.lineTo(280,190);c.lineTo(70,190);c.closePath();c.fillStyle='#aaccee';c.fill();c.strokeStyle='#225588';c.stroke();"
        else:
            drawing += "c.fillStyle='#eee';c.fillRect(40,10,520,200);c.fillStyle='#111';c.font='16px Arial';c.fillText('Zone layer unavailable',180,100);"
        script = drawing + "window.fixtureState={selected:null};for(const b of document.querySelectorAll('button'))b.onclick=()=>{fixtureState.selected=b.id;document.getElementById('receipt').textContent='Selected '+b.id};"
        target = "marker-b" if variant == "near_miss" else "marker-a"
        question = f"Does current visible evidence support clicking supplied target {target} as a marker inside the shaded delivery zone? True only if its center is inside the visible zone or an explicit accessible zone description identifies it as inside. False if outside. If the zone cannot be determined, remain uncertain."
        return {"html": _shell(body, script), "target": target, "question": question,
                "oracle": {"expected": expected_label(variant), "polygon": polygon,
                           "points_canvas": points, "canvas_offset": [0, 70]}}
    body = '<h1>Sample approval</h1><p id="layout-status">Layout revision 1</p><button id="approve" aria-label="Approve sample" style="left:80px;top:140px;width:120px;height:50px">Approve sample</button><button id="cancel" aria-label="Cancel sample" style="left:300px;top:140px;width:120px;height:50px">Cancel sample</button>'
    script = "window.fixtureState={action:null};document.getElementById('approve').onclick=()=>{fixtureState.action='approve';document.getElementById('receipt').textContent='Sample approved'};document.getElementById('cancel').onclick=()=>{fixtureState.action='cancel';document.getElementById('receipt').textContent='Sample cancelled'};window.changeLayout=()=>{document.getElementById('approve').style.left='300px';document.getElementById('cancel').style.left='80px';document.getElementById('layout-status').textContent='Layout revision 2'};window.coverLayout=()=>{const d=document.createElement('div');d.id='cover';d.textContent='Updating layout; controls unavailable';d.style='position:absolute;left:50px;top:120px;width:420px;height:100px;background:#ddd;z-index:5';document.body.appendChild(d)};"
    question = "Does the offered click, with its stated coordinates and observation revision, support approving the sample in the current observation? True only if it binds to the current visible Approve sample button at those coordinates and the stated revision is current. False if an observed change has invalidated it or the point now targets Cancel. If current controls are obscured and cannot be resolved, remain uncertain."
    return {"html": _shell(body, script), "target": "approve", "question": question,
            "oracle": {"expected": expected_label(variant), "intended_action": "approve",
                       "changes_layout": variant in ("near_miss", "text_control"),
                       "obscured": variant == "ambiguous"}}


def _evaluate(backend: Any, expression: str) -> Any:
    result = backend._call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
    if "exceptionDetails" in result:
        raise RuntimeError("Fixture evaluation failed")
    return result["result"].get("value")


def _observe(backend: Any, out: Path, name: str) -> dict[str, Any]:
    start = time.perf_counter()
    timestamp = utc_now()
    raw_png = base64.b64decode(backend._call("Page.captureScreenshot", {
        "format": "png", "clip": {"x": 0, "y": 0, "width": SIZE[0], "height": SIZE[1], "scale": 1},
        "captureBeyondViewport": False,
    })["data"])
    capture_ms = (time.perf_counter() - start) * 1000
    extraction_start = time.perf_counter()
    dom = _evaluate(backend, OBSERVATION_JS)
    ax = backend._call("Accessibility.getFullAXTree")["nodes"]
    accessible = []
    for node in ax:
        if node.get("ignored"):
            continue
        role = node.get("role", {}).get("value", "")
        # Root URL metadata is excluded; all actual visible accessible content retained.
        if role in ("RootWebArea", "none", "generic"):
            continue
        accessible.append({"role": role, "name": node.get("name", {}).get("value", ""),
                           "value": node.get("value", {}).get("value"),
                           "properties": node.get("properties", [])})
    extraction_ms = (time.perf_counter() - extraction_start) * 1000
    encode_start = time.perf_counter()
    path = out / f"{name}.png"
    path.write_bytes(raw_png)
    digest = hashlib.sha256(raw_png).hexdigest()
    revision = hashlib.sha256(json.dumps(dom, sort_keys=True).encode() + raw_png).hexdigest()
    encode_ms = (time.perf_counter() - encode_start) * 1000
    return {"image": path.name, "image_sha256": digest, "dimensions": list(SIZE),
            "captured_at": timestamp, "revision": revision, "target_id": backend.target_id,
            "process_id": backend.pid, "dom": dom, "ax": accessible,
            "phases_ms": {"capture": capture_ms, "extraction": extraction_ms, "encode": encode_ms}}


def proposal_for(spec: dict[str, Any], observations: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    binding = observations[0] if variant == "near_miss" and len(observations) > 1 else observations[-1]
    element = next(e for e in binding["dom"]["elements"] if e["target_id"] == spec["target"])
    r = element["bounds"]
    return {"kind": "click", "target_id": spec["target"], "bounds": r,
            "x": r["x"] + r["width"] / 2, "y": r["y"] + r["height"] / 2,
            "observation_revision": binding["revision"], "browser_target_id": binding["target_id"]}


def guard(case: dict[str, Any], current: dict[str, Any]) -> tuple[bool, str]:
    """Deterministic scope/freshness, with no ground-truth admission gate."""
    proposal = case["proposal"]
    if proposal["browser_target_id"] != current["target_id"]:
        return False, "wrong_browser_target"
    if proposal["observation_revision"] != current["revision"]:
        return False, "stale_observation"
    target = next((e for e in current["dom"]["elements"]
                   if e["target_id"] == proposal["target_id"]), None)
    if target is None or target.get("disabled", False):
        return False, "target_unavailable"
    if target["bounds"] != proposal["bounds"]:
        return False, "target_geometry_changed"
    return True, "scope_and_binding_pass"


def _conformance(backend: Any, case: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    allowed, reason = guard(case, current)
    if case["expected"] is not True:
        allowed, reason = False, "scripted_ground_truth_trajectory_abstains"
    before = _evaluate(backend, "window.fixtureState")
    dispatch_ms = 0.0
    if allowed:
        proposal = case["proposal"]
        dispatch_start = time.perf_counter()
        for event in ("mousePressed", "mouseReleased"):
            backend._call("Input.dispatchMouseEvent", {"type": event, "x": proposal["x"],
                          "y": proposal["y"], "button": "left", "clickCount": 1})
        dispatch_ms = (time.perf_counter() - dispatch_start) * 1000
    read_start = time.perf_counter()
    after = _evaluate(backend, "window.fixtureState")
    family = case["family"]
    if not allowed:
        passed = before == after
    elif family == "toolbar_glyph":
        passed = after.get("mode") == "crop"
    elif family == "map_containment":
        selected = after.get("selected")
        oracle = case["oracle"]
        passed = selected == case["proposal"]["target_id"] and point_in_polygon(
            tuple(oracle["points_canvas"][selected]), oracle["polygon"])
    else:
        passed = after.get("action") == "approve"
    return {"kind": "scripted_ground_truth_conformance", "dispatch_allowed": allowed,
            "guard_reason": reason, "passed": passed, "before": before, "after": after,
            "phases_ms": {"dispatch": dispatch_ms, "readback": (time.perf_counter() - read_start) * 1000,
                          "total": (time.perf_counter() - start) * 1000},
            "independent_postcondition": "fixture_state_after_real_cdp_input"}


def capture(out: Path) -> list[dict[str, Any]]:
    """Capture fresh evidence; refusal to overwrite makes receipts unambiguous."""
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError(f"Capture directory exists: {out}")
    out.mkdir(parents=True)
    if not REFERENCE.exists():
        raise RuntimeError("Local arc-cua reference checkout is unavailable")
    sys.path.insert(0, str(REFERENCE))
    from arc_cua.backends.chrome import ChromeBackend

    profile = out / "chrome-profile"
    profile.mkdir()
    cases = []
    setup = time.perf_counter()
    try:
        with ChromeBackend.launch(headless=True, user_data_dir=str(profile), window_size=SIZE) as backend:
            backend._call("Emulation.setDeviceMetricsOverride", {
                "width": SIZE[0], "height": SIZE[1], "deviceScaleFactor": 1, "mobile": False})
            startup_ms = (time.perf_counter() - setup) * 1000
            for index, (family, variant) in enumerate((f, v) for f in FAMILIES for v in VARIANTS):
                spec = fixture(family, variant)
                source = out / f"fixture-{index:02}.html"
                source.write_text(spec["html"])
                navigate = time.perf_counter()
                backend.navigate(source.as_uri(), quiet_s=0.05)
                navigate_ms = (time.perf_counter() - navigate) * 1000
                observations = [_observe(backend, out, f"case-{index:02}-first")]
                mutations = []
                if family == "target_freshness":
                    if variant in ("near_miss", "text_control"):
                        _evaluate(backend, "window.changeLayout()")
                        mutations.append("window.changeLayout()")
                    if variant == "ambiguous":
                        _evaluate(backend, "window.coverLayout()")
                        mutations.append("window.coverLayout()")
                    observations.append(_observe(backend, out, f"case-{index:02}-current"))
                proposal = proposal_for(spec, observations, variant)
                visible = [{k: o[k] for k in ("captured_at", "revision", "dom", "ax")} for o in observations]
                text = json.dumps({"observations_in_time_order": visible,
                                   "current_revision": observations[-1]["revision"],
                                   "offered_proposal": proposal}, sort_keys=True)
                case = {"id": f"B{index + 1:02}", "family": family, "variant": variant,
                        "surface": "browser_fixture", "expected": spec["oracle"]["expected"],
                        "question": spec["question"], "text": text,
                        "images": [o["image"] for o in observations], "proposal": proposal,
                        "oracle": spec["oracle"], "recipe": {"family": family, "variant": variant,
                                                             "mutations": mutations},
                        "capture": {"observations": observations,
                            "images": [{"path": o["image"], "sha256": o["image_sha256"],
                                        "dimensions": o["dimensions"]} for o in observations],
                            "source_sha256": hashlib.sha256(spec["html"].encode()).hexdigest(),
                            "phase_total_ms": sum(sum(o["phases_ms"].values()) for o in observations),
                            "capture_ms": sum(o["phases_ms"]["capture"] for o in observations),
                            "extraction_ms": sum(o["phases_ms"]["extraction"] for o in observations),
                            "encode_ms": sum(o["phases_ms"]["encode"] for o in observations),
                            "startup_ms": startup_ms if index == 0 else 0.0,
                            "navigation_ms": navigate_ms,
                            "method": "arc_cua.ChromeBackend + CDP DOM/AX/screenshot; no OCR"}}
                case["conformance"] = _conformance(backend, case, observations[-1])
                cases.append(case)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    (out / "capture-summary.json").write_text(json.dumps({"cases": len(cases),
        "conformance_passed": sum(c["conformance"]["passed"] for c in cases),
        "surface": "authored_browser_fixture", "dimensions": list(SIZE)}, indent=2) + "\n")
    return cases


def replay_case(case: dict[str, Any], accepted: bool, out: Path) -> dict[str, Any]:
    """Replay a model band decision on a fresh safe fixture; inspect effect separately.

    Recipe metadata restores the rendered surface, but neither expected label nor
    variant decides admission. Wrong semantic acceptances can therefore produce
    an observable wrong fixture effect rather than being hidden by an oracle gate.
    """
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError(f"Replay directory exists: {out}")
    out.mkdir(parents=True)
    sys.path.insert(0, str(REFERENCE))
    from arc_cua.backends.chrome import ChromeBackend

    profile = out / "chrome-profile"
    profile.mkdir()
    start = time.perf_counter()
    recipe = case["recipe"]
    spec = fixture(recipe["family"], recipe["variant"])
    source = out / "fixture.html"
    source.write_text(spec["html"])
    try:
        with ChromeBackend.launch(headless=True, user_data_dir=str(profile), window_size=SIZE) as backend:
            backend._call("Emulation.setDeviceMetricsOverride", {
                "width": SIZE[0], "height": SIZE[1], "deviceScaleFactor": 1, "mobile": False})
            backend.navigate(source.as_uri(), quiet_s=0.05)
            for mutation in recipe["mutations"]:
                if mutation not in ("window.changeLayout()", "window.coverLayout()"):
                    raise ValueError("Unknown bounded fixture mutation")
                _evaluate(backend, mutation)
            current = _observe(backend, out, "current")
            setup_capture_ms = (time.perf_counter() - start) * 1000
            guard_start = time.perf_counter()
            # Process identity differs in reconstruction. Compare the evidence
            # binding against original current observation, then rebind scope
            # to this run-owned browser target after content identity check.
            original = case["capture"]["observations"][-1]
            proposal = dict(case["proposal"])
            same_content = current["revision"] == original["revision"]
            bound = dict(case)
            proposal["browser_target_id"] = current["target_id"]
            bound["proposal"] = proposal
            allowed, reason = guard(bound, current)
            if not same_content:
                allowed, reason = False, "reconstruction_content_changed"
            if case["proposal"]["browser_target_id"] != original["target_id"]:
                allowed, reason = False, "original_target_scope_mismatch"
            if not accepted:
                allowed, reason = False, "model_not_confidently_true"
            guard_ms = (time.perf_counter() - guard_start) * 1000
            before = _evaluate(backend, "window.fixtureState")
            dispatch_ms = 0.0
            if allowed:
                dispatch_start = time.perf_counter()
                for event in ("mousePressed", "mouseReleased"):
                    backend._call("Input.dispatchMouseEvent", {"type": event, "x": proposal["x"],
                                  "y": proposal["y"], "button": "left", "clickCount": 1})
                dispatch_ms = (time.perf_counter() - dispatch_start) * 1000
            read_start = time.perf_counter()
            after = _evaluate(backend, "window.fixtureState")
            if recipe["family"] == "toolbar_glyph":
                goal_met = after.get("mode") == "crop"
            elif recipe["family"] == "map_containment":
                selected = after.get("selected")
                polygon = spec["oracle"]["polygon"]
                goal_met = bool(selected and polygon and point_in_polygon(
                    tuple(spec["oracle"]["points_canvas"][selected]), polygon))
            else:
                goal_met = after.get("action") == "approve"
            receipt = {"surface": "browser_fixture", "accepted": accepted,
                       "dispatched": allowed, "guard_reason": reason, "goal_met": goal_met,
                       "effect_changed": before != after, "wrong_effect": allowed and before != after and not goal_met,
                       "before": before, "after": after, "current_observation": current,
                       "reconstruction_content_matches": same_content,
                       "phases_ms": {"dispatch": dispatch_ms,
                            "setup_capture": setup_capture_ms, "validation": guard_ms,
                            "readback": (time.perf_counter() - read_start) * 1000,
                            "total": (time.perf_counter() - start) * 1000},
                       "evaluation": "oracle used only in independent goal/effect check"}
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cases = capture(args.out)
    print(json.dumps({"cases": len(cases), "conformance_passed": sum(c["conformance"]["passed"] for c in cases)}))


if __name__ == "__main__":
    main()
