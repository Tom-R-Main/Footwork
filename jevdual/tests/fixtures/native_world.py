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

    def create(self, *, embedded: bool = False) -> World:
        assert embedded is True
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
            summary=None,
            error=None,
            hint=None,
            next_call=None,
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


@dataclass
class TextWorld:
    """TextEdit at the external Cua/AX boundary; menu parsing and insertion stay real.

    Cua omits an empty value and strips whitespace from a nonempty preview. AX
    independently reports the full field, including an explicit zero character
    count when its value is absent. The content-derived label changes on insertion.
    """

    document: Path
    content: str = "Invoice report"
    readable: bool = True
    character_count: int | None = 0
    insertable: bool = True
    setter_error: int = 0
    secure: bool = False
    ambiguous: bool = False
    after_insert: str | None = None
    extra_field: bool = False
    frame: tuple[int, int, int, int] | None = (10, 20, 400, 300)
    writes: list[tuple[str, Any]] = field(default_factory=list)
    n: int = 0
    pid: int = 77
    window_id: int = 40335

    def install(self, monkeypatch: Any) -> None:
        import sys

        import cua_driver
        from jevdual import ax
        from jevdual.posture import ExecutionPolicy

        monkeypatch.setattr(cua_driver.CuaDriver, "create", staticmethod(lambda *, embedded=False: self))
        monkeypatch.setattr(ExecutionPolicy, "locked", lambda _: False)
        monkeypatch.setattr("jevdual.native.accessibility_status", lambda: "granted")
        monkeypatch.setattr(ax, "window_element", lambda pid, wid: self._window(pid, wid))
        monkeypatch.setattr(ax, "_attr", self._attr)
        monkeypatch.setattr(ax, "frame_of", lambda _: ax.Frame(*self.frame) if self.frame else None)
        monkeypatch.setitem(
            sys.modules,
            "ApplicationServices",
            SimpleNamespace(
                AXUIElementSetAttributeValue=self._set,
                AXUIElementIsAttributeSettable=lambda el, name, _: (
                    self.setter_error if name == "AXSelectedText" else 0,
                    self.insertable,
                ),
                AXValueCreate=lambda kind, value: value,
                kAXValueCFRangeType=4,
            ),
        )
        monkeypatch.setitem(sys.modules, "Foundation", SimpleNamespace(NSMakeRange=lambda n, m: (n, m)))

    def _window(self, pid: int, wid: int) -> str:
        assert (pid, wid) == (self.pid, self.window_id)
        return "window"

    def _attr(self, element: Any, name: str) -> Any:
        if element == "window":
            return {
                "AXDocument": self.document.as_uri(),
                "AXRole": "AXWindow",
                "AXChildren": ["body", "duplicate"] if self.ambiguous else ["body"],
            }.get(name)
        return {
            "AXRole": "AXSecureTextField" if self.secure else "AXTextArea",
            "AXValue": self.content if self.readable and self.content else None,
            "AXNumberOfCharacters": len(self.content) if self.readable else self.character_count,
            "AXChildren": [],
        }.get(name)

    def _set(self, element: Any, name: str, value: Any) -> int:
        assert element == "body"
        if not self.insertable:
            return -25205
        self.writes.append((name, value))
        if name == "AXSelectedTextRange":
            assert value == (len(self.content.encode("utf-16-le")) // 2, 0)
        if name == "AXSelectedText":
            assert self.writes[-2][0] == "AXSelectedTextRange"
            self.content += value
            if self.after_insert == "role":
                self.secure = True
            elif self.after_insert == "frame":
                self.frame = (110, 20, 400, 300)
            elif self.after_insert == "ambiguous":
                self.ambiguous = self.extra_field = True
        return 0

    async def shutdown(self) -> None:
        pass

    async def get_window_state(self, inp: Any) -> dict[str, Any]:
        assert (inp.pid, inp.window_id) == (self.pid, self.window_id)
        self.n += 1
        sid = f"s{self.n:08x}"
        preview = self.content.strip() if self.content else None
        body: dict[str, Any] = {
            "element_index": 1,
            "element_token": f"{sid}:1",
            "role": "AXSecureTextField" if self.secure else "AXTextArea",
            "label": preview or "First Text View",
            "parent_index": 0,
            "enabled": True,
        }
        if preview is not None:
            body["value"] = preview
        if self.frame is not None:
            body["frame"] = dict(zip(("x", "y", "w", "h"), self.frame, strict=True))
        elements = [
            {"element_index": 0, "element_token": f"{sid}:0", "role": "AXWindow"},
            body,
        ]
        if self.extra_field:
            elements.append(
                {**body, "element_index": 2, "element_token": f"{sid}:2", "label": "Second Text View"}
            )
        return {
            "snapshot_id": sid,
            "pid": self.pid,
            "window_id": self.window_id,
            "app_name": "TextEdit",
            "window_title": self.document.name,
            "elements_complete": True,
            "tree_markdown": "",
            "elements": elements,
        }
