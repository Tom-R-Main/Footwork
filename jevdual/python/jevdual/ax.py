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

from jevdual.coordination import checkpoint

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
    """The exact AXWindow or independently associated AXSheet with the requested CGWindowID."""
    import objc
    from ApplicationServices import AXUIElementCreateApplication

    get_window = _hi()
    app = AXUIElementCreateApplication(pid)
    windows = list(_attr(app, "AXWindows") or ())

    def number(element: Any) -> int | None:
        wid = ctypes.c_uint32(0)
        return wid.value if get_window(objc.pyobjc_id(element), ctypes.byref(wid)) == 0 else None

    for w in windows:
        if number(w) == window_id:
            return w
    from ApplicationServices import AXUIElementGetPid

    def owned(element: Any) -> bool:
        error, owner = AXUIElementGetPid(element, None)
        return error == 0 and owner == pid

    if len(windows) > 64:
        raise AXError("window_resolution_limit", "too many top-level windows for bounded modal resolution")
    roots = [window for window in windows if _attr(window, "AXRole") == "AXWindow" and owned(window)]

    def associated(sheet: Any, root: Any = None) -> bool:
        if not owned(sheet):
            return False
        declared = _attr(sheet, "AXWindow")
        node = sheet
        for _ in range(32):
            node = _attr(node, "AXParent")
            if node is None or not owned(node):
                return False
            role = _attr(node, "AXRole")
            if role == "AXWindow":
                return (any(same_element(node, known) for known in roots)
                        and (root is None or same_element(node, root))
                        and (declared is None or same_element(node, declared)))
            if role in ("AXWebArea", "AXApplication"):
                return False
        return False

    matches = []

    def retain(sheet: Any, root: Any = None) -> None:
        if (number(sheet) == window_id and associated(sheet, root)
                and not any(same_element(sheet, known) for known in matches)):
            matches.append(sheet)

    queue = [(root, root, 0) for root in roots]
    seen = 0
    while queue:
        if seen >= 512:
            raise AXError("window_resolution_limit", "modal descendant traversal exceeded its bound")
        root, node, depth = queue.pop(0)
        seen += 1
        if depth > 16:
            raise AXError("window_resolution_limit", "modal descendant depth exceeded its bound")
        if not owned(node):
            continue
        role = _attr(node, "AXRole")
        if role == "AXSheet":
            retain(node, root)
            # Do not census a Save panel's file browser. Nested direct sheets and
            # the independently associated focused sheet are sufficient candidates.
            children = _attr(node, "AXChildren") or ()
            if len(children) > 512:
                raise AXError("window_resolution_limit", "modal child enumeration exceeded its bound")
            children = [child for child in children if _attr(child, "AXRole") == "AXSheet"]
        elif role == "AXWebArea" or (role in ("AXWindow", "AXApplication") and node is not root):
            continue
        else:
            children = _attr(node, "AXChildren") or ()
        if seen + len(queue) + len(children) > 512:
            raise AXError("window_resolution_limit", "modal descendant enumeration exceeded its bound")
        queue.extend((root, child, depth + 1) for child in children)
    focused = _attr(app, "AXFocusedWindow")
    if focused is not None and _attr(focused, "AXRole") == "AXSheet":
        retain(focused)
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise AXError("window_ambiguous", f"multiple AXSheets match window {window_id}")
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


def web_area_frame(win: Any, *, depth: int = 12) -> Frame | None:
    """The frame of the first AXWebArea under ``win`` (a browser's content area), or None."""
    stack = [(win, 0)]
    while stack:
        el, d = stack.pop()
        if _attr(el, "AXRole") == "AXWebArea":
            return frame_of(el)
        if d < depth:
            stack.extend((c, d + 1) for c in reversed(_attr(el, "AXChildren") or []))
    return None


def labelled(win: Any, label: str, *, limit: int = 6000) -> list[tuple[str, str, Frame]]:
    """Elements under ``win`` whose AXDescription or AXTitle is ``label`` or starts with it, as
    ``(role, name, frame)``. Reaches containers the Driver collapses (CUA drops every AXGroup)."""
    want = label.casefold()
    hits: list[tuple[str, str, Frame]] = []
    queue, seen = [win], 0
    while queue and seen < limit:
        el = queue.pop(0)
        seen += 1
        for attr in ("AXDescription", "AXTitle"):
            name = _attr(el, attr)
            if isinstance(name, str) and name.strip() and name.casefold().startswith(want):
                frame = frame_of(el)
                if frame is not None and frame.w > 0 and frame.h > 0:
                    hits.append((str(_attr(el, "AXRole") or ""), name, frame))
                break
        queue.extend(_attr(el, "AXChildren") or [])
    return hits


