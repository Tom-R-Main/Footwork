"""Evidence selection for System 2 (Q9, reading assistance).

``find_evidence(question)`` is a tool System 2 can call on a page. Jev selects the page segments
that answer the question (one Choice over segment ids, top three by probability) and judges whether
an answer is present at all (one Noul), in a single request. System 2 receives a compact,
source-linked packet (URL, segment ids, character offsets, exact text) and does the synthesis.
Modelled on TypeSafe's line-by-line search cookbook (select line ids plus a separate
answer-existence judgment). Long pages are handled in two stages: a Choice over groups of segments,
then over the segments of the chosen group.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from browser_use.agent.views import ActionResult
from pydantic import BaseModel, Field
from typesafe_sdk import Choice, Noul

from jevdual.policy import JEV_MODEL, PolicyError

log = logging.getLogger("jevdual.evidence")

SEGMENT_CHARS = 350
MAX_OPTIONS = 200
TOP_K = 3


@dataclass(frozen=True)
class Segment:
    id: int
    start: int
    text: str


def segment_text(full_text: str, chars: int = SEGMENT_CHARS) -> list[Segment]:
    """Split visible text into segments of about ``chars`` characters on sentence-ish boundaries."""
    out: list[Segment] = []
    pos = 0
    n = len(full_text)
    sid = 0
    while pos < n:
        end = min(n, pos + chars)
        if end < n:
            cut = max(full_text.rfind(". ", pos + chars // 2, end), full_text.rfind("\n", pos + chars // 2, end))
            if cut > pos:
                end = cut + 1
        text = full_text[pos:end].strip()
        if text:
            out.append(Segment(sid, pos, text))
            sid += 1
        pos = end
    return out


def _choice_probs(answer: Any) -> dict[str, float]:
    probs = getattr(answer, "probabilities", None) or {}
    if not probs and getattr(answer, "choice", None) is not None:
        probs = {str(answer.choice): float(getattr(answer, "confidence", 1.0) or 1.0)}
    return {str(k): float(v) for k, v in probs.items()}


class EvidenceSelector:
    def __init__(self, client: Any, *, model: str = JEV_MODEL):
        self.client = client
        self.model = model
        self.calls = 0

    async def _ask(self, state: dict[str, Any], questions: dict[str, Any]) -> Any:
        self.calls += 1
        try:
            return await self.client.system_one(state, questions, model=self.model)
        except Exception as exc:
            raise PolicyError(f"evidence selection failed: {type(exc).__name__}: {exc}") from exc

    async def select(self, question: str, url: str, full_text: str, task: str | None = None) -> dict[str, Any]:
        segments = segment_text(full_text)
        if not segments:
            return {"url": url, "answer_present": 0.0, "spans": [], "note": "empty page"}
        candidates = segments
        if len(segments) > MAX_OPTIONS:
            group_size = (len(segments) + MAX_OPTIONS - 1) // MAX_OPTIONS
            groups = [segments[i : i + group_size] for i in range(0, len(segments), group_size)]
            gstate = {
                "question": question,
                "page": {"url": url},
                "groups": [{"id": gi, "preview": " ".join(s.text[:60] for s in g[:3])} for gi, g in enumerate(groups)],
            }
            gq = {
                "group": Choice(
                    instructions={"question": "Which group of page segments most likely contains the answer to `question`?"},
                    criteria={str(gi): f"group {gi}" for gi in range(len(groups))},
                )
            }
            resp = await self._ask(gstate, gq)
            ans = resp.choices.get("group")
            if ans is None:
                raise PolicyError("evidence selection answer missing `group`")
            candidates = groups[int(ans.choice)]
        state = {
            "question": question,
            "page": {"url": url},
            "segments": [{"id": s.id, "text": s.text} for s in candidates],
        }
        if task:
            state["task"] = task
        questions = {
            "segment": Choice(
                instructions={
                    "question": "Which segment in `segments` best answers `question`?",
                    "rules": ["Choose the segment whose own text states the answer; a segment that only mentions the topic is not it."],
                },
                criteria={str(s.id): f"segment {s.id}" for s in candidates},
            ),
            "answer_present": Noul(
                instructions="Does any segment in `segments` state the answer to `question`?",
                criteria={
                    "true": "At least one segment's text contains the information the question asks for.",
                    "false": "No segment states it; the page only refers to the topic, or the answer is elsewhere.",
                },
            ),
        }
        resp = await self._ask(state, questions)
        seg_ans = resp.choices.get("segment")
        if seg_ans is None or "answer_present" not in resp.nouls:
            raise PolicyError("evidence selection answer missing `segment` or `answer_present`")
        probs = _choice_probs(seg_ans)
        by_id = {s.id: s for s in candidates}
        ranked = sorted(((p, int(k)) for k, p in probs.items() if k.isdigit() and int(k) in by_id), reverse=True)[:TOP_K]
        spans = [{"id": sid, "p": round(p, 3), "start": by_id[sid].start, "end": by_id[sid].start + len(by_id[sid].text), "text": by_id[sid].text} for p, sid in ranked]
        return {"url": url, "answer_present": round(resp.nouls["answer_present"].noul, 3), "spans": spans, "segments": len(segments)}


def render_packet(packet: dict[str, Any]) -> str:
    lines = [f"Evidence from {packet['url']} (answer present p={packet.get('answer_present', 0):.2f}; {packet.get('segments', 0)} segments scanned):"]
    for sp in packet.get("spans", []):
        lines.append(f"- [segment {sp['id']}, chars {sp['start']}-{sp['end']}, p={sp['p']:.2f}] {sp['text']}")
    if not packet.get("spans"):
        lines.append("- no segment selected")
    lines.append("Quote from these spans; if none answers the question, say so or look elsewhere.")
    return "\n".join(lines)


class EvidenceParams(BaseModel):
    question: str = Field(description="The specific question the current page should answer, e.g. 'Which module provides lru_cache?'")


def register_find_evidence(
    tools: Any,
    selector: EvidenceSelector,
    page_text: Callable[[], Awaitable[tuple[str, str]]],
    *,
    task: Callable[[], str | None] | None = None,
    on_call: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """Register ``find_evidence`` on a Tools registry. ``page_text`` returns (url, redacted full text)."""

    @tools.action(
        "Find the passages on the current page that answer a specific question. A fast reader scans the whole page "
        "(including parts not shown to you) and returns the best-matching spans with their exact text and positions, "
        "plus whether an answer is present at all. Use it before answering a read question on a long page; then quote "
        "from the returned spans. Do not use it to act on the page.",
        param_model=EvidenceParams,
    )
    async def find_evidence(params: EvidenceParams) -> ActionResult:
        try:
            url, text = await page_text()
            packet = await selector.select(params.question, url, text, task() if task else None)
        except PolicyError as exc:
            return ActionResult(error=str(exc))
        if on_call is not None:
            on_call(packet)
        log.info("find_evidence: %r -> %s span(s), answer_present=%.2f", params.question[:60], len(packet["spans"]), packet["answer_present"])
        return ActionResult(extracted_content=render_packet(packet), include_in_memory=True)


_WS = re.compile(r"\s+")
