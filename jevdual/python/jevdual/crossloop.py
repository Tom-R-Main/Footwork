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


#: M3: what the recovery arm adds to the instructions (the loop's own checks do the rest)
SYSTEM_RECOVERY = """

Also available: {"name": "look", "surface": S, "menu_bar": true} lists a native app's menu items. A stop
names its kind: {"name": "stop", "kind": "unavailable|unsupported_route|ambiguous_target|missing_evidence|other",
"reason": "TEXT"}; when a page or window says the task cannot be done, stop with kind unavailable and quote it.
The harness refuses an action already tried in the same state and an effect already recorded; after several
steps without progress it says RECOVERY, and then ends the run if nothing changes."""

_STOP_KINDS = ("unavailable", "unsupported_route", "ambiguous_target", "missing_evidence", "other")


def compact(out: str, budget: int = 2500) -> str:
    """M3: an observation for the model that keeps its head (identity, notes, the receipt) whole and trims
    the element list and page text, instead of keeping only the last characters."""
    lines = out.splitlines()
    ei = next((i for i, ln in enumerate(lines) if re.match(r"^\d+ elements:", ln)), None)
    pi = next((i for i, ln in enumerate(lines) if ln.startswith("page text")), None)
    if ei is None and pi is None:
        return (
            out if len(out) <= budget else out[: budget - 40] + f"\n… ({len(out) - budget + 40} chars more)"
        )
    head_end = min(i for i in (ei, pi) if i is not None)
    head = lines[:head_end]
    elements = lines[ei : pi if pi is not None and pi > ei else len(lines)] if ei is not None else []
    page = lines[pi:] if pi is not None else []
    used = sum(len(x) + 1 for x in head)
    kept_el = []
    for ln in elements:
        if used + len(ln) + 1 > budget * 0.6:
            kept_el.append(f"  … {len(elements) - len(kept_el)} more elements (look again, or read a target)")
            break
        kept_el.append(ln)
        used += len(ln) + 1
    text = "\n".join(page)
    room = max(200, budget - used)
    if len(text) > room:
        text = text[:room] + f"\n… ({len(text) - room} chars more; read --match searches all of it)"
    return "\n".join([*head, *kept_el, text]).strip()


