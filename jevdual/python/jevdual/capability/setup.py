"""Per-job configuration and diagnostics without permission requests or app startup."""

from __future__ import annotations

import importlib.metadata
import json
import os
import re
import stat
import sys
from pathlib import Path
from uuid import uuid4

from .backend import ScopedBackend
from .completion import REPORT_SCHEMA, ReportError, validate_from_journal
from .contracts import CapabilityError

DEPENDENCIES = {
    "mcp": "==2.1.1",
    "cua-driver": "==0.28.2",
    "psutil": "==7.2.2",
    "browser-use": "==0.13.10",
    "typesafe-sdk": ">=0.7,<1",
    "orjson": ">=3.10",
}
LIMITATION = "macOS only: one loopback HTTP browser fixture and one identified TextEdit document. Window identity is checked when binding."


def make_config(
    run_dir: Path,
    *,
    source_pid: int,
    source_window: int,
    source_url: str,
    destination_pid: int,
    destination_window: int,
    document: Path,
) -> dict:
    if not run_dir.is_absolute() or run_dir.parent.resolve() != run_dir.parent:
        raise ValueError("Run directory must have an absolute, nonsymlink parent")
    if not document.is_absolute() or len(source_url) > 2048:
        raise ValueError("Use an absolute document path and a bounded URL")
    for value in (source_pid, source_window, destination_pid, destination_window):
        if type(value) is not int or not 0 < value < 2**32:
            raise ValueError("PIDs and window IDs must be positive bounded integers")
    doc = document.lstat()
    if not stat.S_ISREG(doc.st_mode) or doc.st_uid != os.getuid():
        raise ValueError("Destination must be an existing owned regular document")
    scope = {
        "task": "task_" + uuid4().hex,
        "source": {"pid": source_pid, "window_id": source_window, "url": source_url},
        "destination": {"pid": destination_pid, "window_id": destination_window, "document": str(document)},
    }
    ScopedBackend._check_scope(scope)
    # Keep the venv symlink: resolving it would launch the base interpreter.
    executable = str(Path(sys.executable).absolute())
    server = {
        "command": executable,
        "args": [
            "-m",
            "jevdual.capability.cli",
            "server",
            "--scope",
            str(run_dir / "scope.json"),
            "--journal",
            str(run_dir / "operations.sqlite"),
        ],
    }
    adapter = [
        executable,
        "-m",
        "jevdual.capability.cli",
        "report",
        "--journal",
        str(run_dir / "operations.sqlite"),
        "--task",
        scope["task"],
    ]
    manifest = {
        "task": scope["task"],
        "host_config": str(run_dir / "host.json"),
        "scope": str(run_dir / "scope.json"),
        "report_schema": str(run_dir / "report-schema.json"),
        "report_adapter": adapter,
        "limitation": LIMITATION,
        "publication": "Validate the structured final report through report_adapter and publish only trusted_summary. Never fall back to raw host prose.",
        "lifecycle": "Reuse this task only for reconnect/restart of this job. Generate a new run directory for each new job.",
    }
    run_dir.mkdir(mode=0o700)
    payloads = {
        "scope.json": scope,
        "host.json": {"mcpServers": {"footwork": server}},
        "report-schema.json": REPORT_SCHEMA,
        "run.json": manifest,
    }
    for name, payload in payloads.items():
        descriptor = os.open(run_dir / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    return manifest


def permission_status() -> dict:
    if sys.platform != "darwin":
        return {"accessibility": "unsupported", "screen_recording": "unsupported"}
    result = {}
    for name, module, function in (
        ("accessibility", "ApplicationServices", "AXIsProcessTrusted"),
        ("screen_recording", "Quartz", "CGPreflightScreenCaptureAccess"),
    ):
        try:
            imported = __import__(module)
            result[name] = "granted" if getattr(imported, function)() else "not_granted"
        except (ImportError, AttributeError):
            result[name] = "unavailable"
    return result


def _compatible(version: str, requirement: str) -> bool:
    """Conservative check for the pinned and numeric ranges declared here."""
    if requirement.startswith("=="):
        return version == requirement[2:]
    if not re.fullmatch(r"\d+(?:\.\d+)*", version):
        return False
    current = tuple(int(part) for part in version.split("."))
    for clause in requirement.split(","):
        match = re.fullmatch(r"(>=|<)(\d+(?:\.\d+)*)", clause)
        if not match:
            return False
        operator, limit = match.groups()
        bound = tuple(int(part) for part in limit.split("."))
        width = max(len(current), len(bound))
        left, right = current + (0,) * (width - len(current)), bound + (0,) * (width - len(bound))
        if (operator == ">=" and left < right) or (operator == "<" and left >= right):
            return False
    return True


def doctor(scope_path: Path | None = None, journal_path: Path | None = None) -> dict:
    dependencies = {}
    required = dict(DEPENDENCIES)
    if sys.platform == "darwin":
        required.update(
            {
                name: ">=12"
                for name in (
                    "pyobjc-framework-applicationservices",
                    "pyobjc-framework-quartz",
                    "pyobjc-framework-cocoa",
                )
            }
        )
    for name, requirement in required.items():
        try:
            version = importlib.metadata.version(name)
            dependencies[name] = {
                "version": version,
                "requirement": requirement,
                "compatible": _compatible(version, requirement),
            }
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = {"version": None, "requirement": requirement, "compatible": False}
    result = {
        "platform": sys.platform,
        "supported": sys.platform == "darwin",
        "dependencies": dependencies,
        "permissions": permission_status(),
        "scope": "not_checked",
        "journal": "not_checked",
        "warnings": [],
        "limitation": LIMITATION,
        "provider_account_required": False,
        "rust_toolchain_required": False,
    }
    scope = None
    if scope_path:
        try:
            with scope_path.open("rb") as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise ValueError("Scope exceeds input bound")
            scope = json.loads(raw)
            ScopedBackend._check_scope(scope)
            doc = Path(scope["destination"]["document"])
            result["scope"] = {
                "valid": True,
                "document_exists": doc.is_file(),
                "window_identity": "checked_at_bind",
            }
            import psutil

            result["scope"]["pids_exist"] = all(
                psutil.pid_exists(scope[name]["pid"]) for name in ("source", "destination")
            )
        except (OSError, ValueError, ImportError, RecursionError, CapabilityError):
            result["scope"] = {"valid": False}
            scope = None
    if journal_path:
        if not journal_path.exists():
            result["journal"] = "not_created"
        elif scope:
            try:
                checked = validate_from_journal(
                    journal_path,
                    scope["task"],
                    {"completion": "unknown", "operations": [], "persistence": "not_checked"},
                )
                count = len(checked["operations"])
                result["journal"] = {
                    "operations": count,
                    "operation_completion": checked["operation_completion"],
                }
                if count:
                    result["warnings"].append(
                        "This task already has operation history. Reuse only for the same job; report its full ledger. Start a fresh run for a new job."
                    )
            except (ReportError, OSError):
                result["journal"] = "unavailable"
        else:
            result["journal"] = "scope_required"
    return result
