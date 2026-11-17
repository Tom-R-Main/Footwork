"""Synthetic held-parent graph through shared Rust capture check and public CLI.

Only the NoValue error is live-derived. No full Chrome graph was captured.
"""
import pytest

from tests import test_native_row_sdk_cli as cli
from tests import test_session_scenarios as scenarios
from tests.test_native_row_sdk import PROBE, click_wire, graph_fixture, node, probe

world = scenarios.world
fw = scenarios.fw
pytestmark = pytest.mark.skipif(not PROBE, reason="requires pinned row_parent_probe")


@pytest.mark.parametrize("durable", [False, True])
@pytest.mark.parametrize("variant", ["complete", "flattened"])
@pytest.mark.parametrize("fault", ["direct", "no_value", "unsupported", "timeout", "foreign"])
def test_public_cli_held_parent_contract(world, fw, monkeypatch, tmp_path, durable, variant, fault):
    original = cli.probe
    def with_membership(data):
        return original({**data, "window_faults": {} if fault == "direct" else {"1": fault}})
    monkeypatch.setattr(cli, "probe", with_membership)
    _graph, sent = cli.sdk_row_world(world, monkeypatch, variant)
    cli.start_row(fw, monkeypatch, tmp_path, durable)
    result = fw("do", "click", "section:Task ID=TASK-0::combobox:Open menu",
                *(["--token", "parent-contract"] if durable else []))
    if fault in ("direct", "no_value"):
        assert result[0] == 0, result
        assert sent == [940]
        assert cli.last_receipt(fw)["effect"] == "unverifiable"
    else:
        assert result[0] != 0, result
        assert sent == []


@pytest.mark.parametrize("fault", ["foreign", "unsupported", "timeout", "missing_parent",
                                   "cycle", "nonreciprocal", "alias", "wrong_pid", "budget"])
def test_actual_dispatch_refuses_invalid_membership(fault):
    graph = graph_fixture()
    data = {"mode": "discover", "graph": graph, "pid": 77, "window_id": 40335, "recipient": 940}
    binding = probe(data)["binding"]
    assert binding
    faults = {"1": "no_value"}
    extra = {}
    if fault in ("foreign", "unsupported", "timeout"):
        faults["1"] = fault
    elif fault == "missing_parent":
        node(graph, 1)["parent"] = None
    elif fault == "cycle":
        node(graph, 1)["parent"] = 2
    elif fault == "nonreciprocal":
        node(graph, 0)["children"] = []
    elif fault == "alias":
        # A conflicting edge outside the proved chain must still fail the full census.
        node(graph, 20)["children"].append(940)
    elif fault == "wrong_pid":
        node(graph, 0)["pid"] = 78
    elif fault == "budget":
        extra["membership_budget"] = 1
    answer = probe({"mode": "dispatch", "click": click_wire(), "binding": binding,
                    "graph": graph, "recipient": 940, "window_faults": faults, **extra})
    assert answer["schema_valid"]
    assert answer["presses"] == []
    assert answer["receipt"]["dispatched"] is False
