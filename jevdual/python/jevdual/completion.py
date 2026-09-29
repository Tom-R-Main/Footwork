"""Evidence for the requested effect, built from a session's own records (M1).

A receipt's ``confirmed`` means the harness saw a change; it does not say the requested effect happened
(a title or a dialog changing confirms too). Some receipts do carry evidence for a specific effect, and
this module lifts exactly those into typed records the done decision can use:

* ``saved``: a save readback read the bound document's file equal to the window's text (current state
  at that time);
* ``submitted``: a click navigated to a result whose URL carries the submitted fields (an event; a POST
  form leaves no such evidence, and a generic confirmation page is not evidence of which request);
* ``field_holds``: a typed or appended field read back holding its value (current state at that time);
* ``read``: a value the harness carried out of an observation, with its source (answer provenance).

Each record keeps its limits. A duplicated submission, a save followed by another edit, a readback of a
document other than the bound one: such a record is shown to the verifier with the limit and never counts
as support for a claimed value.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

KINDS = ("current_state", "event", "answer")
_NAVIGATED = re.compile(r"navigated to (\S+?)[;)]?(?:\s|$)")
_HOLDS = re.compile(r"'(?P<label>[^']+)' now holds '(?P<value>(?:[^'\\]|\\.)*)'")
_EDITS = ("type", "append", "enter", "key", "paste")


@dataclass(frozen=True)
class Effect:
    effect: str  # saved | submitted | field_holds | read
    resource: str
    kind: str  # current_state | event | answer
    step: int
    t: float
    detail: str
    values: tuple[str, ...] = ()
    limits: tuple[str, ...] = field(default_factory=tuple)

    @property
    def usable(self) -> bool:
        return not self.limits

    def line(self) -> str:
        lim = f" [LIMITED: {'; '.join(self.limits)}]" if self.limits else ""
        return f"step {self.step} {self.effect} ({self.kind}) {self.resource}: {self.detail}{lim}"


def _records(session: Path) -> list[dict[str, Any]]:
    p = session / "session.jsonl"
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.exists() else []


def effects(
    records: list[dict[str, Any]], *, document: str = "", carries: dict[str, Any] | None = None
) -> list[Effect]:
    """The effect evidence in one session's records. ``document`` is the bound window's document name
    (a readback of any other file is limited); ``carries`` is the session's carries.json."""
    out: list[Effect] = []
    receipts = [r for r in records if r.get("kind") == "receipt"]
    for r in receipts:
        a = r.get("action") or {}
        op, step, t = a.get("op"), int(r.get("step") or 0), float(r.get("t") or 0.0)
        if r.get("effect") != "confirmed":
            continue
        rb = a.get("save_readback")
        if rb and rb.get("ok"):
            path = str(rb.get("path") or "")
            limits = []
            if document and Path(path).name != document:
                limits.append(f"the readback names {Path(path).name}, not the bound document {document}")
            later = [
                x
                for x in receipts
                if float(x.get("t") or 0) > t
                and (x.get("action") or {}).get("op") in _EDITS
                and x.get("effect") in ("confirmed", "partial", "unverifiable")
            ]
            if later:
                limits.append(f"edited again after this save (step {later[0].get('step')})")
            out.append(
                Effect(
                    "saved", path, "current_state", step, t, str(rb.get("detail") or ""), (), tuple(limits)
                )
            )
            continue
        ev = str(r.get("evidence") or "")
        m = _NAVIGATED.search(ev)
        if op == "click" and m and "?" in m.group(1):
            u = urlsplit(m.group(1))
            fields = tuple(v for _, v in parse_qsl(u.query) if v)
            out.append(Effect("submitted", u.path, "event", step, t, f"submitted {u.query}", fields))
            continue
        h = _HOLDS.search(ev)
        if op in ("type", "append") and h:
            value = h.group("value").encode().decode("unicode_escape")
            # M2: once the page navigated away, the field it held is gone; its readback says nothing now
            moved = [
                x for x in receipts if float(x.get("t") or 0) > t and "navigated to" in str(x.get("evidence"))
            ]
            limits = (f"the page navigated away at step {moved[0].get('step')}",) if moved else ()
            out.append(
                Effect(
                    "field_holds",
                    h.group("label"),
                    "current_state",
                    step,
                    t,
                    f"holds {value!r}",
                    (value,),
                    limits,
                )
            )
    # a submission repeated to the same result is a duplicated effect, whatever its fields
    by_path: dict[str, int] = {}
    for e in out:
        if e.effect == "submitted":
            by_path[e.resource] = by_path.get(e.resource, 0) + 1
    out = [
        Effect(
            e.effect,
            e.resource,
            e.kind,
            e.step,
            e.t,
            e.detail,
            e.values,
            (*e.limits, f"{by_path[e.resource]} submissions to {e.resource}"),
        )
        if e.effect == "submitted" and by_path[e.resource] > 1
        else e
        for e in out
    ]
    for name, c in (carries or {}).items():
        v = str(c.get("text") or "")
        if v:
            where = c.get("location") or c.get("url") or "an observation"
            out.append(
                Effect(
                    "read",
                    f"@{name} from {where}",
                    "answer",
                    int(c.get("step") or 0),
                    float(c.get("taken_at") or 0.0),
                    f"carried {v!r} ({c.get('occurrence') or 'its match'})",
                    (v,),
                )
            )
    return out


