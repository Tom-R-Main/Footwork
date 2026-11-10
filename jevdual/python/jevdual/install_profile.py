"""Describe installed optional distributions without importing their runtimes.

Python does not retain the extras requested by an earlier installer. These are
observed capabilities, not a claim about the command that installed them.
"""

from __future__ import annotations

import importlib.metadata


def installation() -> dict:
    versions = {}
    for extra, distribution in (("desktop", "cua-driver"), ("agent", "browser-use"), ("tools", "mujoco")):
        try:
            versions[extra] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[extra] = None
    extras = [extra for extra, version in versions.items() if version is not None]
    native, agent = "desktop" in extras, "agent" in extras
    profile = "full" if native and agent else "desktop" if native else "agent" if agent else "light"
    return {
        "profile": profile,
        "observed_extras": extras,
        "optional_versions": versions,
        "basis": "installed distributions; requested extras are not retained by Python",
        "light_install": "Install the light bundle, or the Footwork wheel without extras using --only-binary :all:.",
        "full_install": "Install the matching full Footwork bundle with its pinned cua-driver wheel.",
        "runtime_qualification": "not_checked",
    }
