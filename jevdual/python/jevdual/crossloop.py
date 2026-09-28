"""A model-driven loop across surfaces (option 1 after Q13a; docs/experiments/Q13.md).

Each surface a task declares (a browser page, a native app window) is its own footwork session, so every
guarantee the operator had holds for the model: receipts with delivery, carried values with their
source, grants bound to one effect, the posture, and a session that stays on its tab or window. The model
chooses one action per step as JSON; the loop runs it as the same ``footwork`` command an operator would
type and shows the model what the command printed. The model never grants anything: a pause ends the run
with its reason, unless the task's authorized scope (given at the surface's start) covers the effect.

Actions:
  {"name": "look", "surface": S}
  {"name": "read", "surface": S, "match": REGEX | "target": ID_OR_LABEL, "as": NAME}
  {"name": "do", "surface": S, "op": click|type|append|enter|scroll|key|hotkey|menu|navigate,
   "target": ID_OR_LABEL, "text": TEXT_OR_@NAME, "keys": [..], "path": "File > Save"}
  {"name": "done", "surface": S, "answer": TEXT}
  {"name": "stop", "reason": TEXT}
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ACTIONS = ("look", "read", "do", "done", "stop")
OBS_CHARS = 2500

SYSTEM = """You operate a computer through a harness, one action per turn. The task spans several surfaces (a
browser page, an app window); each is named, and every action names the surface it acts on. The harness
prints what each command did: read the receipt line (confirmed, partial, suspected no-op, refused,
unverifiable) before deciding the next step, and do not repeat an action whose receipt says it changed
nothing without trying something else.

Move a value between surfaces by reading it first ("read" with a regular expression "match" whose first
group is the value, or a "target" element, "as" a NAME), then use it as "@NAME" in a "do" type or append.
Never retype a value by hand; "@NAME" in a done answer is replaced by the carried value. Some effects pause for a person's permission: if a command prints "paused",
the run ends there; you cannot grant permission yourself. Finish with "done" on the surface that shows the
result (the harness verifies it), or "stop" with the reason if no available action can make progress.

