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
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jevdual.menu import Candidate, Menu, _tri, control_state

log = logging.getLogger("jevdual.browser")

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR = Path(
    os.environ.get("FOOTWORK_CHROME_PROFILE", str(Path.home() / ".config/jevdual/chrome-profile"))
)
PORT = int(os.environ.get("FOOTWORK_CHROME_PORT", "9333"))
SESSION_LABEL = "footwork"
_CHROME_LAUNCHES: dict[int, subprocess.Popen] = {}


def _browser_candidates() -> list[str]:
    if sys.platform == "darwin":
        return [CHROME]
    if sys.platform == "linux":
        # Prefer real binaries: shell launchers do not share the browser's executable identity.
        return [
            "/opt/google/chrome/chrome",
            "/usr/lib/chromium/chromium",
            "/usr/lib/chromium-browser/chromium-browser",
            *filter(None, (shutil.which(name) for name in ("google-chrome", "chromium", "chromium-browser"))),
        ]
    return []


def chrome_executable() -> str:
    """Resolve an existing browser; never download one or ignore a broken explicit override."""
    override = os.environ.get("FOOTWORK_CHROME_EXECUTABLE")
    candidates = [override] if override is not None else _browser_candidates()
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    raise RuntimeError(
        "Chrome executable unavailable; set FOOTWORK_CHROME_EXECUTABLE to the installed browser binary"
    )


def durable_authority_refusal() -> dict[str, Any]:
    """Describe the missing custody contract without preparing or launching Chrome.

    Current tab handles are connection-local, URL rebinding is not persistent
    identity, and browser replies carry no qualified delivery receipt. A durable
    authority database must not turn those legacy mechanics into guarantees.
    """
    return {
        "code": "browser_authority_unqualified",
        "surface": "browser",
        "dispatched": False,
        "missing_capabilities": [
            "persistent_browser_context_and_tab_identity",
            "document_generation_bound_input",
            "qualified_browser_delivery_receipt",
        ],
        "message": "Durable browser admission is unavailable; no browser was launched or input sent.",
    }


#: semantic roles that take text
_TEXT_ROLES = {"textbox", "searchbox", "inputtime", "inputdate", "combobox", "spinbutton"}


def _page_key(url: str) -> str:
    """A page's identity for binding: the URL without its fragment or a trailing slash."""
    base = url.split("#", 1)[0]
    return base.removesuffix("/")


def chrome_pid() -> int | None:
    """Find the one owned browser root, never a regex match or a renderer process."""
    import psutil

    executable = chrome_executable()
    required = {f"--user-data-dir={PROFILE_DIR}", f"--remote-debugging-port={PORT}"}
    pids = []
    for process in psutil.process_iter(["pid", "cmdline", "exe", "uids"]):
        info = process.info
        args = info.get("cmdline") or []
        owner = info.get("uids")
        if (
            required.issubset(args)
            and not any(arg.startswith("--type=") for arg in args)
            and info.get("exe")
            and str(Path(info["exe"]).resolve()) == executable
            and owner is not None
            and owner.real == os.getuid()
        ):
            pids.append(info["pid"])
    if len(pids) > 1:
        raise RuntimeError("multiple browser processes match the owned profile; refusing ambiguous attachment")
    return pids[0] if pids else None


def _incarnation(pid: int) -> float:
    import psutil

    return psutil.Process(pid).create_time()


def _chrome_args(url: str | None = None, *, new_window: bool = False) -> list[str]:
    args = [chrome_executable(), f"--user-data-dir={PROFILE_DIR}", f"--remote-debugging-port={PORT}",
            "--remote-debugging-address=127.0.0.1", "--no-first-run", "--no-default-browser-check",
            "--window-size=1200,900"]
    if new_window:
        args.append('--new-window')
    if url:
        args.append(url)
    return args


def _recovery_flags(pid: int, incarnation: float) -> list[str]:
    """Preserve only the existing root's explicitly chosen sandbox mode.

    Chromium checks sandbox prerequisites even in a secondary singleton helper.
    Normal launches never add this flag, and arbitrary root arguments are not
    copied into a new command. The pinned root must still own the exact profile.
    """
    import psutil

    process = psutil.Process(pid)
    with process.oneshot():
        if chrome_pid() != pid or process.create_time() != incarnation:
            raise RuntimeError('owned Chrome identity changed before recovery launch')
        args = process.cmdline()
    return ['--no-sandbox'] if '--no-sandbox' in args else []


def _begin_chrome(url: str | None) -> tuple[int, subprocess.Popen | None]:
    for pid, handle in list(_CHROME_LAUNCHES.items()):
        if handle.poll() is not None:
            del _CHROME_LAUNCHES[pid]
    pid = chrome_pid()
    if pid is not None:
        return pid, None
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(_chrome_args(url), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True)
    _CHROME_LAUNCHES[process.pid] = process
    return process.pid, process


