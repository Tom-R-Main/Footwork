"""Recompute current status totals from retained artifacts, without inference or live actions."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from evals.burden import per_progress, progress_rows

ROOT = Path(__file__).resolve().parents[1]
out = {}
for name in (
    "q10b-native-dev-20260924-r2",
    "q11-live-dev-pooled",
    "q12-live-dev-pooled",
    "q8-q9e-live-dev-20260922-162350",
    "q9e-delegate-20260922-212255",
):
    path = ROOT / name / "results.json"
    raw = path.read_bytes()
    rows = json.loads(raw)
    entry = {"sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows), "arms": {}}
    for arm in sorted({r["arm"] for r in rows}):
        rs = [r for r in rows if r["arm"] == arm]
        native = name.startswith("q10b")
        verified = sum(bool(r["passed"] and (r.get("is_done") if native else r.get("success") is True)) for r in rs)
        cost = sum((r.get("jev_cost_usd") or 0) + (r.get("llm_cost_usd") or 0) for r in rs)
        entry["arms"][arm] = {
            "rows": len(rs), "predicate_passes": sum(bool(r["passed"]) for r in rs),
            "verified": verified, "llm_requests": sum(r.get("llm_requests", 0) for r in rs),
            "llm_calls": sum(r.get("llm_calls", 0) for r in rs),
            "jev_calls": sum(r.get("jev_calls", 0) for r in rs),
            "estimated_cost_usd": cost,
            "cost_per_verified": cost / verified if verified else None,
            "noop_receipts": sum(r.get("noop_receipts", 0) for r in rs),
            "terminal_modes": dict(Counter(r.get("terminal_mode", "not_recorded") for r in rs)),
            "false_completion_tasks": [r["task_id"] for r in rs if r.get("success") is True and not r["passed"]],
        }
    if name == "q12-live-dev-pooled":
        entry["progress_comparison"] = per_progress(progress_rows(rows, "guarded"), progress_rows(rows, "guarded_receipts"))
    out[name] = entry
print(json.dumps(out, indent=2))
