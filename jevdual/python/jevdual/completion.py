"""Evidence for the requested effect, built from a session's own records (M1).

A receipt's ``confirmed`` means the harness saw a change; it does not say the requested effect happened
(a title or a dialog changing confirms too). Some receipts do carry evidence for a specific effect, and
this module lifts exactly those into typed records the done decision can use:

* ``saved``: a save readback read the bound document's file equal to the window's text (current state
  at that time);
* ``field_holds``: a typed or appended field read back holding its value (current state at that time);
* ``read``: a value the harness carried out of an observation, with its source (answer provenance).

Query navigation establishes neither a submission nor its values. The current receipt producer has
no qualified submission acknowledgement, so this module emits no ``submitted`` events. The floor can
check such events when a qualified producer exists; labels and result URLs cannot supply that proof.

Each record keeps its limits. A duplicated submission, a save followed by another edit, a readback of a
document other than the bound one: such a record is shown to the verifier with the limit and never counts
as support for a claimed value.
"""

from __future__ import annotations

import ast
import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

KINDS = ("current_state", "event", "answer")
_NAVIGATED = re.compile(r"navigated to (\S+?)[;)]?(?:\s|$)")
_STRING = r"'(?:[^'\\\r\n]|\\.)*'|\"(?:[^\"\\\r\n]|\\.)*\""
_HOLDS = re.compile(rf"(?P<label>{_STRING}) now holds (?P<value>{_STRING})")
_READ_ONLY = ("observe", "read", "look", "status", "inspect")
_NOT_SENT = ("not sent", "not dispatched", "refused")
_MAX_RECEIPT_LITERAL = 16_384


def _literal(text: str) -> str | None:
    """Decode only a bounded, quoted string produced by repr; never execute receipt text."""
    if len(text) > _MAX_RECEIPT_LITERAL or re.fullmatch(_STRING, text) is None:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            value = ast.literal_eval(text)
    except (SyntaxError, SyntaxWarning, ValueError):
        return None
    return value if isinstance(value, str) and repr(value) == text else None


def _same_surface(record: dict[str, Any], earlier: dict[str, Any]) -> bool:
    action, before = record.get("action") or {}, earlier.get("action") or {}
    return not any(
        action.get(scope) and before.get(scope) and action[scope] != before[scope]
        for scope in ("app", "mode")
    )


def _possible_edit(record: dict[str, Any], earlier: dict[str, Any]) -> bool:
    """Whether later input may supersede current-state evidence on the same source.

    Experimental receipt metadata has app/mode scope but no qualified stable field incarnation.
    Presentation labels and snapshot IDs can both remap, so they cannot prove distinct fields.
    Any input route can mutate that source; a route name is not proof that a value stayed unchanged.
    Preserve only read-only operations, explicit non-delivery or a known different source; unknown
    input/scope overlaps. A later qualified readback supplies its own new current-state effect.
    """
    action = record.get("action") or {}
    # New producers record dispatch explicitly. An uncertain/attempted input can
    # supersede prior state even when legacy prose or the diff says "refused".
    if "dispatched" in action or "dispatched" in record:
        dispatched = action.get("dispatched") if "dispatched" in action else record["dispatched"]
        return (
            action.get("op") not in _READ_ONLY and dispatched is not False and _same_surface(record, earlier)
        )
    if (
        action.get("op") in _READ_ONLY
        or record.get("effect") not in ("confirmed", "partial", "unverifiable", "suspected_noop")
        or action.get("driver_effect") in _NOT_SENT
        or action.get("dispatched") is False
        or record.get("dispatched") is False
    ):
        return False
    return _same_surface(record, earlier)


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
    (a readback of any other file is limited); ``carries`` is the session's carries.json.
    Current-state freshness follows receipt order, with conservative source scope because labels
    and snapshot IDs do not establish stable field/document incarnation identity.
    """
    out: list[Effect] = []
    receipts = [r for r in records if r.get("kind") == "receipt"]
    for index, r in enumerate(receipts):
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
            later = next((x for x in receipts[index + 1 :] if _possible_edit(x, r)), None)
            if later is not None:
                limits.append(f"possible edit after this save (step {later.get('step')})")
            out.append(
                Effect(
                    "saved", path, "current_state", step, t, str(rb.get("detail") or ""), (), tuple(limits)
                )
            )
            continue
        ev = str(r.get("evidence") or "")
        h = _HOLDS.fullmatch(ev) if len(ev) <= _MAX_RECEIPT_LITERAL else None
        if op in ("type", "append") and h:
            label, value = _literal(h.group("label")), _literal(h.group("value"))
            if not label or value is None:
                continue
            # M2: once the page navigated away, the field it held is gone; its readback says nothing now
            moved = [
                x
                for x in receipts[index + 1 :]
                if _NAVIGATED.match(str(x.get("evidence") or "")) and _same_surface(x, r)
            ]
            limits = [f"the page navigated away at step {moved[0].get('step')}"] if moved else []
            edited = next((x for x in receipts[index + 1 :] if _possible_edit(x, r)), None)
            if edited is not None:
                limits.append(f"a later input may have changed the field (step {edited.get('step')})")
            out.append(
                Effect(
                    "field_holds",
                    label,
                    "current_state",
                    step,
                    t,
                    f"holds {value!r}",
                    (value,),
                    tuple(limits),
                )
            )
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
    """Conservative repeat risk from observed query navigation, without submission evidence.

    A repeated query URL can repeat a GET form's effect. This guard preserves that pause but does not
    establish whether an earlier submission happened. Absolute URLs keep origin identity; legacy
    relative receipt URLs have unknown origin and conservatively match the same path and query.
    """
    for record in records:
        action = record.get("action") or {}
        if (
            record.get("kind") != "receipt"
            or record.get("effect") != "confirmed"
            or action.get("op") != "click"
            or action.get("driver_effect") in _NOT_SENT
            or action.get("dispatched") is False
            or record.get("dispatched") is False
        ):
            continue
        navigation = _NAVIGATED.match(str(record.get("evidence") or ""))
        if not navigation:
            continue
        prior = urlsplit(navigation.group(1))
        if not prior.query:
            continue
        step = record.get("step")
        if op == "navigate" and url:
            u = urlsplit(url)
            if prior.netloc and (u.scheme.casefold(), u.netloc.casefold()) != (
                prior.scheme.casefold(),
                prior.netloc.casefold(),
            ):
                continue
            if u.path == prior.path and u.query == prior.query:
                return (
                    f"repeating the query navigation recorded at step {step}; "
                    f"loading {u.path}?{u.query} may submit again or repeat an effect"
                )
        if op == "click" and label and action.get("target_label") == label:
            return (
                f"{label!r} caused query navigation at step {step}; "
                "pressing it again may submit again or repeat an effect"
            )
    return None
