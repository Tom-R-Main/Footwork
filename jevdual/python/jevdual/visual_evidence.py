"""Immutable target-bound inspection evidence. It grants no execution authority.

The capturing driver must establish surface/viewport provenance. These types validate
the supplied capture and binding; equality is not a live screen-freshness check.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime


class VisualEvidenceError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise VisualEvidenceError(code)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class Bounds:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        _require(all(_number(v) for v in (self.x, self.y, self.width, self.height)), "invalid_bounds")
        _require(self.width > 0 and self.height > 0, "empty_bounds")
        for name in ("x", "y", "width", "height"):
            object.__setattr__(self, name, float(getattr(self, name)))


@dataclass(frozen=True)
class Surface:
    kind: str
    pid: int | None = None
    window_id: int | None = None
    tab_id: str | None = None

    def __post_init__(self) -> None:
        _require(self.kind in ("native", "browser"), "invalid_surface")
        for v in (self.pid, self.window_id):
            _require(v is None or (type(v) is int and v > 0), "invalid_surface_id")
        if self.kind == "native":
            _require(self.pid is not None and self.window_id is not None and self.tab_id is None,
                     "missing_native_surface")
        else:
            _require(_text(self.tab_id) and self.window_id is None, "missing_browser_surface")


@dataclass(frozen=True)
class BoundTarget:
    id: str
    token: str
    bounds: Bounds
    operation: str
    postcondition: str
    pixel_bounds: tuple[int, int, int, int]

    def __post_init__(self) -> None:
        _require(all(_text(v) for v in (self.id, self.token, self.operation, self.postcondition)),
                 "missing_target_binding")
        _require(isinstance(self.bounds, Bounds), "invalid_target_bounds")
        _require(type(self.pixel_bounds) is tuple and len(self.pixel_bounds) == 4
                 and all(type(v) is int for v in self.pixel_bounds), "invalid_pixel_bounds")
        left, top, right, bottom = self.pixel_bounds
        _require(0 <= left < right and 0 <= top < bottom, "invalid_pixel_bounds")


def _png_dimensions(png: bytes) -> tuple[int, int]:
    _require(type(png) is bytes and 0 < len(png) <= 32_000_000, "invalid_png_bytes")
    # Decode/verify, never alter the captured pixels. Pillow is already supplied by
    # the browser runtime; imported only for the optional inspection capability.
    from PIL import Image

    try:
        with Image.open(io.BytesIO(png)) as im:
            _require(im.format == "PNG", "not_png")
            _require(0 < im.width <= 16_384 and 0 < im.height <= 16_384
                     and im.width * im.height <= 32_000_000, "capture_dimensions")
            dimensions = im.size
            im.verify()
        # verify() checks chunks; load() also rejects corrupt/truncated pixel data.
        with Image.open(io.BytesIO(png)) as im:
            im.load()
    except VisualEvidenceError:
        raise
    except Exception:  # noqa: BLE001 - expose no capture bytes or decoder details
        raise VisualEvidenceError("invalid_png") from None
    return dimensions


def _pixel_bounds(viewport: Bounds, target: Bounds, dimensions: tuple[int, int]) -> tuple[int, int, int, int]:
    _require(target.x >= viewport.x and target.y >= viewport.y
             and target.x + target.width <= viewport.x + viewport.width
             and target.y + target.height <= viewport.y + viewport.height, "target_outside_capture")
    sx, sy = dimensions[0] / viewport.width, dimensions[1] / viewport.height
    bounds = (math.floor((target.x - viewport.x) * sx), math.floor((target.y - viewport.y) * sy),
              math.ceil((target.x + target.width - viewport.x) * sx),
              math.ceil((target.y + target.height - viewport.y) * sy))
    _require(0 <= bounds[0] < bounds[2] <= dimensions[0]
             and 0 <= bounds[1] < bounds[3] <= dimensions[1], "invalid_pixel_bounds")
    return bounds


@dataclass(frozen=True)
class VisualEvidence:
    png: bytes = field(repr=False)
    surface: Surface
    observation_id: str
    captured_at: str
    viewport: Bounds
    target: BoundTarget
    dimensions: tuple[int, int] = field(init=False)
    image_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _require(isinstance(self.surface, Surface) and isinstance(self.viewport, Bounds)
                 and isinstance(self.target, BoundTarget), "invalid_binding_types")
        _require(_text(self.observation_id) and _text(self.captured_at), "missing_observation")
        try:
            stamp = datetime.fromisoformat(self.captured_at)
        except (ValueError, AttributeError):
            raise VisualEvidenceError("invalid_capture_time") from None
        _require(stamp.tzinfo is not None and stamp.utcoffset() is not None, "capture_time_timezone")
        dimensions = _png_dimensions(self.png)
        _require(self.target.pixel_bounds == _pixel_bounds(self.viewport, self.target.bounds, dimensions),
                 "pixel_binding_mismatch")
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "image_sha256", hashlib.sha256(self.png).hexdigest())

    def to_dict(self) -> dict:
        return {"version": 1, "inspection_only": True, "surface": asdict(self.surface),
                "observation_id": self.observation_id, "captured_at": self.captured_at,
                "image": {"sha256": self.image_sha256, "width": self.dimensions[0],
                          "height": self.dimensions[1], "scale_x": self.dimensions[0] / self.viewport.width,
                          "scale_y": self.dimensions[1] / self.viewport.height},
                "viewport": asdict(self.viewport), "target": asdict(self.target)}

    @property
    def binding_sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True,
                                        allow_nan=False).encode()).hexdigest()

    def assert_matches(self, other: VisualEvidence) -> None:
        """Reject changed evidence/proposals. Does not query the live surface or permit an action."""
        _require(isinstance(other, VisualEvidence) and self.binding_sha256 == other.binding_sha256,
                 "visual_binding_changed")


def bind_visual(*, png: bytes, surface: Surface, observation_id: str, captured_at: str,
                viewport: Bounds, target_id: str, target_token: str, target_bounds: Bounds,
                operation: str, postcondition: str) -> VisualEvidence:
    _require(isinstance(viewport, Bounds) and isinstance(target_bounds, Bounds), "invalid_target_bounds")
    dimensions = _png_dimensions(png)
    target = BoundTarget(target_id, target_token, target_bounds, operation, postcondition,
                         _pixel_bounds(viewport, target_bounds, dimensions))
    return VisualEvidence(png, surface, observation_id, captured_at, viewport, target)
