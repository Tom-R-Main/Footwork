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


def setup(task: dict[str, Any], scratch: Path) -> None:
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
            subprocess.run(["open", "-a", args[0]], check=False)
        elif op == "open_in":
            subprocess.run(["open", "-a", args[0], str(scratch / args[1])], check=False)
        elif op == "open_folder":
            subprocess.run(["open", str(scratch)], check=False)
        else:
            raise ValueError(f"unknown setup step {step!r}")
        time.sleep(1.5)


def check(
    task: dict[str, Any], *, answer: str | None, gets: dict[str, list[dict[str, str]]], scratch: Path
) -> Check:
    o = task["oracle"]
    kind = o["kind"]
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


def submission_view(gets: dict[str, list[dict[str, str]]]) -> str:
    return json.dumps(gets)


__all__ = ["Check", "check", "load", "one_submission", "png", "setup"]
