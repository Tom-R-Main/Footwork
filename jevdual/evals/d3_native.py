"""Actual AppKit window captures and background AX effects for D3 development cases.

These authored native fixtures qualify capture mechanics, not Finder/Preview behavior.
Oracle/config files are retained separately and never serialized into model text.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw

VARIANTS = ("supported", "near_miss", "ambiguous", "text_control")
FAMILIES = ("document_identity", "crop_boundary", "export_finalizing")
APP = Path(__file__).parent / "visual/d3/native/app.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoding_error(raw: Image.Image, encoded: Image.Image) -> tuple[float, int]:
    histogram = ImageChops.difference(raw.convert("RGB"), encoded.convert("RGB")).histogram()
    squared = sum(count * (index % 256) ** 2 for index, count in enumerate(histogram))
    rmse = math.sqrt(squared / (raw.width * raw.height * 3))
    maximum = max(index % 256 for index, count in enumerate(histogram) if count)
    return rmse, maximum


def raster_document(path: Path, symbol: str) -> None:
    """A locally authored raster-only PDF; repeated content has identical immutable hash."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    page = Image.new("RGB", (185, 260), "white")
    draw = ImageDraw.Draw(page)
    if symbol == "triangle":
        draw.polygon([(92, 35), (42, 110), (142, 110)], fill="#23647b")
    else:
        draw.ellipse((47, 30, 137, 120), fill="#23647b")
    draw.text((30, 150), "FIELD NOTES", fill="black")
    draw.text((35, 175), "SITE SURVEY", fill="black")
    pdf = canvas.Canvas(str(path), pagesize=(185, 260), invariant=1)
    pdf.drawImage(ImageReader(page), 0, 0, width=185, height=260)
    pdf.showPage()
    pdf.save()


