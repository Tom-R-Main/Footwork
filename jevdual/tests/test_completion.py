"""Evidence for the requested effect (jevdual.completion, M1): which receipts establish a specific effect,
and which limits stop a record from supporting a claimed value."""

from __future__ import annotations

from jevdual.completion import effects, evidence_values
from jevdual.verify import check_claims


def _receipt(step, op, evidence, t=None, **action):
    return {
        "t": float(t if t is not None else step),
        "step": step,
        "kind": "receipt",
        "action": {"op": op, **action},
        "effect": "confirmed",
        "evidence": evidence,
    }


SUBMIT = _receipt(
    3,
    "click",
    "navigated to /q19h-cutting-done.html?reference=QUIET-83&quantity=27; 0 elements added, 6 removed, 0 changed",
)


def test_a_submission_whose_result_url_carries_its_fields_is_evidence_of_those_values():
    (e,) = effects([SUBMIT])
    assert (e.effect, e.resource, e.kind, e.values) == (
        "submitted",
        "/q19h-cutting-done.html",
        "event",
        ("QUIET-83", "27"),
    )
    assert evidence_values([e]) == ("QUIET-83", "27")


def test_a_generic_confirmation_without_submitted_fields_is_not_evidence():
    nav = _receipt(3, "click", "navigated to /done.html; 0 elements added, 6 removed, 0 changed")
    title = _receipt(4, "click", "title changed; 1 elements added")
    assert effects([nav, title]) == []


def test_a_duplicated_submission_is_limited_and_supports_nothing():
    again = {**SUBMIT, "step": 4, "t": 4.0}
    es = effects([SUBMIT, again])
    assert all("2 submissions" in e.limits[0] for e in es) and evidence_values(es) == ()


def _save(step, path, t=None):
    rb = {"ok": True, "path": path, "detail": f"{path} holds the window's text exactly (48 characters)"}
    return _receipt(step, "hotkey", f"saved: {path} ...", t=t, save_readback=rb)


def test_a_save_readback_of_the_bound_document_is_current_state():
    (e,) = effects([_save(2, "/s/h06-labels.txt")], document="h06-labels.txt")
    assert (e.effect, e.kind, e.usable) == ("saved", "current_state", True)


def test_a_readback_of_another_document_or_an_edit_after_the_save_is_limited():
    (wrong,) = effects([_save(2, "/s/h06-neighbor.txt")], document="h06-labels.txt")
    assert "not the bound document" in wrong.limits[0]
    edit = _receipt(3, "type", "'text area' now holds 'Batch amber: 4'", t=3)
    stale = next(
        e
        for e in effects([_save(2, "/s/h06-labels.txt", t=2), edit], document="h06-labels.txt")
        if e.effect == "saved"
    )
    assert "edited again after this save" in stale.limits[0]


def test_carried_reads_are_answer_provenance():
    carries = {
        "QTY": {
            "text": "27",
            "location": "app://TextEdit",
            "step": 0,
            "taken_at": 1.0,
            "occurrence": "match 1 of 1",
        }
    }
    (e,) = effects([], carries=carries)
    assert (e.effect, e.kind, e.values) == ("read", "answer", ("27",))


def test_the_claim_check_counts_evidence_values_absent_from_the_final_page():
    page = "Scratch request recorded\nThe local service has recorded your cutting request."
    (c,) = check_claims("QUIET-83 27", page, strict=True)
    assert not c.supported  # Q19 model H10: refused before M1
    (c,) = check_claims("QUIET-83 27", page, strict=True, evidence=("QUIET-83", "27"))
    assert c.supported and c.source == "evidence"
    # a value no evidence holds is still unsupported, beside one that is
    (c,) = check_claims("QUIET-84 27", page, strict=True, evidence=("QUIET-83", "27"))
    assert not c.supported


def test_the_floor_needs_evidence_for_the_effect_the_task_names():
    """M2: a page saying "recorded" is not evidence; the run's own records must hold the named effect."""
    from jevdual.completion import floor

    (sub,) = effects([SUBMIT])
    assert floor("Submit one cutting request", [sub], answer_bearing=False) is None
    assert (
        floor("Submit one cutting request", [], answer_bearing=False)
        == "no evidence in this run for: submitted"
    )
    (saved,) = effects([_save(2, "/s/a.txt")], document="a.txt")
    assert "saved" in floor("Edit a.txt and save it", [sub], answer_bearing=False)
    assert floor("Edit a.txt and save it", [saved], answer_bearing=False) is None
    assert "only what the page says" in floor("Open the settings page", [], answer_bearing=False)
    # an answer-bearing done is the claim check's; a duplicated event blocks it all the same
    assert floor("Report the height", [], answer_bearing=True) is None
    dup = effects([SUBMIT, {**SUBMIT, "step": 4, "t": 4.0}])
    assert "more than once" in floor("Report the quantity sent", dup, answer_bearing=True)


def test_a_field_readback_is_limited_once_the_page_navigated_away():
    typed = _receipt(2, "type", "'Quantity' now holds '27'", t=2)
    (holds, sub) = effects([typed, SUBMIT])
    assert holds.effect == "field_holds" and "navigated away" in holds.limits[0] and sub.usable


def test_a_repeat_of_a_recorded_submission_is_named():
    """U52: the frozen loop let a model load a sign-up's result address a second time (a GET form
    submits on load); footwork now pauses it, like the loop's reconciliation."""
    from jevdual.completion import repeat_of

    recs = [{**SUBMIT, "action": {"op": "click", "target_label": "Submit cutting request"}}]
    url = "http://127.0.0.1:8768/q19h-cutting-done.html?reference=QUIET-83&quantity=27"
    assert "repeating the submission recorded at step 3" in repeat_of(recs, "navigate", url=url)
    assert repeat_of(recs, "navigate", url=url.replace("27", "28")) is None
    assert "already submitted" in repeat_of(recs, "click", label="Submit cutting request")
    assert repeat_of(recs, "click", label="Cancel") is None
    assert repeat_of([], "navigate", url=url) is None
