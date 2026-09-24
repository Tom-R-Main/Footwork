"""Native completion predicates evaluated against observed end state, never a model's opinion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from evals.native.schema import NativePredicate, parse_expect


@dataclass(frozen=True)
class NativeEndState:
    window_text: str
    answer: str | None
    clicked_labels: tuple[str, ...] = ()
    is_done: bool = False
    tmp: Path | None = None
    #: result of the Driver ``verify_state`` call for ``expect`` predicates: satisfied / unsatisfied / unknown
    expect_status: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


def _norm(s: str | None) -> str:
    return " ".join((s or "").split()).casefold()


def resolve_path(path: str, tmp: Path | None) -> Path:
    return Path(path.replace("{tmp}", str(tmp) if tmp is not None else ""))


def evaluate(pred: NativePredicate, end: NativeEndState) -> bool:
    kind, value = pred.kind, pred.value
    if kind == "window_text_contains":
        return _norm(value) in _norm(end.window_text)
    if kind == "answer_contains":
        return _norm(value) in _norm(end.answer)
    if kind == "answer_equals":
        return _norm(value) == _norm(end.answer)
    if kind == "file_contains":
        p = resolve_path(pred.path or "", end.tmp)
        try:
            return _norm(value) in _norm(p.read_text(errors="replace"))
        except OSError:
            return False
    if kind == "file_equals":
        p = resolve_path(pred.path or "", end.tmp)
        try:
            got = p.read_text(errors="replace")
        except OSError:
            return False
        norm = lambda t: "\n".join(ln.rstrip() for ln in t.replace("\r\n", "\n").split("\n")).strip("\n")
        return norm(got) == norm(value.replace("\\n", "\n"))
    if kind == "file_exists":
        p = resolve_path(pred.path or "", end.tmp)
        return p.exists() == (value.strip().lower() == "true")
    if kind == "not_clicked":
        hit = any(_norm(value) in _norm(label) for label in end.clicked_labels)
        return not hit and not end.is_done
    if kind == "expect":
        parse_expect(value)  # validates the shape even when the runner did not evaluate it
        return end.expect_status == "satisfied"
    raise ValueError(f"unknown predicate kind {kind!r}")
