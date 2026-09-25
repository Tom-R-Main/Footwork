"""Q12: one receipt per action (jevdual.receipts), its three deliveries, and the burden views."""

from __future__ import annotations

import json
from types import SimpleNamespace

from jevdual.effects import Effect
from jevdual.ledger import trajectory_from_agent
from jevdual.receipts import (
    EFFECT_WORDS,
    Receipt,
    action_lines,
    receipt_from_effect,
    receipt_from_native,
    receipt_text,
)


def _effect(**kw) -> Effect:
    base = {
        "url_changed": False,
        "title_changed": False,
        "added": 0,
        "removed": 0,
        "changed": 0,
        "text_ratio": 1.0,
        "dialog_changed": False,
        "tabs_changed": False,
        "summary": "",
    }
    base.update(kw)
    return Effect(**base)


def test_noop_navigation_partial_and_refused_read_from_the_effect():
    noop = receipt_from_effect(
        3, ("click(button 'Add to cart')",), _effect(), url_after="https://s/inventory.html"
    )
    assert noop.effect == "suspected_noop" and noop.no_effect
    assert "same URL /inventory.html" in noop.evidence and "text unchanged" in noop.evidence
    nav = receipt_from_effect(
        4, ("click(a 'Cart')",), _effect(url_changed=True, added=5), url_after="https://s/cart.html"
    )
    assert (
        nav.effect == "confirmed"
        and "navigated to /cart.html" in nav.evidence
        and "5 elements added" in nav.evidence
    )
    part = receipt_from_effect(5, ("input(x)", "click(y)"), _effect(changed=1), error="Element not found")
    assert part.effect == "partial" and "one action failed" in part.evidence
    ref = receipt_from_effect(6, ("click(z)",), _effect(), error="refused by gate")
    assert ref.effect == "refused" and "page unchanged" in ref.evidence
    text_only = receipt_from_effect(7, ("scroll()",), _effect(text_ratio=0.5))
    assert text_only.effect == "confirmed" and "text changed" in text_only.evidence
    for r in (noop, nav, part, ref):
        assert r.effect in EFFECT_WORDS


def test_receipt_text_states_facts_only():
    r = receipt_from_effect(
        1, ("click(button 'Add to cart')",), _effect(), url_after="https://s/inventory.html"
    )
    t = receipt_text(r)
    assert t.startswith("Receipt for click(button 'Add to cart'): suspected no-op (")
    for advice in ("should", "try", "instead", "do not"):
        assert advice not in t.lower()


def test_native_effect_wraps_into_the_same_shape():
    native = SimpleNamespace(
        operation="hotkey",
        label="save",
        effect="unverifiable",
        evidence=(),
        summary="no readback",
        error_code=None,
    )
    r = receipt_from_native(2, native)
    assert r.effect == "unverifiable" and r.actions == ("hotkey(save)",) and r.evidence == "no readback"
    odd = receipt_from_native(
        3,
        SimpleNamespace(
            operation="click", label="6", effect="weird", evidence=("x",), summary="", error_code="E"
        ),
    )
    assert odd.effect == "unverifiable" and odd.error == "E"


def test_action_lines_name_the_element_from_the_pre_step_selector_map():
    el = SimpleNamespace(node_name="BUTTON", attributes={"name": "add-to-cart"}, node_value="")
    state = SimpleNamespace(dom_state=SimpleNamespace(selector_map={5: el}))
    acts = [
        {"click_element_by_index": {"index": 5}},
        {"input_text": {"index": 9, "text": "Ada"}},
        {"navigate": {"url": "https://x/y"}},
        {"wait": {"seconds": 1}},
    ]
    assert action_lines(acts, state) == (
        "click_element_by_index(button name='add-to-cart')",
        "input_text(Ada)",
        "navigate(https://x/y)",
        "wait()",
    )


def _agent(mode: str, receipt: Receipt):
    action = SimpleNamespace(model_dump=lambda exclude_unset=True: {"click": {"index": 1}})
    h = SimpleNamespace(
        model_output=SimpleNamespace(action=[action], memory="m"),
        state=SimpleNamespace(url="https://s/inventory.html", interacted_element=[None]),
        result=[],
    )
    return SimpleNamespace(history=SimpleNamespace(history=[h]), receipts={1: receipt}, receipts_mode=mode)


def test_trajectory_line_carries_the_receipt_only_when_delivered():
    r = receipt_from_effect(1, ("click(x)",), _effect(), url_after="https://s/inventory.html")
    delivered = trajectory_from_agent(_agent("deliver", r))
    assert delivered[0]["actions"] == ["click(index=1) -> suspected_noop"]
    assert delivered[0]["effect"].startswith("no change")
    recorded = trajectory_from_agent(_agent("record", r))
    assert recorded[0]["actions"] == ["click(index=1)"] and "effect" not in recorded[0]


def test_runner_arm_sets_and_agent_mode_validation():
    from evals.runner import ARMS, GUARDED_ARMS, POLICY_ARMS, RECEIPT_ARMS, S2_ARMS

    assert "guarded_receipts" in ARMS and "guarded_receipts" in S2_ARMS and "guarded_receipts" in GUARDED_ARMS
    assert RECEIPT_ARMS == ("guarded_receipts",) and set(ARMS) - set(POLICY_ARMS) == {"stock", "scripted"}
    from jevdual.agent import DualProcessAgent

    try:
        DualProcessAgent.__init__(SimpleNamespace(), receipts="loud")  # type: ignore[arg-type]
    except (ValueError, TypeError) as exc:
        assert "receipts" in str(exc) or isinstance(exc, TypeError)


def test_burden_views(tmp_path):
    from evals.burden import by_mode, per_progress, progress_rows, render

    rows = []
    for arm, mode, req, cps, passed in (
        ("guarded", "paused", 6, 1, False),
        ("guarded", "done_claimed", 8, 2, True),
        ("guarded_receipts", "done_stopped", 9, 2, False),
        ("guarded_receipts", "done_claimed", 8, 2, True),
    ):
        rows.append(
            {
                "task_id": "t1" if mode in ("paused", "done_stopped") else "t2",
                "arm": arm,
                "terminal_mode": mode,
                "llm_requests": req,
                "checkpoints_reached": cps,
                "passed": passed,
                "success": passed or None,
            }
        )
    (tmp_path / "results.json").write_text(json.dumps(rows))
    modes = by_mode(rows)
    assert (
        modes["guarded"]["paused"]["runs"] == 1
        and modes["guarded_receipts"]["done_stopped"]["mean_requests"] == 9
    )
    p = per_progress(progress_rows(rows, "guarded"), progress_rows(rows, "guarded_receipts"))
    # t1: guarded 6 req / 1 progress = 6.0; receipts 9 / 2 = 4.5. t2: 8/3 both.
    assert p["tasks"] == 2 and abs(p["mean_diff"] - (-0.75)) < 1e-9
    out = render(rows, "guarded")
    assert "paused" in out and "requests per progress" in out
