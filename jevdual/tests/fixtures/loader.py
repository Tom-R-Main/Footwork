"""Load recorded CDP fixtures and rebuild the objects browser-use's DOM pipeline consumes."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).resolve().parent / "cdp"


@dataclass(frozen=True)
class Fixture:
    slug: str
    url: str
    why: str
    captured_at: str
    snapshot: dict[str, Any]
    """Raw DOMSnapshot.captureSnapshot result (CaptureSnapshotReturns shape)."""
    dom: dict[str, Any]
    """Raw DOM.getDocument result (GetDocumentReturns shape)."""
    ax: dict[str, Any]
    """Merged Accessibility.getFullAXTree nodes across frames ({'nodes': [...]})."""
    device_pixel_ratio: float
    viewport: dict[str, Any]
    """Raw Page.getLayoutMetrics result."""
    js_click_listener_backend_ids: frozenset[int]
    element_count: int
    """len(selector_map) from get_serialized_dom_tree at capture time."""
    selector_backend_node_ids: dict[int, int]
    """selector_index -> backend_node_id at capture time."""
    timing_ms: dict[str, float]

    def to_target_all_trees(self):
        """Rebuild browser_use.dom.views.TargetAllTrees, the exact input to DomService.get_dom_tree."""
        from browser_use.dom.views import TargetAllTrees

        return TargetAllTrees(
            snapshot=self.snapshot,
            dom_tree=self.dom,
            ax_tree=self.ax,
            device_pixel_ratio=self.device_pixel_ratio,
            cdp_timing={},
            js_click_listener_backend_ids=set(self.js_click_listener_backend_ids) or None,
        )


def fixture_slugs() -> list[str]:
    return sorted(p.name[: -len(".json.gz")] for p in FIXTURE_DIR.glob("*.json.gz"))


def manifest() -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / "manifest.json").read_text())


@lru_cache(maxsize=None)
def load_fixture(slug: str) -> Fixture:
    path = FIXTURE_DIR / f"{slug}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        raw = json.load(f)
    return Fixture(
        slug=raw["slug"],
        url=raw["url"],
        why=raw["why"],
        captured_at=raw["captured_at"],
        snapshot=raw["snapshot"],
        dom=raw["dom"],
        ax=raw["ax"],
        device_pixel_ratio=float(raw["device_pixel_ratio"]),
        viewport=raw["viewport"],
        js_click_listener_backend_ids=frozenset(raw.get("js_click_listener_backend_ids") or []),
        element_count=int(raw["element_count"]),
        selector_backend_node_ids={int(k): int(v) for k, v in raw["selector_backend_node_ids"].items()},
        timing_ms=raw.get("timing_ms", {}),
    )
