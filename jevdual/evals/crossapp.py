"""Q13's oracles: each reads the end state a cross-surface task leaves, never the agent's account of it.

One per task shape (docs/experiments/Q13 pre-registration names the tasks); the first, a value appended
to a saved document, is ``jevdual.carry.check_append``. Each returns a :class:`Check` whose ``detail``
names the first thing that is wrong.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    ok: bool
    detail: str


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def one_submission(gets: dict[str, list[dict[str, str]]], path: str, field: str, value: str) -> Check:
    """Exactly one request to ``path`` carrying ``field`` exactly equal to ``value``, and no other request
    to ``path`` (a retry that submitted twice is a failure, as is a near value)."""
    reqs = gets.get(path, [])
    if not reqs:
        return Check(False, f"nothing was submitted to {path}")
    if len(reqs) > 1:
        return Check(False, f"{len(reqs)} submissions to {path}, not one")
    got = reqs[0].get(field)
    if got is None:
        return Check(False, f"the submission to {path} has no {field!r}")
    if got != value:
        return Check(False, f"{field!r} was {got!r}, not {value!r}")
    return Check(True, f"one submission to {path} with {field}={value!r}")


def downloaded_and_opened(downloads: Path, served: bytes, name: str, opened_path: str | None) -> Check:
    """Exactly one file in ``downloads`` byte-identical to what the server sent (Chrome may add " (1)"),
    and the document the app has open is that file."""
    digest = sha256(served)
    stem, suffix = Path(name).stem, Path(name).suffix
    candidates = [p for p in downloads.glob(f"{stem}*{suffix}") if p.is_file()]
    same = [p for p in candidates if sha256(p.read_bytes()) == digest]
    if not same:
        return Check(False, f"no file in {downloads} matches the served {name}")
    if len(same) > 1:
        return Check(False, f"{len(same)} identical copies downloaded: {', '.join(p.name for p in same)}")
    if opened_path is None:
        return Check(False, f"{same[0].name} was downloaded but no document is open")
    if Path(opened_path).resolve() != same[0].resolve():
        return Check(False, f"the open document is {opened_path}, not the downloaded {same[0]}")
    return Check(True, f"{same[0]} is the served file byte for byte and is the open document")


def renamed(folder: Path, old: str, new: str, original_sha: str) -> Check:
    """The file now has exactly the carried name, its bytes are unchanged, and the old name is gone."""
    if (folder / old).exists():
        return Check(False, f"{old} still exists")
    target = folder / new
    if not target.is_file():
        near = [p.name for p in folder.iterdir() if p.is_file()]
        return Check(False, f"no file named {new!r} (the folder has {near[:5]})")
    if sha256(target.read_bytes()) != original_sha:
        return Check(False, f"{new} exists but its contents changed")
    return Check(True, f"{old} is now {new}, contents unchanged")
