"""Compile and package CUA's exact reference source; never starts the Driver."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_spec = importlib.util.spec_from_file_location(
    "cua_driver_build_support", Path(__file__).with_name("build_support.py")
)
_support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_support)


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name != "wheel":
            return
        tag, include = _support.build_native(Path(self.root))
        build_data["tag"] = tag
        build_data["pure_python"] = False
        build_data.setdefault("force_include", {}).update(include)
