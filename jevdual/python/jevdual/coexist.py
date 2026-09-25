"""The coexistence suite (Q15, ``docs/experiments/Q15.md``): does a footwork session run alongside a
person without taking their work, their input or their focus?

Each case puts a scripted :class:`Person` at the keyboard of a window it owns while the harness acts
through :class:`~jevdual.native.NativeBridge` (or the Driver's browser mode) on another target, then
judges the case on four conditions together:

1. the task's end state is exactly right (read through accessibility or the page's own report, never
   through the Driver that acted);
2. the person's work is exactly what they typed (their window's own record of it);
3. the target is the one intended (no write to another window or tab);
4. no prohibited focus or input side effect (the front app, the key window, the pointer, a keystroke
   the person could not send because their window had lost the front).

The person types through the HID event tap, as a keyboard does, so a keystroke goes to whatever app is
in front. Before each keystroke they check that their own app is in front and hold the key when it is
not (a person notices). That check and the keystroke are not atomic: an agent that takes the front
between them receives the keystroke, which is the diversion the suite exists to catch, and it shows up
in the agent's target and in the person's record.

The suite takes the keyboard. It refuses to start unless the machine has had no input for
``GUARD_IDLE_S`` seconds, and it marks a case ``contaminated`` (rerun, not counted) when the pointer
moved or the HID key-down count rose by more than the person's own keystrokes.
"""

# ruff: noqa: ASYNC220, ASYNC221 - a live harness: blocking process calls are part of each case's setup
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from jevdual.posture import ExecutionPolicy, MacActivity, activate, frontmost_pid

GUARD_IDLE_S = float(os.environ.get("FOOTWORK_Q15_IDLE_S", "20"))
BETWEEN_S = 1.0


class NotIdle(RuntimeError):
    pass


# ---- the machine ---------------------------------------------------------------------------------


def idle_seconds() -> float:
    return MacActivity().idle_seconds()


def require_idle(min_s: float = GUARD_IDLE_S) -> None:
    idle = idle_seconds()
    if idle < min_s:
        raise NotIdle(f"the machine had input {idle:.1f}s ago; the suite needs {min_s:.0f}s idle")


def pointer() -> tuple[float, float]:
    import Quartz

    p = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    return float(p.x), float(p.y)


def keydown_count() -> int:
    """Key-downs the HID system has seen (posted ones included, measured below per case)."""
    import Quartz

    return int(
        Quartz.CGEventSourceCounterForEventType(
            Quartz.kCGEventSourceStateHIDSystemState, Quartz.kCGEventKeyDown
        )
    )


# ---- the person ----------------------------------------------------------------------------------


