"""Q10b stage 1: does the verifier accept each native task's own oracle end state?

    uv run python scripts/verifier_probe.py --split dev --calls 5 --out results/q10b-verifier-probe-<date>

For every task: launch, replay the oracle, observe the final window, then ask the verifier ``--calls``
times on that one menu (task text, requirements, the oracle's answer on answer tasks, no trajectory).
Writes ``probe.json`` (every call's band, complete and unmet probabilities) and ``probe.md``. A task
whose own oracle end state is not accepted on at least four of five calls is not fit for stage 2
until its requirement is rewritten (docs/experiments/Q10.md, amendment).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jevdual.native import NativeBridge
from jevdual.posture import ExecutionPolicy

from evals.native.runner import launch, run_oracle, task_folder, teardown
from evals.native.schema import SPLITS, load_tasks


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=sorted(SPLITS))
    ap.add_argument("--task", action="append")
    ap.add_argument("--calls", type=int, default=5)
    ap.add_argument("--out", default=f"results/q10b-verifier-probe-{time.strftime('%Y%m%d-%H%M%S')}")
    args = ap.parse_args()
    from cua_driver import CuaDriver
    from jevdual.keys import load_keys
    from jevdual.verify import Verifier
    from typesafe_sdk import AsyncTypeSafeClient

    if not load_keys().get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY missing")
    tasks = load_tasks(SPLITS[args.split])
    if args.task:
        tasks = [t for t in tasks if t.id in set(args.task)]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    driver = CuaDriver.create()
    try:
        async with AsyncTypeSafeClient() as client:
            verifier = Verifier(client)
            for task in tasks:
                run_id = f"probe-{time.strftime('%H%M%S')}"
                tmp = task_folder(task, run_id)
                pid = None
                try:
                    pid, window_id, _ = await launch(driver, task, tmp)
                    bridge = NativeBridge(driver, pid, window_id, policy=ExecutionPolicy("exclusive_desktop"))
                    executed, err = await run_oracle(bridge, task)
                    nm = await bridge.observe()
                    answer = next((e["text"] for e in executed if e.get("op") == "answer"), None)
                    # the oracle's steps as the trajectory a run would carry (Q10: the same display was accepted
                    # at 0.91 with System 2's lines in view and refused at 0.49 with System 1's)
                    trajectory = [
                        {
                            "step": i,
                            "url": nm.menu.url,
                            "actions": [
                                f"{e.get('op')}({e.get('label') or e.get('chord') or e.get('text') or ''})"
                            ],
                        }
                        for i, e in enumerate(executed, start=1)
                        if e.get("op") != "answer"
                    ]
                    calls = []
                    for _ in range(args.calls):
                        v = await verifier.verify(
                            task.task,
                            task.requirements,
                            nm.menu,
                            answer,
                            answer_expected=task.answer_expected,
                            trajectory=trajectory or None,
                        )
                        calls.append(v.to_trace())
                    bands = Counter(c["band"] for c in calls)
                    rows.append(
                        {
                            "task": task.id,
                            "oracle_error": err,
                            "window_text": nm.menu.page_text[:300],
                            "answer": answer,
                            "requirements": list(task.requirements),
                            "calls": calls,
                            "bands": dict(bands),
                            "accept_rate": bands.get("accept", 0) / max(1, len(calls)),
                        }
                    )
                    print(
                        f"{task.id}: oracle {'ok' if not err else err[:50]} | bands {dict(bands)} | text {nm.menu.page_text[:60]!r}"
                    )
                except Exception as exc:  # noqa: BLE001 - one task's failure is a row, not a lost probe
                    rows.append({"task": task.id, "error": f"{type(exc).__name__}: {exc}"[:200]})
                    print(f"{task.id}: ERROR {exc}")
                finally:
                    await teardown(driver, pid, task)
                (out / "probe.json").write_text(json.dumps(rows, indent=1))
    finally:
        await driver.shutdown()
    lines = [
        f"# Q10b stage 1: verifier on oracle end states ({args.split}, {args.calls} calls per task)\n",
        "| task | oracle | accept | verify | reject | complete (mean) | max unmet (mean) | window text |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['task']} | error | | | | | | {r['error'][:60]} |")
            continue
        b = r["bands"]
        comp = sum(c.get("complete", 0) for c in r["calls"]) / len(r["calls"])
        unmet = sum(
            max((c.get("unmet_effective") or c.get("unmet") or {}).values() or [0]) for c in r["calls"]
        ) / len(r["calls"])
        lines.append(
            f"| {r['task']} | {'ok' if not r['oracle_error'] else 'FAIL'} | {b.get('accept', 0)} | {b.get('verify', 0)} | {b.get('reject', 0)} | {comp:.2f} | {unmet:.2f} | {r['window_text'][:50].replace(chr(10), ' / ')!r} |"
        )
    (out / "probe.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
