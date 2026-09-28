"""The cross-surface loop (jevdual.crossloop) with a scripted model and a fake footwork."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from jevdual import crossloop
from jevdual.crossloop import CrossLoop, Surface


def _chat(*replies):
    queue = list(replies)

    async def chat(messages):
        chat.seen.append(messages)
        r = queue.pop(0)
        return SimpleNamespace(
            content=r if isinstance(r, str) else json.dumps(r), input_tokens=10, output_tokens=5
        )

    chat.seen = []
    return chat


def _fake_footwork(tmp_path, responses):
    calls = []

    def fw(session, *argv):
        calls.append((session.name, argv))
        if argv[0] == "read":
            (session).mkdir(parents=True, exist_ok=True)
            (session / "carries.json").write_text(json.dumps({argv[-1]: {"text": "624"}}))
        return responses.get(argv[0], (0, "receipt: Receipt for x: confirmed (changed)"))

    fw.calls = calls
    return fw


def _loop(tmp_path, chat, **kw):
    surfaces = [Surface("calc", "app", app="Calculator"), Surface("web", "browser", url="http://x/form.html")]
    return CrossLoop("Send 48 times 13 through the form", surfaces, chat, tmp_path, **kw)


def act(name, **kw):
    return {"note": "n", "action": {"name": name, **kw}}


def test_a_carried_value_is_typed_from_the_surface_that_read_it(tmp_path, monkeypatch):
    fw = _fake_footwork(tmp_path, {"done": (0, "verifier: accept\naccepted. session closed.")})
    monkeypatch.setattr(crossloop, "footwork", fw)
    chat = _chat(
        act("read", surface="calc", match=r"(\d+)", **{"as": "result"}),
        act("do", surface="web", op="type", target="Message", text="@result"),
        act("done", surface="web", answer="sent 624"),
    )
    run = asyncio.run(_loop(tmp_path, chat).run())
    assert run.status == "done" and run.answer == "sent 624"
    typed = next(argv for s, argv in fw.calls if argv[:2] == ("do", "type"))
    assert typed[-2] == "--from" and typed[-1].endswith("/calc")
    assert "CARRIED VALUES: @result = '624' (from surface calc)" in chat.seen[1][1]["content"]


def test_a_pause_ends_the_run_and_the_model_cannot_grant(tmp_path, monkeypatch):
    fw = _fake_footwork(
        tmp_path, {"do": (3, "paused before dispatch: keyword 'send' on click 'Send message'")}
    )
    monkeypatch.setattr(crossloop, "footwork", fw)
    chat = _chat(act("do", surface="web", op="click", target="Send message"))
    run = asyncio.run(_loop(tmp_path, chat).run())
    assert run.status == "paused" and "keyword 'send'" in run.reason
    assert not any(argv[0] == "grant" for _, argv in fw.calls)


def test_unreadable_replies_and_unknown_surfaces_are_fed_back_not_run(tmp_path, monkeypatch):
    fw = _fake_footwork(tmp_path, {})
    monkeypatch.setattr(crossloop, "footwork", fw)
    chat = _chat("I think I should click", act("look", surface="nowhere"), act("stop", reason="no route"))
    loop = _loop(tmp_path, chat)
    run = asyncio.run(loop.run())
    assert run.status == "stopped" and run.reason == "no route"
    assert not any(argv[0] == "look" for _, argv in fw.calls)
    assert "could not be read" in loop.history[0] and "no surface named 'nowhere'" in loop.history[1]


def test_refused_dones_end_unverified_after_the_budget(tmp_path, monkeypatch):
    fw = _fake_footwork(tmp_path, {"done": (5, "verifier: verify: answer carries no fact")})
    monkeypatch.setattr(crossloop, "footwork", fw)
    chat = _chat(*[act("done", surface="web", answer="x")] * 3)
    run = asyncio.run(_loop(tmp_path, chat, max_done_refusals=2).run())
    assert run.status == "done_unverified"


def test_a_carried_reference_in_a_done_answer_is_its_value(tmp_path, monkeypatch):
    fw = _fake_footwork(tmp_path, {"done": (0, "accepted. session closed.")})
    monkeypatch.setattr(crossloop, "footwork", fw)
    chat = _chat(
        act("read", surface="calc", match=r"(\d+)", **{"as": "result"}),
        act("done", surface="web", answer="sent @result"),
    )
    asyncio.run(_loop(tmp_path, chat).run())
    done = next(argv for _, argv in fw.calls if argv[0] == "done")
    assert done[:2] == ("done", "sent 624")
    # the verifier gets the other surface's receipts and carries (V4)
    assert done[2] == "--context-from" and done[3].endswith("/calc")


def test_per_surface_requirements_are_judged_where_they_are_observable(tmp_path, monkeypatch):
    verdicts = {"calc": (0, "verifier: accept"), "web": (5, "verifier: reject (Message sent unmet)")}
    calls = []

    def fw(session, *argv):
        calls.append((session.name, argv))
        if argv[0] == "done":
            return verdicts[session.name]
        return (0, "receipt: confirmed")

    monkeypatch.setattr(crossloop, "footwork", fw)
    surfaces = [
        Surface("calc", "app", app="Calculator", requirements=("The product is shown",)),
        Surface("web", "browser", url="http://x", requirements=("The message was sent",)),
    ]
    chat = _chat(*[act("done", surface="web", answer="sent 624")] * 3)
    run = asyncio.run(CrossLoop("t", surfaces, chat, tmp_path, max_done_refusals=2).run())
    judged = [s for s, argv in calls if argv[0] == "done"]
    assert judged[:2] == ["calc", "web"] and run.status == "done_unverified"
    starts = {s: argv for s, argv in calls if argv[0] == "start"}
    assert starts["calc"][starts["calc"].index("--require") + 1] == "The product is shown"
    verdicts["web"] = (0, "verifier: accept")
    run = asyncio.run(CrossLoop("t", surfaces, _chat(act("done", surface="web", answer="x")), tmp_path).run())
    assert run.status == "done"
