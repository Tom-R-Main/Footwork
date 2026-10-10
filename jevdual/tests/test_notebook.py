from pathlib import Path

from evals.notebook import load, render

NOTEBOOK = Path(__file__).resolve().parents[1] / "docs" / "notebook"

ENTRIES = """\
## P1 · prediction · 2026-09-26 10:00
Hypothesis: the tab is not persisted.
Test: switch tabs between commands.
Predicts: the second command refuses.
Against: it dispatches to the new tab.

## P2 · prediction · 2026-09-26 10:05
Hypothesis: substring confirmation.
Test: type Ada into Ada Lovelace.
Predicts: not confirmed.
Against: the scenario still confirms.

## U1 · update · 2026-09-26 11:00
Resolves: P2 = failed
Observed: the refusal was lost in receipt_for,
  before the field check ran.
Next: move the fix.
"""


def _nb(tmp_path: Path, text: str):
    p = tmp_path / "2026-09-26-x.md"
    p.write_text(text)
    return load(tmp_path)


def test_the_repository_notebook_is_well_formed():
    nb = load(NOTEBOOK)
    assert nb.errors == []
    assert nb.predictions(), "the notebook has at least one prediction"


def test_outcomes_join_predictions_and_continuation_lines(tmp_path):
    nb = _nb(tmp_path, ENTRIES)
    assert nb.errors == []
    outcome, by = nb.outcomes()["P2"]
    assert (outcome, by.id) == ("failed", "U1")
    assert by.fields["Observed"].endswith("before the field check ran.")
    out = render(nb)
    assert "2 predictions: 0 held, 1 failed, 0 inconclusive, 1 open" in out
    assert "P2" in out.split("failed (the diagnoses")[1]


def test_a_prediction_without_against_is_refused(tmp_path):
    nb = _nb(tmp_path, ENTRIES.replace("Against: it dispatches to the new tab.\n", ""))
    assert any("P1: prediction needs 'Against:'" in e for e in nb.errors)


def test_resolving_an_unknown_or_later_id_and_a_bad_outcome_are_errors(tmp_path):
    nb = _nb(tmp_path, ENTRIES.replace("Resolves: P2 = failed", "Resolves: P9 = held"))
    assert any("Resolves names 'P9'" in e for e in nb.errors)
    nb = _nb(tmp_path, ENTRIES.replace("Resolves: P2 = failed", "Resolves: P2 = mostly"))
    assert any("Resolves must be" in e for e in nb.errors)


def test_duplicate_ids_bad_kinds_and_bad_headings_are_errors(tmp_path):
    text = ENTRIES + "\n## P1 · musing · 2026-09-26 12:00\n\n## loose heading\n"
    errs = _nb(tmp_path, text).errors
    assert any("id already used" in e for e in errs)
    assert any("kind 'musing'" in e for e in errs)
    assert any("heading is not" in e for e in errs)
