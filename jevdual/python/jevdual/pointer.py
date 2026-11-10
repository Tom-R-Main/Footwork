"""Real-pointer coordinates.

Footwork works in one space: global screen points with a top-left origin, the space of AX frames and
Quartz events. CUA's desktop-scoped ``move_cursor`` instead takes native ``get_desktop_state`` screenshot
pixels and divides them by the main display's backing scale (platform-macos ``tools/mod.rs``,
``desktop_screenshot_point``). ``desktop_pixels`` is the one conversion between the two, and its result
carries the scale it used so a record can show it.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DesktopPixels:
    """A point in CUA's desktop screenshot pixels, with the backing scale that produced it."""

    x: float
    y: float
    scale: float


def desktop_pixels(x: float, y: float, scale: float) -> DesktopPixels:
    """Convert global screen points to CUA desktop pixels for a main display of backing ``scale``."""
    if not (isinstance(scale, (int, float)) and math.isfinite(scale) and scale > 0):
        raise ValueError(f"backing scale must be a positive finite number, got {scale!r}")
    return DesktopPixels(x * scale, y * scale, float(scale))


def main_display_scale(outcome: Any) -> float | None:
    """The ``scale_factor`` from a CUA ``get_screen_size`` result, or None when it is missing or invalid."""
    if getattr(outcome, "is_error", False):
        return None
    structured = getattr(outcome, "structured_json", None)
    try:
        record = json.loads(structured) if isinstance(structured, str) else structured
    except ValueError:
        return None
    scale = record.get("scale_factor") if isinstance(record, dict) else None
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        return None
    return float(scale) if math.isfinite(scale) and scale > 0 else None
