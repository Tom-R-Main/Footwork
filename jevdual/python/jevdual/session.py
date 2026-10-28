"""A footwork session: the operator is System 2 (P0, 2026-09-25).

The harness observes, declares what it sees, enforces the one authorization boundary, issues a receipt
for every action and verifies every done. The decisions on escalated steps belong to whoever holds the
session: a person at a terminal, or an agent such as a Claude Code session. Each command is one
invocation, so the driver process is fresh each time; the session directory carries the binding, the
task, the last observation, the memory lines and a JSONL log.

    footwork start "task" --app "Google Chrome" [--url ...] [--require "a; b"] [--authorize "Save"]
    footwork look                     observe: elements, page text, the receipt for the last action
    footwork s1 [--act]               System 1's proposal on the current observation (Jev, one call)
    footwork do click 65              dispatch through the boundary, settle, reobserve, receipt
    footwork do type 5 "text"         {NAME} in text is read from $FOOTWORK_SECRET_NAME, never printed
    footwork do key Down | hotkey cmd t | menu "File > Save" | enter 5 | scroll 39 | append 12 "line"
    footwork done "answer"            the verifier judges the done against the page and the trail
    footwork read 12 --as price       carry an element's value (or label) with where it came from
    footwork do append 5 @price --from DIR   write a carried value (package G); receipt names its source
    footwork check-file PATH @price   the exact saved-file oracle: a line equals the carried text
    footwork status
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import dataclasses
import html
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jevdual import carry, grants
from jevdual.menu import Candidate, Menu
from jevdual.native import NativeBridge, NativeBridgeError, NativeMenu

SETTLE_S = 1.0
_CAND_FIELDS = ("id", "label", "role", "operations", "value", "input_type", "checked", "selected", "section")


@dataclass
class SessionState:
    dir: str
    app: str
    pid: int
    window_id: int
    task: str
    requirements: tuple[str, ...] = ()
    authorized: tuple[str, ...] = ()
    answer_expected: bool = False
    step: int = 0
    status: str = "open"
    memory: list[str] = field(default_factory=list)
    #: the last observation, enough to rebuild a Menu for the effect diff and to check ids are current
    last_url: str = ""
    last_title: str = ""
    last_page_text: str = ""
    last_candidates: list[dict[str, Any]] = field(default_factory=list)
    last_snapshot: str = ""
    pending: dict[str, Any] | None = None  # the action dispatched by the last `do`, awaiting its receipt
    #: "native" (accessibility route) or "browser" (the Driver's DevTools route on footwork's Chrome)
    mode: str = "native"
    #: the execution posture (jevdual.posture): background_only unless the operator granted more at start
    posture: str = "background_only"
    #: browser mode: the tab this session bound at start; later commands refuse rather than follow the
    #: active tab (status audit 2026-09-26, probe browser_session_rebind_after_active_tab_switch)
    browser_tab: str = ""
    #: names of the secrets typed in this session (``{NAME}``); their values are scrubbed from every
    #: observation before it is rendered, persisted or shown to a model. Names only, never values.
    secret_names: list[str] = field(default_factory=list)
    #: Visual answers belong to one observation generation and are advisory only.
    visual_generation: str = ""
    last_visual_check: dict[str, Any] | None = None

    @property
    def path(self) -> Path:
        return Path(self.dir)

    def save(self) -> None:
        (self.path / "session.json").write_text(json.dumps(asdict(self), indent=1))

    @classmethod
    def load(cls, d: Path) -> SessionState:
        try:
            raw = json.loads((d / "session.json").read_text())
        except FileNotFoundError:
            raise NativeBridgeError(
                "session_not_found",
                f"No initialized session at {d}; start must complete successfully before using this session.",
            ) from None
        raw["requirements"] = tuple(raw.get("requirements") or ())
        raw["authorized"] = tuple(raw.get("authorized") or ())
        return cls(**raw)

    def log(self, rec: dict[str, Any]) -> None:
        with (self.path / "session.jsonl").open("a") as fh:
            fh.write(json.dumps({"t": time.time(), "step": self.step, **rec}, default=str) + "\n")

    def last_menu(self) -> Menu | None:
        if not self.last_candidates:
            return None
        cands = tuple(Candidate(**{**c, "operations": tuple(c["operations"])}) for c in self.last_candidates)
        return Menu(
            url=self.last_url,
            title=self.last_title,
            page_text=self.last_page_text,
            candidates=cands,
            by_operation={},
        )

    def remember(self, nm: NativeMenu) -> None:
        self.visual_generation = uuid.uuid4().hex
        self.last_visual_check = None
        self.last_url = nm.menu.url
        self.last_title = nm.menu.title
        self.last_page_text = nm.menu.page_text
        self.last_candidates = [{k: getattr(c, k) for k in _CAND_FIELDS} for c in nm.menu.candidates]
        self.last_snapshot = nm.snapshot_id


def session_dir(arg: str | None) -> Path:
    return Path(arg or os.environ.get("FOOTWORK_SESSION") or "runs/session")


# ---- observation and receipts --------------------------------------------------------------


def receipt_for(
    state: SessionState, nm: NativeMenu, *, secret_value: str | None = None
) -> dict[str, Any] | None:
    """The receipt for the pending action: the effect diff between the observation it was taken on and
    this one, in the driver's words. ``nm`` is the raw observation; the diff is taken on its scrubbed
    form (the remembered one is scrubbed), and ``secret_value`` is the secret the command just typed,
    held in memory for the comparison and never written."""
    from jevdual.effects import diff
    from jevdual.receipts import receipt_from_effect, receipt_text

    if state.pending is None:
        return None
    prev = state.last_menu()
    if prev is None:
        return None
    eff = diff(prev, scrub(state, nm, secret_value).menu)
    r = receipt_from_effect(
        state.step,
        (state.pending.get("line", "action"),),
        eff,
        url_after=nm.menu.url,
        error=state.pending.get("error"),
    )
    r = _field_receipt(r, state.pending, nm, prev=prev, secret_value=secret_value)
    r = _save_receipt(r, state.pending)
    r = _outside_receipt(r, state.pending)
    if r.effect == "suspected_noop" and state.pending.get("driver_effect") == "confirmed":
        # the driver confirmed the press but nothing on the menu changed: say both
        text = receipt_text(r) + " The driver reported the press as delivered."
    else:
        text = receipt_text(r)
    out = {"effect": r.effect, "evidence": r.evidence, "text": text}
    for v in _secret_values(state, secret_value):
        out = {k: w.replace(v, "{secret}") for k, w in out.items()}
    return out


def _outside_receipt(r: Any, pending: dict[str, Any]) -> Any:
    """Q13a: two effects that happen outside the observed window. A menu item's effect (File > Open) may
    land in another app, so the window's own change cannot confirm it; a save is the exception, confirmed
    by its readback. A browser navigation Chrome ends with ERR_ABORTED is what a navigation that becomes a
    download looks like, so it is not "not applied": what it did is outside the page."""
    if pending.get("save_readback"):
        return r
    error = str(pending.get("error") or "")
    if pending.get("op") == "navigate" and "ERR_ABORTED" in error:
        return dataclasses.replace(
            r,
            effect="unverifiable",
            evidence="the navigation ended with ERR_ABORTED, as one that becomes a download does; the page did "
            "not change, and a file may have been saved (check the downloads folder)",
        )
    if str(pending.get("app") or "").startswith("Finder") and pending.get("op") in ("type", "append"):
        # E3: writing a Finder name cell shows the new name without renaming the file; Finder renames
        # only when its own edit commits, which this observation does not show
        return dataclasses.replace(
            r,
            effect="unverifiable",
            evidence=f"Finder's name field shows the text ({r.evidence}); whether the file itself was renamed "
            "is not observable here (a written name field is not a committed rename)",
        )
    if pending.get("op") == "menu" and r.effect == "confirmed":
        return dataclasses.replace(
            r,
            effect="unverifiable",
            evidence=f"the window changed ({r.evidence}); a menu item's effect may be in another window or app, "
            "which this observation does not show",
        )
    return r


def _save_receipt(r: Any, pending: dict[str, Any]) -> Any:
    rb = pending.get("save_readback")
    if not rb:
        return r
    if rb.get("ok") is True:
        return dataclasses.replace(r, effect="confirmed", evidence=f"saved: {rb['detail']}")
    if rb.get("ok") is False:
        return dataclasses.replace(r, effect="partial", evidence=f"save not confirmed: {rb['detail']}")
    return dataclasses.replace(r, effect="unverifiable", evidence=f"save unverifiable: {rb['detail']}")


def _secret_values(state: SessionState, extra: str | None = None) -> list[str]:
    """The values to scrub: every secret named in this session, from the environment, plus the one in
    hand. Values under three characters are not scrubbed (they would erase ordinary text)."""
    vals = [os.environ.get(f"FOOTWORK_SECRET_{n}") or "" for n in state.secret_names]
    if extra:
        vals.append(extra)
    return sorted({v for v in vals if len(v) >= 3}, key=len, reverse=True)


def scrub(state: SessionState, nm: Any, extra: str | None = None) -> Any:
    """``nm`` with every secret value replaced by ``{secret}`` in the page text, title, URL and each
    element's label and value: what is rendered, persisted, diffed and shown to a model."""
    vals = _secret_values(state, extra)
    if not vals:
        return nm

    def s(x: Any) -> Any:
        if not isinstance(x, str):
            return x
        for v in vals:
            x = x.replace(v, "{secret}")
        return x

    m = nm.menu
    menu = dataclasses.replace(
        m,
        url=s(m.url),
        title=s(m.title),
        page_text=s(m.page_text),
        candidates=tuple(dataclasses.replace(c, label=s(c.label), value=s(c.value)) for c in m.candidates),
    )
    if dataclasses.is_dataclass(nm):
        out = dataclasses.replace(nm, menu=menu)
    else:
        out = copy.copy(nm)
        out.menu = menu
    if isinstance(getattr(out, "values", None), dict):
        out.values = {k: s(v) for k, v in out.values.items()}
    return out


