"""Run a released author task set once, with immediate independent GET/POST/file oracles.

Stop explanations require adjudication; end-state preservation alone is not a pass.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "python"), str(ROOT)]

from jevdual.crossloop import CrossLoop, Surface, to_json
from jevdual.desktop_s2 import meta_chat_from_env
from jevdual.keys import load_keys

from evals import q19
from evals.fixtures.server import serve
from evals.m_sealed import check, frozen_runtime, grade, manifest

PORT = 0  # its own fixture server, beside the operator's on 8767; tasks name {base}
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


async def main(path: Path, ids: list[str] | None, out: Path, max_steps: int, recovery: bool = False) -> None:
    load_keys()
    chat = meta_chat_from_env()
    if chat is None:
        raise SystemExit("MODEL_API_KEY missing")
    tasks = q19.load(path)
    base, stop = serve(PORT)
    # Each measurement has its own fresh output and server.
    rows = []
    try:
        for tid in ids or list(tasks):
            t = tasks[tid]
            scratch = Path.home() / "footwork-pilot" / "m-independent" / out.name / tid
            try:
                q19.setup(t, scratch)
            except q19.SetupError as e:
                # a trial never starts from a start state it could not establish (review of 2026-09-29)
                rows.append({"task": tid, "status": "setup_failed", "reason": str(e), "oracle_ok": None})
                (out / "results.json").write_text(json.dumps(rows, indent=1))
                print(f"{tid}: not started: {e}", flush=True)
                continue
            text = fill(t["task"], base, scratch)
            if "scratch" in text and str(scratch) not in text:
                text += f" (The scratch folder is {scratch}.)"
            for name, value in (t.get("secrets") or {}).items():
                os.environ[f"FOOTWORK_SECRET_{name}"] = str(value)
                text += SECRET_NOTE.format(name=name)
            run_dir = out / tid
            before = {k: len(v) for k, v in stop.recorder.gets().items()}
            before_posts = {k: len(v) for k, v in stop.recorder.snapshot().items()}
            before_files = q19.file_hashes(scratch)
            t0 = time.perf_counter()
            run = await CrossLoop(
                text,
                surfaces(t, base, scratch),
                chat,
                run_dir,
                max_steps=min(max_steps, t["max_steps"]),
                recovery=recovery,
            ).run()
            wall = time.perf_counter() - t0
            gets = {k: v[before.get(k, 0) :] for k, v in stop.recorder.gets().items()}
            posts = {k: v[before_posts.get(k, 0) :] for k, v in stop.recorder.snapshot().items()}
            c = check(t, answer=run.answer, gets=gets, posts=posts, scratch=scratch, before=before_files)
            t_oracle, files = time.time(), q19.file_hashes(scratch)
            row = {
                "task": tid,
                "expect": t.get("expect"),
                "status": run.status,
                "reason": run.reason,
                "answer": run.answer,
                "oracle_ok": c.ok,
                "oracle": c.detail,
                "outcome": outcome(run.status, c.ok),
                "steps": len(run.steps),
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "cost_usd": run.input_tokens / 1e6 * MUSE_IN + run.output_tokens / 1e6 * MUSE_OUT,
                "wall_s": round(wall, 1),
                "t_oracle": t_oracle,
                "arm": {"recovery": recovery, "completion": os.environ.get("FOOTWORK_COMPLETION", "default")},
                "files": files,
                "gets": gets,
                "posts": posts,
                "before_files": before_files,
                "author_grade": grade(t, run.status, c.ok, len(run.steps)),
                "stop_adjudication": t.get("stop_adjudication"),
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
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--task", action="append")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--recovery", action="store_true", help="M3: bounded recovery in the loop")
    ap.add_argument("--completion", choices=["default", "effect_evidence"], default="default")
    a = ap.parse_args()
    if a.out.exists():
        ap.error("output must not exist; interrupted measurements must not be retried")
    sha = frozen_runtime(ROOT, a.candidate)
    os.environ["FOOTWORK_COMPLETION"] = a.completion
    a.out.mkdir(parents=True)
    payload = [a.tasks, *sorted((ROOT / "evals" / "fixtures" / "site").glob("msealed-*.html"))]
    (a.out / "started.json").write_text(
        json.dumps({"candidate": sha, "payload": manifest(ROOT, payload)}, indent=2)
    )
    asyncio.run(main(a.tasks, a.task, a.out, a.max_steps, a.recovery))
    (a.out / "closed").write_text("One measurement. Stops require reason adjudication.\n")
