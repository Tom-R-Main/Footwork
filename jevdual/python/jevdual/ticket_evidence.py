"""Independent, pre-bound ticket ingress receipts for the owned native Chrome fixture.

This is a cooperative runtime protocol, not authentication of arbitrary SQLite
files. A receipt qualifies one admitted service effect. It supplies no native
input count, and a matching current row alone never enrolls an old operation.
All qualification SQL is read-only; it dispatches no UI or HTTP request.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import os
import re
import sqlite3
import stat
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from jevdual.app_qualification import FIELDS, artifact_identity

VERSION = 1
PRODUCER = "footwork.ticket_ledger/v1"
PREDICATE = "unique_admitted_ticket_ingress"
MAX_JSON = 1_048_576


class TicketEvidenceError(ValueError):
    """Incomplete or contradictory service evidence cannot release native custody."""


def canonical(value: Any) -> str:
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as error:
        raise TicketEvidenceError("ticket evidence must be finite JSON") from error
    if len(text.encode()) > MAX_JSON:
        raise TicketEvidenceError("ticket evidence exceeds retention bound")
    return text


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalize_origin(value: str) -> str:
    """One exact HTTP numeric-loopback origin; no DNS, credentials or URL suffixes."""
    try:
        parts = urlsplit(value)
        if (
            not isinstance(value, str)
            or value != value.strip()
            or any(ord(char) < 33 for char in value)
            or parts.scheme != "http"
            or not parts.hostname
            or not ipaddress.ip_address(parts.hostname).is_loopback
            or parts.username is not None
            or parts.password is not None
            or parts.path not in ("", "/")
            or parts.query
            or parts.fragment
            or parts.port is None
            or not 1 <= parts.port <= 65535
        ):
            raise ValueError("unsupported origin")
        host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
        result = f"http://{host}:{parts.port}"
        if value not in (result, result + "/"):
            raise ValueError("origin alias")
        return result
    except (ValueError, TypeError, AttributeError) as error:
        raise TicketEvidenceError("ticket scope requires an exact numeric-loopback HTTP origin") from error


def _path(value: Any) -> Path:
    if not isinstance(value, (str, Path)):
        raise TicketEvidenceError("owned path is missing")
    text = str(value)
    path = Path(text)
    if (
        not path.is_absolute()
        or len(text) > 4096
        or "\x00" in text
        or str(path) != text
        or any(part in (".", "..") for part in text.split("/"))
    ):
        raise TicketEvidenceError("owned paths must be exact absolute paths")
    return path


def _chain(path: Path, *, file: bool) -> list[dict[str, Any]]:
    """Open every component with O_NOFOLLOW; retain path/device/inode identity."""
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    current = Path("/")
    result = []
    try:
        info = os.fstat(descriptor)
        result.append({"path": "/", "device": info.st_dev, "inode": info.st_ino})
        for index, name in enumerate(path.parts[1:]):
            final = index == len(path.parts) - 2
            flags = os.O_RDONLY | os.O_NOFOLLOW
            if not (file and final):
                flags |= os.O_DIRECTORY
            child = os.open(name, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            current /= name
            info = os.fstat(descriptor)
            if file and final and (not stat.S_ISREG(info.st_mode) or info.st_size > 16 * 1024 * 1024):
                raise TicketEvidenceError("ledger must be a bounded regular file")
            result.append({"path": str(current), "device": info.st_dev, "inode": info.st_ino})
        return result
    except OSError as error:
        raise TicketEvidenceError("owned source path is unavailable or contains a symlink") from error
    finally:
        os.close(descriptor)


def _snapshot(database: Path, root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not database.is_relative_to(root) or database == root:
        raise TicketEvidenceError("ledger is outside the owned root")
    before = _chain(database, file=True)
    root_chain = _chain(root, file=False)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(database) + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            _chain(sidecar, file=True)
    connection = None
    try:
        connection = sqlite3.connect(f"file:{quote(str(database))}?mode=ro", uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        fixture = dict(
            connection.execute("SELECT key,value FROM fixture_state WHERE key IN ('fixture_id','origin')")
        )
        if not re.fullmatch(r"[0-9a-f]{32}", fixture.get("fixture_id", "")):
            raise TicketEvidenceError("ledger lacks a persistent fixture identity")
        origin = normalize_origin(fixture.get("origin", ""))
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("ingress", "tickets")
        }
        # More than one row already falsifies this narrow fresh-ledger protocol.
        # Keep bounded diagnostic counts rather than read arbitrary accumulated data.
        rows = []
        tickets = []
        if counts["ingress"] <= 2 and counts["tickets"] <= 2:
            for row in connection.execute(
                "SELECT id,received,body_sha,fields,error,origin FROM ingress ORDER BY id"
            ):
                fields = json.loads(row["fields"])
                rows.append({**dict(row), "fields": fields})
            tickets = [
                json.loads(row[0])
                for row in connection.execute("SELECT fields FROM tickets ORDER BY request_id")
            ]
        snapshot = {"ingress": rows, "tickets": tickets, "counts": counts}
        source = {
            "database": str(database),
            "identity": before[-1],
            "ancestors": before[:-1],
            "root": root_chain[-1],
            "fixture_id": fixture["fixture_id"],
            "origin": origin,
        }
        canonical(snapshot)
        if before != _chain(database, file=True) or root_chain != _chain(root, file=False):
            raise TicketEvidenceError("ledger identity changed during capture")
        return source, snapshot
    except (sqlite3.Error, ValueError, TypeError) as error:
        if isinstance(error, TicketEvidenceError):
            raise
        raise TicketEvidenceError("ledger does not expose a qualified read-only snapshot") from error
    finally:
        if connection is not None:
            connection.close()


def _expected(value: Any) -> dict[str, str]:
    if (
        not isinstance(value, dict)
        or set(value) != set(FIELDS)
        or any(not isinstance(item, str) or not item or len(item) > 256 for item in value.values())
        or value["orientation"] != "clockwise90"
        or not re.fullmatch(r"[0-9a-f]{64}", value["digest"])
        or not re.fullmatch(r"[0-9a-f]{32}", value["request_id"])
        or value["request_id"] == "0" * 32
    ):
        raise TicketEvidenceError("ticket intent needs exact fields and a fresh UUID nonce")
    if uuid.UUID(hex=value["request_id"]).version != 4:
        raise TicketEvidenceError("ticket intent requires a version-four UUID nonce")
    return {key: value[key] for key in FIELDS}


def form_body(expected: dict[str, str]) -> bytes:
    """HTML form encoding in the fixture's observed control order."""
    expected = _expected(expected)

    def encoded(text: str) -> str:
        return "".join(
            chr(byte)
            if 65 <= byte <= 90 or 97 <= byte <= 122 or 48 <= byte <= 57 or byte in b"*-._"
            else "+"
            if byte == 32
            else f"%{byte:02X}"
            for byte in text.encode("utf-8")
        )

    return "&".join(encoded(key) + "=" + encoded(expected[key]) for key in FIELDS).encode("ascii")


