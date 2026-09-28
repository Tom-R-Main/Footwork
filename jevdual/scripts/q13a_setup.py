"""Q13a setup and oracles (docs/experiments/Q13a.md). The tasks themselves are driven by hand through
footwork commands; this script only makes the start states, keeps the fixture server up, and reads the
end states.

    uv run python scripts/q13a_setup.py serve OUT      # fixture server on :8766; GET record in OUT/gets.json
    uv run python scripts/q13a_setup.py setup OUT      # scratch files and documents for tasks 1, 3, 5
    uv run python scripts/q13a_setup.py check OUT      # run every oracle, write OUT/oracles.json
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.crossapp import downloaded_and_opened, one_submission, renamed, sha256
from evals.fixtures.server import SITE, serve

PORT = 8766
SCRATCH = Path.home() / "footwork-pilot" / "q13a"


def cmd_serve(out: Path) -> None:
    base, stop = serve(PORT)
    print(f"serving {base}; GET record in {out / 'gets.json'}", flush=True)
    try:
        while True:
            (out / "gets.json").write_text(json.dumps(stop.recorder.gets(), indent=1))
            time.sleep(1)
    except KeyboardInterrupt:
        stop()


def cmd_setup(out: Path) -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / "task1.txt").write_text("Price carried from the browser:\n")
    (SCRATCH / "notes.txt").write_text("Next search: quarterly report\n")
    (SCRATCH / "rename").mkdir(exist_ok=True)
    (SCRATCH / "rename" / "draft.txt").write_text("order notes\n")
    for old in (Path.home() / "Downloads").glob("quarterly-report*.txt"):
        old.unlink()
    for doc in ("task1.txt", "notes.txt"):
        subprocess.run(["open", "-a", "TextEdit", str(SCRATCH / doc)], check=False)
    subprocess.run(["open", str(SCRATCH / "rename")], check=False)
    subprocess.run(["open", "-a", "Calculator"], check=False)
    subprocess.run(["open", str(Path.home() / "Downloads")], check=False)
    (out / "setup.json").write_text(json.dumps({"scratch": str(SCRATCH), "t": time.time()}))
    print(f"start states ready under {SCRATCH}")


def cmd_check(out: Path) -> None:
    gets = json.loads((out / "gets.json").read_text()) if (out / "gets.json").exists() else {}
    opened = subprocess.run(
        ["osascript", "-e", 'tell application "TextEdit" to get path of every document'],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    report = next((p.strip() for p in opened.split(",") if p.strip().endswith("quarterly-report.txt")), None)
    oracles = {
        "2": one_submission(gets, "/confirm.html", "message", "624"),
        "3": one_submission(gets, "/search.html", "q", "quarterly report"),
        "4": downloaded_and_opened(
            Path.home() / "Downloads",
            (SITE / "quarterly-report.txt").read_bytes(),
            "quarterly-report.txt",
            report,
        ),
        "5": renamed(SCRATCH / "rename", "draft.txt", "B-20260921.txt", sha256(b"order notes\n")),
    }
    res = {k: {"ok": v.ok, "detail": v.detail} for k, v in oracles.items()}
    (out / "oracles.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(f"task {k}: {'confirmed' if v['ok'] else 'failed'}: {v['detail']}")


if __name__ == "__main__":
    what, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    {"serve": cmd_serve, "setup": cmd_setup, "check": cmd_check}[what](out)
