"""Evidence for the requested effect (jevdual.completion, M1): which receipts establish a specific effect,
and which limits stop a record from supporting a claimed value."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.completion import Effect, effects, evidence_values, floor
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


def _typed_field(value="27"):
    from jevdual.operator_evidence import fact_record
    from jevdual.session_operations import native_resource

    binding = {"boot": "test", "pid": 77, "start": "start", "window_id": 5}
    resource = native_resource(binding)
    interval = {"start": 1.0, "end": 1.5}
    action = {
        "operation_id": "op_one",
        "binding": binding,
        "observation": "obs_one",
        "execution_interval": interval,
        "target_id": 3,
        "dispatched": True,
    }
    fact = fact_record(
        kind="current_state",
        predicate="field_equals",
        resource=resource,
        binding=binding,
        observation="obs_one",
        started_at=1.0,
        ended_at=1.5,
        values=[value],
        evidence_refs=["execution:op_one"],
        parameters={
            "source": "native.ax_insert_ack",
            "label": "Quantity",
            "target_id": 3,
            "source_target_id": 8,
            "source_observation": "obs_revalidated",
            "matches": True,
        },
    )
    record = _receipt(1, "append", "'Quantity' now holds 'misleading prefix'", **action)
    record["structured_evidence"] = {
        "schema_version": "1",
        "producer": {"name": "footwork.session", "version": 1},
        "session_id": "session_one",
        "operation_id": "op_one",
        "resource": resource,
        "binding": binding,
        "observation": "obs_one",
        "interval": interval,
        "evidence_refs": ["execution:op_one"],
        "facts": [fact],
    }
    return record


def test_structured_exact_value_does_not_use_truncated_prose():
    value = "long field value " * 40
    (item,) = effects([_typed_field(value)])
    assert item.values == (value,) and item.usable
    assert "misleading prefix" not in evidence_values([item])


@pytest.mark.parametrize(
    "mutation", ["version", "operation", "binding", "fact_version", "refs", "empty", "secret"]
)
def test_bad_typed_evidence_never_falls_back_to_plausible_prose(mutation):
    record = _typed_field()
    payload = record["structured_evidence"]
    if mutation == "version":
        payload["producer"]["version"] = True
    elif mutation == "operation":
        payload["operation_id"] = "different_operation"
    elif mutation == "binding":
        payload["binding"] = {**payload["binding"], "pid": 88}
    elif mutation == "fact_version":
        payload["facts"][0]["producer"]["version"] = 999
    elif mutation == "refs":
        payload["facts"][0]["evidence_refs"] = ["execution:other"]
    elif mutation == "empty":
        payload["facts"] = []
    else:
        record["action"]["secret"] = True
    assert effects([record]) == []


def test_later_input_limits_structured_current_state():
    later = _receipt(2, "click", "uncertain edit", dispatched=True)
    later["effect"] = "unverifiable"
    (item,) = effects([_typed_field(), later])
    assert not item.usable and "later input" in item.limits[0]


def test_structured_persistence_is_not_saved_task_proof():
    from jevdual.operator_evidence import fact_record

    record = _typed_field()
    payload = record["structured_evidence"]
    payload["facts"] = [
        fact_record(
            kind="persistence",
            predicate="disk_equals_window",
            resource=payload["resource"],
            binding=payload["binding"],
            observation=payload["observation"],
            started_at=1.0,
            ended_at=1.5,
            evidence_refs=payload["evidence_refs"],
            parameters={"path": "/s/document.txt", "task_postcondition": "not_checked"},
        )
    ]
    (item,) = effects([record])
    assert item.effect == "disk_equals_window" and item.kind == "persistence"
    assert not item.usable and not evidence_values([item])
    assert floor("Save the intended document", [item], answer_bearing=False) is not None


SUBMIT = _receipt(
    3,
    "click",
    "navigated to /q19h-cutting-done.html?reference=QUIET-83&quantity=27; 0 elements added, 6 removed, 0 changed",
)


def test_a_query_result_url_does_not_prove_a_submission_or_its_values():
    assert effects([SUBMIT]) == []
    assert evidence_values(effects([SUBMIT])) == ()


def test_a_generic_confirmation_without_submitted_fields_is_not_evidence():
    nav = _receipt(3, "click", "navigated to /done.html; 0 elements added, 6 removed, 0 changed")
    title = _receipt(4, "click", "title changed; 1 elements added")
    assert effects([nav, title]) == []


def test_repeated_query_navigation_does_not_become_submission_evidence():
    again = {**SUBMIT, "step": 4, "t": 4.0}
    assert effects([SUBMIT, again]) == []


def _event_fixture(*, limits=()):
    """A typed event for floor conformance, without pretending receipt navigation proves it."""
    return Effect("submitted", "/result", "event", 3, 3.0, "qualified event", ("27",), limits)


def test_limited_typed_event_supports_no_value():
    item = _event_fixture(limits=("2 submissions to /result",))
    assert not item.usable and evidence_values([item]) == ()


def _save(step, path, t=None, **action):
    rb = {"ok": True, "path": path, "detail": f"{path} holds the window's text exactly (48 characters)"}
    return _receipt(step, "hotkey", f"saved: {path} ...", t=t, save_readback=rb, **action)


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
    assert "possible edit after this save" in stale.limits[0]


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

    sub = _event_fixture()
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
    dup = [_event_fixture(limits=("2 submissions to /result",))]
    assert "more than once" in floor("Report the quantity sent", dup, answer_bearing=True)


def test_a_field_readback_is_limited_once_the_page_navigated_away():
    typed = _receipt(2, "type", "'Quantity' now holds '27'", t=2)
    (holds,) = effects([typed, SUBMIT])
    assert holds.effect == "field_holds" and "navigated away" in holds.limits[0]


def test_repeating_query_navigation_retains_a_risk_guard_without_submission_authority():
    from jevdual.completion import repeat_of

    recs = [{**SUBMIT, "action": {"op": "click", "target_label": "Submit cutting request"}}]
    url = "http://127.0.0.1:8768/q19h-cutting-done.html?reference=QUIET-83&quantity=27"
    assert "repeating the query navigation recorded at step 3" in repeat_of(recs, "navigate", url=url)
    assert repeat_of(recs, "navigate", url=url.replace("27", "28")) is None
    assert "may submit again" in repeat_of(recs, "click", label="Submit cutting request")
    assert repeat_of(recs, "click", label="Cancel") is None
    assert repeat_of([], "navigate", url=url) is None


def _field_readback(step, value, label="Quantity", t=None, **action):
    """Exercise the session's actual repr receipt producer, not a hand-built quote format."""
    from jevdual.menu import Candidate, Menu
    from jevdual.receipts import Receipt
    from jevdual.session import _field_receipt

    pending = {
        "op": "type",
        "target_label": label,
        "target_id": 1,
        "intended": value,
        "secret": False,
        **action,
    }
    candidate = Candidate(
        id=pending["target_id"], label=label, role="textbox", operations=("type",), value=value
    )
    nm = SimpleNamespace(
        menu=Menu(url="app://doc", title="Document", page_text="", candidates=(candidate,), by_operation={})
    )
    receipt = _field_receipt(Receipt(step, (), "confirmed", "changed"), pending, nm)
    assert receipt.effect == "confirmed"
    return _receipt(step, pending.pop("op"), receipt.evidence, t=t, **pending)