@dataclass
class Surface:
    name: str
    kind: str  # "browser" or "app"
    app: str = ""
    window: str = ""
    url: str = ""
    authorize: tuple[str, ...] = ()
    mode: str = "foreground_permitted"
    #: V7: the requirements observable on this surface, judged here; empty uses the task's
    requirements: tuple[str, ...] = ()


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
        recovery: bool = False,
        max_seconds: float | None = None,
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
        #: M3: state signatures, tried actions, bounded recovery and effect reconciliation
        self.recovery = recovery
        self.max_seconds = max_seconds
        from jevdual.progress import Progress

        self.progress = Progress()

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
            reqs = s.requirements or self.requirements
            if reqs:
                argv += ["--require", "; ".join(reqs)]
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
            shown = compact(obs, OBS_CHARS) if self.recovery else obs[-OBS_CHARS:]
            parts.append(f"SURFACE {name} ({s.kind}: {where}), latest observation:\n{shown}")
        if self.history:
            parts.append("RECENT STEPS:\n" + "\n".join(self.history[-10:]))
        note = self.progress.note() if self.recovery else None
        if note:
            parts.append(note)
        system = SYSTEM + SYSTEM_RECOVERY if self.recovery else SYSTEM
        return [{"role": "system", "content": system}, {"role": "user", "content": "\n\n".join(parts)}]

    def state_sig(self, name: str) -> str:
        from jevdual.progress import signature

        p = self.session(name) / "session.json"
        return signature(json.loads(p.read_text())) if p.exists() else ""

    def effect_count(self) -> int:
        """Saved and submitted records across this run's surfaces (jevdual.completion)."""
        from jevdual.completion import _records, effects

        return sum(
            1
            for n in self.surfaces
            for e in effects(_records(self.session(n)))
            if e.effect in ("saved", "submitted")
        )

    def recorded_submissions(self) -> list[tuple[str, Any]]:
        """Every submission this run's receipts establish, with its surface (M3 reconciliation)."""
        from jevdual.completion import _records, effects

        out = []
        for name in self.surfaces:
            recs = _records(self.session(name))
            for e in effects(recs):
                if e.effect == "submitted":
                    label = next(
                        (
                            (r.get("action") or {}).get("target_label")
                            for r in recs
                            if r.get("kind") == "receipt" and float(r.get("t") or 0) == e.t
                        ),
                        None,
                    )
                    out.append((name, e, label))
        return out

    def repeats_effect(self, surface: str, action: dict[str, Any]) -> str | None:
        """Why a do would repeat an effect this run already recorded, or None: loading a submission's
        result address again, or clicking the control that submitted it (Q19 H02's model tried both)."""
        from urllib.parse import urlsplit

        if action.get("name") != "do":
            return None
        op = str(action.get("op") or "")
        for name, e, label in self.recorded_submissions():
            if op == "navigate":
                u = urlsplit(str(action.get("text") or action.get("target") or ""))
                if u.path == e.resource and u.query and u.query == e.detail.removeprefix("submitted "):
                    return f"that address is the result of the submission recorded at step {e.step} ({e.detail}); loading it would submit again"
            if op == "click" and name == surface and label and str(action.get("target") or "") == label:
                return f"'{label}' already submitted at step {e.step} ({e.detail}); clicking it again would submit again"
        return None

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
            return surface, ["look", "--menu-bar"] if action.get("menu_bar") and self.recovery else ["look"]
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
            return surface, [
                "done",
                self.resolve(str(action.get("answer") or "")),
                *self._context_args(surface),
            ]
        return f"unknown action {name!r}"

    def resolve(self, text: str) -> str:
        """``text`` with each carried ``@NAME`` replaced by its value."""
        carried = self.carried()
        return re.sub(
            r"@([A-Za-z_][A-Za-z0-9_]*)",
            lambda m: carried[m.group(1)][0] if m.group(1) in carried else m.group(0),
            text,
        )

    def _context_args(self, surface: str) -> list[str]:
        out: list[str] = []
        for other in self.surfaces:
            if other != surface:
                out += ["--context-from", str(self.session(other))]
        return out

    def _done_everywhere(self, answer: str) -> tuple[int, str]:
        """V7: with per-surface requirements, a done is judged on every surface that has some, each where
        its requirements are observable; it is accepted only if every surface accepts."""
        codes, outs = [], []
        for name, s in self.surfaces.items():
            if not s.requirements:
                continue
            code, out = footwork(self.session(name), "done", answer, *self._context_args(name))
            codes.append(code)
            verdict = next((ln for ln in out.splitlines() if ln.startswith("verifier")), out[-200:])
            outs.append(f"[{name}] exit {code}: {verdict}")
        worst = next((c for c in codes if c != 0), 0)
        return worst, "\n".join(outs)

    async def run(self) -> CrossRun:
        from jevdual.desktop_s2 import parse_reply

        why = self.start()
        if why:
            return CrossRun("error", why)
        run = CrossRun("budget", f"{self.max_steps} steps")
        refusals = 0
        began = time.perf_counter()
        if self.recovery:
            for name in self.surfaces:
                self.progress.enter(name, self.state_sig(name))
        for i in range(1, self.max_steps + 1):
            t0 = time.perf_counter()
            if self.max_seconds is not None and t0 - began > self.max_seconds:
                run.status, run.reason = "time", f"{self.max_seconds:.0f} s"
                return run
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
                if self.recovery:
                    kind = str(action.get("kind") or "other")
                    run.reason = f"[{kind if kind in _STOP_KINDS else 'other'}] {run.reason}"
                return run
            cmd = self.command(action)
            if self.recovery and not isinstance(cmd, str) and action.get("name") in ("look", "read", "do"):
                why_not = self.repeats_effect(cmd[0], action) or self.progress.already(
                    cmd[0], self.state_sig(cmd[0]), action
                )
                if why_not:
                    self.history.append(f"step {i}: {json.dumps(action)} -> not run: {why_not}")
                    run.steps.append(
                        Step(
                            i,
                            note,
                            action,
                            None,
                            f"not run: {why_not}",
                            0.0,
                            reply.input_tokens,
                            reply.output_tokens,
                        )
                    )
                    self.progress.refused_or_idle(i, action, f"not run: {why_not[:60]}")
                    if self.progress.exhausted:
                        run.status, run.reason = "no_progress", self.progress.reason()
                        return run
                    continue
            if isinstance(cmd, str):
                self.history.append(f"step {i}: {json.dumps(action)} -> not run: {cmd}")
                run.steps.append(
                    Step(i, note, action, None, cmd, 0.0, reply.input_tokens, reply.output_tokens)
                )
                continue
            surface, argv = cmd
            sig_before = self.state_sig(surface) if self.recovery else ""
            effects_before = self.effect_count() if self.recovery else 0
            if action["name"] == "done" and any(s.requirements for s in self.surfaces.values()):
                code, out = self._done_everywhere(argv[1])
            else:
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
                        (
                            "receipt",
                            "carried",
                            "not carried",
                            "paused",
                            "stopped",
                            "verifier",
                            "accepted",
                            "[",
                        )
                    )
                ),
                out[:160],
            )
            self.history.append(f"step {i} [{surface}] {' '.join(argv[:3])}: exit {code}: {summary[:220]}")
            if self.recovery:
                if action["name"] in ("look", "read", "do"):
                    self.progress.after(
                        i,
                        surface,
                        sig_before,
                        action,
                        self.state_sig(surface),
                        summary,
                        # M4: an effect is a new saved or submitted record, never a confirmed receipt alone
                        # (every navigation's receipt is confirmed; M3's X1 loops reset on each one)
                        confirmed_effect=self.effect_count() > effects_before,
                        new_values=tuple(v for v, _ in self.carried().values()),
                    )
                else:
                    self.progress.refused_or_idle(i, action, summary, progressed=code == 0)
                # an accepted done, a pause or an error keeps its own, more specific ending
                done_ok = action["name"] == "done" and code == 0
                if self.progress.exhausted and not done_ok and code not in (3, 7):
                    run.status, run.reason = "no_progress", self.progress.reason()
                    return run
            if code == 3:
                run.status, run.reason = "paused", summary
                return run
            if code == 7:
                run.status, run.reason = "error", summary
                return run
            if action["name"] == "done":
                if code == 0:
                    run.status, run.reason = "done", summary
                    # the answer the verifier judged, not the reference (Q19 smoke: "@HEADING" was scored)
                    run.answer = self.resolve(str(action.get("answer") or ""))
                    return run
                refusals += 1
                if refusals > self.max_done_refusals:
                    run.status, run.reason, run.answer = (
                        "done_unverified",
                        summary,
                        self.resolve(str(action.get("answer") or "")),
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
