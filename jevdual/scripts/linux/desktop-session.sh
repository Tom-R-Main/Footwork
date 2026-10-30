#!/bin/bash
# Run only inside the task-owned Linux container, under dbus-run-session.
set -euo pipefail
state=${1:?fresh task state directory required}
if [[ -e "$state" ]]; then
    echo "Choose a fresh desktop state directory" >&2
    exit 2
fi
mkdir -m 700 "$state"
export DISPLAY=:99
export NO_AT_BRIDGE=0
export GTK_MODULES=atk-bridge
export XDG_RUNTIME_DIR="$state/runtime"
mkdir -m 700 "$XDG_RUNTIME_DIR"
printf '%s' "${DBUS_SESSION_BUS_ADDRESS:?dbus-run-session required}" > "$state/session-bus"
children=()
cleanup() {
    for child in "${children[@]}"; do kill "$child" 2>/dev/null || true; done
    wait || true
}
trap cleanup EXIT
trap 'exit 0' TERM INT
Xvfb "$DISPLAY" -screen 0 1280x900x24 -nolisten tcp > "$state/xvfb.log" 2>&1 &
children+=("$!")
python3 - <<'PY'
import ctypes, time
lib = ctypes.CDLL('libX11.so.6')
lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
lib.XOpenDisplay.restype = ctypes.c_void_p
lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
for _ in range(100):
    display = lib.XOpenDisplay(None)
    if display:
        lib.XCloseDisplay(display)
        break
    time.sleep(.05)
else:
    raise SystemExit('isolated X display did not start')
PY
openbox > "$state/openbox.log" 2>&1 &
children+=("$!")
printf 'Footwork Linux fixture\n\tkeep trailing spaces  \n' > "$state/document.txt"
mousepad --disable-server "$state/document.txt" > "$state/editor.log" 2>&1 &
children+=("$!")
printf '%s\n' "${children[-1]}" > "$state/editor.pid"
touch "$state/started"
wait