def _stop_launch(process: subprocess.Popen | None) -> None:
    """Only a handle created here grants cleanup authority; never a discovered root."""
    if process is None:
        return
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=1)
    _CHROME_LAUNCHES.pop(process.pid, None)


def launch_chrome(url: str | None = None, *, settle_s: float = 4.0) -> int:
    """Synchronous compatibility entrypoint; asynchronous binding owns its cancellation."""
    pid, process = _begin_chrome(url)
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process is not None and process.poll() is not None:
                raise RuntimeError('owned Chrome exited before readiness')
            if chrome_pid() == pid:
                time.sleep(max(0, settle_s))
                return pid
            time.sleep(.1)
        raise RuntimeError("footwork's Chrome did not start")
    except BaseException:
        _stop_launch(process)
        raise


def _host_class(pid: int) -> Any:
    import cua_driver as cd
    import psutil

    executable = chrome_executable()
    if chrome_pid() != pid:
        raise RuntimeError("browser process does not match the owned profile")
    incarnation = psutil.Process(pid).create_time()

    class FootworkAuthorizationHost(cd.DriverAuthorizationHost):
        """Allow attaching to footwork's own Chrome and nothing else."""

        async def authorize(self, request: Any) -> Any:
            try:
                res = json.loads(request.resource_json or "{}")
            except json.JSONDecodeError:
                res = {}
            if not isinstance(res, dict):
                res = {}
            fp = res.get("process_fingerprint") or {}
            if not isinstance(fp, dict):
                fp = {}
            try:
                same_process = chrome_pid() == pid and psutil.Process(pid).create_time() == incarnation
            except (psutil.Error, RuntimeError, OSError):
                same_process = False
            ok = (
                same_process
                and res.get("pid") == pid
                and res.get("endpoint_owner_pid") in (None, pid)
                and fp.get("executable") == executable
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
    #: Coverage of the normalized semantic projection, not original webpage bytes.
    text_original_length: int | None = None
    text_truncated: bool = False
    value_truncated: tuple[int, ...] = ()

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
        label = str(x.get("name") or "").strip() or role
        cands.append(
            Candidate(
                id=rid,
                label=label[:120],
                role=role,
                operations=ops,  # type: ignore[arg-type]
                value=(str(x["value"])[:200] if x.get("value") not in (None, "") else None),
                input_type=("textarea" if states.get("editable") == "richtext" else None),
                # the Driver keeps CDP's AX states: checked/pressed are "true", "false" or "mixed";
                # selected/expanded are booleans. Unreported states stay None (not observed).
                checked=control_state(states.get("checked")),
                selected=_tri(states.get("selected")),
                expanded=_tri(states.get("expanded")),
                pressed=control_state(states.get("pressed")),
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
    projected_text = "\n".join(lines)
    clipped_values = tuple(
        _ref_index(x["ref"])
        for x in s.get("refs") or []
        if x.get("ref") in refs.values() and len(str(x.get("value") or "")) > 200
    )
    if len(projected_text) > 6000:
        omitted["text_truncated"] = 1
    if clipped_values:
        omitted["value_previews_truncated"] = len(clipped_values)
    menu = Menu(
        url=str(page.get("url") or ""),
        title=str(page.get("title") or ""),
        page_text=projected_text[:6000],
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
        text_original_length=len(projected_text),
        text_truncated=len(projected_text) > 6000,
        value_truncated=clipped_values,
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
    #: False when the posture refused the step before anything reached the browser
    dispatched: bool = True


class BrowserBridge:
    """One bound tab of footwork's Chrome. ``attach`` once per Driver process (each command)."""

    def __init__(
        self,
        driver: Any,
        pid: int,
        window_id: int,
        *,
        session: str = SESSION_LABEL,
        policy: Any = None,
    ):
        from jevdual.posture import ExecutionPolicy

        self.driver = driver
        self.pid = pid
        self.window_id = window_id
        self.session = session
        #: the execution posture (jevdual.posture): a replace-typed field selects the tab for about
        #: 100 ms (footwork-9c's tab probe, 2026-09-25), which is a foreground step for the posture
        self.policy = policy or ExecutionPolicy("background_only")
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

    async def attach(self, *, tab_id: str | None = None, expect_url: str | None = None) -> dict[str, Any]:
        """Bind the window's browser target. With ``expect_url`` (the page a session last observed) the
        bridge binds the one tab showing that page, and refuses when none or several do. The Driver's tab
        ids are handles for one connection, new on every command (the Q13 oracle stage, 2026-09-28), so a
        session cannot carry them across commands. ``tab_id`` binds a handle within one connection.
        Without either, it takes the active tab (a new session)."""
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
        if expect_url:
            want = _page_key(expect_url)
            same = [t for t in tabs if _page_key(str(t.get("url") or "")) == want]
            if not same:
                raise RuntimeError(
                    f"the session's page {expect_url} is no longer open in this window; nothing dispatched. "
                    "Start a new session on the tab you want."
                )
            if len(same) > 1:
                raise RuntimeError(
                    f"{len(same)} tabs show the session's page {expect_url}; cannot tell which is the session's; "
                    "nothing dispatched. Close the others or start a new session."
                )
            self.tab_id = same[0]["tab_id"]
            return bound
        if tab_id is not None:
            if not any(t.get("tab_id") == tab_id for t in tabs):
                raise RuntimeError(
                    f"the session's tab {tab_id} is no longer in this window; nothing dispatched. "
                    "Start a new session on the tab you want."
                )
            self.tab_id = tab_id
            return bound
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
            # browser_type selects the bound tab for about 100 ms in every mode except
            # insert_text with replace=false (page visibility probe by footwork-9c, 2026-09-25): in
            # that window the person's keystrokes can land in the agent's tab. Inserting into an
            # empty field, or appending, is the only background-safe form; replacing held text is a
            # foreground step and asks the posture. Keystroke mode is never used.
            holds = (c.value or "") if c.role != "password" else ""
            needs_replace = operation == "type" and bool(holds)
            if needs_replace:
                refusal = self.policy.permits(
                    "foreground",
                    why=f"replacing the text {c.label!r} holds selects its tab for ~100 ms",
                )
                if refusal is not None:
                    self.last = None
                    return BrowserEffect(
                        operation,
                        id,
                        c.label,
                        "refused",
                        route="cdp",
                        summary=refusal.reason[:200],
                        error_code=refusal.code,
                        dispatched=False,
                    )
            out = await self._tool(
                "browser_type",
                {**base, "ref": ref, "text": text or "", "mode": "insert_text", "replace": needs_replace},
            )
        else:
            hint = (
                "; content beyond this observation cannot be scrolled into view here, so an answer from "
                "it covers only what the observation shows"
                if operation == "scroll"
                else ""
            )
            raise RuntimeError(
                f"browser mode has no {operation!r} operation (click, type, append, navigate){hint}"
            )
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


async def bind_footwork_chrome(url: str | None = None, *, policy: Any = None) -> tuple[Any, BrowserBridge]:
    """Launch or find footwork's Chrome, build the configured Driver, bind its largest window."""
    from cua_driver import ListWindowsInput

    pid, launch = _begin_chrome(url)
    driver = helper = None
    succeeded = False
    deadline = time.monotonic() + 15
    try:
        incarnation = _incarnation(pid)

        def identity() -> bool:
            return chrome_pid() == pid and _incarnation(pid) == incarnation

        while not identity():
            if launch is None or launch.poll() is not None:
                raise RuntimeError('owned Chrome exited or changed identity before readiness')
            if time.monotonic() >= deadline:
                raise RuntimeError('owned Chrome readiness timed out')
            await asyncio.sleep(.1)
        driver = configured_driver(pid)
        while True:
            if not identity():
                raise RuntimeError('owned Chrome identity changed during window binding')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("footwork's Chrome has no on-screen window after bounded recovery")
            wins = await asyncio.wait_for(driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True)),
                                          timeout=remaining)
            if wins.windows:
                if any(w.pid != pid for w in wins.windows):
                    raise RuntimeError('window discovery returned an unrelated browser process')
                break
            if helper is None:
                if sys.platform == 'linux':
                    args = _chrome_args(url or 'about:blank', new_window=True)
                    args.extend(_recovery_flags(pid, incarnation))
                elif sys.platform == 'darwin':
                    args = ['open', '-na', 'Google Chrome', '--args', f'--user-data-dir={PROFILE_DIR}',
                            '--new-window', url or 'about:blank']
                else:
                    raise RuntimeError('browser window recovery is unavailable on this platform')
                helper = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,  # noqa: ASYNC220 - retain ownership before yielding
                                          start_new_session=True)
            if helper.poll() not in (None, 0):
                raise RuntimeError('owned browser new-window helper exited unsuccessfully')
            await asyncio.sleep(.1)
        w = max(wins.windows, key=lambda w: w.bounds.width * w.bounds.height)
        bridge = BrowserBridge(driver, pid, w.window_id, policy=policy)
        bridge.launch_identity = {'pid': pid, 'incarnation': incarnation, 'new_process': launch is not None}
        await asyncio.wait_for(bridge.attach(), timeout=max(.001, deadline - time.monotonic()))
        if not identity():
            raise RuntimeError('owned Chrome identity changed while attaching')
        succeeded = True
        return driver, bridge
    finally:
        _stop_launch(helper)
        if not succeeded:
            _stop_launch(launch)
            if driver is not None:
                await asyncio.wait_for(driver.shutdown(), timeout=2)