def _bound_field(menu: Menu | None, pending: dict[str, Any]) -> Candidate | None:
    """The field the action was aimed at: the one text element with its label, or, when several share
    the label, the one with the chosen id. Never the first of several."""
    if menu is None:
        return None
    low = pending["target_label"].casefold()
    same = [c for c in menu.candidates if c.label.casefold() == low and "type" in c.operations]
    if len(same) == 1:
        return same[0]
    if len(same) > 1:
        return next((c for c in same if c.id == pending.get("target_id")), None)
    return menu.candidate(pending.get("target_id", -1))


#: characters a password field shows in place of what it holds
_MASK_CHARS = frozenset("•●*·∙")


def _field_receipt(
    r: Any, pending: dict[str, Any], nm: Any, *, prev: Menu | None = None, secret_value: str | None = None
) -> Any:
    """A receipt for ``type`` or ``append`` states the field's postcondition, not the element count: on
    2026-09-25 typing into Wikipedia's search box added 49 elements (the suggestion list), the receipt
    said confirmed, and the query went out empty. ``type`` is confirmed when the field holds exactly
    the intended text, ``append`` when it holds its earlier value plus the insertion; trailing
    whitespace is not compared, because the Cua Driver strips it from values. A step that was not
    dispatched stays ``refused`` whatever the field holds, and a secret's value is never quoted."""
    if pending.get("op") not in ("type", "append") or not pending.get("target_label"):
        return r
    label = pending["target_label"]
    error = pending.get("error") or getattr(r, "error", None)
    if (
        r.effect == "refused"
        or error
        or pending.get("driver_effect") in ("not sent", "not dispatched", "refused")
    ):
        return dataclasses.replace(
            r, effect="refused", evidence=f"not applied: {str(error or pending.get('driver_effect'))[:120]}"
        )
    field = _bound_field(nm.menu, pending)
    if field is None:
        return dataclasses.replace(
            r, effect="unverifiable", evidence=f"{label!r} is not on the fresh observation as one field"
        )
    secret = bool(pending.get("secret"))
    if field.input_type == "password":
        # a password field exposes whether it holds something, never what: that is not a confirmation
        ok = bool(field.has_value)
        return dataclasses.replace(
            r,
            effect="unverifiable" if ok else "suspected_noop",
            evidence=f"{label!r} holds {'a value' if ok else 'nothing'}; the {{secret}} typed into a "
            "password field cannot be read back",
        )
    holds = field.value or ""
    if secret and holds and set(holds) <= _MASK_CHARS:
        # Q19 R3: a browser password field reads back as bullets and is not marked as a password; it
        # cannot confirm what was typed, only how many characters it holds
        n = len(secret_value) if secret_value else None
        same = ", the length of the {secret}" if n == len(holds) else (f", not the {n} typed" if n else "")
        return dataclasses.replace(
            r,
            effect="unverifiable",
            evidence=f"{label!r} is masked and holds {len(holds)} characters{same}; its content cannot be read back",
        )
    was = _bound_field(prev, pending)
    before = (was.value or "") if was is not None else None
    if secret and secret_value is None:
        changed = before is not None and holds != before
        return dataclasses.replace(
            r,
            effect="unverifiable",
            evidence=f"{label!r} {'changed' if changed else 'did not change'}; a secret is compared only during the command that typed it",
        )
    intended = (secret_value if secret else pending.get("intended")) or ""
    alternates: tuple[str, ...] = ()
    if pending["op"] == "type":
        expected: str | None = intended
    else:
        expected = None if before is None else before + intended
        if before and pending.get("mode", "native") == "native":
            # the native bridge appends on a new line unless the exact value already ends with one;
            # the Driver strips that trailing newline from ``before``, so either way the field ends
            # up as the earlier text, one line break, and the insertion (G1 pilot, 2026-09-26)
            alternates = (before + "\n" + intended,)

    def show(x: str) -> str:
        return "{secret}" if secret else repr(x[:80])

    if expected is None:
        return dataclasses.replace(
            r, effect="unverifiable", evidence=f"{label!r} holds {show(holds)}; no earlier value to compare"
        )
    if any(holds.rstrip() == e.rstrip() for e in (expected, *alternates)):
        return dataclasses.replace(r, effect="confirmed", evidence=f"{label!r} now holds {show(holds)}")
    if before is not None and holds == before:
        return dataclasses.replace(
            r, effect="suspected_noop", evidence=f"{label!r} still holds {show(holds)}, not {show(expected)}"
        )
    what = "the text typed" if pending["op"] == "type" else "its earlier value plus the insertion"
    return dataclasses.replace(
        r, effect="partial", evidence=f"{label!r} changed and holds {show(holds)}, not {what}"
    )