def placeholder(el: Any) -> str | None:
    """The element's AXPlaceholderValue, or None."""
    v = _attr(el, "AXPlaceholderValue")
    return None if v is None else str(v)


def link_url(el: Any, *, label: str | None = None) -> str | None:
    """Read a complete HTTP(S) AXURL without display truncation or URL normalization."""
    if label is not None and not any(
        isinstance(name, str) and " ".join(name.split()) == " ".join(label.split())
        for name in (_attr(el, "AXTitle"), _attr(el, "AXDescription"))
    ):
        return None
    return _complete_http_url(_attr(el, "AXURL"))


def _complete_http_url(raw: Any) -> str | None:
    from urllib.parse import urlsplit

    if isinstance(raw, str):
        url = raw
    else:
        absolute = getattr(raw, "absoluteString", None)
        url = absolute() if callable(absolute) else None
    if (not isinstance(url, str) or not url or len(url) > 2048
            or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in url)):
        return None
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname or not parsed.netloc
                or parsed.username is not None or parsed.password is not None):
            return None
        _ = parsed.port  # validate a malformed or out-of-range port without rewriting the resource
    except ValueError:
        return None
    return url


def control_identity(el: Any, *, label: str) -> dict[str, Any] | None:
    """Exact named DOM control scoped by its closest direct AXWebArea, never a sibling/row URL."""
    if _attr(el, "AXRole") not in ("AXButton", "AXPopUpButton"):
        return None
    if not any(isinstance(name, str) and " ".join(name.split()) == " ".join(label.split())
               for name in (_attr(el, "AXTitle"), _attr(el, "AXDescription"))):
        return None
    identifier = _attr(el, "AXDOMIdentifier")
    if (not isinstance(identifier, str) or not identifier or len(identifier) > 512
            or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in identifier)):
        return None
    node = el
    for _ in range(32):
        node = _attr(node, "AXParent")
        if node is None:
            return None
        role = _attr(node, "AXRole")
        if role == "AXWebArea":
            url = _complete_http_url(_attr(node, "AXURL"))
            return {"dom_id": identifier, "document_url": url, "web_area": node} if url else None
        if role in ("AXWindow", "AXApplication"):
            return None
    return None


def exact_control_name(el: Any, *, role: str, label: str) -> bool:
    title, description = _attr(el, "AXTitle"), _attr(el, "AXDescription")
    return (_attr(el, "AXRole") == role and isinstance(title, str) and isinstance(description, str)
            and label in (title, description))


def unique_named_control(window: Any, *, pid: int, role: str, label: str, limit: int = 1024) -> Any:
    """Census-only lookup, never an action target or positional fallback.

    Traverse the entire exposed subtree, refusing unknown branches/names, traversal limits and
    multiple distinct AX objects. Unsupported/no-value attributes are known absent, not failed reads.
    """
    from ApplicationServices import (
        AXUIElementCopyAttributeValue,
        AXUIElementGetPid,
        kAXErrorAttributeUnsupported,
        kAXErrorNoValue,
    )

    if role not in ("AXButton", "AXPopUpButton") or not isinstance(label, str) or not 0 < len(label) <= 512:
        raise AXError("census_name_invalid", "census requires an exact readable supported native name")
    stack, seen, matches = [(window, 0)], [], []
    visits = 0
    while stack:
        node, depth = stack.pop()
        visits += 1
        if visits > limit or depth > 32:
            raise AXError("census_lookup_limit", "named control census exceeded its traversal bound")
        if any(same_element(node, prior) for prior in seen):
            continue
        seen.append(node)
        error, owner = AXUIElementGetPid(node, None)
        actual_role = _attr(node, "AXRole")
        if error != 0 or owner != pid or not isinstance(actual_role, str):
            raise AXError("census_unreadable", "native subtree ownership or role is unreadable")
        if actual_role == role:
            names = []
            for attribute in ("AXTitle", "AXDescription"):
                error, name = AXUIElementCopyAttributeValue(node, attribute, None)
                if error in (kAXErrorAttributeUnsupported, kAXErrorNoValue):
                    continue  # independently known absent attribute, not a failed name read
                if error != 0 or not isinstance(name, str):
                    raise AXError("census_unreadable", "a native peer name is unreadable")
                names.append(name)
            if label in names:
                matches.append(node)
        error, children = AXUIElementCopyAttributeValue(node, "AXChildren", None)
        if error in (kAXErrorAttributeUnsupported, kAXErrorNoValue):
            continue
        if error != 0 or children is None or isinstance(children, (str, bytes, dict)):
            raise AXError("census_unreadable", "a native child branch is unreadable")
        from itertools import islice

        children = list(islice(iter(children), limit + 1))
        if len(children) > limit:
            raise AXError("census_lookup_limit", "native child branch exceeded its traversal bound")
        stack.extend((child, depth + 1) for child in reversed(children))
    if len(matches) != 1:
        raise AXError("census_name_ambiguous", "exact native census name does not identify one AX object")
    return matches[0]


