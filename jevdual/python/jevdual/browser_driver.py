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
import logging
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jevdual.effectors.base import BrowserBinding, BrowserOperations, BrowserReply
from jevdual.menu import Candidate, Menu, _tri, control_state

log = logging.getLogger("jevdual.browser")

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR = Path(
    os.environ.get("FOOTWORK_CHROME_PROFILE", str(Path.home() / ".config/jevdual/chrome-profile"))
)
PORT = int(os.environ.get("FOOTWORK_CHROME_PORT", "9333"))
SESSION_LABEL = "footwork"
#: seconds a new launch gets to put its own window on screen before a recovery window is opened
RECOVERY_GRACE_S = 5.0
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
    from jevdual.coordination import checkpoint

    checkpoint()
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
    from jevdual.effectors import require_available

    require_available("browser")
    from jevdual.effectors.cua import authorization_host

    return authorization_host(pid, executable=chrome_executable(), owned_pid=lambda: chrome_pid())


def configured_driver(pid: int) -> Any:
    """Compatibility entrypoint for the owned-browser CUA effector."""
    from jevdual.effectors import browser_effector

    return browser_effector(pid, host_factory=_host_class)


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


#: how far (CSS px) the centre ``DOM.getBoxModel`` reports may sit from the centre page script reports
LOCATE_TOLERANCE_PX = 2.0
#: how far (CSS px) a filmed target's centre may move while the pointer travels to it
DRIFT_TOLERANCE_PX = 0.5
Rect = tuple[float, float, float, float]


def pointer_shown(cursor: Any) -> bool:
    """Whether the system pointer shows over an element whose computed ``cursor`` is this.

    A page can hide the pointer over an element (``none``) or replace it with an image that may be
    empty or transparent, and a pointer's position then shows nothing on film. Only a single keyword
    other than ``none`` counts; the driver reports ``none`` under a pointer lock. The driver's two
    filmed deliveries apply the same rule in the turn they act."""
    return isinstance(cursor, str) and re.fullmatch(r"[a-z-]+", cursor) is not None and cursor != "none"


def _hidden(cursor: Any, where: str) -> str:
    if cursor is None:
        return f"the driver did not say what the pointer looks like {where} (it needs cua-driver locate9)"
    return (f"the page hides or replaces the pointer {where} (cursor: {str(cursor)[:40]}); "
            "a filmed take needs the system pointer showing")