def render_observation(nm: NativeMenu, *, text_chars: int = 3000, receipt: dict[str, Any] | None) -> str:
    m = nm.menu
    lines = []
    if receipt:
        lines.append(f"receipt: {receipt['text']}")
    flags = ", ".join(
        f"{k} {v}" for k, v in m.omitted.items() if k in ("elements_incomplete", "truncated", "cap")
    )
    lines.append(f"{nm.app_name}: {m.title!r}{'  [' + flags + ']' if flags else ''}")
    if m.omitted.get("elements_incomplete"):
        # Q19 R4: a partial view read as the whole page (D02: 10 of ~117 products)
        lines.append(
            "note: this observation is incomplete; the page holds more than is shown here, and an answer "
            "drawn from it covers only what is shown"
        )
    lines.append(f"{len(m.candidates)} elements:")
    for c in m.candidates:
        extra = f" = {c.value!r}" if c.value else ""
        if c.checked is not None:
            extra += f" checked={c.checked}"
        sect = f"  [{c.section}]" if c.section else ""
        lines.append(f"  [{c.id:>4}] {c.role:<10} {c.label!r}{extra}{sect}")
    txt = m.page_text
    lines.append(
        f"page text ({len(txt)} chars{', first ' + str(text_chars) if len(txt) > text_chars else ''}):"
    )
    lines.append(txt[:text_chars])
    return "\n".join(lines)


async def bind(state: SessionState):
    if state.mode == "browser":
        from jevdual.browser_driver import BrowserBridge, configured_driver

        driver = configured_driver(state.pid)
        from jevdual.posture import ExecutionPolicy

        bridge = BrowserBridge(driver, state.pid, state.window_id, policy=ExecutionPolicy(state.posture))  # type: ignore[arg-type]
        # the tab is the one showing the page this session last observed: the Driver's tab ids are new on
        # every connection, so the page is the identity that survives between commands
        await bridge.attach(expect_url=state.last_url or None)
        state.browser_tab = bridge.tab_id or ""
        return driver, bridge
    from cua_driver import CuaDriver

    driver = CuaDriver.create(embedded=True)
    return driver, _native_bridge(driver, state.pid, state.window_id, state.posture)


def _native_bridge(driver: Any, pid: int, wid: int, posture: str) -> NativeBridge:
    """The operator's bridge: the session's posture, and a live identity check before every element
    action (the person may have changed the window since the operator looked)."""
    from jevdual.posture import ExecutionPolicy

    return NativeBridge(driver, pid, wid, policy=ExecutionPolicy(posture), live_check=True)  # type: ignore[arg-type]


async def observe(
    state: SessionState, bridge: NativeBridge, *, secret_value: str | None = None
) -> tuple[NativeMenu, dict[str, Any] | None]:
    shot: str | None = None
    if state.secret_names or secret_value:
        # the observation is scrubbed below, but pixels cannot be: once the session has handled a secret,
        # no screenshot is written. Keyed on the session's own record, not on whether the value is still
        # in the environment or long enough to scrub (secondary audit 2026-09-27, both rounds)
        state.log({"kind": "screenshot withheld", "reason": "the session holds a secret"})
    else:
        shots = state.path / "screenshots"
        shots.mkdir(exist_ok=True)
        shot = str(shots / f"obs-{state.step:03d}-{int(time.time())}.png")
    nm = await bridge.observe(screenshot_path=shot)
    return finish_observation(state, nm, secret_value=secret_value)


def finish_observation(
    state: SessionState, nm: NativeMenu, *, secret_value: str | None = None, generation: str | None = None
) -> tuple[NativeMenu, dict[str, Any] | None]:
    """Reconcile the prior action before replacing its observation baseline."""
    receipt = receipt_for(state, nm, secret_value=secret_value)
    nm = scrub(state, nm, secret_value)
    if receipt is not None and state.pending is not None:
        word = receipt["effect"]
        line = state.pending.get("line", "action")
        state.memory.append(f"step {state.step}: {line} -> {word}")
        state.log({"kind": "receipt", "action": state.pending, **receipt})
        state.pending = None
    state.remember(nm)
    if generation is not None:
        state.visual_generation = generation
    state.save()
    return nm, receipt


# ---- commands --------------------------------------------------------------------------------


async def cmd_start(args: Any) -> int:
    from cua_driver import CuaDriver

    from jevdual.native import address_bar, find_window, navigate_in_window, new_window, require_accessibility

    if not getattr(args, "browser", False):
        require_accessibility()

    d = session_dir(args.session)
    d.mkdir(parents=True, exist_ok=True)
    # a new session inherits nothing: no carried value or destination snapshot from an older one in
    # the same directory can be used as if it were read in this one (secondary audit: stale carries)
    for old in ("session.json", "session.jsonl", carry.CARRIES, carry.SNAPSHOTS, grants.GRANTS):
        (d / old).unlink(missing_ok=True)
    if getattr(args, "browser", False):
        return await _start_browser(args, d)
    driver = CuaDriver.create(embedded=True)
    try:
        try:
            pid, wid, title = await find_window(driver, args.app, title_contains=args.window or "")
        except LookupError as exc:
            # not running, installed but not running, or no on-screen window: say which, no traceback
            print(f"not starting: {exc}", file=sys.stderr)
            return 2
        state = SessionState(
            dir=str(d),
            app=args.app,
            pid=pid,
            window_id=wid,
            task=args.task,
            requirements=_split(args.require, ";"),
            authorized=_split(args.authorize, ","),
            answer_expected=args.answer,
            posture=getattr(args, "mode", None) or "background_only",
        )
        bridge = _native_bridge(driver, pid, wid, state.posture)
        print(f"bound {args.app} window {wid} {title[:60]!r} ({state.posture})")
        if args.url:
            from urllib.parse import urlsplit

            # the session gets a window of its own; the person keeps theirs
            try:
                wid, title = await new_window(bridge, args.app)
            except RuntimeError as exc:
                if "requires_foreground" in str(exc) or "human_active" in str(exc):
                    print(
                        f"not starting: opening a session window takes the foreground (Command-N) and this "
                        f"session is {state.posture}. Use --browser for a web page, bind a window you opened "
                        "with --window, or grant --mode foreground_permitted.",
                        file=sys.stderr,
                    )
                    return 2
                raise
            state.window_id = wid
            bridge = _native_bridge(driver, pid, wid, state.posture)
            print(f"opened a new window {wid} for the session")
            nm = await navigate_in_window(bridge, args.url)
            bar = address_bar(nm)
            shown = (bar.value or "") if bar else ""
            host = urlsplit(args.url).netloc
            if host and host not in shown and host not in nm.menu.page_text:
                print(f"the address bar reads {shown[:80]!r}, not {host}; not starting", file=sys.stderr)
                return 2
            print(f"opened {args.url} in a new tab")
        state.log({"kind": "start", "task": args.task, "requirements": state.requirements, "app": args.app})
        nm, _ = await observe(state, bridge)
        print(render_observation(nm, text_chars=args.text, receipt=None))
        print(f"\nsession: {d}  (export FOOTWORK_SESSION={d} to omit --session)")
    finally:
        await driver.shutdown()
    return 0


async def _start_browser(args: Any, d: Path) -> int:
    """A session on footwork's own Chrome through the Driver's browser mode (jevdual.browser_driver)."""
    from jevdual.browser_driver import bind_footwork_chrome
    from jevdual.posture import ExecutionPolicy

    posture = getattr(args, "mode", None) or "background_only"
    driver, bridge = await bind_footwork_chrome(args.url, policy=ExecutionPolicy(posture))  # type: ignore[arg-type]
    try:
        state = SessionState(
            dir=str(d),
            app="Google Chrome (footwork)",
            pid=bridge.pid,
            window_id=bridge.window_id,
            task=args.task,
            requirements=_split(args.require, ";"),
            authorized=_split(args.authorize, ","),
            answer_expected=args.answer,
            mode="browser",
            posture=posture,
            browser_tab=bridge.tab_id or "",
        )
        print(f"bound footwork's Chrome (pid {bridge.pid}) window {bridge.window_id}, tab {bridge.tab_id}")
        if args.url:
            eff = await bridge.navigate(args.url)
            print(f"navigate {args.url}: {eff.effect} {eff.summary[:80]}")
            await asyncio.sleep(2.0)
        state.log({"kind": "start", "task": args.task, "requirements": state.requirements, "mode": "browser"})
        nm, _ = await observe(state, bridge)
        print(render_observation(nm, text_chars=args.text, receipt=None))
        print(f"\nsession: {d}  (export FOOTWORK_SESSION={d} to omit --session)")
    finally:
        await driver.shutdown()
    return 0