class Person(threading.Thread):
    """Types ``text`` into the front app through the HID tap, one character every ``interval`` seconds,
    only while ``pid`` is in front. ``sent`` is what reached the keyboard; ``held`` the characters held
    back because another app was in front (each with the front pid)."""

    def __init__(self, pid: int, text: str, *, interval: float = 0.06, start_after: float = 0.0):
        super().__init__(daemon=True)
        self.pid = pid
        self.text = text
        self.interval = interval
        self.start_after = start_after
        self.sent = ""
        self.held: list[tuple[str, int | None]] = []
        self._halt = threading.Event()

    def stop(self) -> None:
        self._halt.set()

    @staticmethod
    def post(ch: str) -> None:
        import Quartz

        src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
        code = 36 if ch == "\n" else 0
        for down in (True, False):
            ev = Quartz.CGEventCreateKeyboardEvent(src, code, down)
            if ch != "\n":
                Quartz.CGEventKeyboardSetUnicodeString(ev, len(ch.encode("utf-16-le")) // 2, ch)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

    def run(self) -> None:
        if self.start_after:
            time.sleep(self.start_after)
        for ch in self.text:
            if self._halt.is_set():
                break
            front = frontmost_pid()
            if front != self.pid:
                self.held.append((ch, front))
            else:
                self.post(ch)
                self.sent += ch
            time.sleep(self.interval)


# ---- surfaces ------------------------------------------------------------------------------------


@dataclass
class TkSurface:
    """The person's own window (``jevdual.coexist_surface``) and the file its content lands in."""

    out: Path
    proc: subprocess.Popen[bytes]

    @property
    def pid(self) -> int:
        return self.proc.pid

    @classmethod
    def launch(cls, dir: Path, name: str, *, x: int = 60, y: int = 60) -> TkSurface:
        out = dir / f"{name}.txt"
        proc = subprocess.Popen(
            [sys.executable, "-m", "jevdual.coexist_surface", "--out", str(out), "--title", name]
            + ["--x", str(x), "--y", str(y)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)
        return cls(out, proc)

    def content(self) -> str:
        time.sleep(0.2)  # the surface writes every 50 ms
        return self.out.read_text() if self.out.exists() else ""

    def close(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def _textedit_pids() -> set[int]:
    out = subprocess.run(["pgrep", "-x", "TextEdit"], capture_output=True, text=True, check=False).stdout
    return {int(p) for p in out.split() if p.strip().isdigit()}


@dataclass
class TextEditInstance:
    """A TextEdit process of the suite's own, holding only the suite's documents (``open -n -g``: a new
    instance, launched without coming to the front, with window restoration off)."""

    pid: int
    windows: dict[str, int]  # file name -> CGWindowID

    @classmethod
    async def launch(cls, driver: Any, files: list[Path]) -> TextEditInstance:
        from cua_driver import ListWindowsInput

        before = _textedit_pids()
        subprocess.run(
            [
                "open",
                "-n",
                "-g",
                "-a",
                "TextEdit",
                *map(str, files),
                "--args",
                "-ApplePersistenceIgnoreState",
                "YES",
            ],
            check=True,
        )
        pid = None
        wins: dict[str, int] = {}
        for _ in range(40):
            await asyncio.sleep(0.25)
            new = _textedit_pids() - before
            if not new:
                continue
            pid = max(new)
            listed = await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))
            wins = {w.title: w.window_id for w in listed.windows if w.title}
            if all(f.name in wins for f in files):
                break
        if pid is None or not all(f.name in wins for f in files):
            raise RuntimeError(f"TextEdit did not open {', '.join(f.name for f in files)} (windows {wins})")
        return cls(pid, wins)

    def value(self, name: str) -> str:
        from jevdual import ax

        return ax.value(ax.resolve(self.pid, self.windows[name], "AXTextArea", None))

    def insert(self, name: str, text: str, *, at_start: bool = False) -> None:
        """Another actor's edit, through AX (the conflicting-edit case)."""
        from ApplicationServices import AXUIElementSetAttributeValue, AXValueCreate, kAXValueCFRangeType
        from Foundation import NSMakeRange

        from jevdual import ax

        el = ax.resolve(self.pid, self.windows[name], "AXTextArea", None)
        if at_start:
            AXUIElementSetAttributeValue(
                el, "AXSelectedTextRange", AXValueCreate(kAXValueCFRangeType, NSMakeRange(0, 0))
            )
            AXUIElementSetAttributeValue(el, "AXSelectedText", text)
        else:
            ax.insert_at_end(el, text)

    def key_window(self) -> str | None:
        """The title of the instance's main window, by AX."""
        from ApplicationServices import AXUIElementCreateApplication

        from jevdual.ax import _attr

        w = _attr(AXUIElementCreateApplication(self.pid), "AXFocusedWindow")
        return str(_attr(w, "AXTitle")) if w is not None else None

    def close(self) -> None:
        subprocess.run(["kill", "-9", str(self.pid)], check=False)


async def front(driver: Any, pid: int, window_id: int | None = None, *, timeout: float = 3.0) -> None:
    """Bring ``pid`` to the front for the person (setup only, before the case's clock starts)."""
    if window_id is None:
        # exact pid: the Driver's bring_to_front resolves by bundle and picked the wrong one of two
        # Python processes (2026-09-25)
        await asyncio.to_thread(activate, pid)
    else:
        await driver.call_tool("bring_to_front", json.dumps({"pid": pid, "window_id": window_id}))
    t0 = time.time()
    while time.time() - t0 < timeout:
        if frontmost_pid() == pid:
            await asyncio.sleep(0.3)
            return
        await asyncio.sleep(0.05)
    raise RuntimeError(f"pid {pid} did not come to the front for the person")


# ---- results -------------------------------------------------------------------------------------


@dataclass
class CaseResult:
    case: str
    checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    contaminated: str | None = None
    error: str | None = None

    @property
    def passed(self) -> bool:
        return (
            self.error is None
            and self.contaminated is None
            and bool(self.checks)
            and all(self.checks.values())
        )

    def check(self, name: str, ok: bool, **detail: Any) -> None:
        self.checks[name] = bool(ok)
        if detail:
            self.details[name] = detail

    def to_record(self) -> dict[str, Any]:
        return {**asdict(self), "passed": self.passed}


class Watch:
    """Front app, pointer and HID key-downs across a case; ``close`` names contamination by a real person."""

    def __init__(self) -> None:
        self.pointer = pointer()
        self.keys = keydown_count()
        self.fronts: list[tuple[float, int | None]] = []
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self) -> None:
        t0 = time.time()
        while not self._stop.is_set():
            f = frontmost_pid()
            if not self.fronts or self.fronts[-1][1] != f:
                self.fronts.append((round(time.time() - t0, 3), f))
            time.sleep(0.02)

    def close(self, r: CaseResult, *, posted_keys: int, agent_keys: int = 0) -> None:
        self._stop.set()
        self._t.join(timeout=2)
        moved = pointer()
        extra = keydown_count() - self.keys - posted_keys - agent_keys
        r.details["fronts"] = self.fronts
        r.details["keydown_delta_unexplained"] = extra
        agent_moved = bool(r.details.get("agent_pointer_moves"))
        r.checks.setdefault("pointer_untouched_by_agent", not agent_moved)
        if not agent_moved and max(abs(moved[0] - self.pointer[0]), abs(moved[1] - self.pointer[1])) > 1.0:
            r.contaminated = f"the pointer moved {self.pointer} -> {moved}: someone is at the machine"
        elif extra > 0:
            r.contaminated = f"{extra} key-downs nobody in the suite sent: someone is at the machine"

    def front_pids(self) -> set[int | None]:
        return {f for _, f in self.fronts}


