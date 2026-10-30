"""Isolated read-only Xlib helper. Its caller must impose a process timeout.

Run by linux_ax with an isolated interpreter and only X11 authentication/display
settings. The process-global Xlib error handler never affects the host driver.
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import sys
import threading

_X_LOCK = threading.Lock()


class ProbeError(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def query(pid: int, window_id: int) -> dict:
    """Query the client XID, not a title or window-list ordinal."""
    if not re.fullmatch(r"(?:unix)?:\d+(?:\.\d+)?", os.environ.get("DISPLAY", "")):
        raise ProbeError("x11_unavailable", "a local X11 display is required for exact window binding")
    if type(pid) is not int or type(window_id) is not int or not 0 < window_id < 2**32 or pid <= 0:
        raise ProbeError("window_missing", "invalid process or X11 window identity")
    try:
        lib = ctypes.CDLL("libX11.so.6")
    except OSError as exc:
        raise ProbeError("x11_unavailable", "libX11 is unavailable") from exc
    pointer, ulong, uint, integer = ctypes.c_void_p, ctypes.c_ulong, ctypes.c_uint, ctypes.c_int
    lib.XOpenDisplay.argtypes, lib.XOpenDisplay.restype = [ctypes.c_char_p], pointer
    lib.XCloseDisplay.argtypes = [pointer]
    lib.XInternAtom.argtypes, lib.XInternAtom.restype = [pointer, ctypes.c_char_p, integer], ulong
    lib.XGetWindowProperty.argtypes = [pointer, ulong, ulong, ctypes.c_long, ctypes.c_long,
                                     integer, ulong, ctypes.POINTER(ulong), ctypes.POINTER(integer),
                                     ctypes.POINTER(ulong), ctypes.POINTER(ulong), ctypes.POINTER(pointer)]
    lib.XGetGeometry.argtypes = [pointer, ulong, ctypes.POINTER(ulong), ctypes.POINTER(integer),
                                ctypes.POINTER(integer), ctypes.POINTER(uint), ctypes.POINTER(uint),
                                ctypes.POINTER(uint), ctypes.POINTER(uint)]
    lib.XTranslateCoordinates.argtypes = [pointer, ulong, ulong, integer, integer,
                                         ctypes.POINTER(integer), ctypes.POINTER(integer), ctypes.POINTER(ulong)]
    lib.XFree.argtypes = [pointer]
    lib.XSync.argtypes = [pointer, integer]
    lib.XSetErrorHandler.argtypes, lib.XSetErrorHandler.restype = [pointer], pointer
    errors = []
    callback_type = ctypes.CFUNCTYPE(integer, pointer, pointer)
    callback = callback_type(lambda _display, _event: errors.append(True) or 0)
    with _X_LOCK:
        display = lib.XOpenDisplay(None)
        if not display:
            raise ProbeError("x11_unavailable", "the X11 display could not be opened")
        previous = lib.XSetErrorHandler(ctypes.cast(callback, pointer))
        try:
            def cardinal(name: bytes, size: int) -> tuple[int, ...] | None:
                actual, kind, count, remaining, data = ulong(), integer(), ulong(), ulong(), pointer()
                atom = lib.XInternAtom(display, name, 1)
                if not atom:
                    return None
                status = lib.XGetWindowProperty(display, window_id, atom, 0, size, 0, 6,
                                               ctypes.byref(actual), ctypes.byref(kind), ctypes.byref(count),
                                               ctypes.byref(remaining), ctypes.byref(data))
                try:
                    if status:
                        raise ProbeError("window_missing", "the X11 window property is unavailable")
                    if actual.value == 0 and count.value == 0:
                        return None
                    if actual.value != 6 or kind.value != 32 or remaining.value or count.value != size or not data:
                        raise ProbeError("geometry_unavailable", "the X11 cardinal property is malformed")
                    values = ctypes.cast(data, ctypes.POINTER(ulong))
                    return tuple(values[index] for index in range(size))
                finally:
                    if data:
                        lib.XFree(data)

            owner = cardinal(b"_NET_WM_PID", 1)
            if owner != (pid,):
                raise ProbeError("lost_identity", "the X11 client does not belong to the original process")
            extents = cardinal(b"_NET_FRAME_EXTENTS", 4)
            root, child = ulong(), ulong()
            x, y, screen_x, screen_y = integer(), integer(), integer(), integer()
            width, height, border, depth = uint(), uint(), uint(), uint()
            geometry = lib.XGetGeometry(display, window_id, ctypes.byref(root), ctypes.byref(x),
                                       ctypes.byref(y), ctypes.byref(width), ctypes.byref(height),
                                       ctypes.byref(border), ctypes.byref(depth))
            translated = lib.XTranslateCoordinates(display, window_id, root.value, 0, 0,
                                                  ctypes.byref(screen_x), ctypes.byref(screen_y),
                                                  ctypes.byref(child)) if geometry else 0
            lib.XSync(display, 0)
            if errors or not geometry or not translated or width.value == 0 or height.value == 0:
                raise ProbeError("window_missing", "the original X11 client geometry is unavailable")
            return {"schema_version": 1,
                    "client": [screen_x.value, screen_y.value, width.value, height.value],
                    "frame_extents": extents}
        finally:
            lib.XSync(display, 0)
            lib.XSetErrorHandler(previous)
            lib.XCloseDisplay(display)



def main() -> int:
    try:
        if len(sys.argv) != 3:
            raise ValueError("expected pid and window")
        report = query(int(sys.argv[1]), int(sys.argv[2]))
    except ProbeError as exc:
        print(json.dumps({"schema_version": 1, "error": {"code": exc.reason, "message": str(exc)}}))
        return 1
    except (ValueError, OSError, OverflowError):
        print(json.dumps({"schema_version": 1, "error": {"code": "x11_unavailable",
                                                        "message": "X11 query could not be completed"}}))
        return 1
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
