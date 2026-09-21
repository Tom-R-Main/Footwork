"""Completion predicates evaluated against the end state of a run, never against a model's opinion."""

from __future__ import annotations

from dataclasses import dataclass, field

from evals.tasks.schema import Predicate


@dataclass(frozen=True)
class EndState:
    final_url: str | None
    page_text: str
    answer: str | None
    visited_urls: tuple[str, ...] = field(default_factory=tuple)
    is_done: bool = False
    success: bool | None = None


def _norm(s: str | None) -> str:
    return " ".join((s or "").split()).casefold()


def evaluate(pred: Predicate, end: EndState) -> bool:
    kind, value = pred.kind, pred.value
    if kind == "url_contains":
        return value in (end.final_url or "")
    if kind == "page_text_contains":
        return _norm(value) in _norm(end.page_text)
    if kind == "answer_contains":
        return _norm(value) in _norm(end.answer)
    if kind == "answer_equals":
        return _norm(value) == _norm(end.answer)
    if kind == "not_reached":
        return not any(value in (u or "") for u in end.visited_urls) and value not in (end.final_url or "")
    raise ValueError(f"unknown predicate kind {kind!r}")
