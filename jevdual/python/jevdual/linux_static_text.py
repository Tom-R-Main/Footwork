"""Passive display-text projection from the pinned Linux CUA tree renderer.

Source: CUA d5373879, platform-linux/src/atspi/native.rs, render (2195-2202)
and is_passive_role (5195-5200), inside vendor/cua-driver/native-source.tar.gz.
Visible unindexed nodes are rendered as `- ROLE = "NAME"`; indexed controls
use a different grammar. Text-like passive roles alone are retained here.

The renderer does not escape names: quotes/newlines can be ambiguous and its
Text reads are capped at 4096 characters. This is a bounded display preview,
never exact text, completeness proof, an action target, or a document identity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MAX_INPUT = 1_048_576
_MAX_RECORD = 65536
_START = re.compile(r'^(?P<indent> *)- (?:\[\d+\] )?(?P<role>[A-Za-z][A-Za-z -]*?) (?:= )?"')
_PASSIVE = re.compile(
    r'^ *- (?P<role>label|static|static text|paragraph|heading) = "(?P<text>[^"]*)"$',
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class StaticTextProjection:
    lines: tuple[str, ...]
    input_truncated: bool
    output_truncated: bool
    ambiguous_records: int
    preview_only: bool = True


def project_static_text(tree_markdown: str | None, *, max_chars: int = 6000) -> StaticTextProjection:
    """Return passive text and limits; joined output including separators fits max_chars.

    Labels are retained only in the passive `label = "..."` form, not an
    action's label, a field value, description, image alt text or frame title.
    Newline-containing records stay together; their inner lines are not parsed
    as independent accessibility nodes. Password-role subtrees are omitted.
    """
    if type(max_chars) is not int or not 0 <= max_chars <= 65536:
        raise ValueError("max_chars must be an integer between 0 and 65536")
    if tree_markdown is None:
        tree_markdown = ""
    if not isinstance(tree_markdown, str):
        raise TypeError("tree_markdown must be text or None")
    input_truncated = len(tree_markdown) > _MAX_INPUT
    source = tree_markdown[:_MAX_INPUT]
    lines: list[str] = []
    length = 0
    ambiguous = 0
    output_truncated = False
    password_depth: int | None = None
    record: list[str] = []
    record_chars = 0
    quote_parity = 0
    role = ""
    depth = 0

    for physical in source.splitlines(keepends=True):
        if not record:
            match = _START.match(physical)
            if match is None:
                if physical.strip():
                    ambiguous += 1
                continue
            depth = len(match["indent"])
            role = match["role"].casefold()
            if depth % 2:
                ambiguous += 1
                continue
            if password_depth is not None and depth <= password_depth:
                password_depth = None
            if "password" in role or role == "secure text":
                password_depth = depth
            record_chars = 0
            quote_parity = 0
        record_chars += len(physical)
        quote_parity ^= physical.count('"') % 2
        record.append(physical if record_chars <= _MAX_RECORD else "")
        if quote_parity:
            continue
        # A source cut in the middle of a record must not appear as complete text.
        if input_truncated and not physical.endswith(("\n", "\r")):
            ambiguous += 1
            record = []
            break
        rendered = "".join(record).rstrip("\r\n")
        record = []
        if record_chars > _MAX_RECORD:
            ambiguous += 1
            continue
        if password_depth is not None:
            continue
        match = _PASSIVE.fullmatch(rendered)
        if match is None:
            if role in {"label", "static", "static text", "paragraph", "heading"}:
                ambiguous += 1
            continue
        text = match["text"]
        if not text.strip():
            continue
        # No unescaping or normalization: the producer supplied literal names.
        separator = 1 if lines else 0
        remaining = max_chars - length - separator
        if remaining <= 0:
            output_truncated = True
            continue
        if len(text) > remaining:
            text = text[:remaining]
            output_truncated = True
        lines.append(text)
        length += separator + len(text)
    if record:
        ambiguous += 1
    return StaticTextProjection(tuple(lines), input_truncated, output_truncated, ambiguous)


def static_text(tree_markdown: str | None, *, max_chars: int = 6000) -> list[str]:
    """Convenience preview; use project_static_text when recording coverage limits."""
    return list(project_static_text(tree_markdown, max_chars=max_chars).lines)
