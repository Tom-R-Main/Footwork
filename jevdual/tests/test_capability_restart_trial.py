"""Restart trial markers are immutable, complete at first visibility, and private."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def trial(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "restart_publication_trial", scripts / "capability_restart_trial.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_marker_is_not_visible_during_serialization(trial, tmp_path, monkeypatch):
    path = tmp_path / "hook.json"
    observed = []
    original_dump, original_dumps = trial.json.dump, trial.json.dumps

    def observe():
        observed.append(path.exists())
        assert not path.exists(), "observer can see the marker before serialization completes"

    def dump(value, stream, *args, **kwargs):
        observe()
        return original_dump(value, stream, *args, **kwargs)

    def dumps(value, *args, **kwargs):
        observe()
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(trial.json, "dump", dump)
    monkeypatch.setattr(trial.json, "dumps", dumps)
    expected = {"name": "native_dispatch_return_held", "pid": 123, "complete": True}
    trial._write(path, expected)
    assert observed and all(exists is False for exists in observed)
    assert trial.json.loads(path.read_text()) == expected
    assert path.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.iterdir()) == [path]


def test_second_publication_keeps_original_record(trial, tmp_path):
    path = tmp_path / "report.json"
    trial._write(path, {"version": "original"})
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        trial._write(path, {"version": "replacement"})
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_aggregate_report_can_exceed_product_packet_bound(trial, tmp_path):
    path = tmp_path / "summary.json"
    value = {"cases": [{"evidence": "x" * 150000}]}
    trial._write(path, value)
    assert trial.json.loads(path.read_text()) == value
