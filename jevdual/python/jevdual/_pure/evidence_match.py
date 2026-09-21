"""Pure twin of the R4 port: quote-to-span evidence matching.

Reference implementation defined by task D3; R4 ports it to Rust behind the
same signature. It is deterministic and dependency-free: normalization is
whitespace collapse plus Unicode casefold, with an optional punctuation fold
that strips ASCII and common typographic punctuation. Spans are reported as
offsets into the *original* ``page_text``.
"""

from __future__ import annotations

import re
import unicodedata

Grade = str  # "exact" | "normalized" | "none"

_WS = re.compile(r"\s+")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', " ": " ", "–": "-", "—": "-"})


def _fold_chars(text: str, *, strip_punct: bool) -> list[tuple[str, int]]:
    """Map each kept normalized character to the offset of the original character that produced it."""
    out: list[tuple[str, int]] = []
    pending_space = False
    for i, ch in enumerate(text.translate(_QUOTES)):
        if ch.isspace():
            pending_space = True
            continue
        if strip_punct and unicodedata.category(ch).startswith("P"):
            continue
        if pending_space and out:
            out.append((" ", i))
        pending_space = False
        for folded in ch.casefold():
            out.append((folded, i))
    return out


def _normalize(text: str, *, strip_punct: bool) -> str:
    return "".join(c for c, _ in _fold_chars(text, strip_punct=strip_punct))


def _span(folded: list[tuple[str, int]], start: int, length: int, original_len: int) -> tuple[int, int]:
    begin = folded[start][1]
    last = folded[start + length - 1][1]
    return begin, min(last + 1, original_len)


def evidence_match(claims: list[str], page_text: str) -> list[dict]:
    """Grade each claim against ``page_text``.

    Returns one dict per claim: ``{"claim", "grade", "start", "end"}``. ``start``/``end``
    are offsets into ``page_text`` (``-1`` when ``grade`` is ``"none"``). Grades:
    ``exact`` (verbatim substring), ``normalized`` (matches after whitespace, case,
    quote and punctuation folding), ``none``.
    """
    results: list[dict] = []
    folded_plain: list[tuple[str, int]] | None = None
    folded_punct: list[tuple[str, int]] | None = None
    for claim in claims:
        claim_stripped = claim.strip()
        if not claim_stripped:
            results.append({"claim": claim, "grade": "none", "start": -1, "end": -1})
            continue
        idx = page_text.find(claim_stripped)
        if idx >= 0:
            results.append({"claim": claim, "grade": "exact", "start": idx, "end": idx + len(claim_stripped)})
            continue
        matched = False
        for strip_punct in (False, True):
            if strip_punct:
                if folded_punct is None:
                    folded_punct = _fold_chars(page_text, strip_punct=True)
                folded = folded_punct
            else:
                if folded_plain is None:
                    folded_plain = _fold_chars(page_text, strip_punct=False)
                folded = folded_plain
            needle = _normalize(claim_stripped, strip_punct=strip_punct)
            if not needle:
                break
            hay = "".join(c for c, _ in folded)
            pos = hay.find(needle)
            if pos >= 0:
                start, end = _span(folded, pos, len(needle), len(page_text))
                results.append({"claim": claim, "grade": "normalized", "start": start, "end": end})
                matched = True
                break
        if not matched:
            results.append({"claim": claim, "grade": "none", "start": -1, "end": -1})
    return results