# ---- the cases -----------------------------------------------------------------------------------

PERSON_TEXT = "The person keeps typing their own notes while the agent works nearby. "
DOC = "".join(("\t" * (i % 3)) + f"line {i:03d}  two  spaces 🧪\n" for i in range(120)) + "tail  \n\n  "


def _bridge(
    driver: Any, pid: int, wid: int, mode: str = "background_only", *, live_check: bool = True
) -> Any:
    from jevdual.native import NativeBridge

    return NativeBridge(driver, pid, wid, policy=ExecutionPolicy(mode), live_check=live_check)  # type: ignore[arg-type]


async def step(r: CaseResult, label: str, coro: Any) -> Any:
    """One agent step, with the pointer read before and after: a move inside a step is the agent's."""
    before = pointer()
    out = await coro
    after = pointer()
    if max(abs(after[0] - before[0]), abs(after[1] - before[1])) > 1.0:
        r.details.setdefault("agent_pointer_moves", []).append({"step": label, "from": before, "to": after})
    return out


def _text_area(nm: Any) -> int:
    return next(c.id for c in nm.menu.candidates if c.input_type == "textarea")


async def case_other_app(driver: Any, work: Path) -> CaseResult:
    """C1: the person types in their own app while the session edits a TextEdit document (one window, so
    background keys are allowed), in background_only."""
    r = CaseResult("C1_person_in_another_app")
    doc = work / "c1.txt"
    doc.write_text(DOC)
    te = await TextEditInstance.launch(driver, [doc])
    tk = TkSurface.launch(work, "c1-person")
    try:
        await front(driver, tk.pid)
        b = _bridge(driver, te.pid, te.windows[doc.name])
        watch = Watch()
        person = Person(tk.pid, PERSON_TEXT)
        person.start()
        await asyncio.sleep(0.3)
        effs = []
        nm = await b.observe()
        effs.append(
            await step(
                r,
                'b.act(nm, "append", _text_area(nm), "age',
                b.act(nm, "append", _text_area(nm), "agent line one"),
            )
        )
        nm = await b.observe()
        effs.append(await step(r, 'b.key(nm, "x")', b.key(nm, "x")))
        nm = await b.observe()
        scroll = next((c.id for c in nm.menu.candidates if "scroll" in c.operations), None)
        if scroll is not None:
            effs.append(await step(r, 'b.act(nm, "scroll", scroll)', b.act(nm, "scroll", scroll)))
        nm = await b.observe()
        effs.append(
            await step(
                r,
                'b.act(nm, "append", _text_area(nm), "age',
                b.act(nm, "append", _text_area(nm), "agent line two"),
            )
        )
        nm = await b.observe()
        effs.append(await step(r, 'b.hotkey(nm, ["cmd", "s"])', b.hotkey(nm, ["cmd", "s"])))
        person.join()
        watch.close(r, posted_keys=len(person.sent), agent_keys=1)
        want_doc = DOC + "\nagent line one" + "x" + "\nagent line two"
        got_doc = te.value(doc.name)
        got_person = tk.content()
        r.details["effects"] = [e.to_record() for e in effs]
        r.check("task_end_state_exact", got_doc == want_doc, got_tail=got_doc[-60:], want_tail=want_doc[-60:])
        r.check(
            "person_work_exact",
            got_person == PERSON_TEXT and not person.held,
            got=got_person,
            held=person.held,
        )
        r.check("no_write_elsewhere", got_person.count("x") == PERSON_TEXT.count("x"))
        r.check("front_never_left_person", watch.front_pids() == {tk.pid}, fronts=watch.fronts)
        r.check(
            "foreground_step_not_sent",
            not effs[-1].dispatched and effs[-1].error_code == "requires_foreground",
        )
        r.check("every_sent_step_background", all(e.delivery == "background" for e in effs if e.dispatched))
    finally:
        tk.close()
        te.close()
    return r


