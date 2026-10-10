"""Check the consumer wheel and installed CLI without dependencies or native input.

Uses an existing interpreter and uv. Installs only the local artifact, offline,
inside a new owned run. This is artifact qualification, not native readiness.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from build_capability_wheel import build, verify
from capability_clean_install import isolated_environment

PROJECT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    if not root.is_relative_to(PROJECT / "output"):
        parser.error("Use a new owned directory under the project's output directory")
    uv = shutil.which("uv")
    if not uv:
        parser.error("An existing uv executable is required")
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    cwd, cache, venv = root / "shadow-host", root / "empty-cache", root / "venv"
    for path in (cwd, cache):
        path.mkdir(mode=0o700)
    for name in ("private-home", "private-config", "private-cache", "private-temp"):
        (root / name).mkdir(mode=0o700)
    for name in ("jevdual", "psutil", "mcp", "cua_driver"):
        package = cwd / name
        package.mkdir()
        (package / "__init__.py").write_text('raise RuntimeError("HOST_CWD_SHADOW")\n')
    env = isolated_environment(root)
    receipt = {"passed": False, "commands": [], "native_qualification": False}

    def save():
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def require(condition, gate):
        if not condition:
            raise ValueError(gate)

    def run(stage, command, expected=0, stdin=None):
        record = {"stage": stage, "argv": command, "returncode": None}
        receipt["commands"].append(record)
        save()
        stdout = root / f"{stage}.stdout.log"
        with stdout.open("w") as out, (root / f"{stage}.stderr.log").open("w") as err:
            proc = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                stdout=out,
                stderr=err,
                text=True,
                input=stdin,
                timeout=120,
                check=False,
            )
        record["returncode"] = proc.returncode
        save()
        require(proc.returncode == expected, stage + "_exit")
        return stdout.read_text()

    try:
        first = build(PROJECT / "jevdual", root / "build-one")
        second = build(PROJECT / "jevdual", root / "build-two")
        require(first.read_bytes() == second.read_bytes(), "reproducible_build")
        receipt["artifact"] = verify(first, PROJECT / "jevdual")
        common = [uv, "--no-config", "--no-progress", "--cache-dir", str(cache), "--no-python-downloads"]
        run("venv", common + ["venv", "--python", os.path.abspath(args.python), str(venv)])
        require("include-system-site-packages = false" in (venv / "pyvenv.cfg").read_text(), "system_site")
        python = str(venv / "bin/python")
        run("install", common + ["pip", "install", "--offline", "--no-deps", "--python", python, str(first)])
        probe = """
import sys,json,importlib.metadata
import jevdual,jevdual.capability.cli as cli
dist=importlib.metadata.distribution('jevdual')
print(json.dumps({'prefix':sys.prefix,'base_prefix':sys.base_prefix,'package':jevdual.__file__,
 'cli':cli.__file__,'backend':jevdual.BACKEND,'license':dist.metadata['License-Expression'],
 'requirements':dist.requires,'entry_points':{e.name:e.value for e in dist.entry_points},
 'sys_path':sys.path}))
"""
        origins = json.loads(run("origins", [python, "-I", "-c", probe]))
        require(origins["prefix"] == str(venv) and origins["base_prefix"] != str(venv), "venv_origin")
        require(all(Path(origins[key]).is_relative_to(venv) for key in ("package", "cli")), "module_origin")
        require(origins["backend"] == "pure-python" and origins["license"] == "MIT", "backend_license")
        require(
            origins["entry_points"].get("footwork-capability") == "jevdual.capability.cli:main", "entry_point"
        )
        require(bool(origins["requirements"]), "dependency_metadata")
        require(
            not any("site-packages" in p and not Path(p).is_relative_to(venv) for p in origins["sys_path"]),
            "borrowed_site",
        )
        receipt["origins"] = origins
        run("entry-help", [str(venv / "bin/footwork-capability"), "--help"])
        cli = [python, "-I", "-m", "jevdual.capability.cli"]
        normal = json.loads(run("doctor", cli + ["doctor"]))
        strict = json.loads(run("strict-doctor", cli + ["doctor", "--strict"], expected=1))
        require(
            normal["prerequisite_status"] == strict["prerequisite_status"] == "blocked", "bare_prerequisites"
        )
        journal = root / "absent.sqlite"
        claim = json.dumps({"completion": "completed", "operations": [], "persistence": "not_checked"})
        report = json.loads(
            run(
                "report",
                cli + ["report", "--journal", str(journal), "--task", "ci-artifact"],
                expected=2,
                stdin=claim,
            )
        )
        require(
            report["operation_completion"] == "unknown" and report["validation"]["accepted"] is False,
            "missing_journal_completion",
        )
        require(not journal.exists(), "report_created_journal")
        receipt["doctor"] = strict
        receipt["report"] = report
        receipt["passed"] = True
        save()
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        receipt["failure"] = type(exc).__name__
        if isinstance(exc, ValueError):
            receipt["failed_gate"] = str(exc)
        save()
        return 1
    print(
        json.dumps({"passed": True, "artifact": receipt["artifact"], "receipt": str(root / "receipt.json")})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