async def cmd_look(args: Any) -> int:
    state = SessionState.load(session_dir(args.session))
    driver, bridge = await bind(state)
    try:
        nm, receipt = await observe(state, bridge)
        menus = None
        if getattr(args, "menu_bar", False) and state.mode == "native":
            # Q19 R4: the app's menu items, so a menu path is chosen from what exists (D09 guessed one); read
            # through AX, since the observation's element cap drops them
            from jevdual import ax

            menus = ax.menu_paths(state.pid)
    finally:
        await driver.shutdown()
    print(render_observation(nm, text_chars=args.text, receipt=receipt))
    if menus is not None:
        print(f"menu bar ({len(menus)} items):")
        for path in menus:
            print(f"  {path}")
    return 0


async def cmd_inspect_target(args: Any) -> int:
    """Private fresh visual binding. It judges nothing, grants nothing and executes nothing."""
    from jevdual.visual_evidence import Bounds, Surface, bind_visual

    directory = session_dir(args.session)
    state = SessionState.load(directory)

    def refused(reason: str, message: str) -> int:
        print(f"not inspected: {reason}: {message}", file=sys.stderr)
        state.log({"kind": "visual inspection refused", "reason": reason})
        return 4

    if state.path.resolve() != directory.resolve():
        print("not inspected: session_path_mismatch: session directory binding changed", file=sys.stderr)
        return 4
    # This precedes driver creation and capture. Pixels cannot scrub a handled secret.
    if state.secret_names:
        return refused("screenshot_withheld", "the session has handled a secret")
    if state.mode != "native":
        return refused("surface_unsupported", "browser target/capture geometry is not yet qualified")
    if not args.postcondition.strip():
        return refused("postcondition_missing", "provide the required effect to inspect")
    inspection = state.path / "inspection"
    if inspection.is_symlink():
        return refused("inspection_path_unsafe", "inspection directory must stay inside this session")
    inspection.mkdir(exist_ok=True)
    identifier = uuid.uuid4().hex
    screenshot = inspection / f"{identifier}.png"
    driver = None
    nm = None
    capture_failed = False
    try:
        driver, bridge = await bind(state)
        nm = await bridge.observe(screenshot_path=str(screenshot))
    except Exception:  # noqa: BLE001 - no raw driver diagnostics or captured text in this refusal
        capture_failed = True
    finally:
        if driver is not None:
            try:
                await driver.shutdown()
            except Exception:  # noqa: BLE001 - driver cleanup failure also stops this inspection
                capture_failed = True
    if capture_failed or nm is None:
        return refused("capture_failed", "the native driver could not complete the fresh capture")
    if nm.pid != state.pid or nm.window_id != state.window_id:
        return refused("surface_mismatch", "the observation belongs to a different window")
    if nm.truncated or nm.degraded or nm.menu.omitted.get("cap"):
        return refused("observation_incomplete", "the observation is truncated or degraded")
    target = args.target
    if target.lstrip("-").isdigit():
        candidate = nm.menu.candidate(int(target))
    else:
        if not nm.elements_complete or nm.menu.omitted.get("duplicate"):
            return refused(
                "label_search_incomplete",
                "use an observed numeric ID; this AX projection cannot prove label uniqueness",
            )
        resolved, why = resolve_label(nm, target)
        if resolved is None:
            return refused("target_unresolved", why)
        candidate = nm.menu.candidate(resolved)
    if candidate is None:
        return refused("target_missing", "the offered ID is absent from the fresh observation")
    if target.lstrip("-").isdigit():
        previous = next((item for item in state.last_candidates if item["id"] == candidate.id), None)
        if previous and (previous["label"] != candidate.label or previous["role"] != candidate.role):
            return refused(
                "target_identity_changed",
                "the ID identifies a different target than the last session observation",
            )
    if args.operation not in candidate.operations:
        return refused("operation_unsupported", "the fresh target does not offer this operation")
    token = nm.token(candidate.id)
    frame = nm.frames.get(candidate.id)
    if not token or frame is None:
        return refused("target_binding_missing", "the fresh target lacks its token or bounds")
    capture = nm.visual_capture
    if capture is None:
        return refused(
            nm.visual_capture_error or "capture_unavailable", "fresh bound-window capture metadata is missing"
        )
    try:
        evidence = bind_visual(
            png=screenshot.read_bytes(),
            surface=Surface(kind="native", pid=nm.pid, window_id=nm.window_id, tab_id=None),
            observation_id=nm.snapshot_id,
            captured_at=capture.captured_at,
            viewport=Bounds(*capture.viewport),
            target_id=str(candidate.id),
            target_token=token,
            target_bounds=Bounds(*frame),
            operation=args.operation,
            postcondition=args.postcondition,
        )
        record = evidence.to_dict()
        if evidence.dimensions != (capture.width, capture.height):
            return refused(
                "capture_dimensions_mismatch", "PNG dimensions differ from the fresh Driver capture"
            )
    except (ValueError, OSError) as exc:
        return refused(getattr(exc, "code", getattr(exc, "reason", "invalid_visual_evidence")), str(exc))
    manifest = inspection / f"{identifier}.json"
    preview = inspection / f"{identifier}.html"
    record["binding_sha256"] = evidence.binding_sha256
    record["inspection"] = {
        "screenshot": screenshot.name,
        "preview": preview.name,
        "elements_complete": nm.elements_complete,
        "driver_reported_scale": capture.reported_scale,
        "target_label": candidate.label,
        "authority": "read-only evidence; no model judgment, dispatch, consent or verified postcondition",
        "coverage_warning": None
        if nm.elements_complete
        else "AX projection proves this observed target's presence, not absence or global label uniqueness",
    }
    manifest.write_text(json.dumps(record, indent=2))
    preview.write_text(_inspection_preview(record, manifest.name), encoding="utf-8")
    state.visual_generation = uuid.uuid4().hex
    state.last_visual_check = None
    state.save()
    state.log(
        {
            "kind": "visual inspection",
            "manifest": str(manifest),
            "preview": str(preview),
            "observation_id": nm.snapshot_id,
            "target_id": candidate.id,
        }
    )
    print(f"inspection: {manifest}")
    print(f"preview: {preview}")
    print("read-only evidence recorded; no action or postcondition was verified")
    return 0


