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
import os
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from browser_use.agent.service import Agent
from browser_use.browser.profile import BrowserProfile
from jevdual import BACKEND, patch
from jevdual.agent import DualProcessAgent, S1Policy
from jevdual.keys import META_BASE_URL, MUSE_CONTRIBUTOR, load_keys
from jevdual.trace import ActionRecord, RunHeader, StepRecord, Timings, TraceWriter

from evals.fixtures.server import serve
from evals.predicates import EndState, evaluate
from evals.report import TaskResult, write_results
from evals.tasks.schema import Task, load_tasks

Arm = Literal["stock", "s1_only", "dual", "scripted"]
JEV_TOKENS_PER_CALL = 2400  # observed mean request size on the local site
JEV_USD_PER_MTOK = 0.042
ARMS: tuple[Arm, ...] = ("stock", "s1_only", "dual", "scripted")
log = logging.getLogger("evals.runner")

PolicyFactory = Callable[[Task, Any], S1Policy]


def _secret_store(task: Task, site_url: str):
    """Scope a task's secrets to the local site's origin (loopback over http is allowed by the strict rule)."""
    if not task.secrets:
        return None
    from urllib.parse import urlsplit

    from jevdual.secrets import SecretStore

    origin = urlsplit(site_url)
    pattern = f"{origin.scheme}://{origin.hostname}"
    return SecretStore({pattern: dict(task.secrets)})


def default_policy_factory(arm: str) -> PolicyFactory:
    """S1 policy for the s1_only and dual arms: Jev over TypeSafe, arbiter per arm."""
    from jevdual.policy import JevPolicy
    from jevdual.s1 import AlwaysAct, JevS1
    from typesafe_sdk import AsyncTypeSafeClient

    client = AsyncTypeSafeClient()  # reads TYPESAFE_API_KEY
    policy = JevPolicy(client)

    def factory(task: Task, store: Any = None) -> S1Policy:
        if arm == "s1_only":
            # S1's own done stands, so false completions are measured, not hidden.
            return JevS1(policy, arbiter=AlwaysAct(), requirements=tuple(task.requirements), secrets=store)
        from jevdual.verify import ArbiterHook, Verifier

        hook = ArbiterHook(Verifier(client), requirements=tuple(task.requirements))
        return JevS1(policy, arbiter=_dual_arbiter(), requirements=tuple(task.requirements), verifier=hook, secrets=store)

    return factory


def _dual_arbiter():
    """A fresh Arbiter per task: its repeat-target and no-effect state is per run."""
    try:
        from jevdual.arbiter import Arbiter  # task D2

        return Arbiter.from_toml()
    except ImportError:  # pragma: no cover - until D2 lands
        from jevdual.s1 import AlwaysAct

        return AlwaysAct()


def _final_page_text(state: Any) -> str:
    try:
        return state.dom_state.llm_representation()
    except Exception:  # noqa: BLE001 - best effort; predicates on text simply fail
        return ""


async def _snapshot_page(agent: Agent) -> dict[str, str]:
    """url plus innerText of the current page, read live over CDP."""
    session = agent.browser_session
    if session is None:
        return {}
    url = await session.get_current_page_url()
    cdp = await session.get_or_create_cdp_session()
    r = await cdp.cdp_client.send.Runtime.evaluate(
        params={"expression": "document.body ? document.body.innerText : ''", "returnByValue": True},
        session_id=cdp.session_id,
    )
    return {"url": url, "text": str(r.get("result", {}).get("value") or "")}


class _EndStateCapture:
    """browser-use closes the session when run() returns, so the end state is captured
    from the on_step_end hook and the last capture wins. Predicates read innerText because
    the serializer's text drops some inline nodes (the number in 'Showing page <b>3</b> of 3')."""

    def __init__(self) -> None:
        self.last: dict[str, str] = {}

    async def __call__(self, agent: Agent) -> None:
        try:
            snap = await _snapshot_page(agent)
            if snap:
                self.last = snap
        except Exception as exc:  # noqa: BLE001
            log.warning("end-state capture failed at step %s: %s", agent.state.n_steps, exc)


def _end_state(capture: _EndStateCapture, history: Any) -> EndState:
    urls = tuple(u for u in history.urls() if u)
    return EndState(
        final_url=capture.last.get("url") or (urls[-1] if urls else None),
        page_text=capture.last.get("text", ""),
        answer=history.final_result(),
        visited_urls=urls,
        is_done=history.is_done(),
        success=history.is_successful(),
    )


