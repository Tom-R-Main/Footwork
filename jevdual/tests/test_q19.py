"""Q19's oracle stage (docs/experiments/Q19.md): every development task's oracle confirms a correct end state
and fails a wrong one, before any driving. Fixture submissions go through the real fixture server."""

from __future__ import annotations

import sys
import urllib.parse
import urllib.request

import pytest

from evals import q19
from evals.fixtures.server import serve

TASKS = q19.load()

#: per task: (correct answer, wrong answer) for answer oracles
ANSWERS = {
    "D01-quote-tag": ("André Gide", "Albert Einstein"),
    "D02-cheapest-laptop": ("The cheapest is the Asus VivoBook X441NA-GA190", "Prestigio SmartBook 133S"),
    "D03-practice-login": ("Logged In Successfully", "Test login"),
    "D04-iana-example": ("example.com", "example.org"),
    "D08-calc-power": ("1024", "1000"),
    "D09-dictionary": ("noun", "verb"),
    "D10-image-size": ("640 × 480 pixels", "640 × 400"),
}


def test_every_task_has_a_known_oracle_and_an_expectation():
    assert len(TASKS) == 20
    kinds = {t["oracle"]["kind"] for t in TASKS.values()}
    assert kinds <= {
        "answer_contains",
        "answer_contains_all",
        "answer_equals_command",
        "submission",
        "file_equals",
        "appended",
        "moved",
        "stickies_contains",
    }
    assert all(t["expect"] in ("complete", "stop") for t in TASKS.values())


@pytest.mark.parametrize("tid", sorted(ANSWERS))
def test_answer_oracles(tid, tmp_path):
    right, wrong = ANSWERS[tid]
    t = TASKS[tid]
    assert q19.check(t, answer=right, gets={}, scratch=tmp_path).ok
    assert not q19.check(t, answer=wrong, gets={}, scratch=tmp_path).ok


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS computer-name oracle requires scutil")
def test_the_computer_name_oracle_reads_the_machine(tmp_path):
    import subprocess

    name = subprocess.run(
        ["scutil", "--get", "ComputerName"], capture_output=True, text=True, check=False
    ).stdout.strip()
    if not name:
        pytest.skip("no computer name on this machine")
    t = TASKS["D13-computer-name"]
    assert q19.check(t, answer=f"It is called {name}.", gets={}, scratch=tmp_path).ok
    assert not q19.check(t, answer="Studio", gets={}, scratch=tmp_path).ok


SUBMITS = {
    "D05-ticket": (
        "/q19-ticket-done.html",
        {"subject": "Printer jam", "amount": "2"},
        {"subject": "Printer", "amount": "2"},
    ),
    "D06-delete-one-draft": ("/q19-deleted.html", {"id": "2"}, {"id": "3"}),
    "D07-settings": ("/q19-saved.html", {"digest": "on", "frequency": "monthly"}, {"frequency": "monthly"}),
    "D16-calc-to-ticket": (
        "/q19-ticket-done.html",
        {"subject": "Calc", "amount": "391"},
        {"subject": "Calc", "amount": "39"},
    ),
    "D18-domain-to-ticket": (
        "/q19-ticket-done.html",
        {"subject": "example.com", "amount": "1"},
        {"subject": "example", "amount": "1"},
    ),
    "D19-image-width-to-search": ("/search.html", {"q": "800"}, {"q": "600"}),
}


@pytest.mark.parametrize("tid", sorted(SUBMITS))
def test_submission_oracles_through_the_fixture_server(tid, tmp_path):
    path, right, wrong = SUBMITS[tid]
    t = TASKS[tid]
    for fields, expect in ((right, True), (wrong, False)):
        url, stop = serve()
        try:
            urllib.request.urlopen(f"{url}{path}?{urllib.parse.urlencode(fields)}").read()
            assert q19.check(t, answer=None, gets=stop.recorder.gets(), scratch=tmp_path).ok is expect
        finally:
            stop()
    url, stop = serve()  # a retry that submitted twice fails
    try:
        for _ in range(2):
            urllib.request.urlopen(f"{url}{path}?{urllib.parse.urlencode(right)}").read()
        assert (
            "2 submissions" in q19.check(t, answer=None, gets=stop.recorder.gets(), scratch=tmp_path).detail
        )
    finally:
        stop()


