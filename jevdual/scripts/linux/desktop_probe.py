"""Read-only readiness probes, run only in bounded isolated subprocesses."""

import asyncio
import ctypes
import json
import sys
from pathlib import Path


def x11(wm=False):
    lib = ctypes.CDLL("libX11.so.6")
    ptr, ulong, integer = ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int
    lib.XOpenDisplay.argtypes, lib.XOpenDisplay.restype = [ctypes.c_char_p], ptr
    lib.XCloseDisplay.argtypes = [ptr]
    display = lib.XOpenDisplay(None)
    if not display:
        raise RuntimeError("X handshake unavailable")
    try:
        if not wm:
            return {"x11_connected": True}
        lib.XDefaultRootWindow.argtypes, lib.XDefaultRootWindow.restype = [ptr], ulong
        lib.XInternAtom.argtypes, lib.XInternAtom.restype = [ptr, ctypes.c_char_p, integer], ulong
        lib.XGetWindowProperty.argtypes = [ptr, ulong, ulong, ctypes.c_long, ctypes.c_long,
                                          integer, ulong, ctypes.POINTER(ulong), ctypes.POINTER(integer),
                                          ctypes.POINTER(ulong), ctypes.POINTER(ulong), ctypes.POINTER(ptr)]
        lib.XFree.argtypes = [ptr]
        atom = lib.XInternAtom(display, b"_NET_SUPPORTING_WM_CHECK", 1)

        def check(window):
            actual, kind, count, remaining, data = ulong(), integer(), ulong(), ulong(), ptr()
            status = lib.XGetWindowProperty(display, window, atom, 0, 1, 0, 33,
                                           ctypes.byref(actual), ctypes.byref(kind), ctypes.byref(count),
                                           ctypes.byref(remaining), ctypes.byref(data))
            try:
                if status or actual.value != 33 or kind.value != 32 or count.value != 1 or remaining.value or not data:
                    raise RuntimeError("WM EWMH identity unavailable")
                return ctypes.cast(data, ctypes.POINTER(ulong))[0]
            finally:
                if data:
                    lib.XFree(data)

        if not atom:
            raise RuntimeError("WM not initialized")
        window = check(lib.XDefaultRootWindow(display))
        if not window or check(window) != window:
            raise RuntimeError("WM identity incomplete")
        return {"wm_ready": True}
    finally:
        lib.XCloseDisplay(display)


def bus():
    from jeepney import DBusAddress, new_method_call
    from jeepney.io.blocking import open_dbus_connection
    from jeepney.wrappers import unwrap_msg

    with open_dbus_connection(bus="SESSION", auth_timeout=1) as connection:
        address = unwrap_msg(connection.send_and_get_reply(new_method_call(
            DBusAddress("/org/a11y/bus", bus_name="org.a11y.Bus", interface="org.a11y.Bus"), "GetAddress"
        ), timeout=1))[0]
    if not isinstance(address, str) or not address.startswith("unix:"):
        raise RuntimeError("local accessibility bus unavailable")
    with open_dbus_connection(bus=address, auth_timeout=1):
        return {"bus_accessible": True}


async def editor(pid, document):
    from cua_driver import CuaDriver, ListWindowsInput
    from jevdual.native import NativeBridge

    driver = CuaDriver.create(embedded=True)
    try:
        windows = (await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))).windows
        if len(windows) != 1:
            raise RuntimeError("fixture window missing or ambiguous")
        snapshot = await NativeBridge(driver, pid, windows[0].window_id).observe()
        targets = [c for c in snapshot.menu.candidates if "append" in c.operations]
        if len(targets) != 1 or snapshot.values[targets[0].id] != document.read_text():
            raise RuntimeError("fixture exact text target is not ready, possibly modal or partial")
        return {"editor_exact_target_ready": True, "window_id": windows[0].window_id}
    finally:
        await driver.shutdown()


def main():
    try:
        stage = sys.argv[1]
        result = (x11(stage == "wm") if stage in {"x11", "wm"} else bus() if stage == "bus"
                  else asyncio.run(editor(int(sys.argv[2]), Path(sys.argv[3]))))
        print(json.dumps(result))
        return 0
    except Exception as exc:  # noqa: BLE001 - supervisor records failed readiness
        print(json.dumps({"ready": False, "reason": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
