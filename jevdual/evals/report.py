"""Aggregate per-task results into the comparison tables the README quotes."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class TaskResult:
    task_id: str
    arm: str
    passed: bool
    steps: int
    s1_steps: int
    s2_steps: int
    llm_calls: int
    jev_calls: int
    llm_tokens: int
    llm_cost_usd: float
    jev_cost_usd: float
    wall_s: float
    is_done: bool
    final_url: str | None
    answer: str | None
    error: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    trace_path: str | None = None
    success: bool | None = None
    paused: bool = False
    #: "predicate" (observed state) or "judge" (upstream judge verdict with the task's criteria as ground truth)
    graded_by: str = "predicate"
    #: Upstream judge (browser-use's judge prompt, run by the System 2 model) on every judged run
    judge_verdict: bool | None = None
    judge_reason: str | None = None
    judge_impossible: bool = False
    judge_captcha: bool = False
    #: Q9 delegate arms: bounded assignments System 2 issued, and how many reached their stop condition with observed support
    delegations: int = 0
    subgoals_reached: int = 0
    #: how each delegation ended (reached, not_reached, budget_exhausted, stuck, low_confidence, ...) and Jev calls spent inside them
    delegation_statuses: dict[str, int] = field(default_factory=dict)
    delegation_jev_calls: int = 0
    #: Q9 evidence arm: find_evidence calls System 2 made
    evidence_calls: int = 0
    #: actual model requests recorded by browser-use's token tracker (driver steps, retries, judge), not the S2 step count
    llm_requests: int = 0
    #: Q8: recoverable evaluate refusals in this run (the terminal pause is counted under paused)
    evaluate_refusals: int = 0
    gate_judgments: int = 0

    @property
    def cost_usd(self) -> float:
        return self.llm_cost_usd + self.jev_cost_usd


def aggregate(results: list[TaskResult]) -> dict[str, dict[str, float]]:
    by_arm: dict[str, list[TaskResult]] = defaultdict(list)
    for r in results:
        by_arm[r.arm].append(r)
    out: dict[str, dict[str, float]] = {}
    for arm, rs in sorted(by_arm.items()):
        n = len(rs)
        out[arm] = {
            "tasks": n,
            "pass": sum(r.passed for r in rs),
            "pass_rate": (sum(r.passed for r in rs) / n) if n else 0.0,
            # a run that ended with done(success=False) or paused before a destructive action is not a claimed success
            "false_done": sum(
                1 for r in rs if r.is_done and not r.passed and r.success is not False and not r.paused
            ),
            "paused": sum(1 for r in rs if r.paused),
            "mean_steps": (sum(r.steps for r in rs) / n) if n else 0.0,
            "llm_calls": sum(r.llm_calls for r in rs),
            "llm_requests": sum(r.llm_requests for r in rs),
            # a pass the agent also claimed (success=True): external success and supported claimed completion together
            "verified_pass": sum(1 for r in rs if r.passed and r.success is True),
            # a pass the agent refused to claim (UNVERIFIED or paused): correct outcome, abstained claim
            "unclaimed_pass": sum(1 for r in rs if r.passed and r.success is not True),
            "jev_calls": sum(r.jev_calls for r in rs),
            "llm_tokens": sum(r.llm_tokens for r in rs),
            "cost_usd": sum(r.cost_usd for r in rs),
            "wall_s": sum(r.wall_s for r in rs),
            "errors": sum(1 for r in rs if r.error),
            "judged": sum(1 for r in rs if r.judge_verdict is not None),
            "judge_pass": sum(1 for r in rs if r.judge_verdict),
            # agreement between the judge and the predicate, over predicate-graded rows the judge saw
            "judge_agree": sum(
                1
                for r in rs
                if r.judge_verdict is not None and r.graded_by == "predicate" and r.judge_verdict == r.passed
            ),
            "judge_false_accept": sum(
                1 for r in rs if r.judge_verdict and r.graded_by == "predicate" and not r.passed
            ),
            "judge_false_reject": sum(
                1 for r in rs if r.judge_verdict is False and r.graded_by == "predicate" and r.passed
            ),
            "captcha": sum(1 for r in rs if r.judge_captcha),
            "impossible": sum(1 for r in rs if r.judge_impossible),
            "graded_by_judge": sum(1 for r in rs if r.graded_by == "judge"),
            "delegations": sum(r.delegations for r in rs),
            "subgoals_reached": sum(r.subgoals_reached for r in rs),
            "evidence_calls": sum(r.evidence_calls for r in rs),
            "evaluate_refusals": sum(r.evaluate_refusals for r in rs),
        }
    return out


def by_tag(results: list[TaskResult]) -> dict[str, dict[str, dict[str, float]]]:
    tags: dict[str, list[TaskResult]] = defaultdict(list)
    for r in results:
        for t in r.tags:
            tags[t].append(r)
    return {t: aggregate(rs) for t, rs in sorted(tags.items())}


def render_markdown(results: list[TaskResult], title: str) -> str:
    agg = aggregate(results)
    lines = [
        f"# {title}",
        "",
        "| arm | tasks | pass | pass rate | false done | paused | mean steps | LLM calls | Jev calls | LLM tokens | est. cost USD | wall s | errors |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for arm, a in agg.items():
        lines.append(
            f"| {arm} | {a['tasks']:.0f} | {a['pass']:.0f} | {a['pass_rate']:.0%} | {a['false_done']:.0f} | {a['paused']:.0f} | {a['mean_steps']:.1f} | "
            f"{a['llm_calls']:.0f} | {a['jev_calls']:.0f} | {a['llm_tokens']:.0f} | {a['cost_usd']:.4f} | {a['wall_s']:.0f} | {a['errors']:.0f} |"
        )
    lines += [
        "",
        "## Outcomes (external success and claimed completion kept apart)",
        "",
        "| arm | verified pass (passed and claimed) | unclaimed pass (passed, UNVERIFIED or paused) | false done | model requests (tracker) | evaluate refusals | cost per verified pass |",
        "|---|---|---|---|---|---|---|",
    ]
    for arm, a in agg.items():
        vp = a["verified_pass"]
        lines.append(
            f"| {arm} | {vp:.0f} | {a['unclaimed_pass']:.0f} | {a['false_done']:.0f} | {a['llm_requests']:.0f} | {a['evaluate_refusals']:.0f} | {(a['cost_usd'] / vp) if vp else 0:.4f} |"
        )
    if any(r.judge_verdict is not None for r in results):
        lines += [
            "",
            "## Judge (upstream judge prompt, run by the System 2 model)",
            "",
            (
                "Predicate-graded rows: agreement, false accepts (judge yes, predicate no) and false rejects "
                "(judge no, predicate yes). Rows graded by the judge alone are counted separately."
            ),
            "",
            "| arm | judged | judge pass | agree | false accept | false reject | captcha | impossible | graded by judge |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for arm, a in agg.items():
            lines.append(
                f"| {arm} | {a['judged']:.0f} | {a['judge_pass']:.0f} | {a['judge_agree']:.0f} | {a['judge_false_accept']:.0f} | "
                f"{a['judge_false_reject']:.0f} | {a['captcha']:.0f} | {a['impossible']:.0f} | {a['graded_by_judge']:.0f} |"
            )
    if any(r.delegations for r in results):
        lines += [
            "",
            "## Delegation (Q9)",
            "",
            "| arm | delegations | subgoals reached | reached per delegation | S1 steps | S2 steps |",
            "|---|---|---|---|---|---|",
        ]
        for arm, a in agg.items():
            rs = [r for r in results if r.arm == arm]
            d = a["delegations"]
            lines.append(
                f"| {arm} | {d:.0f} | {a['subgoals_reached']:.0f} | {(a['subgoals_reached'] / d) if d else 0:.2f} | {sum(r.s1_steps for r in rs)} | {sum(r.s2_steps for r in rs)} |"
            )
    lines += [
        "",
        "## Per task",
        "",
        "| task | arm | pass | graded by | judge | steps | s1/s2 | deleg. | est. cost USD | wall s | error |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: (r.task_id, r.arm)):
        judge = "-" if r.judge_verdict is None else ("yes" if r.judge_verdict else "no")
        lines.append(
            f"| {r.task_id} | {r.arm} | {'yes' if r.passed else 'no'} | {r.graded_by} | {judge} | {r.steps} | {r.s1_steps}/{r.s2_steps} | {r.subgoals_reached}/{r.delegations} | {r.cost_usd:.4f} | {r.wall_s:.0f} | {(r.error or '')[:60]} |"
        )
    return "\n".join(lines) + "\n"


def write_results(results: list[TaskResult], out_dir: Path, title: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps([asdict(r) for r in results], indent=1, default=str))
    (out_dir / "summary.json").write_text(
        json.dumps({"arms": aggregate(results), "by_tag": by_tag(results)}, indent=1)
    )
    (out_dir / "report.md").write_text(render_markdown(results, title))
