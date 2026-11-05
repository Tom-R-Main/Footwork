"""A Tk window that receives drags and logs every pointer event it sees, for the live drag check.

    python scripts/drag_surface.py --out DIR

Writes DIR/ready.json once laid out (screen points of the square's centre, the slider's knob at 0 and the
slider point for 75), and DIR/events.json on every button release and on exit. The events come from Tk's
own bindings, so they are what the app received, independent of the poster.
"""

from __future__ import annotations

import argparse
import json
import time
import tkinter as tk
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    root.title("footwork drag fixture")
    root.geometry("720x420+200+160")
    canvas = tk.Canvas(root, width=700, height=300, bg="white", highlightthickness=0)
    canvas.pack(padx=10, pady=(10, 0))
    square = canvas.create_rectangle(40, 120, 80, 160, fill="#2b6cb0", outline="")
    value = tk.IntVar(value=0)
    scale = tk.Scale(root, from_=0, to=100, orient="horizontal", length=400, variable=value, showvalue=True)
    scale.pack(pady=10)
    events: list[dict] = []
    grab: dict = {}

    def log(kind: str, e: tk.Event, widget: str) -> None:
        events.append(
            {
                "kind": kind,
                "widget": widget,
                "x_root": e.x_root,
                "y_root": e.y_root,
                "tk_ms": e.time,
                "mono": time.monotonic(),
                "slider": value.get(),
            }
        )

    def press(e: tk.Event) -> None:
        log("press", e, "canvas")
        grab["on"] = square in canvas.find_overlapping(e.x, e.y, e.x, e.y)
        grab["x"], grab["y"] = e.x, e.y

    def motion(e: tk.Event) -> None:
        log("motion", e, "canvas")
        if grab.get("on"):
            canvas.move(square, e.x - grab["x"], e.y - grab["y"])
            grab["x"], grab["y"] = e.x, e.y

    def release(e: tk.Event) -> None:
        log("release", e, "canvas")
        grab["on"] = False
        dump()

    def dump() -> None:
        x1, y1, x2, y2 = canvas.coords(square)
        cx, cy = canvas.winfo_rootx(), canvas.winfo_rooty()
        (out / "events.json").write_text(
            json.dumps(
                {
                    "square_centre_root": [cx + (x1 + x2) / 2, cy + (y1 + y2) / 2],
                    "slider": value.get(),
                    "events": events,
                },
                indent=1,
            )
        )

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", motion)
    canvas.bind("<ButtonRelease-1>", release)
    scale.bind("<ButtonPress-1>", lambda e: log("press", e, "slider"), add="+")
    scale.bind("<B1-Motion>", lambda e: log("motion", e, "slider"), add="+")
    scale.bind("<ButtonRelease-1>", lambda e: (log("release", e, "slider"), root.after(50, dump)), add="+")

    def ready() -> None:
        root.update_idletasks()
        cx, cy = canvas.winfo_rootx(), canvas.winfo_rooty()
        x1, y1, x2, y2 = canvas.coords(square)
        sx, sy = scale.winfo_rootx(), scale.winfo_rooty()
        k0x, k0y = scale.coords(0)
        k75x, k75y = scale.coords(75)
        (out / "ready.json").write_text(
            json.dumps(
                {
                    "square_centre_root": [cx + (x1 + x2) / 2, cy + (y1 + y2) / 2],
                    "slider_0_root": [sx + k0x, sy + k0y],
                    "slider_75_root": [sx + k75x, sy + k75y],
                    "window_root": [
                        root.winfo_rootx(),
                        root.winfo_rooty(),
                        root.winfo_width(),
                        root.winfo_height(),
                    ],
                }
            )
        )

    root.after(500, ready)
    root.protocol("WM_DELETE_WINDOW", lambda: (dump(), root.destroy()))
    root.lift()
    root.attributes("-topmost", True)
    root.mainloop()


if __name__ == "__main__":
    main()