def located_rect(locate: Any, point: tuple[float, float] | None = None) -> tuple[Rect | None, str]:
    """A target's rectangle in viewport CSS px from the driver's ``locate`` block, when a filmed pointer
    can be put on it: ``(rect, "")``, or ``(None, why)``.

    The driver must have read the page in an isolated world, where the page's own script cannot answer
    for it, and must say it checks a filmed pointer's position inside the delivery itself
    (``filmed_delivery``): an older driver accepts the position with a click or a type and ignores it,
    and the driver that answers this is the one that will deliver. The target must be in the tab's own
    frame, in a document the browser is showing; at 100% page zoom and pinch scale 1, the only case in
    which viewport CSS px are screen points from the content origin; wholly inside the viewport and
    inside every ancestor that clips or scrolls its overflow, so the film shows the whole of what is
    acted on (the filmed delivery scrolls nothing, so it does not depend on this); hit at its centre
    (itself or something inside it), with the pointer showing there (``pointer_shown``); and where
    ``DOM.getBoxModel`` also puts it. With ``point`` (where the pointer was sent), that point must lie
    inside the rectangle and hit the target too, with the pointer showing there."""
    if not isinstance(locate, dict):
        return None, "the driver reported no position (it needs cua-driver locate9)"
    if locate.get("available") is not True:
        return None, f"the driver could not locate it ({locate.get('reason') or 'no reason given'})"
    if locate.get("world") != "isolated":
        return None, ("the driver did not read the page out of reach of the page's own script "
                      "(it needs cua-driver locate9)")
    if locate.get("filmed_delivery") is not True:
        return None, ("the driver does not say it checks the pointer's position when it delivers "
                      "(it needs cua-driver locate9)")

    def numbers(value: Any, keys: tuple[str, ...]) -> tuple[float, ...] | None:
        if not isinstance(value, dict):
            return None
        out = []
        for key in keys:
            item = value.get(key)
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
                return None
            out.append(float(item))
        return tuple(out)

    rect = numbers(locate.get("rect"), ("x", "y", "width", "height"))
    view = numbers(locate.get("viewport"), ("width", "height", "zoom", "scale"))
    box = numbers(locate.get("box_center"), ("x", "y"))
    if rect is None or rect[2] <= 0 or rect[3] <= 0:
        return None, "the driver reported no usable rectangle"
    if view is None:
        return None, "the driver did not report the viewport's size, zoom and scale"
    if abs(view[2] - 1.0) > 1e-3 or abs(view[3] - 1.0) > 1e-3:
        return None, f"the page is at zoom {view[2]:g} and pinch scale {view[3]:g}; a filmed pointer needs both at 1"
    shown = locate.get("visibility_state")
    if shown != "visible":
        if shown is None:
            return None, "the driver did not say whether the page is showing (it needs cua-driver locate9)"
        return None, f"the page is not showing (its document is {str(shown)[:20]!r}); its tab is not the one on screen"
    x, y, w, h = rect
    if x < -0.5 or y < -0.5 or x + w > view[0] + 0.5 or y + h > view[1] + 0.5:
        return None, "it is not wholly in view; a filmed take acts only on a target the film shows whole"
    clipped = locate.get("clipped")
    if clipped is not False:
        if clipped is not True:
            return None, "the driver did not say whether a container clips it (it needs cua-driver locate9)"
        return None, ("a scrolling or clipping container hides part of it; a filmed take acts only on a "
                      "target the film shows whole")
    hit = locate.get("hit")
    if hit not in ("target", "descendant"):
        return None, ("another element is at its centre" if hit == "other" else "nothing is at its centre")
    if not pointer_shown(locate.get("cursor")):
        return None, _hidden(locate.get("cursor"), "over it")
    centre = (x + w / 2, y + h / 2)
    if box is None or math.dist(box, centre) > LOCATE_TOLERANCE_PX:
        return None, "its position could not be confirmed without page script"
    if point is not None:
        at = numbers(locate.get("point"), ("x", "y"))
        if at is None or math.dist(at, point) > 0.01:
            return None, "the driver did not report what is where the pointer landed"
        if not (x <= point[0] <= x + w and y <= point[1] <= y + h):
            return None, f"the pointer landed at {point[0]:.1f},{point[1]:.1f}, outside it"
        under = locate["point"].get("hit")
        if under not in ("target", "descendant"):
            return None, ("another element is under the pointer" if under == "other"
                          else "nothing of the page is under the pointer")
        if not pointer_shown(locate["point"].get("cursor")):
            return None, _hidden(locate["point"].get("cursor"), "where it landed")
    return rect, ""  # type: ignore[return-value]


def unfocused(locate: Any) -> str | None:
    """Why a located target cannot be typed into in a filmed take, or None when it can: it must already
    be the active element of its root. The filmed insert focuses nothing (a field can move when it
    gains focus, after the pointer was verified on it) and inserts only into the active element, so a
    field without focus is refused here, before the pointer moves. A filmed click on it gives it
    focus."""
    if not isinstance(locate, dict) or not isinstance(locate.get("focused"), bool):
        return "the driver did not say whether it has focus (it needs cua-driver locate9)"
    if not locate["focused"]:
        return "it does not have focus; click it first, then type"
    return None


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
    #: the effector's own delivery word on a refusal ("unknown" after an acknowledged input), and
    #: whether it says a retry is safe. Carried for the record; a refusal alone never means not sent.
    delivery: str | None = None
    retryable: bool | None = None
    #: the effector's advisory recovery text and suggested call; diagnostic data, never agent-callable
    hint: str | None = None
    next_call: dict[str, Any] | None = None
    #: the effector's escalation advice (target, reason); diagnostic data, never a next step
    escalation: dict[str, Any] | None = None


#: effector effect words carried through unchanged. Each reads the target's state around the action
#: and settles nothing about the application. A non-error reply that says "refused" is not taken as
#: proof that nothing was sent, and any other or missing word is no evidence of an effect.
_CARRIED_EFFECTS = frozenset({"confirmed", "partial", "suspected_noop"})


