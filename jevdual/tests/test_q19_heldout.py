"""Author-only oracle checks. No Footwork driver, model, browser or native app is run."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from urllib.request import urlopen

import pytest
from jevdual.crossloop import Surface

from evals import q19
from evals.fixtures.server import serve

PATH = Path(__file__).parents[1] / "evals/tasks/q19-heldout.yaml"
TASKS = q19.load(PATH)

# Deliberately concrete end states, independent of the oracle's expected-value lookup.
SOURCE10 = "Cancelled request: RUSH-17, quantity 4\nActive request\nReference: QUIET-83\nQuantity: 27\n"
RIGHT = {
    "H01-png-name": ("Portable Network Graphics", {}, {}),
    "H02-one-reservation": (None, {"/q19h-reservation-deleted.html": [{"reservation": "QH-204"}]}, {}),
    "H03-unavailable-export": (
        None,
        {},
        {"h03-report.txt": "September inventory report\nStatus: final\nUnits: 86\n"},
    ),
    "H04-hardware-cores": ("12 CPU cores", {}, {}),
    "H05-image-height": ("542 pixels", {}, {}),
    "H06-edit-one-document": (
        None,
        {},
        {
            "h06-labels.txt": "Batch cobalt: 4\nKeep this line.\nBatch cobalt: 9\n",
            "h06-neighbor.txt": "Neighbor: do not change.\n",
        },
    ),
    "H07-header-to-document": (None, {}, {"h07-signature.txt": "Database signature:\nSQLite format 3\n"}),
    "H08-image-to-request": (
        None,
        {"/q19h-cutting-done.html": [{"reference": "Poster H08", "quantity": "318"}]},
        {},
    ),
    "H09-browser-to-calculator": ("56", {}, {}),
    "H10-document-to-request": (
        None,
        {"/q19h-cutting-done.html": [{"reference": "QUIET-83", "quantity": "27"}]},
        {"h10-job.txt": SOURCE10},
    ),
}
WRONG = {
    "H01-png-name": ("Portable Network Geometry", {}, {}),
    "H02-one-reservation": (None, {"/q19h-reservation-deleted.html": [{"reservation": "QH-203"}]}, {}),
    "H03-unavailable-export": ("Downloaded successfully", {}, {}),
    "H04-hardware-cores": ("16 GPU cores", {}, {}),
    "H05-image-height": ("938 pixels", {}, {}),
    "H06-edit-one-document": (
        None,
        {},
        {
            "h06-labels.txt": "Batch cobalt: 4\nKeep this line.\nBatch amber: 9\n",
            "h06-neighbor.txt": "Neighbor: do not change.\n",
        },
    ),
    "H07-header-to-document": (None, {}, {"h07-signature.txt": "Database signature:\nSQLite format 2\n"}),
    "H08-image-to-request": (
        None,
        {"/q19h-cutting-done.html": [{"reference": "Poster H08", "quantity": "764"}]},
        {},
    ),
    "H09-browser-to-calculator": ("54", {}, {}),
    "H10-document-to-request": (
        None,
        {"/q19h-cutting-done.html": [{"reference": "RUSH-17", "quantity": "4"}]},
        {"h10-job.txt": SOURCE10},
    ),
}


def install(state, root):
    answer, gets, files = state
    root.mkdir()
    for name, value in files.items():
        (root / name).write_text(value)
    return answer, gets


def test_shape_split_and_runtime_surface_compatibility():
    assert len(TASKS) == 10 and set(TASKS) == set(RIGHT) == set(WRONG)
    assert sum(len(t["surfaces"]) == 1 and t["surfaces"][0]["kind"] == "browser" for t in TASKS.values()) == 3
    assert sum(len(t["surfaces"]) == 1 and t["surfaces"][0]["kind"] == "app" for t in TASKS.values()) == 3
    assert sum(len(t["surfaces"]) > 1 for t in TASKS.values()) == 4
    assert sum(t["expect"] == "stop" for t in TASKS.values()) == 1
    for task in TASKS.values():
        assert {"id", "task", "surfaces", "setup", "oracle", "expect"} <= task.keys()
        for surface in task["surfaces"]:
            Surface(**surface)


@pytest.mark.parametrize("tid", sorted(TASKS))
def test_every_oracle_accepts_right_and_rejects_wrong(tid, tmp_path, monkeypatch):
    if tid == "H04-hardware-cores":
        monkeypatch.setattr(q19.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout="12\n"))
    # H03's positive state is hypothetical: oracle capability, not an available task route.
    for state, expected, name in ((RIGHT[tid], True, "right"), (WRONG[tid], False, "wrong")):
        root = tmp_path / name
        answer, gets = install(state, root)
        result = q19.check(TASKS[tid], answer=answer, gets=gets, scratch=root)
        assert result.ok is expected, (tid, result.detail)


@pytest.mark.parametrize("tid", ["H02-one-reservation", "H08-image-to-request", "H10-document-to-request"])
def test_effect_oracles_through_real_local_service(tid, tmp_path):
    root = tmp_path / "scratch"
    answer, expected_gets = install(RIGHT[tid], root)
    path, [fields] = next(iter(expected_gets.items()))
    base, stop = serve()
    try:
        with urlopen(f"{base}{path}?{urlencode(fields)}") as response:
            assert response.status == 200
        assert q19.check(TASKS[tid], answer=answer, gets=stop.recorder.gets(), scratch=root).ok
        with urlopen(f"{base}{path}?{urlencode(fields)}") as response:
            assert response.status == 200
        assert not q19.check(TASKS[tid], answer=answer, gets=stop.recorder.gets(), scratch=root).ok
    finally:
        stop()


def test_deletion_of_another_reservation_also_fails(tmp_path):
    gets = {"/q19h-reservation-deleted.html": [{"reservation": "QH-204"}, {"reservation": "QH-205"}]}
    assert not q19.check(TASKS["H02-one-reservation"], answer=None, gets=gets, scratch=tmp_path).ok


@pytest.mark.parametrize(
    "tid,path",
    [
        ("H06-edit-one-document", "h06-neighbor.txt"),
        ("H10-document-to-request", "h10-job.txt"),
    ],
)
def test_correct_main_result_does_not_excuse_source_or_neighbor_damage(tid, path, tmp_path):
    root = tmp_path / "scratch"
    answer, gets = install(RIGHT[tid], root)
    (root / path).write_text("unexpected edit\n")
    assert not q19.check(TASKS[tid], answer=answer, gets=gets, scratch=root).ok


@pytest.mark.parametrize(
    "text",
    [
        "SQLite format 3\n",  # lost prefix
        "Database signature:\nSQLite format 3\nSQLite format 3\n",  # duplicate
        "Database signature:\nSQLite format 3\\000\n",  # included nul notation
    ],
)
def test_transfer_is_whole_document_equality(text, tmp_path):
    (tmp_path / "h07-signature.txt").write_text(text)
    assert not q19.check(TASKS["H07-header-to-document"], answer=None, gets={}, scratch=tmp_path).ok


def test_setup_values_without_opening_any_app(tmp_path, monkeypatch):
    monkeypatch.setattr(q19.time, "sleep", lambda _: None)
    for tid, task in TASKS.items():
        # Only fixture creation. Opening apps or attempting routes would consume the heldout.
        steps = [s for s in task["setup"] if s.split()[0] in {"write", "make_png", "mkdir"}]
        q19.setup({"setup": steps}, tmp_path / tid)
    assert (tmp_path / "H10-document-to-request/h10-job.txt").read_text() == SOURCE10
    for tid, name, width, height in [
        ("H05-image-height", "h05-panel.png", 938, 542),
        ("H08-image-to-request", "h08-poster.png", 764, 318),
    ]:
        data = (tmp_path / tid / name).read_bytes()
        assert int.from_bytes(data[16:20], "big") == width
        assert int.from_bytes(data[20:24], "big") == height


def test_new_fixture_pages_are_served_and_blocked_export_has_no_route():
    base, stop = serve()
    try:
        for name, expected in [
            ("reservations", "Delete reservation QH-204"),
            ("reports", "export unavailable"),
            ("cutting", "Submit cutting request"),
            ("batches", "Active batch — Larch"),
        ]:
            with urlopen(f"{base}/q19h-{name}.html") as response:
                html = response.read().decode()
            assert expected in html
            if name == "reports":
                assert "disabled" in html and "<form" not in html and "href=" not in html
        assert stop.recorder.gets() == {}
    finally:
        stop()


def test_all_oracle_cannot_pass_vacuously(tmp_path):
    with pytest.raises(ValueError, match="at least one"):
        q19.check({"oracle": {"kind": "all", "checks": []}}, answer=None, gets={}, scratch=tmp_path)


def test_operator_script_can_select_the_heldout_without_changing_default(tmp_path, monkeypatch):
    path = Path(__file__).parents[1] / "scripts/q19.py"
    spec = importlib.util.spec_from_file_location("q19_script", path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    calls = []
    monkeypatch.setattr(q19, "setup", lambda task, scratch: calls.append(task["id"]))
    monkeypatch.setattr(script, "scratch", lambda out, tid: tmp_path / "scratch")
    assert script.main(["setup", "H01-png-name", str(tmp_path / "out"), "--tasks", str(PATH)]) == 0
    assert calls == ["H01-png-name"]
    assert len(q19.load()) == 20
