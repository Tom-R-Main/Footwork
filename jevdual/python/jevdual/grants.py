"""Grants bound to a resource and an effect (package H; design in docs/plans/grants.md).

A label grant clears a label anywhere, with any arguments, any number of times. A :class:`Grant` clears
one operation on one resource (a URL or a document, and an element on it), with these arguments, while
the element still holds the value it held, for a fixed number of dispatches. :func:`why_not` says which
part of a grant does not match a proposed dispatch, so a pause can name it.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

GRANTS = "grants.json"


def sha(text: str | None) -> str | None:
    return hashlib.sha256(text.encode()).hexdigest() if text is not None else None


@dataclass(frozen=True)
class Proposal:
    """One dispatch as the grant check sees it."""

    op: str
    location: str
    element_role: str | None
    element_label: str | None
    arguments: str | None
    value: str | None
    #: what a target-less action (a menu item, a chord) acts on: the selected elements' labels
    selection: tuple[str, ...] = ()
    #: Q19 R2: which of several look-alikes (same role and label) the element is, "2 of 3"; empty when unique
    element_ref: str = ""


@dataclass
class Grant:
    id: str
    op: str
    location: str
    element_role: str | None
    element_label: str | None
    arguments_sha: str | None
    value_sha: str | None
    uses_left: int
    issued_step: int
    issued_at: float
    selection: tuple[str, ...] = ()
    element_ref: str = ""

    def describe(self) -> str:
        on = f"{self.element_role} {self.element_label!r}" if self.element_label else "the window"
        return f"{self.op} on {on} at {self.location} ({self.uses_left} use{'s' if self.uses_left != 1 else ''} left)"


def issue(p: Proposal, *, uses: int = 1, step: int = 0) -> Grant:
    if uses < 1:
        raise ValueError("a grant clears at least one dispatch")
    return Grant(
        id=uuid.uuid4().hex[:8],
        op=p.op,
        location=p.location,
        element_role=p.element_role,
        element_label=p.element_label,
        arguments_sha=sha(p.arguments),
        value_sha=sha(p.value),
        uses_left=uses,
        issued_step=step,
        issued_at=time.time(),
        selection=tuple(p.selection),
        element_ref=p.element_ref,
    )


def why_not(g: Grant, p: Proposal) -> str | None:
    """None when ``g`` clears ``p``; otherwise the first part that differs, in words."""
    if g.uses_left < 1:
        return "no uses left (it was granted for fewer dispatches)"
    if g.op != p.op:
        return f"it grants {g.op}, not {p.op}"
    if g.location != p.location:
        return f"it grants {g.location}, and this is {p.location}"
    if (g.element_role, g.element_label, g.element_ref) != (p.element_role, p.element_label, p.element_ref):
        if (g.element_role, g.element_label) == (p.element_role, p.element_label):
            return f"it grants the {g.element_label!r} {g.element_role} {g.element_ref}, and this is {p.element_ref}"
        return f"it grants {g.element_role} {g.element_label!r}, and this is {p.element_role} {p.element_label!r}"
    if g.arguments_sha != sha(p.arguments):
        return "the arguments differ from the granted ones"
    if g.value_sha != sha(p.value):
        return "the element's value changed since the grant"
    if tuple(g.selection) != tuple(p.selection):
        return f"it grants the selection {list(g.selection)}, and the selection is {list(p.selection)}"
    return None


def load(session_dir: Path) -> list[Grant]:
    path = session_dir / GRANTS
    return (
        [Grant(**(g | {"selection": tuple(g.get("selection") or ())})) for g in json.loads(path.read_text())]
        if path.exists()
        else []
    )


def save(session_dir: Path, grants: list[Grant]) -> None:
    (session_dir / GRANTS).write_text(json.dumps([asdict(g) for g in grants], indent=1))


def consume(session_dir: Path, p: Proposal) -> tuple[Grant | None, list[str]]:
    """The first open grant that clears ``p``, with one use spent and saved; otherwise None and, per open
    grant, why it did not apply."""
    grants = load(session_dir)
    reasons = []
    for g in grants:
        why = why_not(g, p)
        if why is None:
            g.uses_left -= 1
            save(session_dir, grants)
            return g, []
        reasons.append(f"grant {g.id} ({g.describe()}): {why}")
    return None, reasons


def record(session_dir: Path, g: Grant) -> None:
    grants = load(session_dir)
    grants.append(g)
    save(session_dir, grants)


def as_dict(g: Grant) -> dict[str, Any]:
    return asdict(g)
