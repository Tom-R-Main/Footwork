"""A value carried from one surface to another, with where it came from (package G).

A handoff is where identity and authority get lost: a price read in the browser and typed into a
document arrives as bare text, and nothing afterwards can say where it came from or whether what was
saved is what was read. A :class:`Carry` is the value plus its provenance, taken by ``footwork read``
from the session's current observation and stored in that session's ``carries.json``. ``do append``
and ``do type`` accept ``@NAME`` (from this session or ``--from`` another), and ``footwork check-file``
is the exact saved-file oracle: a line of the file must equal the carried text byte for byte.

A secret is never carried: a password field or a value holding a scrubbed secret is refused.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CARRIES = "carries.json"
_REF = re.compile(r"^@([A-Za-z_][A-Za-z0-9_]*)$")


class CarryError(Exception):
    pass


@dataclass(frozen=True)
class Carry:
    name: str
    text: str
    #: "browser" or "native"
    surface: str
    app: str
    #: the page URL (browser) or the window's document or title (native)
    location: str
    title: str
    element_id: int
    element_label: str
    element_role: str
    #: "value" (a field's value) or "label" (the element's own text)
    part: str
    step: int
    session: str
    taken_at: float

    def provenance(self) -> str:
        return (
            f"@{self.name} = {self.text!r}, read from {self.surface} {self.app} at {self.location or self.title} "
            f"({self.element_role} {self.element_label!r}, its {self.part}) at step {self.step} of session {self.session}"
        )


def is_ref(text: str | None) -> str | None:
    """``NAME`` when ``text`` is exactly ``@NAME``."""
    m = _REF.match((text or "").strip())
    return m.group(1) if m else None


def take(
    name: str,
    candidate: Any,
    *,
    surface: str,
    app: str,
    location: str,
    title: str,
    step: int,
    session: str,
    part: str = "auto",
) -> Carry:
    """A carry from one candidate of the current observation. ``part`` auto takes the value when the
    element holds one, else its label."""
    if not _REF.match(f"@{name}"):
        raise CarryError(f"{name!r} is not a name: letters, digits and _ only")
    if (candidate.input_type or "").lower() == "password" or getattr(
        candidate, "has_value", None
    ) is not None:
        raise CarryError(f"[{candidate.id}] is a secure field; its value is never carried")
    if part == "auto":
        part = "value" if candidate.value else "label"
    text = candidate.value if part == "value" else candidate.label
    if not text:
        raise CarryError(f"[{candidate.id}] {candidate.label!r} has no {part} to carry")
    if "{secret" in text:
        raise CarryError(f"[{candidate.id}] holds a scrubbed secret; it is never carried")
    return Carry(
        name=name,
        text=text,
        surface=surface,
        app=app,
        location=location,
        title=title,
        element_id=candidate.id,
        element_label=candidate.label,
        element_role=candidate.role,
        part=part,
        step=step,
        session=session,
        taken_at=time.time(),
    )


def take_match(
    name: str,
    pattern: str,
    page_text: str,
    *,
    surface: str,
    app: str,
    location: str,
    title: str,
    step: int,
    session: str,
) -> Carry:
    """A carry from the observation's text: the first match of ``pattern`` (its first group when it has
    one). The element fields name the text itself; ``label`` holds the match's surrounding line."""
    if not _REF.match(f"@{name}"):
        raise CarryError(f"{name!r} is not a name: letters, digits and _ only")
    try:
        m = re.search(pattern, page_text)
    except re.error as exc:
        raise CarryError(f"{pattern!r} is not a regular expression: {exc}") from exc
    if m is None:
        raise CarryError(f"{pattern!r} does not occur in the observation's text")
    text = m.group(1) if m.groups() else m.group(0)
    text = text.replace("\u200e", "").strip()
    if not text:
        raise CarryError(f"{pattern!r} matched empty text")
    if "{secret" in text:
        raise CarryError("the match holds a scrubbed secret; it is never carried")
    start = page_text.rfind("\n", 0, m.start()) + 1
    end = page_text.find("\n", m.end())
    context = page_text[start : end if end >= 0 else len(page_text)].strip()[:120]
    return Carry(
        name=name,
        text=text,
        surface=surface,
        app=app,
        location=location,
        title=title,
        element_id=-1,
        element_label=context,
        element_role="text",
        part="match",
        step=step,
        session=session,
        taken_at=time.time(),
    )


