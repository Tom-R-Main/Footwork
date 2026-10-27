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
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument("--python", default="3.12")
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
    uv = shutil.which("uv")
    if not uv:
        parser.error("uv is required; no system installer is invoked")
    subprocess.run([uv, "venv", "--python", args.python, str(venv)], check=True)
    python = venv / ("Scripts/python.exe" if __import__("os").name == "nt" else "bin/python")
    product = str(root / manifest["product"])
    if not args.core_only:
        product += "[tools]"
    command = [uv, "pip", "install", "--python", str(python), "--find-links", str(root),
               product, str(root / manifest["cua"])]
    if args.offline:
        command.append("--offline")
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
