"""Bounded exact text through AT-SPI, qualified against an X11 client window.

This adapter never focuses a widget or substitutes a keyboard/clipboard write.
An AT-SPI object path is retained with its unique bus owner and ancestry; stale
objects are refused rather than found again by ordinal. No document-path claim
is derived from a window title. Wayland window qualification is not provided.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from jevdual.ax import AXError, Frame

__all__ = ["AXError", "Frame", "can_insert", "can_set_value", "document_path", "frame_of",
           "insert_at_end", "resolve", "set_value_ack", "text_capabilities", "value"]

_ACCESSIBLE = "org.a11y.atspi.Accessible"
_TEXT = "org.a11y.atspi.Text"
_EDITABLE = "org.a11y.atspi.EditableText"
_COMPONENT = "org.a11y.atspi.Component"
_PROPERTIES = "org.freedesktop.DBus.Properties"
_DBUS = ("org.freedesktop.DBus", "/org/freedesktop/DBus")
_ROOT = ("org.a11y.atspi.Registry", "/org/a11y/atspi/accessible/root")
_MAX_TEXT = 65536
_MAX_NODES = 2048
_MAX_DEPTH = 64
_TIMEOUT = 2.0
_DEADLINE = 12.0


@dataclass(frozen=True)
class WindowGeometry:
    client: Frame
    decorated: Frame | None = None


def _process_start(pid: int) -> str:
    import psutil

    try:
        return psutil.Process(pid).create_time().hex()
    except (psutil.Error, OSError) as exc:
        raise AXError("lost_identity", "the original process is unavailable") from exc


def _x11_window(pid: int, window_id: int) -> WindowGeometry:
    """Isolate Xlib's global handlers and blocking socket I/O from the host driver."""
    if type(pid) is not int or type(window_id) is not int or not 0 < window_id < 2**32 or pid <= 0:
        raise AXError("window_missing", "invalid process or X11 window identity")
    environment = {name: os.environ[name] for name in ("DISPLAY", "HOME", "XAUTHORITY") if name in os.environ}
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).with_name("linux_x11.py")), str(pid), str(window_id)],
            env=environment, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=3, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AXError("x11_timeout", "the isolated X11 query exceeded three seconds") from exc
    except (OSError, UnicodeError) as exc:
        raise AXError("x11_unavailable", "the isolated X11 query could not run") from exc
    try:
        if len(result.stdout) > 4096:
            raise ValueError("oversized reply")
        report = json.loads(result.stdout)
        if not isinstance(report, dict) or type(report.get("schema_version")) is not int or report["schema_version"] != 1:
            raise ValueError("invalid reply schema")
        if result.returncode != 0:
            error = report.get("error", {})
            code = error.get("code") if isinstance(error, dict) else None
            if code in {"window_missing", "lost_identity", "x11_unavailable", "geometry_unavailable"}:
                raise AXError(code, "the isolated X11 query refused the original window")
            raise ValueError("failed helper")
        if set(report) != {"schema_version", "client", "frame_extents"}:
            raise ValueError("invalid reply fields")
        client = report["client"]
        if (not isinstance(client, list) or len(client) != 4 or any(type(n) is not int for n in client)
                or not all(-2**31 <= n < 2**31 for n in client[:2])
                or not all(0 < n < 2**31 for n in client[2:])):
            raise ValueError("invalid client geometry")
        extents = report["frame_extents"]
        if extents is not None and not isinstance(extents, list):
            raise ValueError("invalid extents")
        return _window_geometry(Frame(*client), tuple(extents) if extents is not None else None)
    except (ValueError, TypeError) as exc:
        raise AXError("geometry_unavailable", "the isolated X11 reply is invalid or incomplete") from exc


def _window_geometry(client: Frame, extents: tuple[int, ...] | None) -> WindowGeometry:
    if extents is None:
        return WindowGeometry(client)
    if len(extents) != 4 or any(type(n) is not int or not 0 <= n <= 65536 for n in extents):
        raise AXError("geometry_unavailable", "the X11 frame extents are malformed or exceed the bound")
    left, right, top, bottom = extents
    return WindowGeometry(client, Frame(client.x - left, client.y - top,
                                        client.w + left + right, client.h + top + bottom))


