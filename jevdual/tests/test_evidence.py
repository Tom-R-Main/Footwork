import asyncio
import json

from jevdual.evidence import EvidenceSelector, register_find_evidence, render_packet, segment_text
from typesafe_sdk import SystemOneResponse


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def system_one(self, state, questions, *, model=None, **kwargs):
        self.calls.append({"state": state, "questions": questions})
        return self.responses.pop(0)


def _resp(choice: str, probs: dict, present: float) -> SystemOneResponse:
    return SystemOneResponse.model_validate(
        json.loads(
            json.dumps(
                {
                    "model": "jev-1.13.0",
                    "usage": {"input_tokens": 500, "output_tokens": 0},
                    "answers": {
                        "segment": {
                            "type": "choice",
                            "choice": choice,
                            "confidence": 0.8,
                            "probabilities": probs,
                        },
                        "answer_present": {"type": "noul", "noul": present},
                    },
                }
            )
        )
    )


PAGE = (
    ("Built-in exceptions. " * 20)
    + "exception KeyError Raised when a mapping (dictionary) key is not found. "
    + ("More text here. " * 30)
)


def test_segments_cover_the_page_in_order():
    segs = segment_text(PAGE, chars=120)
    assert segs[0].start == 0 and all(segs[i].start < segs[i + 1].start for i in range(len(segs) - 1))
    assert "".join(s.text for s in segs).replace(" ", "") == PAGE.replace(" ", "")


def test_select_returns_top_spans_and_answer_presence_in_one_call():
    segs = segment_text(PAGE)
    hit = next(s for s in segs if "KeyError" in s.text)
    client = FakeClient(
        _resp(str(hit.id), {str(hit.id): 0.85, str(segs[0].id): 0.10, str(segs[-1].id): 0.05}, 0.93)
    )
    sel = EvidenceSelector(client)
    packet = asyncio.run(
        sel.select(
            "Which exception is raised when a dictionary key is not found?", "http://s/exceptions", PAGE
        )
    )
    assert sel.calls == 1 and packet["answer_present"] == 0.93
    assert (
        packet["spans"][0]["id"] == hit.id
        and "KeyError" in packet["spans"][0]["text"]
        and packet["spans"][0]["start"] == hit.start
    )
    assert len(packet["spans"]) == 3
    state = client.calls[0]["state"]
    assert state["segments"][hit.id]["text"] == hit.text and "answer_present" in client.calls[0]["questions"]
    text = render_packet(packet)
    assert "KeyError" in text and "p=0.85" in text


def test_find_evidence_tool_returns_a_packet_and_counts_calls():
    from browser_use import Tools

    segs = segment_text(PAGE)
    hit = next(s for s in segs if "KeyError" in s.text)
    client = FakeClient(_resp(str(hit.id), {str(hit.id): 0.9}, 0.9))
    sel = EvidenceSelector(client)
    tools = Tools()

    async def page_text():
        return "http://s/exceptions", PAGE

    seen = []
    register_find_evidence(tools, sel, page_text, task=lambda: "find the exception", on_call=seen.append)
    assert "find_evidence" in tools.registry.registry.actions
    result = asyncio.run(
        tools.registry.execute_action("find_evidence", {"question": "which exception for a missing key?"})
    )
    assert result.error is None and "KeyError" in (result.extracted_content or "")
    assert sel.calls == 1 and seen and seen[0]["url"] == "http://s/exceptions"
    assert client.calls[0]["state"]["task"] == "find the exception"
