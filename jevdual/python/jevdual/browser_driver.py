"""The Driver's browser mode for a Chrome that footwork owns (P6, 2026-09-25).

The accessibility route cannot type into a browser the person is using: the Driver refuses
background keyboard input to a process with several windows and the session window cannot become
key while the person works. The Driver's browser tools act over a DevTools endpoint instead:
``get_browser_state`` binds a native window to a CDP target and returns a semantic snapshot with
short-lived refs, ``browser_type`` and ``browser_click`` act on refs, ``browser_navigate`` opens a
URL. Nothing is foregrounded.

footwork launches its own Chrome (``launch_chrome``): the system Chrome binary, a profile directory
of its own under ``~/.config/jevdual`` that the person signs into once, and a loopback debugging
port. Attaching to it is an existing-profile attachment, which the Driver authorizes only through a
host callback: :class:`FootworkAuthorizationHost` allows exactly the process footwork launched (pid
and executable in the request's resource) and denies anything else. The Driver never sees the
person's own Chrome profile.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jevdual.menu import Candidate, Menu

log = logging.getLogger("jevdual.browser")

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR = Path(
    os.environ.get("FOOTWORK_CHROME_PROFILE", str(Path.home() / ".config/jevdual/chrome-profile"))
)
PORT = int(os.environ.get("FOOTWORK_CHROME_PORT", "9333"))
SESSION_LABEL = "footwork"

#: semantic roles that take text
_TEXT_ROLES = {"textbox", "searchbox", "inputtime", "inputdate", "combobox", "spinbutton"}


def chrome_pid() -> int | None:
    """The pid of the Chrome footwork launched (by its profile directory), or None."""
    out = subprocess.run(
        ["pgrep", "-f", f"user-data-dir={PROFILE_DIR}"], capture_output=True, text=True, check=False
    )
    pids = [int(p) for p in out.stdout.split() if p.strip().isdigit()]
    return min(pids) if pids else None


def launch_chrome(url: str | None = None, *, settle_s: float = 4.0) -> int:
    """Start footwork's Chrome if it is not running, and return its pid."""
    pid = chrome_pid()
    if pid is not None:
        return pid
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    args = [
        CHROME,
        f"--user-data-dir={PROFILE_DIR}",
        f"--remote-debugging-port={PORT}",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1200,900",
    ]
    if url:
        args.append(url)
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + settle_s + 10
    while time.time() < deadline:
        time.sleep(0.5)
        pid = chrome_pid()
        if pid is not None:
            time.sleep(settle_s)
            return pid
    raise RuntimeError("footwork's Chrome did not start")


def _host_class(pid: int) -> Any:
    import cua_driver as cd

    class FootworkAuthorizationHost(cd.DriverAuthorizationHost):
        """Allow attaching to footwork's own Chrome and nothing else."""

        async def authorize(self, request: Any) -> Any:
            try:
                res = json.loads(request.resource_json or "{}")
            except json.JSONDecodeError:
                res = {}
            fp = res.get("process_fingerprint") or {}
            ok = (
                res.get("pid") == pid
                and res.get("endpoint_owner_pid") in (None, pid)
                and str(fp.get("executable", CHROME)) == CHROME
            )
            log.info(
                "driver authorization %s: %s", "allowed" if ok else "denied", request.human_summary[:160]
            )
            action = cd.DriverAuthorizationAction.ALLOW if ok else cd.DriverAuthorizationAction.DENY
            return cd.DriverAuthorizationDecision(action=action, request_digest=request.request_digest)

    return FootworkAuthorizationHost


def configured_driver(pid: int) -> Any:
    """A Driver whose authorization callback allows footwork's Chrome only. Call from inside a
    running event loop: the binding needs it to deliver the callback."""
    import cua_driver as cd
    from cua_driver import _native

    _native.uniffi_set_event_loop(asyncio.get_running_loop())
    opts = cd.ConfiguredDriverOptions(
        claude_code_compatibility=False,
        authorization=cd.RuntimeAuthorizationOptions(
            allowed_modes=[cd.SessionPermissionMode.STANDARD],
            compatibility_mode=cd.SessionPermissionMode.STANDARD,
            compatibility_capability_manifest_path=None,
            compatibility_bounded_manifest_path=None,
            unrestricted_acknowledged=False,
            max_session_ttl_seconds=8 * 3600,
            max_idle_ttl_seconds=1800,
        ),
    )
    return cd.CuaDriver.create_configured_with_authorization_host(opts, _host_class(pid)())