def _refusal_message(reply: BrowserReply) -> str:
    return (reply.refusal.message if reply.refusal is not None else "") or reply.text


def _with_text(reply: BrowserReply) -> dict[str, Any]:
    """The reply as the compatibility ``attach`` result: its fields plus ``_text`` and ``_is_error``."""
    out = dict(reply.payload)
    out.setdefault("_text", reply.text)
    out.setdefault("_is_error", reply.is_error)
    return out


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
        operations: BrowserOperations | None = None,
    ):
        from jevdual.effectors import browser_operations
        from jevdual.posture import ExecutionPolicy

        #: the driver's lifecycle (shutdown) stays with whoever created it; the bridge only acts
        self.driver = driver
        self.operations = operations or browser_operations(driver, session=session)
        self.pid = pid
        self.window_id = window_id
        self.session = session
        #: the execution posture (jevdual.posture): a replace-typed field selects the tab for about
        #: 100 ms (footwork-9c's tab probe, 2026-09-25), which is a foreground step for the posture
        self.policy = policy or ExecutionPolicy("background_only")
        self.target_id: str | None = None
        self.tab_id: str | None = None
        self.binding: BrowserBinding | None = None
        self.target_pin: dict[str, Any] = {}
        self.last: WebMenu | None = None
        #: filmed pointer mode (``jevdual.filmed``, B7): the real pointer travels onto each page target
        #: before the page action; set by the session from its filmed record
        self.filmed: Any = None
        #: with ``filmed``: ``scene(filmed, url)`` says why the take's recorded scene no longer holds, or
        #: None (``jevdual.filmed.browser_scene_change`` bound to this window, set by the session). A
        #: filmed bridge without one refuses every page action.
        self.scene: Any = None

    async def attach(self, *, tab_id: str | None = None, expect_url: str | None = None) -> dict[str, Any]:
        """Bind the window's browser target. With ``expect_url`` (the page a session last observed) the
        bridge binds the one tab showing that page, and refuses when none or several do. The Driver's tab
        ids are handles for one connection, new on every command (the Q13 oracle stage, 2026-09-28), so a
        session cannot carry them across commands. ``tab_id`` binds a handle within one connection.
        Without either, it takes the active tab (a new session)."""
        prep = await self.operations.prepare(pid=self.pid, window_id=self.window_id)
        if prep.status == "refused":
            raise RuntimeError(f"browser_prepare refused: {_refusal_message(prep)[:200]}")
        reply = await self.operations.bind(pid=self.pid, window_id=self.window_id)
        if reply.status != "ok":
            raise RuntimeError(f"bind refused: {_refusal_message(reply)[:200]}")
        bound = _with_text(reply)
        self.target_id = bound["target_id"]
        tabs = bound.get("tabs") or []
        self.binding = BrowserBinding(target_id=self.target_id, tabs=tuple(tabs))
        if tab_id is not None:
            if not any(t.get("tab_id") == tab_id for t in tabs):
                raise RuntimeError(
                    f"the session's tab {tab_id} is no longer in this window; nothing dispatched. "
                    "Start a new session on the tab you want."
                )
            self.tab_id = tab_id
            return bound
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
        active = next((t for t in tabs if t.get("active")), tabs[0] if tabs else None)
        if active is None:
            raise RuntimeError("bound target has no tab")
        self.tab_id = active["tab_id"]
        return bound

    async def _validate_pin(self, url: str | None = None) -> None:
        if self.target_pin:
            from jevdual.browser_target import resolve

            await resolve(self.pid, url=url, expected=self.target_pin)

    async def observe(self, *, screenshot_path: str | None = None, **_: Any) -> WebMenu:
        if self.target_id is None:
            await self.attach()
        await self._validate_pin()
        reply = await self.operations.snapshot(target_id=self.target_id, tab_id=self.tab_id)
        if reply.status == "refused":
            raise RuntimeError(f"snapshot refused: {_refusal_message(reply)[:200]}")
        self.last = menu_from_semantic(dict(reply.payload))
        await self._validate_pin(self.last.menu.url)
        return self.last

    def _fresh(self, nm: WebMenu, id: int) -> tuple[Candidate, str]:
        if self.last is None or nm.snapshot_id != self.last.snapshot_id:
            raise RuntimeError("stale snapshot; reobserve")
        c = nm.menu.candidate(id)
        ref = nm.refs.get(id)
        if c is None or ref is None:
            raise RuntimeError(f"id {id} is not on snapshot {nm.snapshot_id}")
        return c, ref

    def _effect(self, reply: BrowserReply, op: str, id: int, label: str) -> BrowserEffect:
        advice = {
            "hint": reply.hint,
            "next_call": dict(reply.next_call) if reply.next_call else None,
            "escalation": dict(reply.escalation) if reply.escalation else None,
        }
        if reply.refused:
            refusal = reply.refusal
            return BrowserEffect(
                op,
                id,
                label,
                "refused",
                summary=_refusal_message(reply)[:200],
                error_code=refusal.code if refusal is not None else None,
                delivery=refusal.delivery if refusal is not None else None,
                retryable=refusal.retryable if refusal is not None else None,
                # only an effector that refused before sending may say nothing was sent
                dispatched=reply.dispatched is not False,
                **advice,
            )
        effect = reply.effect if reply.effect in _CARRIED_EFFECTS else "unverifiable"
        return BrowserEffect(
            op, id, label, effect, evidence=reply.evidence, summary=reply.text[:200], **advice
        )

    #: form controls whose trusted (hardware-like) click did not toggle them in the background
    #: on 2026-09-25 (receipts said suspected no-op, the snapshot agreed): a synthetic DOM click
    #: is the honest route for these, and the receipt still proves the outcome
    DOM_EVENT_ROLES = frozenset({"radio", "checkbox", "switch"})

    async def act(
        self, nm: WebMenu, operation: str, id: int, text: str | None = None, *, route: str | None = None
    ) -> BrowserEffect:
        c, ref = self._fresh(nm, id)
        await self._validate_pin(nm.menu.url)
        base = {"target_id": self.target_id, "tab_id": self.tab_id, "ref": ref}
        if operation == "click":
            # 2026-09-25: in this background posture the trusted route toggled no radio or checkbox,
            # activated no submit button and opened no suggestion link (six no-op receipts, zero
            # successes); the DOM route did all of them. DOM is the default; the receipt proves the
            # outcome either way, and --route trusted is there for controls that ignore synthetic clicks.
            input_route = route or "dom_event"
            refused, moved, at = await self._filmed_approach(operation, id, c, ref, nm.menu.url, route=input_route)
            if refused is not None:
                return refused
            out = await self.operations.click(**base, input_route=input_route, **self._filmed_point(at))
            eff = self._after_approach(self._incomplete_click(self._effect(out, operation, id, c.label), out), moved)
            eff = await self._after_delivery(eff, at, nm.menu.url)
            self.last = None
            return dataclasses.replace(eff, route=out.route or input_route)
        elif operation in ("type", "append"):
            # browser_type selects the bound tab for about 100 ms in every mode except
            # insert_text with replace=false (page visibility probe by footwork-9c, 2026-09-25): in
            # that window the person's keystrokes can land in the agent's tab. Inserting into an
            # empty field is the background form; replacing held text is a foreground step and asks
            # the posture. Keystroke mode is never used.
            holds = (c.value or "") if c.role != "password" else ""
            if operation == "append" and (holds or c.role == "password"):
                # Without replace, browser_type focuses the node and inserts at the caret focus
                # leaves, which was the start of the field (BH7/BH8), so this route cannot append
                # onto held text. Rebuilding the value from the observation is not safe either: the
                # observation trims it. Nothing is sent; the caller can type the whole value.
                self.last = None
                return BrowserEffect(
                    operation, id, c.label, "refused", route="cdp", dispatched=False,
                    error_code="append_unavailable",
                    summary=f"{c.label!r} "
                            + ("may hold text this observation cannot read" if c.role == "password"
                               else "holds text")
                            + "; this route inserts at the start of held text, so nothing was sent. "
                              "Type the whole intended value instead (a foreground step).",
                )
            needs_replace = operation == "type" and bool(holds)
            # a filmed take refuses a replacement outright (replace_unfilmed, in _filmed_approach), so
            # asking the posture for it would only advise a step that is then refused
            if needs_replace and self.filmed is None:
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
            refused, moved, at = await self._filmed_approach(operation, id, c, ref, nm.menu.url,
                                                             replacing=needs_replace)
            if refused is not None:
                return refused
            out = await self.operations.type_text(**base, text=text or "", replace=needs_replace,
                                                  **self._filmed_point(at))
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
        eff = self._after_approach(self._effect(out, operation, id, c.label), moved)
        return await self._after_delivery(eff, at, nm.menu.url)

    def _filmed_point(self, at: tuple[float, float] | None) -> dict[str, Any]:
        """The driver's ``filmed_point`` for a pointer verified at screen point ``at``: the same point in
        viewport CSS px. Nothing when the take is not filmed, so an unfilmed call is unchanged."""
        if at is None or self.filmed is None:
            return {}
        origin = self.filmed.viewport(0.0, 0.0)
        return {"filmed_point": (at[0] - origin[0], at[1] - origin[1])}

    #: Every reply the driver gives for a page click that is neither a completed click nor a refusal
    #: (cua-driver locate9, tools.rs ``DomClickNext``), by the start of its text: a sequence that
    #: stopped part way, one that did not report completing, and one a dialog interrupted or followed.
    _PARTIAL_CLICK = re.compile(
        r"^sent part of a synthetic DOM click .*?: (the ref's node left the filmed point|"
        r"the page hid or replaced the pointer over the ref's node|the ref's node left its document) "
        r"after (\w+), so the rest of the sequence was not sent", re.DOTALL)
    _INTERRUPTED_CLICK = re.compile(
        r"^ran a synthetic DOM click .*?, but its sequence did not report completing \((.*?)\);", re.DOTALL)
    _DIALOG_CLICK = re.compile(r"^dispatched synthetic DOM click .*?; its handler opened an? (\w+) dialog", re.DOTALL)
    #: its one refusal of a filmed click that does not begin with what was sent: the text is the
    #: unfilmed sequence's and is left as it is there
    _GONE_BEFORE_CLICK = "the ref's node left its document before the click's first event"
    #: what it adds to a completed filmed click whose press gave no focus
    _UNFOCUSED_CLICK = ". The press moved no focus: "
    _PRESS_EVENTS = ("pointerdown", "mousedown", "pointerup", "mouseup")

    def _incomplete_click(self, eff: BrowserEffect, out: BrowserReply) -> BrowserEffect:
        """A filmed click that did not complete, in one sentence that begins with what was sent, and
        marked so that the session says it (``filmed.PAGE_MARKS``).

        The driver sends every event of a filmed click only to an element under the pointer and stops
        where it cannot. Stopped before anything, or after hover events only, it refuses, in a text
        that begins with what was sent, and that is passed on as it is. The other outcomes are not
        refusals, and their texts are longer than a summary keeps and written for a caller that can
        act on the driver's advice, which this one cannot:

        - the sequence stopped after the press (the control left the pointer, the page hid the
          pointer, or the node left its document): the press went and no click event did;
        - the node left its document during the hover events: no press went;
        - the sequence did not report completing, or a dialog opened: what was sent is unknown.

        One completed click is marked too, without becoming an error: the driver gives focus only to
        an element of the control, so for a control inside a focusable container the press moves no
        focus where a pointer's would have focused the container. The click went; the person is told
        the focus did not, and what to click for it.

        Outside a filmed take nothing is changed."""
        if self.filmed is None:
            return eff
        if eff.effect == "refused":
            if eff.summary.startswith(self._GONE_BEFORE_CLICK):
                return dataclasses.replace(eff, summary=f"no event was sent: {eff.summary}"[:200])
            return eff
        text = out.text or ""
        observe = "so observe before acting again."
        if (partial := self._PARTIAL_CLICK.match(text)) is not None:
            why, last = partial[1], partial[2]
            if last in self._PRESS_EVENTS:
                mark = "click_stopped_after_press"
                summary = (f"the click stopped after {last} and no click event was sent: {why}. The press was "
                           f"sent; what it did is unverifiable, {observe}")
            else:
                mark = "click_stopped_before_press"
                summary = (f"no press or click was sent: {why} after {last}. Hover events were sent; what they "
                           f"did is unverifiable, {observe}")
        elif (interrupted := self._INTERRUPTED_CLICK.match(text)) is not None:
            mark = "click_interrupted"
            summary = (f"the click did not report completing ({interrupted[1]}): some of its events may have been "
                       f"sent and what they did is unverifiable, {observe}")
        elif (dialog := self._DIALOG_CLICK.match(text)) is not None:
            mark = "click_interrupted"
            summary = (f"a {dialog[1]} dialog opened during the click and is blocking the page: whether the whole "
                       f"click was sent is unknown, {observe}")
        elif self._UNFOCUSED_CLICK in text:
            mark = "focus_not_given"
            summary = ("the press moved no focus: the element a press would focus holds this control and is not "
                       "part of it. The click was sent; click that element to focus it.")
        else:
            return eff
        return dataclasses.replace(eff, summary=summary, evidence=(*eff.evidence, mark))

    async def _after_delivery(
        self, eff: BrowserEffect, at: tuple[float, float] | None, url: str | None
    ) -> BrowserEffect:
        """After a filmed page action that was not refused: were the pointer and the page still where
        they were verified?

        The page side is checked inside the delivery itself, against the viewport point Footwork gave
        it. What nothing in the page can see is the pointer leaving, the window moving under it, or
        something that is not the page lying over it, so all three are read again here, as they were
        immediately before the delivery: the pointer (one that is not at ``at`` ends the take, as
        ``Filmed.held`` does), the frames of the window and its page area, and what the system finds
        under the pointer. The address, the main window and the frontmost application are not read:
        the action's own effects may change them, and the next filmed action reads the whole scene
        before it does anything. A finding is added to the effect, which then says the action was
        delivered without that proof; it is not turned into a refusal, because the action went.

        The two readings bracket the delivery and do not span it: a native surface that covers the
        pointer only between them is seen by neither. No reader of state can exclude that; the film
        is the record of it."""
        if at is None or self.filmed is None or eff.effect == "refused":
            return eff
        from jevdual.filmed import FilmedRefusal

        found: list[tuple[str, str]] = []
        try:
            await self.filmed.held(at)
        except FilmedRefusal as refusal:
            found.append(("pointer_left_during_delivery",
                          f"the pointer was not where it was verified ({refusal.code}); the take ended"))
        try:
            await self._scene(url, at, delivered=True)
        except FilmedRefusal as refusal:
            found.append(("scene_changed_during_delivery", refusal.reason))
        if not found:
            return eff
        findings = "; and ".join(why for _, why in found)
        if any(mark.startswith("click_") or mark == "focus_not_given" for mark in eff.evidence):
            # what the click itself has to say comes first; what was found afterwards follows it
            summary = f"{eff.summary} When it returned, {findings}."
        else:
            summary = f"the {eff.operation} was delivered, but when it returned {findings}. {eff.summary}"
        return dataclasses.replace(eff, summary=summary[:500],
                                   evidence=(*eff.evidence, *(mark for mark, _ in found)))

    @staticmethod
    def _after_approach(eff: BrowserEffect, moved: bool) -> BrowserEffect:
        """A page action refused after a filmed approach posted pointer events still says the pointer
        moved; its own account of what reached the page is kept as it is."""
        if not moved or eff.effect != "refused":
            return eff
        lead = f"the pointer moved; the {eff.operation} was then refused: "
        return dataclasses.replace(eff, summary=(lead + eff.summary)[:300],
                                   evidence=(*eff.evidence, "pointer_moved"))

    async def _locate(
        self, ref: str, point: tuple[float, float] | None = None
    ) -> tuple[Rect | None, str, Any]:
        """The target's rectangle or why there is none (``located_rect``), and the driver's locate block."""
        try:
            reply = await self.operations.locate(target_id=self.target_id, tab_id=self.tab_id, ref=ref, point=point)
        except Exception as exc:  # noqa: BLE001 - any failed read is a refusal: the caller withholds the action
            return None, f"the locate call failed ({type(exc).__name__}: {str(exc)[:100]})", None
        if reply.refused:
            return None, _refusal_message(reply)[:160], None
        block = reply.payload.get("locate")
        return (*located_rect(block, point), block)

    async def _scene(
        self, url: str | None, point: tuple[float, float] | None = None, *, delivered: bool = False
    ) -> None:
        """Refuse ``scene_changed`` unless the window on screen is still the take's recorded scene and,
        with ``point`` (screen points), the page of that window is what lies at that point.
        ``delivered`` is the reading for after a page action: the frames and the point only
        (``jevdual.filmed.browser_scene_change``)."""
        from jevdual.filmed import FilmedRefusal

        if self.scene is None:
            raise FilmedRefusal("scene_changed", "this session has no way to check the filmed window")
        try:
            why = await asyncio.to_thread(self.scene, self.filmed, url, point,
                                          **({"delivered": True} if delivered else {}))
        except Exception as exc:  # noqa: BLE001 - a scene that cannot be read is not a scene that holds
            why = f"the filmed window could not be read ({type(exc).__name__}: {str(exc)[:100]})"
        if why:
            raise FilmedRefusal("scene_changed", why)

    async def _filmed_approach(
        self, operation: str, id: int, c: Candidate, ref: str, url: str | None, *,
        route: str | None = None, replacing: bool = False,
    ) -> tuple[BrowserEffect | None, bool, tuple[float, float] | None]:
        """In a filmed take, put the real pointer on the target before the page action.

        The scene is checked (``_scene``), the driver reads where the element is now
        (``located_rect``), the pointer travels there, and the driver reads it again, asked about the
        point the pointer is at as the system reports it: the action goes ahead only if that point is
        on the element, the element has not moved, the scene still holds with the page under that
        point, and the pointer is still there. Returns the refusal, if any, whether the approach
        posted pointer events, and the screen point the pointer was verified at. Any refusal withholds
        the page action; when events had been posted, the refusal says so instead of claiming nothing
        happened.

        These checks decide whether to send. The proof that the pointer is on the target at delivery
        is the driver's: the caller passes the verified point with the action (``_filmed_point``), and
        the driver checks it against the element in the same turn of script as each event of the
        action, in a world the page's script cannot reach, scrolling and focusing nothing first, and
        stops when the element is no longer under that point or the page hides the pointer there.
        What the driver cannot see (the pointer itself, the window, a surface over the page) is read
        here immediately before the delivery and again immediately after it (``_after_delivery``).

        Three actions cannot be delivered that way and are refused before the pointer moves. A click by
        the trusted route is pressed at the content-box centre, not the point verified
        (``route_unfilmed``); a type that replaces held text selects it first (``replace_unfilmed``);
        both before anything is read. A filmed insert focuses nothing, so a field that is not already
        the active element is refused (``target_unfocused``, by ``unfocused``, read with the first
        locate and again after the approach): a filmed click on the field gives it focus.
        ``replacing`` is whether the type replaces held text."""
        if self.filmed is None:
            return None, False, None
        from jevdual.filmed import FilmedRefusal

        gestures = len(self.filmed.gestures)
        typing = operation in ("type", "append")
        try:
            self.filmed.check()
            if route == "trusted":
                raise FilmedRefusal(
                    "route_unfilmed",
                    f"{c.label!r}: a filmed click goes by the DOM route. The trusted route presses at the "
                    "centre of the content box, which is not the point the pointer is verified on; "
                    "leave out --route trusted")
            if replacing:
                raise FilmedRefusal(
                    "replace_unfilmed",
                    f"{c.label!r} holds text, and replacing it selects that text first, after the pointer "
                    "was verified; a filmed take types only into an empty field")
            await self._scene(url)
            rect, why, block = await self._locate(ref)
            if rect is None:
                raise FilmedRefusal("target_unlocated", f"{c.label!r}: {why}")
            if typing and (gap := unfocused(block)):
                raise FilmedRefusal("target_unfocused", f"{c.label!r}: {gap}")
            centre = (rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)
            x, y = self.filmed.viewport(rect[0], rect[1])
            await self.filmed.approach((x, y, rect[2], rect[3]), c.label)
            # where the pointer is, not where it was sent: a start within a point of the centre posts nothing
            here = await self.filmed.pointer()
            origin = self.filmed.viewport(0.0, 0.0)
            again, why, block = await self._locate(ref, (here[0] - origin[0], here[1] - origin[1]))
            if again is None:
                raise FilmedRefusal("target_moved", f"{c.label!r} could not be confirmed under the pointer: {why}")
            drift = math.dist((again[0] + again[2] / 2, again[1] + again[3] / 2), centre)
            if drift > DRIFT_TOLERANCE_PX:
                raise FilmedRefusal("target_moved", f"{c.label!r} moved {drift:.1f} px while the pointer travelled")
            if typing and (gap := unfocused(block)):
                raise FilmedRefusal("target_unfocused", f"{c.label!r} lost focus while the pointer travelled: {gap}")
            await self._scene(url, here)
            await self.filmed.held(here)
        except FilmedRefusal as refusal:
            self.last = None
            moved = self._posted(gestures)
            lead = f"the pointer moved but the {operation} was not sent: " if moved else ""
            return BrowserEffect(operation, id, c.label, "refused", route="desktop", dispatched=False,
                                 error_code=refusal.code, summary=(lead + refusal.reason)[:300],
                                 evidence=("pointer_moved",) if moved else ()), moved, None
        return None, self._posted(gestures), here

    def _posted(self, since: int) -> bool:
        """Whether a gesture of this take after index ``since`` posted pointer events."""
        return any(g.get("posted") for g in self.filmed.gestures[since:])

    async def navigate(self, url: str) -> BrowserEffect:
        if self.target_id is None:
            await self.attach()
        if self.filmed is not None:
            from jevdual.filmed import FilmedRefusal

            try:
                self.filmed.check()  # an ended take takes no further page action either
            except FilmedRefusal as refusal:
                return BrowserEffect("navigate", -1, url, "refused", route="desktop", dispatched=False,
                                     error_code=refusal.code, summary=refusal.reason[:300])
        await self._validate_pin(self.last.menu.url if self.last else None)
        out = await self.operations.navigate(target_id=self.target_id, tab_id=self.tab_id, url=url)
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


