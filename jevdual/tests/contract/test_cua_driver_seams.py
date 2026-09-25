"""Contract tests pinning the cua-driver 0.28.2 seams jevdual depends on.

The native arm, the receipts and the coexistence posture all read the Driver's own types: its five
effect words, its routes and delivery modes, the snapshot fields that make ids stale by construction.
Each assertion names the jevdual module that relies on it. If a bump of cua-driver turns one of these
red, that module needs a look before the upgrade lands. Nothing here starts a Driver or needs a
permission grant; it is all import and signature inspection, so it runs in CI on Linux.
"""

from __future__ import annotations

import enum
import importlib.metadata
import inspect

import pytest

cd = pytest.importorskip("cua_driver")

PINNED_VERSION = "0.28.2"


def _params(cls) -> set[str]:
    return set(inspect.signature(cls.__init__).parameters) - {"self"}


def _members(e: type[enum.Enum]) -> set[str]:
    return {m.name for m in e}


# --------------------------------------------------------------------------- version


def test_cua_driver_version_is_pinned():
    # every native module: the effect vocabulary and refusal codes below are this version's
    assert importlib.metadata.version("cua-driver") == PINNED_VERSION


# --------------------------------------------------------------------------- names imported


@pytest.mark.parametrize(
    "name",
    [
        # native.py, desktop.py, cli.py, coexist.py; evals/native/runner.py for the predicates
        "CuaDriver",
        "ListAppsInput",
        "ListWindowsInput",
        "GetWindowStateInput",
        "VerifyStateInput",
        "InvokeMenuInput",
        "ElementPredicate",
        "ElementSelector",
        "StatePredicate",
        "ClickInput",
        "ClickPosition",
        "InputDeliveryMode",
        "ActionTarget",
        # browser_driver.py: the existing-profile attachment authorized by an in-process host
        "SessionPermissionMode",
        "DriverAuthorizationAction",
        "RuntimeAuthorizationOptions",
        "DriverAuthorizationHost",
        "DriverAuthorizationDecision",
        "ConfiguredDriverOptions",
    ],
)
def test_public_names_jevdual_imports(name):
    assert hasattr(cd, name), name


def test_private_event_loop_hook():
    # browser_driver.py: the authorization callback times out unless uniffi has our event loop
    from cua_driver import _native

    assert callable(_native.uniffi_set_event_loop)


def test_enum_members_jevdual_names():
    # browser_driver.py and native.py name these members directly
    assert {"ALLOW", "DENY"} <= _members(cd.DriverAuthorizationAction)
    assert "STANDARD" in _members(cd.SessionPermissionMode)
    assert {"BACKGROUND", "FOREGROUND"} <= _members(cd.InputDeliveryMode)


# --------------------------------------------------------------------------- driver methods


@pytest.mark.parametrize(
    ("method", "params"),
    [
        # native.py: every non-click action goes through call_tool with a JSON argument string
        ("call_tool", {"name", "arguments_json"}),
        ("click", {"input"}),
        ("get_window_state", {"input"}),
        ("invoke_menu", {"input"}),
        ("list_apps", {"input"}),
        ("list_windows", {"input"}),
        ("verify_state", {"input"}),
        ("shutdown", set()),
    ],
)
def test_driver_methods(method, params):
    fn = getattr(cd.CuaDriver, method)
    assert set(inspect.signature(fn).parameters) - {"self"} == params


# --------------------------------------------------------------------------- the receipt vocabulary


def test_effect_words_are_the_drivers():
    # receipts.py: EFFECT_WORDS is the Driver's ActionEffect, lowercased by native._enum_name
    from jevdual.receipts import EFFECT_WORDS

    assert {m.lower() for m in _members(cd.ActionEffect)} == set(EFFECT_WORDS)


def test_routes_and_delivery_modes():
    # native.py: an AX press with no route reads as "accessibility"; NativeEffect keeps the Driver's
    # delivery.mode beside the delivery the bridge declared
    assert "ACCESSIBILITY" in _members(cd.ActionRoute)
    assert {"BACKGROUND", "FOREGROUND"} <= _members(cd.ActionDeliveryMode)


def test_action_result_fields():
    # native.effect_from_action_result reads effect, route, delivery.mode and evidence[].kind
    assert {"effect", "route", "delivery", "evidence"} <= _params(cd.ActionResult)
    assert "mode" in _params(cd.ActionDelivery)


def test_evidence_carries_a_kind_only():
    # native.effect_from_action_result formats "<kind>: <detail>", but in this version evidence has
    # no detail: a receipt's evidence line from the Driver is the kind alone. The detail in
    # tests/test_native.py's fake is richer than the real SDK; readback text comes from our own
    # reobservation (jevdual.ax), not from here.
    assert _params(cd.ActionEvidence) == {"kind"}
    assert {"VALUE_READBACK", "WINDOW_CHANGE"} <= _members(cd.ActionEvidenceKind)


def test_mapping_reads_a_real_action_result():
    # the mapping end to end on the SDK's own types, not a fake
    from jevdual.native import effect_from_action_result

    res = cd.ActionResult(
        effect=cd.ActionEffect.SUSPECTED_NOOP,
        route=cd.ActionRoute.ACCESSIBILITY,
        delivery=cd.ActionDelivery(mode=cd.ActionDeliveryMode.BACKGROUND, delivered_count=1),
        evidence=[cd.ActionEvidence(kind=cd.ActionEvidenceKind.WINDOW_CHANGE)],
        escalation=None,
    )
    eff = effect_from_action_result("click", 3, "OK", res)
    assert eff.effect == "suspected_noop"
    assert eff.route == "accessibility"
    assert eff.driver_delivery == "background"
    assert eff.evidence == ("window_change:",)


def test_tool_result_fields():
    # native.py: call_tool and invoke_menu return a ToolResult; refusals arrive as is_error + error_code
    assert {"text", "is_error", "error_code", "action", "verification", "degraded"} <= _params(cd.ToolResult)


# --------------------------------------------------------------------------- the snapshot


def test_window_state_fields():
    # native.build_native_menu: snapshot_id binds every id to its capture (stale by construction);
    # truncated and degraded are conditions that call for a reobserve, not errors
    need = {
        "pid",
        "window_id",
        "snapshot_id",
        "tree_markdown",
        "elements",
        "elements_complete",
        "degraded",
        "truncated",
        "window_bounds",
    }
    assert need <= _params(cd.WindowStateOutput)


def test_window_element_fields():
    # native.build_native_menu reads each of these off an element
    need = {
        "element_index",
        "element_token",
        "role",
        "label",
        "value",
        "value_description",
        "enabled",
        "selected",
        "in_web_content",
        "actions",
        "parent_index",
        "frame",
    }
    assert need <= _params(cd.WindowElement)


def test_verify_state_predicates():
    # native.py calls verify_state; evals/native/runner.py builds the element predicates for task oracles
    assert {"pid", "window_id", "expect"} <= _params(cd.VerifyStateInput)
    assert {"window", "element"} <= _params(cd.StatePredicate)
    assert {"selector", "exists", "value_equals", "enabled", "selected"} <= _params(cd.ElementPredicate)