@dataclass
class WebMenu:
    """A semantic snapshot as System 1 and the verifier read it (duck-typed like NativeMenu)."""

    menu: Menu
    snapshot_id: str
    refs: dict[int, str]
    app_name: str = "Google Chrome (footwork)"
    page_url: str = ""
    page_title: str = ""
    truncated: bool = False
    degraded: bool = False
    elements_complete: bool = True
    frames: dict[int, tuple[float, float, float, float]] = field(default_factory=dict)
    #: current value per text control, read by the authorization boundary's replacement rule
    values: dict[int, str] = field(default_factory=dict)

    def token(self, id: int) -> str | None:
        return self.refs.get(id)


def _ref_index(ref: str) -> int:
    return int(ref.split(":", 1)[1])


def menu_from_semantic(s: dict[str, Any]) -> WebMenu:
    page = s.get("page") or {}
    snap = s.get("snapshot") or {}
    cands: list[Candidate] = []
    refs: dict[int, str] = {}
    for x in s.get("refs") or []:
        ref = x.get("ref") or ""
        try:
            rid = _ref_index(ref)
        except (IndexError, ValueError):
            continue
        role = str(x.get("role") or "element")
        states = x.get("states") or {}
        acts = set(x.get("actions") or ())
        if role in _TEXT_ROLES or "type" in acts and "click" not in acts:
            ops: tuple[str, ...] = ("type",)
        else:
            ops = ("click",)
        checked = states.get("checked")
        checked_b = None if checked is None else str(checked).lower() == "true"
        label = str(x.get("name") or "").strip() or role
        cands.append(
            Candidate(
                id=rid,
                label=label[:120],
                role=role,
                operations=ops,  # type: ignore[arg-type]
                value=(str(x["value"])[:200] if x.get("value") not in (None, "") else None),
                input_type=("textarea" if states.get("editable") == "richtext" else None),
                checked=checked_b,
                offscreen=x.get("visibility") not in (None, "in_viewport", "near_viewport"),
            )
        )
        refs[rid] = ref
    lines: list[str] = []
    for c in s.get("content_refs") or []:
        name = c.get("name")
        if name and c.get("role") in ("statictext", "heading", "link", "listitem", "cell", "paragraph"):
            t = " ".join(str(name).split())
            if t and (not lines or lines[-1] != t):
                lines.append(t)
    for c in cands:
        if c.value and c.value not in lines:
            lines.append(c.value)
    by_op: dict[str, tuple[Candidate, ...]] = {}
    for c in cands:
        for op in c.operations:
            by_op[op] = by_op.get(op, ()) + (c,)
    omitted = {k: v for k, v in (snap.get("omitted") or {}).items() if v}
    if not snap.get("complete", True):
        omitted["elements_incomplete"] = 1
    menu = Menu(
        url=str(page.get("url") or ""),
        title=str(page.get("title") or ""),
        page_text="\n".join(lines)[:6000],
        candidates=tuple(cands),
        by_operation=by_op,  # type: ignore[arg-type]
        omitted=omitted,
    )
    return WebMenu(
        menu=menu,
        snapshot_id=str(snap.get("id") or ""),
        refs=refs,
        values={c.id: c.value for c in cands if c.value},
        page_url=menu.url,
        page_title=menu.title,
        elements_complete=bool(snap.get("complete", True)),
    )


@dataclass
class BrowserEffect:
    """Duck-typed like NativeEffect for the session's receipt plumbing."""

    operation: str
    target: int
    label: str
    effect: str
    route: str | None = "cdp"
    evidence: tuple[str, ...] = ()
    summary: str = ""
    error_code: str | None = None


