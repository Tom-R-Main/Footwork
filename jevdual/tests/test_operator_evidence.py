"""Evidence shapes preserve predicate boundaries and reject mismatched execution claims."""

from __future__ import annotations

import copy
import time
from types import SimpleNamespace

import pytest
from jevdual.operator_evidence import (
    EvidenceError,
    execution_record,
    fact_record,
    validate_execution,
    validate_fact,
)
from jevdual.session_operations import native_resource

BINDING = {"boot": "fixture-boot", "pid": 77, "start": "fixture-start", "window_id": 12}


def make_execution(**over):
    now = time.time()
    op = SimpleNamespace(
        id="op_1",
        task="session1",
        request_digest="digest1",
        resource=native_resource(BINDING),
        observation="obs1",
        target="target1",
        move="click",
        created=now - 1,
    )
    args = {
        "binding": BINDING,
        "started_at": now - 0.5,
        "ended_at": now,
        "producer_evidence": {
            "name": "footwork.native",
            "version": 1,
            "delivery_basis": "sdk_delivery_count",
            "delivered_count": 1,
        },
        "dispatched": True,
        "effect": "confirmed",
        "phase": "sent",
        "projection": {"operation_id": op.id, "binding": BINDING, "driver_effect": "confirmed"},
        **over,
    }
    return op, execution_record(op, **args)


def test_returned_execution_binds_attempt_resource_and_full_interval():
    op, record = make_execution()
    assert validate_execution(record, op, binding=BINDING) == record
    assert record["custody"] == "returned" and record["kind"] == "execution"


@pytest.mark.parametrize(
    "field", ["operation_id", "session_id", "request_digest", "resource", "observation", "target", "move"]
)
def test_other_attempt_cannot_supply_execution(field):
    op, record = make_execution()
    record[field] = "another"
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": "99"},
        {"protocol": True},
        {"custody": "running"},
        {"binding": {**BINDING, "window_id": 99}},
        {"interval": {"start": 0, "end": 1}},
        {"interval": {"start": True, "end": 2}},
        {"interval": {"start": float("nan"), "end": 2}},
        {"interval": {"start": time.time() + 100, "end": time.time() + 101}},
        {"phase": "not_sent"},
        {"dispatched": None},
    ],
)
def test_unsupported_or_contradictory_execution_is_rejected(change):
    op, record = make_execution()
    record.update(change)
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)


@pytest.mark.parametrize("count", [None, 0, True, -1, "1"])
def test_sent_requires_positive_typed_count(count):
    with pytest.raises(EvidenceError):
        make_execution(
            producer_evidence={
                "name": "footwork.native",
                "version": 1,
                "delivery_basis": "sdk_delivery_count",
                "delivered_count": count,
            }
        )


def test_menu_delivery_cannot_certify_application_effect():
    producer = {
        "name": "footwork.native",
        "version": 1,
        "delivery_basis": "ax_menu_press_ack",
        "delivered_count": 1,
    }
    with pytest.raises(EvidenceError):
        make_execution(producer_evidence=producer)
    _, record = make_execution(producer_evidence=producer, effect="unverifiable")
    assert record["phase"] == "sent" and record["effect"] == "unverifiable"


def test_no_send_requires_a_qualified_gate_not_a_refusal_word():
    with pytest.raises(EvidenceError):
        make_execution(dispatched=False, effect="refused", phase="not_sent")
    _, record = make_execution(
        dispatched=False,
        effect="refused",
        phase="not_sent",
        producer_evidence={
            "name": "footwork.native",
            "version": 1,
            "delivery_basis": "qualified_gate",
            "delivered_count": 0,
        },
    )
    assert record["phase"] == "not_sent"


def make_fact(**over):
    return fact_record(
        **{
            "kind": "current_state",
            "predicate": "field_equals",
            "resource": "field1",
            "binding": BINDING,
            "observation": "obs2",
            "started_at": 1.0,
            "ended_at": 2.0,
            "values": ["A" * 300],
            "evidence_refs": ["obs2/field1"],
            **over,
        }
    )


