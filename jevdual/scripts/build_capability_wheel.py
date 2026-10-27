"""Build and verify an offline pure-Python wheel using the standard library.

The accelerated maturin build remains separate. No dependency is downloaded.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

REQUIRED = {
    "jevdual/__init__.py",
    "jevdual/arbiter.toml",
    "jevdual/_native.py",
    "jevdual/capability/cli.py",
    "jevdual/capability/mcp_server.py",
    "jevdual/capability/completion.py",
    "jevdual/capability/execution_worker.py",
    "jevdual/capability/setup.py",
}


def digest(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def inventory(root: Path) -> tuple[str, dict[str, bytes]]:
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    name = re.sub(r"[-_.]+", "_", project["name"])
    version = project["version"]
    if not re.fullmatch(r"[A-Za-z0-9_]+", name) or not re.fullmatch(r"[A-Za-z0-9_.]+", version):
        raise ValueError("Unsupported distribution identity")
    dist = f"{name}-{version}.dist-info"
    source = root / "python" / "jevdual"
    if source.is_symlink():
        raise ValueError("Package root must not be a symlink")
    files = {}
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("Source symlinks cannot be packaged")
        resource = path.is_relative_to(source / "_tool_resources")
        if path.is_file() and (
            path.suffix == ".py" or path == source / "arbiter.toml"
            or (resource and path.suffix in {".mjs", ".json", ".xml", ".html", ".swift", ".txt", ".md"})
        ):
            files[path.relative_to(root / "python").as_posix()] = path.read_bytes()
    license_path = root.parent / "LICENSE"
    if source.is_symlink() or license_path.is_symlink():
        raise ValueError("Package roots and license must not be symlinks")
    files[f"{dist}/licenses/LICENSE"] = license_path.read_bytes()
    metadata = [
        "Metadata-Version: 2.4",
        f"Name: {project['name']}",
        f"Version: {version}",
        f"Summary: {project['description']}",
        f"Requires-Python: {project['requires-python']}",
        "License-Expression: MIT",
        "License-File: LICENSE",
    ]
    metadata.extend(f"Requires-Dist: {dep}" for dep in project["dependencies"])
    for extra, dependencies in project.get("optional-dependencies", {}).items():
        metadata.append(f"Provides-Extra: {extra}")
        metadata.extend(f'Requires-Dist: {dep}; extra == "{extra}"' for dep in dependencies)
    files[f"{dist}/METADATA"] = ("\n".join(metadata) + "\n\n").encode()
    files[f"{dist}/WHEEL"] = (
        b"Wheel-Version: 1.0\nGenerator: footwork-stdlib\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    )
    scripts = "\n".join(f"{key} = {value}" for key, value in sorted(project["scripts"].items()))
    files[f"{dist}/entry_points.txt"] = ("[console_scripts]\n" + scripts + "\n").encode()
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows((key, digest(value), str(len(value))) for key, value in sorted(files.items()))
    writer.writerow((f"{dist}/RECORD", "", ""))
    files[f"{dist}/RECORD"] = output.getvalue().encode()
    return f"{name}-{version}-py3-none-any.whl", files


def verify(wheel: Path, root: Path) -> dict:
    expected_name, expected = inventory(root)
    if wheel.name != expected_name:
        raise ValueError("Wheel filename does not match project identity")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Wheel inventory differs from allowed source inventory")
        if not REQUIRED.issubset(names):
            raise ValueError("Required runtime resource is absent")
        for name in names:
            if archive.read(name) != expected[name]:
                raise ValueError(f"Artifact bytes differ: {name}")
        record = next(name for name in names if name.endswith(".dist-info/RECORD"))
        rows = list(csv.reader(io.StringIO(archive.read(record).decode())))
        if {row[0] for row in rows} != set(names) or len(rows) != len(names):
            raise ValueError("RECORD inventory mismatch")
        for name, hashed, size in rows:
            data = archive.read(name)
            if name == record:
                if hashed or size:
                    raise ValueError("RECORD self entry must be empty")
            elif hashed != digest(data) or size != str(len(data)):
                raise ValueError("RECORD hash or size mismatch")
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        if metadata["License-Expression"] != "MIT":
            raise ValueError("License declaration missing")
        dist = metadata_name.rsplit("/", 1)[0]
        for license_file in metadata.get_all("License-File", []):
            if f"{dist}/licenses/{license_file}" not in names:
                raise ValueError("Declared license file is absent")
    return {
        "wheel": str(wheel.resolve()),
        "files": len(names),
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "verified": True,
    }


def build(root: Path, output: Path) -> Path:
    filename, files = inventory(root)
    output.mkdir(parents=True, exist_ok=True)
    wheel = output / filename
    # Exclusive creation avoids replacing a previous artifact silently.
    with (
        wheel.open("xb") as stream,
        zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive,
    ):
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    verify(wheel, root)
    return wheel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if bool(args.output) == bool(args.verify):
        parser.error("Choose --output or --verify")
    wheel = args.verify or build(root, args.output)
    print(json.dumps(verify(wheel, root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
