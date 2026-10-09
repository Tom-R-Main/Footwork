"""Deterministic authored development inputs, explicitly ineligible for qualification."""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from jevdual.visual_checks import CropSpec
from jevdual.visual_evidence import Bounds, Surface, bind_visual
from PIL import Image, ImageDraw


def save_json(path: Path, value: object) -> None:
    # Atomic, fsynced publication; a callback cannot precede its durable reservation.
    data = json.dumps(value, indent=2, allow_nan=False) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=".vq-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _asset(root: Path, name: str, im: Image.Image) -> dict:
    buffer = io.BytesIO()
    im.save(buffer, format="PNG")
    data = buffer.getvalue()
    path = root / "assets" / name
    path.write_bytes(data)
    return {"path": f"assets/{name}", "sha256": hashlib.sha256(data).hexdigest(),
            "dimensions": list(im.size)}


def _page(style: int, changed: bool = False) -> Image.Image:
    im = Image.new("RGB", (480, 360), "white")
    d = ImageDraw.Draw(im)
    color = ("#246276", "#984b45", "#446936")[style]
    d.rectangle((20, 20, 460, 340), outline="black", width=3)
    d.text((50, 45), "FIELD NOTES", fill="black")
    if style == 1:
        d.rectangle((190, 100, 290, 200), fill=color)
    else:
        d.polygon(((240, 95), (170, 205), (310, 205)), fill=color)
    d.text((50, 270), "SITE SURVEY", fill="black")
    d.text((50, 300), "REVISION 8" if changed else "REVISION 3", fill="black")
    return im


def seed_corpus(out: Path) -> Path:
    """Never overwrite an old corpus; no private documents or screenshots are read."""
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    (out / "assets").mkdir(mode=0o700)
    cases, labels = [], {}
    stamp = datetime.now(UTC).isoformat()
    for role_index, role in enumerate(("document_reference_match", "crop_subject_containment")):
        for style in range(3):
            for variant in ("supported", "near_miss", "ambiguous", "text_control"):
                ident = f"c{len(cases) + 1:03d}"
                expected = False if variant == "near_miss" else None if variant == "ambiguous" else True
                text = "Offered preview has no additional accessible description."
                crop = None
                if role_index == 0:
                    resource_im = _page(style)
                    capture_im = _page(style, changed=variant == "near_miss")
                    criterion = "Assess whether the offered page matches the supplied reference, including its revision."
                    if variant == "ambiguous":
                        ImageDraw.Draw(capture_im).rectangle((21, 250, 459, 339), fill="#888888")
                        text = "Lower preview area is obscured."
                    if variant == "text_control":
                        text = ("Reference and offered page each show FIELD NOTES; SITE SURVEY; REVISION 3. "
                                f"Both have the same centered {'square' if style == 1 else 'triangle'} symbol "
                                "and page border, with no obscured areas.")
                else:
                    resource_im = Image.new("RGB", (480, 360), "white")
                    d = ImageDraw.Draw(resource_im)
                    shift = style * 8
                    subject = (140 + shift, 60, 335 + shift, 300)
                    d.ellipse((200 + shift, 60, 280 + shift, 140), fill="#cc8a3f", outline="black")
                    d.rectangle((200 + shift, 135, 280 + shift, 300), fill="#cc8a3f", outline="black")
                    d.rectangle((140 + shift, 160, 340 + shift, 172), fill="#cc8a3f", outline="black")
                    rectangle = Bounds(120 + shift, 40, 250, 280)
                    if variant == "near_miss":
                        rectangle = Bounds(175 + shift, 40, 195, 280)
                    if variant == "ambiguous":
                        d.rectangle((125 + shift, 145, 210 + shift, 185), fill="#aaaaaa")
                        text = "A foreground opaque patch hides part of the orange figure."
                    capture_im = resource_im.copy()
                    cd = ImageDraw.Draw(capture_im)
                    cd.rectangle((rectangle.x, rectangle.y, rectangle.x + rectangle.width,
                                  rectangle.y + rectangle.height), outline="#0066dd", width=3)
                    criterion = "Does the proposed rectangle retain the entire orange figure, including both arms?"
                    crop = CropSpec(rectangle, Bounds(0, 0, 480, 360)).to_dict()
                    if variant == "text_control":
                        text = (f"Complete visible orange figure extent: x={subject[0]}..{340 + shift}, "
                                f"y={subject[1]}..{subject[3]}; crop x={rectangle.x}.."
                                f"{rectangle.x + rectangle.width}, y=40..320. No occlusion.")
                capture_asset = _asset(out, ident + "-a.png", capture_im)
                resource_asset = _asset(out, ident + "-b.png", resource_im)
                capture = bind_visual(
                    png=(out / capture_asset['path']).read_bytes(), surface=Surface("native", pid=1, window_id=2),
                    observation_id="authored-observation", captured_at=stamp, viewport=Bounds(0, 0, 480, 360),
                    target_id="1", target_token="authored-placeholder", target_bounds=Bounds(0, 0, 480, 360),
                    operation="inspect", postcondition="appearance assessment only",
                )
                source_record = out / f"{ident}-source.txt"
                source_record.write_text("Authored fixture; synthetic surface IDs; no real native capture.\n"
                                         f"Construction: role={role}; style={style}; variant={variant}.\n")
                cases.append({
                    "id": ident, "role": role, "source_group": f"g{role_index * 3 + style + 1:03d}",
                    "input": {"criterion": criterion, "criterion_version": "vq-v1", "accessible_text": text,
                              "capture": capture_asset | {"binding": capture.to_dict()},
                              "resource": resource_asset | {"resource_id": "supplied-resource", "revision": "v1",
                                                            "page": 1, "render_recipe": "authored-vq-fixture"},
                              "crop": crop},
                    "provenance": {"kind": "authored_fixture", "source_record": {
                        "path": source_record.name, "sha256": hashlib.sha256(source_record.read_bytes()).hexdigest()},
                        "labelers": ["fixture-construction"], "adjudicated": False},
                })
                labels[ident] = expected
    save_json(out / "labels.json", {"version": 1, "labels": labels})
    save_json(out / "manifest.json", {"version": 1, "split": "development", "labels": {
        "path": "labels.json", "sha256": hashlib.sha256((out / 'labels.json').read_bytes()).hexdigest()},
        "cases": cases})
    return out / "manifest.json"