def build_fixture(directory: Path, family: str, variant: str) -> dict[str, Any]:
    """Author raster content, ordinary AX controls and a separate deterministic oracle."""
    directory.mkdir(parents=True, exist_ok=True)
    expected = None if variant == "ambiguous" else variant != "near_miss"
    image = Image.new("RGB", (620, 316), "#f2f3f5")
    draw = ImageDraw.Draw(image)
    config: dict[str, Any] = {"family": family, "variant": variant}
    if family == "document_identity":
        symbols = ("triangle", "circle", "triangle" if variant != "near_miss" else "circle")
        for x, title, symbol in zip(
            (8, 212, 416), ("Reference", "Candidate A", "Candidate B"), symbols, strict=True
        ):
            draw.text((x + 10, 10), title, fill="black")
            draw.rectangle((x, 35, x + 185, 295), fill="white", outline="#222222", width=2)
            if variant != "ambiguous":
                if symbol == "triangle":
                    draw.polygon([(x + 92, 70), (x + 42, 145), (x + 142, 145)], fill="#23647b")
                else:
                    draw.ellipse((x + 47, 65, x + 137, 155), fill="#23647b")
                draw.text((x + 30, 185), "FIELD NOTES", fill="black")
                draw.text((x + 35, 210), "SITE SURVEY", fill="black")
            else:
                draw.text((x + 28, 135), "Preview unavailable", fill="black")
        # Hashes belong to source artifacts, not answer-bearing filenames or model metadata.
        for index, symbol in enumerate(symbols):
            raster_document(directory / f"source-{index}.pdf", symbol)
        config.update(
            source_hashes=[digest(directory / "source-1.pdf"), digest(directory / "source-2.pdf")],
            reference_hash=digest(directory / "source-0.pdf"),
            buttons=["Select Candidate A", "Select Candidate B"],
            caption="Select the document matching the reference cover.",
        )
        if variant == "text_control":
            config["caption"] = (
                "Reference: teal triangle. Candidate A: teal circle. Candidate B: teal triangle."
            )
        question = "Does the observed evidence support selecting Candidate B as the document matching the reference cover?"
        proposal = {"action": "AXPress", "target_label": "Select Candidate B", "candidate_index": 1}
        positive_label = "Select Candidate B" if variant != "near_miss" else "Select Candidate A"
        # Near miss has A=triangle/B=circle; supported has A=circle/B=triangle.
        if variant == "near_miss":
            raster_document(directory / "source-1.pdf", "triangle")
            config["source_hashes"][0] = digest(directory / "source-1.pdf")
            # Render candidate A as the reference for the executable positive trajectory.
            draw.rectangle((212, 35, 397, 295), fill="white", outline="#222222", width=2)
            draw.polygon([(304, 70), (254, 145), (354, 145)], fill="#23647b")
            draw.text((242, 185), "FIELD NOTES", fill="black")
            draw.text((247, 210), "SITE SURVEY", fill="black")
        oracle = {"reference_hash": config["reference_hash"], "positive_label": positive_label}
    elif family == "crop_boundary":
        draw.text((12, 10), "Crop proposal (blue outline); retain the entire subject", fill="black")
        if variant != "ambiguous":
            draw.ellipse((260, 70, 360, 170), fill="#ce8d42", outline="#432f21", width=2)
            draw.rectangle((280, 165, 340, 260), fill="#ce8d42", outline="#432f21", width=2)
        else:
            draw.rectangle((0, 40, 619, 300), fill="#999999")
            draw.text((230, 150), "Image unavailable", fill="black")
        proposed = [220, 45, 400, 280] if variant != "near_miss" else [290, 45, 400, 280]
        draw.rectangle(proposed, outline="#156bdf", width=4)
        config.update(
            buttons=["Apply proposed crop", "Apply safe crop"],
            proposed_crop=proposed,
            valid_crop=[220, 45, 400, 280],
            caption="Apply the displayed crop while preserving the entire subject.",
        )
        if variant == "text_control":
            config["caption"] = "Subject bounds x260..360 y70..260. Crop bounds x220..400 y45..280."
        question = "Does the displayed proposed crop rectangle preserve the entire visible subject?"
        proposal = {"action": "apply_crop", "rectangle": proposed, "target_label": "Apply proposed crop"}
        oracle = {
            "subject_bounds": [260, 70, 360, 260],
            "valid_crop": config["valid_crop"],
            "positive_label": "Apply safe crop",
        }
    else:
        draw.text((35, 40), "Export", fill="black")
        draw.rectangle((35, 95, 580, 128), fill="#3579b8")
        draw.text((280, 105), "100%", fill="white")
        phase = "complete" if expected is True else "finalizing"
        if variant == "ambiguous":
            phase = "unknown"
        draw.text(
            (40, 165),
            "Export complete"
            if phase == "complete"
            else "Finalizing output..."
            if phase == "finalizing"
            else "Status unavailable",
            fill="black",
        )
        if phase == "finalizing":
            draw.arc((270, 205, 310, 245), 20, 290, fill="#3579b8", width=5)
        config.update(buttons=["Finish export"], caption="Export progress: 100%", phase=phase)
        if variant == "text_control":
            config["caption"] = "Export progress: 100%. Status: Export complete. Output available."
        if phase == "complete":
            (directory / "export.txt").write_text("D3 fixture exported content\n")
        question = "Does the current observed export state support reporting that export has completed and the output is available?"
        proposal = {"action": "report_complete", "target_label": "Finish export"}
        oracle = {
            "phase": phase,
            "positive_label": "Finish export",
            "output_content": "D3 fixture exported content\n",
        }
    image.save(directory / "view.png", optimize=True)
    (directory / "config.json").write_text(json.dumps(config, indent=2))
    (directory / "oracle.json").write_text(json.dumps(oracle, indent=2))
    return {
        "family": family,
        "variant": variant,
        "expected": expected,
        "question": question,
        "proposal": proposal,
        "oracle": oracle,
    }


async def observe(driver: Any, pid: int, wid: int, screenshot: Path | None = None) -> Any:
    from cua_driver import GetWindowStateInput

    return await driver.get_window_state(
        GetWindowStateInput(
            pid=pid,
            window_id=wid,
            session=None,
            query=None,
            include_accessibility_tree=True,
            include_screenshot=screenshot is not None,
            screenshot_out_file=str(screenshot) if screenshot else None,
            max_elements=500,
            max_depth=None,
            max_dimension=660,
            max_image_dimension=None,
            full_output=True,
        )
    )


