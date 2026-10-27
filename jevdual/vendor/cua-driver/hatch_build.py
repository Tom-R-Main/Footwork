"""Build unchanged upstream CUA Python bindings with checksum-pinned binaries."""

from __future__ import annotations

import importlib.util
import os
import shutil
import ssl
import tempfile
import urllib.request
from pathlib import Path

import certifi
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_spec = importlib.util.spec_from_file_location(
    "cua_driver_build_support", Path(__file__).with_name("build_support.py")
)
_support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_support)
VERSION = _support.VERSION
BASE_URL = _support.BASE_URL
TARGETS = _support.TARGETS
native_target = _support.native_target
verify = _support.verify
extract_selected = _support.extract_selected


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name != "wheel":
            return
        system, arch = native_target()
        extension, tag, checksum, names = TARGETS[(system, arch)]
        filename = f"cua-driver-rs-{VERSION}-{system}-{arch}-binary.{extension}"
        cache = Path(self.root) / ".native-cache"
        cache.mkdir(exist_ok=True)
        archive = cache / filename
        if not archive.exists():
            with tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
                temporary = Path(stream.name)
            try:
                context = ssl.create_default_context(cafile=certifi.where())
                with (
                    urllib.request.urlopen(
                        f"{BASE_URL}/{filename}", timeout=120, context=context
                    ) as response,
                    temporary.open("wb") as output,
                ):
                    shutil.copyfileobj(response, output)
                verify(temporary, checksum)
                os.replace(temporary, archive)
            finally:
                temporary.unlink(missing_ok=True)
        verify(archive, checksum)
        self._staging = tempfile.TemporaryDirectory(prefix="cua-driver-wheel-")
        destination = Path(self._staging.name)
        extract_selected(archive, names, destination)
        build_data["tag"] = tag
        build_data["pure_python"] = False
        include = build_data.setdefault("force_include", {})
        for name in names:
            relative = (
                f"cua_driver/{name}" if name.endswith((".dylib", ".so", ".dll")) else f"cua_driver/bin/{name}"
            )
            include[str(destination / name)] = relative

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        if hasattr(self, "_staging"):
            self._staging.cleanup()
