"""Effects diff: what visibly changed between two observations.

The arbiter needs to tell a no-op from progress without asking a model. Two
menus (task C1) are compared on url, title, the candidate set keyed by a
stable identity that survives selector-index reallocation, candidate values
(so typing counts as an effect), page text similarity, dialogs and tabs.

``key_fn`` is injectable: the default is a tuple of stable attributes; task R3
swaps in upstream's SHA-256 element hashes computed in Rust.

Controls that share a key are matched in document order when both observations hold the same number
of them; otherwise the count difference is what appeared or disappeared. A control state (checked,
selected, expanded, pressed) is compared only when both observations report it: a state reported on
one side only is counted in ``unknown``, and a step whose only difference is unknown state is
``inconclusive``, neither progress nor a proven no-op.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal
from urllib.parse import urlsplit

from jevdual.menu import Candidate, Menu

KeyFn = Callable[[Candidate], Hashable]

#: Page text similarity at or above this ratio counts as unchanged text.
TEXT_UNCHANGED_RATIO = 0.98

STATE_FIELDS = ("checked", "selected", "expanded", "pressed")
#: transitions named in the summary; the rest are counted
_TRANSITIONS_SHOWN = 3


def default_key(c: Candidate) -> Hashable:
    return (c.role, c.label, c.href, c.input_type, c.section)


@dataclass(frozen=True)
class Effect:
    url_changed: bool
    title_changed: bool
    added: int
    removed: int
    changed: int
    text_ratio: float
    dialog_changed: bool
    tabs_changed: bool
    summary: str
    #: state comparisons that could not be made: a matched control reported the state on one side only
    unknown: int = 0
    #: control state transitions, e.g. ``'Details' expanded False -> True``
    transitions: tuple[str, ...] = ()

    @property
    def visible_change(self) -> bool:
        return bool(
            self.url_changed
            or self.title_changed
            or self.added
            or self.removed
            or self.changed
            or self.dialog_changed
            or self.tabs_changed
            or self.text_ratio < TEXT_UNCHANGED_RATIO
        )

    @property
    def no_effect(self) -> bool:
        """Proven unchanged: every comparison was made and none differed."""
        return not self.visible_change and not self.unknown

    @property
    def inconclusive(self) -> bool:
        """Nothing differed, but some control state was not observed on both sides."""
        return not self.visible_change and bool(self.unknown)

    @property
    def status(self) -> Literal["changed", "unchanged", "inconclusive"]:
        if self.visible_change:
            return "changed"
        return "inconclusive" if self.unknown else "unchanged"


def _path(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    return parts.path + (f"?{parts.query}" if parts.query else "")


def _index(menu: Menu, key_fn: KeyFn) -> dict[Hashable, list[Candidate]]:
    out: dict[Hashable, list[Candidate]] = {}
    for c in menu.candidates:
        out.setdefault(key_fn(c), []).append(c)
    return out


def _compare(before: Candidate, after: Candidate) -> tuple[bool, int, list[str]]:
    """(changed, unknown state comparisons, transitions) for one matched control."""
    changed = before.value != after.value
    unknown = 0
    transitions: list[str] = []
    for name in STATE_FIELDS:
        a, b = getattr(before, name), getattr(after, name)
        if a == b:
            continue
        if a is None or b is None:
            unknown += 1
            continue
        changed = True
        transitions.append(f"{after.label!r} {name} {a} -> {b}")
    return changed, unknown, transitions


def diff(
    prev: Menu | None,
    cur: Menu,
    *,
    prev_dialog: object | None = None,
    cur_dialog: object | None = None,
    key_fn: KeyFn = default_key,
) -> Effect:
    """Compare two observations. ``prev=None`` (first step) is reported as a navigation."""
    if prev is None:
        return Effect(
            True,
            True,
            len(cur.candidates),
            0,
            0,
            0.0,
            cur_dialog is not None,
            False,
            f"first observation of {_path(cur.url)}",
        )

    url_changed = prev.url != cur.url
    title_changed = prev.title != cur.title
    before = _index(prev, key_fn)
    after = _index(cur, key_fn)
    added = sum(max(0, len(cs) - len(before.get(k, ()))) for k, cs in after.items())
    removed = sum(max(0, len(cs) - len(after.get(k, ()))) for k, cs in before.items())
    changed = unknown = 0
    transitions: list[str] = []
    for k, cs in after.items():
        prior = before.get(k)
        if not prior or len(prior) != len(cs):
            continue  # identity unresolved: the count difference is reported as added/removed
        for b, a in zip(prior, cs, strict=True):
            moved, unk, trans = _compare(b, a)
            changed += moved
            unknown += unk
            transitions.extend(trans)
    if prev.page_text == cur.page_text:
        text_ratio = 1.0
    elif not prev.page_text or not cur.page_text:
        text_ratio = 0.0
    else:
        text_ratio = SequenceMatcher(None, prev.page_text, cur.page_text, autojunk=False).quick_ratio()
    dialog_changed = (prev_dialog is None) != (cur_dialog is None) or (
        prev_dialog is not None and prev_dialog != cur_dialog
    )
    tabs_changed = len(prev.tabs) != len(cur.tabs)

    parts: list[str] = []
    if url_changed:
        parts.append(f"navigated {_path(prev.url)} -> {_path(cur.url)}")
    elif title_changed:
        parts.append(f"title changed to {cur.title!r}")
    if added or removed:
        parts.append(f"{added} elements appeared, {removed} disappeared")
    if changed:
        parts.append(f"{changed} element values changed")
    if transitions:
        more = len(transitions) - _TRANSITIONS_SHOWN
        parts.append(", ".join(transitions[:_TRANSITIONS_SHOWN]) + (f" and {more} more" if more > 0 else ""))
    if dialog_changed:
        parts.append("dialog opened" if cur_dialog is not None else "dialog closed")
    if tabs_changed:
        parts.append(f"tabs {len(prev.tabs)} -> {len(cur.tabs)}")
    if not parts and text_ratio < TEXT_UNCHANGED_RATIO:
        parts.append(f"page text changed ({text_ratio:.0%} similar)")
    if parts:
        summary = "; ".join(parts)
    elif unknown:
        summary = f"no visible change; {unknown} control states not observed both before and after"
    else:
        summary = "no visible change"
    return Effect(
        url_changed,
        title_changed,
        added,
        removed,
        changed,
        text_ratio,
        dialog_changed,
        tabs_changed,
        summary,
        unknown=unknown,
        transitions=tuple(transitions),
    )
