"""One authorization boundary for every native dispatch route.

The secondary audit (results/annotation/secondary-audit-20260924) showed that a guarded click
path does not protect the same effect reached through a keyboard shortcut, Return, a menu item or
a text replacement, and that a failed destructive judgment fell through to "allow". Every route
now resolves to a :class:`NativeAction` and passes :meth:`Authorizer.check` before the bridge
is touched; ``NativeAgent.execute`` is the only caller of the bridge's mutating methods.

Rules, in order:

1. Scoped authorisation: the task's ``authorized_actions`` (label substrings) or ``authorize_all``
   stand the gate down for that label.
2. Keyword fast path (``arbiter.destructive_match``) on the action's label with its context.
   For key routes the label is the chord's meaning (``cmd+delete`` is "delete", Return is "confirm
   the default button"), and the labels of every button on the current menu are checked too: a
   Return with a "Replace" or "Don't Save" button on screen is a pause.
3. Replacing existing content: a ``type`` that overwrites a multi-line field's non-empty content is
   a pause unless the task authorises it. The content is the field's whole value (``NativeMenu.values``),
   never the model's 480-character preview. ``append`` is not a replacement: the bridge inserts at the
   end of the exact value and reports ``partial`` unless the old text reads back unchanged.
4. The Jev destructive judgment (``Verifier.judge_destructive``) on System 2 proposals for click,
   menu and hotkey routes (System 1's own ``destructive`` noul already went through the arbiter).
   A judgment that fails is not an allow: ``on_judgment_failure`` is ``"confirm"`` by default.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from jevdual.arbiter import ArbiterPolicy, destructive_match
from jevdual.menu import Candidate
from jevdual.native import NativeMenu

log = logging.getLogger("jevdual.authorize")

Route = Literal["click", "type", "append", "enter", "key", "hotkey", "menu", "scroll", "hover"]

#: chord meanings the keyword gate can read
#: routes System 2 proposes that get the destructive judgment (type is covered by the replace rule)
JUDGED_ROUTES = ("click", "menu", "hotkey", "key", "enter")

CHORD_MEANING = {
    "cmd+delete": "delete",
    "cmd+backspace": "delete",
    "cmd+shift+delete": "empty trash",
    "cmd+q": "quit",
    "cmd+w": "close",
    "cmd+s": "save",
    "cmd+shift+s": "save as",
    "cmd+d": "don't save",
    "return": "confirm the default button",
    "enter": "confirm the default button",
}


@dataclass(frozen=True)
class NativeAction:
    route: Route
    label: str
    system: Literal["s1", "s2"]
    target: Candidate | None = None
    text: str | None = None
    keys: tuple[str, ...] = ()
    path: tuple[str, ...] = ()
    context: str = ""
    #: labels of every button on the current menu (a key press may activate one of them)
    buttons: tuple[str, ...] = ()
    #: the target's whole current value (execution data), when it is a text element
    current: str | None = None

    @property
    def replaces_content(self) -> bool:
        if self.route != "type" or self.target is None:
            return False
        cur = self.current if self.current is not None else (self.target.value or "")
        return (
            self.target.input_type == "textarea"
            # any existing content: a length floor (20 characters until 2026-09-26) let a short document
            # be replaced unpaused (status audit, probe short_document_replacement)
            and bool(cur.strip())
            and (self.text or "") != cur
            and not (self.text or "").startswith(cur)
        )


def action_for(
    route: Route,
    nm: NativeMenu,
    system: Literal["s1", "s2"],
    *,
    target: Candidate | None = None,
    text: str | None = None,
    keys: tuple[str, ...] = (),
    path: tuple[str, ...] = (),
) -> NativeAction:
    """Build the action record every route hands to the authorizer, with the same context rules."""
    buttons = tuple(c.label for c in nm.menu.candidates if c.role in ("button", "menuitem", "menubar"))
    parts = [nm.menu.title]
    if target is not None and target.section:
        parts.append(target.section)
    parts.append(nm.menu.page_text[:300])
    context = " ".join(p for p in parts if p)
    if route in ("key", "hotkey"):
        chord = "+".join(k.casefold() for k in keys)
        label = CHORD_MEANING.get(chord, chord)
    elif route == "menu":
        label = " > ".join(path)
    elif route == "enter":
        label = CHORD_MEANING["return"]
    else:
        label = target.label if target is not None else route
    current = nm.values.get(target.id) if target is not None else None
    return NativeAction(
        route, label, system, target, text, tuple(keys), tuple(path), context, buttons, current
    )


Judge = Callable[..., Awaitable[list[float]]]  # Verifier.judge_destructive(task, targets, *, url, title)

GRANT_ROUTES = ("click", "type", "append", "enter", "scroll", "hover", "key", "hotkey", "menu", "navigate")


def checked_probabilities(probs: Any, n: int) -> list[float]:
    """A judgment's answer, or ValueError: exactly ``n`` finite probabilities in [0, 1]. An empty,
    short, NaN or non-numeric answer is a judgment that did not answer, never a p of 0 (package B1)."""
    if not isinstance(probs, (list, tuple)) or len(probs) != n:
        raise ValueError(
            f"judgment returned {len(probs) if isinstance(probs, (list, tuple)) else type(probs).__name__} values for {n} targets"
        )
    out = []
    for p in probs:
        if (
            isinstance(p, bool)
            or not isinstance(p, (int, float))
            or not math.isfinite(p)
            or not 0.0 <= p <= 1.0
        ):
            raise ValueError(f"judgment returned {p!r}, not a probability")
        out.append(float(p))
    return out


def _norm(s: str) -> str:
    return " ".join(s.casefold().split())


@dataclass
class Authorizer:
    policy: ArbiterPolicy = field(default_factory=ArbiterPolicy)
    authorized_actions: tuple[str, ...] = ()
    authorize_all: bool = False
    #: ``async (task, targets, url, title) -> [p]``: ``Verifier.judge_destructive`` bound to the task, or None
    judge: Judge | None = None
    on_judgment_failure: Literal["confirm", "keyword"] = "confirm"
    #: an extra caller rule (legacy ``gate`` callables in tests): reason string or None
    extra: Callable[[NativeMenu, Candidate], Any] | None = None
    judgments: list[dict[str, Any]] = field(default_factory=list)

    def is_authorized(self, label: str, *, route: str | None = None) -> bool:
        """A grant clears the action it names: the whole label (case and spacing aside), or for a menu
        path its whole path or final item, optionally prefixed by a route (``menu:File > Move to Trash``).
        Until 2026-09-26 a grant was a substring, so ``Delete`` cleared "Delete account" (package B3)."""
        if self.authorize_all:
            return True
        lab = _norm(label)
        last = _norm(label.split(">")[-1]) if ">" in label else None
        for g in self.authorized_actions:
            head, sep, rest = g.partition(":")
            grant_route = _norm(head) if sep and _norm(head) in GRANT_ROUTES else None
            name = _norm(rest if grant_route else g)
            if grant_route is not None and grant_route != (route or ""):
                continue
            if name == lab or (last is not None and name == last):
                return True
        return False

    def _keyword(self, action: NativeAction) -> str | None:
        hit = destructive_match(action.label, action.context, self.policy)
        if hit:
            return f"keyword {hit!r} on {action.route} {action.label!r}"
        if action.route in ("key", "hotkey", "enter"):
            # the chord may activate a button on screen; the buttons carry the meaning
            for b in action.buttons:
                if self.is_authorized(b, route="click"):
                    continue
                bh = destructive_match(b, action.context, self.policy)
                if bh:
                    return f"keyword {bh!r} on button {b!r} reachable by {action.label!r}"
        return None

    async def check(self, nm: NativeMenu, action: NativeAction, *, task: str = "") -> str | None:
        """Reason to pause before dispatching ``action``, or None."""
        if self.is_authorized(action.label, route=action.route):
            return None
        if self.extra is not None and action.target is not None:
            r = self.extra(nm, action.target)
            if hasattr(r, "__await__"):
                r = await r
            if r:
                return str(r)
        hit = self._keyword(action)
        if hit:
            return hit
        if action.replaces_content and not self.is_authorized("replace"):
            n = len(action.current if action.current is not None else (action.target.value or ""))
            return f"replaces {n} characters of existing content in {action.label!r}"
        if action.system == "s2" and self.judge is not None and action.route in JUDGED_ROUTES:
            # a key, chord or Return may press any button on screen (the keyword rule above already
            # reads them that way), so those buttons are judged with it: the same effect gets the same
            # decision whether it is clicked or confirmed by a key (package B2)
            labels = [action.label]
            if action.route in ("key", "hotkey", "enter"):
                labels += [b for b in action.buttons if not self.is_authorized(b, route="click")]
            try:
                probs = checked_probabilities(
                    await self.judge(
                        task,
                        [{"label": lab, "context": action.context} for lab in labels],
                        url=nm.menu.url,
                        title=nm.menu.title,
                    ),
                    len(labels),
                )
            except Exception as exc:  # noqa: BLE001 - a failed judgment has an explicit outcome, never an allow
                log.warning("destructive judgment failed on %r: %s", action.label, exc)
                self.judgments.append({"route": action.route, "label": action.label, "error": str(exc)[:120]})
                if self.on_judgment_failure == "confirm":
                    return f"judgment unavailable for {action.route} {action.label!r} ({type(exc).__name__}); pausing"
                return None
            p, which = max(zip(probs, labels, strict=True))
            self.judgments.append({"route": action.route, "label": action.label, "p": p, "on": which})
            if p >= self.policy.destructive_confirm:
                if which != action.label:
                    # name the button first: the grant a pause suggests is the effect, not the key
                    return (
                        f"judgment p={p:.2f} on button {which!r} reachable by {action.route} {action.label!r}"
                    )
                return f"judgment p={p:.2f} on {action.route} {action.label!r}"
        return None
