"""Adapter for the R2 native port: raw DOMSnapshot dict -> EnhancedSnapshotNode lookup.

``jevdual._core.snapshot_lookup_flat`` reads the CDP dict, runs the algorithm
with the interpreter detached, and returns parallel arrays keyed by backend
node id. This module rebuilds browser-use's ``EnhancedSnapshotNode`` dataclasses
from those arrays so the result is field-for-field identical to the pure twin
(``jevdual._pure.snapshot_lookup``). Dataclass construction is Python-object
creation and is deliberately kept on this side of the boundary.
"""

from __future__ import annotations

from typing import Any

from browser_use.dom.enhanced_snapshot import REQUIRED_COMPUTED_STYLES
from browser_use.dom.views import DOMRect, EnhancedSnapshotNode

from jevdual._native import core

_available: bool | None = None


def available() -> bool:
    """Opt-in only: the native path proves equality but is not faster end to end
    while EnhancedSnapshotNode dataclasses are rebuilt in Python (see R2 notes in
    results/r2-snapshot-lookup.md). Set JEVDUAL_NATIVE_SNAPSHOT=1 to enable."""
    import os

    if os.environ.get("JEVDUAL_NATIVE_SNAPSHOT") != "1":
        return False
    return _available_impl()


def _available_impl() -> bool:
    """True when the loaded extension has a working (non-placeholder) ``snapshot_lookup_flat``."""
    global _available
    if _available is None:
        fn = getattr(core, "snapshot_lookup_flat", None)
        if fn is None:
            _available = False
        else:
            try:
                out = fn({"documents": [], "strings": []}, 1.0)
                _available = isinstance(out, dict) and "ids" in out
            except Exception:  # noqa: BLE001 - a placeholder raises; treat as not built
                _available = False
    return _available


def flat(snapshot: dict[str, Any], device_pixel_ratio: float = 1.0, strategy: str = "cast") -> dict[str, Any]:
    """The raw parallel arrays from Rust (used by benchmarks to time the core alone)."""
    return core.snapshot_lookup_flat(snapshot, float(device_pixel_ratio), strategy)


def build(snapshot: dict[str, Any], out: dict[str, Any]) -> dict[int, EnhancedSnapshotNode]:
    """Rebuild ``EnhancedSnapshotNode`` objects from the parallel arrays."""
    strings = snapshot["strings"]
    ids = out["ids"]
    clickable = out["clickable"]
    cursor = out["cursor"]
    has_b, b = out["has_bounds"], out["bounds"]
    has_c, c = out["has_client_rect"], out["client_rects"]
    has_s, s = out["has_scroll_rect"], out["scroll_rects"]
    styles = out["styles"]
    n_styles = out["style_count"]
    paint = out["paint_order"]
    stacking = out["stacking_context"]
    ivalue = out["input_value"]
    ichecked = out["input_checked"]
    names = REQUIRED_COMPUTED_STYLES
    result: dict[int, EnhancedSnapshotNode] = {}
    for i, bid in enumerate(ids):
        j = 4 * i
        k = n_styles * i
        cs: dict[str, str] | None = None
        row = styles[k : k + n_styles]
        if any(x >= 0 for x in row):
            cs = {names[m]: strings[x] for m, x in enumerate(row) if x >= 0}
        result[bid] = EnhancedSnapshotNode(
            is_clickable=None if clickable[i] < 0 else bool(clickable[i]),
            cursor_style=strings[cursor[i]] if cursor[i] >= 0 else None,
            bounds=DOMRect(x=b[j], y=b[j + 1], width=b[j + 2], height=b[j + 3]) if has_b[i] else None,
            clientRects=DOMRect(x=c[j], y=c[j + 1], width=c[j + 2], height=c[j + 3]) if has_c[i] else None,
            scrollRects=DOMRect(x=s[j], y=s[j + 1], width=s[j + 2], height=s[j + 3]) if has_s[i] else None,
            computed_styles=cs,
            paint_order=paint[i] if paint[i] >= 0 else None,
            stacking_contexts=stacking[i] if stacking[i] >= 0 else None,
            input_value=strings[ivalue[i]] if ivalue[i] >= 0 else None,
            input_checked=None if ichecked[i] < 0 else bool(ichecked[i]),
        )
    return result


def snapshot_lookup(
    snapshot: dict[str, Any], device_pixel_ratio: float = 1.0
) -> dict[int, EnhancedSnapshotNode]:
    """Same signature and result as the pure twin, computed natively."""
    if not snapshot.get("documents"):
        return {}
    return build(snapshot, flat(snapshot, device_pixel_ratio))