def _artifact(root: Path, path: Path) -> dict[str, Any]:
    _chain(root, file=False)
    _chain(path, file=True)
    try:
        return artifact_identity(root, path)
    except (ValueError, OSError) as error:
        raise TicketEvidenceError("bound artifact changed or became unavailable") from error


def bind(database: Path, url: str, expected: dict[str, str], artifact: Path, root: Path) -> dict[str, Any]:
    """Enroll a fresh owned service source and input before any submission."""
    database, artifact, root = _path(database), _path(artifact), _path(root)
    origin, expected = normalize_origin(url), _expected(expected)
    source, snapshot = _snapshot(database, root)
    identity = _artifact(root, artifact)
    if source["origin"] != origin or snapshot["counts"] != {"ingress": 0, "tickets": 0}:
        raise TicketEvidenceError("ticket source must match the origin and be empty before enrollment")
    if expected["artifact"] != artifact.name or expected["digest"] != identity["sha256"]:
        raise TicketEvidenceError("ticket intent differs from its exact input artifact")
    scope = {
        "schema_version": VERSION,
        "kind": "ticket_scope",
        "root": str(root),
        "url": origin,
        "source": source,
        "expected": expected,
        "artifact": identity,
        "bound_at": time.time(),
    }
    canonical(scope)
    return scope


