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
import json
import logging
import os
import time
import uuid
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from browser_use.agent.service import Agent
from browser_use.browser.profile import BrowserProfile
from jevdual import BACKEND, patch
from jevdual.agent import DualProcessAgent, S1Policy
from jevdual.keys import META_BASE_URL, MUSE_CONTRIBUTOR, load_keys
from jevdual.trace import ActionRecord, MenuEntry, RunHeader, StepRecord, Timings, TraceWriter

from evals.fixtures.server import serve
from evals.predicates import EndState, checkpoints_missed, evaluate
from evals.report import TaskResult, write_results
from evals.tasks.schema import Task, load_tasks

Arm = Literal["stock", "s1_only", "dual", "guarded", "delegate", "delegate_evidence", "scripted"]
JEV_TOKENS_PER_CALL = 2400  # observed mean request size on the local site
JEV_USD_PER_MTOK = 0.042
ARMS: tuple[Arm, ...] = ("stock", "s1_only", "dual", "guarded", "delegate", "delegate_evidence", "scripted")
S2_ARMS = ("dual", "guarded", "delegate", "delegate_evidence")
DELEGATE_ARMS = ("delegate", "delegate_evidence")  # arms whose System 2 is the real model and whose done is verified
log = logging.getLogger("evals.runner")

PolicyFactory = Callable[[Task, Any, str], S1Policy]  # (task, secret store, arm)


def _secret_store(task: Task, site_url: str):
    """Scope a task's secrets to the origin of its start page: the local fixture (loopback over http is
    allowed by the strict rule) or, for a live task, that site's https origin and nothing else."""
    if not task.secrets:
        return None
    from urllib.parse import urlsplit

    from jevdual.secrets import SecretStore

    origin = urlsplit(task.resolved_start_url(site_url))
    pattern = f"{origin.scheme}://{origin.hostname}"
    return SecretStore({pattern: dict(task.secrets)})


def default_policy_factory() -> PolicyFactory:
    """S1 policy for the s1_only and dual arms: Jev over TypeSafe, arbiter chosen per arm at call time.

    The arm is a call-time argument on purpose: an earlier version bound it at construction from
    the first arm listed, so a heldout run with --arm s1_only --arm dual ran the dual arm with the
    always-act arbiter and no verifier.
    """
    from jevdual.policy import JevPolicy
    from jevdual.s1 import AlwaysAct, JevS1
    from typesafe_sdk import AsyncTypeSafeClient

    base_client = AsyncTypeSafeClient()  # reads TYPESAFE_API_KEY

    def factory(task: Task, store: Any = None, arm: str = "dual") -> S1Policy:
        client = CountingClient(base_client)  # one counter per task: every Jev request is billed
        policy = JevPolicy(client)
        if arm == "s1_only":
            # S1's own done stands, so false completions are measured, not hidden.
            s1 = JevS1(policy, arbiter=AlwaysAct(), requirements=tuple(task.requirements), secrets=store)
        elif arm == "guarded":
            # System 2 alone behind the same gate and done verification: the fair baseline (Q9).
            from jevdual.s1 import GuardOnly
            from jevdual.verify import ArbiterHook, Verifier

            hook = ArbiterHook(Verifier(client), requirements=tuple(task.requirements), answer_expected=task.answer_expected)
            guard = GuardOnly(verifier=hook, secrets=store)
            guard.jev_counter = client  # type: ignore[attr-defined]
            return guard
        else:
            from jevdual.verify import ArbiterHook, Verifier

            hook = ArbiterHook(Verifier(client), requirements=tuple(task.requirements), answer_expected=task.answer_expected)
            s1 = JevS1(
                policy,
                arbiter=_dual_arbiter(),
                requirements=tuple(task.requirements),
                verifier=hook,
                secrets=store,
                # Q9 delegate arm: S1 acts only inside a bounded assignment from System 2
                only_when_delegated=(arm in DELEGATE_ARMS),
            )
        s1.jev_counter = client  # type: ignore[attr-defined]
        return s1

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


class CountingClient:
    """Counts every System One request and its input tokens at the client boundary."""

    def __init__(self, inner: Any):
        self.inner = inner
        self.calls = 0
        self.input_tokens = 0

    async def system_one(self, state: Any, questions: Any, *, model: str | None = None, **kwargs: Any) -> Any:
        self.calls += 1
        r = await self.inner.system_one(state, questions, model=model, **kwargs)
        usage = getattr(r, "usage", None)
        tokens = getattr(usage, "input_tokens", None)
        if isinstance(tokens, int):
            self.input_tokens += tokens
        else:
            log.warning("Jev response without input_tokens; cost will undercount this call")
        return r


