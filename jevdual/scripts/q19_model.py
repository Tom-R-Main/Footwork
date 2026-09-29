"""Q19 (docs/experiments/Q19.md): tasks from a Q19 task file driven by the model through
``jevdual.crossloop``, one run each, the oracle read right after the run (TextEdit autosaves in place, so
a later read can make a stopped save task look done; notebook U49). Acts on the desktop.

    uv run python scripts/q19_model.py --tasks evals/tasks/q19-dev.yaml --out results/q19-model-smoke [--task D05-ticket ..]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jevdual.crossloop import CrossLoop, Surface, to_json
from jevdual.desktop_s2 import meta_chat_from_env
from jevdual.keys import load_keys

from evals import q19
from evals.fixtures.server import serve

PORT = 8767  # the operator's fixture port: task files name {base}
MUSE_IN, MUSE_OUT = 0.10, 0.20  # USD per million tokens, Muse Spark contributor rates
SECRET_NOTE = " Where the task names a secret in braces, such as {{{name}}}, type it exactly so; the harness fills it in."


def fill(text: str, base: str, scratch: Path) -> str:
    return text.replace("{base}", base).replace("{scratch}", str(scratch)).replace("{run}", scratch.name)


def surfaces(t: dict[str, Any], base: str, scratch: Path) -> list[Surface]:
    out = []
    for s in t["surfaces"]:
        out.append(
            Surface(
                s["name"],
                "browser" if s["kind"] == "browser" else "app",
                app=s.get("app", ""),
                window=fill(s.get("window", ""), base, scratch),
                url=fill(s.get("url", ""), base, scratch),
                authorize=tuple(s.get("authorize") or ()),
            )
        )
    return out


def outcome(status: str, oracle_ok: bool) -> str:
    """proven: an accepted done the oracle confirms; untruthful: an accepted done the oracle fails;
    unaccepted: the verifier would not accept the done (the model claimed, the harness did not); stopped:
    a pause, stop or budget, ``_effect_present`` when the oracle finds the effect anyway. Whether a stop's
    reason is the right one is judged by hand from the run."""
    if status == "done":
        return "proven" if oracle_ok else "untruthful"
    if status == "done_unverified":
        return "unaccepted_effect_present" if oracle_ok else "unaccepted"
    return "stopped_effect_present" if oracle_ok else "stopped"


async def main(path: Path, ids: list[str] | None, out: Path, max_steps: int) -> None:
    load_keys()
    chat = meta_chat_from_env()
    if chat is None:
        raise SystemExit("MODEL_API_KEY missing")
    tasks = q19.load(path)
    base, stop = serve(PORT)
    rows = []
    try:
        for tid in ids or list(tasks):
            t = tasks[tid]
            scratch = Path.home() / "footwork-pilot" / "q19" / out.name / tid
            q19.setup(t, scratch)
            text = fill(t["task"], base, scratch)
            for name, value in (t.get("secrets") or {}).items():
                os.environ[f"FOOTWORK_SECRET_{name}"] = str(value)
                text += SECRET_NOTE.format(name=name)
            run_dir = out / tid
            before = {k: len(v) for k, v in stop.recorder.gets().items()}
            t0 = time.perf_counter()
            run = await CrossLoop(text, surfaces(t, base, scratch), chat, run_dir, max_steps=max_steps).run()
            wall = time.perf_counter() - t0
            gets = {k: v[before.get(k, 0) :] for k, v in stop.recorder.gets().items()}
            c = q19.check(t, answer=run.answer, gets=gets, scratch=scratch)
            row = {
                "task": tid,
                "expect": t.get("expect"),
                "status": run.status,
                "reason": run.reason[:400],
                "answer": run.answer,
                "oracle_ok": c.ok,
                "oracle": c.detail,
                "outcome": outcome(run.status, c.ok),
                "steps": len(run.steps),
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "cost_usd": run.input_tokens / 1e6 * MUSE_IN + run.output_tokens / 1e6 * MUSE_OUT,
                "wall_s": round(wall, 1),
            }
            rows.append(row)
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "run.json").write_text(json.dumps(to_json(run), indent=1, default=str))
            (out / "results.json").write_text(json.dumps(rows, indent=1))
            print(
                f"{tid}: {run.status} ({run.reason[:80]}); oracle {'confirmed' if c.ok else 'failed'}: "
                f"{c.detail[:90]} -> {row['outcome']}",
                flush=True,
            )
    finally:
        stop()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, default=q19.TASKS)
    ap.add_argument("--task", action="append")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-steps", type=int, default=20)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    asyncio.run(main(a.tasks, a.task, a.out, a.max_steps))
