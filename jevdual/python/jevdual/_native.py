"""Backend selection: native extension or pure-Python twins.

Set ``JEVDUAL_PURE_PY=1`` to force the pure-Python implementations. The chosen
backend name is exported as ``BACKEND`` and written into every trace header.

Every hot path has a name in ``FUNCTIONS``. ``native_or_pure(name)`` returns the
native implementation from ``jevdual._core`` when the extension is loaded and
exports that attribute, otherwise the pure twin from ``jevdual._pure``. The
Python-level signature is the contract: a port's native function must accept
the same arguments as its twin (a thin adapter here is fine when the Rust side
wants flat arrays). ``backend_report()`` says which side each name resolved to.
"""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Callable
from typing import Any

_log = logging.getLogger("jevdual.native")

PURE_PY_ENV = "JEVDUAL_PURE_PY"

core = None
if os.environ.get(PURE_PY_ENV) != "1":
    try:
        from jevdual import _core as core  # type: ignore[no-redef]
    except ImportError as exc:  # pragma: no cover - exercised only when the wheel lacks the extension
        _log.warning("jevdual._core unavailable (%s); falling back to pure Python", exc)
        core = None

BACKEND: str = f"native {core.version()}" if core is not None else "pure-python"
_log.info("jevdual backend: %s", BACKEND)

#: name -> (pure module path, attribute name shared by the pure twin and the native export)
FUNCTIONS: dict[str, tuple[str, str]] = {
    "paint_order": ("jevdual._pure.paint_order", "paint_order"),  # R1
    "snapshot_lookup": ("jevdual._pure.snapshot_lookup", "snapshot_lookup"),  # R2
    "element_hashes": ("jevdual._pure.element_hashes", "element_hashes"),  # R3
    "evidence_match": ("jevdual._pure.evidence_match", "evidence_match"),  # R4
}

_resolved: dict[str, tuple[str, Callable[..., Any]]] = {}
_fallback_logged: set[str] = set()


def native_available() -> bool:
    return core is not None


def _resolve(name: str) -> tuple[str, Callable[..., Any]]:
    if name in _resolved:
        return _resolved[name]
    if name not in FUNCTIONS:
        raise KeyError(f"unknown jevdual hot path {name!r}; known: {sorted(FUNCTIONS)}")
    module_path, attr = FUNCTIONS[name]
    fn = None
    if core is not None:
        # A port may need a thin Python adapter that flattens the input for the
        # native core (docs/rust-boundary.md). If ``jevdual._adapters.<name>``
        # exposes ``attr`` and the core has what it needs, that adapter is the
        # native implementation; otherwise a same-signature ``_core.<attr>`` is.
        try:
            adapter = importlib.import_module(f"jevdual._adapters.{name}")
        except ImportError:
            adapter = None
        if adapter is not None and getattr(adapter, "available", lambda: True)():
            fn = getattr(adapter, attr, None)
        if fn is None:
            fn = getattr(core, attr, None)
    if fn is not None:
        _resolved[name] = ("native", fn)
        return _resolved[name]
    if core is not None and name not in _fallback_logged:
        _fallback_logged.add(name)
        _log.info("native extension has no %r yet; using pure Python", attr)
    pure = getattr(importlib.import_module(module_path), attr)
    _resolved[name] = ("pure", pure)
    return _resolved[name]


def native_or_pure(name: str) -> Callable[..., Any]:
    """Return the implementation for ``name``: native when built, else the pure twin."""
    return _resolve(name)[1]


def pure(name: str) -> Callable[..., Any]:
    """Always the pure twin, for equality tests and baselines."""
    module_path, attr = FUNCTIONS[name]
    return getattr(importlib.import_module(module_path), attr)


def native(name: str) -> Callable[..., Any] | None:
    """The native export for ``name`` if the extension is loaded and provides it, else None."""
    if core is None:
        return None
    return getattr(core, FUNCTIONS[name][1], None)


def backend_report() -> dict[str, str]:
    """{name: "native" | "pure"} for every hot path; written into the trace header."""
    return {name: _resolve(name)[0] for name in FUNCTIONS}
