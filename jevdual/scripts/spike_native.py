"""Native computer-use spike: Jev as System 1 over a Cua Driver window snapshot.

    uv run python scripts/spike_native.py --app Calculator --menu             # print the menu
    uv run python scripts/spike_native.py --app Calculator --script "All Clear,6,Multiply,7,Equals"
    uv run python scripts/spike_native.py --app Calculator --task "Compute 6 times 7" --steps 8 [--act]

``--script`` clicks labelled buttons in order without a model (proves dispatch + readback).
``--task`` runs the observe -> Jev -> arbiter -> act -> reobserve loop with the real
``JevPolicy`` and ``Arbiter`` (arbiter.toml floors); without ``--act`` it is a dry run that prints
each decision. Every step's Driver effect is printed verbatim. Output is a JSONL log when
``--log`` is given; nothing is sent anywhere but TypeSafe (the menu) when ``--task`` is used.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from jevdual.native import NativeBridge, NativeBridgeError, find_window, menu_from_snapshot


def _print_menu(nm) -> None:
    m = nm.menu
    print(
        f"{m.url} | {m.title!r} | snapshot {nm.snapshot_id} | {len(m.candidates)} candidates | omitted {m.omitted}"
    )
    print("text:", m.page_text[:300].replace("\n", " / "))
    for c in m.candidates:
        extra = " ".join(
            f"{k}={v!r}" for k, v in c.to_state().items() if k not in ("id", "label", "role", "operations")
        )
        print(f"  [{c.id:>3}] {c.role:<10} {c.label[:50]!r:<54} {','.join(c.operations):<12} {extra}")


async def run_script(bridge: NativeBridge, labels: list[str], log) -> None:
    for name in labels:
        nm = await bridge.observe()
        cand = next((c for c in nm.menu.candidates if c.label == name), None)
        if cand is None:
            print(f"!! no candidate labelled {name!r} on snapshot {nm.snapshot_id}")
            return
        eff = await bridge.act(nm, "click", cand.id)
        print(
            f"click [{cand.id}] {name!r}: {eff.effect} via {eff.route} {list(eff.evidence)} {eff.summary[:80]!r}"
        )
        log({"kind": "script", "label": name, **eff.to_record()})
    nm = await bridge.observe()
    print("display:", nm.menu.page_text.replace("\n", " / "))


async def run_task(bridge: NativeBridge, task: str, steps: int, act: bool, log) -> None:
    from jevdual.arbiter import Arbiter
    from jevdual.keys import load_keys
    from jevdual.policy import JevPolicy, StepContext
    from typesafe_sdk import AsyncTypeSafeClient

    present = load_keys()
    if not present.get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY missing (see jevdual.keys)")
        return
    arbiter = Arbiter.from_toml()
    agent = SimpleNamespace(step_systems={})
    recent: list[str] = []
    async with AsyncTypeSafeClient() as client:
        policy = JevPolicy(client)
        for step in range(1, steps + 1):
            nm = await bridge.observe()
            ctx = StepContext(task=task, recent_actions=tuple(recent[-8:]), step=step)
            t0 = time.perf_counter()
            decision = await policy.decide(nm.menu, ctx)
            ms = (time.perf_counter() - t0) * 1000
            target = nm.menu.candidate(decision.target) if decision.target is not None else None
            verdict = arbiter.judge(decision, nm.menu, ctx, agent)
            print(
                f"step {step}: {decision.operation} p={decision.operation_confidence:.2f}"
                + (f" -> [{target.id}] {target.label!r} p={decision.target_confidence:.2f}" if target else "")
                + f" | nouls {{{', '.join(f'{k}={v:.2f}' for k, v in decision.nouls.items())}}}"
                + f" | {verdict.kind}: {verdict.reason} | {ms:.0f} ms"
            )
            rec = {
                "kind": "step",
                "step": step,
                "snapshot": nm.snapshot_id,
                "decision": decision.to_trace(sum(nm.menu.omitted.values())).__dict__
                if hasattr(decision.to_trace(), "__dict__")
                else None,
                "verdict": {"kind": verdict.kind, "reason": verdict.reason},
                "latency_ms": ms,
            }
            if decision.operation in ("done", "blocked"):
                log(rec)
                print(
                    f"S1 says {decision.operation}; stopping. display: {nm.menu.page_text.replace(chr(10), ' / ')}"
                )
                return
            if verdict.kind != "act" or target is None:
                agent.step_systems[step] = "s2"
                log(rec)
                if not act:
                    continue
                print("  (would escalate to System 2; no System 2 in this spike, stopping)")
                return
            agent.step_systems[step] = "s1"
            if not act:
                log(rec)
                continue
            try:
                eff = await bridge.act(nm, decision.operation, target.id)
            except NativeBridgeError as e:
                print(f"  bridge refused: {e.reason}: {e}")
                log({**rec, "bridge_error": e.reason})
                continue
            recent.append(f"step {step}: {decision.operation} [{target.id}] {target.label!r} -> {eff.effect}")
            rec["effect"] = eff.to_record()
            log(rec)
            print(f"  effect: {eff.effect} via {eff.route} {list(eff.evidence)} {eff.summary[:80]!r}")
    nm = await bridge.observe()
    print("display:", nm.menu.page_text.replace("\n", " / "))


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", default="Calculator")
    ap.add_argument("--menu", action="store_true", help="print the menu and exit")
    ap.add_argument("--menu-bar", action="store_true", help="include menu bar items in the menu")
    ap.add_argument("--dump", help="write the raw snapshot JSON here (fixture recording)")
    ap.add_argument("--script", help="comma-separated button labels to click in order")
    ap.add_argument("--task")
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--act", action="store_true", help="execute System 1 decisions (default: dry run)")
    ap.add_argument("--log", help="JSONL log path")
    args = ap.parse_args()

    from cua_driver import CuaDriver

    log_path = Path(args.log) if args.log else None

    def log(rec: dict) -> None:
        if log_path:
            with log_path.open("a") as fh:
                fh.write(json.dumps(rec, default=str) + "\n")

    driver = CuaDriver.create()
    try:
        pid, window_id, title = await find_window(driver, args.app)
        print(f"{args.app}: pid {pid} window {window_id} {title!r}")
        bridge = NativeBridge(driver, pid, window_id)
        if args.dump:
            from cua_driver import GetWindowStateInput

            snap = await driver.get_window_state(
                GetWindowStateInput(
                    pid=pid,
                    window_id=window_id,
                    session=None,
                    query=None,
                    include_accessibility_tree=True,
                    include_screenshot=False,
                    screenshot_out_file=None,
                    max_elements=None,
                    max_depth=None,
                    max_dimension=None,
                )
            )

            def dump(o):
                if isinstance(o, (str, int, float, bool)) or o is None:
                    return o
                if isinstance(o, (list, tuple)):
                    return [dump(x) for x in o]
                if hasattr(o, "name") and hasattr(o, "value") and not hasattr(o, "element_index"):
                    return o.name
                return {
                    k: dump(getattr(o, k))
                    for k in dir(o)
                    if not k.startswith("_") and not callable(getattr(o, k))
                }

            Path(args.dump).write_text(json.dumps(dump(snap), indent=1))
            print("wrote", args.dump)
            _print_menu(menu_from_snapshot(snap, include_menu_bar=args.menu_bar))
            return
        if args.menu or not (args.script or args.task):
            _print_menu(await bridge.observe(include_menu_bar=args.menu_bar))
            return
        if args.script:
            await run_script(bridge, [s.strip() for s in args.script.split(",") if s.strip()], log)
        if args.task:
            await run_task(bridge, args.task, args.steps, args.act, log)
    finally:
        await driver.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
