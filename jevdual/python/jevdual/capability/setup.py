"""Per-job configuration and diagnostics without permission requests or app startup."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import re
import stat
import sys
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from .backend import ScopedBackend
from .completion import REPORT_SCHEMA, ReportError, validate_from_journal
from .contracts import CapabilityError

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
        "env": {
            "PYTHONPATH": "",
            "PYTHONHOME": "",
            "PYTHONNOUSERSITE": "1",
            "ANONYMIZED_TELEMETRY": "false",
            "BROWSER_USE_CLOUD_SYNC": "false",
        },
        "args": [
            "-I",
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
        "-I",
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


def _distribution_provenance(name: str) -> dict:
    try:
        installed = importlib.metadata.distribution(name)
        return {
            "version": installed.version,
            "location": str(Path(installed.locate_file("")).absolute()),
        }
    except importlib.metadata.PackageNotFoundError:
        return {"version": None, "location": None}


def doctor(scope_path: Path | None = None, journal_path: Path | None = None) -> dict:
    """Probe prerequisites only; met prerequisites do not qualify a native resource."""
    dependencies = {}
    warnings = []
    blockers = []

    def block(code: str) -> None:
        if code not in blockers:
            blockers.append(code)

    installed = _distribution_provenance("jevdual")
    python_requirement = None
    python_compatible = "unparsed"
    try:
        distribution = importlib.metadata.distribution("jevdual")
        python_requirement = distribution.metadata.get("Requires-Python")
        try:
            from packaging.specifiers import InvalidSpecifier, SpecifierSet
            from packaging.version import InvalidVersion, Version

            if not python_requirement or not python_requirement.strip():
                block("python_requirement_unparsed")
            else:
                try:
                    python_compatible = SpecifierSet(python_requirement).contains(
                        Version(platform.python_version())
                    )
                    if not python_compatible:
                        block("python_incompatible")
                except (InvalidSpecifier, InvalidVersion):
                    block("python_requirement_unparsed")
        except ImportError:
            block("python_requirement_unparsed")
    except importlib.metadata.PackageNotFoundError:
        block("dependency_metadata_unavailable")
    try:
        from packaging.requirements import InvalidRequirement, Requirement

        declared = importlib.metadata.requires("jevdual")
        if not declared:
            warnings.append("Installed distribution has no dependency metadata; compatibility is unverified.")
            block("dependency_metadata_unavailable")
        for declaration in declared or []:
            try:
                required = Requirement(declaration)
                if required.marker and not required.marker.evaluate():
                    continue
                name, requirement = required.name, str(required.specifier)
                understood = (
                    bool(requirement)
                    and all(
                        re.fullmatch(r"(?:==|>=|<)\d+(?:\.\d+)*", clause) for clause in requirement.split(",")
                    )
                    and not required.url
                    and not required.extras
                )
                try:
                    version = importlib.metadata.version(name)
                    compatibility = _compatible(version, requirement) if understood else "unparsed"
                    if compatibility is False:
                        block("dependency_incompatible")
                except importlib.metadata.PackageNotFoundError:
                    version, compatibility = None, False
                    block("dependency_missing")
                dependencies[name] = {
                    "version": version,
                    "requirement": requirement,
                    "compatible": compatibility,
                    "location": _distribution_provenance(name)["location"],
                }
                if not understood:
                    block("dependency_unparsed")
                    warnings.append(f"Dependency requirement is unparsed: {name}")
            except (InvalidRequirement, ValueError):
                block("dependency_unparsed")
                warnings.append("A dependency requirement is unparsed; compatibility is unverified.")
    except (ImportError, importlib.metadata.PackageNotFoundError):
        block("dependency_metadata_unavailable")
        warnings.append(
            "Installed distribution metadata or requirement parser unavailable; compatibility is unverified."
        )
    permissions = permission_status()
    if sys.platform != "darwin":
        block("platform_unsupported")
    elif permissions.get("accessibility") != "granted":
        block(
            "accessibility_not_granted"
            if permissions.get("accessibility") == "not_granted"
            else "accessibility_unavailable"
        )
    if sys.platform == "darwin" and permissions.get("screen_recording") != "granted":
        warnings.append("Screen Recording is not qualified. Routes that capture pixels may require it.")
    loaded_modules = {}
    for name in ("jevdual", "jevdual.capability.setup", "psutil", "ApplicationServices", "Quartz"):
        module = sys.modules.get(name)
        location = vars(module).get("__file__") if isinstance(module, ModuleType) else None
        if location:
            loaded_modules[name] = str(Path(location).absolute())
    result = {
        "platform": sys.platform,
        "supported": sys.platform == "darwin",
        "runtime": {
            "python_version": platform.python_version(),
            "python_requirement": python_requirement,
            "python_compatible": python_compatible,
            # Do not resolve the venv symlink into its base interpreter.
            "interpreter": str(Path(sys.executable).absolute()),
            "architecture": platform.machine(),
            "distribution": installed,
            "loaded_modules": loaded_modules,
        },
        "dependencies": dependencies,
        "permissions": permissions,
        "scope": "not_checked",
        "journal": "not_checked",
        "warnings": warnings,
        "dependency_metadata": "installed distribution",
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
            try:
                document = doc.lstat()
                document_exists = stat.S_ISREG(document.st_mode) and document.st_uid == os.getuid()
            except OSError:
                document_exists = False
            result["scope"] = {
                "valid": True,
                "document_exists": document_exists,
                "window_identity": "checked_at_bind",
            }
            if not document_exists:
                block("scope_document_unavailable")
            import psutil

            result["scope"]["pids_exist"] = all(
                psutil.pid_exists(scope[name]["pid"]) for name in ("source", "destination")
            )
            if not result["scope"]["pids_exist"]:
                block("scope_pids_unavailable")
        except (OSError, ValueError, ImportError, RecursionError, CapabilityError):
            result["scope"] = {"valid": False}
            scope = None
            block("scope_invalid")
    if journal_path:
        if not os.path.lexists(journal_path):
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
                if checked["operation_completion"] == "unknown":
                    block("journal_unknown_operations")
                if count:
                    result["warnings"].append(
                        "This task already has operation history. Reuse only for the same job; report its full ledger. Start a fresh run for a new job."
                    )
            except (ReportError, OSError):
                result["journal"] = "unavailable"
                block("journal_unavailable")
        else:
            result["journal"] = "scope_required"
            block("journal_scope_required")
    result["blockers"] = blockers
    result["prerequisite_status"] = "blocked" if blockers else "met"
    result["qualification"] = (
        "Prerequisites only. Window identity, current state, effects and job completion require separate checks."
    )
    return result