def test_exact_fact_preserves_long_value_and_explicit_limits():
    record = make_fact(limits=["window birth not established"])
    assert record["values"] == ["A" * 300]
    assert record["limits"] == ["window birth not established"]
    assert validate_fact(record) == record


def test_boolean_versions_and_equal_boolean_bindings_are_not_identity():
    op, record = make_execution()
    record["producer"]["version"] = True
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)
    record = make_fact()
    record["producer"]["version"] = True
    with pytest.raises(EvidenceError):
        validate_fact(record)
    op, record = make_execution()
    identity = {**BINDING, "pid": 1}
    op.resource = native_resource(identity)
    record["resource"] = op.resource
    record["binding"] = {**identity, "pid": True}
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=identity)


@pytest.mark.parametrize(
    "projection", [{"op": "append"}, {"observation": "other"}, {"target_id": "other"}, {"dispatched": False}]
)
def test_projection_cannot_rebind_a_retained_execution(projection):
    op, record = make_execution()
    record["projection"].update(projection)
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)


def test_current_or_persistence_fact_does_not_become_execution_or_task():
    record = make_fact()
    for kind in ("execution", "task", "persistence"):
        changed = copy.deepcopy(record)
        changed["kind"] = kind
        with pytest.raises(EvidenceError):
            validate_fact(changed)
    persisted = make_fact(
        kind="persistence", predicate="disk_equals_window", resource="/fixture/file.txt", values=[]
    )
    assert persisted["kind"] == "persistence"


@pytest.mark.parametrize(
    "change",
    [
        {"producer": {"name": "external", "version": 1}},
        {"observation": ""},
        {"binding": {}},
        {"interval": {"start": True, "end": 2}},
        {"values": "text"},
        {"parameters": None},
    ],
)
def test_malformed_fact_cannot_supply_support(change):
    record = make_fact()
    record.update(change)
    with pytest.raises(EvidenceError):
        validate_fact(record)


def fullscreen_execution():
    op, record = make_execution()
    op.target = '-2'
    op.args = {'words': ['click', '-2']}
    record['target'] = '-2'
    control = {'pid': 77, 'window_id': 12, 'window_hash': 100, 'button_hash': 200,
               'subrole': 'AXFullScreenButton', 'fullscreen': False}
    proof = {'schema_version': 1, 'producer': 'footwork.ax.fullscreen',
             'predicate': 'native_fullscreen_state_transition', 'before': control,
             'after': {'pid': 77, 'window_id': 12, 'fullscreen': True, 'bounds': None},
             'press_acknowledged': True, 'transition_observed': True}
    record['producer']['delivery_basis'] = 'ax_fullscreen_state_readback'
    record['projection'].update(op='click', target_id=-2, target_label='Enter Full Screen',
        dispatched=True, target_identity={'role': 'button', 'label': 'Enter Full Screen',
                                         'section': 'Native window', 'native_window_control': copy.deepcopy(control)},
        native_readback=proof)
    return op, record


def test_fullscreen_evidence_requires_exact_fixed_action():
    op, record = fullscreen_execution()
    assert validate_execution(record, op, binding=BINDING) == record