def _write_trace(path: Path, run_id: str, task: Task, arm: str, agent: Agent, history: Any, llm_model: str | None, redactor: Any = None) -> None:
    systems = getattr(agent, "step_systems", {})
    s1_records = getattr(agent, "s1_records", {})
    with TraceWriter(path, redactor=redactor) as w:
        w.write(
            RunHeader(
                run_id=run_id,
                task=task.task,
                arm=arm if arm != "scripted" else "s1_only",
                backend=BACKEND,
                browser_use_version=importlib.metadata.version("browser_use"),
                patches=patch.describe(),
                llm_model=llm_model,
            )
        )
        for i, h in enumerate(history.history, start=1):
            actions = [ActionRecord(name=next(iter(a.model_dump(exclude_unset=True))), params=next(iter(a.model_dump(exclude_unset=True).values())) or {}) for a in (h.model_output.action if h.model_output else [])]
            step_ms = None
            if h.metadata:
                step_ms = (h.metadata.step_end_time - h.metadata.step_start_time) * 1000
            rec = s1_records.get(i)
            decision = rec.decision.to_trace(sum(rec.menu_omitted.values())) if rec and rec.decision else None
            w.write(
                StepRecord(
                    run_id=run_id,
                    step=i,
                    system=systems.get(i, "s2"),  # type: ignore[arg-type]
                    url_after=h.state.url,
                    decision=decision,
                    arbiter_reason=(rec.verdict.reason if rec and rec.verdict else None),
                    proposed=list(rec.proposed) if rec and rec.proposed else actions,
                    executed=actions,
                    result_error=next((r.error for r in h.result if r.error), None),
                    is_done=any(r.is_done for r in h.result),
                    memory_line=h.model_output.memory if h.model_output else None,
                    timings=Timings(step_ms=step_ms, jev_ms=(rec.jev_ms if rec else None), dom_ms=(rec.menu_ms if rec else None)),
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
    store = _secret_store(task, site_url)
    sensitive = store.to_browser_use() if store is not None else None
    t0 = time.perf_counter()
    error: str | None = None
    if arm == "stock":
        if llm is None:
            raise ValueError("stock arm needs an llm")
        agent: Agent = Agent(task=task.task, llm=llm, browser_profile=profile, calculate_cost=True, sensitive_data=sensitive)
    else:
        if policy_factory is None:
            raise ValueError(f"{arm} arm needs a policy_factory")
        from jevdual.testing import RefusingLLM

        agent = DualProcessAgent(
            task=task.task,
            llm=llm if (arm == "dual" and llm is not None) else RefusingLLM(),
            browser_profile=profile,
            s1_policy=policy_factory(task, store),
            calculate_cost=llm is not None,
            sensitive_data=sensitive,
            authorized_destructive=task.authorize,
        )
    capture = _EndStateCapture()
    try:
        await agent.browser_session.start()
        await agent.browser_session.navigate_to(start_url)
        history = await agent.run(max_steps=max_steps, on_step_end=capture)
        end = _end_state(capture, history)
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
    passed = evaluate(task.predicate, end) and error is None
    redactor = store.redactor() if store is not None else None
    _write_trace(trace_path, run_id, task, arm, agent, history, llm_model, redactor=redactor)
    if redactor is not None:
        end = EndState(
            final_url=redactor(end.final_url) if end.final_url else end.final_url,
            page_text=redactor(end.page_text),
            answer=redactor(end.answer) if end.answer else end.answer,
            visited_urls=tuple(redactor(u) for u in end.visited_urls),
            is_done=end.is_done,
            success=end.success,
        )
        if error:
            error = redactor(error)
    usage = history.usage
    llm_cost = usage.total_cost if usage else 0.0
    if usage and not llm_cost and llm_model and "muse" in llm_model:
        # browser-use has no price table for Muse; contributor rates from developer.meta.com.
        llm_cost = usage.total_prompt_tokens / 1e6 * 0.10 + usage.total_completion_tokens / 1e6 * 0.20
    jev_cost = getattr(agent, "s1_steps", 0) * JEV_TOKENS_PER_CALL / 1e6 * JEV_USD_PER_MTOK
    s1 = getattr(agent, "s1_steps", 0)
    s2 = getattr(agent, "s2_steps", len(history.history))
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
        llm_cost_usd=llm_cost,
        jev_cost_usd=jev_cost,
        wall_s=wall,
        is_done=end.is_done,
        success=end.success,
        paused=bool(getattr(agent, "paused_before_action", None)),
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
    patch.install()
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
    """System 2 provider. ``meta`` is Muse Spark 1.3 Contributor over the Meta Model API (OpenAI-compatible)."""
    if not name:
        return None
    if name in ("meta", "muse", MUSE_CONTRIBUTOR, "muse-spark-1.3"):
        from browser_use.llm.openai.chat import ChatOpenAI

        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise SystemExit("MODEL_API_KEY is not set; materialize META_MODEL_API_KEY into ~/.config/jevdual first")
        model = MUSE_CONTRIBUTOR if name in ("meta", "muse", MUSE_CONTRIBUTOR) else "muse-spark-1.3"
        return ChatOpenAI(model=model, base_url=META_BASE_URL, api_key=key, temperature=0.0)
    if name == "browser-use":
        from browser_use import ChatBrowserUse  # type: ignore[attr-defined]

        return ChatBrowserUse()
    raise SystemExit(f"unknown --llm {name}; wire the provider in evals/runner.py")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "heldout"])
    ap.add_argument("--arm", action="append", choices=ARMS, help="repeatable; default stock")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--task", action="append")
    ap.add_argument("--live", action="store_true", help="include live-site tasks")
    ap.add_argument("--llm", default="meta", help="System 2 provider for stock/dual arms: meta (Muse Spark 1.3 Contributor, default), browser-use, or none")
    ap.add_argument("--max-steps", type=int, default=25)
    ap.add_argument("--out", default=f"results/run-{time.strftime('%Y%m%d-%H%M%S')}")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    present = load_keys()
    logging.getLogger("evals.runner").info("keys present: %s", {k: v for k, v in present.items()})
    arms = tuple(args.arm or ["stock"])
    if "scripted" in arms:
        raise SystemExit("the scripted arm is for tests; supply a policy_factory programmatically")
    llm = _default_llm(None if args.llm == "none" else args.llm)
    policy_factory = default_policy_factory(arms[0]) if any(a in ("s1_only", "dual") for a in arms) else None
    results = asyncio.run(
        run_split(
            args.split,
            arms,  # type: ignore[arg-type]
            Path(args.out),
            llm=llm,
            policy_factory=policy_factory,
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
