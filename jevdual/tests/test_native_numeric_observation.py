"""Numeric observation is snapshot evidence, never a numeric setter or exact text authority."""

from types import SimpleNamespace

import pytest
from jevdual.native import menu_from_snapshot


def _menu(**fields):
    return menu_from_snapshot({"elements": [{
        "element_index": 1, "element_token": "snap:1", "role": "AXSlider", "label": "Level",
        "actions": ["AXIncrement", "AXDecrement"], **fields,
    }]})


@pytest.mark.parametrize(("raw", "expected"), [("0", 0.0), ("-12.25", -12.25), (" 1e-3 ", .001), (0, 0.0)])
def test_finite_current_keeps_supplied_spelling_without_exact_text_authority(raw, expected):
    nm = _menu(value=raw)
    (candidate,) = nm.menu.candidates
    assert candidate.value == str(raw).strip()
    assert candidate.to_state()["numeric"] == {"source": "cua.window_state", "value": expected}
    assert candidate.operations == ("click",)
    assert nm.values == {} and nm.exact_ax_values == frozenset()
    assert candidate.value_truncated is None


@pytest.mark.parametrize("raw", [None, "", True, float("nan"), float("inf"), "Infinity", "NaN", "-6 dB",
                                 "1,000", "0x10", "1e9999", "1" * 121, 10 ** 200, [], {"value": 1}])
def test_unavailable_or_invalid_current_never_becomes_a_number(raw):
    (candidate,) = _menu(value=raw).menu.candidates
    assert candidate.value is None and candidate.numeric is None


def test_description_and_optional_independent_bounds_have_no_inferred_unit_or_default():
    (candidate,) = _menu(value=".75", value_description="-2.5 dB", min=0, max=1).menu.candidates
    numeric = candidate.to_state()["numeric"]
    assert numeric == {"source": "cua.window_state", "value": .75, "min": 0., "max": 1.,
                       "range_valid": True, "value_description": "-2.5 dB", "value_description_truncated": False}
    assert "unit" not in numeric
    (missing,) = _menu(value_description="105 BPM").menu.candidates
    assert missing.value is None
    assert missing.numeric == {"source": "cua.window_state", "value_description": "105 BPM",
                               "value_description_truncated": False}


def test_malformed_bounds_are_omitted_individually_and_inverted_bounds_marked():
    (partial,) = _menu(value="2", min=True, max=float("nan")).menu.candidates
    assert partial.numeric == {"source": "cua.window_state", "value": 2.}
    (inverted,) = _menu(min=5, max=-5).menu.candidates
    assert inverted.numeric == {"source": "cua.window_state", "min": 5., "max": -5., "range_valid": False}


def test_long_description_is_bounded_and_explicitly_clipped():
    (candidate,) = _menu(value_description="dB " * 10000).menu.candidates
    assert len(candidate.numeric["value_description"]) <= 120
    assert candidate.numeric["value_description_truncated"] is True


def test_typed_sdk_style_element_and_incrementor_use_same_read_only_projection():
    element = SimpleNamespace(element_index=1, element_token="s:1", role="AXIncrementor", label="Tempo",
                              value="105", value_description="105 BPM", min=None, max=None)
    (candidate,) = menu_from_snapshot({"elements": [element]}).menu.candidates
    assert candidate.role == "spinbutton" and candidate.value == "105"
    assert candidate.operations == ("click",) and candidate.numeric["value"] == 105


def test_numeric_looking_text_and_secure_fields_do_not_receive_numeric_metadata():
    for role in ("AXTextField", "AXSecureTextField", "AXButton"):
        (candidate,) = _menu(role=role, value="123", min=0, max=999).menu.candidates
        assert candidate.numeric is None
