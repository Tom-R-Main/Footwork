"""Categorise done rejections in a run: what the verifier refused, and whether the predicate later passed.

    uv run python -m evals.rejections results/<run>

Sources: System 2 rejections are logged by the agent (``System 2 done rejected by verification``) and
attributed to the task by the preceding ``running <task> on dual`` line; System 1 done vetoes are in
the trace as ``arbiter_reason`` starting with ``verification``. Categories:

- ``process_unmet``: a per-requirement ``unmet`` verdict on a requirement that names an action
  (entered, submitted, clicked, opened, signed in, ...). Judged on the final page, where the action
  is no longer visible: the trajectory-ledger case.
- ``outcome_unmet``: ``unmet`` on a requirement that names a result (reported, found, price, ...).
- ``uncertain``: the ``complete`` noul fell between the accept and reject bands.
- ``no_fact``: the answer carried no atom found on the page.
A rejection is a *false reject by predicate* when the run later passed its predicate and the
rejected done was issued on the same URL the run ended on.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

PROCESS_WORDS = re.compile(
    r"\b(entered|submitted|clicked|opened|attempted|searched|signed in|sign-in|switched|in cart|chosen|typed|"
    r"dismissed|handled|performed|navigated|followed|added|pressed|waited|sorted|filled|logged)\b",
    re.IGNORECASE,
)
OUTCOME_WORDS = re.compile(r"\b(reported|found|price|answer|name|year|total|message|amount|title|author|license|language)\b", re.IGNORECASE)


@dataclass
class Rejection:
    task_id: str
    system: str  # s1 (S1 done vetoed) or s2 (System 2 done rejected)
    step: int | None
    band: str
    reason: str
    category: str
    requirement: str | None
    passed: bool | None = None
    at_final_url: bool | None = None

    @property
    def false_reject(self) -> bool:
        return bool(self.passed) and bool(self.at_final_url)


def categorise(reason: str) -> tuple[str, str | None]:
    m = re.search(r"(?:; )?([^;:]+?) unmet with p=", reason)
    if m:
        req = m.group(1).strip()
        if PROCESS_WORDS.search(req) and not OUTCOME_WORDS.search(req):
            return "process_unmet", req
        if OUTCOME_WORDS.search(req) and not PROCESS_WORDS.search(req):
            return "outcome_unmet", req
        return ("process_unmet" if PROCESS_WORDS.search(req) else "outcome_unmet"), req
    if "no fact found" in reason or "no claim quoted" in reason:
        return "no_fact", None
    if "uncertain" in reason:
        return "uncertain", None
    if "answer_required" in reason or "asks for an answer" in reason:
        return "answer_missing", None
    return "other", None


def load(run_dir: Path) -> list[Rejection]:
    results = {(r["task_id"], r["arm"]): r for r in json.loads((run_dir / "results.json").read_text())}
    out: list[Rejection] = []
    # System 2 rejections from the log, attributed by the last "running X on dual" line
    cur: tuple[str, str] | None = None
    log_path = run_dir / "run.log"
    if log_path.is_file():
        for line in log_path.read_text(errors="replace").splitlines():
            m = re.search(r"running (\S+) on (s1_only|stock|dual)", line)
            if m:
                cur = (m.group(1), m.group(2))
                continue
            m = re.search(r"step (\d+): System 2 done rejected by verification \((verify|reject)\): (.*)$", line)
            if m and cur and cur[1] == "dual":
                cat, req = categorise(m.group(3))
                out.append(Rejection(cur[0], "s2", int(m.group(1)), m.group(2), m.group(3).strip(), cat, req))
    # System 1 done vetoes from the traces
    for f in sorted((run_dir / "traces").glob("*-dual-*.jsonl")):
        task_id = None
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "header":
                task_id = r["run_id"].rsplit("-", 2)[0]
                continue
            a = r.get("arbiter_reason") or ""
            if a.startswith("verification"):
                band = a.split(":", 1)[0].split()[-1]
                reason = a.split(":", 1)[1].strip() if ":" in a else a
                cat, req = categorise(reason)
                out.append(Rejection(task_id or f.stem, "s1", r["step"], band, reason, cat, req))
    # outcome and final-URL context
    urls: dict[str, dict[int, str]] = defaultdict(dict)
    for f in sorted((run_dir / "traces").glob("*-dual-*.jsonl")):
        task_id = None
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "header":
                task_id = r["run_id"].rsplit("-", 2)[0]
                continue
            urls[task_id or f.stem][r["step"]] = r.get("url_after") or ""
    for rej in out:
        res = results.get((rej.task_id, "dual"))
        if res is None:
            continue
        rej.passed = bool(res["passed"])
        final = res.get("final_url") or ""
        step_url = urls.get(rej.task_id, {}).get(rej.step or -1, "")
        rej.at_final_url = bool(final) and step_url.split("#")[0] == final.split("#")[0]
    return out


def render(run_dir: Path, rejections: list[Rejection]) -> str:
    lines = [f"# Done rejections: {run_dir.name}", ""]
    for system, label in (("s2", "System 2 done rejected"), ("s1", "System 1 done vetoed")):
        rs = [r for r in rejections if r.system == system]
        lines += [f"## {label} ({len(rs)})", "", "| category | count | run later passed | at final URL and passed (false reject by predicate) |", "|---|---|---|---|"]
        for cat, n in Counter(r.category for r in rs).most_common():
            sub = [r for r in rs if r.category == cat]
            lines.append(f"| {cat} | {n} | {sum(1 for r in sub if r.passed)} | {sum(1 for r in sub if r.false_reject)} |")
        reqs = Counter(r.requirement for r in rs if r.requirement)
        if reqs:
            lines += ["", "Requirements judged unmet most often:", ""]
            lines += [f"- {req}: {n}" for req, n in reqs.most_common(12)]
        lines.append("")
    total = len(rejections)
    fr = sum(1 for r in rejections if r.false_reject)
    proc = sum(1 for r in rejections if r.category == "process_unmet")
    unc = sum(1 for r in rejections if r.category == "uncertain")
    lines += [
        "## Reading",
        "",
        (
            f"{total} rejections in total; {fr} were issued on the URL the run ended on in a run whose predicate passed "
            f"(false rejects by predicate, an upper bound since the claim text is not checked here). "
            f"{proc} are per-requirement verdicts on an action judged from the final page, where the action is no longer "
            f"visible: the trajectory ledger addresses these. {unc} are the `complete` noul in the uncertain band, which "
            f"a ledger changes only indirectly (fewer unmet requirements raise `complete`)."
        ),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    text = render(run_dir, load(run_dir))
    (run_dir / "rejections.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
