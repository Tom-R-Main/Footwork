"""R4 equality: native evidence matcher vs the pure twin.

There is no recorded oracle output for this port, so the corpus is built from
the replayed fixtures' page text plus claims derived from it: verbatim windows,
whitespace/case/typography perturbations, punctuation-stripped variants,
padded, empty and absent claims. Every (claims, text) pair must grade and
locate identically; a hypothesis test covers random small texts as well.
"""

from __future__ import annotations

import random
import re
import unicodedata

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from jevdual import _native
from jevdual._pure.evidence_match import evidence_match as pure_match

from tests.equality.conftest import assert_equal, require_native

_PUNCT = re.compile(r"[!\"#%&'()*,\-./:;?@\[\\\]_{}¿¡«»、。「」『』]")


def _page(slug: str) -> str:
    try:
        from tests.fixtures.replay import replay_serialized
    except ImportError:
        pytest.skip("replay helper not available")
    from jevdual.menu import _page_text

    _state, root, _timing = replay_serialized(slug)
    text = _page_text(root, 400_000)
    if not text:
        pytest.skip(f"{slug}: no page text")
    return text


def _perturb(s: str, rng: random.Random) -> list[str]:
    out = [
        s,
        s.upper(),
        s.swapcase(),
        re.sub(r" ", lambda _m: rng.choice(["  ", "\n", "\t ", " "]), s),
        s.replace("'", "’").replace('"', "“").replace("-", "—"),
        _PUNCT.sub("", s),
        f"  {s}\n",
        s.rstrip(".") + ".",
        s + " zzqx",
    ]
    return [c for c in out if c is not None]


def corpus_claims(text: str, seed: int = 7) -> list[str]:
    rng = random.Random(seed)
    n = len(text)
    claims: list[str] = ["", "   ", "　", "...", "not on this page at all zzqx"]
    for _ in range(12):
        start = rng.randrange(0, max(1, n - 90))
        length = rng.choice([5, 12, 30, 60, 90])
        window = text[start : start + length]
        claims.extend(_perturb(window, rng))
    return claims


def test_dispatch_is_native():
    require_native("evidence_match")
    assert _native.backend_report()["evidence_match"] == "native"


def test_native_matches_pure_on_fixture_corpus(slug):
    native = require_native("evidence_match")
    text = _page(slug)
    claims = corpus_claims(text)
    assert_equal("evidence_match", slug, pure_match(claims, text), native(claims, text))


_ALPHABET = st.sampled_from(list("abcAB xyzß.,-'\"\n\t ’“—　日本語ǅİςİ\x1c") + ["fi", "ﬁ"])


@settings(max_examples=150, deadline=None)
@given(
    page=st.lists(_ALPHABET, min_size=0, max_size=40).map("".join),
    extra=st.lists(st.lists(_ALPHABET, min_size=0, max_size=6).map("".join), max_size=4),
    data=st.data(),
)
def test_native_matches_pure_random(page, extra, data):
    native = require_native("evidence_match")
    claims = list(extra)
    if page:
        a = data.draw(st.integers(0, len(page) - 1))
        b = data.draw(st.integers(a, len(page)))
        window = page[a:b]
        claims += [window, window.upper(), _PUNCT.sub("", window), f" {window} "]
    assert pure_match(claims, page) == native(claims, page)


def test_c0_separators_and_categories_agree_with_python():
    """The Rust tables were generated from CPython; spot-check a few sharp edges."""
    native = require_native("evidence_match")
    page = "a\x1cb  ¿c? Straße ǅ"
    claims = ["a b", "c", "strasse", "ǆ", "\x1c"]
    assert pure_match(claims, page) == native(claims, page)
    assert unicodedata.category("¿").startswith("P")
