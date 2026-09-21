"""Offline arbiter threshold sweep (task E1).

Re-judges the System 1 decisions recorded in a run's traces under candidate
ArbiterPolicy settings. It costs no model calls and no browser time, so it is
the cheap first pass: it tells you how many recorded steps each setting would
have escalated, confirmed or acted on, split by whether the task passed. It
cannot tell you what System 2 would then have done; a chosen setting still
needs one confirmation run of the dual arm.

Approximations, stated so they are not mistaken for measurements: traces
carry no candidate labels, so the destructive keyword rule cannot fire (the
destructive noul still does); the no-effect rule is disabled offline because it needs menus.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from jevdual.arbiter import Arbiter, ArbiterPolicy
from jevdual.menu import Menu
from jevdual.policy import Decision, StepContext
from jevdual.trace import StepRecord, read_trace


def decision_from_record(rec: StepRecord) -> Decision | None:
    d = rec.decision
    if d is None or d.operation is None:
        return None
    op = d.operation
    tgt = d.target
    target_probs = {int(k): v for k, v in (tgt.probabilities if tgt else {}).items()}
    target = int(tgt.choice) if tgt and tgt.choice not in (None, "") else None
    alternates = tuple(k for k, _ in sorted(target_probs.items(), key=lambda kv: -kv[1]) if k != target)
    return Decision(
        operation=op.choice,
        operation_confidence=op.confidence or 0.0,
        operation_probabilities=dict(op.probabilities),
        target=target,
        target_confidence=(tgt.confidence if tgt else None),
        target_probabilities=target_probs,
        alternates=alternates,
        nouls=dict(d.nouls),
        model=d.model or "",
        request_tokens=d.request_tokens,
        latency_ms=d.latency_ms or 0.0,
    )


def replay_trace(steps: list[StepRecord], policy: ArbiterPolicy) -> list[tuple[int, str, str]]:
    """(step, verdict kind, rule) per recorded S1 decision under ``policy``."""
    arb = Arbiter(policy)
    agent = SimpleNamespace(step_systems={}, s1_records={}, history=SimpleNamespace(history=[]), task="")
    out = []
    prev_url = None
    for rec in steps:
        agent.step_systems[rec.step] = rec.system
        dec = decision_from_record(rec)
        if dec is None:
            continue
        url = rec.url_after or prev_url or ""
        menu = Menu(url=url, title="", page_text=url, candidates=(), by_operation={})
        ctx = StepContext(task="", step=rec.step)
        try:
            v = arb.judge(dec, menu, ctx, agent)
            kind, rule = v.kind, v.reason.split(":")[0]
        except Exception as exc:  # noqa: BLE001 - a rule that needs data the trace lacks is reported, not hidden
            kind, rule = "error", type(exc).__name__
        out.append((rec.step, kind, rule))
        prev_url = url
    return out


GRID: dict[str, list[float]] = {
    "act_operation_confidence": [0.45, 0.55, 0.65],
    "act_target_confidence": [0.35, 0.45, 0.55],
    "goal_done_escalate": [0.75, 0.85, 0.95],
    "needs_reasoning_escalate": [0.5, 0.6, 0.7],
}


def sweep(run_dir: Path) -> str:
    results = json.loads((run_dir / "results.json").read_text())
    base = ArbiterPolicy.from_toml() if hasattr(ArbiterPolicy, "from_toml") else ArbiterPolicy()
    # Traces carry no candidates, so the no-effect diff would fire on every same-url step; disable it offline.
    base = replace(base, no_effect_steps=10**6)
    traces = []
    for r in results:
        p = Path(r["trace_path"])
        if not p.exists():
            continue
        _, steps = read_trace(p)
        if any(s.decision for s in steps):
            traces.append((r, steps))
    lines = [f"# Arbiter sweep over {run_dir.name} ({len(traces)} traces with S1 decisions)", "",
             "Counts are recorded S1 steps re-judged offline; 'on failed tasks' means the task did not pass in this run.", "",
             "| setting | value | act | escalate | confirm | retry | escalations on passed tasks | escalations on failed tasks | top rules |",
             "|---|---|---|---|---|---|---|---|---|"]
    variants: list[tuple[str, float, ArbiterPolicy]] = [("baseline", 0.0, base)]
    for name, values in GRID.items():
        for v in values:
            if getattr(base, name) == v:
                continue
            variants.append((name, v, replace(base, **{name: v})))
    for name, value, pol in variants:
        kinds: Counter[str] = Counter()
        rules: Counter[str] = Counter()
        esc_pass = esc_fail = 0
        for r, steps in traces:
            for _, kind, rule in replay_trace(steps, pol):
                kinds[kind] += 1
                if kind != "act":
                    rules[rule] += 1
                    if r["passed"]:
                        esc_pass += 1
                    else:
                        esc_fail += 1
        top = ", ".join(f"{k} {v}" for k, v in rules.most_common(3))
        lines.append(f"| {name} | {value if name != 'baseline' else ''} | {kinds['act']} | {kinds['escalate']} | {kinds['confirm']} | {kinds['retry_alternate']} | {esc_pass} | {esc_fail} | {top} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> None:
    run_dir = Path(argv[0])
    text = sweep(run_dir)
    (run_dir / "sweep.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(sys.argv[1:])
