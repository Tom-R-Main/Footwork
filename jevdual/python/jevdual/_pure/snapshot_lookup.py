"""Pure twin of the R2 port: DOMSnapshot -> per-backend-node lookup.

Wraps upstream ``build_snapshot_lookup`` unchanged so the reference semantics are
exactly browser-use 0.13.10's, including the sensitive-input value filter.
"""

from __future__ import annotations

from typing import Any

from browser_use.dom.enhanced_snapshot import build_snapshot_lookup
from browser_use.dom.views import EnhancedSnapshotNode


def snapshot_lookup(
    snapshot: dict[str, Any], device_pixel_ratio: float = 1.0
) -> dict[int, EnhancedSnapshotNode]:
    """Map backend_node_id -> EnhancedSnapshotNode for a raw CaptureSnapshotReturns dict."""
    return build_snapshot_lookup(snapshot, device_pixel_ratio)  # type: ignore[arg-type]