def control_backing(el: Any, *, pid: int, window: Any, role: str) -> dict[str, Any] | None:
    """Read an opaque control's literal backing, including known absence of a DOM ID.

    No purpose is inferred. A complete direct parent walk of at most 64 nodes must prove this
    process/window and the closest WebArea's actual document URL. Missing attributes never
    mean an empty name. Native-object equality detects cycles, including aliased AX proxies.
    """
    from ApplicationServices import AXUIElementGetPid

    if role not in ("AXButton", "AXPopUpButton") or _attr(el, "AXRole") != role:
        return None
    identifier = _attr(el, "AXDOMIdentifier")
    if (not isinstance(identifier, str) or len(identifier) > 512
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in identifier)):
        return None
    title, description = _attr(el, "AXTitle"), _attr(el, "AXDescription")
    node, web_area, url = el, None, None
    seen = []
    for _ in range(64):
        if any(same_element(node, prior) for prior in seen):
            return None
        seen.append(node)
        error, owner = AXUIElementGetPid(node, None)
        if error != 0 or owner != pid:
            return None
        role = _attr(node, "AXRole")
        if not isinstance(role, str) or not role:
            return None
        if role == "AXWebArea" and web_area is None:
            web_area, url = node, _complete_http_url(_attr(node, "AXURL"))
            if url is None:
                return None
        if same_element(node, window):
            if web_area is None or role not in ("AXWindow", "AXSheet"):
                return None
            return {"dom_id": identifier, "document_url": url, "web_area": web_area,
                    "unnamed": isinstance(title, str) and title == ""
                    and isinstance(description, str) and description == ""}
        if role in ("AXWindow", "AXSheet", "AXApplication"):
            return None
        node = _attr(node, "AXParent")
        if node is None:
            return None
    return None


def same_element(left: Any, right: Any) -> bool:
    from CoreFoundation import CFEqual

    return left is not None and right is not None and bool(CFEqual(left, right))


def semantic_section(el: Any) -> str | None:
    """Read an explicit ancestor name, including groups omitted by CUA's projection.

    This is semantic context, not a retained object identifier. Never infer a row name from
    sibling text, screen position, entered field values or the page's unstructured text.
    """
    node = el
    for _ in range(32):
        node = _attr(node, "AXParent")
        if node is None:
            return None
        role = _attr(node, "AXRole")
        if role in ("AXWindow", "AXWebArea", "AXApplication"):
            return None
        if role in ("AXRow", "AXCell", "AXOutlineRow", "AXGroup"):
            for attribute in ("AXTitle", "AXDescription"):
                name = _attr(node, attribute)
                if isinstance(name, str) and name.strip():
                    return name.strip()
    return None


def value(el: Any) -> str:
    """The element's exact AXValue. An empty text view reports none at all (Notes' new note body,
    2026-09-25); it is the empty string only when the element says it holds no characters."""
    v = _attr(el, "AXValue")
    if v is None:
        if _attr(el, "AXNumberOfCharacters") == 0:
            return ""
        raise AXError("no_value", "element has no readable AXValue")
    return str(v)