async def case_same_process(driver: Any, work: Path) -> CaseResult:
    """C2: the person types in document A while the session edits document B of the same TextEdit
    process, in background_only: the same-process key ambiguity."""
    r = CaseResult("C2_same_process_two_documents")
    a, bdoc = work / "c2-person.txt", work / "c2-agent.txt"
    a.write_text("")
    bdoc.write_text(DOC)
    te = await TextEditInstance.launch(driver, [a, bdoc])
    try:
        await front(driver, te.pid, te.windows[a.name])
        b = _bridge(driver, te.pid, te.windows[bdoc.name])
        watch = Watch()
        person = Person(te.pid, PERSON_TEXT)
        person.start()
        await asyncio.sleep(0.3)
        effs = []
        nm = await b.observe()
        effs.append(
            await step(
                r,
                'b.act(nm, "append", _text_area(nm), "age',
                b.act(nm, "append", _text_area(nm), "agent line one"),
            )
        )
        nm = await b.observe()
        effs.append(await step(r, 'b.key(nm, "x")', b.key(nm, "x")))
        nm = await b.observe()
        effs.append(
            await step(
                r,
                'b.act(nm, "append", _text_area(nm), "age',
                b.act(nm, "append", _text_area(nm), "agent line two"),
            )
        )
        person.join()
        key_window = te.key_window()
        watch.close(r, posted_keys=len(person.sent))
        got_a, got_b = te.value(a.name), te.value(bdoc.name)
        r.details["effects"] = [e.to_record() for e in effs]
        r.check(
            "task_end_state_exact", got_b == DOC + "\nagent line one\nagent line two", got_tail=got_b[-60:]
        )
        r.check("person_work_exact", got_a == PERSON_TEXT and not person.held, got=got_a, held=person.held)
        r.check(
            "ambiguous_key_not_sent", not effs[1].dispatched and effs[1].error_code == "requires_foreground"
        )
        r.check("person_window_stays_key", key_window == a.name, key_window=key_window)
        r.check("front_never_left_person", watch.front_pids() == {te.pid}, fronts=watch.fronts)
    finally:
        te.close()
    return r