Reply with one JSON object only: {"note": "<one short sentence>", "action": {...}} where the action is one of
{"name": "look", "surface": S}
{"name": "read", "surface": S, "match": "REGEX" or "target": "ID or label", "as": "NAME"}
{"name": "do", "surface": S, "op": "click|type|append|enter|scroll|key|hotkey|menu|navigate", "target": "ID or label", "text": "TEXT or @NAME", "keys": ["cmd", "s"], "path": "File > Save"}
{"name": "done", "surface": S, "answer": "TEXT"}
{"name": "stop", "reason": "TEXT"}"""


@dataclass
class Surface:
    name: str
    kind: str  # "browser" or "app"
    app: str = ""
    window: str = ""
    url: str = ""
    authorize: tuple[str, ...] = ()
    mode: str = "foreground_permitted"


@dataclass
class Step:
    step: int
    note: str
    action: dict[str, Any]
    exit: int | None
    output: str
    ms: float
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class CrossRun:
    status: str  # done, done_unverified, paused, stopped, budget, error
    reason: str
    steps: list[Step] = field(default_factory=list)
    answer: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


def footwork(session: Path, *argv: str) -> tuple[int, str]:
    p = subprocess.run(
        ["uv", "run", "footwork", *argv, "--session", str(session)],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (p.stdout + p.stderr).strip()
    # the model reads what an operator reads, without the driver's log lines
    out = "\n".join(ln for ln in out.splitlines() if not ln.startswith(("INFO ", "WARNING ", "DEBUG ")))
    return p.returncode, out


class CrossLoop:
    def __init__(
        self,
        task: str,
        surfaces: list[Surface],
        chat: Any,
        run_dir: Path,
        *,
        requirements: tuple[str, ...] = (),
        max_steps: int = 20,
        max_done_refusals: int = 2,
    ):
        self.task = task
        self.surfaces = {s.name: s for s in surfaces}
        self.chat = chat
        self.run_dir = run_dir
        self.requirements = requirements
        self.max_steps = max_steps
        self.max_done_refusals = max_done_refusals
        self.observations: dict[str, str] = {}
        self.history: list[str] = []

    def session(self, name: str) -> Path:
        return self.run_dir / name

    def start(self) -> str | None:
        """Bind every surface; the first observation of each is what the model starts from."""
        for s in self.surfaces.values():
            argv = ["start", self.task]
            if s.kind == "browser":
                argv += ["--browser"] + (["--url", s.url] if s.url else [])
            else:
                argv += ["--app", s.app] + (["--window", s.window] if s.window else [])
            argv += ["--mode", s.mode]
            if s.authorize:
                argv += ["--authorize", ",".join(s.authorize)]
            if self.requirements:
                argv += ["--require", "; ".join(self.requirements)]
            code, out = footwork(self.session(s.name), *argv)
            if code != 0:
                return f"surface {s.name} did not start: {out[-300:]}"
            self.observations[s.name] = out
        return None

    def messages(self) -> list[dict[str, str]]:
        parts = [f"TASK: {self.task}"]
        if self.requirements:
            parts.append("REQUIREMENTS: " + "; ".join(self.requirements))
        carried = self.carried()
        if carried:
            parts.append(
                "CARRIED VALUES: "
                + "; ".join(f"@{k} = {v!r} (from surface {s})" for k, (v, s) in carried.items())
            )
        for name, obs in self.observations.items():
            s = self.surfaces[name]
            where = s.url or f"{s.app} {s.window}".strip()
            parts.append(f"SURFACE {name} ({s.kind}: {where}), latest observation:\n{obs[-OBS_CHARS:]}")
        if self.history:
            parts.append("RECENT STEPS:\n" + "\n".join(self.history[-10:]))
        return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n\n".join(parts)}]

    def carried(self) -> dict[str, tuple[str, str]]:
        out = {}
        for name in self.surfaces:
            p = self.session(name) / "carries.json"
            if p.exists():
                for k, c in json.loads(p.read_text()).items():
                    out[k] = (c["text"], name)
        return out

    def command(self, action: dict[str, Any]) -> tuple[str, list[str]] | str:
        """``(surface, footwork argv)`` for an action, or a reason it cannot be run."""
        name = action.get("name")
        surface = str(action.get("surface") or "")
        if name in ("look", "read", "do", "done") and surface not in self.surfaces:
            return f"no surface named {surface!r}; surfaces: {', '.join(self.surfaces)}"
        if name == "look":
            return surface, ["look"]
        if name == "read":
            argv = ["read"]
            if action.get("match"):
                argv += ["--match", str(action["match"])]
            elif action.get("target") is not None:
                argv += [str(action["target"])]
            else:
                return "read needs a match or a target"
            return surface, [*argv, "--as", str(action.get("as") or "value")]
        if name == "do":
            op = str(action.get("op") or "")
            argv = ["do", op]
            if op in ("key", "hotkey"):
                argv += [str(k) for k in (action.get("keys") or [])]
            elif op == "menu":
                argv += [str(action.get("path") or "")]
            elif op == "navigate":
                argv += [str(action.get("text") or action.get("target") or "")]
            else:
                argv += [str(action.get("target") or "")]
                if action.get("text") is not None:
                    argv += [str(action["text"])]
            text = str(action.get("text") or "")
            ref = re.fullmatch(r"@([A-Za-z_][A-Za-z0-9_]*)", text.strip())
            if ref:
                holder = self.carried().get(ref.group(1))
                if holder is None:
                    return f"@{ref.group(1)} has not been read on any surface"
                argv += ["--from", str(self.session(holder[1]))]
            return surface, argv
        if name == "done":
            # a carried reference in the answer is the carried value (Q13 smoke: "@RESULT" reached the
            # verifier as literal text)
            carried = self.carried()
            answer = re.sub(
                r"@([A-Za-z_][A-Za-z0-9_]*)",
                lambda m: carried[m.group(1)][0] if m.group(1) in carried else m.group(0),
                str(action.get("answer") or ""),
            )
            others: list[str] = []
            for other in self.surfaces:
                if other != surface:
                    others += ["--context-from", str(self.session(other))]
            return surface, ["done", answer, *others]
        return f"unknown action {name!r}"

    async def run(self) -> CrossRun:
        from jevdual.desktop_s2 import parse_reply

        why = self.start()
        if why:
            return CrossRun("error", why)
        run = CrossRun("budget", f"{self.max_steps} steps")
        refusals = 0
        for i in range(1, self.max_steps + 1):
            t0 = time.perf_counter()
            reply = await self.chat(self.messages())
            run.input_tokens += reply.input_tokens
            run.output_tokens += reply.output_tokens
            try:
                note, action = _parse(reply.content, parse_reply)
            except ValueError as exc:
                self.history.append(
                    f"step {i}: your reply could not be read ({exc}); reply with one JSON object"
                )
                run.steps.append(
                    Step(
                        i,
                        "",
                        {},
                        None,
                        f"unreadable reply: {exc}",
                        0.0,
                        reply.input_tokens,
                        reply.output_tokens,
                    )
                )
                continue
            if action.get("name") == "stop":
                run.steps.append(
                    Step(i, note, action, None, "", 0.0, reply.input_tokens, reply.output_tokens)
                )
                run.status, run.reason = "stopped", str(action.get("reason") or "")
                return run
            cmd = self.command(action)
            if isinstance(cmd, str):
                self.history.append(f"step {i}: {json.dumps(action)} -> not run: {cmd}")
                run.steps.append(
                    Step(i, note, action, None, cmd, 0.0, reply.input_tokens, reply.output_tokens)
                )
                continue
            surface, argv = cmd
            code, out = footwork(self.session(surface), *argv)
            ms = (time.perf_counter() - t0) * 1000
            run.steps.append(
                Step(i, note, action, code, out[-1500:], ms, reply.input_tokens, reply.output_tokens)
            )
            if action["name"] in ("look", "do"):
                self.observations[surface] = out
            summary = next(
                (
                    ln
                    for ln in out.splitlines()
                    if ln.startswith(
                        ("receipt", "carried", "not carried", "paused", "stopped", "verifier", "accepted")
                    )
                ),
                out[:160],
            )
            self.history.append(f"step {i} [{surface}] {' '.join(argv[:3])}: exit {code}: {summary[:220]}")
            if code == 3:
                run.status, run.reason = "paused", summary
                return run
            if code == 7:
                run.status, run.reason = "error", summary
                return run
            if action["name"] == "done":
                if code == 0:
                    run.status, run.reason, run.answer = "done", summary, str(action.get("answer") or "")
                    return run
                refusals += 1
                if refusals > self.max_done_refusals:
                    run.status, run.reason, run.answer = (
                        "done_unverified",
                        summary,
                        str(action.get("answer") or ""),
                    )
                    return run
        return run


def _parse(raw: str, parse_reply: Any) -> tuple[str, dict[str, Any]]:
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        raise ValueError("no JSON object")
    obj = json.loads(m.group(0))
    action = obj.get("action") if isinstance(obj, dict) else None
    if not isinstance(action, dict) or action.get("name") not in ACTIONS:
        raise ValueError(f"no known action in {str(obj)[:120]}")
    return str(obj.get("note") or "")[:200], action


def to_json(run: CrossRun) -> dict[str, Any]:
    return asdict(run)