def ax_text(pid: int, wid: int) -> tuple[str, list[dict[str, Any]]]:
    from jevdual import ax

    root = ax.window_element(pid, wid)
    nodes = []
    stack = [root]
    while stack and len(nodes) < 500:
        element = stack.pop()
        node = {
            key: str(value)
            for key in ("AXRole", "AXTitle", "AXDescription", "AXValue")
            if (value := ax._attr(element, key)) is not None
        }
        frame = ax.frame_of(element)
        if frame:
            node["bounds"] = [frame.x, frame.y, frame.w, frame.h]
        nodes.append(node)
        stack.extend(reversed(list(ax._attr(element, "AXChildren") or ())))
    return json.dumps(nodes, ensure_ascii=False), nodes


def native_ocr(screenshot: Path) -> list[dict[str, Any]]:
    """Existing macOS Vision through PyObjC, including visible raster text and bounds."""
    import objc
    from Foundation import NSURL

    objc.loadBundle("Vision", globals(), bundle_path="/System/Library/Frameworks/Vision.framework")
    request = objc.lookUpClass("VNRecognizeTextRequest").alloc().init()
    handler = (
        objc.lookUpClass("VNImageRequestHandler")
        .alloc()
        .initWithURL_options_(NSURL.fileURLWithPath_(str(screenshot.resolve())), {})
    )
    result = handler.performRequests_error_([request], None)
    success = result[0] if isinstance(result, tuple) else result
    if not success:
        raise RuntimeError("macOS Vision OCR failed")
    out = []
    for observation in request.results() or ():
        candidates = observation.topCandidates_(1)
        if not candidates:
            continue
        box = observation.boundingBox()
        out.append(
            {
                "text": str(candidates[0].string()),
                "confidence": float(candidates[0].confidence()),
                "normalized_bounds_bottom_left": [
                    float(box.origin.x),
                    float(box.origin.y),
                    float(box.size.width),
                    float(box.size.height),
                ],
            }
        )
    return out


def press(pid: int, wid: int, label: str) -> dict[str, Any]:
    """Background AXPress against the fresh bound window; never activates application."""
    from ApplicationServices import AXUIElementPerformAction
    from jevdual import ax

    root = ax.window_element(pid, wid)
    matches = [el for el in ax.elements_by_role(root, "AXButton") if str(ax._attr(el, "AXTitle")) == label]
    if len(matches) != 1:
        return {"dispatched": False, "reason": "target_missing_or_ambiguous", "matches": len(matches)}
    error = int(AXUIElementPerformAction(matches[0], "AXPress"))
    return {
        "dispatched": error == 0,
        "route": "background_accessibility",
        "error_code": error,
        "target_label": label,
    }


def check_effect(directory: Path, family: str, oracle: dict[str, Any]) -> bool:
    effect_path = directory / "effect.json"
    if not effect_path.exists():
        return False
    effect = json.loads(effect_path.read_text())
    if family == "document_identity":
        selected = directory / "selected.pdf"
        return (
            selected.exists()
            and digest(selected) == oracle["reference_hash"]
            and effect.get("selected_hash") == digest(selected)
        )
    if family == "crop_boundary":
        from PIL import ImageChops

        bounds = oracle["subject_bounds"]
        rectangle = effect.get("saved_crop")
        artifact = directory / "cropped.png"
        if not rectangle or not artifact.exists():
            return False
        saved = Image.open(artifact).convert("RGB")
        intended = Image.open(directory / "view.png").convert("RGB").crop(rectangle)
        pixels_match = (
            saved.size == intended.size and ImageChops.difference(saved, intended).getbbox() is None
        )
        return bool(
            rectangle
            and pixels_match
            and rectangle[0] <= bounds[0]
            and rectangle[1] <= bounds[1]
            and rectangle[2] >= bounds[2]
            and rectangle[3] >= bounds[3]
        )
    return (directory / "export.txt").read_text() == oracle["output_content"] and effect.get(
        "output_hash"
    ) == digest(directory / "export.txt")