def _inspection_preview(record: dict[str, Any], manifest_name: str) -> str:
    """Static review of the original capture with a CSS target outline; no executable content."""
    escape = html.escape
    image, target = record["image"], record["target"]
    left, top, right, bottom = target["pixel_bounds"]
    width, height = image["width"], image["height"]
    overlay = f"left:{left / width * 100:.8f}%;top:{top / height * 100:.8f}%;width:{(right - left) / width * 100:.8f}%;height:{(bottom - top) / height * 100:.8f}%"
    target_label = record["inspection"]["target_label"]
    scope = f"Read-only native window {record['surface']['window_id']}, process {record['surface']['pid']}; captured {record['captured_at']}. No model judgment, action, consent or postcondition verification."
    warning = (
        record["inspection"]["coverage_warning"]
        or "The driver reported a complete observation; this capture does not check the current live screen."
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="script-src 'none'; object-src 'none'; base-uri 'none'">
<title>Target {escape(target["id"])} inspection</title>
<style>body{{font:16px system-ui,sans-serif;margin:24px;color:#17202a;background:#fafafa}}h1{{font-size:24px}}dt{{font-weight:600}}dd{{margin:4px 0 16px}}.scope{{max-width:80ch}}figure{{margin:24px 0}}.capture{{position:relative;width:100%;max-width:{width}px}}.capture img{{display:block;width:100%;height:auto}}.target-outline{{position:absolute;outline:3px solid #fa6b0c;pointer-events:none}}figcaption{{margin-top:12px}}</style>
</head><body><h1>Target {escape(target["id"])}: {escape(target_label)}</h1>
<dl><dt>Operation</dt><dd>{escape(target["operation"])}</dd><dt>Required postcondition</dt><dd>{escape(target["postcondition"])}</dd></dl>
<p class="scope">{escape(scope)}</p><p class="scope">{escape(warning)}</p>
<p><a href="{escape(manifest_name, quote=True)}">Capture manifest</a> · <a href="{escape(record["inspection"]["screenshot"], quote=True)}">Original PNG</a></p>
<figure><div class="capture"><img src="{escape(record["inspection"]["screenshot"], quote=True)}" width="{width}" height="{height}" alt="Original bound-window capture">
<div class="target-outline" style="{overlay}" aria-label="Offered target {escape(target["id"], quote=True)}"></div></div>
<figcaption>Orange outline: offered target pixels ({left}, {top}) to ({right}, {bottom}). The original PNG is unchanged.</figcaption></figure>
</body></html>'''


_ROUTES = ("click", "type", "append", "enter", "scroll", "hover", "key", "hotkey", "menu", "navigate")


def parse_do(words: list[str]) -> tuple[str, int | None, str | None, tuple[str, ...], tuple[str, ...]]:
    """``(operation, id, text, keys, path)`` from the command words."""
    if not words or words[0] not in _ROUTES:
        raise SystemExit(f"do takes one of {', '.join(_ROUTES)}")
    op = words[0]
    if op == "key":
        keys = tuple(words[1:])
        if not keys:
            raise SystemExit("key needs a key name, e.g. key Down, key cmd Down")
        return op, None, None, keys, ()
    if op == "hotkey":
        keys = tuple(words[1:])
        if not keys:
            raise SystemExit("hotkey needs keys, e.g. hotkey cmd s, or hotkey Return (foreground route)")
        return op, None, None, keys, ()
    if op == "navigate":
        if len(words) != 2:
            raise SystemExit("navigate needs one URL")
        return op, None, words[1], (), ()
    if op == "menu":
        path = tuple(p.strip() for p in " ".join(words[1:]).split(">") if p.strip())
        if not path:
            raise SystemExit('menu needs a path, e.g. menu "File > Save"')
        return op, None, None, (), path
    if len(words) < 2:
        raise SystemExit(f'{op} needs an element id or a label, e.g. {op} 65 or {op} "Telephone"')
    text = " ".join(words[2:]) if len(words) > 2 else None
    if op in ("type", "append") and text is None:
        raise SystemExit(f"{op} needs text")
    if words[1].lstrip("-").isdigit():
        return op, int(words[1]), text, (), ()
    # a label: resolved against the fresh observation in cmd_do (ids renumber between snapshots)
    return op, words[1], text, (), ()  # type: ignore[return-value]


def resolve_label(nm: Any, label: str) -> tuple[int | None, str]:
    """The one candidate whose label contains ``label`` (case-insensitive); an exact match wins."""
    role = None
    if label.startswith("label:"):
        label = label[len("label:") :]  # label:2 addresses a label that is a number (Q19 R4)
    elif ":" in label and label.split(":", 1)[0].isalpha():
        role, label = label.split(":", 1)  # button:Search narrows by role
    low = label.casefold()
    pool = [c for c in nm.menu.candidates if role is None or c.role == role.casefold()]
    exact = [c for c in pool if c.label.casefold() == low]
    if len(exact) == 1:
        return exact[0].id, ""
    hits = exact or [c for c in pool if low in c.label.casefold()]
    if len(hits) == 1:
        return hits[0].id, ""
    if not hits:
        return None, f"no element labelled {label!r} on the current observation"
    return None, f"{label!r} matches {len(hits)} elements: " + ", ".join(
        f"[{c.id}] {c.label!r}" for c in hits[:6]
    )


def resolve_secrets(text: str | None) -> tuple[str | None, bool]:
    """``{NAME}`` placeholders come from ``$FOOTWORK_SECRET_NAME``; the value never reaches the log."""
    if not text:
        return text, False
    used = False

    def sub(m: re.Match[str]) -> str:
        nonlocal used
        v = os.environ.get(f"FOOTWORK_SECRET_{m.group(1)}")
        if v is None:
            raise SystemExit(f"{{{m.group(1)}}} names no secret: export FOOTWORK_SECRET_{m.group(1)}")
        used = True
        return v

    return re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", sub, text), used


async def cmd_do(args: Any) -> int:
    from jevdual.arbiter import ArbiterPolicy
    from jevdual.authorize import Authorizer, action_for
    from jevdual.native import NativeBridgeError

    state = SessionState.load(session_dir(args.session))
    op, cid, raw_text, keys, path = parse_do(args.words)
    carried = None
    ref = carry.is_ref(raw_text) if op in ("type", "append") else None
    if ref is not None:
        # package G: a carried value, from this session or the one named by --from
        src = Path(getattr(args, "from_session", None) or state.dir)
        try:
            carried = carry.load(src, ref)
        except carry.CarryError as exc:
            print(str(exc), file=sys.stderr)
            return 4
        raw_text = carried.text
        print(f"carrying {carried.provenance()}")
    text, secret_used = resolve_secrets(raw_text)
    shown_text = raw_text if not secret_used else re.sub(r"\{[^}]+\}", "{secret}", raw_text or "")
    if secret_used:
        for name in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", raw_text or ""):
            if name not in state.secret_names:
                state.secret_names.append(name)
    driver, bridge = await bind(state)
    try:
        before = state.last_menu()
        # the ids the operator chose from: the observation before this command, not the fresh one
        chosen_from = {c["id"]: c["label"] for c in state.last_candidates}
        nm, receipt = await observe(state, bridge)
        if receipt:
            print(f"receipt (previous action): {receipt['text']}")
        elif before is not None:
            from jevdual.effects import diff

            drift = diff(before, nm.menu)
            if not drift.no_effect:
                print(
                    f"note: the window changed since your last look ({drift.summary[:120]}); "
                    "ids below are from the fresh observation"
                )
        target = None
        if isinstance(cid, str):
            rid, why = resolve_label(nm, cid)
            if rid is None:
                print(why, file=sys.stderr)
                return 4
            cid = rid
            chosen_from = {}  # a label is resolved on the fresh observation; nothing to compare
        if cid is not None:
            target = nm.menu.candidate(cid)
            known = chosen_from.get(cid)
            if target is None:
                named = [c for c in nm.menu.candidates if c.label == str(cid)]
                hint = f" (an element is labelled {str(cid)!r}: address it as label:{cid})" if named else ""
                print(
                    f"id {cid} is not on the current observation{hint}; run `footwork look`", file=sys.stderr
                )
                return 4
            if known is not None and known != target.label:
                print(
                    f"id {cid} is now {target.label!r}, it was {known!r} when you looked; the page changed. "
                    "Nothing dispatched. Choose again from the observation below.",
                    file=sys.stderr,
                )
                print(render_observation(nm, text_chars=args.text, receipt=None))
                return 4
        judge = None
        client = None
        # every route the authorizer judges (authorize.JUDGED_ROUTES), plus navigation: a key or Return
        # can press the same button a click can (secondary audit 2026-09-27: key and enter were missing)
        from jevdual.authorize import JUDGED_ROUTES

        if not getattr(args, "no_judge", False) and op in (*JUDGED_ROUTES, "navigate"):
            from jevdual.keys import load_keys

            if load_keys().get("TYPESAFE_API_KEY"):
                from typesafe_sdk import AsyncTypeSafeClient

                from jevdual.verify import Verifier

                client = AsyncTypeSafeClient()
                await client.__aenter__()
                judge = Verifier(client).judge_destructive
            else:
                reason = (
                    f"judgment_unavailable: {op} requires configured Jev judgment. "
                    "No action dispatched. Configure judgment access, or deliberately choose "
                    "--no-judge for keyword/replacement-only checks."
                )
                state.memory.append(f"step {state.step + 1}: {op} -> paused before dispatch ({reason})")
                state.log({"kind": "paused", "code": "judgment_unavailable", "op": op, "reason": reason})
                state.save()
                print(f"paused before dispatch: {reason}")
                return 3
        if getattr(args, "no_judge", False):
            print("judgment mode: explicit --no-judge; keyword/replacement-only checks, no Jev judgment")
        authorizer = Authorizer(
            policy=ArbiterPolicy.from_toml(),
            authorized_actions=tuple(state.authorized) + _split(args.authorize, ","),
            judge=judge,
        )
        route = "click" if op == "navigate" else op
        action = action_for(
            route, nm, "s2", target=target, text=text if op != "navigate" else None, keys=keys, path=path
        )
        if op == "navigate":
            action = dataclasses.replace(action, label=f"navigate to {text}", route="click")
        line = f"{op}({target.label if target else (text if op == 'navigate' else ('+'.join(keys) if keys else ' > '.join(path)))})"
        if carried is not None:
            line += f" text=@{carried.name} (from {carried.surface} {carried.location or carried.title})"
        elif shown_text:
            line += f" text={shown_text[:60]!r}"
        hit = await authorizer.check(nm, action, task=state.task)
        if not hit and op in ("navigate", "click"):
            # U52: a repeat of a submission this session already recorded pauses like any gated effect,
            # whatever the label authorization says; a grant for exactly this action clears it
            from jevdual.completion import _records, repeat_of

            hit = repeat_of(
                _records(state.path),
                op,
                url=text or "" if op == "navigate" else "",
                label=target.label if target else "",
            )
        if client is not None:
            await client.__aexit__(None, None, None)
        if authorizer.judgments:
            j = authorizer.judgments[-1]
            print(
                f"destructive judgment: p={j.get('p', 0):.2f} on {j.get('label')!r}"
                if "p" in j
                else f"judgment failed: {j.get('error')}"
            )
        if hit:
            # package H: a grant for exactly this effect on exactly this resource clears the pause once
            proposal = _proposal(state, nm, op, target, text, keys, path)
            granted, why = grants.consume(state.path, proposal)
            if granted is not None:
                print(f"cleared by grant {granted.id}: {granted.describe()}")
                state.log({"kind": "grant_used", "grant": granted.id, "reason": hit})
                hit = None
            else:
                for w in why:
                    print(f"  not cleared by {w}")
        if hit:
            state.memory.append(f"step {state.step + 1}: {line} -> paused before dispatch ({hit[:80]})")
            state.log({"kind": "paused", "line": line, "reason": hit})
            state.save()
            label = action.label
            print(f"paused before dispatch: {hit}")
            print(
                f"to allow exactly this, once: footwork grant {' '.join(args.words)}   "
                f"(broad: --authorize {label!r}, any {label!r} anywhere)"
            )
            return 3
        state.step += 1
        t0 = time.perf_counter()
        error = None
        eff = None  # a raised dispatch leaves no effect; the refusal below is still recorded
        try:
            if op == "navigate":
                eff = await bridge.navigate(text or "")
            elif op == "hotkey":
                eff = await bridge.hotkey(nm, list(keys))
            elif op == "key":
                eff = await bridge.key(nm, keys[-1], list(keys[:-1]))
            elif op == "menu":
                eff = await bridge.menu(nm, list(path))
            else:
                assert target is not None
                route_arg = getattr(args, "route", None)
                if route_arg and state.mode == "browser":
                    eff = await bridge.act(
                        nm, op, target.id, text, route="dom_event" if route_arg == "dom" else "trusted"
                    )
                else:
                    eff = await bridge.act(nm, op, target.id, text)
            driver_effect = eff.effect
            if not getattr(eff, "dispatched", True):
                # the posture refused it: nothing reached any window
                driver_effect = "not sent"
                error = f"{eff.error_code}: {eff.summary[:140]}"
            elif eff.effect == "refused":
                error = f"driver refused: {eff.error_code or ''} {eff.summary[:100]}".strip()
        except (NativeBridgeError, RuntimeError) as exc:
            driver_effect = "not dispatched"
            error = f"{getattr(exc, 'reason', 'error')}: {exc}"[:160]
        exec_ms = (time.perf_counter() - t0) * 1000
        state.pending = {
            "line": line,
            "driver_effect": driver_effect,
            "error": error,
            "exec_ms": exec_ms,
            "op": op,
            "target_id": target.id if target is not None else None,
            "target_label": target.label if target is not None else None,
            "intended": None if secret_used else text,
            "secret": secret_used,
            "mode": state.mode,
            "app": state.app,
            **({"carry": dataclasses.asdict(carried)} if carried is not None else {}),
        }
        if getattr(eff, "readback", None) is not None:
            state.pending["save_readback"] = eff.readback
        state.log({"kind": "do", **state.pending})
        state.save()
        print(
            f"dispatched {line}: driver says {driver_effect}{(' (' + error + ')') if error else ''} in {exec_ms / 1000:.1f}s"
        )
        await asyncio.sleep(args.settle)
        nm, receipt = await observe(state, bridge, secret_value=text if secret_used else None)
    finally:
        await driver.shutdown()
    print(render_observation(nm, text_chars=args.text, receipt=receipt))
    return 0


async def cmd_s1(args: Any) -> int:
    from typesafe_sdk import AsyncTypeSafeClient

    from jevdual.keys import load_keys
    from jevdual.policy import JevPolicy, StepContext

    if not load_keys().get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY missing", file=sys.stderr)
        return 2
    state = SessionState.load(session_dir(args.session))
    driver, bridge = await bind(state)
    try:
        nm, receipt = await observe(state, bridge)
        if receipt:
            print(f"receipt (previous action): {receipt['text']}")
        async with AsyncTypeSafeClient() as client:
            t0 = time.perf_counter()
            decision = await JevPolicy(client).decide(
                nm.menu,
                StepContext(
                    task=state.task,
                    requirements=state.requirements,
                    recent_actions=tuple(state.memory[-8:]),
                    step=state.step + 1,
                ),
            )
            ms = (time.perf_counter() - t0) * 1000
    finally:
        await driver.shutdown()
    tgt = ""
    if decision.target is not None:
        c = nm.menu.candidate(decision.target)
        tgt = f" on [{decision.target}] {c.label if c else '?'!r} (target p={decision.target_confidence:.2f})"
    print(
        f"System 1 proposes: {decision.operation} (p={decision.operation_confidence:.2f}){tgt}  [{ms:.0f} ms]"
    )
    alts = sorted(decision.target_probabilities.items(), key=lambda kv: -kv[1])[1:4]
    if alts:
        print(
            "  alternatives: "
            + ", ".join(
                f"[{i}] {(nm.menu.candidate(i).label if nm.menu.candidate(i) else '?')!r} {p:.2f}"
                for i, p in alts
            )
        )
    if getattr(decision, "text", None):
        print(f"  text: {decision.text!r}")  # type: ignore[attr-defined]
    state.log(
        {
            "kind": "s1",
            "operation": decision.operation,
            "p": decision.operation_confidence,
            "target": decision.target,
            "target_p": decision.target_confidence,
        }
    )
    state.save()
    if args.act and decision.operation in ("type", "append") and decision.target is not None:
        # System 1 picks the field; the text is System 2's to supply (the harness never composes it)
        c = nm.menu.candidate(decision.target)
        print(
            f"System 1 would {decision.operation} into [{decision.target}] {c.label if c else '?'!r}; supply the text: "
            f'footwork do {decision.operation} {decision.target} "..."'
        )
        return 0
    if args.act and decision.operation in _ROUTES and decision.target is not None:
        text = getattr(decision, "text", None)
        words = [decision.operation, str(decision.target)] + ([text] if text else [])
        args.words = words
        return await cmd_do(args)
    return 0


def carried_checks(records: list[dict[str, Any]], menu: Menu) -> list[dict[str, Any]]:
    """V5: for each carried value this session typed or appended, whether the field holds it now, checked
    by the harness: a typed field must equal the value, an appended one must end with it as its own line.
    The verifier reads a verdict instead of comparing a trajectory line with the window itself (V4)."""
    out = []
    seen = set()
    for rec in records:
        c = rec.get("carry")
        label = rec.get("target_label")
        if rec.get("kind") != "do" or not c or not label or (label, c["name"]) in seen:
            continue
        seen.add((label, c["name"]))
        field = next((x for x in menu.candidates if x.label == label), None)
        src = f"read at {c['location'] or c['title']}"
        if field is None:
            verdict = (
                f"harness check: {label!r} is not on the current window, so @{c['name']} cannot be checked"
            )
        else:
            value = field.value or ""
            last = value.rstrip("\n").split("\n")[-1]
            ok = value == c["text"] if rec.get("op") == "type" else last == c["text"]
            where = "its value" if rec.get("op") == "type" else "its last line"
            verdict = (
                f"harness check: {label!r} holds @{c['name']} = {c['text']!r} ({src}) as {where}"
                if ok
                else f"harness check: {label!r} does NOT hold @{c['name']} = {c['text']!r} ({src}) as {where}; {where} is {last if rec.get('op') != 'type' else value!r}"
            )
        out.append({"step": "check", "actions": [verdict]})
    return out


def carry_line(name: str, c: dict[str, Any]) -> str:
    """How a carried value reads on the verifier's trajectory: the value, where it was read, and for a
    match which occurrence it was and the lines around it (V6)."""
    line = f"read @{name} = {c['text']!r} at {c['location'] or c['title']} from {c['element_role']} {c['element_label']!r}"
    if c.get("occurrence"):
        line += f"; {c['occurrence']}"
    if c.get("surroundings"):
        line += f"; around it: {c['surroundings']}"
    return line


def _carried_values(own: Path, others: list[str]) -> tuple[str, ...]:
    """The values carried in this session and the sessions it names: facts with a recorded source."""
    out = []
    for d in (own, *[Path(o) for o in others]):
        p = d / carry.CARRIES
        if p.exists():
            out += [c["text"] for c in json.loads(p.read_text()).values()]
    return tuple(out)


def cross_context(d: Path, *, last: int = 12) -> list[dict[str, Any]]:
    """Trajectory entries from another surface's session: each receipt with its evidence, and each value
    carried there with its source, labelled with the surface."""
    if not (d / "session.json").exists():
        return []
    other = SessionState.load(d)
    where = f"{other.app} {other.last_url or other.last_title}".strip()
    out: list[dict[str, Any]] = []
    log_path = d / "session.jsonl"
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("kind") == "receipt":
                act = (rec.get("action") or {}).get("line", "action")
                out.append(
                    {
                        "surface": where,
                        "actions": [f"{act} -> {rec.get('effect')}: {str(rec.get('evidence'))[:160]}"],
                    }
                )
    for name, c in (
        json.loads((d / carry.CARRIES).read_text()) if (d / carry.CARRIES).exists() else {}
    ).items():
        out.append({"surface": where, "actions": [carry_line(name, c)]})
    return out[-last:]


async def cmd_done(args: Any) -> int:
    from typesafe_sdk import AsyncTypeSafeClient

    from jevdual.keys import load_keys
    from jevdual.verify import Verifier

    if not load_keys().get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY missing", file=sys.stderr)
        return 2
    state = SessionState.load(session_dir(args.session))
    driver, bridge = await bind(state)
    try:
        nm, receipt = await observe(state, bridge)
        if receipt:
            print(f"receipt (previous action): {receipt['text']}")
        trajectory = [
            {"step": i + 1, "url": state.last_url, "actions": [m.split(": ", 1)[-1]]}
            for i, m in enumerate(state.memory[-12:])
        ]
        # V4: the other surfaces' receipts and the carried values' sources, so a done that moved a value
        # across surfaces can be judged with where the value came from in view
        context = [e for d in (getattr(args, "context_from", None) or []) for e in cross_context(Path(d))]
        if context:
            trajectory = context + trajectory
        log_path = state.path / "session.jsonl"
        records = [json.loads(ln) for ln in log_path.read_text().splitlines()] if log_path.exists() else []
        trajectory += carried_checks(records, nm.menu)
        # M1/M2: evidence for the requested effect from this session's records and the other surfaces'.
        # Opt-in (FOOTWORK_COMPLETION=effect_evidence) until independently authored cases validate it;
        # the default keeps the decision Q16c adopted (done text is always answer-bearing)
        from jevdual.completion import session_effects

        by_evidence = os.environ.get("FOOTWORK_COMPLETION") == "effect_evidence"
        effects = None
        if by_evidence:
            document = state.last_title.split(" — ")[0] if state.mode == "native" else ""
            effects = session_effects(state.path, document=document)
            for d in getattr(args, "context_from", None) or []:
                effects += session_effects(Path(d))
        async with AsyncTypeSafeClient() as client:
            t0 = time.perf_counter()
            v = await Verifier(client).verify(
                state.task,
                state.requirements,
                nm.menu,
                args.answer or None,
                # M1: with effect evidence, done text is an explanation unless the task asks for an answer
                # (start --answer, or Jev's answer_required); a fact it states is still checked
                answer_expected=state.answer_expected or (bool(args.answer) and not by_evidence),
                trajectory=trajectory or None,
                carried=_carried_values(state.path, getattr(args, "context_from", None) or []),
                effects=tuple(effects) if effects is not None else None,
            )
            ms = (time.perf_counter() - t0) * 1000
    finally:
        await driver.shutdown()
    unmet = v.unmet_effective or v.unmet
    print(f"verifier: {v.band} (complete p={v.complete:.2f}) [{ms:.0f} ms]: {v.reason}")
    for req, p in sorted(unmet.items(), key=lambda kv: -kv[1]):
        print(f"  {'unmet' if p >= 0.5 else 'met  '} p(unmet)={p:.2f}: {req}")
    unsupported = getattr(v, "unsupported_claims", None) or []
    for c in unsupported[:3]:
        print(f"  not found on the page: {str(c)[:120]!r}")
    state.log({"kind": "done", "answer": args.answer, "band": v.band, "reason": v.reason, "unmet": unmet})
    if v.band == "accept":
        state.status = "done"
        state.memory.append(f"step {state.step + 1}: done accepted")
        state.save()
        print("accepted. session closed.")
        return 0
    state.memory.append(f"step {state.step + 1}: done refused ({v.reason[:80]})")
    state.save()
    return 5


async def cmd_status(args: Any) -> int:
    state = SessionState.load(session_dir(args.session))
    print(
        f"{state.status}: {state.app} window {state.window_id} ({state.posture}), step {state.step}, "
        f"task {state.task!r}"
    )
    print("requirements:", "; ".join(state.requirements) or "(none)")
    for m in state.memory[-12:]:
        print(" ", m)
    if state.pending:
        print("pending receipt for:", state.pending["line"])
    return 0


async def cmd_read(args: Any) -> int:
    """Package G: carry one element's value (or label) out of the current observation, with its source."""
    state = SessionState.load(session_dir(args.session))
    driver, bridge = await bind(state)
    try:
        nm, receipt = await observe(state, bridge)
    finally:
        await driver.shutdown()
    if receipt:
        print(f"receipt (previous action): {receipt['text']}")
    target = args.target
    if getattr(args, "match", None):
        try:
            c = carry.take_match(
                args.name,
                args.match,
                nm.menu.page_text,
                surface=state.mode,
                app=state.app,
                location=nm.menu.url,
                title=nm.menu.title,
                step=state.step,
                session=str(state.path),
            )
        except carry.CarryError as exc:
            print(f"not carried: {exc}", file=sys.stderr)
            return 4
        return _keep_carry(state, c)
    if not target:
        print("read needs an element id or label, or --match REGEX", file=sys.stderr)
        return 2
    if target.lstrip("-").isdigit():
        cand = nm.menu.candidate(int(target))
        if cand is None:
            print(f"id {target} is not on the current observation; run `footwork look`", file=sys.stderr)
            return 4
    else:
        rid, why = resolve_label(nm, target)
        if rid is None:
            print(why, file=sys.stderr)
            return 4
        cand = nm.menu.candidate(rid)
    try:
        c = carry.take(
            args.name,
            cand,
            surface=state.mode,
            app=state.app,
            location=nm.menu.url,
            title=nm.menu.title,
            step=state.step,
            session=str(state.path),
            part=args.part,
        )
    except carry.CarryError as exc:
        print(f"not carried: {exc}", file=sys.stderr)
        return 4
    return _keep_carry(state, c)


def _keep_carry(state: SessionState, c: carry.Carry) -> int:
    carry.store(state.path, c)
    state.memory.append(f"step {state.step}: read [{c.element_id}] {c.element_label!r} as @{c.name}")
    state.log({"kind": "read", "carry": dataclasses.asdict(c)})
    state.save()
    print(f"carried {c.provenance()}")
    return 0


async def cmd_check_file(args: Any) -> int:
    """Package G: the exact saved-file oracle for a carried value; exit 0 when a line equals it, 6 when not."""
    name = carry.is_ref(args.ref)
    if name is None:
        print("check-file takes a carried value as @NAME", file=sys.stderr)
        return 2
    src = Path(args.from_session or session_dir(args.session))
    try:
        c = carry.load(src, name)
    except carry.CarryError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    target = Path(args.path).expanduser()
    if getattr(args, "appended", False):
        try:
            before = carry.load_snapshot(session_dir(args.session), target)
        except carry.CarryError as exc:
            print(str(exc), file=sys.stderr)
            return 4
        result = carry.check_append(target, c, before)
    else:
        result = carry.check_file(target, c)
    text = result.receipt(c)
    print(text)
    own = session_dir(args.session)
    if (own / "session.json").exists():
        state = SessionState.load(own)
        state.memory.append(
            f"step {state.step}: check-file {args.path} @{name} -> {'confirmed' if result.ok else 'failed'}"
        )
        state.log(
            {
                "kind": "check_file",
                "ok": result.ok,
                "path": result.path,
                "line": result.line,
                "detail": result.detail,
                "carry": dataclasses.asdict(c),
            }
        )
        state.save()
    return 0 if result.ok else 6


async def cmd_snapshot_file(args: Any) -> int:
    """Package G: record a destination file before the work, for ``check-file --appended``."""
    d = session_dir(args.session)
    d.mkdir(parents=True, exist_ok=True)
    rec = carry.snapshot(d, Path(args.path).expanduser())
    what = (
        f"{len(rec['text'])} characters, sha256 {rec['sha256'][:12]}"
        if rec["exists"]
        else "does not exist yet"
    )
    print(f"snapshot of {rec['path']}: {what}")
    return 0


def _location(state: SessionState, nm: Any) -> str:
    """Where a grant binds: the page URL, or the native window's document (its file) or else its title."""
    if state.mode == "browser":
        return nm.menu.url
    doc = None
    with contextlib.suppress(Exception):  # no document: the window's own identity is the resource
        from jevdual import ax

        doc = ax.document_path(state.pid, state.window_id)
    if doc:
        return f"file://{doc}"
    return f"{nm.menu.url} window {nm.menu.title!r}"


def _proposal(
    state: SessionState,
    nm: Any,
    op: str,
    target: Any,
    text: str | None,
    keys: tuple[str, ...],
    path: tuple[str, ...],
) -> grants.Proposal:
    arguments = (
        text
        if op in ("type", "append", "navigate")
        else ("+".join(keys) if keys else " > ".join(path) or None)
    )
    return grants.Proposal(
        op=op,
        location=_location(state, nm),
        element_role=target.role if target is not None else None,
        element_label=target.label if target is not None else None,
        arguments=arguments,
        value=target.value if target is not None else None,
        # a menu item or chord acts on the selection: bind it, so a grant for trashing a.txt does not
        # trash b.txt (the audit's "different selected item")
        selection=tuple(sorted(c.label for c in nm.menu.candidates if c.selected)) if target is None else (),
        element_ref=_element_ref(nm, target),
    )


def _element_ref(nm: Any, target: Any) -> str:
    """Q19 R2: "2 of 3" when other elements share the target's role and label (three "Delete draft" links),
    so a grant for one row does not clear another; empty when the element is unique."""
    if target is None:
        return ""
    same = [c.id for c in nm.menu.candidates if c.role == target.role and c.label == target.label]
    return f"{same.index(target.id) + 1} of {len(same)}" if len(same) > 1 else ""


async def cmd_grant(args: Any) -> int:
    """Package H: allow one exact effect on one resource, issued against the current observation."""
    state = SessionState.load(session_dir(args.session))
    op, cid, raw_text, keys, path = parse_do(args.words)
    ref = carry.is_ref(raw_text) if op in ("type", "append") else None
    if ref is not None:
        try:
            raw_text = carry.load(Path(getattr(args, "from_session", None) or state.dir), ref).text
        except carry.CarryError as exc:
            print(str(exc), file=sys.stderr)
            return 4
    if raw_text and re.search(r"\{[A-Za-z_][A-Za-z0-9_]*\}", raw_text):
        print("a grant never binds a secret's value; grant the field without it", file=sys.stderr)
        return 2
    driver, bridge = await bind(state)
    try:
        nm, _ = await observe(state, bridge)
        target = None
        if isinstance(cid, str):
            rid, why = resolve_label(nm, cid)
            if rid is None:
                print(why, file=sys.stderr)
                return 4
            cid = rid
        if cid is not None:
            target = nm.menu.candidate(cid)
            if target is None:
                print(f"id {cid} is not on the current observation", file=sys.stderr)
                return 4
        g = grants.issue(
            _proposal(state, nm, op, target, raw_text, keys, path), uses=args.uses, step=state.step
        )
    finally:
        await driver.shutdown()
    grants.record(state.path, g)
    state.log({"kind": "grant", "grant": grants.as_dict(g)})
    state.save()
    print(f"granted {g.id}: {g.describe()}")
    return 0


def _split(s: str | None, sep: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in (s or "").split(sep) if x.strip())