class _Bus:
    def __init__(self) -> None:
        self.connection = None
        self.deadline = time.monotonic() + _DEADLINE

    def __enter__(self) -> Self:
        try:
            from jeepney.io.blocking import open_dbus_connection

            with open_dbus_connection(bus="SESSION", auth_timeout=_TIMEOUT) as session:
                address = self._call(session, ("org.a11y.Bus", "/org/a11y/bus"),
                                     "org.a11y.Bus", "GetAddress")[0]
            if not isinstance(address, str) or not address.startswith("unix:") or len(address) > 4096:
                raise AXError("accessibility_unavailable", "a local accessibility bus is required")
            self.connection = open_dbus_connection(bus=address, auth_timeout=_TIMEOUT)
            self.identity = self.call(_DBUS, "org.freedesktop.DBus", "GetId")[0]
            if not isinstance(self.identity, str) or not self.identity or len(self.identity) > 128:
                raise AXError("lost_identity", "the accessibility bus identity is unavailable")
            return self
        except Exception as exc:
            self.__exit__(None, None, None)
            if isinstance(exc, AXError):
                raise
            raise AXError("accessibility_unavailable", "the accessibility bus could not be opened") from exc

    def __exit__(self, *_args: object) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _call(self, connection: Any, ref: tuple[str, str], interface: str, method: str,
              signature: str = "", body: tuple = ()) -> tuple:
        from jeepney import DBusAddress, new_method_call
        from jeepney.wrappers import unwrap_msg

        timeout = min(_TIMEOUT, self.deadline - time.monotonic())
        if timeout <= 0:
            raise AXError("accessibility_timeout", "the bounded accessibility operation expired")
        try:
            message = new_method_call(DBusAddress(ref[1], bus_name=ref[0], interface=interface),
                                      method, signature=signature, body=body)
            reply = unwrap_msg(connection.send_and_get_reply(message, timeout=timeout))
            if not isinstance(reply, tuple) or not reply:
                raise AXError("invalid_reply", "the accessibility method reply is malformed")
            return reply
        except Exception as exc:
            raise AXError("accessibility_reply_unavailable", "the accessibility reply is unavailable") from exc

    def call(self, ref: tuple[str, str], interface: str, method: str,
             signature: str = "", body: tuple = ()) -> tuple:
        return self._call(self.connection, ref, interface, method, signature, body)

    def prop(self, ref: tuple[str, str], interface: str, name: str) -> Any:
        reply = self.call(ref, _PROPERTIES, "Get", "ss", (interface, name))
        if len(reply) != 1 or not isinstance(reply[0], tuple) or len(reply[0]) != 2:
            raise AXError("invalid_reply", "the accessibility property reply is malformed")
        return reply[0][1]

    def unique(self, ref: Any, pid: int | None = None) -> tuple[str, str]:
        if (not isinstance(ref, (tuple, list)) or len(ref) != 2
                or not all(isinstance(value, str) for value in ref)
                or not ref[0] or not ref[1].startswith("/") or len(ref[1]) > 2048):
            raise AXError("lost_identity", "invalid accessibility object reference")
        owner = self.call(_DBUS, "org.freedesktop.DBus", "GetNameOwner", "s", (ref[0],))[0]
        if not isinstance(owner, str) or not owner.startswith(":"):
            raise AXError("lost_identity", "the accessibility object has no unique bus owner")
        if pid is not None:
            actual = self.call(_DBUS, "org.freedesktop.DBus", "GetConnectionUnixProcessID", "s", (owner,))[0]
            if actual != pid:
                raise AXError("lost_identity", "the accessibility object belongs to another process")
        return owner, ref[1]

    def children(self, ref: tuple[str, str]) -> list:
        count = self.prop(ref, _ACCESSIBLE, "ChildCount")
        if type(count) is not int or not 0 <= count <= _MAX_NODES:
            raise AXError("observation_incomplete", "the accessibility child count exceeds the bound")
        children = self.call(ref, _ACCESSIBLE, "GetChildren")[0] if count else []
        if not isinstance(children, (tuple, list)) or len(children) != count:
            raise AXError("observation_incomplete", "the accessibility children changed during observation")
        return list(children)


def _frame(bus: _Bus, ref: tuple[str, str]) -> Frame:
    result = bus.call(ref, _COMPONENT, "GetExtents", "u", (0,))
    coordinates = result[0] if len(result) == 1 and isinstance(result[0], (tuple, list)) else result
    if (not isinstance(coordinates, (tuple, list)) or len(coordinates) != 4
            or any(type(n) is not int for n in coordinates)
            or coordinates[2] <= 0 or coordinates[3] <= 0):
        raise AXError("geometry_unavailable", "complete accessible screen geometry is required")
    return Frame(*coordinates)


def _role(bus: _Bus, ref: tuple[str, str]) -> str:
    value = bus.call(ref, _ACCESSIBLE, "GetRoleName")[0]
    if not isinstance(value, str) or not value or len(value) > 128:
        raise AXError("invalid_reply", "the accessibility role is unavailable")
    return value.casefold()


