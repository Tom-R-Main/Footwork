"""Every outcome the driver can return for a filmed click or insert, to what the command says (FP44).

The eighth review found a partial click that the command reported with the effect word alone: its text
was one the bridge did not recognise. So this file is a table, not a list of the cases thought of so
far. Each row is one outcome of the pinned driver; its text is checked to be in the pinned archive's
source, so a row cannot describe a driver that is not the one installed; and the rows are checked to
cover every variant of the driver's own outcome type for a click and every reason its insert function
returns. For each row, at the bridge and through the ``do`` command:

- a refusal reaches the person beginning with what was sent, inside the hundred characters the session
  prints of a refusal after the bridge's lead;
- an outcome that is not a refusal and not a completed action is marked, printed as an error under its
  mark with one sentence saying what was sent, and its receipt is unverifiable;
- a completed action prints nothing more than it did.

The first two are what "the command says so" means; nothing here is about the page's own change.
"""

# ruff: noqa: F811  (the scenario fixtures are imported by name)
from __future__ import annotations

import re
import tarfile
from pathlib import Path

import pytest

pytest.importorskip("cua_driver")

from jevdual.filmed import PAGE_MARKS

from tests.test_filmed_page_pointer import _act, focused, take  # noqa: F401
from tests.test_filmed_session import _did, _filmed_page, filmed, fw, world  # noqa: F401
from tests.test_session_scenarios import _id

ROOT = Path(__file__).resolve().parents[1]
TOOLS = "libs/cua-driver/rust/crates/cua-driver-core/src/browser/tools.rs"
LEAD = "the pointer moved; the {op} was then refused: "
EXT, TAB = "snap-1:1", "tab-b0e626b5-9e58-4f02-a686-dd195b85efa6"

LEFT = "the ref's node left the filmed point"
HID = "the page hid or replaced the pointer over the ref's node"
PARTIAL = ("sent part of a synthetic DOM click on {ext} in {tab_id}: {why} after {last}, so the rest of the sequence "
           "was not sent and no click event was; {count} events were sent and application effect is unverifiable. "
           "Refresh page state and verify the expected postcondition")
DETACHED = ("sent part of a synthetic DOM click on {ext} in {tab_id}: the ref's node left its document after {last}, "
            "so the rest of the sequence was not sent; application effect is unverifiable. Refresh page state and "
            "verify the expected postcondition")
INTERRUPTED = ("ran a synthetic DOM click on {ext} in {tab_id}, but its sequence did not report completing "
               "({reason}); some of its events may have been sent and application effect is unverifiable. Refresh "
               "page state and verify the expected postcondition")
DIALOG = ("dispatched synthetic DOM click on {ext} in {tab_id}; its handler opened a {} dialog that is blocking the "
          "page. Inspect and resolve it with browser_dialog (dialog_id {}) before any other action on this tab")
UNPRESSED = "no press or click was sent: {why} after {last} ({count} hover and move events were sent)"
INSERT_REFUSED = "nothing was inserted: {message}"
INSERT_UNKNOWN = "what reached the page is unknown: the filmed insert did not report completing ({why})"
HIDES = "the page hides or replaces the pointer over the ref's node (a pointer lock or its cursor style)"

