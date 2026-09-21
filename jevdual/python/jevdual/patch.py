"""Import-time patches that swap upstream hot paths for faster implementations.

Every patch is guarded by the contract tests in ``tests/contract`` (task A4), is
idempotent, and can be disabled with ``JEVDUAL_PURE_PY=1``. ``active_patches()``
is written into the trace header so a run records what it ran with.

R6: cdp-use decodes every CDP message with the stdlib ``json.loads``; on
DOMSnapshot payloads that is 12 to 75 ms per step. ``orjson`` is already a
dependency, so this swaps the decoder and keeps ``json.dumps`` for sending.

R5: the serializer calls ``PaintOrderRemover(tree).calculate_paint_order()``
through the name it imported into ``browser_use.dom.serializer.serializer``,
and ``DomService.get_dom_tree`` calls ``build_snapshot_lookup`` through the
name imported into ``browser_use.dom.service``. Both the defining module and
the importing module are rebound, and the contract tests pin that those are
the bindings upstream actually uses. Paint order goes native whenever R1 is
built; snapshot lookup only when its adapter opts in (JEVDUAL_NATIVE_SNAPSHOT=1),
because it is not faster end to end (results/r2-snapshot-lookup.md).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger("jevdual.patch")

_ACTIVE: dict[str, bool] = {}
_ORIGINALS: dict[str, Any] = {}


class _JsonShim:
    """Stand-in for the ``json`` module inside ``cdp_use.client``.

    ``loads`` is orjson (accepts str or bytes, returns the same dict shape).
    ``dumps`` stays stdlib because the websocket send path expects ``str``.
    """

    @staticmethod
    def loads(raw: str | bytes) -> Any:
        import orjson

        return orjson.loads(raw)

    dumps = staticmethod(json.dumps)


def install_orjson_decode() -> bool:
    """Route cdp-use message decoding through orjson. Returns True if active."""
    if os.environ.get("JEVDUAL_PURE_PY") == "1":
        return False
    if _ACTIVE.get("orjson_decode"):
        return True
    from cdp_use import client

    if client.json is not json and client.json is not _JsonShim:  # pragma: no cover
        log.warning("cdp_use.client.json is not the stdlib module; leaving it alone")
        return False
    client.json = _JsonShim  # type: ignore[assignment]
    _ACTIVE["orjson_decode"] = True
    log.info("jevdual patch active: cdp-use orjson decode")
    return True


class _NativePaintOrderRemover:
    """Drop-in for upstream's ``PaintOrderRemover``: same constructor and method."""

    __slots__ = ("root",)

    def __init__(self, root: Any):
        self.root = root

    def calculate_paint_order(self) -> None:
        from jevdual._adapters.paint_order import paint_order

        paint_order(self.root)


def install_paint_order() -> bool:
    """Route DOMTreeSerializer's paint-order pass through the R1 native port."""
    if os.environ.get("JEVDUAL_PURE_PY") == "1":
        return False
    if _ACTIVE.get("paint_order"):
        return True
    from jevdual import _native

    if _native.native("paint_order") is None:
        log.info("paint_order native port not built; upstream PaintOrderRemover kept")
        return False
    from browser_use.dom.serializer import paint_order as po_mod
    from browser_use.dom.serializer import serializer as ser_mod

    for mod in (po_mod, ser_mod):
        current = getattr(mod, "PaintOrderRemover", None)
        if current is not None and current is not po_mod.PaintOrderRemover and current is not _NativePaintOrderRemover:
            log.warning("%s.PaintOrderRemover already replaced by something else; leaving it alone", mod.__name__)
            return False
    _ORIGINALS.setdefault("PaintOrderRemover", po_mod.PaintOrderRemover)
    po_mod.PaintOrderRemover = _NativePaintOrderRemover  # type: ignore[assignment]
    ser_mod.PaintOrderRemover = _NativePaintOrderRemover  # type: ignore[assignment]
    _ACTIVE["paint_order"] = True
    log.info("jevdual patch active: native paint order")
    return True


