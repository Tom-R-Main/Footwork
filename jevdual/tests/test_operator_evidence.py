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