def decide_passed(task: Task, end: EndState, error: str | None, paused: bool, judgement: dict[str, Any] | None = None) -> bool:
    """A run that paused before a destructive action passes only a not_reached predicate.
    Multistep tasks also need every checkpoint URL visited (key intermediate states).
    A ``judge`` task passes on the upstream judge's verdict alone (its criteria were the ground truth)."""
    if error is not None:
        return False
    if task.predicate.kind == "judge":
        return bool(judgement and judgement.get("verdict")) and not checkpoints_missed(task, end)
    if paused and task.predicate.kind != "not_reached":
        return False
    if checkpoints_missed(task, end):
        return False
    return evaluate(task.predicate, end)


class _EndStateCapture:
    """browser-use closes the session when run() returns, so the end state is captured
    from the on_step_end hook and the last capture wins. Predicates read innerText because
    the serializer's text drops some inline nodes (the number in 'Showing page <b>3</b> of 3')."""

    def __init__(self) -> None:
        self.last: dict[str, str] = {}
        self.last_step = 0
        self.failures = 0

    async def __call__(self, agent: Agent) -> None:
        try:
            snap = await _snapshot_page(agent)
            if snap:
                self.last = snap
                self.last_step = agent.state.n_steps
        except Exception as exc:  # noqa: BLE001
            self.failures += 1
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
            verify = rec.verify if rec and rec.verify else next((v for v in getattr(agent, "s2_verifications", []) if v.get("step") == i), None)
            menu = [MenuEntry(**m) for m in (rec.menu if rec else ())]
            w.write(
                StepRecord(
                    run_id=run_id,
                    step=i,
                    system=systems.get(i, "s2"),  # type: ignore[arg-type]
                    url_after=h.state.url,
                    decision=decision,
                    arbiter_reason=(rec.verdict.reason if rec and rec.verdict else None),
                    proposed=list(rec.proposed) if rec and rec.proposed else [],  # S1's own proposal only; executed carries what ran
                    executed=actions,
                    result_error=next((r.error for r in h.result if r.error), None),
                    is_done=any(r.is_done for r in h.result),
                    memory_line=h.model_output.memory if h.model_output else None,
                    menu=menu,
                    verify=verify,
                    timings=Timings(step_ms=step_ms, jev_ms=(rec.jev_ms if rec else None), dom_ms=(rec.menu_ms if rec else None)),
                )
            )


BROWSER_START_FAILURE = "BrowserStartEvent"


def _remove_temp_profile(agent: Any) -> None:
    """browser-use leaves its per-session Chrome profile in the temp dir (about 25 MB each; 636 of
    them filled the disk on 2026-09-21). Remove ours once the session is closed."""
    import shutil
    import tempfile

    try:
        profile = getattr(getattr(agent, "browser_session", None), "browser_profile", None)
        path = getattr(profile, "user_data_dir", None)
        if not path:
            return
        path = Path(str(path))
        tmp = Path(tempfile.gettempdir()).resolve()
        if path.name.startswith("browser-use-user-data-dir") and path.resolve().is_relative_to(tmp) and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        log.debug("temp profile cleanup skipped: %s", exc)


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
    browser_start_retries: int = 1,
) -> TaskResult:
    """Run one task on one arm; a browser that fails to start is retried once (infrastructure, not the agent)."""
    result = await _run_task_once(task, arm, site_url, out_dir, llm=llm, policy_factory=policy_factory, max_steps=max_steps, headless=headless)
    attempts = 0
    while result.error and BROWSER_START_FAILURE in result.error and attempts < browser_start_retries:
        attempts += 1
        log.warning("browser failed to start for %s on %s; retrying (%s/%s)", task.id, arm, attempts, browser_start_retries)
        result = await _run_task_once(task, arm, site_url, out_dir, llm=llm, policy_factory=policy_factory, max_steps=max_steps, headless=headless)
    return result


