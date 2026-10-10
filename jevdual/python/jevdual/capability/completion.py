"""Validate operation reports against a full, read-only task ledger snapshot.

The trusted renderer certifies historical admitted operations only. It never
endorses arbitrary model prose, current GUI content, persistence or a broader job.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import stat
import time
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import quote

MAX_OPERATIONS = 256
DISPOSITIONS = ("applied", "partial", "refused", "not_sent", "unknown")
REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "completion": {"type": "string", "enum": ["completed", "not_completed", "unknown"]},
        "operations": {
            "type": "array",
            "maxItems": MAX_OPERATIONS,
            "items": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "minLength": 1, "maxLength": 128},
                    "disposition": {"type": "string", "enum": list(DISPOSITIONS)},
                },
                "required": ["operation", "disposition"],
                "additionalProperties": False,
            },
        },
        "persistence": {"type": "string", "enum": ["not_checked", "saved", "unsaved"]},
    },
    "required": ["completion", "operations", "persistence"],
    "additionalProperties": False,
}


class ReportError(ValueError):
    code = "invalid_report"


class ReportUnavailable(ReportError):
    code = "report_unavailable"


def check_report(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"completion", "operations", "persistence"}:
        raise ReportError("Report requires completion, operations and persistence only")
    if value["completion"] not in ("completed", "not_completed", "unknown"):
        raise ReportError("Invalid completion")
    if value["persistence"] not in ("not_checked", "saved", "unsaved"):
        raise ReportError("Invalid persistence")
    claims = value["operations"]
    if not isinstance(claims, list) or len(claims) > MAX_OPERATIONS:
        raise ReportError("Operations must be a bounded array")
    ids = set()
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"operation", "disposition"}:
            raise ReportError("Each operation requires its ID and disposition only")
        op_id = claim["operation"]
        if not isinstance(op_id, str) or not op_id.strip() or len(op_id) > 128:
            raise ReportError("Invalid operation ID")
        if op_id in ids:
            raise ReportError("Duplicate operation ID")
        ids.add(op_id)
        if claim["disposition"] not in DISPOSITIONS:
            raise ReportError("Invalid disposition")
    return value


def ledger_snapshot(db: sqlite3.Connection, task: str) -> dict[str, Any]:
    if not isinstance(task, str) or not task.strip():
        raise ReportUnavailable("A configured task is required")
    # One SELECT is one SQLite snapshot; LIMIT detects overflow, never certifies
    # an incomplete projection or status's last-ten-operations view.
    rows = db.execute(
        "SELECT id,state,disposition,updated FROM operations WHERE task=? ORDER BY created,id LIMIT ?",
        (task, MAX_OPERATIONS + 1),
    ).fetchall()
    if len(rows) > MAX_OPERATIONS:
        raise ReportUnavailable("Task ledger exceeds the report bound; no completion certified")
    operations = []
    for op_id, state, disposition, updated in rows:
        if state not in ("dispatching", "unknown", "final"):
            raise ReportUnavailable("Unsupported operation state")
        if state == "final" and disposition not in DISPOSITIONS:
            raise ReportUnavailable("Invalid final disposition")
        if not isinstance(op_id, str) or not op_id.strip() or len(op_id) > 128:
            raise ReportUnavailable("Invalid operation identity")
        if not isinstance(updated, (float, int)) or not math.isfinite(updated):
            raise ReportUnavailable("Invalid operation revision")
        operations.append(
            {
                "operation": op_id,
                "state": state,
                "disposition": disposition if state == "final" else "unknown",
                "updated": updated,
            }
        )
    content = {"task": task, "operations": operations}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**content, "digest": digest, "as_of": time.time()}


def validate_report(report: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    check_report(report)
    operations = snapshot["operations"]
    actual = {op["operation"]: op["disposition"] for op in operations}
    completion = (
        "unknown"
        if "unknown" in actual.values()
        else "completed"
        if "applied" in actual.values() and "partial" not in actual.values()
        else "not_completed"
    )
    claimed = {c["operation"]: c["disposition"] for c in report["operations"]}
    reasons = []
    if set(claimed) != set(actual):
        reasons.append("operation_set_mismatch")
    if any(claimed.get(op_id) != disposition for op_id, disposition in actual.items()):
        reasons.append("disposition_mismatch")
    if report["completion"] == "completed" and completion != "completed":
        reasons.append("completion_mismatch")
    if report["persistence"] != "not_checked":
        reasons.append("disk_persistence_not_checked")
    accepted = not reasons
    summary = {
        "unknown": "Execution remains unknown. Matching text cannot confirm the attempted append; do not append again.",
        "completed": (
            f"{sum(d == 'applied' for d in actual.values())} recorded operations confirmed applied; "
            f"{sum(d in ('refused', 'not_sent') for d in actual.values())} attempts confirmed no input. "
            "These are historical effects, not certification of the host job."
        ),
        "not_completed": "The recorded operations do not establish completion.",
    }[completion]
    if not actual:
        summary = "No recorded operations; completion cannot be confirmed."
    if not accepted:
        summary = "Host completion report rejected (" + ", ".join(reasons) + "). " + summary
    summary += " Current document state and disk persistence are not certified by this report."
    return {
        "schema_version": "1",
        "scope": "all_admitted_task_operations",
        "validation": {"accepted": accepted, "reasons": reasons},
        "operation_completion": completion,
        "operations": operations,
        "persistence": "not_checked",
        "current_state": "not_checked",
        "task": snapshot["task"],
        "snapshot_digest": snapshot["digest"],
        "as_of": snapshot["as_of"],
        "trusted_summary": summary,
    }


def _private_file(path: Path) -> os.stat_result:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ReportUnavailable("Journal and sidecars must be private owned regular files")
    return info


def validate_from_journal(path: Path, task: str, report: Any) -> dict[str, Any]:
    """Host adapter: no journal startup recovery, lock takeover or operation writes."""
    check_report(report)
    path = Path(path).absolute()
    before = _private_file(path)
    for suffix in ("-wal", "-shm"):
        side = Path(str(path) + suffix)
        if side.exists() or side.is_symlink():
            _private_file(side)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ReportUnavailable("Journal identity changed")
        with closing(sqlite3.connect("file:" + quote(str(path), safe="/") + "?mode=ro", uri=True)) as db:
            db.execute("PRAGMA query_only=ON")
            after = _private_file(path)
            if (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino):
                raise ReportUnavailable("Journal identity changed")
            return validate_report(report, ledger_snapshot(db, task))
    except sqlite3.Error as exc:
        raise ReportUnavailable("Journal could not be validated") from exc
    finally:
        os.close(fd)


def unavailable_summary() -> dict[str, Any]:
    """Never return unvalidated host prose as a fallback."""
    return {
        "schema_version": "1",
        "validation": {"accepted": False, "reasons": ["report_unavailable"]},
        "operation_completion": "unknown",
        "trusted_summary": "Completion validation is unavailable. No completion is certified.",
    }