async def _capture(out: Path) -> list[dict[str, Any]]:
    from cua_driver import CuaDriver

    driver = CuaDriver.create(embedded=True)
    cases = []
    for family in FAMILIES:
        for variant in VARIANTS:
            directory = out / f"native-{family}-{variant}"
            case = build_fixture(directory, family, variant)
            stderr = (directory / "app-stderr.txt").open("w")
            process = await asyncio.to_thread(
                subprocess.Popen,
                [sys.executable, str(APP), str(directory)],
                stdout=subprocess.DEVNULL,
                stderr=stderr,
            )
            try:
                started = time.perf_counter()
                while not (directory / "ready.json").exists():
                    if process.poll() is not None or time.perf_counter() - started > 10:
                        raise RuntimeError(f"Native fixture failed to start: {directory}")
                    await asyncio.sleep(0.05)
                ready = json.loads((directory / "ready.json").read_text())
                pid, wid = ready["pid"], ready["window_id"]
                await asyncio.sleep(0.15)
                screenshot = directory / "capture.png"
                captured_at = datetime.now(UTC).isoformat()
                t0 = time.perf_counter()
                await observe(driver, pid, wid, screenshot)
                capture_ms = (time.perf_counter() - t0) * 1000
                t0 = time.perf_counter()
                text, nodes = ax_text(pid, wid)
                extraction_ms = (time.perf_counter() - t0) * 1000
                (directory / "ax.json").write_text(json.dumps(nodes, indent=2))
                t0 = time.perf_counter()
                ocr = native_ocr(screenshot)
                ocr_ms = (time.perf_counter() - t0) * 1000
                (directory / "ocr.json").write_text(json.dumps(ocr, indent=2))
                text += (
                    "\nmacOS Vision OCR (visible screenshot text, not hidden file contents):\n"
                    + json.dumps(ocr, ensure_ascii=False)
                )
                size = Image.open(screenshot).size
                # Keep the exact Driver PNG; encode simple run-owned fixture pixels using
                # an explicit 256-color palette so full AX/OCR plus image fits the body cap.
                t0 = time.perf_counter()
                raw_screenshot = directory / "capture-raw.png"
                raw_screenshot.write_bytes(screenshot.read_bytes())
                im = Image.open(screenshot).convert("RGB")
                encoded = im.quantize(colors=256)
                encoded.save(screenshot, optimize=True)
                encoding_rmse, encoding_max_delta = encoding_error(im, encoded)
                encoding_ms = (time.perf_counter() - t0) * 1000
                case.update(
                    id=f"native-{family}-{variant}",
                    surface="native_fixture",
                    text=text,
                    question={"instructions": case["question"]},
                    images=[str(screenshot.relative_to(out))],
                    capture={
                        "pid": pid,
                        "window_id": wid,
                        "timestamp": captured_at,
                        "revision": 1,
                        "sha256": digest(screenshot),
                        "raw_capture_sha256": digest(raw_screenshot),
                        "encoding": "256-color indexed PNG; exact Cua Driver raw PNG retained separately",
                        "dimensions": list(size),
                        "images": [
                            {
                                "path": str(screenshot.relative_to(out)),
                                "sha256": digest(screenshot),
                                "dimensions": list(size),
                            }
                        ],
                        "capture_ms": capture_ms + extraction_ms + ocr_ms + encoding_ms,
                        "screenshot_ms": capture_ms,
                        "phase_total_ms": capture_ms + extraction_ms + ocr_ms + encoding_ms,
                        "encoding_rmse": encoding_rmse,
                        "encoding_max_channel_delta": encoding_max_delta,
                        "extraction_ms": extraction_ms,
                        "encoding_ms": encoding_ms,
                        "ocr": "macOS Vision VNRecognizeTextRequest; all returned lines retained with confidence and normalized bounds",
                        "ocr_ms": ocr_ms,
                        "ax_nodes": len(nodes),
                        "ax_truncated": len(nodes) >= 500,
                        "text_sources": ["native AX tree", "macOS Vision OCR of bound-window screenshot"],
                        "source": "Cua Driver bound AppKit window + direct native AX tree",
                        "posture": "background_only",
                    },
                )
                t0 = time.perf_counter()
                before = (directory / "effect.json").exists()
                rejected = case["expected"] is not True
                # Negative/ambiguous proposal is not dispatched. A separate known-good path
                # establishes actual native action delivery and independently checked persistence.
                action = press(pid, wid, case["oracle"]["positive_label"])
                for _ in range(40):
                    if (directory / "effect.json").exists():
                        break
                    await asyncio.sleep(0.025)
                after_text, _ = ax_text(pid, wid)
                case["conformance"] = {
                    "scripted_proposal_choice": "skip_negative_or_ambiguous" if rejected else "positive",
                    "negative_proposal_dispatched": False,
                    "effect_existed_before": before,
                    "positive_trajectory": action,
                    "postcondition": check_effect(directory, family, case["oracle"]),
                    "dispatch_readback_ms": (time.perf_counter() - t0) * 1000,
                    "fresh_readback_observed": bool(after_text),
                    "scope": "scripted conformance; not provider-driven dispatch",
                }
                (directory / "case.json").write_text(json.dumps(case, indent=2))
                cases.append(case)
            finally:
                process.terminate()
                await asyncio.to_thread(process.wait, timeout=5)
                stderr.close()
    return cases


