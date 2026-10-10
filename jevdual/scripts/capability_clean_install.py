"""Fresh-cache binary dependency installation into one owned environment.

No global installs, existing dependency borrowing or repository configuration.
The host OS/interpreter prerequisites remain explicitly outside this isolation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def isolated_environment() -> dict[str, str]:
    env = {}
    for name, value in os.environ.items():
        if name in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CONDA_PREFIX", "JEVDUAL_PURE_PY"}:
            continue
        if name.startswith(("UV_", "PIP_")) or name.endswith(("_KEY", "_TOKEN", "_SECRET")):
            continue
        env[name] = value
    env["PYTHONNOUSERSITE"] = "1"
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    root, wheel = args.run_dir.resolve(), args.wheel.resolve()
    if not root.is_relative_to(PROJECT / "output") or not wheel.is_file():
        parser.error("owned output run and existing wheel required")
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    cwd, cache, venv = root / "outside-source", root / "empty-cache", root / "venv"
    cwd.mkdir(mode=0o700)
    cache.mkdir(mode=0o700)
    env = isolated_environment()
    uv = shutil.which("uv")
    if not uv:
        parser.error("existing uv executable required; no installer invoked")
    interpreter = os.path.abspath(args.python)
    common = [uv, "--no-config", "--no-progress", "--cache-dir", str(cache), "--no-python-downloads"]
    receipt = {
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True
        ).strip(),
        "host": {"platform": platform.system(), "machine": platform.machine()},
        "interpreter_requested": interpreter,
        "wheel": str(wheel),
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "cache_initially_empty": not list(cache.iterdir()),
        "system_site_packages": False,
        "borrowed_dependencies": False,
        "registry": "https://pypi.org/simple",
        "binary_only": True,
        "commands": [],
        "passed": False,
        "limits": "Fresh dependencies on existing host OS/interpreter, not a fresh machine or TCC permission database.",
    }

    def run(name, command, timeout=300):
        receipt["commands"].append({"stage": name, "argv": command})
        with (
            (root / (name + ".stdout.log")).open("w") as out,
            (root / (name + ".stderr.log")).open("w") as err,
        ):
            try:
                proc = subprocess.run(
                    command, cwd=cwd, env=env, stdout=out, stderr=err, check=False, timeout=timeout
                )
                code = proc.returncode
            except subprocess.TimeoutExpired:
                code = -1
        receipt["commands"][-1]["returncode"] = code
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"stage": name, "returncode": code}), flush=True)
        return code == 0

    if not run("venv", common + ["venv", "--python", interpreter, str(venv)]):
        return 1
    assert "include-system-site-packages = false" in (venv / "pyvenv.cfg").read_text()
    python = str(venv / "bin/python")
    if not run(
        "install",
        common
        + [
            "pip",
            "install",
            "--python",
            python,
            "--default-index",
            "https://pypi.org/simple",
            "--only-binary",
            ":all:",
            str(wheel),
        ],
    ):
        return 1
    if not run("consistency", common + ["pip", "check", "--python", python]):
        return 1
    if not run("inventory", common + ["pip", "list", "--python", python, "--format", "json"]):
        return 1
    probe = """
import sys,json,importlib.metadata,importlib
from pathlib import Path
import jevdual,jevdual.capability.execution_worker as worker
from jevdual._native import BACKEND
names=("cua_driver","psutil","mcp","ApplicationServices","Quartz","Foundation","packaging")
modules={n:str(importlib.import_module(n).__file__) for n in names}
print(json.dumps({"version":sys.version,"prefix":sys.prefix,"base_prefix":sys.base_prefix,"python":sys.executable,"package":jevdual.__file__,"worker":worker.__file__,"backend":BACKEND,"module_origins":modules,"sys_path":sys.path}))
"""
    if not run("origins", [python, "-c", probe], timeout=30):
        return 1
    origins = json.loads((root / "origins.stdout.log").read_text())
    assert origins["prefix"] == str(venv) and origins["backend"] == "pure-python"
    assert Path(origins["package"]).is_relative_to(venv)
    assert Path(origins["worker"]).is_relative_to(venv)
    assert all(Path(p).is_relative_to(venv) for p in origins["module_origins"].values())
    assert not any(
        p.endswith("footwork/jevdual/python") or ("site-packages" in p and not Path(p).is_relative_to(venv))
        for p in origins["sys_path"]
    )
    receipt["origins"] = origins
    if not run("doctor", [str(venv / "bin/footwork-capability"), "doctor"], timeout=30):
        return 1
    receipt["doctor"] = json.loads((root / "doctor.stdout.log").read_text())
    receipt["inventory"] = json.loads((root / "inventory.stdout.log").read_text())
    receipt["passed"] = True
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {"passed": True, "packages": len(receipt["inventory"]), "python": origins["version"].split()[0]}
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
