"""Optional private runtime provenance; never execution authority or a receipt."""

from __future__ import annotations

import json
import logging
import os
import stat
import sys
import time
from pathlib import Path

MODULES = (
    "jevdual",
    "jevdual.capability.execution_worker",
    "cua_driver",
    "mcp",
    "ApplicationServices",
    "Quartz",
    "Foundation",
)


def runtime_context() -> dict:
    modules = {}
    for name in MODULES:
        module = sys.modules.get(name)
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        if module is None:
            modules[name] = None
        elif origin and origin not in ("built-in", "frozen"):
            modules[name] = [origin]
        else:
            modules[name] = list(getattr(spec, "submodule_search_locations", ()) or ())
    native = sys.modules.get("cua_driver._native")
    library = getattr(getattr(native, "_UniffiLib", None), "_name", None)
    return {
        "pid": os.getpid(),
        "python": sys.executable,
        "prefix": sys.prefix,
        "modules": modules,
        "cua_library": library,
        "home": str(Path.home()),
        "user_site_disabled": bool(sys.flags.no_user_site),
        "browser_telemetry_disabled": os.environ.get("ANONYMIZED_TELEMETRY") == "false",
        "browser_cloud_sync_disabled": os.environ.get("BROWSER_USE_CLOUD_SYNC") == "false",
        "as_of_ns": time.time_ns(),
    }


def emit_runtime_audit(role: str, operation: str | None = None) -> None:
    """Opt-in audit goes only to an existing private owned directory.

    Files are diagnostic data, outside the journal/packet/receipt contracts.
    An absent or failed audit never supplies completion evidence.
    """
    configured = os.environ.get("FOOTWORK_RUNTIME_AUDIT_DIR")
    if not configured:
        return
    try:
        directory = Path(configured)
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise OSError("Runtime audit directory is not private")
        if role not in ("server", "worker"):
            raise ValueError("Invalid runtime audit role")
        context = {"role": role, "operation": operation, **runtime_context()}
        name = f"{role}-{context['pid']}-{context['as_of_ns']}.json"
        fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(context, stream)
            stream.write("\n")
    except (OSError, ValueError, TypeError) as exc:
        logging.getLogger(__name__).warning("Runtime audit unavailable (%s)", type(exc).__name__)
