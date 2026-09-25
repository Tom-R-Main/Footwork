"""The scripted person's own window for the coexistence suite (Q15): a Tk text box in its own process
that writes its whole content to ``--out`` whenever it changes, so the oracle reads what the person's
keystrokes produced without going through the Driver or accessibility.

    python -m jevdual.coexist_surface --out /tmp/person.txt --title "person" [--x 60 --y 60]
"""

from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="person")
    ap.add_argument("--x", type=int, default=60)
    ap.add_argument("--y", type=int, default=60)
    args = ap.parse_args()
    out = Path(args.out)
    out.write_text("")
    root = tk.Tk()
    root.title(args.title)
    root.geometry(f"520x260+{args.x}+{args.y}")
    txt = tk.Text(root, wrap="word")
    txt.pack(fill="both", expand=True)
    last = {"v": ""}

    def dump() -> None:
        v = txt.get("1.0", "end-1c")
        if v != last["v"]:
            out.write_text(v)
            last["v"] = v
        root.after(50, dump)

    def focus() -> None:
        root.lift()
        txt.focus_set()

    root.bind("<FocusIn>", lambda _e: txt.focus_set())
    root.after(100, focus)
    root.after(50, dump)
    root.protocol("WM_DELETE_WINDOW", lambda: (out.write_text(txt.get("1.0", "end-1c")), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