def _state(bus: _Bus, ref: tuple[str, str]) -> int:
    words = bus.call(ref, _ACCESSIBLE, "GetState")[0]
    if (not isinstance(words, (tuple, list)) or len(words) != 2
            or any(type(n) is not int or not 0 <= n < 2**32 for n in words)):
        raise AXError("invalid_reply", "the accessibility state is unavailable")
    state = words[0] | (words[1] << 32)
    if state & ((1 << 6) | (1 << 27)):
        raise AXError("lost_identity", "the accessibility object is defunct or stale")
    return state


@dataclass(frozen=True)
class Element:
    pid: int
    window_id: int
    process_start: str
    bus_identity: str
    chain: tuple[tuple[str, str], ...]
    role: str
    frame: Frame
    window_frame: Frame
    window_geometry: WindowGeometry

    @property
    def ref(self) -> tuple[str, str]:
        return self.chain[-1]


def _validate(bus: _Bus, element: Element) -> None:
    if bus.identity != element.bus_identity or _process_start(element.pid) != element.process_start:
        raise AXError("lost_identity", "the original process or accessibility bus changed")
    if _x11_window(element.pid, element.window_id) != element.window_geometry:
        raise AXError("lost_identity", "the original X11 window geometry changed")
    for index, ref in enumerate(element.chain):
        if bus.unique(ref, element.pid) != ref:
            raise AXError("lost_identity", "the accessibility owner changed")
        _state(bus, ref)
        if index:
            parent = bus.unique(bus.prop(ref, _ACCESSIBLE, "Parent"), element.pid)
            if parent != element.chain[index - 1]:
                raise AXError("lost_identity", "the original accessible ancestry changed")
            children = [bus.unique(child, element.pid) for child in bus.children(parent)]
            if children.count(ref) != 1:
                raise AXError("lost_identity", "the original object is no longer a unique child of its parent")
    if _window_ref(bus, element.chain[0], element.pid, element.window_geometry) != element.chain[1]:
        raise AXError("lost_identity", "the accessible no longer uniquely matches the X11 client window")
    if _frame(bus, element.chain[1]) != element.window_frame:
        raise AXError("lost_identity", "the bound accessible top-level geometry changed")
    if _role(bus, element.ref) != element.role or _frame(bus, element.ref) != element.frame:
        raise AXError("lost_identity", "the original accessible role or frame changed")


@contextmanager
def _bound(element: Element):
    with _Bus() as bus:
        _validate(bus, element)
        yield bus


def _window_ref(bus: _Bus, app: tuple[str, str], pid: int, geometry: WindowGeometry) -> tuple[str, str]:
    windows = []
    for item in bus.children(app):
        ref = bus.unique(item, pid)
        actual = _frame(bus, ref)
        if actual == geometry.client or (geometry.decorated is not None and actual == geometry.decorated):
            windows.append(ref)
    if len(windows) != 1:
        raise AXError("window_ambiguous", "one accessible top-level must match the X11 client geometry")
    return windows[0]


def resolve(pid: int, window_id: int, role: str, frame: Frame | None) -> Element:
    if not isinstance(role, str) or not role or len(role) > 128:
        raise AXError("element_missing", "an exact accessibility role is required")
    start = _process_start(pid)
    geometry = _x11_window(pid, window_id)
    with _Bus() as bus:
        apps = []
        registry = bus.unique(_ROOT)
        for item in bus.children(registry):
            ref = bus.unique(item)
            actual = bus.call(_DBUS, "org.freedesktop.DBus", "GetConnectionUnixProcessID", "s", (ref[0],))[0]
            if actual == pid:
                apps.append(ref)
        if len(apps) != 1:
            raise AXError("element_ambiguous", "one accessibility application for the original process is required")
        app = apps[0]
        window = _window_ref(bus, app, pid, geometry)
        window_frame = _frame(bus, window)
        stack = [(window, (app, window))]
        seen, hits = set(), []
        while stack:
            ref, chain = stack.pop()
            if ref in seen or len(chain) > _MAX_DEPTH or len(seen) >= _MAX_NODES:
                raise AXError("observation_incomplete", "the accessibility tree is cyclic or exceeds the bound")
            seen.add(ref)
            _state(bus, ref)
            if _role(bus, ref) == role.casefold():
                actual_frame = _frame(bus, ref)
                if frame is None or actual_frame.near(frame):
                    hits.append(Element(pid, window_id, start, bus.identity, chain, role.casefold(),
                                        actual_frame, window_frame, geometry))
            for child in bus.children(ref):
                unique = bus.unique(child, pid)
                stack.append((unique, (*chain, unique)))
        if len(hits) != 1:
            raise AXError("element_ambiguous" if hits else "element_missing",
                          "one exact role/frame match in the bound window is required")
        _validate(bus, hits[0])
        return hits[0]


