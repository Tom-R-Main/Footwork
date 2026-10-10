"""Q19: task loading, start states and oracles for the development tasks (evals/tasks/q19-dev.yaml).

Every oracle reads end state through a path independent of the driver: the driver's reported answer
(read tasks), the fixture server's GET record, a file on disk, a shell command, or Stickies' own store.
"""

from __future__ import annotations

import json
import shlex
import struct
import subprocess
import time
import zlib
from pathlib import Path
from typing import Any

import yaml

from evals.crossapp import Check, one_submission

TASKS = Path(__file__).parent / "tasks" / "q19-dev.yaml"
STICKIES = Path.home() / "Library" / "Containers" / "com.apple.Stickies" / "Data" / "Library" / "Stickies"


def load(path: Path = TASKS) -> dict[str, dict[str, Any]]:
    return {t["id"]: t for t in yaml.safe_load(path.read_text())["tasks"]}


def png(path: Path, width: int, height: int) -> None:
    """A plain grey PNG of the given size, written without any imaging library."""
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    )


class SetupError(RuntimeError):
    """A start state that setup could not establish; the trial must not begin."""


def _osa(*lines: str) -> str:
    args = [a for ln in lines for a in ("-e", ln)]
    return subprocess.run(["osascript", *args], capture_output=True, text=True, check=False).stdout.strip()


def window_names(app: str) -> list[str]:
    out = _osa(f'tell application "System Events" to get name of every window of process "{app}"')
    return [w.strip() for w in out.split(",") if w.strip()]


def sheet_count(app: str) -> int:
    out = _osa(f'tell application "System Events" to get count of sheets of every window of process "{app}"')
    return sum(int(x) for x in out.replace(" ", "").split(",") if x.isdigit())


def calculator_display() -> list[str]:
    """The texts of Calculator's front window (its display; the history too when shown)."""
    from ApplicationServices import AXUIElementCreateApplication
    from jevdual import ax

    pids = subprocess.run(
        ["pgrep", "-x", "Calculator"], capture_output=True, text=True, check=False
    ).stdout.split()
    if not pids:
        return []
    wins = ax._attr(AXUIElementCreateApplication(int(pids[0])), "AXWindows") or []
    return [
        str(ax._attr(e, "AXValue") or ax._attr(e, "AXDescription") or "").replace("\u200e", "").strip()
        for w in wins[:1]
        for e in ax.elements_by_role(w, "AXStaticText")
    ]


def reset_calculator() -> None:
    """Opening Calculator restores its last expression and result (Q19 H09 read the operator's 8×7 = 56):
    clear it with Escape twice and hide the history, so the display holds only 0."""
    subprocess.run(["open", "-a", "Calculator"], check=False)
    time.sleep(1.5)
    _osa(
        'tell application "Calculator" to activate',
        "delay 0.3",
        'tell application "System Events" to key code 53',
        "delay 0.2",
        'tell application "System Events" to key code 53',
    )
    _osa(
        'tell application "System Events" to tell process "Calculator"',
        'if exists menu item "Hide History" of menu "View" of menu bar 1 then click menu item "Hide History" of menu "View" of menu bar 1',
        "end tell",
    )
    time.sleep(0.5)


def start_problems(task: dict[str, Any], *, probe: Any = None) -> list[str]:
    """What is wrong with the start state setup was meant to establish: an intended document not open,
    another document of the same app open (a previous trial's), a sheet left open, a Calculator display
    that is not a cleared 0. ``probe`` supplies the readers (tests pass fakes)."""
    p = probe or __import__(__name__, fromlist=["window_names"])
    wanted: dict[str, set[str]] = {}
    apps: set[str] = set()
    for step in task.get("setup") or []:
        words = shlex.split(step)
        if words[0] == "open_in":
            wanted.setdefault(words[1], set()).add(words[2])
            apps.add(words[1])
        elif words[0] == "open_app":
            apps.add(words[1])
    out = []
    for app, files in wanted.items():
        names = set(p.window_names(app))
        out += [f"{app}: {f} is not open" for f in sorted(files - names)]
        out += [f"{app}: {n} is open from outside this trial" for n in sorted(names - files)]
    for app in sorted(apps):
        if p.sheet_count(app):
            out.append(f"{app}: a sheet is open")
    if "Calculator" in apps:
        shown = p.calculator_display()
        if shown != ["0"]:
            out.append(f"Calculator: the display shows {shown!r}, not a cleared 0")
    return out