def session_effects(session: Path, *, document: str = "") -> list[Effect]:
    cp = session / "carries.json"
    carries = json.loads(cp.read_text()) if cp.exists() else {}
    return effects(_records(session), document=document, carries=carries)


def evidence_values(items: list[Effect]) -> tuple[str, ...]:
    """Values the usable evidence establishes, for the claim check (limited records establish none)."""
    seen: list[str] = []
    for e in items:
        if e.usable:
            seen += [v for v in e.values if v and v not in seen]
    return tuple(seen)


#: M2: the effect a task names, and the evidence that effect needs
_NAMED = (
    ("saved", re.compile(r"\bsav(?:e|es|ed|ing)\b", re.IGNORECASE)),
    (
        "submitted",
        re.compile(r"\b(?:submit|send|delete|cancel|request|order|book|reserve)\w*", re.IGNORECASE),
    ),
)


def required_effects(task: str) -> tuple[str, ...]:
    return tuple(kind for kind, rx in _NAMED if rx.search(task))


def floor(task: str, items: list[Effect] | tuple[Effect, ...], *, answer_bearing: bool) -> str | None:
    """Why a done cannot be accepted on this run's evidence, or None (M2). A duplicated event always
    blocks; a done that is not answer-bearing needs usable evidence for the effect the task names (or,
    naming none, any usable current-state or event record). The page saying "recorded" is not enough."""
    dup = [e for e in items if e.kind == "event" and any("submissions to" in lim for lim in e.limits)]
    if dup:
        return f"the effect happened more than once ({dup[0].limits[-1]})"
    if answer_bearing:
        return None
    usable = [e for e in items if e.usable and e.kind in ("current_state", "event")]
    need = required_effects(task)
    missing = [k for k in need if not any(e.effect == k for e in usable)]
    if missing:
        return "no evidence in this run for: " + ", ".join(missing)
    if not need and not usable:
        return "no evidence in this run for the requested effect (only what the page says)"
    return None


def repeat_of(records: list[dict[str, Any]], op: str, *, url: str = "", label: str = "") -> str | None:
    """Why an action would repeat a submission these records already hold, or None: loading the
    submission's result address again (a GET form submits on load), or clicking the control that made
    it. U52: in the loop as frozen for Q19, a model whose done was refused loaded the sign-up's result
    address, submitting a second time, and its next done was accepted."""
    from urllib.parse import urlsplit

    for e in effects(records):
        if e.effect != "submitted":
            continue
        query = e.detail.removeprefix("submitted ")
        if op == "navigate" and url:
            u = urlsplit(url)
            if u.path == e.resource and u.query and u.query == query:
                return f"loading {u.path}?{u.query} would submit again (repeating the submission recorded at step {e.step})"
        if op == "click" and label:
            made = [
                r
                for r in records
                if r.get("kind") == "receipt"
                and float(r.get("t") or 0) == e.t
                and (r.get("action") or {}).get("target_label") == label
            ]
            if made:
                return f"'{label}' already submitted at step {e.step} ({query}); pressing it again would submit again"
    return None