def capture(out: Path) -> list[dict[str, Any]]:
    if out.exists() and any(out.iterdir()):
        raise ValueError("Native capture requires a fresh or empty output directory")
    out.mkdir(parents=True, exist_ok=True)
    return asyncio.run(_capture(out))


async def _replay(case: dict[str, Any], accepted: bool, out: Path) -> dict[str, Any]:
    """Reconstruct the frozen case; no label/oracle branch decides admission."""
    from cua_driver import CuaDriver

    total_start = time.perf_counter()
    recipe = build_fixture(out, case["family"], case["variant"])
    stderr = (out / "app-stderr.txt").open("w")
    process = await asyncio.to_thread(
        subprocess.Popen, [sys.executable, str(APP), str(out)], stdout=subprocess.DEVNULL, stderr=stderr
    )
    try:
        while not (out / "ready.json").exists():
            if process.poll() is not None or time.perf_counter() - total_start > 10:
                raise RuntimeError("Native replay fixture startup failed")
            await asyncio.sleep(0.05)
        ready = json.loads((out / "ready.json").read_text())
        pid, wid = ready["pid"], ready["window_id"]
        await asyncio.sleep(0.1)
        await observe(CuaDriver.create(embedded=True), pid, wid)
        text, nodes = ax_text(pid, wid)
        setup_ms = (time.perf_counter() - total_start) * 1000
        effect_start = time.perf_counter()
        dispatched = False
        final_accepted = False
        actual_postcondition = False
        reason = "model_not_accepted"
        action = None
        if accepted:
            if case["family"] == "export_finalizing":
                # Completion claim requires independently readable persisted output.
                output = out / "export.txt"
                actual_postcondition = (
                    output.exists() and output.read_text() == "D3 fixture exported content\n"
                )
                final_accepted = actual_postcondition
                reason = (
                    "persisted_output_verified" if actual_postcondition else "output_missing_or_incomplete"
                )
            else:
                label = case["proposal"]["target_label"]
                observed = any(
                    node.get("AXRole") == "AXButton" and node.get("AXTitle") == label for node in nodes
                )
                if observed:
                    action = press(pid, wid, label)
                    dispatched = bool(action["dispatched"])
                    for _ in range(40):
                        if (out / "effect.json").exists():
                            break
                        await asyncio.sleep(0.025)
                    actual_postcondition = check_effect(out, case["family"], recipe["oracle"])
                    final_accepted = dispatched and actual_postcondition
                    reason = "effect_verified" if actual_postcondition else "effect_failed_independent_check"
                else:
                    reason = "fresh_target_missing"
        result = {
            "accepted_by_model": accepted,
            "final_accepted": final_accepted,
            "dispatched": dispatched,
            "postcondition_observed": actual_postcondition,
            "admission_reason": reason,
            "action": action,
            "setup_ms": setup_ms,
            "effect_ms": (time.perf_counter() - effect_start) * 1000,
            "total_ms": (time.perf_counter() - total_start) * 1000,
            "fresh_bound_window": {"pid": pid, "window_id": wid},
            "observation_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "surface": "native_fixture",
            "scope": "reconstructed authored fixture; independently checked persisted effect",
        }
        (out / "replay.json").write_text(json.dumps(result, indent=2))
        return result
    finally:
        process.terminate()
        await asyncio.to_thread(process.wait, timeout=5)
        stderr.close()


def replay_case(case: dict[str, Any], accepted: bool, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=False)
    return asyncio.run(_replay(case, accepted, out))


if __name__ == "__main__":
    result = capture(Path(sys.argv[1]))
    print(
        json.dumps(
            {
                "cases": len(result),
                "conformance_passed": sum(bool(case["conformance"]["postcondition"]) for case in result),
            }
        )
    )
