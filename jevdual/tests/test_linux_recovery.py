"""Recovery route schemas bind the observed native field role, without replay authority."""

from __future__ import annotations

import copy
from contextlib import closing

import pytest
from jevdual.capability import recovery
from jevdual.capability.journal import Journal


@pytest.fixture
def inputs(tmp_path):
    scope = {
        "task": "linux_recovery_fixture",
        "source": {"pid": 11, "window_id": 12, "url": "http://127.0.0.1:8000/"},
        "destination": {"pid": 77, "window_id": 123, "document": str(tmp_path / "owned.txt")},
    }
    identity = {
        "boot": "fixture-boot", "pid": 77, "start": "0x1.0p0",
        "document": scope["destination"]["document"], "device": 1, "inode": 2,
    }
    return scope, identity


def envelope(inputs, role):
    scope, identity = inputs
    return recovery.make_recovery(scope, identity, role, (10, 20, 300, 400), "Before\n", "Before\nAfter")


def test_linux_mousepad_text_gets_distinct_route_and_complete_packet_binding(inputs, tmp_path, monkeypatch):
    monkeypatch.setattr(recovery.sys, "platform", "linux")
    scope, _ = inputs
    value = envelope(inputs, "text")
    assert value["route"] == "mousepad-atspi-append-v1"
    assert value["field"] == {"role": "text", "frame": [10, 20, 300, 400]}
    assert value["before"] == recovery.fingerprint("Before\n")
    assert value["expected"] == recovery.fingerprint("Before\nAfter")
    with closing(Journal(tmp_path / "operations.sqlite")) as journal:
        op, _ = journal.begin(
            task=scope["task"], resource="native:77:123", observation="obs_fixture", target="target_fixture",
            move="append", args={"text": "After"}, client_token="append-once", recovery=value,
        )
        packet = recovery.packet_for(op)
        assert packet["recovery"] == value
        assert recovery.validate_packet(packet) == packet
        altered = copy.deepcopy(packet)
        altered["recovery"]["route"] = recovery.ROUTE
        with pytest.raises(recovery.RecoveryError, match="field identity"):
            recovery.validate_packet(altered)


@pytest.mark.parametrize("platform,role", [
    ("darwin", "text"), ("linux", "AXTextArea"), ("linux", "entry"),
    ("linux", "password text"), ("linux", "textbox"), ("linux", "Text"),
    ("linux", " text "), ("freebsd", "text"), ("darwin", "AXTextField"),
])
def test_generation_refuses_unqualified_platform_role_pairs(inputs, monkeypatch, platform, role):
    monkeypatch.setattr(recovery.sys, "platform", platform)
    with pytest.raises(recovery.RecoveryError, match="platform or field role"):
        envelope(inputs, role)


@pytest.mark.parametrize("role", ["AXTextArea", "entry", "password text", "textbox", "", None, []])
def test_linux_validation_never_accepts_arbitrary_roles(inputs, monkeypatch, role):
    monkeypatch.setattr(recovery.sys, "platform", "linux")
    value = envelope(inputs, "text")
    value["field"]["role"] = role
    with pytest.raises(recovery.RecoveryError, match="field identity"):
        recovery.validate_recovery(value)


@pytest.mark.parametrize("route", ["mousepad-atspi-append-v2", "generic-append", "", None, []])
def test_validation_refuses_unknown_route_without_dispatch(inputs, monkeypatch, route):
    monkeypatch.setattr(recovery.sys, "platform", "linux")
    value = envelope(inputs, "text")
    value["route"] = route
    with pytest.raises(recovery.RecoveryError, match="recovery envelope"):
        recovery.validate_recovery(value)


def test_mac_envelope_contract_and_cross_host_history_validation_are_preserved(inputs, monkeypatch):
    monkeypatch.setattr(recovery.sys, "platform", "darwin")
    mac = envelope(inputs, "AXTextArea")
    assert mac["version"] == 1
    assert mac["route"] == recovery.ROUTE == "textedit-ax-append-v1"
    assert mac["field"] == {"role": "AXTextArea", "frame": [10, 20, 300, 400]}
    assert set(mac) == {"version", "route", "nonce", "scope", "scope_digest", "identity", "field", "before", "expected"}
    monkeypatch.setattr(recovery.sys, "platform", "linux")
    assert recovery.validate_recovery(mac) is mac
    linux = envelope(inputs, "text")
    monkeypatch.setattr(recovery.sys, "platform", "darwin")
    assert recovery.validate_recovery(linux) is linux


def test_linux_route_retains_document_identity_and_exact_content_checks(inputs, monkeypatch):
    monkeypatch.setattr(recovery.sys, "platform", "linux")
    original = envelope(inputs, "text")
    mutated = copy.deepcopy(original)
    mutated["identity"]["pid"] += 1
    with pytest.raises(recovery.RecoveryError, match="native identity"):
        recovery.validate_recovery(mutated)
    mutated = copy.deepcopy(original)
    mutated["scope"]["destination"]["document"] += ".different"
    with pytest.raises(recovery.RecoveryError, match="scope fingerprint"):
        recovery.validate_recovery(mutated)
    mutated = copy.deepcopy(original)
    mutated["expected"]["sha256"] = "unknown"
    with pytest.raises(recovery.RecoveryError, match="content fingerprint"):
        recovery.validate_recovery(mutated)
