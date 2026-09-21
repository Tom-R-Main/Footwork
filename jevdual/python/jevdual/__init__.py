"""jevdual: a dual-process browser agent on top of browser-use.

System 1 is TypeSafe Jev, one speculative fan-out request per step. System 2 is
the stock browser-use LLM path. Hot paths run natively when ``jevdual._core`` is
importable and ``JEVDUAL_PURE_PY`` is not ``1``.
"""

from jevdual._native import BACKEND

__all__ = ["BACKEND", "__version__"]
__version__ = "0.0.1"
