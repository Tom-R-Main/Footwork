"""Explicit external engine pins. Consumers never download or build an engine here."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

ARTIFACTS = {
    "darwin-arm64": {
        "name": "lightpanda-aarch64-macos", "asset_id": 694148451, "bytes": 93911048,
        "sha256": "273a4659510f8c48e6c5f26a2eee6aa20051632210cbf0f59975ac705056c44f",
    },
    "linux-x86_64": {
        "name": "lightpanda-x86_64-linux", "asset_id": 694146173, "bytes": 77129032,
        "sha256": "19f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3",
    },
}


def host_key() -> str:
    machine = platform.machine().lower()
    machine = {"aarch64": "arm64", "amd64": "x86_64"}.get(machine, machine)
    return f"{sys.platform}-{machine}"


def artifact(key: str | None = None) -> dict:
    selected = key or host_key()
    value = ARTIFACTS.get(selected)
    if value is None:
        return {"platform": selected, "available": False,
                "reason": "no qualified engine artifact for this platform; no source-build fallback"}
    return {"platform": selected, "available": True, **value,
            "repository": "lightpanda-io/browser", "release": "nightly",
            "asset_api_url": f"https://api.github.com/repos/lightpanda-io/browser/releases/assets/{value['asset_id']}",
            "download_accept": "application/octet-stream",
            "pin_semantics": "asset bytes and SHA256; the rolling release tag is not source identity"}


def executable(override: str | None = None) -> Path | None:
    selected = override or os.environ.get("FOOTWORK_LIGHTPANDA_EXECUTABLE") or shutil.which("lightpanda")
    try:
        return Path(selected).expanduser().resolve() if selected else None
    except (OSError, RuntimeError, ValueError):
        return None
