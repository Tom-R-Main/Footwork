from __future__ import annotations

import pytest
from jevdual.capability.contracts import CapabilityError, check_arguments


@pytest.mark.parametrize(
    "tool,args",
    [
        ("bind", {"name": "other"}),
        ("bind", {"name": "source", "pid": 4}),
        ("act", {"target": "t"}),
        ("act", {"target": "t", "text": " "}),
        ("act", {"target": "t", "text": "x", "approved": True}),
        ("status", {"reconcile": "true"}),
        ("status", {"operation": "o", "client_token": "t"}),
        ("observe", []),
    ],
)
def test_rejects_arguments_that_expand_scope_or_hide_recovery(tool, args):
    with pytest.raises(CapabilityError):
        check_arguments(tool, args)


def test_an_append_needs_only_the_offered_target_and_text():
    assert check_arguments("act", {"target": "t", "text": "17.25"}) == {"target": "t", "text": "17.25"}
    assert check_arguments("status", {}) == {}
