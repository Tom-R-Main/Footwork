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
            "false_done": sum(1 for r in rs if r.is_done and not r.passed),
            "mean_steps": (sum(r.steps for r in rs) / n) if n else 0.0,
            "llm_calls": sum(r.llm_calls for r in rs),
            "jev_calls": sum(r.jev_calls for r in rs),
            "llm_tokens": sum(r.llm_tokens for r in rs),
            "cost_usd": sum(r.cost_usd for r in rs),
            "wall_s": sum(r.wall_s for r in rs),
            "errors": sum(1 for r in rs if r.error),
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
    lines = [f"# {title}", "", "| arm | tasks | pass | pass rate | false done | mean steps | LLM calls | Jev calls | LLM tokens | cost USD | wall s | errors |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, a in agg.items():
        lines.append(
            f"| {arm} | {a['tasks']:.0f} | {a['pass']:.0f} | {a['pass_rate']:.0%} | {a['false_done']:.0f} | {a['mean_steps']:.1f} | "
            f"{a['llm_calls']:.0f} | {a['jev_calls']:.0f} | {a['llm_tokens']:.0f} | {a['cost_usd']:.4f} | {a['wall_s']:.0f} | {a['errors']:.0f} |"
        )
    lines += ["", "## Per task", "", "| task | arm | pass | steps | s1/s2 | cost USD | wall s | error |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: (r.task_id, r.arm)):
        lines.append(f"| {r.task_id} | {r.arm} | {'yes' if r.passed else 'no'} | {r.steps} | {r.s1_steps}/{r.s2_steps} | {r.cost_usd:.4f} | {r.wall_s:.0f} | {(r.error or '')[:60]} |")
    return "\n".join(lines) + "\n"


def write_results(results: list[TaskResult], out_dir: Path, title: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps([asdict(r) for r in results], indent=1, default=str))
    (out_dir / "summary.json").write_text(json.dumps({"arms": aggregate(results), "by_tag": by_tag(results)}, indent=1))
    (out_dir / "report.md").write_text(render_markdown(results, title))
