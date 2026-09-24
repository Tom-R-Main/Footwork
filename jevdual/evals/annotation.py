"""Q1 annotation set: one row per step where System 1 produced a decision, drawn from every run whose
traces carry the menu snapshot and verification scores (trace schema 2), for a person to label.

    uv run python -m evals.annotation results/<run> [results/<run> ...] --out results/annotation/<name>.csv

A row is labelable when System 1 chose a target: either it acted (``system`` s1) or it proposed and the
arbiter escalated (``system`` s2 with an S1 target). Steps where System 1 made no decision at all
(declined without a call, verification-only steps) carry nothing to label and are left out.

Columns a labeller uses: ``task_text``, ``url``, ``menu_size``, ``s1_operation``, ``s1_target``,
``alternatives`` (the next best targets with their probabilities), ``s1_proposed`` (what S1 would have
run), ``executed`` (what ran, S1's own action or System 2's), ``url_after``, ``next_reason`` (what the
arbiter said at the next step), ``result_error``, ``run_passed``. ``auto_label`` is the heuristic from
``evals.labels`` and is to be overwritten in ``label`` (right / wrong / unclear) with a ``note``.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter
from pathlib import Path

from evals.metrics import reason_class

BAD_NEXT = {"stuck", "no_effect", "repeated_target"}


log = logging.getLogger("evals.annotation")


def _start_urls() -> dict[str, str]:
    """task id -> start_url from every task file, for the page System 1 saw at step 1 (traces record url_after only)."""
    import yaml

    out: dict[str, str] = {}
    for f in sorted((Path(__file__).parent / "tasks").glob("*.yaml")):
        data = yaml.safe_load(f.read_text()) or {}
        for t in data.get("tasks", data if isinstance(data, list) else []):
            if isinstance(t, dict) and t.get("id"):
                out[t["id"]] = t.get("start_url") or ""
    return out


def _menu_label(menu: dict[int, dict], sid: object) -> str:
    try:
        return (menu.get(int(str(sid))) or {}).get("label", "") or ""
    except (TypeError, ValueError):
        return ""


def rows_for(run_dir: Path) -> list[dict]:
    rows_json = json.loads((run_dir / "results.json").read_text())
    results = {(r["task_id"], r["arm"]): r for r in rows_json}
    tasks_text = {r["task_id"]: r.get("task") or "" for r in results.values()}
    start_urls = _start_urls()
    # the measured population is the manifest: a trace with no result row (an aborted attempt, a crash
    # before its row was written) is exploratory and stays out unless the manifest has no trace paths at all
    manifest = {Path(r["trace_path"]).name for r in rows_json if r.get("trace_path")}
    out = []
    skipped: list[str] = []
    for f in sorted((run_dir / "traces").glob("*.jsonl")):
        if manifest and f.name not in manifest:
            skipped.append(f.name)
            continue
        header = None
        steps = []
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "header":
                header = r
                continue
            steps.append(r)
        if header is None or int(header.get("schema_version", 1)) < 2:
            continue
        arm = header["arm"]
        task_id = header["run_id"].rsplit("-", 2)[0]
        res = results.get((task_id, arm), {})
        passed = bool(res.get("passed"))
        steps.sort(key=lambda r: r["step"])
        last_step = steps[-1]["step"] if steps else 0
        prev_url = start_urls.get(task_id, "")
        for i, r in enumerate(steps):
            url_before = (
                r.get("url_before") or prev_url
            )  # the runner records url_after only; the previous step's is the page S1 saw
            prev_url = r.get("url_after") or prev_url
            d = r.get("decision") or {}
            op = d.get("operation") or {}
            tg = d.get("target") or {}
            if tg.get("choice") is None and not op.get("choice"):
                continue  # System 1 made no decision here: nothing to label
            menu = {m["id"]: m for m in (r.get("menu") or [])}
            nouls = d.get("nouls") or {}
            nxt = steps[i + 1] if i + 1 < len(steps) else None
            next_reason = reason_class(nxt.get("arbiter_reason")) if nxt else ""
            executed = r.get("executed") or []
            exec_names = ",".join(a.get("name", "") for a in executed)
            exec_idx = next(
                (
                    a.get("params", {}).get("index")
                    for a in executed
                    if isinstance(a.get("params"), dict) and a.get("params", {}).get("index") is not None
                ),
                None,
            )
            bad = (
                bool(r.get("result_error"))
                or (next_reason in BAD_NEXT)
                or (not passed and r["step"] >= last_step - 1)
            )
            system = r.get("system", "s2")
            auto = ("wrong" if bad else "right") if system == "s1" else "unknown"
            probs = tg.get("probabilities") or {}
            alts = sorted(((float(p_), k) for k, p_ in probs.items()), reverse=True)[:5]
            verify = r.get("verify") or {}
            unmet = verify.get("unmet_effective") or verify.get("unmet") or {}
            out.append(
                {
                    "run": run_dir.name,
                    "run_id": header["run_id"],
                    "task": task_id,
                    "arm": arm,
                    "step": r["step"],
                    "system": system,
                    "task_text": (tasks_text.get(task_id) or header.get("task", ""))[:300],
                    "url": url_before,
                    "menu_size": len(menu),
                    "s1_operation": op.get("choice", ""),
                    "s1_op_conf": op.get("confidence", ""),
                    "s1_target": _menu_label(menu, tg.get("choice")) or str(tg.get("choice", "")),
                    "s1_target_conf": tg.get("confidence", ""),
                    "alternatives": "; ".join(
                        f"{_menu_label(menu, k)[:40] or k} ({p_:.2f})" for p_, k in alts
                    ),
                    "goal_done": nouls.get("goal_done", ""),
                    "stuck": nouls.get("stuck", ""),
                    "needs_reasoning": nouls.get("needs_reasoning", ""),
                    "destructive": nouls.get("destructive", ""),
                    "arbiter_reason": (r.get("arbiter_reason") or "")[:120],
                    "s1_proposed": json.dumps(r.get("proposed") or []),
                    "executed": exec_names,
                    "executed_target": _menu_label(menu, exec_idx) if exec_idx is not None else "",
                    "url_after": r.get("url_after") or "",
                    "result_error": (r.get("result_error") or "")[:80],
                    "next_reason": next_reason,
                    "verify_band": verify.get("band", ""),
                    "verify_complete": verify.get("complete", ""),
                    "verify_unmet_max": (max(unmet.values()) if unmet else ""),
                    "run_passed": passed,
                    "auto_label": auto,
                    "label": "",
                    "note": "",
                }
            )
    if skipped:
        log.info("annotation: %s trace(s) not in the results manifest skipped: %s", len(skipped), skipped[:5])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = []
    for d in args.run_dirs:
        rows.extend(rows_for(Path(d)))
    if not rows:
        raise SystemExit("no labelable rows: the runs' traces carry no System 1 decisions (schema 2 needed)")
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    by = Counter((r["run"], r["arm"], r["system"]) for r in rows)
    print(f"{len(rows)} rows -> {path}")
    for k, v in sorted(by.items()):
        print(f"  {k[0]} {k[1]} {k[2]}: {v}")
    print("auto labels:", dict(Counter(r["auto_label"] for r in rows)))


if __name__ == "__main__":
    main()