async def _run_task_once(
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
    sensitive = store.to_browser_use_for(start_url) if store is not None else None
    t0 = time.perf_counter()
    error: str | None = None
    holder: dict[str, Any] = {}
    if arm == "stock":
        if llm is None:
            raise ValueError("stock arm needs an llm")
        agent: Agent = Agent(
            task=task.task,
            llm=llm,
            browser_profile=profile,
            calculate_cost=True,
            sensitive_data=sensitive,
            ground_truth=task.judge_ground_truth,
        )
    else:
        if policy_factory is None:
            raise ValueError(f"{arm} arm needs a policy_factory")
        from jevdual.testing import RefusingLLM

        tools = None
        s1_policy = policy_factory(task, store, arm)
        if arm in DELEGATE_ARMS:
            from browser_use import Tools
            from jevdual.tools import register_delegation

            tools = Tools()
            register_delegation(tools, lambda: holder.get("agent"))
        if arm == "delegate_evidence":
            from jevdual.evidence import EvidenceSelector, register_find_evidence
            from jevdual.menu import build_menu

            selector = EvidenceSelector(getattr(s1_policy, "jev_counter", None) or getattr(getattr(s1_policy, "policy", None), "client", None))
            holder["evidence"] = selector

            async def _page_text() -> tuple[str, str]:
                agent_ = holder["agent"]
                state_ = await agent_.browser_session.get_browser_state_summary(include_screenshot=False)
                m = build_menu(state_)
                text_ = m.full_text or m.page_text
                if store is not None:
                    text_ = store.redactor()(text_)
                return m.url, text_

            register_find_evidence(tools, selector, _page_text, task=lambda: holder["agent"].task)
        extend: str | None = None
        if arm in DELEGATE_ARMS:
            from jevdual.tools import DELEGATION_GUIDANCE, EVIDENCE_GUIDANCE

            extend = DELEGATION_GUIDANCE + ("\n\n" + EVIDENCE_GUIDANCE if arm == "delegate_evidence" else "")
        agent = DualProcessAgent(
            task=task.task,
            llm=llm if (arm in S2_ARMS and llm is not None) else RefusingLLM(),
            browser_profile=profile,
            s1_policy=s1_policy,
            calculate_cost=llm is not None,
            sensitive_data=sensitive,
            authorized_destructive=task.authorize,
            authorized_actions=task.authorized_actions,
            # the upstream judge runs on the System 2 model after the run; nothing to judge with on S1-only
            use_judge=llm is not None and arm in S2_ARMS,
            ground_truth=task.judge_ground_truth,
            **({"tools": tools} if tools is not None else {}),
            **({"extend_system_message": extend} if extend else {}),
        )
        holder["agent"] = agent
    capture = _EndStateCapture()
    try:
        await agent.browser_session.start()
        await agent.browser_session.navigate_to(start_url)
        history = await agent.run(max_steps=max_steps, on_step_end=capture)
        end = _end_state(capture, history)
        if capture.last_step < len(history.history):
            error = f"end state unavailable: last capture at step {capture.last_step} of {len(history.history)}"
    except Exception as exc:  # noqa: BLE001 - a crashed run is a failed task, not a crashed rig
        error = repr(exc)
        history = agent.history
        end = EndState(final_url=None, page_text="", answer=None, is_done=False)
    finally:
        try:
            await agent.close()
        except Exception as exc:  # noqa: BLE001
            log.warning("close failed: %s", exc)
        _remove_temp_profile(agent)
    wall = time.perf_counter() - t0
    trace_path = out_dir / "traces" / f"{run_id}.jsonl"
    llm_model = getattr(llm, "model", None) if llm is not None else None
    paused = bool(getattr(agent, "paused_before_action", None))
    judgement: dict[str, Any] | None = None
    try:
        judgement = history.judgement() if history is not None else None
    except Exception as exc:  # noqa: BLE001
        log.warning("judgement unavailable: %s", exc)
    passed = decide_passed(task, end, error, paused, judgement)
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
    counter = getattr(getattr(agent, "s1_policy", None), "jev_counter", None)
    if counter is not None:
        jev_calls_total = counter.calls
        jev_cost = counter.input_tokens / 1e6 * JEV_USD_PER_MTOK
    else:
        jev_calls_total = getattr(agent, "s1_steps", 0)
        jev_cost = jev_calls_total * JEV_TOKENS_PER_CALL / 1e6 * JEV_USD_PER_MTOK
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
        jev_calls=jev_calls_total,
        llm_tokens=usage.total_tokens if usage else 0,
        llm_cost_usd=llm_cost,
        jev_cost_usd=jev_cost,
        wall_s=wall,
        is_done=end.is_done,
        success=end.success,
        paused=paused,
        final_url=end.final_url,
        answer=end.answer,
        error=error,
        tags=tuple(task.tags),
        graded_by="judge" if task.predicate.kind == "judge" else "predicate",
        judge_verdict=(bool(judgement["verdict"]) if judgement and judgement.get("verdict") is not None else None),
        judge_reason=(redactor(str(judgement.get("failure_reason") or "")) if judgement and redactor is not None else (str(judgement.get("failure_reason") or "") if judgement else None)),
        judge_impossible=bool(judgement.get("impossible_task")) if judgement else False,
        judge_captcha=bool(judgement.get("reached_captcha")) if judgement else False,
        delegations=len(getattr(agent, "delegations", []) or []) + (1 if getattr(agent, "delegation", None) is not None else 0),
        subgoals_reached=sum(1 for d in (getattr(agent, "delegations", []) or []) if getattr(d, "status", "") == "reached"),
        delegation_statuses=dict(Counter(getattr(d, "status", "?") for d in (getattr(agent, "delegations", []) or []))),
        delegation_jev_calls=sum(getattr(d, "jev_calls", 0) for d in (getattr(agent, "delegations", []) or [])),
        evidence_calls=getattr(holder.get("evidence"), "calls", 0),
        llm_requests=int(getattr(usage, "entry_count", 0) or 0) if usage else 0,
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
    resume: bool = False,
) -> list[TaskResult]:
    tasks = load_tasks(Path(__file__).parent / "tasks" / f"{split}.yaml")
    if task_ids:
        tasks = [t for t in tasks if t.id in task_ids]
    if not include_live and not split.startswith("live"):
        tasks = [t for t in tasks if "live" not in t.tags]
    if limit:
        tasks = tasks[:limit]
    patch.install()
    site_url, stop = serve()
    title = f"{split} split, arms {', '.join(arms)}"
    results: list[TaskResult] = load_partial(out_dir) if resume else []
    done = {(r.task_id, r.arm) for r in results}
    if done:
        log.info("resuming: %s task runs already in %s", len(done), out_dir / "results.json")
    try:
        for task in tasks:
            for arm in arms:
                if (task.id, arm) in done:
                    continue
                log.info("running %s on %s", task.id, arm)
                results.append(
                    await run_task(task, arm, site_url, out_dir, llm=llm, policy_factory=policy_factory, max_steps=max_steps)
                )
                # written after every task run so a crash (disk full, power) keeps what finished
                write_results(results, out_dir, title)
    finally:
        stop()
    write_results(results, out_dir, title)
    return results