def _validate_scope(scope: Any) -> None:
    if (
        not isinstance(scope, dict)
        or set(scope)
        != {"schema_version", "kind", "root", "url", "source", "expected", "artifact", "bound_at"}
        or type(scope["schema_version"]) is not int
        or scope["schema_version"] != VERSION
        or scope["kind"] != "ticket_scope"
        or not isinstance(scope["source"], dict)
        or not isinstance(scope["artifact"], dict)
    ):
        raise TicketEvidenceError("unsupported ticket scope")
    canonical(scope)
    _expected(scope["expected"])
    if normalize_origin(scope["url"]) != scope["url"]:
        raise TicketEvidenceError("ticket origin alias")
    _time(scope["bound_at"])
    root = _path(scope["root"])
    source = scope["source"]
    if set(source) != {"database", "identity", "ancestors", "root", "fixture_id", "origin"}:
        raise TicketEvidenceError("unsupported ticket source identity")
    database = _path(source["database"])
    artifact = scope["artifact"]
    artifact_path = _path(artifact.get("path"))
    if not database.is_relative_to(root) or not artifact_path.is_relative_to(root):
        raise TicketEvidenceError("ticket source/input is outside the owned root")
    if (
        not isinstance(source["ancestors"], list)
        or not 1 <= len(source["ancestors"]) <= 128
        or not isinstance(source["fixture_id"], str)
        or not re.fullmatch(r"[0-9a-f]{32}", source["fixture_id"])
        or source["origin"] != scope["url"]
    ):
        raise TicketEvidenceError("invalid ticket source identity")
    for identity in [source["root"], source["identity"], *source["ancestors"]]:
        if (
            not isinstance(identity, dict)
            or set(identity) != {"path", "device", "inode"}
            or any(type(identity[key]) is not int or identity[key] < 0 for key in ("device", "inode"))
        ):
            raise TicketEvidenceError("invalid ticket path identity")
        _path(identity["path"])
    if source["root"]["path"] != str(root) or source["identity"]["path"] != str(database):
        raise TicketEvidenceError("ticket identity names another path")
    if (
        set(artifact) != {"path", "device", "inode", "size", "mtime_ns", "sha256"}
        or any(
            type(artifact[key]) is not int or artifact[key] < 0
            for key in ("device", "inode", "size", "mtime_ns")
        )
        or artifact["sha256"] != scope["expected"]["digest"]
        or artifact_path.name != scope["expected"]["artifact"]
    ):
        raise TicketEvidenceError("invalid ticket artifact identity")


def _time(value: Any) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise TicketEvidenceError("ticket capture time is invalid")


def _capture(scope: dict[str, Any]) -> dict[str, Any]:
    _validate_scope(scope)
    root = Path(scope["root"])
    source, snapshot = _snapshot(Path(scope["source"]["database"]), root)
    if source != scope["source"] or _artifact(root, Path(scope["artifact"]["path"])) != scope["artifact"]:
        raise TicketEvidenceError("ticket source or input artifact changed")
    return {"source": source, "snapshot": snapshot, "checked_at": time.time()}