def frame_of(element: Element) -> Frame:
    with _bound(element) as bus:
        return _frame(bus, element.ref)


def _value(bus: _Bus, element: Element) -> str:
    count = bus.prop(element.ref, _TEXT, "CharacterCount")
    if type(count) is not int or not 0 <= count <= _MAX_TEXT:
        raise AXError("value_incomplete", "the exact text count is unavailable or exceeds 65536 characters")
    text = bus.call(element.ref, _TEXT, "GetText", "ii", (0, count))[0]
    after = bus.prop(element.ref, _TEXT, "CharacterCount")
    if not isinstance(text, str) or len(text) != count or after != count:
        raise AXError("value_incomplete", "the exact text read is incomplete or changed during observation")
    _validate(bus, element)
    return text


def value(element: Element) -> str:
    with _bound(element) as bus:
        return _value(bus, element)


def _capabilities(bus: _Bus, element: Element) -> dict[str, bool | None]:
    interfaces = bus.call(element.ref, _ACCESSIBLE, "GetInterfaces")[0]
    if not isinstance(interfaces, (tuple, list)) or any(not isinstance(name, str) for name in interfaces):
        raise AXError("invalid_reply", "the accessibility interfaces are unavailable")
    state = _state(bus, element.ref)
    required = (1 << 7) | (1 << 8) | (1 << 24)
    multiline, single_line = bool(state & (1 << 17)), bool(state & (1 << 26))
    return {
        "readable": _TEXT in interfaces,
        "writable": _TEXT in interfaces and _EDITABLE in interfaces and state & required == required,
        "multiline": multiline if multiline != single_line else None,
    }


def _writable(bus: _Bus, element: Element) -> bool:
    return _capabilities(bus, element)["writable"] is True


def text_capabilities(element: Element) -> dict[str, bool | None]:
    """AT-SPI interfaces/states, never inferred from a text-like role alone.

    MULTI_LINE=17 and SINGLE_LINE=26 are the published Atspi.StateType values.
    Missing or contradictory line states remain unknown.
    """
    with _bound(element) as bus:
        return _capabilities(bus, element)


def can_insert(element: Element) -> bool:
    with _bound(element) as bus:
        return _writable(bus, element)


def can_set_value(element: Element) -> bool:
    return can_insert(element)


def _input_text(text: str) -> None:
    if not isinstance(text, str) or len(text) > _MAX_TEXT or "\x00" in text:
        raise AXError("invalid_text", "text must be a bounded string without NUL")
    try:
        text.encode("utf-8")
    except UnicodeError as exc:
        raise AXError("invalid_text", "text must have a valid UTF-8 representation") from exc


def set_value_ack(element: Element, text: str) -> None:
    _input_text(text)
    with _bound(element) as bus:
        if not _writable(bus, element):
            raise AXError("not_writable", "the exact element does not expose writable text")
        _validate(bus, element)
        # No alternate route and no retry after a lost reply.
        reply = bus.call(element.ref, _EDITABLE, "SetTextContents", "s", (text,))
        if reply != (True,):
            raise AXError("set_value_refused", "the single exact text replacement was not acknowledged")


def insert_at_end(element: Element, text: str, *, expect: str | None = None) -> tuple[str, str]:
    _input_text(text)
    with _bound(element) as bus:
        before = _value(bus, element)
        if expect is not None and before != expect:
            raise AXError("precondition_changed", "the field changed before insertion")
        if len(before) + len(text) > _MAX_TEXT:
            raise AXError("value_incomplete", "the expected complete value exceeds 65536 characters")
        if not _writable(bus, element):
            raise AXError("not_writable", "the exact element does not expose writable text")
        _validate(bus, element)
        if _value(bus, element) != before:
            raise AXError("precondition_changed", "the field changed before insertion")
        reply = bus.call(element.ref, _EDITABLE, "InsertText", "isi",
                         (len(before), text, len(text.encode("utf-8"))))
        if reply != (True,):
            raise AXError("insert_refused", "the single exact text insertion was not acknowledged")
        # The caller grades exact equality; successful delivery does not establish completion.
        return before, _value(bus, element)


def document_path(pid: int, window_id: int) -> None:
    """Unavailable: AT-SPI text/window identity is not a saved-document identity."""