@pytest.mark.parametrize("later_t", [2.0, 1.0, 0.5])
def test_later_same_field_readback_replaces_current_value_in_record_order(later_t):
    old = _field_readback(1, "27", t=1)
    new = _field_readback(2, "28", t=later_t)
    previous, current = effects([old, new])
    assert not previous.usable and "step 2" in previous.limits[0]
    assert current.usable and evidence_values([previous, current]) == ("28",)
    assert not check_claims("27", "", strict=True, evidence=evidence_values([previous, current]))[0].supported
    assert check_claims("28", "", strict=True, evidence=evidence_values([previous, current]))[0].supported


@pytest.mark.parametrize("op", ["type", "append", "enter", "key", "paste"])
@pytest.mark.parametrize("effect", ["partial", "unverifiable"])
def test_potentially_delivered_same_field_mutation_removes_completion_support(op, effect):
    later = _receipt(2, op, "the outcome cannot be confirmed", target_label="Quantity", target_id=1)
    later["effect"] = effect
    items = effects([_field_readback(1, "27"), later])
    assert not items[0].usable and evidence_values(items) == ()
    assert floor("Set the quantity to 27", items, answer_bearing=False) is not None


@pytest.mark.parametrize("driver_effect", ["not sent", "not dispatched", "refused"])
def test_no_send_same_field_mutation_does_not_invalidate_readback(driver_effect):
    later = _receipt(
        2, "type", "not applied", target_label="Quantity", target_id=1, driver_effect=driver_effect
    )
    later["effect"] = "unverifiable"
    (item,) = effects([_field_readback(1, "27"), later])
    assert item.usable


