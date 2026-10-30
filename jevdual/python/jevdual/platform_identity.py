"""Read the kernel's boot incarnation; never synthesize identity on failure."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from uuid import UUID

_LINUX_BOOT_ID = Path("/proc/sys/kernel/random/boot_id")


def boot_identity() -> str:
    """Return the native boot identifier, preserving Darwin's existing spelling.

    Linux has no sysctl boot-session UUID. Its procfs boot_id is distinct from
    the persistent machine-id and must be available for restart identity.
    """
    if sys.platform == "darwin":
        value = subprocess.check_output(
            ["sysctl", "-n", "kern.bootsessionuuid"], text=True, timeout=2,
        ).strip()
        if not value:
            raise ValueError("kernel boot identity is empty")
        return value
    if sys.platform == "linux":
        with _LINUX_BOOT_ID.open("r", encoding="ascii") as stream:
            raw = stream.read(128)
        if len(raw) == 128:
            raise ValueError("kernel boot identity exceeds its read bound")
        value = raw.strip()
        try:
            parsed = UUID(value)
        except ValueError as exc:
            raise ValueError("kernel boot identity is not a UUID") from exc
        if not parsed.int or str(parsed) != value.lower():
            raise ValueError("kernel boot identity is not a nonzero canonical UUID")
        return str(parsed)
    raise ValueError("kernel boot identity is unsupported on this platform")
