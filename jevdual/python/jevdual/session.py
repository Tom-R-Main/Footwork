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
    footwork status
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jevdual.menu import Candidate, Menu
from jevdual.native import NativeBridge, NativeMenu

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

    @property
    def path(self) -> Path:
        return Path(self.dir)

    def save(self) -> None:
        (self.path / "session.json").write_text(json.dumps(asdict(self), indent=1))

    @classmethod
    def load(cls, d: Path) -> SessionState:
        raw = json.loads((d / "session.json").read_text())
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
        self.last_url = nm.menu.url
        self.last_title = nm.menu.title
        self.last_page_text = nm.menu.page_text
        self.last_candidates = [{k: getattr(c, k) for k in _CAND_FIELDS} for c in nm.menu.candidates]
        self.last_snapshot = nm.snapshot_id


def session_dir(arg: str | None) -> Path:
    return Path(arg or os.environ.get("FOOTWORK_SESSION") or "runs/session")


# ---- observation and receipts --------------------------------------------------------------


def receipt_for(state: SessionState, nm: NativeMenu) -> dict[str, Any] | None:
    """The receipt for the pending action: the effect diff between the observation it was taken on and
    this one, in the driver's words."""
    from jevdual.effects import diff
    from jevdual.receipts import receipt_from_effect, receipt_text

    if state.pending is None:
        return None
    prev = state.last_menu()
    if prev is None:
        return None
    eff = diff(prev, nm.menu)
    r = receipt_from_effect(
        state.step,
        (state.pending.get("line", "action"),),
        eff,
        url_after=nm.menu.url,
        error=state.pending.get("error"),
    )
    r = _field_receipt(r, state.pending, nm)
    if r.effect == "suspected_noop" and state.pending.get("driver_effect") == "confirmed":
        # the driver confirmed the press but nothing on the menu changed: say both
        text = receipt_text(r) + " The driver reported the press as delivered."
    else:
        text = receipt_text(r)
    return {"effect": r.effect, "evidence": r.evidence, "text": text}


