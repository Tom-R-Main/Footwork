"""Three-arm eval runner: stock browser-use, S1-only, dual.

Every arm runs the same tasks against the same local site and live pages and
writes one JSONL trace per task (schema in ``jevdual.trace``); the numbers in
the report are computed from those traces and browser-use's own history, never
from a model's self-report. A fourth ``scripted`` arm runs a caller-supplied S1
policy with no model at all, so the rig itself is testable offline.

Usage:
    uv run python -m evals.runner --split dev --arm stock --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import logging
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from browser_use.agent.service import Agent
from browser_use.browser.profile import BrowserProfile
from jevdual import BACKEND
from jevdual.agent import DualProcessAgent, S1Policy
from jevdual.trace import ActionRecord, RunHeader, StepRecord, Timings, TraceWriter

from evals.fixtures.server import serve
from evals.predicates import EndState, evaluate
from evals.report import TaskResult, write_results
from evals.tasks.schema import Task, load_tasks

Arm = Literal["stock", "s1_only", "dual", "scripted"]
ARMS: tuple[Arm, ...] = ("stock", "s1_only", "dual", "scripted")
log = logging.getLogger("evals.runner")

PolicyFactory = Callable[[Task], S1Policy]


def _final_page_text(state: Any) -> str:
    try:
        return state.dom_state.llm_representation()
    except Exception:  # noqa: BLE001 - best effort; predicates on text simply fail
        return ""


async def _capture_end_state(agent: Agent, history: Any) -> EndState:
    page_text = ""
    final_url = None
    try:
        if agent.browser_session is not None:
            state = await agent.browser_session.get_browser_state_summary(include_screenshot=False)
            page_text = _final_page_text(state)
            final_url = state.url
    except Exception as exc:  # noqa: BLE001
        log.warning("could not capture end state: %s", exc)
    urls = tuple(u for u in history.urls() if u)
    return EndState(
        final_url=final_url or (urls[-1] if urls else None),
        page_text=page_text,
        answer=history.final_result(),
        visited_urls=urls,
        is_done=history.is_done(),
    )


def _write_trace(path: Path, run_id: str, task: Task, arm: str, agent: Agent, history: Any, llm_model: str | None) -> None:
    systems = getattr(agent, "step_systems", {})
    with TraceWriter(path) as w:
        w.write(
            RunHeader(
                run_id=run_id,
                task=task.task,
                arm=arm if arm != "scripted" else "s1_only",
                backend=BACKEND,
                browser_use_version=importlib.metadata.version("browser_use"),
                llm_model=llm_model,
            )
        )
        for i, h in enumerate(history.history, start=1):
            actions = [ActionRecord(name=next(iter(a.model_dump(exclude_unset=True))), params=next(iter(a.model_dump(exclude_unset=True).values())) or {}) for a in (h.model_output.action if h.model_output else [])]
            step_ms = None
            if h.metadata:
                step_ms = (h.metadata.step_end_time - h.metadata.step_start_time) * 1000
            w.write(
                StepRecord(
                    run_id=run_id,
                    step=i,
                    system=systems.get(i, "s2"),  # type: ignore[arg-type]
                    url_after=h.state.url,
                    proposed=actions,
                    executed=actions,
                    result_error=next((r.error for r in h.result if r.error), None),
                    is_done=any(r.is_done for r in h.result),
                    memory_line=h.model_output.memory if h.model_output else None,
                    timings=Timings(step_ms=step_ms),
                )
            )


async def run_task(
    task: Task,
    arm: Arm,
    site_url: str,
    out_dir: Path,
    *,
    llm: Any = None,
    policy_factory: PolicyFactory | None = None,
    max_steps: int = 25,
    headless: bool = True,
) -> TaskResult:
    run_id = f"{task.id}-{arm}-{uuid.uuid4().hex[:8]}"
    start_url = task.resolved_start_url(site_url)
    profile = BrowserProfile(headless=headless)
    t0 = time.perf_counter()
    error: str | None = None
    if arm == "stock":
        if llm is None:
            raise ValueError("stock arm needs an llm")
        agent: Agent = Agent(task=task.task, llm=llm, browser_profile=profile, calculate_cost=True)
    else:
        if policy_factory is None:
            raise ValueError(f"{arm} arm needs a policy_factory")
        from jevdual.testing import RefusingLLM

        agent = DualProcessAgent(
            task=task.task,
            llm=llm if (arm == "dual" and llm is not None) else RefusingLLM(),
            browser_profile=profile,
            s1_policy=policy_factory(task),
            calculate_cost=llm is not None,
        )
    try:
        await agent.browser_session.start()
        await agent.browser_session.navigate_to(start_url)
        history = await agent.run(max_steps=max_steps)
        end = await _capture_end_state(agent, history)
    except Exception as exc:  # noqa: BLE001 - a crashed run is a failed task, not a crashed rig
        error = repr(exc)
        history = agent.history
        end = EndState(final_url=None, page_text="", answer=None, is_done=False)
    finally:
        try:
            await agent.close()
        except Exception as exc:  # noqa: BLE001
            log.warning("close failed: %s", exc)
    wall = time.perf_counter() - t0
    trace_path = out_dir / "traces" / f"{run_id}.jsonl"
    llm_model = getattr(llm, "model", None) if llm is not None else None
    _write_trace(trace_path, run_id, task, arm, agent, history, llm_model)
    usage = history.usage
    s1 = getattr(agent, "s1_steps", 0)
    s2 = getattr(agent, "s2_steps", len(history.history))
    passed = evaluate(task.predicate, end) and error is None
    return TaskResult(
        task_id=task.id,
        arm=arm,
        passed=passed,
        steps=len(history.history),
        s1_steps=s1,
        s2_steps=s2,
        llm_calls=s2,
        jev_calls=s1,
        llm_tokens=usage.total_tokens if usage else 0,
        llm_cost_usd=usage.total_cost if usage else 0.0,
        jev_cost_usd=0.0,
        wall_s=wall,
        is_done=end.is_done,
        final_url=end.final_url,
        answer=end.answer,
        error=error,
        tags=tuple(task.tags),
        trace_path=str(trace_path),
    )


async def run_split(
    split: str,
    arms: tuple[Arm, ...],
    out_dir: Path,
    *,
    llm: Any = None,
    policy_factory: PolicyFactory | None = None,
    limit: int | None = None,
    task_ids: set[str] | None = None,
    include_live: bool = False,
    max_steps: int = 25,
) -> list[TaskResult]:
    tasks = load_tasks(Path(__file__).parent / "tasks" / f"{split}.yaml")
    if task_ids:
        tasks = [t for t in tasks if t.id in task_ids]
    if not include_live:
        tasks = [t for t in tasks if "live" not in t.tags]
    if limit:
        tasks = tasks[:limit]
    site_url, stop = serve()
    results: list[TaskResult] = []
    try:
        for task in tasks:
            for arm in arms:
                log.info("running %s on %s", task.id, arm)
                results.append(
                    await run_task(task, arm, site_url, out_dir, llm=llm, policy_factory=policy_factory, max_steps=max_steps)
                )
    finally:
        stop()
    write_results(results, out_dir, f"{split} split, arms {', '.join(arms)}")
    return results


def _default_llm(name: str | None) -> Any:
    if not name:
        return None
    from browser_use import ChatBrowserUse  # type: ignore[attr-defined]

    if name == "browser-use":
        return ChatBrowserUse()
    raise SystemExit(f"unknown --llm {name}; wire the provider in evals/runner.py")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "heldout"])
    ap.add_argument("--arm", action="append", choices=ARMS, help="repeatable; default stock")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--task", action="append")
    ap.add_argument("--live", action="store_true", help="include live-site tasks")
    ap.add_argument("--llm", help="LLM for stock/dual arms, e.g. browser-use")
    ap.add_argument("--max-steps", type=int, default=25)
    ap.add_argument("--out", default=f"results/run-{time.strftime('%Y%m%d-%H%M%S')}")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    arms = tuple(args.arm or ["stock"])
    if "scripted" in arms:
        raise SystemExit("the scripted arm is for tests; supply a policy_factory programmatically")
    llm = _default_llm(args.llm)
    results = asyncio.run(
        run_split(
            args.split,
            arms,  # type: ignore[arg-type]
            Path(args.out),
            llm=llm,
            limit=args.limit,
            task_ids=set(args.task) if args.task else None,
            include_live=args.live,
            max_steps=args.max_steps,
        )
    )
    print((Path(args.out) / "report.md").read_text())
    print(f"{len(results)} results written to {args.out}")


if __name__ == "__main__":
    main()