class BrowserBridge:
    """One bound tab of footwork's Chrome. ``attach`` once per Driver process (each command)."""

    def __init__(self, driver: Any, pid: int, window_id: int, *, session: str = SESSION_LABEL):
        self.driver = driver
        self.pid = pid
        self.window_id = window_id
        self.session = session
        self.target_id: str | None = None
        self.tab_id: str | None = None
        self.last: WebMenu | None = None

    async def _tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        r = await self.driver.call_tool(name, json.dumps({"session": self.session, **args}))
        raw = getattr(r, "structured_json", None) or "{}"
        try:
            out = json.loads(raw)
        except json.JSONDecodeError:
            out = {}
        out.setdefault("_text", str(getattr(r, "text", "") or ""))
        out.setdefault("_is_error", bool(getattr(r, "is_error", False)))
        return out

    async def attach(self) -> dict[str, Any]:
        prep = await self._tool(
            "browser_prepare",
            {"pid": self.pid, "window_id": self.window_id, "strategy": {"kind": "existing_profile"}},
        )
        if prep.get("status") == "refused":
            raise RuntimeError(
                f"browser_prepare refused: {prep.get('refusal', {}).get('message', prep['_text'])[:200]}"
            )
        bound = await self._tool("get_browser_state", {"pid": self.pid, "window_id": self.window_id})
        if bound.get("status") != "ok":
            raise RuntimeError(
                f"bind refused: {bound.get('refusal', {}).get('message', bound['_text'])[:200]}"
            )
        self.target_id = bound["target_id"]
        tabs = bound.get("tabs") or []
        active = next((t for t in tabs if t.get("active")), tabs[0] if tabs else None)
        if active is None:
            raise RuntimeError("bound target has no tab")
        self.tab_id = active["tab_id"]
        return bound

    async def observe(self, *, screenshot_path: str | None = None, **_: Any) -> WebMenu:
        if self.target_id is None:
            await self.attach()
        s = await self._tool(
            "get_browser_state",
            {"target_id": self.target_id, "tab_id": self.tab_id, "snapshot_format": "semantic_v2"},
        )
        if s.get("status") == "refused":
            raise RuntimeError(f"snapshot refused: {s.get('refusal', {}).get('message', s['_text'])[:200]}")
        self.last = menu_from_semantic(s)
        return self.last

    def _fresh(self, nm: WebMenu, id: int) -> tuple[Candidate, str]:
        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise RuntimeError("stale snapshot; reobserve")
        c = nm.menu.candidate(id)
        ref = nm.refs.get(id)
        if c is None or ref is None:
            raise RuntimeError(f"id {id} is not on snapshot {nm.snapshot_id}")
        return c, ref

    def _effect(self, out: dict[str, Any], op: str, id: int, label: str) -> BrowserEffect:
        if out.get("status") == "refused" or out.get("_is_error"):
            msg = (out.get("refusal") or {}).get("message") or out["_text"]
            code = (out.get("refusal") or {}).get("code")
            return BrowserEffect(op, id, label, "refused", summary=str(msg)[:200], error_code=code)
        return BrowserEffect(op, id, label, "unverifiable", summary=out["_text"][:200])

    #: form controls whose trusted (hardware-like) click did not toggle them in the background
    #: on 2026-09-25 (receipts said suspected no-op, the snapshot agreed): a synthetic DOM click
    #: is the honest route for these, and the receipt still proves the outcome
    DOM_EVENT_ROLES = frozenset({"radio", "checkbox", "switch"})

    async def act(
        self, nm: WebMenu, operation: str, id: int, text: str | None = None, *, route: str | None = None
    ) -> BrowserEffect:
        c, ref = self._fresh(nm, id)
        base = {"target_id": self.target_id, "tab_id": self.tab_id}
        if operation == "click":
            # 2026-09-25: in this background posture the trusted route toggled no radio or checkbox,
            # activated no submit button and opened no suggestion link (six no-op receipts, zero
            # successes); the DOM route did all of them. DOM is the default; the receipt proves the
            # outcome either way, and --route trusted is there for controls that ignore synthetic clicks.
            input_route = route or "dom_event"
            out = await self._tool("browser_click", {**base, "ref": ref, "input_route": input_route})
            eff = self._effect(out, operation, id, c.label)
            self.last = None
            return dataclasses.replace(eff, route=input_route)
        elif operation in ("type", "append"):
            out = await self._tool(
                "browser_type", {**base, "ref": ref, "text": text or "", "replace": operation == "type"}
            )
        else:
            raise RuntimeError(f"browser mode has no {operation!r} operation (click, type, append, navigate)")
        self.last = None
        return self._effect(out, operation, id, c.label)

    async def navigate(self, url: str) -> BrowserEffect:
        if self.target_id is None:
            await self.attach()
        out = await self._tool(
            "browser_navigate", {"target_id": self.target_id, "tab_id": self.tab_id, "url": url}
        )
        self.last = None
        return self._effect(out, "navigate", -1, url)

    async def key(self, nm: WebMenu, key: str, modifiers: list[str] | None = None) -> BrowserEffect:
        return BrowserEffect(
            "key", -1, key, "refused", summary="browser mode has no key route; use a control"
        )

    async def hotkey(self, nm: WebMenu, keys: list[str]) -> BrowserEffect:
        return BrowserEffect("hotkey", -1, "+".join(keys), "refused", summary="browser mode has no key route")

    async def menu(self, nm: WebMenu, path: list[str]) -> BrowserEffect:
        return BrowserEffect(
            "menu", -1, " > ".join(path), "refused", summary="browser mode has no menu route"
        )


async def bind_footwork_chrome(url: str | None = None) -> tuple[Any, BrowserBridge]:
    """Launch or find footwork's Chrome, build the configured Driver, bind its largest window."""
    from cua_driver import ListWindowsInput

    pid = launch_chrome(url)
    driver = configured_driver(pid)
    wins = await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))
    if not wins.windows:
        raise RuntimeError("footwork's Chrome has no on-screen window")
    w = max(wins.windows, key=lambda w: w.bounds.width * w.bounds.height)
    bridge = BrowserBridge(driver, pid, w.window_id)
    await bridge.attach()
    return driver, bridge