def can_insert(el: Any) -> bool:
    """Read-only qualification for the caret-and-insert route used by ``insert_at_end``.

    A text-area role or readable value alone does not establish editability.
    Unknown/refused setter capability is not permission to attempt input.
    """
    from ApplicationServices import AXUIElementIsAttributeSettable

    for name in ("AXSelectedTextRange", "AXSelectedText"):
        err, settable = AXUIElementIsAttributeSettable(el, name, None)
        if err or not settable:
            return False
    return True


def selected_range(el: Any) -> tuple[int, int]:
    """Read the field's current UTF-16 selection; no selection is inferred from a key receipt."""
    from ApplicationServices import AXValueGetValue, kAXValueCFRangeType

    raw = _attr(el, "AXSelectedTextRange")
    if raw is None:
        raise AXError("selection_unreadable", "the field's selected range is unavailable")
    ok, value = AXValueGetValue(raw, kAXValueCFRangeType, None)
    if isinstance(value, tuple) and len(value) == 2:
        location, length = value
    else:
        location, length = getattr(value, "location", None), getattr(value, "length", None)
    if not ok or type(location) is not int or type(length) is not int or location < 0 or length < 0:
        raise AXError("selection_unreadable", "the field's selected range cannot be qualified")
    return location, length


def selected_text(el: Any) -> str:
    """The independent exact AXSelectedText, including an explicitly empty selection."""
    text = _attr(el, "AXSelectedText")
    if not isinstance(text, str):
        raise AXError("selection_unreadable", "the field's selected text is unavailable")
    return text


def focus_text_field_ack(el: Any) -> None:
    """One explicit AXFocused preparation write; acknowledgement alone does not prove focus."""
    from ApplicationServices import AXUIElementSetAttributeValue

    error = AXUIElementSetAttributeValue(el, "AXFocused", True)
    if error:
        raise AXError("focus_refused", f"AXFocused did not acknowledge the write ({error})")


def focused_element_matches(pid: int, window_id: int, el: Any) -> bool:
    """Independent application focused-element equality and exact key-window identity."""
    from ApplicationServices import AXUIElementCreateApplication

    if focused_window_id(pid) != window_id:
        return False
    focused = _attr(AXUIElementCreateApplication(pid), "AXFocusedUIElement")
    return same_element(focused, el)


def can_set_value(el: Any) -> bool:
    from ApplicationServices import AXUIElementIsAttributeSettable

    err, writable = AXUIElementIsAttributeSettable(el, "AXValue", None)
    return err == 0 and bool(writable)


def set_value_ack(el: Any, text: str) -> None:
    """One AXValue setter. A returned acknowledgement counts one accepted AX input."""
    from ApplicationServices import AXUIElementSetAttributeValue

    checkpoint()
    err = AXUIElementSetAttributeValue(el, "AXValue", text)
    if err:
        raise AXError("value_write_uncertain", f"AXValue did not acknowledge the write ({err})")


def finder_row(el: Any) -> Any:
    """Find the filename's own row through its short, exact AX ancestry."""
    node = el
    for _ in range(5):
        if _attr(node, "AXRole") == "AXRow":
            return node
        node = _attr(node, "AXParent")
        if node is None:
            break
    raise AXError("file_row_missing", "filename has no exact Finder row")


def select_finder_row_ack(el: Any) -> None:
    from ApplicationServices import AXUIElementIsAttributeSettable, AXUIElementSetAttributeValue

    row = finder_row(el)
    err, writable = AXUIElementIsAttributeSettable(row, "AXSelected", None)
    if err or not writable:
        raise AXError("file_row_not_selectable", "Finder row selection is unavailable")
    checkpoint()
    err = AXUIElementSetAttributeValue(row, "AXSelected", True)
    if err:
        raise AXError("file_selection_uncertain", f"Finder row selection was not acknowledged ({err})")
    if not _attr(row, "AXSelected"):
        raise AXError("file_selection_unverified", "Finder did not report the exact row selected")