def install_snapshot_lookup() -> bool:
    """Route DomService.get_dom_tree's snapshot lookup through the R2 native port (opt-in)."""
    if os.environ.get("JEVDUAL_PURE_PY") == "1":
        return False
    if _ACTIVE.get("snapshot_lookup"):
        return True
    from jevdual._adapters import snapshot_lookup as adapter

    if not adapter.available():
        log.info("snapshot_lookup native port not enabled (JEVDUAL_NATIVE_SNAPSHOT=1 opts in); upstream kept")
        return False
    from browser_use.dom import enhanced_snapshot as es_mod
    from browser_use.dom import service as svc_mod

    for mod in (es_mod, svc_mod):
        current = getattr(mod, "build_snapshot_lookup", None)
        if current is not None and current is not es_mod.build_snapshot_lookup and current is not adapter.snapshot_lookup:
            log.warning("%s.build_snapshot_lookup already replaced by something else; leaving it alone", mod.__name__)
            return False
    _ORIGINALS.setdefault("build_snapshot_lookup", es_mod.build_snapshot_lookup)
    es_mod.build_snapshot_lookup = adapter.snapshot_lookup  # type: ignore[assignment]
    svc_mod.build_snapshot_lookup = adapter.snapshot_lookup  # type: ignore[assignment]
    _ACTIVE["snapshot_lookup"] = True
    log.info("jevdual patch active: native snapshot lookup")
    return True


def uninstall() -> None:
    """Restore upstream bindings (tests and benchmarks only)."""
    if "PaintOrderRemover" in _ORIGINALS:
        from browser_use.dom.serializer import paint_order as po_mod
        from browser_use.dom.serializer import serializer as ser_mod

        po_mod.PaintOrderRemover = _ORIGINALS["PaintOrderRemover"]  # type: ignore[assignment]
        ser_mod.PaintOrderRemover = _ORIGINALS["PaintOrderRemover"]  # type: ignore[assignment]
        _ACTIVE.pop("paint_order", None)
    if "build_snapshot_lookup" in _ORIGINALS:
        from browser_use.dom import enhanced_snapshot as es_mod
        from browser_use.dom import service as svc_mod

        es_mod.build_snapshot_lookup = _ORIGINALS["build_snapshot_lookup"]  # type: ignore[assignment]
        svc_mod.build_snapshot_lookup = _ORIGINALS["build_snapshot_lookup"]  # type: ignore[assignment]
        _ACTIVE.pop("snapshot_lookup", None)
    if "lazy_uuid" in _ORIGINALS:
        from browser_use.dom import service as svc_mod

        svc_mod.EnhancedDOMTreeNode = _ORIGINALS.pop("lazy_uuid")  # type: ignore[attr-defined]
        _ACTIVE.pop("lazy_uuid", None)
        _ACTIVE.pop("snapshot_lookup", None)


def install_lazy_uuid() -> bool:
    """Skip the per-node uuid7 in the DOM tree builder.

    Upstream's EnhancedDOMTreeNode declares ``uuid: str = field(default_factory=uuid7str)``
    and nothing reads it (the contract test pins that), so ~15k uuid7 calls per step on a
    dense page are pure cost (22 ms on the Wikipedia fixture, measured directly). The tree
    builder constructs nodes through the name bound in ``browser_use.dom.service``; this
    rebinds it to a subclass whose uuid defaults to an empty string. Everything else about
    the node, including isinstance checks, is unchanged.
    """
    if os.environ.get("JEVDUAL_PURE_PY") == "1":
        return False
    if _ACTIVE.get("lazy_uuid"):
        return True
    import dataclasses

    from browser_use.dom import service, views

    if service.EnhancedDOMTreeNode is not views.EnhancedDOMTreeNode:  # pragma: no cover
        log.warning("browser_use.dom.service.EnhancedDOMTreeNode already rebound; leaving it alone")
        return False

    # eq=False keeps upstream's __eq__ and explicit __hash__ (a dataclass with eq=True would set __hash__ = None).
    # repr=False keeps upstream's __repr__: a regenerated dataclass repr walks children recursively, and
    # bubus reprs every handler result, which took minutes per step on a live Wikipedia page.
    @dataclasses.dataclass(eq=False, repr=False)
    class EnhancedDOMTreeNodeNoUuid(views.EnhancedDOMTreeNode):
        uuid: str = ""

    EnhancedDOMTreeNodeNoUuid.__name__ = views.EnhancedDOMTreeNode.__name__
    EnhancedDOMTreeNodeNoUuid.__qualname__ = views.EnhancedDOMTreeNode.__qualname__
    service.EnhancedDOMTreeNode = EnhancedDOMTreeNodeNoUuid  # type: ignore[attr-defined]
    _ORIGINALS["lazy_uuid"] = views.EnhancedDOMTreeNode
    _ACTIVE["lazy_uuid"] = True
    log.info("jevdual patch active: lazy node uuid")
    return True


def install() -> dict[str, bool]:
    """Install every available patch; returns the active map for the trace header."""
    install_orjson_decode()
    install_paint_order()
    install_snapshot_lookup()
    install_lazy_uuid()
    return active_patches()


def active_patches() -> dict[str, bool]:
    return dict(_ACTIVE)


def describe() -> dict[str, Any]:
    """What a run actually ran with; written into the trace header."""
    from jevdual import _native

    return {"patches": active_patches(), "backends": _native.backend_report()}
