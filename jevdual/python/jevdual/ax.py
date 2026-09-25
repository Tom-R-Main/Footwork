"""Direct macOS accessibility for what the Driver does not give exactly: a text element's value and an
insertion at its end.

Measured 2026-09-25 on TextEdit: the Driver's ``get_window_state`` reports a text area's value with its
trailing whitespace stripped (the file ``'a\\n\\tb  \\n\\n  '`` came back ``'a\\n\\tb'``), while the element's
own AXValue is exact. A whole-field write built from the Driver's value would delete that whitespace, and
one built from the model-facing preview (capped at 480 characters, indentation collapsed) destroyed the
document. So the append route never rebuilds the field: it places the caret at the end of the exact value
and inserts, both as AX attribute writes that neither raise the window nor move the pointer, then reads the
value back and requires ``after == before + inserted``.

The window is resolved by the same CGWindowID the Driver binds (``_AXUIElementGetWindow``, the private but
stable HIServices call every window-level AX tool uses), and the element by role and frame.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from typing import Any

_FRAME_TOL = 3.0


class AXError(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def _hi() -> Any:
    lib = ctypes.cdll.LoadLibrary(
        "/System/Library/Frameworks/ApplicationServices.framework/Frameworks/HIServices.framework/HIServices"
    )
    fn = lib._AXUIElementGetWindow
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    fn.restype = ctypes.c_int32
    return fn


def _attr(el: Any, name: str) -> Any:
    from ApplicationServices import AXUIElementCopyAttributeValue

    err, val = AXUIElementCopyAttributeValue(el, name, None)
    return val if err == 0 else None


def window_element(pid: int, window_id: int) -> Any:
    """The AX window of ``pid`` whose CGWindowID is ``window_id``."""
    import objc
    from ApplicationServices import AXUIElementCreateApplication

    get_window = _hi()
    app = AXUIElementCreateApplication(pid)
    for w in _attr(app, "AXWindows") or ():
        wid = ctypes.c_uint32(0)
        if get_window(objc.pyobjc_id(w), ctypes.byref(wid)) == 0 and wid.value == window_id:
            return w
    raise AXError("window_missing", f"pid {pid} has no AX window {window_id}")


@dataclass(frozen=True)
class Frame:
    x: float
    y: float
    w: float
    h: float

    def near(self, other: Frame) -> bool:
        return all(
            abs(a - b) <= _FRAME_TOL
            for a, b in ((self.x, other.x), (self.y, other.y), (self.w, other.w), (self.h, other.h))
        )


def frame_of(el: Any) -> Frame | None:
    from ApplicationServices import AXValueGetValue, kAXValueCGPointType, kAXValueCGSizeType

    pos, size = _attr(el, "AXPosition"), _attr(el, "AXSize")
    if pos is None or size is None:
        return None
    ok_p, p = AXValueGetValue(pos, kAXValueCGPointType, None)
    ok_s, s = AXValueGetValue(size, kAXValueCGSizeType, None)
    if not (ok_p and ok_s):
        return None
    return Frame(float(p.x), float(p.y), float(s.width), float(s.height))


def elements_by_role(root: Any, role: str, *, limit: int = 4000) -> list[Any]:
    out: list[Any] = []
    stack = [root]
    seen = 0
    while stack and seen < limit:
        el = stack.pop()
        seen += 1
        if _attr(el, "AXRole") == role:
            out.append(el)
        stack.extend(reversed(list(_attr(el, "AXChildren") or ())))
    return out


def resolve(pid: int, window_id: int, role: str, frame: Frame | None) -> Any:
    """The one element of ``role`` in the window: the only one of that role, or among several the one at
    ``frame`` (screen points, the Driver's element frame). Ambiguity is refused, never guessed."""
    win = window_element(pid, window_id)
    cands = elements_by_role(win, role)
    hits = cands
    if frame is not None and len(cands) > 1:
        hits = [e for e in cands if (f := frame_of(e)) is not None and f.near(frame)]
    if len(hits) != 1:
        raise AXError(
            "element_ambiguous" if hits else "element_missing",
            f"{len(hits)} {role} elements match in window {window_id}"
            + (f" at {frame}" if frame is not None else ""),
        )
    return hits[0]


def value(el: Any) -> str:
    """The element's exact AXValue. An empty text view reports none at all (Notes' new note body,
    2026-09-25); it is the empty string only when the element says it holds no characters."""
    v = _attr(el, "AXValue")
    if v is None:
        if _attr(el, "AXNumberOfCharacters") == 0:
            return ""
        raise AXError("no_value", "element has no readable AXValue")
    return str(v)


def utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def insert_at_end(el: Any, text: str, *, expect: str | None = None) -> tuple[str, str]:
    """Place the caret at the end of ``el``'s exact value and insert ``text`` there. Returns ``(before,
    after)``; the caller decides whether ``after == before + text``. With ``expect``, a value that differs
    from it is refused before anything is written (``precondition_changed``)."""
    from ApplicationServices import AXUIElementSetAttributeValue, AXValueCreate, kAXValueCFRangeType
    from Foundation import NSMakeRange

    before = value(el)
    if expect is not None and before != expect:
        raise AXError("precondition_changed", "the field changed between the read and the insertion")
    rng = AXValueCreate(kAXValueCFRangeType, NSMakeRange(utf16_len(before), 0))
    err = AXUIElementSetAttributeValue(el, "AXSelectedTextRange", rng)
    if err != 0:
        raise AXError("selection_refused", f"AXSelectedTextRange write refused ({err})")
    err = AXUIElementSetAttributeValue(el, "AXSelectedText", text)
    if err != 0:
        raise AXError("insert_refused", f"AXSelectedText write refused ({err})")
    return before, value(el)


def focused_window_id(pid: int) -> int | None:
    """CGWindowID of the process's focused (key) window, or None."""
    import objc
    from ApplicationServices import AXUIElementCreateApplication

    w = _attr(AXUIElementCreateApplication(pid), "AXFocusedWindow")
    if w is None:
        return None
    wid = ctypes.c_uint32(0)
    return wid.value if _hi()(objc.pyobjc_id(w), ctypes.byref(wid)) == 0 else None


def _title(el: Any) -> str:
    t = str(_attr(el, "AXTitle") or "").strip()
    return t.removesuffix("…").removesuffix("...").strip().casefold()


def _menu_items(node: Any) -> list[Any]:
    role = _attr(node, "AXRole")
    kids = list(_attr(node, "AXChildren") or ())
    if role in ("AXMenuBar", "AXMenu"):
        return kids
    sub = next((k for k in kids if _attr(k, "AXRole") == "AXMenu"), None)
    return list(_attr(sub, "AXChildren") or ()) if sub is not None else []


def press_menu(pid: int, path: list[str]) -> None:
    """Press an application menu item by its path through AX. It acts on the app's key window and does
    nothing while the app is inactive (measured on TextEdit, 2026-09-25: the press returned success and
    selected nothing in the background, and selected all with the window in front), and it never
    activates the app itself, unlike the Driver's invoke_menu, which took the front back from a person
    who had moved away during the step."""
    from ApplicationServices import AXUIElementCreateApplication, AXUIElementPerformAction

    node = _attr(AXUIElementCreateApplication(pid), "AXMenuBar")
    if node is None:
        raise AXError("menu_missing", f"pid {pid} has no menu bar")
    for depth, name in enumerate(path):
        want = name.strip().removesuffix("…").removesuffix("...").strip().casefold()
        hits = [i for i in _menu_items(node) if _title(i) == want]
        if len(hits) != 1:
            raise AXError(
                "menu_missing" if not hits else "menu_ambiguous",
                f"{len(hits)} menu items titled {name!r} under {' > '.join(path[:depth]) or 'the menu bar'}",
            )
        node = hits[0]
    if _attr(node, "AXEnabled") is False:
        raise AXError("menu_disabled", f"{' > '.join(path)} is disabled")
    err = AXUIElementPerformAction(node, "AXPress")
    if err != 0:
        raise AXError("press_refused", f"AXPress on {' > '.join(path)} refused ({err})")
