"""Read-only host prerequisites; runnable with Python alone, including outside a checkout.

No subprocesses, network requests, native imports, permission prompts, or app startup.
Presence of a binary or session variable is not a successful runtime observation.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shlex
import shutil
import sys
from pathlib import Path, PurePosixPath

_TOOLS = (
    "uv", "pip", "pip3", "rustc", "cargo", "rustup", "cc", "clang", "pkg-config",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "dbus-run-session", "dbus-send", "gdbus", "Xvfb", "node", "ffmpeg", "tesseract",
)
_SESSION = ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR")


def _read(path: Path, limit: int = 65536) -> str | None:
    try:
        with path.open("rb") as stream:
            content = stream.read(limit + 1)
        if len(content) > limit:
            return None
        return content.decode("utf-8", errors="replace")
    except OSError:
        return None


def _number(value: str | None) -> int | None:
    try:
        number = int(value or "")
        return number if number >= 0 else None
    except ValueError:
        return None


def _distribution(path: Path) -> dict[str, str]:
    result = {}
    for line in (_read(path) or "").splitlines():
        key, _, value = line.partition("=")
        if key not in {"ID", "VERSION_ID", "PRETTY_NAME"}:
            continue
        try:
            words = shlex.split(value, comments=True)
        except ValueError:
            continue
        if len(words) == 1:
            result[key] = words[0][:256]
    return result


def _memory(path: Path) -> dict[str, int | None]:
    values = {}
    for line in (_read(path) or "").splitlines():
        key, _, value = line.partition(":")
        parts = value.split()
        if key in {"MemTotal", "MemAvailable"} and len(parts) == 2 and parts[1] == "kB":
            number = _number(parts[0])
            values[key] = number * 1024 if number is not None else None
    return {"total_bytes": values.get("MemTotal"), "available_bytes": values.get("MemAvailable")}


def _hierarchy(root: Path, membership: str) -> list[Path]:
    """Include visible ancestors; namespace root files may be the only visible limits."""
    relative = PurePosixPath(membership).relative_to("/") if membership.startswith("/") else None
    if relative is None or ".." in relative.parts:
        return [root]
    target = root.joinpath(*relative.parts)
    return [root, *reversed(list(target.parents)[:len(relative.parts) - 1]), target] if relative.parts else [root]


def _cgroups(proc: Path, root: Path) -> dict:
    records = []
    membership = _read(proc / "self/cgroup")
    for line in (membership or "").splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            records.append(parts)
    memory_limits, memory_remaining, cpu_limits = [], [], []
    versions = set()
    for _, controllers, member in records:
        if controllers == "":
            versions.add(2)
            directories = _hierarchy(root, member)
            for directory in directories:
                limit = _number(_read(directory / "memory.max"))
                current = _number(_read(directory / "memory.current"))
                if limit is not None:
                    memory_limits.append(limit)
                    if current is not None:
                        memory_remaining.append(max(0, limit - current))
                quota = (_read(directory / "cpu.max") or "").split()
                if len(quota) == 2:
                    budget, period = _number(quota[0]), _number(quota[1])
                    if budget is not None and period:
                        cpu_limits.append(budget / period)
        else:
            versions.add(1)
            names = set(controllers.split(","))
            if "memory" in names:
                for directory in _hierarchy(root / "memory", member):
                    limit = _number(_read(directory / "memory.limit_in_bytes"))
                    current = _number(_read(directory / "memory.usage_in_bytes"))
                    # Common v1 unlimited sentinel is near signed LONG_MAX.
                    if limit is not None and limit < 2**60:
                        memory_limits.append(limit)
                        if current is not None:
                            memory_remaining.append(max(0, limit - current))
            if "cpu" in names:
                for mount in ("cpu", "cpu,cpuacct", "cpuacct,cpu"):
                    for directory in _hierarchy(root / mount, member):
                        budget = _number(_read(directory / "cpu.cfs_quota_us"))
                        period = _number(_read(directory / "cpu.cfs_period_us"))
                        if budget is not None and period:
                            cpu_limits.append(budget / period)
    return {
        "versions": sorted(versions),
        "membership_readable": membership is not None,
        "memory_limit_bytes": min(memory_limits, default=None),
        "memory_remaining_bytes": min(memory_remaining, default=None),
        "cpu_quota_cores": min(cpu_limits, default=None),
        "scope": "visible standard cgroup mounts and ancestors; hidden or custom mounts are unverified",
        "null_limit_meaning": "no finite limit observed, not proof of unlimited resources",
        **_task_and_swap_counters(records, root),
    }


def _events(path: Path, names: set[str]) -> dict | None:
    text = _read(path, 4096)
    if text is None:
        return None
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in names:
            number = _number(parts[1])
            if number is not None:
                values[parts[0]] = number
    return values or None


def _task_and_swap_counters(records: list, root: Path) -> dict:
    pids, remaining, swap, combined, snapshots = [], [], [], [], []
    visited = set()
    for _, controllers, member in records:
        names = set(controllers.split(','))
        mounts = [root] if not controllers else [root / c for c in ('pids', 'memory') if c in names]
        for mount in mounts:
            for directory in _hierarchy(mount, member)[:128]:
                if directory in visited or len(visited) >= 256:
                    continue
                visited.add(directory)
                limit, current = _number(_read(directory / 'pids.max')), _number(_read(directory / 'pids.current'))
                swap_limit = _number(_read(directory / 'memory.swap.max'))
                combined_limit = _number(_read(directory / 'memory.memsw.limit_in_bytes'))
                if limit is not None:
                    pids.append(limit)
                    if current is not None:
                        remaining.append(max(0, limit - current))
                if swap_limit is not None:
                    swap.append(swap_limit)
                if combined_limit is not None and combined_limit < 2**60:
                    combined.append(combined_limit)
                snapshot = {
                    'path': str(directory.relative_to(root)),
                    'pids_limit': limit, 'pids_current': current,
                    'pids_events': _events(directory / 'pids.events', {'max'}),
                    'swap_limit_bytes': swap_limit,
                    'swap_current_bytes': _number(_read(directory / 'memory.swap.current')),
                    'swap_events': _events(directory / 'memory.swap.events', {'high', 'max', 'fail'}),
                    'memory_events': _events(directory / 'memory.events', {'low', 'high', 'max', 'oom', 'oom_kill', 'oom_group_kill'}),
                    'memory_failcnt': _number(_read(directory / 'memory.failcnt')),
                    'memory_and_swap_failcnt': _number(_read(directory / 'memory.memsw.failcnt')),
                }
                if any(v is not None for k, v in snapshot.items() if k != 'path'):
                    snapshots.append(snapshot)
    return {'pids_limit': min(pids, default=None), 'pids_remaining_upper_bound': min(remaining, default=None),
            'swap_limit_bytes': min(swap, default=None),
            'memory_and_swap_limit_bytes': min(combined, default=None),
            'task_swap_event_snapshots': snapshots,
            'counter_scope': 'bounded visible hierarchy snapshots; missing/delegated/hidden counters remain unknown'}


def _supervision(proc: Path) -> dict:
    comm = _read(proc / '1/comm', 256)
    parent = None
    for line in (_read(proc / 'self/status') or '').splitlines():
        if line.startswith('PPid:'):
            parent = _number(line.partition(':')[2].strip())
    return {'pid1_comm': comm.strip() if comm else None, 'self_parent_pid': parent,
            'pid1_is_self': os.getpid() == 1,
            'orphan_reaping': 'not_checked', 'wait_ownership': 'not_checked'}


def _module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def probe(*, proc: Path = Path("/proc"), cgroup: Path = Path("/sys/fs/cgroup"),
          os_release: Path = Path("/etc/os-release")) -> dict:
    linux = sys.platform == "linux"
    memory = _memory(proc / "meminfo") if linux else {"total_bytes": None, "available_bytes": None}
    limits = _cgroups(proc, cgroup) if linux else None
    tools = {name: shutil.which(name) is not None for name in _TOOLS}
    session = {name: bool(os.environ.get(name)) for name in _SESSION}
    try:
        libc = os.confstr("CS_GNU_LIBC_VERSION") if linux else None
    except (ValueError, OSError):
        libc = None
    try:
        affinity = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        affinity = None
    candidates = [memory["available_bytes"]]
    if limits:
        candidates.append(limits["memory_remaining_bytes"])
    available = [value for value in candidates if value is not None]
    return {
        "schema_version": 1,
        "platform": sys.platform,
        "architecture": platform.machine()[:128],
        "kernel": platform.release()[:128],
        "libc": libc,
        "distribution": _distribution(os_release) if linux else {},
        "python": {"version": platform.python_version(), "pip_module": _module_present("pip"),
                   "venv_module": _module_present("venv"), "ensurepip_module": _module_present("ensurepip")},
        "resources": {"memory": memory, "cgroup": limits,
                      "available_memory_upper_bound_bytes": min(available, default=None),
                      "cpu_count": os.cpu_count(), "cpu_affinity_count": affinity},
        "process_supervision": _supervision(proc) if linux else None,
        "executables_present": tools,
        "session_indicators_present": session,
        "prerequisite_candidates": {
            "browser_executable": any(tools[name] for name in
                                      ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")),
            "graphical_session_indicator": session["DISPLAY"] or session["WAYLAND_DISPLAY"],
            "session_bus_indicator": session["DBUS_SESSION_BUS_ADDRESS"],
        },
        "runtime_qualification": "unverified",
        "effect_verification": "not_asserted",
        "limitations": [
            "Executable and environment presence do not establish connection, permissions, or driver support.",
            "No browser, desktop, accessibility service, native CUA library, or provider was started or queried.",
            "Resource values are a transient upper bound, not a reservation or build-capacity guarantee.",
            "Prebuilt installation avoids compilers; Python fallback does not replace native CUA desktop control.",
        ],
    }


def main() -> int:
    print(json.dumps(probe(), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