@pytest.mark.parametrize("dispatched", [True, None])
def test_explicit_uncertain_dispatch_overrides_legacy_refusal(dispatched):
    later = _receipt(2, "type", "outcome unknown", driver_effect="refused", dispatched=dispatched)
    later["effect"] = "refused"
    (item,) = effects([_field_readback(1, "27"), later])
    assert not item.usable


def test_refused_same_field_action_retains_readback():
    later = _receipt(2, "type", "not changed", target_label="Quantity", target_id=1)
    later["effect"] = "refused"
    (item,) = effects([_field_readback(1, "27"), later])
    assert item.usable


@pytest.mark.parametrize(
    "action",
    [
        {"target_label": "Quantity", "target_id": 1, "app": "OtherApp"},
        {"target_label": "Quantity", "target_id": 1, "mode": "browser"},
    ],
)
def test_provably_other_surface_mutation_retains_readback(action):
    old = _field_readback(1, "27", app="TextEdit", mode="native")
    later = _receipt(2, "append", "partial field change", **action)
    later["effect"] = "partial"
    (item,) = effects([old, later])
    assert item.usable


def test_legacy_receipt_label_and_metadata_match_without_target_ids():
    old = _receipt(1, "type", "'Quantity' now holds '27'")
    later = _receipt(2, "append", "partial readback", target_label="quantity")
    later["effect"] = "partial"
    (item,) = effects([old, later])
    assert not item.usable


def test_changed_snapshot_id_does_not_prove_matching_label_is_another_field():
    old = _field_readback(1, "27")
    later = _field_readback(2, "28", target_id=2)
    previous, current = effects([old, later])
    assert not previous.usable and current.usable
    assert evidence_values([previous, current]) == ("28",)


@pytest.mark.parametrize("label", ["Quantity", "Other"])
def test_presentation_label_and_id_cannot_prove_a_different_field_incarnation(label):
    old = _field_readback(1, "27", app="TextEdit", mode="native")
    later = _field_readback(2, "28", label=label, target_id=2, app="TextEdit", mode="native")
    previous, current = effects([old, later])
    assert not previous.usable and current.usable
    assert evidence_values([previous, current]) == ("28",)
    assert not check_claims("27", "", strict=True, evidence=evidence_values([previous, current]))[0].supported


def test_unknown_other_field_metadata_cannot_preserve_same_surface_readback():
    old = _field_readback(1, "27", app="TextEdit", mode="native")
    later = _receipt(2, "append", "partial readback", target_label="Other", target_id=2)
    later["effect"] = "partial"
    (previous,) = effects([old, later])
    assert not previous.usable


def test_equal_timestamp_navigation_limits_field_but_preserves_event_and_carry():
    old = _field_readback(1, "27", t=3)
    later = _receipt(4, "type", "changed", target_label="Quantity", target_id=1, t=3)
    later["effect"] = "partial"
    items = effects([old, SUBMIT, later], carries={"QTY": {"text": "27", "step": 0}})
    assert "navigated away" in items[0].limits[0]
    assert items[1].effect == "read" and items[1].usable
    event = _event_fixture()
    assert floor("Submit a request", [*items, event], answer_bearing=False) is None


@pytest.mark.parametrize(
    "value", ["café", "東京 😀", "O'Brien", 'He said "hello"', "both '\" quotes", r"C:\new\test", "a\nb\t "]
)
@pytest.mark.parametrize(
    "label", ["Quantity", "Customer's note", 'Quoted "field"', "both '\" labels", "数量 😀"]
)
def test_actual_receipt_repr_preserves_literal_label_and_value(label, value):
    (item,) = effects([_field_readback(1, value, label)])
    assert item.usable and item.resource == label and item.values == (value,)
    assert item.detail == f"holds {value!r}"


@pytest.mark.parametrize(
    "evidence",
    [
        "'Quantity' now holds 'unterminated",
        "'Quantity' now holds '27' + '28'",
        "'Quantity' now holds '27'garbage",
        "'Quantity' now holds '\\xGG'",
        "'Quantity' now holds '\\q'",
        "'' now holds '27'",
        "'Quantity' now holds " + repr("x" * 16_385),
        "'Quantity' now holds 27",
        "'Quantity' now holds {secret}",
        "'Quantity' now holds __import__('os').getcwd()",
        "page text: 'Quantity' now holds '27'",
    ],
)
def test_malformed_or_nonliteral_receipt_cannot_establish_current_state(evidence):
    items = effects([_receipt(1, "type", evidence)])
    assert evidence_values(items) == ()
    assert floor("Set the quantity to 27", items, answer_bearing=False) is not None