def prepare(scope: dict[str, Any]) -> dict[str, Any]:
    """Capture a fresh baseline immediately before admission, without input."""
    capture = _capture(scope)
    if capture["snapshot"]["counts"] != {"ingress": 0, "tickets": 0}:
        raise TicketEvidenceError("ticket baseline is no longer empty")
    return {
        "schema_version": VERSION,
        "kind": "ticket_preparation",
        "scope": json.loads(canonical(scope)),
        "baseline": capture["snapshot"],
        "baseline_sha256": digest(capture["snapshot"]),
        "captured_at": capture["checked_at"],
    }


def _admission(op: Any, prepared: Any, binding: Any, *, allow_prepared: bool = False) -> None:
    from jevdual.operator_evidence import validate_binding

    try:
        validate_binding(binding)
        if (
            not isinstance(prepared, dict)
            or set(prepared)
            != {"schema_version", "kind", "scope", "baseline", "baseline_sha256", "captured_at"}
            or type(prepared["schema_version"]) is not int
            or prepared["schema_version"] != VERSION
            or prepared["kind"] != "ticket_preparation"
            or canonical(prepared["baseline"])
            != canonical({"ingress": [], "tickets": [], "counts": {"ingress": 0, "tickets": 0}})
            or prepared["baseline_sha256"] != digest(prepared["baseline"])
        ):
            raise TicketEvidenceError("unsupported pre-admitted ticket preparation")
        _validate_scope(prepared["scope"])
        _time(prepared["captured_at"])
        _time(op.created)
        if (
            canonical(prepared["scope"]) != canonical(op.args.get("ticket_scope"))
            or prepared["captured_at"] > op.created
            or prepared["scope"]["bound_at"] > prepared["captured_at"]
            or op.move != "click"
            or op.args.get("words") != ["click", "button:Register asset"]
            or getattr(op, "execution_stage", None)
            not in (("prepared", "started") if allow_prepared else ("started",))
            or normalize_origin(op.args.get("native_scope", {}).get("url", "")) != prepared["scope"]["url"]
            or set(op.args["native_scope"]) != {"url", "title"}
            or not isinstance(op.args["native_scope"]["title"], str)
            or not op.args["native_scope"]["title"]
        ):
            raise TicketEvidenceError("ticket preparation differs from the admitted submission")
        for value in (op.id, op.task, op.request_digest, op.resource, op.observation, op.target):
            if not isinstance(value, str) or not value:
                raise TicketEvidenceError("ticket admission identity is missing")
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        if isinstance(error, TicketEvidenceError):
            raise
        raise TicketEvidenceError("ticket admission identity is invalid") from error