async def case_conflicting_edit(driver: Any, work: Path) -> CaseResult:
    """C5: a long, whitespace-sensitive document; another actor edits it between the session's look and
    its append; the append is refused and nothing is lost; appended afresh it is exact."""
    r = CaseResult("C5_long_append_and_conflicting_edit")
    doc = work / "c5.txt"
    doc.write_text(DOC * 3)
    te = await TextEditInstance.launch(driver, [doc])
    tk = TkSurface.launch(work, "c5-person")
    try:
        await front(driver, tk.pid)
        b = _bridge(driver, te.pid, te.windows[doc.name], live_check=False)
        watch = Watch()
        person = Person(tk.pid, PERSON_TEXT)
        person.start()
        nm = await b.observe()
        te.insert(doc.name, "EDIT BY SOMEONE ELSE\n", at_start=True)
        refused = await step(r, "append", b.act(nm, "append", _text_area(nm), "agent line"))
        after_refusal = te.value(doc.name)
        nm = await b.observe()
        ok = await step(r, "append", b.act(nm, "append", _text_area(nm), "agent line ✓ 🧪"))
        person.join()
        watch.close(r, posted_keys=len(person.sent))
        edited = "EDIT BY SOMEONE ELSE\n" + DOC * 3
        r.details["effects"] = [refused.to_record(), ok.to_record()]
        r.check(
            "conflict_refused_before_write",
            not refused.dispatched
            and refused.error_code == "precondition_changed"
            and after_refusal == edited,
        )
        r.check("task_end_state_exact", te.value(doc.name) == edited + "\nagent line ✓ 🧪")
        r.check("person_work_exact", tk.content() == PERSON_TEXT and not person.held)
        r.check("front_never_left_person", watch.front_pids() == {tk.pid}, fronts=watch.fronts)
    finally:
        tk.close()
        te.close()
    return r


async def case_foreground_permitted(driver: Any, work: Path) -> CaseResult:
    """C4: foreground_permitted beside a person. (a) While they type, a step that needs the foreground
    yields and nothing is sent. (b) After three idle seconds it runs, and the front is theirs again
    afterwards with none of their later keystrokes lost. (c) When they move to another app during a
    foreground step, the bridge leaves them there."""
    r = CaseResult("C4_foreground_permitted_yields_and_hands_back")
    d1, d2 = work / "c4-a.txt", work / "c4-b.txt"
    d1.write_text("first document\n")
    d2.write_text(DOC)
    te = await TextEditInstance.launch(driver, [d1, d2])  # two windows: keys need the foreground
    tk = TkSurface.launch(work, "c4-person")
    tk2 = TkSurface.launch(work, "c4-elsewhere", x=640, y=60)
    try:
        await front(driver, tk.pid)
        b = _bridge(driver, te.pid, te.windows[d2.name], "foreground_permitted")
        watch = Watch()
        p1 = Person(tk.pid, "typing while the agent waits. ")
        p1.start()
        await asyncio.sleep(0.5)
        nm = await b.observe()
        busy = await step(r, "key", b.key(nm, "down", ["cmd"]))
        p1.join()
        # (b) idle three seconds and a bit, then a foreground chord (caret to the end: no content change)
        await asyncio.sleep(3.6)
        nm = await b.observe()
        idle_step = await step(r, "hotkey", b.hotkey(nm, ["cmd", "down"]))
        front_after_b = frontmost_pid()
        p2 = Person(tk.pid, "and typing again afterwards. ")
        p2.start()
        p2.join()
        # (c) the person moves to their other window while the menu step is in flight
        await asyncio.sleep(3.6)
        nm = await b.observe()

        def move() -> None:
            # the person clicks their other window as soon as the agent's window has the front: a tight
            # poll in its own thread, so the move can land inside a step that holds the front ~75 ms
            t0 = time.time()
            while time.time() - t0 < 5.0 and frontmost_pid() != te.pid:
                pass
            activate(tk2.pid)

        mover = threading.Thread(target=move, daemon=True)
        mover.start()
        moved_step = await step(r, "menu", b.menu(nm, ["Edit", "Select All"]))
        await asyncio.to_thread(mover.join, 6.0)
        r.details["move_overlapped_step"] = tk2.pid in ((moved_step.foreground or {}).get("fronts_during") or [])
        await asyncio.sleep(0.5)
        front_after_c = frontmost_pid()
        p3 = Person(tk2.pid, "now over here.")
        p3.start()
        p3.join()
        sent = len(p1.sent) + len(p2.sent) + len(p3.sent)
        watch.close(r, posted_keys=sent, agent_keys=1)
        r.details["effects"] = [busy.to_record(), idle_step.to_record(), moved_step.to_record()]
        r.check("yields_while_person_types", not busy.dispatched and busy.error_code == "human_active")
        r.check("runs_after_idle", idle_step.dispatched and idle_step.delivery == "foreground")
        r.check("front_is_persons_after", front_after_b == tk.pid, front_after=front_after_b)
        r.check(
            "person_work_exact",
            tk.content() == p1.text + p2.text and not p1.held and not p2.held,
            got=tk.content(),
            held=p1.held + p2.held,
        )
        # after the person's move lands, neither the agent's app nor their previous window takes the front
        seq = [f for _, f in watch.fronts]
        after_move = seq[seq.index(tk2.pid) :] if tk2.pid in seq else []
        r.check(
            "never_fights_persons_move",
            front_after_c == tk2.pid and bool(after_move) and set(after_move) == {tk2.pid},
            front_after=front_after_c,
            after_move=after_move,
            foreground=moved_step.foreground,
        )
        r.check("person_work_after_move_exact", tk2.content() == p3.text and not p3.held, got=tk2.content())
        r.check("other_document_unchanged", te.value(d1.name) == "first document\n")
        r.check("agent_document_unchanged", te.value(d2.name) == DOC)
    finally:
        tk2.close()
        tk.close()
        te.close()
    return r


