"""Coverage is retained at the producer before bounded semantic projection."""

import pytest
from jevdual.browser_driver import menu_from_semantic
from jevdual.capability.observations import Observations


@pytest.mark.parametrize("length", [5999, 6000, 6001, 12000])
def test_text_cap_survives_capability_projection(length):
    snapshot = menu_from_semantic(
        {
            "snapshot": {"id": "s1", "complete": True},
            "content_refs": [{"role": "paragraph", "name": "x" * length}],
        }
    )
    projected = Observations().project("browser:fixture", snapshot, writable=False)
    assert len(projected["text"]) == min(6000, length)
    assert projected["coverage"]["text_truncated"] is (length > 6000)
    assert projected["coverage"]["text_original_length"] == length


def test_clipped_field_preview_does_not_appear_complete_after_second_projection():
    snapshot = menu_from_semantic(
        {
            "snapshot": {"id": "s1", "complete": True},
            "refs": [{"ref": "s1:7", "role": "textbox", "name": "Quantity", "value": "z" * 201}],
        }
    )
    projected = Observations().project("browser:fixture", snapshot, writable=False)
    assert len(projected["elements"][0]["value"]) == 200
    assert projected["elements"][0]["value_truncated"] is True
    assert projected["coverage"]["omitted"]["value_previews_truncated"] == 1


def test_incomplete_source_is_not_made_complete_by_short_text():
    snapshot = menu_from_semantic({"snapshot": {"id": "s1", "complete": False}})
    projected = Observations().project("browser:fixture", snapshot, writable=False)
    assert projected["coverage"]["elements_complete"] is False
    assert projected["coverage"]["text_truncated"] is False
