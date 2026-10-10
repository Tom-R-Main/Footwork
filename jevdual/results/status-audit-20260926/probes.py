"""Offline audit probes. Fake drivers and synthetic values; no model or desktop calls.

Run from jevdual/: .venv/bin/python results/status-audit-20260926/probes.py
"""

import asyncio
import json
import logging
from types import SimpleNamespace as NS

from jevdual import browser_driver, session
from jevdual.agent import DualProcessAgent
from jevdual.authorize import Authorizer, action_for
from jevdual.menu import Candidate, Menu
from jevdual.receipts import Receipt


def field(value, label="Name", id=1):
    return Candidate(id=id, label=label, role="textbox", operations=("type",), value=value)


def nm(*cands):
    return NS(
        menu=Menu(url="https://example.invalid/", title="Document", page_text="", candidates=cands,
                  by_operation={}),
        values={c.id: c.value for c in cands},
    )


async def main():
    logging.disable(logging.CRITICAL)
    out = {}
    pending = {"op": "type", "target_label": "Name", "target_id": 1, "intended": "Ada", "secret": False}
    base = Receipt(1, ("type(Name)",), "suspected_noop", "unchanged")
    r = session._field_receipt(base, pending, nm(field("Ada Lovelace")))
    out["type_accepts_substring_instead_of_exact_value"] = {"effect": r.effect, "exact_match": False}
    r = session._field_receipt(base, {**pending, "op": "append"}, nm(field("Ada")))
    out["append_can_confirm_preexisting_text_without_new_insertion"] = {"effect": r.effect}
    refused = Receipt(1, ("type(Name)",), "refused", "not sent", error="requires_foreground")
    r = session._field_receipt(refused, pending, nm(field("Ada Lovelace")))
    out["field_receipt_overrides_refusal"] = {"effect": r.effect, "error": r.error}
    marker = "SYNTHETIC_AUDIT_MARKER"
    r = session._field_receipt(base, {**pending, "secret": True, "intended": None}, nm(field(marker)))
    out["secret_placeholder_in_nonpassword_field"] = {
        "synthetic_value_in_receipt": marker in r.evidence,
        "effect": r.effect,
    }

    async def fails(*args, **kwargs):
        raise RuntimeError("synthetic unavailable judge")

    stub = NS(
        s1_policy=NS(verifier=NS(verifier=NS(judge_destructive=fails))),
        _click_targets=lambda actions: [(1, "Continue", "form")],
        browser_session=NS(_cached_browser_state_summary=NS(url="https://example.invalid/", title="form")),
        task="inspect form", state=NS(n_steps=1),
    )
    out["browser_use_judge_failure"] = {
        "pause_returned": await DualProcessAgent._destructive_judgment(stub, []) is not None,
        "dispatch_performed": False,
    }
    current = "First line.\n"
    c = Candidate(id=1, label="Document", role="textbox", operations=("type",), value=current,
                  input_type="textarea")
    n = nm(c)
    action = action_for("type", n, "s2", target=c, text="Second line.")
    out["short_document_replacement"] = {
        "original_characters": len(current),
        "pause_returned": await Authorizer().check(n, action, task="Append a line") is not None,
        "dispatch_performed": False,
    }

    class FakeDriver:
        active = "tab-A"

        async def call_tool(self, name, args):
            args = json.loads(args)
            if name == "browser_prepare":
                payload = {"status": "ok"}
            elif name == "get_browser_state" and "tab_id" not in args:
                payload = {"status": "ok", "target_id": "browser-target", "tabs": [
                    {"tab_id": t, "active": t == self.active} for t in ("tab-A", "tab-B")
                ]}
            elif name == "get_browser_state":
                payload = {"status": "ok", "page": {"url": "https://example.invalid/"},
                           "snapshot": {"id": "snapshot"},
                           "refs": [{"ref": "snapshot:1", "role": "button", "name": "Continue",
                                     "actions": ["click"]}]}
            else:
                dispatches.append({"tool": name, "tab_id": args.get("tab_id")})
                payload = {"status": "ok"}
            return NS(structured_json=json.dumps(payload), text="synthetic", is_error=False)

    dispatches = []
    driver = FakeDriver()
    old = browser_driver.configured_driver
    browser_driver.configured_driver = lambda pid: driver
    try:
        state = session.SessionState(dir="unused", app="Chrome", pid=1, window_id=2,
                                     task="Use original tab", mode="browser")
        for active in ("tab-A", "tab-B"):
            driver.active = active
            _, bridge = await session.bind(state)
            obs = await bridge.observe()
            await bridge.act(obs, "click", 1)
        out["browser_session_rebind_after_active_tab_switch"] = {
            "fake_dispatches": dispatches,
            "persisted_tab_identity": "tab_id" in state.__dataclass_fields__,
        }
    finally:
        browser_driver.configured_driver = old
    print(json.dumps(out, indent=2))


asyncio.run(main())
