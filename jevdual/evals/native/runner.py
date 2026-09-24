"""Native eval runner: one app at a time through Cua Driver, results in the browser rig's layout.

    uv run python -m evals.native.runner --split dev --arm s1_only --arm dual --out results/native-<ts>
    uv run python -m evals.native.runner --split dev --oracle          # admit tasks: every oracle must pass

Arms: ``s1_only`` (System 1 and the arbiter; an escalation ends the run), ``dual`` (escalations go
to System 2 behind the gate), ``guarded`` (System 2 decides every step behind the same gate).
Each task run gets a private folder under ``$TMPDIR/jevdual-native``; the app is launched with
the task's files, bound by window title, run, graded by its predicate on observed state, and
killed when the task says so. Traces are schema-2 JSONL under ``<out>/traces``; ``results.json``,
``summary.json`` and ``report.md`` come from ``evals.report`` unchanged.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from jevdual.native import NativeBridge, NativeBridgeError, NativeMenu
from jevdual.trace import RunHeader, TraceWriter

from evals.native.predicates import NativeEndState, evaluate
from evals.native.schema import SPLITS, NativeTask, load_tasks, parse_expect
from evals.report import TaskResult, write_results

log = logging.getLogger("evals.native")

Arm = Literal["s1_only", "dual", "guarded"]
ARMS: tuple[Arm, ...] = ("s1_only", "dual", "guarded")
BACKEND = "cua-driver"
JEV_USD_PER_MTOK = 0.042
JEV_TOKENS_PER_CALL = 2400
MUSE_IN_PER_MTOK, MUSE_OUT_PER_MTOK = 0.10, 0.20
LAUNCH_TIMEOUT_S = 20.0


@dataclass
class Deps:
    """What a run needs beyond the Driver: built once per split by :func:`default_deps`, or faked."""

    policy_factory: Any  # (task) -> policy with decide()
    verifier_factory: Any  # (task) -> ArbiterHook-like or None
    s2_factory: Any  # (task, verifier) -> SystemTwo or None
    arbiter_factory: Any  # () -> Arbiter
    jev_model: str | None = None
    llm_model: str | None = None


def task_folder(task: NativeTask, run_id: str) -> Path:
    root = Path(os.environ.get("TMPDIR", "/tmp")) / "jevdual-native"
    folder = root / f"{task.id}-{run_id}"
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in task.files.items():
        (folder / name).write_text(content)
    return folder


async def launch(driver: Any, task: NativeTask, tmp: Path) -> tuple[int, int, str]:
    """Launch a fresh instance of the app with the task's files and bind its window; ``(pid, window_id,
    title)``. A new instance per task run keeps background keyboard delivery unambiguous (the Driver
    refuses process-scoped key presses when the pid owns several eligible windows) and isolates state."""
    from jevdual.native import find_window_for_pid

    urls = [u.replace("{tmp}", str(tmp)) for u in task.open]
    args: dict[str, Any] = {"bundle_id": task.bundle_id, "creates_new_application_instance": True}
    if urls:
        args["urls"] = urls
    res = await driver.call_tool("launch_app", json.dumps(args))
    try:
        pid = int(json.loads(res.structured_json or "{}").get("pid") or 0)
    except (ValueError, TypeError, AttributeError):
        pid = 0
    if not pid:
        raise RuntimeError(f"{task.id}: launch_app returned no pid: {(getattr(res, 'text', '') or '')[:120]}")
    deadline = time.monotonic() + LAUNCH_TIMEOUT_S
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            window_id, title = await find_window_for_pid(driver, pid, title_contains=task.window_title)
            return pid, window_id, title
        except LookupError as exc:
            last = exc
            await asyncio.sleep(0.5)
    raise RuntimeError(f"{task.id}: window not found after {LAUNCH_TIMEOUT_S:.0f}s: {last}")


async def teardown(driver: Any, pid: int | None, task: NativeTask) -> None:
    if pid is None or not task.relaunch:
        return
    try:
        await driver.call_tool("kill_app", json.dumps({"pid": pid}))
    except Exception as exc:  # noqa: BLE001 - teardown never fails a result
        log.warning("kill_app %s failed: %s", pid, exc)


# ---- oracle -------------------------------------------------------------------------


def find_candidate(nm: NativeMenu, spec: str) -> Any:
    """A candidate by exact label, then case-insensitive label, then role, then label substring."""
    cands = nm.menu.candidates
    for c in cands:
        if c.label == spec:
            return c
    low = spec.casefold()
    for c in cands:
        if c.label.casefold() == low:
            return c
    for c in cands:
        if c.role == low:
            return c
    for c in cands:
        if low in c.label.casefold():
            return c
    return None


async def run_oracle(bridge: NativeBridge, task: NativeTask) -> tuple[list[dict[str, Any]], str | None]:
    """Replay ``task.solve`` through the bridge. Returns the executed steps and an error, if any."""
    steps: list[dict[str, Any]] = []
    for line in task.solve:
        parts = line.split(" ", 1)
        op = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        nm = await bridge.observe()
        if op == "wait":
            await asyncio.sleep(float(rest or "1"))
            steps.append({"op": "wait", "seconds": float(rest or "1")})
            continue
        if op == "key":
            chord = rest.strip().split("+")
            eff = await bridge.key(nm, chord[-1], chord[:-1])
            steps.append({"op": "key", "chord": rest, "effect": eff.effect, "summary": eff.summary[:120]})
            if eff.effect == "refused":
                return steps, f"oracle: key {rest!r} refused: {eff.summary[:80]}"
            continue
        if op == "answer":
            steps.append({"op": "answer", "text": rest})
            continue
        if op == "hotkey":
            eff = await bridge.hotkey(nm, rest.strip().split("+"))
            steps.append({"op": "hotkey", "chord": rest, "effect": eff.effect, "summary": eff.summary[:120]})
            if eff.effect == "refused":
                return steps, f"oracle: hotkey {rest!r} refused: {eff.summary[:80]}"
            continue
        if op == "menu":
            path = [x.strip() for x in rest.split(">")]
            eff = await bridge.menu(nm, path)
            steps.append({"op": "menu", "path": path, "effect": eff.effect, "summary": eff.summary[:120]})
            if eff.effect == "refused":
                return steps, f"oracle: menu {rest!r} refused: {eff.summary[:80]}"
            continue
        if op in ("type", "append"):
            # "type <label> <text>": the label is the first token or the first candidate label prefix
            label, text = _split_type(rest, nm)
            cand = find_candidate(nm, label)
            if cand is None:
                return steps, f"oracle: no candidate for {label!r}"
            eff = await bridge.act(nm, op, cand.id, text.replace("\\n", "\n"))
        elif op in ("click", "enter"):
            cand = find_candidate(nm, rest.strip())
            if cand is None:
                return steps, f"oracle: no candidate for {rest.strip()!r}"
            try:
                eff = await bridge.act(nm, op, cand.id)
            except NativeBridgeError as exc:
                return steps, f"oracle: {exc.reason}: {exc}"
        else:
            return steps, f"oracle: unknown op {op!r}"
        steps.append({"op": op, "label": cand.label, "id": cand.id, "effect": eff.effect})
        if eff.effect == "refused":
            return steps, f"oracle: {op} on {cand.label!r} refused: {eff.summary[:80]}"
    return steps, None


def _split_type(rest: str, nm: NativeMenu) -> tuple[str, str]:
    """``<label> <text>``: the longest candidate label or role that prefixes ``rest`` wins."""
    best = ""
    for c in nm.menu.candidates:
        for key in (c.label, c.role):
            if key and rest.startswith(key + " ") and len(key) > len(best):
                best = key
    if best:
        return best, rest[len(best) + 1 :]
    label, _, text = rest.partition(" ")
    return label, text


# ---- one task run -------------------------------------------------------------------


def _end_state(agent: Any, run: Any, tmp: Path, expect_status: str | None) -> NativeEndState:
    clicked = tuple(
        str(a.params.get("label") or "") for o in agent.steps for a in o.executed if a.name == "click"
    )
    text = run.final_menu.menu.page_text if run.final_menu is not None else ""
    return NativeEndState(
        window_text=text,
        answer=run.answer,
        clicked_labels=clicked,
        is_done=run.is_done,
        tmp=tmp,
        expect_status=expect_status,
    )


async def _expect_status(bridge: NativeBridge, task: NativeTask) -> str | None:
    if task.predicate.kind != "expect":
        return None
    from cua_driver import ElementPredicate, ElementSelector, StatePredicate

    spec = parse_expect(task.predicate.value)
    sel = ElementSelector(role=spec.get("role"), label_contains=spec.get("label_contains"))
    pred = ElementPredicate(
        selector=sel,
        exists=True,
        value_equals=spec.get("value_equals"),
        enabled=(spec["enabled"] == "true") if "enabled" in spec else None,
        selected=(spec["selected"] == "true") if "selected" in spec else None,
    )
    try:
        status, _ = await bridge.verify([StatePredicate(element=pred, window=None)], timeout_ms=2000)
    except Exception as exc:  # noqa: BLE001 - an unknown verification is an unknown, never a pass
        log.warning("verify_state failed: %s", exc)
        return "unknown"
    return status


async def run_task(
    driver: Any,
    task: NativeTask,
    arm: Arm | Literal["oracle"],
    out_dir: Path,
    deps: Deps | None,
    *,
    max_steps: int = 25,
) -> TaskResult:
    run_id = f"{task.id}-{arm}-{uuid.uuid4().hex[:8]}"
    tmp = task_folder(task, run_id)
    (out_dir / "traces").mkdir(parents=True, exist_ok=True)
    trace_path = out_dir / "traces" / f"{run_id}.jsonl"
    t0 = time.perf_counter()
    pid: int | None = None
    error: str | None = None
    passed = False
    paused = False
    is_done = False
    answer: str | None = None
    steps = s1 = s2 = llm_calls = jev_calls = 0
    llm_in = llm_out = jev_tokens = 0
    gate_judgments = 0
    final_text = ""
    try:
        pid, window_id, _title = await launch(driver, task, tmp)
        bridge = NativeBridge(driver, pid, window_id)
        if arm == "oracle":
            executed, error = await run_oracle(bridge, task)
            steps = len(executed)
            nm = await bridge.observe()
            final_text = nm.menu.page_text
            end = NativeEndState(
                window_text=final_text,
                answer=next((e["text"] for e in executed if e.get("op") == "answer"), None),
                clicked_labels=tuple(str(e.get("label", "")) for e in executed if e.get("op") == "click"),
                is_done=error is None,
                tmp=tmp,
                expect_status=await _expect_status(bridge, task),
            )
            passed = error is None and evaluate(task.predicate, end)
            trace_path.write_text(json.dumps({"kind": "oracle", "run_id": run_id, "steps": executed}) + "\n")
        else:
            assert deps is not None
            from jevdual.arbiter import ArbiterPolicy
            from jevdual.authorize import Authorizer
            from jevdual.desktop import NativeAgent
            from jevdual.secrets import SecretStore

            store = SecretStore({f"app://{task.app}": dict(task.secrets)}) if task.secrets else None
            policy = deps.policy_factory(task)
            verifier = deps.verifier_factory(task)
            system_two = deps.s2_factory(task, verifier) if arm in ("dual", "guarded") else None
            redactor = store.redactor() if store is not None else None
            with TraceWriter(trace_path, redactor=redactor) as trace:
                trace.write(
                    RunHeader(
                        run_id=run_id,
                        task=task.task,
                        arm=arm,
                        backend=BACKEND,
                        browser_use_version="n/a",
                        patches={"native": True},
                        jev_model=deps.jev_model,
                        llm_model=deps.llm_model if system_two is not None else None,
                    )
                )
                agent = NativeAgent(
                    bridge,
                    policy,
                    task=task.task,
                    requirements=task.requirements,
                    arbiter=deps.arbiter_factory(),
                    verifier=verifier,
                    secrets=store,
                    s2=system_two,
                    trace=trace,
                    run_id=run_id,
                    max_steps=max_steps,
                    answer_expected=task.answer_expected,
                    authorizer=Authorizer(
                        policy=ArbiterPolicy.from_toml(),
                        authorized_actions=task.authorized_actions,
                        authorize_all=task.authorize and not task.authorized_actions,
                        judge=(
                            getattr(getattr(verifier, "verifier", None), "judge_destructive", None)
                            if system_two is not None
                            else None
                        ),
                    ),
                    s1_enabled=(arm != "guarded"),
                )
                run = await agent.run()
            steps = len(agent.steps)
            s1 = sum(1 for o in agent.steps if o.system == "s1")
            s2 = sum(1 for o in agent.steps if o.system == "s2")
            llm_calls = getattr(agent.s2, "calls", 0) if agent.s2 is not None else 0
            gate_judgments = len(agent.authorizer.judgments)
            jev_calls = agent.jev_calls
            jev_tokens = sum((o.decision.request_tokens or 0) for o in agent.steps if o.decision is not None)
            llm_in = sum(o.llm_input_tokens for o in agent.steps)
            llm_out = sum(o.llm_output_tokens for o in agent.steps)
            is_done = run.is_done
            answer = run.answer
            paused = run.status == "paused"
            final_text = run.final_menu.menu.page_text if run.final_menu is not None else ""
            end = _end_state(agent, run, tmp, await _expect_status(bridge, task))
            passed = evaluate(task.predicate, end)
            if run.status in ("escalated", "blocked", "budget_exhausted", "error"):
                error = f"{run.status}: {run.reason[:160]}"
            if redactor is not None:
                final_text = redactor(final_text)
                answer = redactor(answer) if answer else answer
                error = redactor(error) if error else error
    except Exception as exc:
        log.exception("%s on %s crashed", task.id, arm)
        error = f"crash: {type(exc).__name__}: {exc}"[:300]
    finally:
        await teardown(driver, pid, task)
        if not os.environ.get("JEVDUAL_KEEP_TMP"):
            shutil.rmtree(tmp, ignore_errors=True)
    wall = time.perf_counter() - t0
    jev_cost = (jev_tokens or jev_calls * JEV_TOKENS_PER_CALL) / 1e6 * JEV_USD_PER_MTOK
    return TaskResult(
        task_id=task.id,
        arm=arm if arm != "oracle" else "s1_only",
        passed=passed,
        steps=steps,
        s1_steps=s1,
        s2_steps=s2,
        llm_calls=llm_calls,
        jev_calls=jev_calls,
        llm_tokens=llm_in + llm_out,
        llm_cost_usd=llm_in / 1e6 * MUSE_IN_PER_MTOK + llm_out / 1e6 * MUSE_OUT_PER_MTOK,
        jev_cost_usd=jev_cost,
        wall_s=wall,
        is_done=is_done,
        final_url=f"app://{task.app}",
        answer=answer,
        error=error,
        tags=tuple(task.tags) + (("oracle",) if arm == "oracle" else ()),
        trace_path=str(trace_path),
        paused=paused,
        gate_judgments=gate_judgments,
    )


# ---- split ---------------------------------------------------------------------------


def load_partial(out_dir: Path) -> list[TaskResult]:
    """Rows already in ``out_dir/results.json`` (for ``--resume``)."""
    path = out_dir / "results.json"
    if not path.is_file():
        return []
    out = []
    for r in json.loads(path.read_text()):
        r["tags"] = tuple(r.get("tags") or ())
        out.append(TaskResult(**r))
    return out


def default_deps(llm: str | None, client: Any) -> Deps:
    from jevdual.arbiter import Arbiter
    from jevdual.desktop_s2 import NativeS2, meta_chat_from_env
    from jevdual.policy import JEV_MODEL, JevPolicy
    from jevdual.verify import ArbiterHook, Verifier

    chat = meta_chat_from_env() if llm not in (None, "none") else None

    def s2_factory(task: NativeTask, verifier: Any):
        if chat is None:
            raise SystemExit("MODEL_API_KEY missing for a System 2 arm; run with --llm none for s1_only")
        return NativeS2(chat)

    return Deps(
        policy_factory=lambda task: JevPolicy(client),
        verifier_factory=lambda task: ArbiterHook(
            Verifier(client), task.requirements, answer_expected=task.answer_expected, use_trajectory=False
        ),
        s2_factory=s2_factory,
        arbiter_factory=Arbiter.from_toml,
        jev_model=JEV_MODEL,
        llm_model=getattr(chat, "model", None),
    )


async def run_split(
    split: str,
    arms: tuple[str, ...],
    out_dir: Path,
    *,
    deps: Deps | None,
    driver: Any = None,
    task_ids: set[str] | None = None,
    limit: int | None = None,
    max_steps: int = 25,
    repeats: int = 1,
    resume: bool = False,
) -> list[TaskResult]:
    tasks = [t for t in load_tasks(SPLITS[split]) if t.enabled]
    if task_ids:
        tasks = [t for t in tasks if t.id in task_ids]
    if limit:
        tasks = tasks[:limit]
    own = driver is None
    if own:
        from cua_driver import CuaDriver

        driver = CuaDriver.create()
    title = f"native {split} split, arms {', '.join(arms)}"
    results: list[TaskResult] = load_partial(out_dir) if resume else []
    if results:
        log.info("resuming: %s rows already in %s", len(results), out_dir / "results.json")
    try:
        for rep in range(repeats):
            for task in tasks:
                for arm in arms:
                    have = sum(1 for r in results if r.task_id == task.id and r.arm == arm)
                    if have > rep:
                        continue
                    log.info("running %s on %s (repeat %s)", task.id, arm, rep + 1)
                    results.append(await run_task(driver, task, arm, out_dir, deps, max_steps=max_steps))  # type: ignore[arg-type]
                    write_results(results, out_dir, title)
    finally:
        if own:
            await driver.shutdown()
    write_results(results, out_dir, title)
    return results


def main(argv: list[str] | None = None) -> None:
    from jevdual.keys import load_keys

    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=sorted(SPLITS))
    ap.add_argument("--arm", action="append", choices=ARMS)
    ap.add_argument("--oracle", action="store_true", help="replay each task's solve script instead of an arm")
    ap.add_argument("--task", action="append")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=25)
    ap.add_argument("--llm", default="meta", help="System 2 provider: meta (Muse Spark) or none")
    ap.add_argument("--out", default=f"results/native-{time.strftime('%Y%m%d-%H%M%S')}")
    ap.add_argument(
        "--resume", action="store_true", help="fill missing (task, arm, repeat) rows in --out/results.json"
    )
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    present = load_keys()
    log.info("keys present: %s", present)
    arms: tuple[str, ...] = ("oracle",) if args.oracle else tuple(args.arm or ["s1_only"])

    async def go() -> list[TaskResult]:
        if args.oracle:
            return await run_split(
                args.split,
                arms,
                Path(args.out),
                deps=None,
                task_ids=set(args.task) if args.task else None,
                limit=args.limit,
                max_steps=args.max_steps,
                repeats=args.repeats,
                resume=args.resume,
            )
        from typesafe_sdk import AsyncTypeSafeClient

        async with AsyncTypeSafeClient() as client:
            deps = default_deps(None if args.llm == "none" else args.llm, client)
            return await run_split(
                args.split,
                arms,
                Path(args.out),
                deps=deps,
                task_ids=set(args.task) if args.task else None,
                limit=args.limit,
                max_steps=args.max_steps,
                repeats=args.repeats,
                resume=args.resume,
            )

    results = asyncio.run(go())
    print((Path(args.out) / "report.md").read_text())
    print(f"{len(results)} results written to {args.out}")


if __name__ == "__main__":
    main()
