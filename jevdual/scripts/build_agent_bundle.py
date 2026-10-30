"""Build one portable installer bundle for this host's Footwork and CUA wheels."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

from build_capability_wheel import build

INSTALLER = '''"""Install the verified Footwork bundle into one new isolated environment."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def target_matches(filename, host):
    """Accept the host-specific tags emitted by the pinned CUA build only."""
    try:
        _, python, abi, target = filename[:-4].rsplit("-", 3)
    except ValueError:
        return False
    if python != "py3" or abi != "none":
        return False
    arch = {"amd64": "x86_64", "aarch64": "arm64"}.get(host["machine"].lower(), host["machine"].lower())
    if host["system"] == "Linux":
        return target == "linux_" + {"arm64": "aarch64"}.get(arch, arch)
    if host["system"] == "Windows":
        return target == "win_" + {"x86_64": "amd64"}.get(arch, arch)
    if host["system"] == "Darwin":
        parts = target.split("_")
        if len(parts) < 4 or parts[0] != "macosx":
            return False
        try:
            minimum = (int(parts[1]), int(parts[2]))
            current = tuple(int(p) for p in host["macos"].split(".")[:2])
        except ValueError:
            return False
        return "_".join(parts[3:]) == arch and current >= minimum
    return False


def interpreter(requested, parser):
    candidate = shutil.which(requested)
    if candidate is None and requested.replace(".", "").isdigit():
        candidate = shutil.which("python" + requested)
    if candidate is None:
        parser.error("requested Python is not installed; no interpreter will be downloaded")
    probe = (
        "import json,platform,sys,importlib.util,importlib.metadata;"
        "print(json.dumps(dict(system=platform.system(),machine=platform.machine(),"
        "macos=platform.mac_ver()[0],version=list(sys.version_info[:2]),"
        "venv=importlib.util.find_spec('venv') is not None,"
        "ensurepip=importlib.util.find_spec('ensurepip') is not None,"
        "pip=importlib.metadata.version('pip') if importlib.util.find_spec('pip') else None)))"
    )
    try:
        result = subprocess.run([candidate, "-I", "-c", probe], check=True, capture_output=True, text=True)
        host = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.CalledProcessError):
        parser.error("cannot inspect the requested Python interpreter")
    if not [3, 11] <= host["version"] < [4, 0]:
        parser.error("Footwork requires an installed Python >=3.11,<4.0")
    return candidate, host


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable, help="existing interpreter path, name, or version")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--core-only", action="store_true", help="omit optional simulator dependencies")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "MANIFEST.json").read_text())
    for name, digest in manifest["files"].items():
        if Path(name).name != name:
            parser.error("invalid bundle member")
        path = root / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            parser.error("bundle checksum mismatch: " + name)
    for role in ("product", "cua"):
        name = manifest.get(role)
        if not isinstance(name, str) or Path(name).name != name or name not in manifest["files"]:
            parser.error("invalid bundle wheel role: " + role)
        if not name.endswith(".whl"):
            parser.error("bundle role must identify a verified wheel")
    venv = args.venv.absolute()
    if venv.exists() or venv.is_symlink():
        parser.error("choose a new environment; existing environments are never overwritten")
    selected_python, host = interpreter(args.python, parser)
    if not target_matches(manifest["cua"], host):
        parser.error("CUA wheel is incompatible with this Python host; obtain a bundle built for its OS and architecture")
    uv = shutil.which("uv")
    bundled_pip = False
    if not uv:
        try:
            pip_version = tuple(int(p) for p in (host["pip"] or "0").split(".")[:2])
        except ValueError:
            pip_version = (0,)
        bundled_pip = pip_version < (22, 3)
        if not host["venv"] or (bundled_pip and not host["ensurepip"]):
            parser.error("without uv, the selected Python needs venv and either pip >=22.3 or bundled ensurepip; no tools are downloaded")
        # venv's ensurepip seeds only the new environment from Python's bundled wheels.
        # Existing base pip can instead manage an unseeded environment via --python.
        command = [selected_python, "-I", "-m", "venv"]
        if not bundled_pip:
            command.append("--without-pip")
        subprocess.run([*command, str(venv)], check=True)
    else:
        subprocess.run([uv, "venv", "--no-python-downloads", "--python", selected_python, str(venv)], check=True)
    python = venv / ("Scripts/python.exe" if __import__("os").name == "nt" else "bin/python")
    product = str(root / manifest["product"])
    if not args.core_only:
        product += "[tools]"
    if uv:
        command = [uv, "pip", "install", "--python", str(python)]
    elif bundled_pip:
        command = [str(python), "-I", "-m", "pip", "--isolated", "install", "--disable-pip-version-check"]
    else:
        command = [selected_python, "-I", "-m", "pip", "--isolated", "--python", str(python),
                   "install", "--disable-pip-version-check"]
    command += ["--only-binary", ":all:", "--find-links", str(root), product, str(root / manifest["cua"])]
    if args.offline:
        command.append("--offline" if uv else "--no-index")
    subprocess.run(command, check=True)
    executable = venv / ("Scripts/footwork.exe" if __import__("os").name == "nt" else "bin/footwork")
    subprocess.run([str(executable), "tools"], check=True)
    print(json.dumps({"installed": True, "executable": str(executable), "environment": str(venv)}))


if __name__ == "__main__":
    main()
'''


def build_bundle(output: Path, cua_wheel: Path | None = None) -> dict:
    root = Path(__file__).resolve().parents[1]
    output.mkdir(parents=True, exist_ok=False)
    if cua_wheel is None:
        subprocess.run(["uv", "build", str(root / "vendor/cua-driver"), "--wheel", "--out-dir", str(output)],
                       check=True)
        candidates = list(output.glob("cua_driver-*.whl"))
        if len(candidates) != 1:
            raise ValueError("exactly one built CUA wheel required")
        cua_wheel = candidates[0]
    else:
        if cua_wheel.is_symlink() or not cua_wheel.is_file():
            raise ValueError("CUA wheel must be a regular file")
        cua_wheel = cua_wheel.resolve()
        copied = output / cua_wheel.name
        shutil.copyfile(cua_wheel, copied)
        cua_wheel = copied
    with zipfile.ZipFile(cua_wheel) as archive:
        metadata = [n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
        if len(metadata) != 1:
            raise ValueError("invalid CUA wheel metadata")
        parsed = BytesParser().parsebytes(archive.read(metadata[0]))
    import tomllib
    config = tomllib.loads((root / 'pyproject.toml').read_text())
    pin = next(d.split('==', 1)[1] for d in config['project']['dependencies'] if d.startswith('cua-driver=='))
    if parsed['Name'] != 'cua-driver' or parsed['Version'] != pin:
        raise ValueError("CUA wheel does not match the exact source pin")
    product = build(root, output)
    (output / 'install.py').write_text(INSTALLER)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.iterdir()) if p.is_file()}
    manifest = {'schema_version': 1, 'product': product.name, 'cua': cua_wheel.name, 'files': files}
    (output / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cua-wheel', type=Path)
    args = parser.parse_args()
    result = build_bundle(args.output.resolve(), args.cua_wheel)
    print(json.dumps({'bundle': str(args.output.resolve()), **result}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'Bundle build failed: {exc}', file=sys.stderr)
        raise SystemExit(1) from exc