def setup(task: dict[str, Any], scratch: Path) -> None:
    """Make the task's start state, then check it (``SetupError`` when it does not hold)."""
    scratch.mkdir(parents=True, exist_ok=True)
    for step in task.get("setup") or []:
        words = shlex.split(step)
        op, args = words[0], words[1:]
        if op == "write":
            (scratch / args[0]).write_text(args[1].encode().decode("unicode_escape"))
        elif op == "make_png":
            png(scratch / args[0], int(args[1]), int(args[2]))
        elif op == "mkdir":
            (scratch / args[0]).mkdir(exist_ok=True)
        elif op == "open_app":
            if args[0] == "Calculator":
                reset_calculator()
            else:
                subprocess.run(["open", "-a", args[0]], check=False)
        elif op == "open_in":
            subprocess.run(["open", "-a", args[0], str(scratch / args[1])], check=False)
        elif op == "open_folder":
            subprocess.run(["open", str(scratch)], check=False)
        else:
            raise ValueError(f"unknown setup step {step!r}")
        time.sleep(1.5)
    bad = start_problems(task)
    if bad:
        raise SetupError("start state not established: " + "; ".join(bad))


def check(
    task: dict[str, Any], *, answer: str | None, gets: dict[str, list[dict[str, str]]], scratch: Path
) -> Check:
    o = task["oracle"]
    kind = o["kind"]
    if kind == "all":
        # Heldout authoring: the intended write and preservation of the other scratch files
        # must both hold. No change to any existing oracle's meaning.
        children = o.get("checks") or []
        if not children:
            raise ValueError("an all oracle needs at least one check")
        checks = [check({"oracle": child}, answer=answer, gets=gets, scratch=scratch) for child in children]
        return Check(all(c.ok for c in checks), "; ".join(c.detail for c in checks))
    if kind == "answer_contains":
        ok = o["value"].casefold() in (answer or "").casefold()
        return Check(ok, f"answer {'contains' if ok else 'lacks'} {o['value']!r}")
    if kind == "answer_contains_all":
        missing = [v for v in o["values"] if v not in (answer or "")]
        return Check(not missing, "answer has every value" if not missing else f"answer lacks {missing}")
    if kind == "answer_equals_command":
        truth = subprocess.run(
            o["command"], shell=True, capture_output=True, text=True, check=False
        ).stdout.strip()
        ok = bool(truth) and truth.casefold() in (answer or "").casefold()
        return Check(ok, f"answer {'contains' if ok else 'lacks'} {truth!r} (from `{o['command']}`)")
    if kind == "submission":
        reqs = gets.get(o["path"], [])
        if not reqs:
            return Check(False, f"nothing was submitted to {o['path']}")
        if len(reqs) > 1:
            return Check(False, f"{len(reqs)} submissions to {o['path']}, not one")
        wrong = {k: reqs[0].get(k) for k, v in o["fields"].items() if reqs[0].get(k) != v}
        return Check(
            not wrong,
            f"one submission to {o['path']} with {reqs[0]}" if not wrong else f"fields differ: {wrong}",
        )
    if kind == "file_equals":
        p = scratch / o["path"]
        if not p.exists():
            return Check(False, f"{p.name} does not exist")
        got = p.read_text()
        ok = got.rstrip("\n") == o["value"].rstrip("\n")
        return Check(
            ok,
            f"{p.name} {'equals' if ok else 'differs from'} the expected text"
            + ("" if ok else f": {got[:80]!r}"),
        )
    if kind == "appended":
        p = scratch / o["path"]
        got = p.read_text() if p.exists() else ""
        lines = [ln for ln in got.split("\n") if ln.strip()]
        n = got.count(o["value"])
        ok = bool(lines) and lines[-1] == o["value"] and n == 1
        last = lines[-1] if lines else None
        return Check(ok, f"last line {last!r}; the value appears {n} time(s)")
    if kind == "moved":
        src, dst = scratch / o["from"], scratch / o["to"]
        ok = dst.exists() and not src.exists()
        return Check(
            ok,
            f"{o['to']} {'exists' if dst.exists() else 'missing'}, {o['from']} {'gone' if not src.exists() else 'still there'}",
        )
    if kind == "stickies_contains":
        hits = [p for p in STICKIES.glob("*.rtfd/TXT.rtf") if o["value"] in p.read_text(errors="ignore")]
        return Check(bool(hits), f"{len(hits)} sticky note(s) contain {o['value']!r}")
    raise ValueError(f"unknown oracle kind {kind!r}")


def file_hashes(scratch: Path) -> dict[str, str]:
    """sha256 of every file under a task's scratch folder, read with the oracle (the held-back protocol)."""
    import hashlib

    return {
        str(p.relative_to(scratch)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(scratch.rglob("*"))
        if p.is_file()
    }


def submission_view(gets: dict[str, list[dict[str, str]]]) -> str:
    return json.dumps(gets)


__all__ = ["Check", "check", "load", "one_submission", "png", "setup"]