def focused_finder_editor(pid: int, window_id: int, frame: Frame, expect: str) -> Any:
    """Bind Finder's transient rename editor when AXWindow is absent.

    Finder publishes that editor directly under AXApplication. Its main window,
    exact focused value and overlapping filename frame jointly qualify this case.
    This exception is not used for arbitrary text fields or other apps.
    """
    import objc
    from ApplicationServices import AXUIElementCreateApplication

    app = AXUIElementCreateApplication(pid)
    if _attr(app, "AXTitle") not in ("Finder", None):
        raise AXError("file_editor_wrong_app", "the transient editor does not belong to Finder")
    element = _attr(app, "AXFocusedUIElement")
    if element is None or _attr(element, "AXRole") != "AXTextField" or value(element) != expect:
        raise AXError("file_editor_missing", "the focused Finder editor does not hold the expected name")
    window = _attr(element, "AXWindow") or _attr(app, "AXMainWindow")
    wid = ctypes.c_uint32(0)
    if window is None or _hi()(objc.pyobjc_id(window), ctypes.byref(wid)) != 0 or wid.value != window_id:
        raise AXError("file_editor_wrong_window", "Finder's main window differs from the bound window")
    actual = frame_of(element)
    if actual is None or not (
        frame.x - _FRAME_TOL <= actual.x + actual.w / 2 <= frame.x + frame.w + _FRAME_TOL
        and frame.y - _FRAME_TOL <= actual.y + actual.h / 2 <= frame.y + frame.h + _FRAME_TOL
    ):
        raise AXError(
            "file_editor_wrong_frame", "the focused editor does not overlap the exact filename field"
        )
    return element


def finder_completion_editor(pid: int, window_id: int, expect: str) -> Any:
    """Authorize reactivation of an owned Finder window from its current editor.

    Finder may replace the rename editor after Return and omit its AXWindow.
    This read establishes only window ownership; file input still requires the
    normal filename AXURL/inode target after the window is reacquired.
    """
    import objc
    from ApplicationServices import AXUIElementCreateApplication

    from jevdual.finder_targets import _attribute_names, _read_attribute

    app = AXUIElementCreateApplication(pid)
    if _attr(app, "AXTitle") != "Finder":
        raise AXError("file_editor_wrong_app", "the completion editor does not belong to Finder")
    element = _attr(app, "AXFocusedUIElement")
    if element is None or _attr(element, "AXRole") != "AXTextField" or value(element) != expect:
        raise AXError("file_editor_missing", "the current completion editor does not hold the new name")
    main = _attr(app, "AXMainWindow")
    explicit = _read_attribute(element, _attribute_names(element), "AXWindow", optional=True)
    for window in (main, explicit) if explicit is not None else (main,):
        wid = ctypes.c_uint32(0)
        if window is None or _hi()(objc.pyobjc_id(window), ctypes.byref(wid)) != 0 or wid.value != window_id:
            raise AXError("file_editor_wrong_window", "the current completion editor names another window")
    return element


def finder_selection_state(el: Any) -> dict[str, Any]:
    row = finder_row(el)
    outline = _attr(row, "AXParent")
    rows = _attr(outline, "AXSelectedRows") if outline is not None else None
    return {
        "exact_row_selected": bool(_attr(row, "AXSelected")),
        "selected_row_count": len(rows) if rows is not None else None,
        "exact_row_only": len(rows) == 1 and rows[0] == row if rows is not None else False,
    }


def finder_window_context(pid: int) -> dict[str, Any]:
    import objc
    from ApplicationServices import AXUIElementCreateApplication

    app = AXUIElementCreateApplication(pid)
    result = {}
    for attribute, key in (("AXMainWindow", "main_window_id"), ("AXFocusedWindow", "focused_window_id")):
        element = _attr(app, attribute)
        wid = ctypes.c_uint32(0)
        result[key] = (
            wid.value
            if element is not None and _hi()(objc.pyobjc_id(element), ctypes.byref(wid)) == 0
            else None
        )
    focused = _attr(app, "AXFocusedUIElement")
    result["focused_role"] = str(_attr(focused, "AXRole")) if focused is not None else None
    return result


def pasteboard_change_count() -> int:
    """Clipboard generation only; never reads the person's prior clipboard content."""
    from AppKit import NSPasteboard

    count = NSPasteboard.generalPasteboard().changeCount()
    if type(count) is not int or count < 0:
        raise AXError("file_clipboard_unavailable", "clipboard generation is unavailable")
    return count