def validate_preparation(op: Any, prepared: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    """Validate the original preparation inside admission's transaction, before input starts."""
    _admission(op, prepared, binding, allow_prepared=True)
    return prepared


def _matches(snapshot: Any, expected: dict[str, str], origin: str, *, began: float, ended: float) -> bool:
    if (
        not isinstance(snapshot, dict)
        or set(snapshot) != {"counts", "ingress", "tickets"}
        or not isinstance(snapshot.get("counts"), dict)
        or any(type(value) is not int for value in snapshot["counts"].values())
        or snapshot.get("counts") != {"ingress": 1, "tickets": 1}
        or not isinstance(snapshot.get("ingress"), list)
        or len(snapshot["ingress"]) != 1
        or snapshot.get("tickets") != [expected]
    ):
        return False
    row = snapshot["ingress"][0]
    return (
        isinstance(row, dict)
        and set(row) == {"id", "received", "body_sha", "fields", "error", "origin"}
        and type(row.get("id")) is int
        and row["id"] > 0
        and type(row.get("received")) in (int, float)
        and math.isfinite(row["received"])
        and began <= row["received"] <= ended
        and row.get("fields") == expected
        and row.get("error") is None
        and row.get("origin") == origin
        and row.get("body_sha") == hashlib.sha256(form_body(expected)).hexdigest()
    )


def qualify(op: Any, prepared: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any] | None:
    """Observe the independent service ledger; never resend or manufacture native delivery."""
    _admission(op, prepared, binding)
    if getattr(op, "state", None) != "unknown" or getattr(op, "phase", None) == "not_sent":
        raise TicketEvidenceError("ticket qualification requires unresolved started custody")
    scope = prepared["scope"]
    capture = _capture(scope)
    if not _matches(
        capture["snapshot"], scope["expected"], scope["url"], began=op.created, ended=capture["checked_at"]
    ):
        return None
    receipt = {
        "schema_version": VERSION,
        "kind": "ticket_submission",
        "producer": PRODUCER,
        "predicate": PREDICATE,
        "operation_id": op.id,
        "session_id": op.task,
        "request_digest": op.request_digest,
        "resource": op.resource,
        "observation": op.observation,
        "target": op.target,
        "move": op.move,
        "binding": json.loads(canonical(binding)),
        "phase": "sent",
        "effect": "confirmed",
        "preparation_sha256": digest(prepared),
        "source": scope["source"],
        "expected": scope["expected"],
        "artifact": scope["artifact"],
        "interval": {"start": op.created, "end": capture["checked_at"]},
        "capture": capture,
        "projection": {
            "app": "Google Chrome",
            "native_scope": op.args["native_scope"],
            "ticket_submission": prepared,
            "independent_effect": "confirmed",
        },
    }
    return validate_receipt(receipt, op, prepared, binding)


def validate_receipt(
    record: Any, op: Any, prepared: dict[str, Any], binding: dict[str, Any]
) -> dict[str, Any]:
    """Validate retained historical evidence without opening the app, artifact or ledger."""
    _admission(op, prepared, binding)
    keys = {
        "schema_version",
        "kind",
        "producer",
        "predicate",
        "operation_id",
        "session_id",
        "request_digest",
        "resource",
        "observation",
        "target",
        "move",
        "binding",
        "phase",
        "effect",
        "preparation_sha256",
        "source",
        "expected",
        "artifact",
        "interval",
        "capture",
        "projection",
    }
    if not isinstance(record, dict) or set(record) != keys:
        raise TicketEvidenceError("unsupported ticket receipt")
    from jevdual.operator_evidence import validate_binding

    try:
        validate_binding(record["binding"])
    except ValueError as error:
        raise TicketEvidenceError("invalid ticket receipt native binding") from error
    canonical(record)
    expected = {
        "schema_version": VERSION,
        "kind": "ticket_submission",
        "producer": PRODUCER,
        "predicate": PREDICATE,
        "operation_id": op.id,
        "session_id": op.task,
        "request_digest": op.request_digest,
        "resource": op.resource,
        "observation": op.observation,
        "target": op.target,
        "move": op.move,
        "binding": binding,
        "phase": "sent",
        "effect": "confirmed",
        "preparation_sha256": digest(prepared),
        "source": prepared["scope"]["source"],
        "expected": prepared["scope"]["expected"],
        "artifact": prepared["scope"]["artifact"],
        "projection": {
            "app": "Google Chrome",
            "native_scope": op.args["native_scope"],
            "ticket_submission": prepared,
            "independent_effect": "confirmed",
        },
    }
    if type(record["schema_version"]) is not int or any(
        canonical(record[key]) != canonical(value) for key, value in expected.items()
    ):
        raise TicketEvidenceError("ticket receipt differs from the admitted attempt")
    capture, interval = record["capture"], record["interval"]
    if not isinstance(capture, dict) or set(capture) != {"source", "snapshot", "checked_at"}:
        raise TicketEvidenceError("unsupported ticket capture")
    _time(capture["checked_at"])
    if (
        capture["checked_at"] > time.time()
        or canonical(capture["source"]) != canonical(record["source"])
        or canonical(interval) != canonical({"start": op.created, "end": capture["checked_at"]})
        or not _matches(
            capture["snapshot"],
            record["expected"],
            record["source"]["origin"],
            began=op.created,
            ended=capture["checked_at"],
        )
    ):
        raise TicketEvidenceError("ticket capture does not establish the admitted service effect")
    return record
