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
import re
import shutil
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def source_commit(project: Path) -> str:
    """Packet provenance never calls Git or the macOS developer-tools shim."""
    manifest = project / "MANIFEST.json"
    if manifest.exists() or manifest.is_symlink():
        if manifest.is_symlink() or not manifest.is_file():
            raise ValueError("Packet manifest must be a regular file")
        payload = json.loads(manifest.read_text())
        commit = payload.get("source_commit") if isinstance(payload, dict) else None
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Packet manifest requires a full immutable source commit")
        return commit
    if (project / ".git").exists():
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip()
    return "unavailable"


def isolated_environment(state_root: Path | None = None) -> dict[str, str]:
    env = {}
    for name, value in os.environ.items():
        if name in {
            "PYTHONPATH",
            "PYTHONHOME",
            "VIRTUAL_ENV",
            "CONDA_PREFIX",
            "JEVDUAL_PURE_PY",
            "PYTHONOPTIMIZE",
        }:
            continue
        if name.startswith(("UV_", "PIP_")) or name.endswith(("_KEY", "_TOKEN", "_SECRET")):
            continue
        env[name] = value
    env["PYTHONNOUSERSITE"] = "1"
    env["ANONYMIZED_TELEMETRY"] = "false"
    env["BROWSER_USE_CLOUD_SYNC"] = "false"
    if state_root is not None:
        state_root = state_root.resolve()
        for name, suffix in {
            "HOME": "private-home",
            "XDG_CONFIG_HOME": "private-config",
            "XDG_CACHE_HOME": "private-cache",
            "TMPDIR": "private-temp",
            "TMP": "private-temp",
            "TEMP": "private-temp",
        }.items():
            env[name] = str(state_root / suffix)
        env["BROWSER_USE_CONFIG_DIR"] = str(state_root / "private-config/browseruse")
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(state_root / "private-cache/playwright")
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--find-links", type=Path, help="Local wheelhouse containing the built CUA dependency")
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    root, wheel = args.run_dir.resolve(), args.wheel.resolve()
    if not root.is_relative_to(PROJECT / "output") or not wheel.is_file():
        parser.error("owned output run and existing wheel required")
    wheelhouse = args.find_links.resolve() if args.find_links else None
    if wheelhouse is not None and not wheelhouse.is_dir():
        parser.error("--find-links requires an existing wheelhouse directory")
    cua_wheels = sorted(wheelhouse.glob("cua_driver-*.whl")) if wheelhouse else []
    if wheelhouse is not None and len(cua_wheels) != 1:
        parser.error("--find-links requires exactly one CUA wheel for this installation platform")
    provenance = source_commit(PROJECT)
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    cwd, cache, venv = root / "outside-source", root / "empty-cache", root / "venv"
    cwd.mkdir(mode=0o700)
    cache.mkdir(mode=0o700)
    for suffix in ("private-home", "private-config", "private-cache", "private-temp"):
        (root / suffix).mkdir(mode=0o700)
    env = isolated_environment(root)
    uv = shutil.which("uv")
    if not uv:
        parser.error("existing uv executable required; no installer invoked")
    interpreter = os.path.abspath(args.python)
    common = [uv, "--no-config", "--no-progress", "--cache-dir", str(cache), "--no-python-downloads"]
    receipt = {
        "source_commit": provenance,
        "host": {"platform": platform.system(), "machine": platform.machine()},
        "interpreter_requested": interpreter,
        "wheel": str(wheel),
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "cache_initially_empty": not list(cache.iterdir()),
        "system_site_packages": False,
        "borrowed_dependencies": False,
        "registry": "https://pypi.org/simple",
        "binary_only": True,
        "local_dependency_wheels": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(wheelhouse.glob("*.whl"))
        } if wheelhouse else {},
        "commands": [],
        "passed": False,
        "limits": "Fresh dependencies on existing host OS/interpreter, not a fresh machine or TCC permission database.",
    }

    def run(name, command, timeout=300):
        receipt["commands"].append({"stage": name, "argv": command})
        stdout_log = root / (name + ".stdout.log")
        stderr_log = root / (name + ".stderr.log")
        timed_out = False
        with (
            stdout_log.open("w") as out,
            stderr_log.open("w") as err,
        ):
            try:
                proc = subprocess.run(
                    command, cwd=cwd, env=env, stdout=out, stderr=err, check=False, timeout=timeout
                )
                code = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                code = -1
        receipt["commands"][-1].update(returncode=code, timed_out=timed_out)
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        report = {"stage": name, "returncode": code}
        if code != 0:
            # Bound console output; the full logs remain in the uploaded artifact.
            # JSON quoting keeps child output from becoming workflow commands.
            with stderr_log.open("rb") as err:
                err.seek(max(0, stderr_log.stat().st_size - 4096))
                tail = err.read(4096).decode("utf-8", errors="replace")
            report.update(
                timed_out=timed_out,
                stderr_tail=tail,
                stdout_log=str(stdout_log),
                stderr_log=str(stderr_log),
            )
        print(json.dumps(report), flush=True)
        return code == 0

    def require(condition, code):
        if not condition:
            receipt.setdefault("failed_gates", []).append(code)
            (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps({"failed_gate": code}), flush=True)
        return bool(condition)

    if not run("venv", common + ["venv", "--python", interpreter, str(venv)]):
        return 1
    if not require(
        "include-system-site-packages = false" in (venv / "pyvenv.cfg").read_text(), "system_site_inheritance"
    ):
        return 1
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
        ]
        + (["--find-links", str(wheelhouse)] if wheelhouse else [])
        + [
            str(wheel),
        ]
        + [str(path) for path in cua_wheels],
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
    if not run("origins", [python, "-I", "-c", probe], timeout=30):
        return 1
    origins = json.loads((root / "origins.stdout.log").read_text())
    if not all(
        (
            require(
                origins["prefix"] == str(venv) and origins["backend"] == "pure-python", "interpreter_backend"
            ),
            require(
                Path(origins["package"]).is_relative_to(venv)
                and Path(origins["worker"]).is_relative_to(venv),
                "product_origin",
            ),
            require(
                all(Path(p).is_relative_to(venv) for p in origins["module_origins"].values()),
                "dependency_origin",
            ),
            require(
                not any(
                    p.endswith("footwork/jevdual/python")
                    or ("site-packages" in p and not Path(p).is_relative_to(venv))
                    for p in origins["sys_path"]
                ),
                "import_path_borrow",
            ),
        )
    ):
        return 1
    receipt["origins"] = origins
    if not run("doctor", [str(venv / "bin/footwork-capability"), "doctor"], timeout=30):
        return 1
    receipt["doctor"] = json.loads((root / "doctor.stdout.log").read_text())
    receipt["inventory"] = json.loads((root / "inventory.stdout.log").read_text())
    tag_probe = 'import json,importlib.metadata;print(json.dumps([{"name":d.metadata["Name"],"version":d.version,"tags":[l[5:] for l in (d.read_text("WHEEL") or "").splitlines() if l.startswith("Tag: ")]} for d in importlib.metadata.distributions()]))'
    if not run("wheel-tags", [python, "-I", "-c", tag_probe], timeout=30):
        return 1
    receipt["wheel_tags"] = json.loads((root / "wheel-tags.stdout.log").read_text())
    receipt["cache_bytes_after_install"] = sum(p.stat().st_size for p in cache.rglob("*") if p.is_file())
    receipt["private_state"] = {
        name: str(root / name) for name in ("private-home", "private-config", "private-cache", "private-temp")
    }
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
