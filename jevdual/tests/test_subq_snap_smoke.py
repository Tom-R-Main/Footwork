"""Offline SQ1 contract, attempt accounting, and credential boundary tests."""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "subq_snap_smoke", Path(__file__).resolve().parents[1] / "scripts/subq_snap_smoke.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def response(route="act", usage=True):
    value = {
        "model": probe.MODEL,
        "answers": {
            "route": {"type": "choice", "choice": route, "confidence": 1,
                      "probabilities": {r: int(r == route) for r in probe.ROUTES}},
            "completion": {"type": "noul", "noul": int(route == "done")},
            "progress": {"type": "score", "score": 0, "confidence": 1,
                         "legend": {"0": "not started", "1": "partial", "2": "complete"},
                         "probabilities": {"0": 1, "1": 0, "2": 0}},
        },
    }
    if usage:
        value["usage"] = {"input_tokens": 100, "output_tokens": 0}
    return value


@pytest.mark.parametrize("path,bad", [
    (("model",), "other"),
    (("answers", "completion", "type"), "score"),
    (("answers", "completion", "noul"), float("nan")),
    (("answers", "completion", "noul"), True),
    (("answers", "completion", "noul"), 1.1),
    (("answers", "route", "confidence"), float("inf")),
    (("answers", "route", "choice"), "done"),
    (("answers", "route", "probabilities"), {"act": 1}),
    (("answers", "route", "probabilities"), dict.fromkeys(probe.ROUTES, 1)),
    (("answers", "progress", "score"), 1),
    (("answers", "progress", "legend"), {}),
    (("usage", "input_tokens"), -1),
    (("usage", "input_tokens"), True),
    (("usage", "input_tokens"), 1.5),
    (("usage", "output_tokens"), 1),
])
def test_malformed_contract_refused(path, bad):
    value = response()
    node = value
    for name in path[:-1]:
        node = node[name]
    node[path[-1]] = bad
    with pytest.raises(probe.ProbeError):
        probe.validate_response(value)


def test_valid_response_and_rounding_tolerance():
    value = response()
    value["answers"]["progress"].update(
        score=1.86, probabilities={"0": 0, "1": 0.13, "2": 0.87}
    )
    assert probe.validate_response(value)["score"] == 1.86
    assert probe.validate_response(response(usage=False))["input_tokens"] is None


def test_fixed_synthetic_matrix_and_reservation_within_cap():
    cases = list(probe.cases())
    assert len(cases) == 12
    assert len({c["id"] for c in cases}) == 12
    assert {c["distractor_characters"] for c in cases} == {0, 8000, 80000}
    assert all(c["body"].isascii() and len(c["body"]) <= 90000 for c in cases)
    assert sum(len(c["body"]) * 3 * probe.RATE for c in cases) < probe.CAP


def execute(tmp_path, post):
    calls = []

    def send(method, endpoint, key, body=None):
        calls.append((method, endpoint))
        if method == "GET":
            return {"data": [{"id": probe.MODEL}]}
        # Reservation must already be durable at the dispatch boundary.
        attempts = json.loads((tmp_path / "attempts.json").read_text())
        assert attempts[-1]["status"] == "reserved"
        assert attempts[-1]["reserved_input_tokens"] == len(body) * 3
        return post(key, len(calls) - 2)

    result = probe.run(tmp_path, "sk-test-secret-only", "abc", send, lambda _: "abc")
    return result, calls, json.loads((tmp_path / "attempts.json").read_text())


def test_error_stops_without_retry_and_retains_unknown_reservation(tmp_path):
    def post(key, index):
        raise RuntimeError("provider echoed " + key)

    result, calls, records = execute(tmp_path, post)
    assert len(calls) == 2
    assert result["attempted"] == 1 and result["completed"] == 0
    assert records[0]["accounted_tokens"] == records[0]["reserved_input_tokens"]
    assert "Unexpected failure" == result["stop_reason"]
    assert all("sk-test-secret-only" not in p.read_text() for p in tmp_path.iterdir())


def test_provider_key_echo_is_redacted_in_values_and_keys(tmp_path):
    def post(key, index):
        value = response()
        value["echo"] = {key: [key, "prefix " + key]}
        return value

    result, calls, _ = execute(tmp_path, post)
    assert len(calls) == 13 and result["completed"] == 12
    assert all("sk-test-secret-only" not in p.read_text() for p in tmp_path.iterdir())
    assert "[REDACTED]" in (tmp_path / "attempts.json").read_text()


def test_reported_usage_exceeding_reservation_stops(tmp_path):
    def post(key, index):
        value = response()
        value["usage"]["input_tokens"] = 900_000
        return value

    result, calls, records = execute(tmp_path, post)
    assert len(calls) == 2
    assert "exceed" in result["stop_reason"]
    assert records[0]["accounted_tokens"] == 900_000
    assert result["reported_input_tokens"] == 900_000


def test_malformed_response_stops_after_one_attempt(tmp_path):
    result, calls, _ = execute(tmp_path, lambda *_: {"model": "wrong"})
    assert len(calls) == 2 and result["completed"] == 0
    assert "model" in result["stop_reason"]


def test_missing_usage_reservation_is_retained(tmp_path):
    result, _, records = execute(tmp_path, lambda *_: response(usage=False))
    assert result["reported_usage_available_calls"] == 0
    assert all(r["accounted_tokens"] == r["reserved_input_tokens"] for r in records)


def test_budget_cap_prevents_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "CAP", 0)
    result = probe.run(tmp_path, "secret", "abc", lambda *_: {"data": [{"id": probe.MODEL}]}, lambda _: None)
    assert result["attempted"] == 0 and "cap" in result["stop_reason"]


def test_cancelled_dialog_never_exposes_captured_output(monkeypatch):
    class Cancelled:
        returncode = 1
        stdout = "secret"
        stderr = "secret"

    monkeypatch.setattr(probe.sys, "platform", "darwin")
    monkeypatch.setattr(probe.subprocess, "run", lambda *a, **kw: Cancelled())
    with pytest.raises(probe.ProbeError, match="cancelled") as error:
        probe.prompt_key()
    assert "secret" not in str(error.value)


def test_dry_run_does_not_prompt_or_dispatch(monkeypatch, capsys):
    def forbidden(*a, **kw):
        raise AssertionError("No key or API access in dry run")

    monkeypatch.setattr(probe, "prompt_key", forbidden)
    monkeypatch.setattr(probe, "transport", forbidden)
    assert probe.main(["--prompt-key"]) == 0
    assert json.loads(capsys.readouterr().out)["requests"] == 12
