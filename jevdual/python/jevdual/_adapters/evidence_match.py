"""Native adapter for R4: quote-to-span evidence matching.

Same signature and result shape as the pure twin
``jevdual._pure.evidence_match.evidence_match(claims, page_text) -> list[dict]``.
The whole computation runs in ``_core.evidence_match_flat``; this only maps the
compact ``(grade, start, end)`` triples back to the twin's dicts.
"""

from __future__ import annotations

from jevdual import _native

_GRADES = ("none", "exact", "normalized")
_available: bool | None = None


def available() -> bool:
    """True once the real R4 export is built (the placeholder takes no arguments)."""
    global _available
    if _available is None:
        core = _native.core
        try:
            _available = core is not None and core.evidence_match_flat([], "") == []
        except (TypeError, NotImplementedError):
            _available = False
    return _available


def evidence_match(claims: list[str], page_text: str) -> list[dict]:
    triples = _native.core.evidence_match_flat(list(claims), page_text)
    return [
        {"claim": claim, "grade": _GRADES[grade], "start": start, "end": end}
        for claim, (grade, start, end) in zip(claims, triples, strict=True)
    ]
