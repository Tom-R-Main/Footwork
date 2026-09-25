"""A simulated Mac for the operator session: a Driver double with state, so a scenario can run the real
``footwork start / look / s1 / do / done`` commands end to end without a permission grant.

The window is the recorded Calculator snapshot (``fixtures/native/calculator.json``) with a working
calculator behind it: presses change the display, which is what the receipts and the verifier read. The
world takes the SDK's real input types, answers clicks with a real ``ActionResult``, and numbers every
observation, so element tokens carry the snapshot they came from as the Driver's do. A test can change
the window under the operator (``relabel``), list an app as installed but not running, or make the
Driver refuse a press.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

FIXTURE = Path(__file__).parent / "native" / "calculator.json"
LRM = "‎"
_OPS = {"Add": "+", "Subtract": "−", "Multiply": "×", "Divide": "÷"}


@dataclass
class Calc:
    entry: str = "0"
    acc: float | None = None
    op: str | None = None
    expr: str = ""
    fresh: bool = True

    def press(self, label: str) -> None:
        if label.isdigit():
            self.entry = label if self.fresh or self.entry == "0" else self.entry + label
            self.fresh = False
        elif label in _OPS:
            self._settle()
            self.acc, self.op, self.fresh = float(self.entry), label, True
            self.expr = f"{_fmt(self.acc)}{_OPS[label]}"
        elif label == "Equals":
            self.expr = f"{self.expr}{self.entry}" if self.op else self.expr
            self._settle()
            self.op, self.fresh = None, True
        elif label == "All Clear":
            self.entry, self.acc, self.op, self.expr, self.fresh = "0", None, None, "", True
        elif label == "Delete":
            self.entry = self.entry[:-1] or "0"

    def _settle(self) -> None:
        if self.op is None or self.acc is None:
            return
        b = float(self.entry)
        r = {"Add": self.acc + b, "Subtract": self.acc - b, "Multiply": self.acc * b, "Divide": self.acc / b}
        self.entry = _fmt(r[self.op])


def _fmt(x: float) -> str:
    return f"{int(x):,}" if float(x).is_integer() else f"{x:,.6g}"


@dataclass
class World:
    """A Driver double: ``create()`` hands out this same world, so state survives between commands."""

    calc: Calc = field(default_factory=Calc)
    apps: list[tuple[str, int, bool]] = field(default_factory=lambda: [("Calculator", 77, True)])
    window_id: int = 40335
    #: element_index -> label, applied to every later observation (the person changed the window)
    relabels: dict[int, str] = field(default_factory=dict)
    #: labels whose press the Driver refuses
    refuse: set[str] = field(default_factory=set)
    presses: list[str] = field(default_factory=list)
    tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    n: int = 0
    base: dict[str, Any] = field(default_factory=lambda: json.loads(FIXTURE.read_text()))

    # ---- the Driver surface NativeBridge and the session use

    def create(self) -> World:
        return self

    async def shutdown(self) -> None:
        return None

    async def list_apps(self, inp: Any) -> Any:
        return SimpleNamespace(
            apps=[
                SimpleNamespace(name=n, pid=(pid if running else 0), running=running)
                for n, pid, running in self.apps
            ]
        )

    async def list_windows(self, inp: Any) -> Any:
        if inp.pid != 77:
            return SimpleNamespace(windows=[])
        return SimpleNamespace(
            windows=[
                SimpleNamespace(
                    window_id=self.window_id,
                    title="Calculator",
                    bounds=SimpleNamespace(width=230, height=408),
                )
            ]
        )

    async def get_window_state(self, inp: Any) -> dict[str, Any]:
        self.n += 1
        sid = f"s{self.n:08x}"
        snap = dict(self.base)
        snap["snapshot_id"] = sid
        snap["elements"] = [self._element(e, sid) for e in self.base["elements"]]
        snap["tree_markdown"] = self._markdown()
        return snap

    async def click(self, inp: Any) -> Any:
        import cua_driver as cd

        sid, idx = inp.position.element_token.split(":")
        if sid != f"s{self.n:08x}":
            raise RuntimeError(f"tool='click', message='stale element token {sid}', error_code='stale_token'")
        label = self._label(int(idx))
        if label in self.refuse:
            raise RuntimeError("tool='click', message='AX action failed', error_code='ax_failed'")
        self.presses.append(label)
        self.calc.press(label)
        return cd.ActionResult(
            effect=cd.ActionEffect.CONFIRMED,
            route=cd.ActionRoute.ACCESSIBILITY,
            delivery=cd.ActionDelivery(mode=cd.ActionDeliveryMode.BACKGROUND, delivered_count=1),
            evidence=[],
            escalation=None,
        )

    async def call_tool(self, name: str, args_json: str) -> Any:
        self.tool_calls.append((name, json.loads(args_json)))
        return SimpleNamespace(action=None, text="", is_error=False, error_code=None, structured_json=None)

    # ---- rendering

    def display(self) -> str:
        return self.calc.entry

    def _label(self, idx: int) -> str | None:
        if idx in self.relabels:
            return self.relabels[idx]
        el = next((e for e in self.base["elements"] if e["element_index"] == idx), None)
        return el.get("label") if el else None

    def _element(self, e: dict[str, Any], sid: str) -> dict[str, Any]:
        out = {**e, "element_token": f"{sid}:{e['element_index']}"}
        if e["element_index"] in self.relabels and e.get("role") == "AXButton":
            out["label"] = self.relabels[e["element_index"]]
        return out

    def _markdown(self) -> str:
        md = self.base["tree_markdown"]
        lines = md.split("\n")
        statics = [i for i, ln in enumerate(lines[:4]) if 'AXStaticText = "' in ln]
        if len(statics) >= 2:
            expr = self.calc.expr or self.calc.entry
            lines[statics[0]] = re.sub(r'= ".*"', f'= "{LRM}{expr}"', lines[statics[0]])
            lines[statics[1]] = re.sub(r'= ".*"', f'= "{LRM}{self.calc.entry}"', lines[statics[1]])
        for idx, label in self.relabels.items():
            lines = [re.sub(rf"(\[{idx}\] AXButton) \([^)]*\)", rf"\1 ({label})", ln) for ln in lines]
        return "\n".join(lines)
