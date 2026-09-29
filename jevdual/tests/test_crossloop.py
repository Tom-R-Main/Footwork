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
    run = asyncio.run(_loop(tmp_path, chat).run())
    done = next(argv for _, argv in fw.calls if argv[0] == "done")
    assert done[:2] == ("done", "sent 624")
    # the run records the answer the verifier judged, not the reference (Q19 smoke)
    assert run.answer == "sent 624"
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


# ---- M3: bounded recovery (recovery=True); the frozen loop (recovery=False) is unchanged above


def _stateful_footwork(pages, receipts=()):
    """A fake footwork whose navigate/look write the surface's session.json, so states have signatures."""
    calls = []
    where = {}

    def fw(session, *argv):
        calls.append((session.name, argv))
        session.mkdir(parents=True, exist_ok=True)
        if argv[0] == "start":
            where[session.name] = next(iter(pages))
        if argv[:2] == ("do", "navigate"):
            where[session.name] = argv[2]
        title = where.get(session.name, "")
        (session / "session.json").write_text(
            json.dumps(
                {
                    "last_url": title,
                    "last_title": title,
                    "last_page_text": pages.get(title, ""),
                    "last_candidates": [],
                }
            )
        )
        if receipts and not (session / "session.jsonl").exists():
            (session / "session.jsonl").write_text("\n".join(json.dumps(r) for r in receipts) + "\n")
        return 0, f"Google Chrome (footwork): '{title}'\n0 elements:\npage text:\n{pages.get(title, '')}"

    fw.calls = calls
    return fw


def test_alternating_between_two_pages_ends_as_no_progress_not_the_budget(tmp_path, monkeypatch):
    """Q19 H03: the model alternated between the portal and the site root for 20 steps. With recovery,
    revisiting known states without a new value or effect ends the run, naming the steps."""
    pages = {"http://x/reports": "Status: export unavailable", "http://x/": "Home"}
    monkeypatch.setattr(crossloop, "footwork", _stateful_footwork(pages))
    moves = [act("do", surface="web", op="navigate", text=u) for u in ["http://x/", "http://x/reports"] * 10]
    loop = CrossLoop(
        "Download the report",
        [Surface("web", "browser", url="http://x/reports")],
        _chat(*moves),
        tmp_path,
        recovery=True,
    )
    run = asyncio.run(loop.run())
    assert run.status == "no_progress" and len(run.steps) < 12
    assert "no progress" in run.reason


def test_an_action_already_tried_in_the_same_state_is_not_run_again(tmp_path, monkeypatch):
    fw = _stateful_footwork({"http://x/a": "A"})
    monkeypatch.setattr(crossloop, "footwork", fw)
    chat = _chat(
        act("look", surface="web"), act("look", surface="web"), act("stop", kind="unavailable", reason="gone")
    )
    loop = CrossLoop("t", [Surface("web", "browser", url="http://x/a")], chat, tmp_path, recovery=True)
    run = asyncio.run(loop.run())
    assert sum(1 for _, a in fw.calls if a[0] == "look") == 1  # the second look was refused, not run
    assert run.status == "stopped" and run.reason == "[unavailable] gone"


SUBMITTED = {
    "t": 5.0,
    "step": 2,
    "kind": "receipt",
    "action": {"op": "click", "target_label": "Delete reservation QH-204"},
    "effect": "confirmed",
    "evidence": "navigated to /deleted.html?reservation=QH-204; 0 elements added, 3 removed, 0 changed",
}


def test_an_effect_already_recorded_is_not_repeated(tmp_path, monkeypatch):
    """Q19 H02: after a confirmed deletion the model navigated to the deletion's result address, which
    would have deleted again. The loop refuses both that and a second click on the same control."""
    fw = _stateful_footwork({"http://x/list": "QH-204"}, receipts=[SUBMITTED])
    monkeypatch.setattr(crossloop, "footwork", fw)
    chat = _chat(
        act("do", surface="web", op="navigate", text="http://x/deleted.html?reservation=QH-204"),
        act("do", surface="web", op="click", target="Delete reservation QH-204"),
        act("stop", reason="done already"),
    )
    loop = CrossLoop(
        "Delete QH-204", [Surface("web", "browser", url="http://x/list")], chat, tmp_path, recovery=True
    )
    run = asyncio.run(loop.run())
    sent = [a for _, a in fw.calls if a[0] == "do"]
    assert sent == [] and all("submit again" in s.output for s in run.steps[:2])


def test_a_compact_observation_keeps_its_head_and_trims_the_body():
    from jevdual.crossloop import compact

    head = "note: this observation is incomplete\nreceipt: Receipt for click(Save): confirmed (saved)"
    body = "\n".join(f"  [{i:4}] button 'b{i}'" for i in range(400))
    out = compact(f"{head}\n400 elements:\n{body}\npage text (9000 chars):\n" + "x" * 9000, 2500)
    assert out.startswith(head) and "more elements" in out and "chars more" in out and len(out) < 2700


def test_confirmed_navigations_between_known_pages_are_not_progress(tmp_path, monkeypatch):
    """M3's X1: every navigation's receipt is confirmed, and counting that as an effect kept resetting the
    no-progress streak. Only a new state, value or effect record is progress (M4)."""
    pages = {"http://x/archive": "Status: withdrawn", "http://x/": "Home"}
    fw = _stateful_footwork(pages)

    def confirming(session, *argv):
        code, out = fw(session, *argv)
        return code, "receipt: Receipt for navigate: confirmed (navigated)\n" + out

    monkeypatch.setattr(crossloop, "footwork", confirming)
    # distinct wordings, so the tried-action refusal cannot be what ends it
    moves = [
        act("do", surface="web", op="navigate", text=u, target=f"t{i}")
        for i, u in enumerate(["http://x/", "http://x/archive"] * 10)
    ]
    loop = CrossLoop(
        "Download the archive",
        [Surface("web", "browser", url="http://x/archive")],
        _chat(*moves),
        tmp_path,
        recovery=True,
    )
    run = asyncio.run(loop.run())
    assert run.status == "no_progress" and len(run.steps) <= 10