# ---- C3: tab B while the person types in tab A --------------------------------------------------

PAGE = """<!doctype html><meta charset=utf-8><title>{title}</title>
<body style="font:16px sans-serif">{body}
<script>
const tab = {tab!r};
function post(path, obj) {{ fetch(path, {{method:'POST', body: JSON.stringify({{tab, ...obj, t: Date.now()}})}}); }}
document.addEventListener('visibilitychange', () => post('/event', {{kind:'visibility', state: document.visibilityState}}));
window.addEventListener('focus', () => post('/event', {{kind:'focus'}}));
window.addEventListener('blur', () => post('/event', {{kind:'blur'}}));
post('/event', {{kind:'load', state: document.visibilityState}});
{script}
</script>"""

PAGE_A = PAGE.format(
    title="person tab",
    tab="a",
    body="<textarea id=t rows=8 cols=60 autofocus></textarea>",
    script="const t=document.getElementById('t'); t.addEventListener('input',()=>post('/state',{value:t.value}));"
    " window.addEventListener('focus',()=>t.focus()); t.focus();",
)
PAGE_B = PAGE.format(
    title="agent tab",
    tab="b",
    body='<label>Name <input id=name aria-label="Name"></label> <button id=go>Submit</button>',
    script="document.getElementById('go').addEventListener('click',()=>post('/submit',"
    "{value:document.getElementById('name').value}));",
)


class _Pages(BaseHTTPRequestHandler):
    store: ClassVar[dict[str, Any]] = {}

    def log_message(self, *a: Any) -> None:
        return

    def do_GET(self) -> None:
        body = {"/a": PAGE_A, "/b": PAGE_B}.get(self.path.split("?")[0])
        self.send_response(200 if body else 404)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write((body or "").encode())

    def do_POST(self) -> None:
        n = int(self.headers.get("content-length") or 0)
        rec = json.loads(self.rfile.read(n) or b"{}")
        s = _Pages.store
        if self.path == "/state":
            s["a_value"] = rec.get("value", "")
        elif self.path == "/submit":
            s.setdefault("submits", []).append(rec.get("value"))
        else:
            s.setdefault("events", []).append(rec)
        self.send_response(204)
        self.end_headers()