def store(session_dir: Path, carry: Carry) -> None:
    path = session_dir / CARRIES
    data = json.loads(path.read_text()) if path.exists() else {}
    data[carry.name] = asdict(carry)
    path.write_text(json.dumps(data, indent=1))


def load(session_dir: Path, name: str) -> Carry:
    path = session_dir / CARRIES
    data = json.loads(path.read_text()) if path.exists() else {}
    if name not in data:
        known = ", ".join(f"@{k}" for k in data) or "none"
        raise CarryError(f"@{name} was not read in session {session_dir} (carried there: {known})")
    return Carry(**data[name])


@dataclass(frozen=True)
class FileCheck:
    ok: bool
    path: str
    line: int | None
    detail: str

    def receipt(self, carry: Carry) -> str:
        if self.ok:
            return f"confirmed: line {self.line} of {self.path} equals {carry.provenance()}"
        return f"failed: {self.detail}; expected {carry.provenance()}"


def check_file(path: Path, carry: Carry) -> FileCheck:
    """The exact oracle: some line of the saved file equals the carried text, byte for byte (only the
    line break is removed). A file that holds the text inside a longer line, or with different
    whitespace, fails and says so."""
    if not path.exists():
        return FileCheck(False, str(path), None, f"{path} does not exist")
    try:
        content = path.read_text()
    except UnicodeDecodeError:
        return FileCheck(False, str(path), None, f"{path} is not plain text")
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if line.rstrip("\r") == carry.text:
            return FileCheck(True, str(path), i, "")
    near = next((i for i, line in enumerate(lines, 1) if carry.text.strip() in line), None)
    if near is not None:
        return FileCheck(
            False,
            str(path),
            near,
            f"line {near} contains the text but is not equal to it: {lines[near - 1][:120]!r}",
        )
    return FileCheck(False, str(path), None, f"no line of {path} holds {carry.text[:80]!r}")


# ---- the workflow oracle: where the value went, what it kept, how many times -------------------

SNAPSHOTS = "destinations.json"


def snapshot(session_dir: Path, path: Path) -> dict[str, Any]:
    """Record a destination file before the work, so the oracle can say what changed."""
    import hashlib

    text = path.read_text() if path.exists() else None
    rec = {
        "path": str(path),
        "exists": text is not None,
        "text": text,
        "sha256": hashlib.sha256(text.encode()).hexdigest() if text is not None else None,
        "taken_at": time.time(),
    }
    store_path = session_dir / SNAPSHOTS
    data = json.loads(store_path.read_text()) if store_path.exists() else {}
    data[str(path)] = rec
    store_path.write_text(json.dumps(data, indent=1))
    return rec


def load_snapshot(session_dir: Path, path: Path) -> dict[str, Any]:
    store_path = session_dir / SNAPSHOTS
    data = json.loads(store_path.read_text()) if store_path.exists() else {}
    if str(path) not in data:
        raise CarryError(
            f"no snapshot of {path} in session {session_dir}: run `footwork snapshot-file` first"
        )
    return data[str(path)]


def check_append(path: Path, carry: Carry, before: dict[str, Any]) -> FileCheck:
    """The exact append oracle: the file is its earlier text, one line break when that text did not end
    with one, and the carried text, once, at the end (a trailing line break allowed). Anything else fails
    and says which: earlier content not preserved, the value duplicated, or the value somewhere else."""
    if not path.exists():
        return FileCheck(False, str(path), None, f"{path} does not exist")
    after = path.read_text()
    was = before.get("text") or ""
    sep = "" if was == "" or was.endswith("\n") else "\n"
    expected = was + sep + carry.text
    if after in (expected, expected + "\n"):
        line = expected.count("\n") + 1
        return FileCheck(True, str(path), line, "")
    if not after.startswith(was):
        at = next(
            (i for i, (a, b) in enumerate(zip(after, was, strict=False)) if a != b), min(len(after), len(was))
        )
        return FileCheck(
            False, str(path), None, f"the earlier content was not preserved (it differs at character {at})"
        )
    added = after[len(was) :]
    lines = [ln.rstrip("\r") for ln in added.split("\n") if ln.strip()]
    n = sum(1 for ln in lines if ln == carry.text)
    if n > 1:
        return FileCheck(False, str(path), None, f"the value was inserted {n} times")
    if n == 0:
        return FileCheck(
            False, str(path), None, f"the added text {added[:80]!r} does not hold the value as a line"
        )
    return FileCheck(False, str(path), None, f"the value is there, but with other text added: {added[:80]!r}")
