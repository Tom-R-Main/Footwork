"""Secrets: names only reach models; values resolve at dispatch for the right origin; nothing echoes.

browser-use already scopes ``sensitive_data`` by domain pattern and substitutes
``<secret>name</secret>`` placeholders inside action params at dispatch
(``Registry._replace_sensitive_data`` via ``match_url_with_domain_pattern``).
This module builds on that instead of re-implementing dispatch:

* ``SecretStore`` holds the values, exposes only ``names()`` to model-facing
  code, produces the exact ``sensitive_data`` dict for the Agent, and applies a
  stricter origin rule than upstream (``allowed_for``) so a caller can pre-filter.
* ``Redactor`` scrubs every value and its common encodings from anything that
  gets serialized: trace lines, memory lines, error messages.
* ``assert_no_secrets`` walks a JSON-able object and raises if a raw value is
  present; JevS1 uses it in debug mode.

Values shorter than ``MIN_SECRET_CHARS`` are refused: a three-character secret
would redact ordinary words and offers no protection worth the false positives.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
from collections.abc import Iterator, Mapping
from typing import Any
from urllib.parse import quote, quote_plus, urlsplit

MIN_SECRET_CHARS = 4
PLACEHOLDER_RE = re.compile(r"<secret>([^<]+)</secret>")
DEBUG_ASSERT_ENV = "JEVDUAL_SECRETS_ASSERT"
DEBUG_ASSERT = os.environ.get(DEBUG_ASSERT_ENV) == "1"

ANY_ORIGIN = "*"
_LOOPBACK = {"localhost", "127.0.0.1", "::1", "[::1]"}


class SecretError(ValueError):
    pass


class SecretLeak(AssertionError):
    """Raised by ``assert_no_secrets`` when a raw value is found in model-facing data."""


def _is_loopback(host: str) -> bool:
    return host in _LOOPBACK or host.endswith(".localhost")


def _parse_pattern(pattern: str) -> tuple[str | None, str]:
    """Split a browser-use style pattern into (scheme or None, host). Ports are dropped."""
    p = pattern.strip().lower().rstrip("/")
    scheme: str | None = None
    if "://" in p:
        scheme, p = p.split("://", 1)
    if p.startswith("[") and "]" in p:  # bracketed ipv6
        host = p[: p.index("]") + 1]
    else:
        host = p.split("/", 1)[0].split(":", 1)[0]
    return scheme, host


def origin_allows(url: str, pattern: str) -> bool:
    """Strict origin rule for one pattern.

    * ``*`` (or a flat, un-scoped entry) matches any http(s) origin.
    * ``example.com`` matches exactly that host.
    * ``*.example.com`` matches that host and any subdomain, by whole labels only,
      so ``evil-example.com`` and ``example.com.evil.test`` never match.
    * https is required unless the pattern names a scheme explicitly or the host
      is loopback; ``http*://`` is accepted as "either".
    * Any other wildcard placement is rejected.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    scheme = (parts.scheme or "").lower()
    host = (parts.hostname or "").lower()
    if not scheme or not host:
        return False
    if parts.username or parts.password:
        return False
    pat_scheme, pat_host = _parse_pattern(pattern)
    # Plaintext HTTP carries credentials in the clear; it is allowed only to loopback hosts,
    # whatever the pattern says (an explicit http:// pattern cannot opt a remote host in).
    if scheme == "http" and not _is_loopback(host):
        return False
    if pat_host == ANY_ORIGIN:
        return scheme in ("http", "https")
    if "*" in pat_host and not (pat_host.startswith("*.") and "*" not in pat_host[2:]):
        return False
    if pat_scheme is None or pat_scheme == "http*":
        scheme_ok = scheme in ("http", "https")
    else:
        scheme_ok = scheme == pat_scheme
    if not scheme_ok:
        return False
    if pat_host.startswith("*."):
        parent = pat_host[2:]
        return host == parent or host.endswith("." + parent)
    return host == pat_host


