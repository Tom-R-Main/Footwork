"""One receipt for every action, on both backends (Q12; docs/plans/legible-harness.md P1).

Q11 showed the harness knowing what the driver had to guess: ``jevdual.effects.diff`` computes each
step's visible effect and the arbiter acts on ``no_effect``, while System 2 is told "Clicked" by
browser-use whether or not anything changed. The native path already returns the Cua Driver's own
account of each action. A :class:`Receipt` is that account in one shape for both backends, with the
effect in the driver's five words:

``confirmed``       the page or window changed in a way the harness observed
``partial``         something changed but an action in the step also failed
``unverifiable``    the harness could not observe the outcome (no readback)
``suspected_noop``  nothing observable changed: same URL, no elements added, removed or changed,
                    text unchanged, no dialog or tab change
``refused``         the harness did not dispatch the action (a gate pause, a refused input)

Three deliveries, all made by the runtime and none by the model: the driver's action result text
(:func:`receipt_text`), the verifier's trajectory line (``jevdual.ledger.trajectory_from_agent``)
and the trace (``StepRecord.effect``). The receipt states what was observed; it does not advise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jevdual.effects import Effect

EFFECT_WORDS = ("confirmed", "partial", "unverifiable", "suspected_noop", "refused")


@dataclass(frozen=True)
class Receipt:
    step: int
    #: the actions the step executed, as ``name(label or text)`` lines
    actions: tuple[str, ...]
    effect: str
    #: what the harness observed, in words a driver or a verifier can read
    evidence: str
    #: the effect diff's counts, for the trace and the false-receipt audit
    url_changed: bool = False
    added: int = 0
    removed: int = 0
    changed: int = 0
    text_ratio: float = 1.0
    error: str | None = None

    @property
    def no_effect(self) -> bool:
        return self.effect == "suspected_noop"


def _path(url: str) -> str:
    from jevdual.effects import _path as p

    return p(url or "")


def receipt_from_effect(
    step: int,
    actions: tuple[str, ...],
    effect: Effect,
    *,
    url_after: str = "",
    error: str | None = None,
) -> Receipt:
    """Read an :class:`Effect` (the diff between the menu before the step and the state after it)."""
    if effect.no_effect:
        word = "suspected_noop"
        evidence = (
            f"no change: same URL {_path(url_after)}, no elements added, removed or changed, text unchanged"
        )
        if error:
            word = "refused"
            evidence = f"not applied: {error[:120]}; page unchanged"
    else:
        parts = []
        if effect.url_changed:
            parts.append(f"navigated to {_path(url_after)}")
        if effect.title_changed and not effect.url_changed:
            parts.append("title changed")
        if effect.added or effect.removed or effect.changed:
            parts.append(f"{effect.added} elements added, {effect.removed} removed, {effect.changed} changed")
        if effect.dialog_changed:
            parts.append("a dialog opened or closed")
        if effect.tabs_changed:
            parts.append("tabs changed")
        if not parts:
            parts.append(f"text changed ({effect.text_ratio:.2f} unchanged)")
        word = "partial" if error else "confirmed"
        evidence = "; ".join(parts) + (f"; one action failed: {error[:120]}" if error else "")
    return Receipt(
        step=step,
        actions=tuple(actions),
        effect=word,
        evidence=evidence,
        url_changed=effect.url_changed,
        added=effect.added,
        removed=effect.removed,
        changed=effect.changed,
        text_ratio=effect.text_ratio,
        error=error,
    )


def receipt_from_native(step: int, native: Any) -> Receipt:
    """Wrap a ``jevdual.native.NativeEffect`` (the Driver's words, verbatim) in the shared shape."""
    word = native.effect if native.effect in EFFECT_WORDS else "unverifiable"
    evidence = native.summary or (", ".join(native.evidence) if native.evidence else word)
    return Receipt(
        step=step,
        actions=(f"{native.operation}({native.label})",),
        effect=word,
        evidence=evidence,
        error=native.error_code,
    )


def receipt_text(r: Receipt) -> str:
    """The receipt as the driver reads it in its action result. Facts only."""
    what = ", ".join(r.actions) if r.actions else "the step"
    if r.effect == "suspected_noop":
        return f"Receipt for {what}: suspected no-op ({r.evidence})."
    if r.effect == "refused":
        return f"Receipt for {what}: refused ({r.evidence})."
    if r.effect == "partial":
        return f"Receipt for {what}: partial ({r.evidence})."
    if r.effect == "unverifiable":
        return f"Receipt for {what}: unverifiable ({r.evidence})."
    return f"Receipt for {what}: confirmed ({r.evidence})."


def action_lines(actions: list[Any], state: Any = None) -> tuple[str, ...]:
    """``name(label)`` per executed action, the label from the pre-step selector map when the action
    names an index (the same wording the trajectory uses)."""
    from jevdual.ledger import _element_label

    selector = getattr(getattr(state, "dom_state", None), "selector_map", None) or {}
    out = []
    for a in actions:
        dumped = a.model_dump(exclude_unset=True) if hasattr(a, "model_dump") else dict(a)
        name, params = next(iter(dumped.items()))
        params = dict(params or {})
        label = None
        if "index" in params:
            label = _element_label(selector.get(params["index"]))
        if label is None:
            for key in ("text", "url", "keys", "query"):
                if params.get(key) is not None:
                    label = str(params[key])[:40]
                    break
        out.append(f"{name}({label})" if label else f"{name}()")
    return tuple(out)