async def bind_footwork_chrome(
    url: str | None = None, *, policy: Any = None, wrap_operations: Any = None
) -> tuple[Any, BrowserBridge]:
    """Launch or find footwork's Chrome, build the configured Driver, bind its largest window.

    ``wrap_operations`` receives the driver's browser operations before the first attach and returns
    the operations the bridge uses (the session holder keeps the first prepare this way)."""
    from jevdual.effectors import require_available

    require_available("browser")
    from jevdual.effectors.cua import list_windows_input

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
        # A new launch's own window can take a few seconds to reach the screen. Recovering a window
        # before then opens a second one on the same page, which the unique-page pin then refuses
        # (BH4). An existing browser without a window is recovered at once.
        recover_after = time.monotonic() + (RECOVERY_GRACE_S if launch is not None else 0.0)
        while True:
            if not identity():
                raise RuntimeError('owned Chrome identity changed during window binding')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("footwork's Chrome has no on-screen window after bounded recovery")
            wins = await asyncio.wait_for(driver.list_windows(list_windows_input(pid=pid, on_screen_only=True)),
                                          timeout=remaining)
            if wins.windows:
                if any(w.pid != pid for w in wins.windows):
                    raise RuntimeError('window discovery returned an unrelated browser process')
                break
            if helper is None and time.monotonic() < recover_after:
                await asyncio.sleep(.1)
                continue
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
            # An invocation-owned singleton helper temporarily satisfies the
            # same root predicate. Complete/reap it before rediscovering roots;
            # never exclude an arbitrary matching PID from that predicate.
            while helper.poll() is None:
                if time.monotonic() >= deadline:
                    raise RuntimeError('owned browser new-window helper timed out')
                await asyncio.sleep(.1)
            if helper.wait(timeout=0) != 0:
                raise RuntimeError('owned browser new-window helper exited unsuccessfully')
            await asyncio.sleep(.1)
        w = max(wins.windows, key=lambda w: w.bounds.width * w.bounds.height)
        operations = None
        if wrap_operations is not None:
            from jevdual.effectors import browser_operations

            operations = wrap_operations(browser_operations(driver, session=SESSION_LABEL))
        bridge = BrowserBridge(driver, pid, w.window_id, policy=policy, operations=operations)
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