#: (row, operation, the driver's outcome it is, the template in the driver's source, what fills it, the
#: refusal code or None, the mark or None, and the fact the person must be told)
ROWS = [
    # ---- click: refused with nothing sent
    ("off the point", "click", "Misplaced", "no event was sent: the ref's node is not under the filmed point", {},
     "browser_action_unavailable", None, "no event was sent"),
    ("pointer hidden", "click", "Misplaced", f"no event was sent: {HIDES}", {},
     "browser_action_unavailable", None, "no event was sent"),
    ("child frame", "click", "before", "no event was sent: filmed_point is for a ref in the tab's own frame", {},
     "browser_action_unavailable", None, "no event was sent"),
    ("no isolated world", "click", "before", "no event was sent: no isolated world could be made for the filmed click", {},
     "browser_action_unavailable", None, "no event was sent"),
    ("gone before the first event", "click", "Refuse", "the ref's node left its document before the click's first event", {},
     "browser_ref_stale", None, "no event was sent"),
    # ---- click: refused after hover events only
    ("left on hover", "click", "Left", UNPRESSED, {"why": LEFT, "last": "pointerover", "count": 1},
     "browser_action_unavailable", None, "no press or click was sent"),
    ("hidden on hover", "click", "Left", UNPRESSED, {"why": HID, "last": "mousemove", "count": 6},
     "browser_action_unavailable", None, "no press or click was sent"),
    # ---- click: not a refusal and not complete
    ("left once pressed", "click", "Left", PARTIAL, {"why": LEFT, "last": "mousedown", "count": 8},
     None, "click_stopped_after_press", "the click stopped after mousedown and no click event was sent"),
    ("left once released", "click", "Left", PARTIAL, {"why": LEFT, "last": "mouseup", "count": 10},
     None, "click_stopped_after_press", "the click stopped after mouseup and no click event was sent"),
    ("hidden once pressed", "click", "Left", PARTIAL, {"why": HID, "last": "pointerdown", "count": 7},
     None, "click_stopped_after_press", "the click stopped after pointerdown and no click event was sent"),
    ("removed once pressed", "click", "Partial", DETACHED, {"last": "mousedown"},
     None, "click_stopped_after_press", "the click stopped after mousedown and no click event was sent"),
    ("removed once released", "click", "Partial", DETACHED, {"last": "pointerup"},
     None, "click_stopped_after_press", "the click stopped after pointerup and no click event was sent"),
    ("removed on hover", "click", "Partial", DETACHED, {"last": "mouseover"},
     None, "click_stopped_before_press", "no press or click was sent"),
    ("threw", "click", "Interrupted", INTERRUPTED, {"reason": "the sequence threw"},
     None, "click_interrupted", "the click did not report completing (the sequence threw)"),
    ("no receipt", "click", "Interrupted", INTERRUPTED, {"reason": "no completion receipt"},
     None, "click_interrupted", "the click did not report completing (no completion receipt)"),
    ("malformed receipt", "click", "Interrupted", INTERRUPTED, {"reason": "a malformed receipt"},
     None, "click_interrupted", "the click did not report completing (a malformed receipt)"),
    ("dialog", "click", "Dialog", DIALOG, ("alert", "dlg-1"),
     None, "click_interrupted", "a alert dialog opened during the click"),
    ("call failed", "click", "Failed", "DOM click failed: {error}", {"error": "connection closed"},
     "error", None, "DOM click failed"),
    # ---- insert: refused with nothing inserted, one row per reason the function returns
    ("field removed", "type", "detached", INSERT_REFUSED, {"message": "the ref's node is no longer in its document"},
     "browser_ref_stale", None, "nothing was inserted"),
    ("field not focused", "type", "not_focused", INSERT_REFUSED,
     {"message": "the requested ref is not a focused editable element"},
     "browser_input_trust_unavailable", None, "nothing was inserted"),
    ("field not editable", "type", "not_editable", INSERT_REFUSED,
     {"message": "the requested ref is not a focused editable element"},
     "browser_input_trust_unavailable", None, "nothing was inserted"),
    ("field off the point", "type", "not_under_pointer", INSERT_REFUSED,
     {"message": "the ref's node is not under the filmed point"},
     "browser_action_unavailable", None, "nothing was inserted"),
    ("pointer hidden over the field", "type", "pointer_hidden", INSERT_REFUSED, {"message": HIDES},
     "browser_action_unavailable", None, "nothing was inserted"),
    ("field in a child frame", "type", "before", INSERT_REFUSED,
     {"message": "filmed_point is for a ref in the tab's own frame"},
     "browser_action_unavailable", None, "nothing was inserted"),
    ("no isolated world for the insert", "type", "before", INSERT_REFUSED,
     {"message": "no isolated world could be made for the filmed insert"},
     "browser_action_unavailable", None, "nothing was inserted"),
    # ---- insert: what was inserted is unknown
    ("document refused the insertion", "type", "command_refused", INSERT_UNKNOWN,
     {"why": "the page's document did not accept the insertion"},
     "browser_input_incomplete", None, "what reached the page is unknown"),
    ("insert threw", "type", "unknown", INSERT_UNKNOWN, {"why": "it threw"},
     "browser_input_incomplete", None, "what reached the page is unknown"),
]
IDS = [row[0] for row in ROWS]


def _text(row) -> str:
    template, fill = row[3], row[4]
    known = {"ext": EXT, "tab_id": TAB}
    return template.format(*fill, **known) if isinstance(fill, tuple) else template.format(**{**known, **fill})


def _reply(row) -> dict:
    """The arguments that make the stand-in driver answer as the driver does for this row. A field to
    type into has focus when Footwork reads it, twice: the outcome under test is the driver's."""
    op, code, text = row[1], row[5], _text(row)
    reads = {"locates": [focused(), focused()]} if op == "type" else {}
    if code == "error":
        return {"action": {}, "action_text": text, "action_error": True, **reads}
    if code is not None:
        # an action tool's refusal arrives as its typed result: the code only in the summary
        said = f"refused ({code}): {text}"
        return {"action": {"effect": "refused", "summary": said}, "action_text": said, **reads}
    return {"action": {"effect": "unverifiable", "summary": text}, "action_text": text, **reads}


