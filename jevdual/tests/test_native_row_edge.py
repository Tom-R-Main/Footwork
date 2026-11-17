"""Scoped failure evidence uses synthetic hop operands, never a live Chrome graph."""

import json

import pytest
from jevdual.row_trace import retain


@pytest.mark.parametrize(
    "case,want",
    [
        ("empty", "absent_at_read"),
        ("absent", "absent_at_read"),
        ("equal", "raw_match_lost"),
        ("changed", "changed_parent"),
        ("partial", "unknown"),
        ("malformed", None),
        ("binding", None),
    ],
)
def test_failed_hop_retention(tmp_path, case, want):
    url = "http://127.0.0.1:5176/tasks"
    edge = {
        "root": 0,
        "outer": 6,
        "current": 6,
        "parent": 2,
        "first_parent": 2,
        "proof_parent": 2,
        "hop": 1,
        "raw_count": 1,
        "samples": [[5, False]],
        "truncated": False,
    }
    if case == "empty":
        edge.update(raw_count=0, samples=[])
    if case == "equal":
        edge["samples"][0][1] = True
    if case == "changed":
        edge["first_parent"] = 4
    if case == "partial":
        edge.update(truncated=True, samples=[])
    if case == "malformed":
        edge["samples"][0][0] = "private page content"
    trace = {
        "version": 1,
        "pid": 77,
        "window_id": 9,
        "scope_url": url,
        "scope_matched": False,
        "snapshot_id": "s1",
        "status": "capture_refused",
        "error": "row parent/child mismatch",
        "node": 6,
        "failed_hop": edge,
        "truncated": edge["truncated"],
    }
    out = tmp_path / "trace.json"
    retain(
        out,
        {"pid": 77, "window_id": 9, "row_trace_url": url},
        {
            "pid": 77,
            "window_id": 9,
            "snapshot_id": "other" if case == "binding" else "s1",
            "row_trace_json": json.dumps(trace),
        },
        [],
    )
    result = json.loads(out.read_text())
    observed = (result.get("sdk") or {}).get("failed_hop")
    if want is None:
        assert observed is None and "private page content" not in out.read_text()
    else:
        assert observed == dict(edge, classification=want)
        assert result["sdk"]["error"] == "row parent/child mismatch"
        assert result["truncated"] is edge["truncated"]


def test_partial_raw_match_cannot_establish_a_complete_edge(tmp_path):
    from jevdual.row_trace import _failed_hop

    refusal = {"status": "capture_refused", "error": "row parent/child mismatch", "node": 6}
    edge = {
        "root": 0,
        "outer": 6,
        "current": 3,
        "parent": 0,
        "first_parent": 3,
        "proof_parent": 3,
        "hop": 2,
        "raw_count": 2,
        "samples": [[5, True]],
        "truncated": True,
    }
    assert _failed_hop(refusal, edge)["classification"] == "unknown"
    assert _failed_hop(refusal, dict(edge, samples=[[3, True]])) is None
    assert _failed_hop(dict(refusal, status="qualified"), edge) is None


def test_public_start_retains_bound_refusal_once_without_input(world, fw, monkeypatch, tmp_path):
    from tests.test_native_row_sdk import PROBE
    from tests.test_native_row_sdk_cli import sdk_row_world

    if not PROBE:
        pytest.skip("requires compiled SDK row adapter")
    _, sent = sdk_row_world(world, monkeypatch, "complete")
    url = "http://127.0.0.1:5176/tasks"
    out = tmp_path / "trace.json"
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"pid": 77, "window_id": 40335, "url": url, "output": str(out)}))
    monkeypatch.setenv("FOOTWORK_ROW_TRACE_CONFIG", str(config))
    original = world.get_window_state
    requests = []

    async def capture(request):
        requests.append(request)
        snapshot = await original(request)
        for element in snapshot["elements"]:
            element.pop("expected_row", None)
        snapshot["row_trace_json"] = json.dumps(
            {
                "version": 1,
                "pid": 77,
                "window_id": 40335,
                "scope_url": url,
                "snapshot_id": snapshot["snapshot_id"],
                "scope_matched": False,
                "status": "capture_refused",
                "error": "row parent/child mismatch",
                "node": 6,
                "truncated": False,
                "failed_hop": {
                    "root": 0,
                    "outer": 6,
                    "current": 6,
                    "parent": 2,
                    "first_parent": 2,
                    "proof_parent": 2,
                    "hop": 1,
                    "raw_count": 0,
                    "samples": [],
                    "truncated": False,
                },
            }
        )
        return snapshot

    monkeypatch.setattr(world, "get_window_state", capture)
    code, _, err = fw("start", "Observe row", "--app", "Calculator", "--mode", "exclusive_desktop")
    assert code == 0, err
    assert len(requests) == 1 and sent == []
    result = json.loads(out.read_text())
    assert result["status"] == "scope_unproven"
    assert result["sdk"]["failed_hop"]["classification"] == "absent_at_read"


from tests import test_session_scenarios as scenarios

fw = scenarios.fw
world = scenarios.world