def pasteboard_file_paths() -> list[str]:
    """Read file URLs only after the caller's acknowledged Copy changed the clipboard.

    Callers retain values only when they equal their exact owned source. Other
    representations, clipboard types and the previous content are not inspected.
    """
    from AppKit import NSPasteboard, NSPasteboardURLReadingFileURLsOnlyKey
    from Foundation import NSURL

    board = NSPasteboard.generalPasteboard()
    urls = board.readObjectsForClasses_options_([NSURL], {NSPasteboardURLReadingFileURLsOnlyKey: True})
    if urls is None or len(urls) > 16:
        raise AXError("file_clipboard_unavailable", "bounded copied file URLs are unavailable")
    paths = []
    for url in urls:
        if not url.isFileURL() or url.host() not in (None, "", "localhost"):
            raise AXError("file_clipboard_unavailable", "copied resource is not a local file")
        concrete = url.filePathURL()
        if concrete is None or concrete.path() is None:
            raise AXError("file_clipboard_unavailable", "copied file URL could not be resolved")
        paths.append(str(concrete.path()))
    return paths


def document_path(pid: int, window_id: int) -> str | None:
    """The file a document window shows (its AXDocument URL as a path), or None when it names none."""
    from urllib.parse import unquote, urlsplit

    doc = _attr(window_element(pid, window_id), "AXDocument")
    if not doc:
        return None
    parts = urlsplit(str(doc))
    return unquote(parts.path) if parts.scheme == "file" else None