@pytest.mark.parametrize(
    ("effect", "answer", "expected_band"),
    [("confirmed", "27", "verify"), ("confirmed", "28", "accept"), ("unverifiable", None, "verify")],
)
def test_persisted_effects_reach_the_real_verifier_floor_and_claim_check(
    tmp_path, effect, answer, expected_band
):
    from jevdual.completion import session_effects
    from jevdual.menu import Menu
    from jevdual.verify import Verifier, VerifyPolicy
    from typesafe_sdk import SystemOneResponse

    old = _field_readback(1, "27")
    later = _field_readback(2, "28")
    later["effect"] = effect
    (tmp_path / "session.jsonl").write_text("\n".join(json.dumps(r) for r in [old, later]) + "\n")
    items = tuple(session_effects(tmp_path))
    response_path = Path(__file__).parent / "fixtures" / "jev_responses" / "verify_accept.json"

    class Client:
        async def system_one(self, state, questions, **kwargs):
            assert "LIMITED" in state["evidence"][0]
            return SystemOneResponse.model_validate(json.loads(response_path.read_text()))

    verifier = Verifier(Client(), policy=VerifyPolicy(claim_evidence="page_and_fields"))
    menu = Menu(url="app://doc", title="Document", page_text="", candidates=(), by_operation={})
    verdict = asyncio.run(verifier.verify("Set the quantity", (), menu, answer, effects=items))
    assert verdict.band == expected_band
    if answer == "27":
        assert verdict.unsupported_claims == ("27",)
    if effect == "unverifiable":
        assert "no evidence in this run" in verdict.reason


@pytest.mark.parametrize("op", ["type", "append", "enter", "key", "paste"])
@pytest.mark.parametrize("effect", ["unverifiable", "suspected_noop"])
def test_targetless_potential_mutation_cannot_preserve_a_current_field(op, effect):
    later = _receipt(2, op, "outcome unknown")
    later["effect"] = effect
    (item,) = effects([_field_readback(1, "27", app="TextEdit"), later])
    assert not item.usable


def test_targetless_mutation_in_a_known_other_app_preserves_current_field():
    later = _receipt(2, "key", "outcome unknown", app="OtherApp")
    later["effect"] = "unverifiable"
    (item,) = effects([_field_readback(1, "27", app="TextEdit"), later])
    assert item.usable


@pytest.mark.parametrize("label", ["View report", "Submit cutting request"])
def test_query_navigation_cannot_identify_a_submission_even_with_a_submit_label(label):
    report = _receipt(1, "click", "navigated to /report?quantity=27; 0 elements added", target_label=label)
    items = effects([report])
    assert items == [] and evidence_values(items) == ()
    assert floor("Submit one cutting request", items, answer_bearing=False) is not None


@pytest.mark.parametrize("keys", ["cmd+v", "ctrl+v", "control+v"])
def test_actual_hotkey_paste_metadata_invalidates_current_field(keys):
    later = _receipt(2, "hotkey", "no visible change", line=f"hotkey({keys})")
    later["effect"] = "suspected_noop"
    (item,) = effects([_field_readback(1, "27"), later])
    assert not item.usable


def test_save_hotkey_cannot_establish_unchanged_field_without_its_own_readback():
    later = _receipt(2, "hotkey", "saved", line="hotkey(cmd+s)")
    (item,) = effects([_field_readback(1, "27"), later])
    assert not item.usable


def test_repeat_navigation_guard_keeps_known_origin_and_never_establishes_an_event():
    from jevdual.completion import repeat_of

    prior = _receipt(1, "click", "navigated to https://one.test/report?quantity=27")
    assert repeat_of([prior], "navigate", url="https://two.test/report?quantity=27") is None
    assert "may submit again" in repeat_of([prior], "navigate", url="https://one.test/report?quantity=27")
    assert effects([prior]) == []


def test_another_surface_field_containing_navigation_words_does_not_invalidate_current_field():
    old = _field_readback(1, "27")
    old["action"]["app"] = "TextEdit"
    other = _field_readback(2, "navigated to /report", label="Other", target_id=2, app="OtherApp")
    assert all(item.usable for item in effects([old, other]))


