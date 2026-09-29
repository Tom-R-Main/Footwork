"""Q19 driving harness (docs/experiments/Q19.md). The operator drives by hand; this keeps the count.

uv run python scripts/q19.py serve OUT                      # fixture server on :8767, GET record kept
uv run python scripts/q19.py setup TASK OUT                 # start state under ~/footwork-pilot/q19/<OUT name>/<TASK>
uv run python scripts/q19.py fw TASK OUT SURFACE -- ARGS..   # one footwork command, logged with exit and time
uv run python scripts/q19.py note TASK OUT KIND TEXT        # a friction event: misread|retry|dead_end|contradicted|vague_stop
uv run python scripts/q19.py check TASK OUT [--answer TEXT] # the oracle; writes the task's result
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals import q19
from evals.fixtures.server import serve

PORT = 8767
KINDS = ("misread", "retry", "dead_end", "contradicted", "vague_stop")


def scratch(out: Path, task: str) -> Path:
    return Path.home() / "footwork-pilot" / "q19" / out.name / task


def main(argv: list[str]) -> int:
    # Evaluation-only selection; the runtime and the default development set stay frozen.
    task_path = q19.TASKS
    if "--tasks" in argv:
        argv = list(argv)
        at = argv.index("--tasks")
        task_path = Path(argv[at + 1])
        del argv[at : at + 2]
    cmd, rest = argv[0], argv[1:]
    if cmd == "serve":
        out = Path(rest[0])
        out.mkdir(parents=True, exist_ok=True)
        base, stop = serve(PORT)
        print(f"serving {base}", flush=True)
        while True:
            (out / "gets.json").write_text(json.dumps(stop.recorder.gets(), indent=1))
            time.sleep(0.5)
    task, out = rest[0], Path(rest[1])
    tdir = out / task
    tdir.mkdir(parents=True, exist_ok=True)
    t = q19.load(task_path)[task]
    if cmd == "setup":
        q19.setup(t, scratch(out, task))
        gets = json.loads((out / "gets.json").read_text()) if (out / "gets.json").exists() else {}
        (tdir / "start.json").write_text(
            json.dumps({"t": time.time(), "gets": {k: len(v) for k, v in gets.items()}})
        )
        print(f"{task}: {t['task']}\nscratch: {scratch(out, task)}\nsurfaces: {json.dumps(t['surfaces'])}")
        return 0
    if cmd == "fw":
        surface, args = rest[2], rest[rest.index("--") + 1 :]
        args = [
            a.replace("{base}", f"http://127.0.0.1:{PORT}").replace("{scratch}", str(scratch(out, task)))
            for a in args
        ]
        t0 = time.perf_counter()
        p = subprocess.run(
            ["uv", "run", "footwork", *args, "--session", str(tdir / surface)],
            capture_output=True,
            text=True,
            check=False,
        )
        text = "\n".join(
            ln for ln in (p.stdout + p.stderr).splitlines() if not ln.startswith(("INFO ", "WARNING "))
        )
        with (tdir / "commands.jsonl").open("a") as fh:
            fh.write(
                json.dumps(
                    {
                        "t": time.time(),
                        "surface": surface,
                        "args": args,
                        "exit": p.returncode,
                        "s": round(time.perf_counter() - t0, 2),
                    }
                )
                + "\n"
            )
        print(text)
        return p.returncode
    if cmd == "note":
        kind, text = rest[2], " ".join(rest[3:])
        if kind not in KINDS:
            raise SystemExit(f"kind is one of {KINDS}")
        with (tdir / "friction.jsonl").open("a") as fh:
            fh.write(json.dumps({"t": time.time(), "kind": kind, "text": text}) + "\n")
        return 0
    if cmd == "check":
        answer = rest[rest.index("--answer") + 1] if "--answer" in rest else None
        start = json.loads((tdir / "start.json").read_text())
        gets_all = json.loads((out / "gets.json").read_text()) if (out / "gets.json").exists() else {}
        gets = {k: v[start["gets"].get(k, 0) :] for k, v in gets_all.items()}
        c = q19.check(t, answer=answer, gets=gets, scratch=scratch(out, task))
        cmds = (
            [json.loads(ln) for ln in (tdir / "commands.jsonl").read_text().splitlines()]
            if (tdir / "commands.jsonl").exists()
            else []
        )
        fr = (
            [json.loads(ln) for ln in (tdir / "friction.jsonl").read_text().splitlines()]
            if (tdir / "friction.jsonl").exists()
            else []
        )
        res = {
            "task": task,
            "oracle_ok": c.ok,
            "oracle": c.detail,
            "answer": answer,
            "commands": len(cmds),
            "wall_s": round((cmds[-1]["t"] if cmds else time.time()) - start["t"], 1),
            "friction": len(fr),
            "friction_by_kind": {k: sum(1 for f in fr if f["kind"] == k) for k in KINDS},
        }
        (tdir / "result.json").write_text(json.dumps(res, indent=1))
        print(json.dumps(res))
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