def preview_document_state(pid: int, window_id: int) -> dict[str, Any]:
    """Bounded Preview UI state; disk identity binds the named document, not its pixels."""
    import hashlib
    import os
    import stat

    window = window_element(pid, window_id)
    path = document_path(pid, window_id)
    edited = _attr(window, "AXEdited")
    if not path:
        raise AXError("document_state_missing", "document path unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        identity = os.fstat(fd)
        if not stat.S_ISREG(identity.st_mode) or identity.st_size > 64 * 1024 * 1024:
            raise AXError("document_state_missing", "the document is not a bounded regular file")
        digest = hashlib.sha256()
        while data := os.read(fd, 65536):
            digest.update(data)
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        stamp = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if stamp(identity) != stamp(after) or stamp(identity) != stamp(current):
            raise AXError("document_state_changed", "the document changed while being observed")
    finally:
        os.close(fd)
    return {
        "pid": pid,
        "window_id": window_id,
        "document": path,
        "identity": {"device": identity.st_dev, "inode": identity.st_ino},
        "sha256": digest.hexdigest(),
        "edited": bool(edited) if isinstance(edited, (bool, int)) and edited in (0, 1) else None,
        "undo": [p.split(" > ", 1)[1] for p in menu_paths(pid) if p.startswith("Edit > Undo ")],
    }


def text_area_values(pid: int, window_id: int) -> list[str]:
    """The exact values of the window's text areas, in tree order."""
    out = []
    for el in elements_by_role(window_element(pid, window_id), "AXTextArea"):
        try:
            out.append(value(el))
        except AXError:
            continue
    return out


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
    checkpoint()
    err = AXUIElementSetAttributeValue(el, "AXSelectedTextRange", rng)
    if err != 0:
        raise AXError("selection_refused", f"AXSelectedTextRange write refused ({err})")
    checkpoint()
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


def title_bar_point(pid: int, window_id: int) -> tuple[float, float] | None:
    """A point on the bound window's title bar, left of the title (clicking a document's title can open
    its rename popover) and right of the window buttons, or None when a hit test there does not land on
    that window (another window covers it, or it has no frame)."""
    import objc
    from ApplicationServices import AXUIElementCopyElementAtPosition, AXUIElementCreateSystemWide

    f = frame_of(window_element(pid, window_id))
    if f is None or f.w < 120:
        return None
    x, y = f.x + min(90.0, f.w / 4), f.y + 12
    err, hit = AXUIElementCopyElementAtPosition(AXUIElementCreateSystemWide(), x, y, None)
    win = _attr(hit, "AXWindow") if err == 0 and hit is not None else None
    if win is None and err == 0 and _attr(hit, "AXRole") == "AXWindow":
        win = hit
    wid = ctypes.c_uint32(0)
    if win is None or _hi()(objc.pyobjc_id(win), ctypes.byref(wid)) != 0 or wid.value != window_id:
        return None
    return x, y


def click_at(x: float, y: float, *, trace: Any = None) -> None:
    """One real left click at a screen point, the cursor put back where it was: the one input TextEdit
    takes to change its key window (Q19 U48: AX raises, the Window menu and AppleScript reorder its
    windows but leave the previous one key)."""
    import time

    from Quartz import (
        CGEventCreate,
        CGEventCreateMouseEvent,
        CGEventGetLocation,
        CGEventPost,
        CGWarpMouseCursorPosition,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGHIDEventTap,
        kCGMouseButtonLeft,
    )

    checkpoint()
    back = CGEventGetLocation(CGEventCreate(None))
    for kind in (kCGEventLeftMouseDown, kCGEventLeftMouseUp):
        event = CGEventCreateMouseEvent(None, kind, (x, y), kCGMouseButtonLeft)
        if trace is None:
            CGEventPost(kCGHIDEventTap, event)
        else:
            trace.post("down" if kind == kCGEventLeftMouseDown else "up", x, y,
                       lambda event=event: CGEventPost(kCGHIDEventTap, event))
        time.sleep(0.03)
    if trace is None:
        CGWarpMouseCursorPosition(back)
    else:
        trace.post("warp", back.x, back.y, lambda: CGWarpMouseCursorPosition(back))


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


def menu_paths(pid: int, *, limit: int = 400) -> list[str]:
    """Every menu item under the app's menu bar as a path ("File > Save"), two levels deep, read through AX
    (the observation's element cap dropped them all on Dictionary, Q19 frozen re-drive)."""
    from ApplicationServices import AXUIElementCreateApplication

    bar = _attr(AXUIElementCreateApplication(pid), "AXMenuBar")
    out: list[str] = []
    for top in _menu_items(bar) if bar is not None else []:
        head = str(_attr(top, "AXTitle") or "").strip()
        if not head or head == "Apple":
            continue
        for item in _menu_items(top):
            title = str(_attr(item, "AXTitle") or "").strip()
            if title:
                out.append(f"{head} > {title}")
            if len(out) >= limit:
                return out
    return out


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
    # AXEnabled is not checked first: a menu item's enabled state is validated when its menu opens, so it
    # can read False for an item that works (Q15 smoke 6: Edit > Select All); the press reports a refusal
    checkpoint()
    err = AXUIElementPerformAction(node, "AXPress")
    if err != 0:
        raise AXError("press_refused", f"AXPress on {' > '.join(path)} refused ({err})")


def menu_item_enabled(pid: int, path: list[str]) -> bool:
    """Read the exact menu item's validated enabled state after opening its menu."""
    from ApplicationServices import AXUIElementCreateApplication

    node = _attr(AXUIElementCreateApplication(pid), "AXMenuBar")
    if node is None:
        raise AXError("menu_missing", "the application menu bar is unavailable")
    for name in path:
        want = name.strip().removesuffix("…").removesuffix("...").strip().casefold()
        hits = [item for item in _menu_items(node) if _title(item) == want]
        if len(hits) != 1:
            raise AXError(
                "menu_missing" if not hits else "menu_ambiguous", "the exact menu item is unavailable"
            )
        node = hits[0]
    enabled = _attr(node, "AXEnabled")
    return isinstance(enabled, (bool, int)) and enabled == 1


def raise_window(pid: int, window_id: int) -> None:
    """Make the bound window its app's main and key window through AX (``AXMain``, ``AXRaise``). It does
    not activate the app; with ``posture.activate`` it replaces the Driver's ``bring_to_front``, which
    took 1.2 s to return while our window already held the front (2026-09-25)."""
    from ApplicationServices import AXUIElementPerformAction, AXUIElementSetAttributeValue

    w = window_element(pid, window_id)
    if _attr(w, "AXRole") == "AXSheet":
        if focused_window_id(pid) == window_id:
            return  # SDK foreground intent already established this exact modal as key.
        raise AXError("sheet_not_key", f"requested modal {window_id} is not the exact key window; not raised")
    checkpoint()
    AXUIElementSetAttributeValue(w, "AXMain", True)
    checkpoint()
    err = AXUIElementPerformAction(w, "AXRaise")
    if err != 0:
        raise AXError("raise_refused", f"AXRaise on window {window_id} refused ({err})")