def test_navigation_in_another_known_app_does_not_invalidate_current_field():
    old = _field_readback(1, "27", app="TextEdit", mode="native")
    other = _receipt(2, "click", "navigated to /report", app="Chrome", mode="browser")
    (item,) = effects([old, other])
    assert item.usable


@pytest.mark.parametrize("later_t", [2.0, 1.0, 0.5])
def test_save_readback_is_limited_by_later_possible_edit_in_record_order(later_t):
    saved = _save(1, "/s/document.txt", t=1, app="TextEdit", mode="native")
    later = _receipt(2, "type", "outcome unknown", t=later_t, app="TextEdit", mode="native")
    later["effect"] = "unverifiable"
    (item,) = effects([saved, later], document="document.txt")
    assert item.effect == "saved" and item.step == 1 and not item.usable
    assert "step 2" in item.limits[0]
    assert floor("Save document.txt", [item], answer_bearing=False) is not None


@pytest.mark.parametrize("effect", ["unverifiable", "suspected_noop"])
def test_paste_hotkey_limits_prior_save_even_without_observable_change(effect):
    saved = _save(1, "/s/document.txt", app="TextEdit", mode="native")
    later = _receipt(2, "hotkey", "outcome unknown", line="hotkey(cmd+v)")
    later["effect"] = effect
    (item,) = effects([saved, later], document="document.txt")
    assert not item.usable


@pytest.mark.parametrize(
    "action",
    [
        {"app": "OtherApp"},
        {"mode": "browser"},
        {"driver_effect": "not sent"},
        {"driver_effect": "not dispatched"},
        {"driver_effect": "refused"},
        {"dispatched": False},
    ],
)
def test_provably_other_surface_or_no_send_mutation_preserves_prior_save(action):
    saved = _save(1, "/s/document.txt", app="TextEdit", mode="native")
    later = _receipt(2, "type", "outcome unknown", **action)
    later["effect"] = "unverifiable"
    (item,) = effects([saved, later], document="document.txt")
    assert item.usable


def test_refused_mutation_preserves_prior_save():
    saved = _save(1, "/s/document.txt")
    later = _receipt(2, "hotkey", "not applied", line="hotkey(cmd+v)")
    later["effect"] = "refused"
    (item,) = effects([saved, later], document="document.txt")
    assert item.usable


@pytest.mark.parametrize(
    ("op", "action"),
    [
        ("hotkey", {"line": "hotkey(cmd+x)"}),
        ("menu", {"line": "menu(Edit > Cut)"}),
        ("click", {"target_label": "Reset", "target_id": 2}),
        ("unclassified_input", {}),
    ],
)
@pytest.mark.parametrize("effect", ["confirmed", "partial", "unverifiable", "suspected_noop"])
def test_any_possible_same_surface_input_limits_field_and_save_evidence(op, action, effect):
    old_field = _field_readback(1, "27", app="TextEdit", mode="native")
    saved = _save(2, "/s/document.txt", app="TextEdit", mode="native")
    later = _receipt(3, op, "outcome unknown", app="TextEdit", mode="native", **action)
    later["effect"] = effect
    field, save = effects([old_field, saved, later], document="document.txt")
    assert not field.usable and not save.usable
    assert evidence_values([field, save]) == ()
    assert floor("Save document.txt", [field, save], answer_bearing=False) is not None


@pytest.mark.parametrize("op", ["observe", "read", "look", "status", "inspect"])
def test_known_readonly_operations_preserve_field_and_save_evidence(op):
    later = _receipt(2, op, "observed without input")
    for old in [_field_readback(1, "27"), _save(1, "/s/document.txt")]:
        (item,) = effects([old, later], document="document.txt")
        assert item.usable


def test_fresh_qualified_save_replaces_prior_field_support_and_satisfies_saved_floor():
    old = _field_readback(1, "27", app="TextEdit", mode="native")
    saved = _save(2, "/s/document.txt", app="TextEdit", mode="native")
    field, save = effects([old, saved], document="document.txt")
    assert not field.usable and save.usable
    assert evidence_values([field, save]) == ()
    assert floor("Save document.txt", [field, save], answer_bearing=False) is None


@pytest.mark.parametrize("effect", [None, "unknown"])
def test_record_without_positive_input_effect_does_not_supersede_readback(effect):
    later = _receipt(2, "unclassified_input", "initial observation")
    later["effect"] = effect
    (item,) = effects([_field_readback(1, "27"), later])
    assert item.usable