@pytest.mark.parametrize('mutation', [
    'missing_proof', 'wrong_predicate', 'wrong_producer', 'schema_bool', 'before_bool', 'after_bool',
    'ack_integer', 'transition_integer', 'wrong_pid', 'wrong_window', 'different_expected_state',
    'wrong_operation', 'wrong_target', 'wrong_selector', 'partial_selector', 'projection_target',
    'projection_identity_type', 'projection_control_type', 'control_bool', 'identity_label', 'unknown_field',
    'invalid_bounds', 'nonfinite_bounds', 'no_transition', 'no_ack', 'two_presses', 'missing_count',
    'dispatched_false', 'effect_refused', 'projection_effect', 'unknown_basis', 'contradictory_error',
])
def test_fullscreen_evidence_rejects_contradictions(mutation):
    op, record = fullscreen_execution()
    proof = record['projection']['native_readback']
    projection = record['projection']
    if mutation == 'missing_proof': projection.pop('native_readback')
    elif mutation == 'wrong_predicate': proof['predicate'] = 'arbitrary_toggle'
    elif mutation == 'wrong_producer': proof['producer'] = 'footwork.ax.preview'
    elif mutation == 'schema_bool': proof['schema_version'] = True
    elif mutation == 'before_bool': proof['before']['fullscreen'] = 0
    elif mutation == 'after_bool': proof['after']['fullscreen'] = 1
    elif mutation == 'ack_integer': proof['press_acknowledged'] = 1
    elif mutation == 'transition_integer': proof['transition_observed'] = 1
    elif mutation == 'wrong_pid': proof['after']['pid'] = 88
    elif mutation == 'wrong_window': proof['after']['window_id'] = 13
    elif mutation == 'different_expected_state': proof['before']['fullscreen'] = True
    elif mutation == 'wrong_operation': op.move = record['move'] = 'drag'
    elif mutation == 'wrong_target': op.target = record['target'] = '980'
    elif mutation == 'wrong_selector': op.args['words'] = ['click', '980']
    elif mutation == 'partial_selector': op.args['words'] = ['click', 'Full']
    elif mutation == 'projection_target': projection['target_id'] = 980
    elif mutation == 'projection_identity_type': projection['target_identity'] = 'bad'
    elif mutation == 'projection_control_type': projection['target_identity']['native_window_control'] = None
    elif mutation == 'control_bool': projection['target_identity']['native_window_control']['fullscreen'] = 0
    elif mutation == 'identity_label': projection['target_identity']['label'] = 'Exit Full Screen'
    elif mutation == 'unknown_field': proof['extra'] = 'not supported'
    elif mutation == 'invalid_bounds': proof['after']['bounds'] = {'x': 0, 'y': 0, 'w': True, 'h': 100}
    elif mutation == 'nonfinite_bounds': proof['after']['bounds'] = {'x': float('inf'), 'y': 0, 'w': 100, 'h': 100}
    elif mutation == 'no_transition': proof['transition_observed'] = False
    elif mutation == 'no_ack': proof['press_acknowledged'] = False
    elif mutation == 'two_presses': record['producer']['delivered_count'] = 2
    elif mutation == 'missing_count': record['producer']['delivered_count'] = None
    elif mutation == 'dispatched_false': projection['dispatched'] = False
    elif mutation == 'effect_refused': record['effect'] = 'refused'
    elif mutation == 'projection_effect': projection['driver_effect'] = 'unverifiable'
    elif mutation == 'unknown_basis': record['producer']['delivery_basis'] = 'unknown'
    elif mutation == 'contradictory_error': proof['error'] = 'unreadable'
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)


@pytest.mark.parametrize('basis', ['sdk_delivery_count', 'ax_insert_ack'])
@pytest.mark.parametrize('count', [1, 2])
def test_fullscreen_reserved_target_cannot_erase_its_proof(basis, count):
    op, record = fullscreen_execution()
    record['producer'].update(delivery_basis=basis, delivered_count=count)
    record['projection'].pop('target_identity')
    record['projection'].pop('native_readback')
    assert op.target == '-2'
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)


@pytest.mark.parametrize('phase,dispatched,basis,count,effect', [
    ('not_sent', False, 'qualified_gate', 0, 'refused'),
    ('ambiguous', None, 'unknown', None, 'unverifiable'),
])
def test_fullscreen_reserved_target_preserves_no_dispatch_or_unknown(phase, dispatched, basis, count, effect):
    op, record = fullscreen_execution()
    record.update(phase=phase, dispatched=dispatched, effect=effect)
    record['producer'].update(delivery_basis=basis, delivered_count=count)
    record['projection'].pop('target_identity')
    record['projection'].pop('native_readback')
    record['projection'].update(dispatched=dispatched, driver_effect=effect)
    assert validate_execution(record, op, binding=BINDING) == record


def test_fullscreen_reserved_target_unknown_dispatch_cannot_confirm_without_proof():
    op, record = fullscreen_execution()
    record.update(phase='ambiguous', dispatched=None)
    record['producer'].update(delivery_basis='unknown', delivered_count=None)
    record['projection'].pop('target_identity')
    record['projection'].pop('native_readback')
    record['projection']['dispatched'] = None
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)