class SecretStore:
    """Secret values keyed by name, each scoped to one origin pattern.

    Accepts the same shape browser-use does: ``{name: value}`` (any origin) or
    ``{pattern: {name: value}}``. A name may appear under several patterns.
    """

    def __init__(self, data: Mapping[str, str | Mapping[str, str]]):
        self._scoped: dict[str, dict[str, str]] = {}
        for key, content in data.items():
            if isinstance(content, Mapping):
                pattern, entries = key, dict(content)
            else:
                pattern, entries = ANY_ORIGIN, {key: content}
            for name, value in entries.items():
                self._check(name, value)
                self._scoped.setdefault(pattern, {})[name] = value
        self._values: dict[str, set[str]] = {}
        for entries in self._scoped.values():
            for name, value in entries.items():
                self._values.setdefault(name, set()).add(value)

    @staticmethod
    def _check(name: str, value: Any) -> None:
        if not isinstance(name, str) or not name or "<" in name or ">" in name:
            raise SecretError(f"invalid secret name {name!r}")
        if not isinstance(value, str):
            raise SecretError(f"secret {name!r}: value must be a string")
        if len(" ".join(value.split())) < MIN_SECRET_CHARS:
            raise SecretError(f"secret {name!r}: value shorter than {MIN_SECRET_CHARS} characters after whitespace normalization")

    def names(self) -> tuple[str, ...]:
        """The only thing a model ever sees."""
        return tuple(sorted(self._values))

    def values(self) -> Iterator[tuple[str, str]]:
        for name in sorted(self._values):
            for value in sorted(self._values[name]):
                yield name, value

    def to_browser_use(self) -> dict[str, str | dict[str, str]]:
        """The ``sensitive_data`` argument for browser-use's Agent, unchanged in shape."""
        out: dict[str, str | dict[str, str]] = {}
        for pattern, entries in self._scoped.items():
            if pattern == ANY_ORIGIN:
                out.update(entries)
            else:
                out[pattern] = dict(entries)
        return out

    def to_browser_use_for(self, url: str) -> dict[str, str | dict[str, str]]:
        """Only the scopes the strict rule allows for ``url`` (pre-filter before handing to upstream)."""
        out: dict[str, str | dict[str, str]] = {}
        for pattern, entries in self._scoped.items():
            if not origin_allows(url, pattern):
                continue
            if pattern == ANY_ORIGIN:
                out.update(entries)
            else:
                out[pattern] = dict(entries)
        return out

    def allowed_for(self, url: str, name: str) -> bool:
        return any(name in entries and origin_allows(url, pattern) for pattern, entries in self._scoped.items())

    @staticmethod
    def placeholder(name: str) -> str:
        return f"<secret>{name}</secret>"

    def redactor(self) -> Redactor:
        return Redactor(self)


def _lower_escapes(encoded: str) -> str:
    """Lowercase only the hex digits of percent escapes, leaving literal letters untouched."""
    return re.sub(r"%[0-9A-Fa-f]{2}", lambda m: m.group(0).lower(), encoded)


def _variants(value: str) -> set[str]:
    """Every echo form a page, log or serializer is likely to produce for a value."""
    v: set[str] = {value}
    collapsed = " ".join(value.split())
    v.add(collapsed)
    for s in (value, collapsed):
        pct = quote(s, safe="")
        v.add(pct)
        v.add(_lower_escapes(pct))
        v.add(quote_plus(s))
        v.add(_lower_escapes(quote_plus(s)))
        v.add(html.escape(s, quote=True))
        v.add(html.escape(s, quote=False))
        v.add(json.dumps(s)[1:-1])
        v.add(json.dumps(s, ensure_ascii=True)[1:-1])
        v.add(base64.b64encode(s.encode()).decode())
        v.add(base64.urlsafe_b64encode(s.encode()).decode().rstrip("="))
        v.add(re.sub(r"([\\`*_\[\]])", r"\\\1", s))  # markdown escaping
    return {x for x in v if len(x) >= MIN_SECRET_CHARS}


class Redactor:
    """Callable that replaces every secret value (and its encodings) with ``[REDACTED:name]``.

    Whitespace inside a value matches any whitespace run, because pages collapse
    and pad whitespace when they echo text.
    """

    def __init__(self, store: SecretStore):
        patterns: list[tuple[int, str, str]] = []
        for name, value in store.values():
            for variant in _variants(value):
                if " " in variant:
                    pat = r"\s+".join(re.escape(part) for part in variant.split(" ") if part)
                else:
                    pat = re.escape(variant)
                patterns.append((len(variant), pat, name))
        # Longest first so a value that contains another is replaced whole.
        patterns.sort(key=lambda p: p[0], reverse=True)
        self._rules: list[tuple[re.Pattern[str], str]] = [(re.compile(pat), name) for _, pat, name in patterns]

    def __call__(self, text: str) -> str:
        if not text or not self._rules:
            return text
        for rx, name in self._rules:
            if rx.search(text):
                text = rx.sub(f"[REDACTED:{name}]", text)
        return text


def _walk_strings(obj: Any) -> Iterator[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, Mapping):
        for k, v in obj.items():
            yield from _walk_strings(k)
            yield from _walk_strings(v)
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            yield from _walk_strings(item)
    elif hasattr(obj, "model_dump"):
        yield from _walk_strings(obj.model_dump())
    elif hasattr(obj, "__dict__") and not isinstance(obj, type):
        yield from _walk_strings(vars(obj))


def assert_no_secrets(obj: Any, store: SecretStore, *, where: str = "model-facing data") -> None:
    """Raise ``SecretLeak`` if any raw secret value (or encoded variant) appears in ``obj``."""
    redactor = store.redactor()
    for s in _walk_strings(obj):
        if redactor(s) != s:
            raise SecretLeak(f"secret value present in {where}")


def install(agent_kwargs: dict[str, Any], store: SecretStore, trace_writer: Any | None = None, *, url: str | None = None) -> dict[str, Any]:
    """Return Agent kwargs with ``sensitive_data`` set and wire the trace redactor.

    With ``url``, only scopes the strict rule allows for that url are handed to
    browser-use; without it the full store is passed and upstream matches per step.
    """
    kwargs = dict(agent_kwargs)
    kwargs["sensitive_data"] = store.to_browser_use_for(url) if url else store.to_browser_use()
    if trace_writer is not None:
        trace_writer.set_redactor(store.redactor())
    return kwargs
