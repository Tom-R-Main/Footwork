"""Effects diff: what visibly changed between two observations.

The arbiter needs to tell a no-op from progress without asking a model. Two
menus (task C1) are compared on url, title, the candidate set keyed by a
stable identity that survives selector-index reallocation, candidate values
(so typing counts as an effect), page text similarity, dialogs and tabs.

``key_fn`` is injectable: the default is a tuple of stable attributes; task R3
swaps in upstream's SHA-256 element hashes computed in Rust.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from jevdual.menu import Candidate, Menu

KeyFn = Callable[[Candidate], Hashable]

#: Page text similarity at or above this ratio counts as unchanged text.
TEXT_UNCHANGED_RATIO = 0.98


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

    @property
    def no_effect(self) -> bool:
        return not (
            self.url_changed
            or self.title_changed
            or self.added
            or self.removed
            or self.changed
            or self.dialog_changed
            or self.tabs_changed
            or self.text_ratio < TEXT_UNCHANGED_RATIO
        )


def _path(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    return parts.path + (f"?{parts.query}" if parts.query else "")


def _index(menu: Menu, key_fn: KeyFn) -> dict[Hashable, Candidate]:
    out: dict[Hashable, Candidate] = {}
    for c in menu.candidates:
        out.setdefault(key_fn(c), c)
    return out


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
    added = sum(1 for k in after if k not in before)
    removed = sum(1 for k in before if k not in after)
    changed = sum(
        1
        for k, c in after.items()
        if k in before
        and (
            before[k].value != c.value
            or before[k].checked != c.checked
            or before[k].selected != c.selected
            or before[k].expanded != c.expanded
        )
    )
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
    if dialog_changed:
        parts.append("dialog opened" if cur_dialog is not None else "dialog closed")
    if tabs_changed:
        parts.append(f"tabs {len(prev.tabs)} -> {len(cur.tabs)}")
    if not parts and text_ratio < TEXT_UNCHANGED_RATIO:
        parts.append(f"page text changed ({text_ratio:.0%} similar)")
    summary = "; ".join(parts) if parts else "no visible change"
    return Effect(
        url_changed, title_changed, added, removed, changed, text_ratio, dialog_changed, tabs_changed, summary
    )
