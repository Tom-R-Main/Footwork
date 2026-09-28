"""Q13's oracle stage (notebook G8): each oracle must confirm a correct scripted solve and name the fault
in a wrong one, on the real apps, before Q13 is pre-registered.

Reads go through footwork sessions (carried values with their source); effects go through footwork where
it has a route (type, click, navigate) and by script where it has none (opening a file in TextEdit, a
Finder rename). The fixture server runs in this process, so the oracles read its request record directly.
Acts on the desktop: footwork's Chrome, Calculator, TextEdit. Evidence: results/q13-oracle-stage-<time>/.

    uv run python scripts/q13_oracle_stage.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.crossapp import Check, downloaded_and_opened, one_submission, renamed, sha256
from evals.fixtures.server import SITE, serve

STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT = Path(f"results/q13-oracle-stage-{STAMP}")
SCRATCH = Path.home() / "footwork-pilot" / f"q13-{STAMP}"
DOWNLOADS = Path.home() / "Downloads"
LOG = OUT / "stage.log"
results: list[dict] = []


def fw(session: str, *argv: str, check: bool = True) -> str:
    cmd = ["uv", "run", "footwork", *argv, "--session", str(OUT / session)]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    with LOG.open("a") as fh:
        fh.write(f"$ footwork {' '.join(argv)} [{session}] -> {p.returncode}\n{p.stdout}{p.stderr}\n")
    if check and p.returncode not in (0,):
        raise RuntimeError(
            f"footwork {' '.join(argv)} exited {p.returncode}: {(p.stderr or p.stdout)[-300:]}"
        )
    return p.stdout


def element_id(session: str, label: str) -> str:
    out = fw(session, "look")
    for line in out.splitlines():
        m = re.match(r"\s*\[\s*(\d+)\]\s+\S+\s+'(.*)'", line)
        if m and m.group(2) == label:
            return m.group(1)
    raise RuntimeError(f"no element labelled {label!r} in {session}")


def record(task: str, solve: str, check: Check, expect_ok: bool) -> None:
    passed = check.ok == expect_ok
    results.append(
        {"task": task, "solve": solve, "oracle_ok": check.ok, "detail": check.detail, "as_expected": passed}
    )
    print(
        f"{task} [{solve}]: oracle {'confirmed' if check.ok else 'failed'}: {check.detail}  -> {'as expected' if passed else 'NOT AS EXPECTED'}"
    )


def osa(script: str) -> str:
    return subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, check=False
    ).stdout.strip()


def task2_calculator_to_form(base: str, gets) -> None:
    fw("calc", "start", "Compute 48 times 13", "--app", "Calculator", "--mode", "foreground_permitted")
    fw("calc", "do", "click", "All Clear", "--no-judge")
    for label in ("4", "8", "Multiply", "1", "3", "Equals"):
        target = element_id("calc", label) if label.isdigit() else label
        fw("calc", "do", "click", target, "--no-judge")
    fw("calc", "read", "--match", r"(?m)^\s*‎?(\d[\d,]*)\s*$", "--as", "result")
    carried = json.loads((OUT / "calc" / "carries.json").read_text())["result"]["text"]
    fw("form", "start", "Send the result through the form", "--browser", "--url", f"{base}/form.html")

    def submit() -> None:
        fw("form", "do", "type", "Name", "Ada")
        fw("form", "do", "type", "Email", "ada@example.com")
        fw("form", "do", "type", "Message", "@result", "--from", str(OUT / "calc"))
        fw("form", "do", "click", "Send message", "--no-judge")
        time.sleep(1)

    submit()
    record("2 calculator->form", "correct", one_submission(gets(), "/confirm.html", "message", carried), True)
    fw("form", "do", "navigate", f"{base}/form.html")
    submit()  # the wrong solve: the same submission again
    record(
        "2 calculator->form", "duplicate", one_submission(gets(), "/confirm.html", "message", carried), False
    )


def task3_textedit_to_search(base: str, gets) -> None:
    doc = SCRATCH / "notes.txt"
    doc.write_text("Next search: quarterly report\n")
    subprocess.run(["open", "-a", "TextEdit", str(doc)], check=False)
    time.sleep(3)
    fw("notes", "start", "Read the next search", "--app", "TextEdit", "--window", "notes.txt")
    fw("notes", "read", "--match", r"Next search: (.+)", "--as", "query")
    carried = json.loads((OUT / "notes" / "carries.json").read_text())["query"]["text"]
    fw("search", "start", "Search for the carried query", "--browser", "--url", f"{base}/search.html")
    fw("search", "do", "type", "q", "@query", "--from", str(OUT / "notes"))
    fw("search", "do", "click", "Search", "--no-judge")
    time.sleep(1)
    record("3 textedit->search", "correct", one_submission(gets(), "/search.html", "q", carried), True)
    fw("search", "do", "click", "Search", "--no-judge")  # the wrong solve: searched twice
    time.sleep(1)
    record("3 textedit->search", "duplicate", one_submission(gets(), "/search.html", "q", carried), False)
    osa('tell application "TextEdit" to close (every document whose name is "notes.txt") saving no')


def task4_download_and_open(base: str) -> None:
    name = "quarterly-report.txt"
    served = (SITE / name).read_bytes()
    for old in DOWNLOADS.glob("quarterly-report*.txt"):
        old.unlink()  # earlier runs' copies of this fixture only
    fw("dl", "start", "Download the quarterly report", "--browser", "--url", f"{base}/index.html")
    fw("dl", "do", "navigate", f"{base}/{name}", check=False)
    for _ in range(20):
        if (DOWNLOADS / name).exists():
            break
        time.sleep(0.5)
    subprocess.run(["open", "-a", "TextEdit", str(DOWNLOADS / name)], check=False)
    time.sleep(3)
    opened = osa('tell application "TextEdit" to get path of front document') or None
    record("4 download->open", "correct", downloaded_and_opened(DOWNLOADS, served, name, opened), True)
    fw("dl", "do", "navigate", f"{base}/{name}", check=False)  # the wrong solve: downloaded again
    time.sleep(3)
    record("4 download->open", "duplicate", downloaded_and_opened(DOWNLOADS, served, name, opened), False)
    osa(f'tell application "TextEdit" to close (every document whose name is "{name}") saving no')


def task5_order_to_rename(base: str) -> None:
    fw("order", "start", "Read the order reference", "--browser", "--url", f"{base}/order-confirmed.html")
    fw("order", "read", "--match", r"(B-\d+)", "--as", "ref")
    ref = json.loads((OUT / "order" / "carries.json").read_text())["ref"]["text"]
    for solve, new, expect in (("correct", f"{ref}.txt", True), ("truncated", f"{ref[:-1]}.txt", False)):
        folder = SCRATCH / f"rename-{solve}"
        folder.mkdir()
        (folder / "draft.txt").write_text("order notes\n")
        digest = sha256(b"order notes\n")
        (folder / "draft.txt").rename(folder / new)  # Finder rename is unreachable through footwork (plan)
        record("5 order->rename", solve, renamed(folder, "draft.txt", f"{ref}.txt", digest), expect)


def main() -> int:
    OUT.mkdir(parents=True)
    SCRATCH.mkdir(parents=True)
    base, stop = serve(0)
    gets = stop.recorder.gets
    try:
        for fn, args in (
            (task2_calculator_to_form, (base, gets)),
            (task3_textedit_to_search, (base, gets)),
            (task4_download_and_open, (base,)),
            (task5_order_to_rename, (base,)),
        ):
            try:
                fn(*args)
            except Exception as exc:  # noqa: BLE001 - a task that cannot be solved is recorded, not a crash
                results.append({"task": fn.__name__, "error": f"{type(exc).__name__}: {exc}"[:300]})
                print(f"{fn.__name__}: stopped: {exc}")
    finally:
        stop()
        (OUT / "gets.json").write_text(json.dumps(stop.recorder.gets(), indent=1))
        (OUT / "results.json").write_text(json.dumps(results, indent=1))
        for d in OUT.glob("*/screenshots"):
            shutil.rmtree(d, ignore_errors=True)
    ok = sum(1 for r in results if r.get("as_expected"))
    print(f"{ok} of {len(results)} checks as expected; evidence in {OUT}")
    return 0 if ok == len(results) == 8 else 6


if __name__ == "__main__":
    sys.exit(main())
