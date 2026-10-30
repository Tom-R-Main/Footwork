"""Installed synthetic OCR/review qualification and missing-camera refusal.

No physical device is opened. The harness approves only an OCR candidate that
exactly matches its generated fixture text. Use fresh output and an installed
TrueType font; Linux needs Tesseract English data and FFmpeg.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--font", type=Path, required=True)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(mode=0o700)
os.environ["FOOTWORK_TOOL_OUTPUT_ROOT"] = str(root / "runs")
font = ImageFont.truetype(str(args.font), 48)
image = Image.new("RGB", (1200, 240), "white")
ImageDraw.Draw(image).multiline_text(
    (35, 35), "FOOTWORK LINUX\nExact reviewed note 42.", font=font, fill="black", spacing=15
)
image.save(root / "fixture.png")
ImageOps.mirror(image).save(root / "mirrored.png")


def call(name, *args, expect=0):
    args = list(args)
    if "--run-dir" in args:
        index = args.index("--run-dir") + 1
        family = "desk-inbox-experiment" if args[0] == "inbox" else "camera-capture-experiment"
        args[index] = str(root / "runs" / family / args[index])
    r = subprocess.run(
        [sys.executable, "-I", "-m", "jevdual.cli", *args], capture_output=True, text=True, timeout=90, check=False
    )
    (root / (name + ".stdout")).write_text(r.stdout)
    (root / (name + ".stderr")).write_text(r.stderr)
    assert r.returncode == expect, (name, r.returncode, r.stdout, r.stderr)
    return json.loads(r.stdout)


receipts = []
for name, filename, extra in [("direct", "fixture.png", []), ("mirror", "mirrored.png", ["--mirror-input"])]:
    source = root / filename
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    prepared = call(
        name + "-prepare", "inbox", "prepare", "--run-dir", name, "--fixture-image", str(source), *extra
    )
    assert prepared["state"] == "needs_review", prepared
    run = root / "runs" / "desk-inbox-experiment" / name
    candidate = (run / "candidate.txt").read_text()
    assert candidate == "FOOTWORK LINUX\nExact reviewed note 42.\n", repr(candidate)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    accepted = call(
        name + "-accept",
        "inbox",
        "accept",
        "--run-dir",
        name,
        "--approved-sha256",
        prepared["candidate_sha256"],
    )
    assert accepted["state"] == "saved", accepted
    replay = call(
        name + "-repeat",
        "inbox",
        "accept",
        "--run-dir",
        name,
        "--approved-sha256",
        prepared["candidate_sha256"],
    )
    assert replay["state"] == "saved"
    status = call(name + "-status", "inbox", "status", "--run-dir", name)
    assert status["current_artifact_check"]["ok"]
    receipts.append(
        {
            "case": name,
            "source_unchanged": True,
            "exact_candidate": True,
            "saved": True,
            "repeat_saved": True,
            "note_sha256": prepared["candidate_sha256"],
        }
    )
doctor = call("camera-doctor", "camera", "doctor", "--run-dir", "camera")
assert doctor["backend"] == "v4l2" and doctor["permission_status"] == "not_checked"
refusal = call(
    "camera-missing",
    "camera",
    "capture",
    "--run-dir",
    "camera",
    "--camera",
    "/dev/video999",
    "--token",
    "missing",
    expect=2,
)
result = {
    "ocr_synthetic_cases": receipts,
    "camera_inventory": doctor,
    "camera_missing_refusal": refusal,
    "physical_camera_qualified": False,
}
(root / "receipt.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result))
