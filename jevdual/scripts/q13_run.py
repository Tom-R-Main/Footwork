"""Q13 (docs/experiments/Q13.md): the five cross-surface tasks driven by the model through
``jevdual.crossloop``, each run judged by its oracle. Acts on the desktop.

    uv run python scripts/q13_run.py --repeats 3 --out results/q13-20260928 [--task 1 --task 2]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jevdual.carry import check_append
from jevdual.crossloop import CrossLoop, Surface, to_json
from jevdual.desktop_s2 import meta_chat_from_env
from jevdual.keys import load_keys

from evals.crossapp import downloaded_and_opened, one_submission, renamed, sha256
from evals.fixtures.server import SITE, serve

SCRATCH = Path.home() / "footwork-pilot" / "q13"
DOWNLOADS = Path.home() / "Downloads"
MUSE_IN, MUSE_OUT = 0.10, 0.20  # USD per million tokens, Muse Spark contributor rates


def osa(script: str) -> str:
    return subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, check=False
    ).stdout.strip()


def task(n: int, rep: int, base: str) -> tuple[str, list[Surface], tuple[str, ...], Any, Any]:
    """``(task text, surfaces, requirements, oracle, cleanup)`` for task ``n`` repeat ``rep``; makes its start state."""
    tag = f"{n}-{rep}-{time.strftime('%H%M%S')}"
    if n == 1:
        doc = SCRATCH / f"prices-{tag}.txt"
        doc.write_text("Price carried from the browser:\n")
        before = {"text": doc.read_text()}
        subprocess.run(["open", "-a", "TextEdit", str(doc)], check=False)
        time.sleep(3)
        text = (
            "Read the price of the first book on books.toscrape.com and add it as a new line at the end of the "
            f"TextEdit document {doc.name}, then save the document."
        )
        surfaces = [
            Surface("web", "browser", url="https://books.toscrape.com/"),
            Surface("doc", "app", app="TextEdit", window=doc.name, authorize=("Save",)),
        ]
        reqs = ("The document's last line is the first book's price", "The document was saved")
        return (
            text,
            surfaces,
            reqs,
            lambda gets: check_append(doc, SimpleNamespace(text="£51.77"), before),
            lambda: osa(
                f'tell application "TextEdit" to close (every document whose name is "{doc.name}") saving no'
            ),
        )
    if n == 2:
        subprocess.run(["open", "-a", "Calculator"], check=False)
        time.sleep(2)
        text = (
            "Compute 48 times 13 in Calculator, then send the result as the message of the contact form, "
            'with name "Ada" and email "ada@example.com".'
        )
        surfaces = [
            Surface("calc", "app", app="Calculator"),
            Surface("web", "browser", url=f"{base}/form.html", authorize=("Send message",)),
        ]
        reqs = ("The contact form was sent", "The message sent is the product of 48 and 13")
        return (
            text,
            surfaces,
            reqs,
            lambda gets: one_submission(gets, "/confirm.html", "message", "624"),
            lambda: None,
        )
    if n == 3:
        doc = SCRATCH / f"notes-{tag}.txt"
        doc.write_text("Next search: quarterly report\n")
        subprocess.run(["open", "-a", "TextEdit", str(doc)], check=False)
        time.sleep(3)
        text = f"Search the shop for the text after 'Next search:' in the TextEdit note {doc.name}."
        surfaces = [
            Surface("note", "app", app="TextEdit", window=doc.name),
            Surface("web", "browser", url=f"{base}/search.html"),
        ]
        reqs = ("The shop's search results page is shown for the note's query",)
        return (
            text,
            surfaces,
            reqs,
            lambda gets: one_submission(gets, "/search.html", "q", "quarterly report"),
            lambda: osa(
                f'tell application "TextEdit" to close (every document whose name is "{doc.name}") saving no'
            ),
        )
    if n == 4:
        for old in DOWNLOADS.glob("quarterly-report*.txt"):
            old.unlink()
        subprocess.run(["open", str(DOWNLOADS)], check=False)
        time.sleep(2)
        text = "Download the shop's quarterly report (quarterly-report.txt) and open it in TextEdit."
        surfaces = [
            Surface("web", "browser", url=f"{base}/index.html"),
            Surface("finder", "app", app="Finder", window="Downloads"),
        ]
        reqs = ("The quarterly report was downloaded", "The report is open in TextEdit")

        def oracle4(gets):
            names = osa('tell application "TextEdit" to get path of every document')
            opened = next(
                (p.strip() for p in names.split(",") if p.strip().endswith("quarterly-report.txt")), None
            )
            return downloaded_and_opened(
                DOWNLOADS, (SITE / "quarterly-report.txt").read_bytes(), "quarterly-report.txt", opened
            )

        return (
            text,
            surfaces,
            reqs,
            oracle4,
            lambda: osa(
                'tell application "TextEdit" to close (every document whose name is "quarterly-report.txt") saving no'
            ),
        )
    folder = SCRATCH / f"rename-{tag}"
    folder.mkdir()
    (folder / "draft.txt").write_text("order notes\n")
    subprocess.run(["open", str(folder)], check=False)
    time.sleep(2)
    text = f"Rename draft.txt in the Finder folder {folder.name} to the order number shown on the shop's order page, keeping .txt."
    surfaces = [
        Surface("web", "browser", url=f"{base}/order-confirmed.html"),
        Surface("finder", "app", app="Finder", window=folder.name),
    ]
    reqs = ("draft.txt is renamed to the order number with .txt",)
    return (
        text,
        surfaces,
        reqs,
        lambda gets: renamed(folder, "draft.txt", "KB-20260921.txt", sha256(b"order notes\n")),
        lambda: osa(f'tell application "Finder" to close (every window whose name is "{folder.name}")'),
    )


async def main(tasks: list[int], repeats: int, out: Path) -> None:
    load_keys()
    chat = meta_chat_from_env()
    if chat is None:
        raise SystemExit("MODEL_API_KEY missing")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    base, stop = serve(0)
    rows = []
    try:
        for rep in range(1, repeats + 1):
            for n in tasks:
                text, surfaces, reqs, oracle, cleanup = task(n, rep, base)
                run_dir = out / f"task{n}-r{rep}"
                before_gets = {k: len(v) for k, v in stop.recorder.gets().items()}
                t0 = time.perf_counter()
                run = await CrossLoop(text, surfaces, chat, run_dir, requirements=reqs).run()
                wall = time.perf_counter() - t0
                gets = {k: v[before_gets.get(k, 0) :] for k, v in stop.recorder.gets().items()}
                check = oracle(gets)
                cleanup()
                row = {
                    "task": n,
                    "repeat": rep,
                    "status": run.status,
                    "reason": run.reason[:300],
                    "answer": run.answer,
                    "oracle_ok": check.ok,
                    "oracle": check.detail,
                    "steps": len(run.steps),
                    "input_tokens": run.input_tokens,
                    "output_tokens": run.output_tokens,
                    "cost_usd": run.input_tokens / 1e6 * MUSE_IN + run.output_tokens / 1e6 * MUSE_OUT,
                    "wall_s": wall,
                }
                rows.append(row)
                (run_dir / "run.json").write_text(json.dumps(to_json(run), indent=1, default=str))
                (out / "results.json").write_text(json.dumps(rows, indent=1))
                print(
                    f"task {n} r{rep}: {run.status} ({run.reason[:80]}); oracle {'confirmed' if check.ok else 'failed'}: {check.detail[:90]}",
                    flush=True,
                )
    finally:
        stop()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=int, action="append")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    asyncio.run(main(a.task or [1, 2, 3, 4, 5], a.repeats, a.out))