def _field_receipt(r: Any, pending: dict[str, Any], nm: Any) -> Any:
    """A receipt for ``type`` or ``append`` names what the field holds now, and its verdict follows
    the field, not the element count: on 2026-09-25 typing into Wikipedia's search box added 49
    elements (the suggestion list), the receipt said confirmed, and the query went out empty."""
    if pending.get("op") not in ("type", "append") or not pending.get("target_label"):
        return r
    label = pending["target_label"]
    low = label.casefold()
    fields = [c for c in nm.menu.candidates if c.label.casefold() == low and "type" in c.operations]
    field = fields[0] if fields else nm.menu.candidate(pending.get("target_id", -1))
    if field is None:
        return dataclasses.replace(
            r, effect="unverifiable", evidence=f"{label!r} is not on the fresh observation"
        )
    if field.input_type == "password":
        ok = bool(field.has_value)
        shown, holds = "{secret}", "a value" if ok else "nothing"
    else:
        holds = field.value or ""
        if pending.get("secret"):
            ok, shown = bool(holds), "{secret}"
        else:
            intended = pending.get("intended") or ""
            ok, shown = bool(intended) and intended in holds, intended
    if ok:
        return dataclasses.replace(r, effect="confirmed", evidence=f"{label!r} now holds {str(holds)[:80]!r}")
    return dataclasses.replace(
        r, effect="suspected_noop", evidence=f"{label!r} holds {str(holds)[:80]!r}, not {str(shown)[:60]!r}"
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
        bridge = BrowserBridge(driver, state.pid, state.window_id)
        await bridge.attach()
        return driver, bridge
    from cua_driver import CuaDriver

    driver = CuaDriver.create()
    return driver, _native_bridge(driver, state.pid, state.window_id, state.posture)


def _native_bridge(driver: Any, pid: int, wid: int, posture: str) -> NativeBridge:
    """The operator's bridge: the session's posture, and a live identity check before every element
    action (the person may have changed the window since the operator looked)."""
    from jevdual.posture import ExecutionPolicy

    return NativeBridge(driver, pid, wid, policy=ExecutionPolicy(posture), live_check=True)  # type: ignore[arg-type]


async def observe(state: SessionState, bridge: NativeBridge) -> tuple[NativeMenu, dict[str, Any] | None]:
    shots = state.path / "screenshots"
    shots.mkdir(exist_ok=True)
    nm = await bridge.observe(screenshot_path=str(shots / f"obs-{state.step:03d}-{int(time.time())}.png"))
    receipt = receipt_for(state, nm)
    if receipt is not None and state.pending is not None:
        word = receipt["effect"]
        line = state.pending.get("line", "action")
        state.memory.append(f"step {state.step}: {line} -> {word}")
        state.log({"kind": "receipt", "action": state.pending, **receipt})
        state.pending = None
    state.remember(nm)
    state.save()
    return nm, receipt


# ---- commands --------------------------------------------------------------------------------


async def cmd_start(args: Any) -> int:
    from cua_driver import CuaDriver

    from jevdual.native import address_bar, find_window, navigate_in_window, new_window

    d = session_dir(args.session)
    d.mkdir(parents=True, exist_ok=True)
    for old in ("session.json", "session.jsonl"):
        (d / old).unlink(missing_ok=True)
    if getattr(args, "browser", False):
        return await _start_browser(args, d)
    driver = CuaDriver.create()
    try:
        pid, wid, title = await find_window(driver, args.app, title_contains=args.window or "")
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

    driver, bridge = await bind_footwork_chrome(args.url)
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
    finally:
        await driver.shutdown()
    print(render_observation(nm, text_chars=args.text, receipt=receipt))
    return 0


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
    if ":" in label and label.split(":", 1)[0].isalpha():
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
    text, secret_used = resolve_secrets(raw_text)
    shown_text = raw_text if not secret_used else re.sub(r"\{[^}]+\}", "{secret}", raw_text or "")
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
                print(f"id {cid} is not on the current observation; run `footwork look`", file=sys.stderr)
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
        if not getattr(args, "no_judge", False) and op in ("click", "menu", "hotkey", "navigate"):
            from jevdual.keys import load_keys

            if load_keys().get("TYPESAFE_API_KEY"):
                from typesafe_sdk import AsyncTypeSafeClient

                from jevdual.verify import Verifier

                client = AsyncTypeSafeClient()
                await client.__aenter__()
                judge = Verifier(client).judge_destructive
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
        if shown_text:
            line += f" text={shown_text[:60]!r}"
        hit = await authorizer.check(nm, action, task=state.task)
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
            state.memory.append(f"step {state.step + 1}: {line} -> paused before dispatch ({hit[:80]})")
            state.log({"kind": "paused", "line": line, "reason": hit})
            state.save()
            label = action.label
            print(f"paused before dispatch: {hit}")
            print(f"to allow it once: footwork do ... --authorize {label!r}   (or --authorize at start)")
            return 3
        state.step += 1
        t0 = time.perf_counter()
        error = None
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
        }
        state.log({"kind": "do", **state.pending})
        state.save()
        print(
            f"dispatched {line}: driver says {driver_effect}{(' (' + error + ')') if error else ''} in {exec_ms / 1000:.1f}s"
        )
        await asyncio.sleep(args.settle)
        nm, receipt = await observe(state, bridge)
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
        async with AsyncTypeSafeClient() as client:
            t0 = time.perf_counter()
            v = await Verifier(client).verify(
                state.task,
                state.requirements,
                nm.menu,
                args.answer or None,
                answer_expected=state.answer_expected or bool(args.answer),
                trajectory=trajectory or None,
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


def _split(s: str | None, sep: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in (s or "").split(sep) if x.strip())
