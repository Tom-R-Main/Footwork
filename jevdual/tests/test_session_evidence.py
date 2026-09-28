"""Package A (docs/notebook/2026-09-26-a-session-evidence.md): the operator session's evidence cannot
overstate what happened, a named secret reaches no output, and a session stays on the tab it bound.

Each case is a status-audit probe (results/status-audit-20260926/probes.py) turned into a test that
fails on afe6d94: fake drivers and synthetic values, never the desktop.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace as NS

import pytest
from jevdual import browser_driver, session
from jevdual.authorize import Authorizer, action_for
from jevdual.menu import Candidate, Menu

MARKER = "SYNTHETIC-A3-MARKER"


def _field(value: str, label: str = "Name", id: int = 1, input_type: str | None = None) -> Candidate:
    return Candidate(
        id=id, label=label, role="textbox", operations=("type",), value=value, input_type=input_type
    )


def _nm(*cands: Candidate, page_text: str = "", sid: str = "s1") -> NS:
    return NS(
        menu=Menu(url="app://doc", title="Document", page_text=page_text, candidates=cands, by_operation={}),
        snapshot_id=sid,
        app_name="TextEdit",
        values={c.id: c.value for c in cands},
    )


def _state(tmp_path, before: NS, **pending) -> session.SessionState:
    st = session.SessionState(dir=str(tmp_path), app="TextEdit", pid=1, window_id=2, task="t")
    st.remember(before)
    st.pending = {
        "line": "type(Name)",
        "driver_effect": "confirmed",
        "error": None,
        "op": "type",
        "target_id": 1,
        "target_label": "Name",
        "intended": "Ada",
        "secret": False,
        **pending,
    }
    return st


def _receipt(tmp_path, before: NS, after: NS, **pending) -> dict:
    r = session.receipt_for(_state(tmp_path, before, **pending), after)
    assert r is not None
    return r


# ---- A2: a receipt follows the action's postcondition and never upgrades a refusal


def test_type_confirms_only_the_exact_value(tmp_path):
    r = _receipt(tmp_path, _nm(_field("")), _nm(_field("Ada Lovelace")))
    assert r["effect"] != "confirmed"
    assert _receipt(tmp_path, _nm(_field("")), _nm(_field("Ada")))["effect"] == "confirmed"


def test_trailing_whitespace_the_driver_strips_is_not_a_mismatch(tmp_path):
    # the Cua Driver strips trailing whitespace from values (Legible Loop v6, L2 evidence)
    r = _receipt(tmp_path, _nm(_field("")), _nm(_field("Ada")), intended="Ada ")
    assert r["effect"] == "confirmed"


def test_append_confirms_only_before_plus_insertion(tmp_path):
    already = _receipt(tmp_path, _nm(_field("Ada")), _nm(_field("Ada")), op="append")
    assert already["effect"] == "suspected_noop"
    done = _receipt(tmp_path, _nm(_field("Ada")), _nm(_field("AdaAda")), op="append")
    assert done["effect"] == "confirmed"
    replaced = _receipt(tmp_path, _nm(_field("Hello ")), _nm(_field("Ada")), op="append")
    assert replaced["effect"] != "confirmed"


def test_a_refused_step_stays_refused_whatever_the_field_holds(tmp_path):
    before = _nm(_field("Ada Lovelace"))
    after = _nm(_field("Ada Lovelace"), _field("", label="Other", id=2))  # something else changed
    for driver_effect in ("not sent", "not dispatched", "refused"):
        r = _receipt(
            tmp_path, before, after, driver_effect=driver_effect, error="requires_foreground: posture"
        )
        assert r["effect"] == "refused", driver_effect
        assert "requires_foreground" in r["evidence"]


def test_a_refusal_carried_on_the_receipt_is_kept():
    # the audit probe's form: the refusal arrives on the receipt, not in the pending action
    from jevdual.receipts import Receipt

    refused = Receipt(1, ("type(Name)",), "refused", "not sent", error="requires_foreground")
    pending = {"op": "type", "target_label": "Name", "target_id": 1, "intended": "Ada", "secret": False}
    r = session._field_receipt(refused, pending, _nm(_field("Ada")))
    assert r.effect == "refused" and "requires_foreground" in r.evidence


def test_two_fields_with_one_label_bind_to_the_chosen_id(tmp_path):
    before = _nm(_field("", id=1), _field("", id=7))
    after = _nm(_field("", id=1), _field("Ada", id=7))
    assert _receipt(tmp_path, before, after, target_id=7)["effect"] == "confirmed"
    assert _receipt(tmp_path, before, after, target_id=1)["effect"] != "confirmed"


# ---- A3: a named secret reaches no output, log or persisted file


def test_a_secret_in_an_ordinary_field_reaches_no_output(tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTWORK_SECRET_TOKEN", MARKER)
    before = _nm(_field(""))
    after = _nm(_field(MARKER), page_text=f'AXTextField "Name" = "{MARKER}"')
    st = _state(tmp_path, before, intended=None, secret=True)
    st.secret_names = ["TOKEN"]

    class Bridge:
        async def observe(self, **_):
            return after

    nm, receipt = asyncio.run(session.observe(st, Bridge()))
    assert receipt is not None and receipt["effect"] in ("confirmed", "unverifiable")
    rendered = session.render_observation(nm, receipt=receipt)
    assert MARKER not in rendered
    assert MARKER not in json.dumps(receipt)
    for f in tmp_path.rglob("*"):
        if f.is_file():
            assert MARKER not in f.read_text(errors="ignore"), f.name


def test_the_masked_value_is_still_compared_during_the_command(tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTWORK_SECRET_TOKEN", MARKER)
    st = _state(tmp_path, _nm(_field("")), intended=None, secret=True)
    st.secret_names = ["TOKEN"]
    wrong = session.receipt_for(st, _nm(_field("something else")), secret_value=MARKER)
    assert wrong is not None and wrong["effect"] != "confirmed"
    right = session.receipt_for(st, _nm(_field(MARKER)), secret_value=MARKER)
    assert right is not None and right["effect"] == "confirmed" and MARKER not in json.dumps(right)


# ---- A4: replacing existing content is a replacement at any length


def test_replacing_a_short_document_pauses():
    c = Candidate(
        id=1,
        label="Document",
        role="textbox",
        operations=("type",),
        value="First line.\n",
        input_type="textarea",
    )
    nm = _nm(c)
    action = action_for("type", nm, "s2", target=c, text="Second line.")
    assert asyncio.run(Authorizer().check(nm, action, task="Append a line")) is not None


def test_typing_into_an_empty_document_or_extending_it_does_not_pause():
    empty = Candidate(
        id=1, label="Document", role="textbox", operations=("type",), value="", input_type="textarea"
    )
    nm = _nm(empty)
    assert (
        asyncio.run(Authorizer().check(nm, action_for("type", nm, "s2", target=empty, text="Hi"), task="t"))
        is None
    )
    short = Candidate(
        id=1, label="Document", role="textbox", operations=("type",), value="Hi", input_type="textarea"
    )
    nm = _nm(short)
    extend = action_for("type", nm, "s2", target=short, text="Hi there")
    assert asyncio.run(Authorizer().check(nm, extend, task="t")) is None


# ---- A1: a browser session stays on the tab it bound


class _Chrome:
    """A DevTools-route double with two tabs on two pages; ``active`` is the tab the person has in front.
    Like the real Driver, its tab ids are handles for one connection: every ``configured_driver`` call
    (one per footwork command) hands out new ones (the Q13 oracle stage, 2026-09-28)."""

    def __init__(self) -> None:
        self.active = "A"
        self.pages = {"A": "https://example.invalid/a", "B": "https://example.invalid/b"}
        self.conn = 0
        self.dispatches: list[tuple[str, str | None]] = []

    def connect(self):
        self.conn += 1
        return self

    def _key(self, handle: str) -> str | None:
        key, _, conn = handle.partition("@")
        return key if conn == str(self.conn) and key in self.pages else None

    async def call_tool(self, name, args):
        a = json.loads(args)
        if name == "browser_prepare":
            p = {"status": "ok"}
        elif name == "get_browser_state" and "tab_id" not in a:
            p = {
                "status": "ok",
                "target_id": "target-1",
                "tabs": [
                    {"tab_id": f"{k}@{self.conn}", "active": k == self.active, "url": u}
                    for k, u in self.pages.items()
                ],
            }
        elif name == "get_browser_state":
            key = self._key(a["tab_id"])
            if key is None:
                p = {"status": "refused", "refusal": {"message": f"no tab {a['tab_id']}"}}
            else:
                p = {
                    "status": "ok",
                    "page": {"url": self.pages[key]},
                    "snapshot": {"id": f"snap-{key}"},
                    "refs": [
                        {"ref": f"snap-{key}:1", "role": "button", "name": "Continue", "actions": ["click"]}
                    ],
                }
        else:
            self.dispatches.append((name, self._key(a.get("tab_id") or "")))
            p = {"status": "ok"}
        return NS(structured_json=json.dumps(p), text="", is_error=False)


@pytest.fixture
def chrome(monkeypatch):
    c = _Chrome()
    monkeypatch.setattr(browser_driver, "configured_driver", lambda pid: c.connect())
    return c


def _browser_state(tmp_path) -> session.SessionState:
    return session.SessionState(dir=str(tmp_path), app="Chrome", pid=1, window_id=2, task="t", mode="browser")


async def _command(st):
    """One footwork command: a fresh connection, bind, observe (remembering the page), click."""
    _, bridge = await session.bind(st)
    nm, _ = await session.observe(st, bridge)
    await bridge.act(nm, "click", 1)


def test_a_later_command_stays_on_the_bound_tab(tmp_path, chrome):
    st = _browser_state(tmp_path)
    asyncio.run(_command(st))
    chrome.active = "B"  # the person switched tabs between commands
    asyncio.run(_command(st))
    # new handles on every connection, and still the same page's tab both times
    assert [t for _, t in chrome.dispatches] == ["A", "A"] and chrome.conn == 2


def test_a_closed_bound_tab_refuses_and_dispatches_nothing(tmp_path, chrome):
    st = _browser_state(tmp_path)
    asyncio.run(_command(st))
    del chrome.pages["A"]
    chrome.active = "B"
    with pytest.raises(RuntimeError, match="no longer open"):
        asyncio.run(_command(st))
    assert len(chrome.dispatches) == 1


def test_two_tabs_on_the_sessions_page_refuse(tmp_path, chrome):
    st = _browser_state(tmp_path)
    asyncio.run(_command(st))
    chrome.pages["C"] = chrome.pages["A"]  # the person opened the same page in another tab
    with pytest.raises(RuntimeError, match="2 tabs show the session's page"):
        asyncio.run(_command(st))
    assert len(chrome.dispatches) == 1
