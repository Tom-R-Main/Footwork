"""Run the coexistence suite (Q15, docs/experiments/Q15.md) and write its results.

    FOOTWORK_LIVE=1 uv run python scripts/q15_coexistence.py --reps 3 --out results/q15-coexistence
    FOOTWORK_LIVE=1 uv run python scripts/q15_coexistence.py --cases C1 --reps 1 --out runs/q15-smoke

The suite takes the keyboard: it refuses to start unless the machine has been idle for
FOOTWORK_Q15_IDLE_S seconds (default 20). A contaminated case (someone at the machine) is rerun up to
twice and never counted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from jevdual.coexist import CASES, GUARD_IDLE_S, NotIdle, idle_seconds, require_idle, run_case


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=",".join(CASES))
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--wait", type=float, default=0.0, help="wait up to this many seconds for the idle guard")
    args = ap.parse_args()
    if os.environ.get("FOOTWORK_LIVE") != "1":
        print("set FOOTWORK_LIVE=1: the suite types on this machine's keyboard", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + args.wait
    while True:
        try:
            require_idle(GUARD_IDLE_S)
            break
        except NotIdle as exc:
            if time.time() > deadline:
                print(f"not starting: {exc}", file=sys.stderr)
                return 3
            await asyncio.sleep(2.0)
    keys = [k.strip() for k in args.cases.split(",") if k.strip()]
    rows = []
    with (out / "cases.jsonl").open("a") as fh:
        for rep in range(1, args.reps + 1):
            for key in keys:
                for attempt in range(1, 4):
                    while idle_seconds() < 1.0:
                        await asyncio.sleep(0.5)
                    work = Path(tempfile.mkdtemp(prefix=f"q15-{key}-"))
                    t0 = time.perf_counter()
                    r = await run_case(key, work)
                    rec = {
                        "rep": rep,
                        "attempt": attempt,
                        "seconds": round(time.perf_counter() - t0, 1),
                        **r.to_record(),
                    }
                    fh.write(json.dumps(rec, default=str) + "\n")
                    fh.flush()
                    failed = [k for k, v in r.checks.items() if not v]
                    status = "PASS" if r.passed else ("CONTAMINATED" if r.contaminated else "FAIL")
                    print(
                        f"rep {rep} {key} attempt {attempt}: {status} in {rec['seconds']}s"
                        + (f" failed={failed}" if failed else "")
                        + (f" error={r.error}" if r.error else "")
                        + (f" contaminated={r.contaminated}" if r.contaminated else ""),
                        flush=True,
                    )
                    if r.contaminated is None:
                        rows.append(rec)
                        break
                    # someone is at the machine: wait for the full guard again before the retry
                    while idle_seconds() < GUARD_IDLE_S:
                        await asyncio.sleep(2.0)
    passed = sum(1 for r in rows if r["passed"])
    lines = [f"# Q15 run {time.strftime('%Y-%m-%d %H:%M')}", "", f"{passed} of {len(rows)} cases passed", ""]
    lines.append("| rep | case | passed | failed checks |")
    lines.append("|---|---|---|---|")
    for r in rows:
        bad = ", ".join(k for k, v in r["checks"].items() if not v) or ("error: " + r["error"] if r["error"] else "")
        lines.append(f"| {r['rep']} | {r['case']} | {'yes' if r['passed'] else 'no'} | {bad} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