def test_file_oracles(tmp_path):
    t11 = TASKS["D11-replace-word"]
    (tmp_path / "d11.txt").write_text("The color of the sky.\nA color chart.\n")
    assert q19.check(t11, answer=None, gets={}, scratch=tmp_path).ok
    (tmp_path / "d11.txt").write_text("The color of the sky.\nA colour chart.\n")
    assert not q19.check(t11, answer=None, gets={}, scratch=tmp_path).ok
    t12 = TASKS["D12-save-new"]
    assert "does not exist" in q19.check(t12, answer=None, gets={}, scratch=tmp_path).detail
    (tmp_path / "d12.txt").write_text("Draft D12")
    assert q19.check(t12, answer=None, gets={}, scratch=tmp_path).ok
    t15 = TASKS["D15-quote-to-doc"]
    (tmp_path / "d15.txt").write_text("Authors:\nAlbert Einstein")
    assert q19.check(t15, answer=None, gets={}, scratch=tmp_path).ok
    (tmp_path / "d15.txt").write_text("Authors:\nAlbert Einstein\nAlbert Einstein\n")
    assert not q19.check(t15, answer=None, gets={}, scratch=tmp_path).ok
    t20 = TASKS["D20-move-file"]
    (tmp_path / "d20.txt").write_text("move me\n")
    (tmp_path / "archive").mkdir()
    assert not q19.check(t20, answer=None, gets={}, scratch=tmp_path).ok
    (tmp_path / "d20.txt").rename(tmp_path / "archive" / "d20.txt")
    assert q19.check(t20, answer=None, gets={}, scratch=tmp_path).ok


def test_setup_writes_start_states(tmp_path):
    q19.setup({"setup": ['write d.txt "a\\nb\\n"', "make_png i.png 64 48", "mkdir archive"]}, tmp_path)
    assert (tmp_path / "d.txt").read_text() == "a\nb\n" and (tmp_path / "archive").is_dir()
    head = (tmp_path / "i.png").read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and int.from_bytes(head[16:20], "big") == 64


class _Probe:
    def __init__(self, windows=None, sheets=0, display=("0",)):
        self.windows, self.sheets, self.display = windows or {}, sheets, list(display)

    def window_names(self, app):
        return self.windows.get(app, [])

    def sheet_count(self, app):
        return self.sheets

    def calculator_display(self):
        return self.display


def test_a_start_state_is_checked_not_assumed():
    """Review of 2026-09-29: opening an app is not resetting it (H09's Calculator showed the operator's
    8×7 = 56). Setup names what is wrong: a leftover display, a missing or foreign document, a sheet."""
    calc = {"setup": ["open_app Calculator"]}
    assert q19.start_problems(calc, probe=_Probe()) == []
    assert "not a cleared 0" in q19.start_problems(calc, probe=_Probe(display=("8×7", "56")))[0]
    docs = {"setup": ["open_in TextEdit a.txt", "open_in TextEdit b.txt"]}
    assert q19.start_problems(docs, probe=_Probe({"TextEdit": ["a.txt", "b.txt"]})) == []
    bad = q19.start_problems(docs, probe=_Probe({"TextEdit": ["a.txt", "other.txt"]}, sheets=1))
    assert bad == [
        "TextEdit: b.txt is not open",
        "TextEdit: other.txt is open from outside this trial",
        "TextEdit: a sheet is open",
    ]


def test_m3_development_oracles(tmp_path):
    from pathlib import Path

    t = q19.load(Path(__file__).resolve().parents[1] / "evals" / "tasks" / "m3-dev.yaml")
    assert not q19.check(t["X1-withdrawn-archive"], answer=None, gets={}, scratch=tmp_path).ok
    x3 = t["X3-unreserved-washers"]
    assert q19.check(x3, answer="60 washers", gets={}, scratch=tmp_path).ok
    assert not q19.check(x3, answer="155", gets={}, scratch=tmp_path).ok
    x2 = t["X2-one-signup"]
    for fields, expect in (
        ({"name": "Ada Byron", "team": "Blue"}, True),
        ({"name": "Ada Byron", "team": "Red"}, False),
    ):
        url, stop = serve()
        try:
            urllib.request.urlopen(f"{url}/m3-signup-done.html?{urllib.parse.urlencode(fields)}").read()
            assert q19.check(x2, answer=None, gets=stop.recorder.gets(), scratch=tmp_path).ok is expect
        finally:
            stop()
