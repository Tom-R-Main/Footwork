"""Backend selection: native extension or pure-Python twins.

Set ``JEVDUAL_PURE_PY=1`` to force the pure-Python implementations. The chosen
backend name is exported as ``BACKEND`` and written into every trace header.
"""

from __future__ import annotations

import logging
import os

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


def native_available() -> bool:
    return core is not None
