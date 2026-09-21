"""Text composition for TYPE and SELECT operations (task D4).

System 1 picks the field; it never writes the value. The value comes from:

1. a literal in the task (a quoted string, optionally bound to a field by the
   words before it), typed verbatim with no model call;
2. a secret placeholder when the field is a credential and a store knows the
   name, so browser-use substitutes the value at dispatch (task D5);
3. a small helper model behind a strict JSON ``{"text": ...}`` contract
   (jev-ultrafast's field_text pattern), which fails closed on chatty output;
4. otherwise ``None``, which the S1 wrapper turns into an escalation to S2.

Never regex a value out of the goal beyond an explicit quoted literal:
browserclaw's trailing-phrase extraction is the counterexample.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from jevdual.menu import Candidate, Menu

log = logging.getLogger("jevdual.text")

MAX_TEXT_CHARS = 2000
_QUOTE_RE = re.compile(r"[\"“”']([^\"“”']{1,200})[\"“”']")
_STOP = {"the", "a", "an", "into", "in", "to", "for", "with", "as", "field", "box", "and", "then", "search", "type", "enter", "fill"}

SecretPlaceholder = Callable[[Candidate], str | None]
HelperFn = Callable[[str, Candidate, Menu], Awaitable[str | None]]


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.casefold()) if t not in _STOP}


def literal_from_task(task: str, target: Candidate) -> str | None:
    """Pick the quoted literal in ``task`` that belongs to ``target``.

    One literal: it is the value. Several: the one whose preceding words share a
    token with the field label (e.g. ``email "a@b.c"`` for the Email field); if
    none binds, return ``None`` rather than guess.
    """
    matches = list(_QUOTE_RE.finditer(task))
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0].group(1).strip() or None
    label = _tokens(target.label) | _tokens(target.input_type or "")
    best: tuple[int, str] | None = None
    for m in matches:
        before = task[max(0, m.start() - 60) : m.start()]
        score = len(_tokens(before) & label)
        if score and (best is None or score > best[0]):
            best = (score, m.group(1).strip())
    return best[1] if best else None


class TextHelper:
    """OpenAI-compatible chat helper with a strict {"text": ...} contract."""

    def __init__(self, base_url: str, api_key: str, model: str, *, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._cache: dict[tuple[str, str, str], str | None] = {}

    @staticmethod
    def parse_field_text(raw: str) -> str | None:
        """Accept only a JSON object with a single string ``text`` field, ≤ MAX_TEXT_CHARS."""
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict) or set(obj) != {"text"} or not isinstance(obj["text"], str):
            return None
        text = obj["text"]
        if not text.strip() or len(text) > MAX_TEXT_CHARS:
            return None
        return text

    def _prompt(self, task: str, target: Candidate, menu: Menu) -> list[dict[str, str]]:
        ctx = {
            "task": task,
            "page": {"url": menu.url, "title": menu.title},
            "field": target.to_state(),
            "options": list(target.options) if target.options else None,
        }
        return [
            {
                "role": "system",
                "content": 'You write the exact text to enter into one form field. Reply with JSON only: {"text": "..."}. '
                "If the field is a dropdown, text must be one of options verbatim. No explanation.",
            },
            {"role": "user", "content": json.dumps(ctx, ensure_ascii=False)},
        ]

    async def compose(self, task: str, target: Candidate, menu: Menu) -> str | None:
        key = (task, json.dumps(target.to_state(), sort_keys=True), menu.url)
        if key in self._cache:
            return self._cache[key]
        import httpx

        body = {"model": self.model, "messages": self._prompt(task, target, menu), "temperature": 0, "max_tokens": 600}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=body,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                r.raise_for_status()
                raw = r.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001 - any helper failure fails closed
            log.warning("text helper failed: %s", exc)
            self._cache[key] = None
            return None
        text = self.parse_field_text(raw.strip())
        if text is not None and target.options and text not in target.options:
            log.warning("helper returned %r, not one of the select options", text)
            text = None
        self._cache[key] = text
        return text


@dataclass
class TextSource:
    """The composed policy: literal, then secret placeholder, then helper, else None."""

    helper: HelperFn | None = None
    secret_placeholder: SecretPlaceholder | None = None
    calls: dict[str, int] = field(default_factory=lambda: {"literal": 0, "secret": 0, "helper": 0, "none": 0})

    async def compose(self, task: str, target: Candidate, menu: Menu) -> str | None:
        if self.secret_placeholder is not None:
            ph = self.secret_placeholder(target)
            if ph is not None:
                self.calls["secret"] += 1
                return ph
        if target.input_type != "password":
            lit = literal_from_task(task, target)
            if lit is not None and (not target.options or lit in target.options):
                self.calls["literal"] += 1
                return lit
        if self.helper is not None and target.input_type != "password":
            text = await self.helper(task, target, menu)
            if text is not None:
                self.calls["helper"] += 1
                return text
        self.calls["none"] += 1
        return None


def as_sync_literal_source(task: str, target: Candidate, menu: Menu) -> str | None:
    """Drop-in for JevS1.text_source until the wrapper takes async sources."""
    if target.input_type == "password":
        return None
    return literal_from_task(task, target)


def helper_from_env() -> TextHelper | None:
    """JEVDUAL_TEXT_BASE_URL, JEVDUAL_TEXT_API_KEY, JEVDUAL_TEXT_MODEL; None if unset."""
    import os

    base, key, model = (os.environ.get(k) for k in ("JEVDUAL_TEXT_BASE_URL", "JEVDUAL_TEXT_API_KEY", "JEVDUAL_TEXT_MODEL"))
    if not (base and key and model):
        return None
    return TextHelper(base, key, model)


__all__: list[Any] = ["MAX_TEXT_CHARS", "TextHelper", "TextSource", "as_sync_literal_source", "helper_from_env", "literal_from_task"]