@pytest.fixture(scope="module")
def driver_source() -> str:
    with tarfile.open(ROOT / "vendor/cua-driver/native-source.tar.gz") as archive:
        return re.sub(r"\\\n\s*", "", archive.extractfile(TOOLS).read().decode())


def test_every_rows_text_is_the_pinned_drivers(driver_source):
    for row in ROWS:
        template = row[3]
        assert template in driver_source or all(part in driver_source for part in template.split("{message}")), row[0]
        for value in (row[4].values() if isinstance(row[4], dict) else ()):
            if isinstance(value, str) and " " in value and row[0] != "call failed":
                assert value in driver_source, (row[0], value)


def test_the_rows_cover_every_outcome_the_driver_has(driver_source):
    """A new variant of the driver's click outcome, or a new reason from its insert function, has no
    row until someone writes one, and this fails until they do."""
    variants = set(re.findall(r"^    (\w+)", re.search(r"enum DomClickNext \{(.*?)\n\}", driver_source, re.DOTALL)[1],
                              re.MULTILINE))
    assert variants == {"Readback", "Dialog", "Refuse", "Misplaced", "Left", "Partial", "Interrupted", "Failed"}
    assert variants - {"Readback"} == {row[2] for row in ROWS if row[1] == "click"} - {"before"}
    insert = re.search(r'const DOM_FILMED_INSERT: &str = "(.*?)";\n', driver_source, re.DOTALL)[1]
    reasons = set(re.findall(r"why: (?:done \? null : )?'(\w+)'", insert))
    assert reasons == {"detached", "not_focused", "not_editable", "not_under_pointer", "pointer_hidden", "command_refused"}
    assert reasons == {row[2] for row in ROWS if row[1] == "type"} - {"before", "unknown"}
    # every mark a row expects is one the session says, and every click mark has a row
    assert {row[6] for row in ROWS if row[6]} == {mark for mark in PAGE_MARKS if mark.startswith("click_")}


@pytest.mark.parametrize("row", ROWS, ids=IDS)
def test_the_bridge_says_what_was_sent(take, row):
    _, op, _, _, _, code, mark, fact = row
    eff = _act(take, op, "Go" if op == "click" else "Name", None if op == "click" else "Ada", **_reply(row))
    assert eff.dispatched is not False  # none of these is "not sent": the driver was called
    if code is not None:
        assert eff.effect == "refused" and not set(eff.evidence) & set(PAGE_MARKS)
        assert eff.summary.startswith(LEAD.format(op=op))
        # inside what the session prints of a refusal
        assert fact in eff.summary[:100], eff.summary
    else:
        assert eff.effect == "unverifiable" and mark in eff.evidence
        assert eff.summary.startswith(fact) and "observe before acting again" in eff.summary, eff.summary
        # the driver's advice to a caller that can act on it is not passed on
        assert "browser_dialog" not in eff.summary and "Refresh page state" not in eff.summary


@pytest.mark.parametrize("row", ROWS, ids=IDS)
def test_the_command_says_what_was_sent(world, fw, filmed, monkeypatch, row):
    _, op, _, _, _, _, mark, fact = row
    go = _filmed_page(monkeypatch, fw, [], **_reply(row))
    words = ("click", go) if op == "click" else ("type", str(_id(fw.started, "Name")), "Ada")
    _, out, err = fw("do", *words, "--no-judge")
    said = next((line for line in out.splitlines() if line.startswith("dispatched ")), "")
    assert "driver says unverifiable (" in said and fact in said, (out, err)
    assert "not sent" not in said
    if mark is not None:
        assert f"driver says unverifiable ({mark}: {fact}" in said
        assert _did(fw)["error"].startswith(f"{mark}: ") and "input outcome unknown after error" in out


@pytest.mark.parametrize("op", ["click", "type"])
def test_a_completed_action_prints_nothing_more(world, fw, filmed, monkeypatch, op):
    go = _filmed_page(monkeypatch, fw, [], **({"locates": [focused(), focused()]} if op == "type" else {}))
    words = ("click", go) if op == "click" else ("type", str(_id(fw.started, "Name")), "Ada")
    code, out, err = fw("do", *words, "--no-judge")
    said = next(line for line in out.splitlines() if line.startswith("dispatched "))
    assert code == 0 and "(" not in said.split(": driver says ")[1] and "filmed take:" not in out, (out, err)
    assert _did(fw)["error"] is None


def test_outside_a_filmed_take_the_drivers_words_are_kept(take):
    for row in ROWS:
        op, code = row[1], row[5]
        eff = _act(take, op, "Go" if op == "click" else "Name", None if op == "click" else "Ada", filmed=False,
                   **_reply(row))
        assert not set(eff.evidence) & set(PAGE_MARKS), row[0]
        if code is None:
            assert eff.summary == _text(row)[:200], row[0]
        del take[:]