async def case_background_tab(driver_unused: Any, work: Path) -> CaseResult:
    """C3: the person types in tab A of a Chrome window while the session fills and submits a form in tab B
    of the same window through the Driver's browser mode."""
    import jevdual.browser_driver as bd

    r = CaseResult("C3_background_tab_same_window")
    _Pages.store = {}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Pages)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    profile = work / "chrome-profile"
    port = 9400 + os.getpid() % 500
    subprocess.Popen(
        [
            bd.CHROME,
            f"--user-data-dir={profile}",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1000,700",
            f"{base}/a",
            f"{base}/b",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    driver = None
    try:
        pid = None
        for _ in range(60):
            await asyncio.sleep(0.25)
            out = subprocess.run(
                ["pgrep", "-f", f"user-data-dir={profile}"], capture_output=True, text=True, check=False
            )
            pids = [int(p) for p in out.stdout.split() if p.isdigit()]
            if pids:
                pid = min(pids)
                break
        assert pid is not None, "test Chrome did not start"
        await asyncio.sleep(3.0)
        driver = bd.configured_driver(pid)
        from cua_driver import ListWindowsInput

        wins = (await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))).windows
        w = max(wins, key=lambda w: w.bounds.width * w.bounds.height)
        bridge = bd.BrowserBridge(driver, pid, w.window_id, session="q15")
        bound = await bridge.attach()
        tabs = bound.get("tabs") or []
        r.details["tabs"] = [{k: t.get(k) for k in ("tab_id", "active", "title", "url")} for t in tabs]
        tab_b = next(t for t in tabs if "/b" in str(t.get("url", "")) or t.get("title") == "agent tab")
        tab_a_active = any(t.get("active") and "/a" in str(t.get("url", "")) for t in tabs)
        if not tab_a_active:
            raise RuntimeError(f"setup: the person's tab is not the selected tab ({r.details['tabs']})")
        bridge.tab_id = tab_b["tab_id"]
        await front(driver, pid, w.window_id)
        await asyncio.sleep(0.5)
        _Pages.store.setdefault("events", []).append(
            {"tab": "-", "kind": "case-start", "t": time.time() * 1000}
        )
        watch = Watch()
        person = Person(pid, PERSON_TEXT)
        person.start()
        await asyncio.sleep(0.3)
        nm = await step(r, "observe", bridge.observe())
        name = next(c.id for c in nm.menu.candidates if c.role in ("textbox", "searchbox"))
        t1 = await step(r, "type", bridge.act(nm, "type", name, "Ada Lovelace"))
        nm = await step(r, "observe", bridge.observe())
        go = next(c.id for c in nm.menu.candidates if c.role == "button" and "Submit" in c.label)
        t2 = await step(r, "click", bridge.act(nm, "click", go))
        person.join()
        await asyncio.sleep(0.5)
        watch.close(r, posted_keys=len(person.sent))
        s = _Pages.store
        start = next(i for i, e in enumerate(s.get("events", [])) if e.get("kind") == "case-start")
        during = s["events"][start + 1 :]
        r.details["effects"] = [
            asdict(t1) if hasattr(t1, "__dataclass_fields__") else str(t1),
            asdict(t2) if hasattr(t2, "__dataclass_fields__") else str(t2),
        ]
        r.details["events"] = during
        r.check("tab_a_was_selected", tab_a_active)
        r.check("task_end_state_exact", s.get("submits") == ["Ada Lovelace"], submits=s.get("submits"))
        r.check(
            "person_work_exact",
            s.get("a_value") == PERSON_TEXT and not person.held,
            got=s.get("a_value"),
            held=person.held,
        )
        r.check(
            "tab_a_never_hidden_or_blurred",
            not any(e["tab"] == "a" and (e.get("state") == "hidden" or e["kind"] == "blur") for e in during),
        )
        r.check("tab_b_never_shown", not any(e["tab"] == "b" and e.get("state") == "visible" for e in during))
        r.check("front_never_left_person", watch.front_pids() == {pid}, fronts=watch.fronts)
    finally:
        if driver is not None:
            try:
                await driver.shutdown()
            except Exception as exc:  # noqa: BLE001 - teardown
                r.details["shutdown_error"] = str(exc)[:120]
        subprocess.run(["pkill", "-f", f"user-data-dir={profile}"], check=False)
        srv.shutdown()
    return r


CASES = {
    "C1": case_other_app,
    "C2": case_same_process,
    "C3": case_background_tab,
    "C4": case_foreground_permitted,
    "C5": case_conflicting_edit,
}


async def run_case(key: str, work: Path | None = None) -> CaseResult:
    from cua_driver import CuaDriver

    require_idle(BETWEEN_S if work is not None else GUARD_IDLE_S)
    work = work or Path(tempfile.mkdtemp(prefix="q15-"))
    driver = CuaDriver.create()
    try:
        return await CASES[key](driver, work)
    except Exception as exc:  # noqa: BLE001 - a crashed case is a failed case with its reason
        return CaseResult(key, error=f"{type(exc).__name__}: {str(exc)[:300]}")
    finally:
        await driver.shutdown()