def load_partial(out_dir: Path) -> list[TaskResult]:
    """Rows already in ``out_dir/results.json`` (for ``--resume``)."""
    path = out_dir / "results.json"
    if not path.is_file():
        return []
    rows = json.loads(path.read_text())
    out = []
    for r in rows:
        r["tags"] = tuple(r.get("tags") or ())
        out.append(TaskResult(**r))
    return out


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
    ap.add_argument("--split", default="dev", help="dev, heldout, or any live-* task file in evals/tasks")
    ap.add_argument("--arm", action="append", choices=ARMS, help="repeatable; default stock")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--task", action="append")
    ap.add_argument("--live", action="store_true", help="include live-site tasks")
    ap.add_argument("--llm", default="meta", help="System 2 provider for stock/dual arms: meta (Muse Spark 1.3 Contributor, default), browser-use, or none")
    ap.add_argument("--max-steps", type=int, default=25)
    ap.add_argument("--out", default=f"results/run-{time.strftime('%Y%m%d-%H%M%S')}")
    ap.add_argument("--resume", action="store_true", help="skip task/arm pairs already in --out/results.json")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    present = load_keys()
    logging.getLogger("evals.runner").info("keys present: %s", {k: v for k, v in present.items()})
    arms = tuple(args.arm or ["stock"])
    if "scripted" in arms:
        raise SystemExit("the scripted arm is for tests; supply a policy_factory programmatically")
    llm = _default_llm(None if args.llm == "none" else args.llm)
    policy_factory = default_policy_factory() if any(a in ("s1_only", "dual", "guarded", "delegate", "delegate_evidence") for a in arms) else None
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
            resume=args.resume,
            max_steps=args.max_steps,
        )
    )
    print((Path(args.out) / "report.md").read_text())
    print(f"{len(results)} results written to {args.out}")


if __name__ == "__main__":
    main()
