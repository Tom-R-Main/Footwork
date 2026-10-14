"""Build a transportable, non-executing U2 qualification packet from fixed files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from build_capability_wheel import verify as verify_wheel

PROJECT = Path(__file__).resolve().parents[2]
HELPERS = (
    "verify_onboarding_packet.py",
    "capability_clean_install.py",
    "capability_fixture.py",
    "capability_fixture_config.py",
    "capability_host_trial.py",
    "capability_interrupt_trial.py",
    "capability_restart_trial.py",
    "capability_installed_trial.py",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_committed_wheel(name: str, data: bytes, commit: str, project: Path) -> None:
    """Verify runtime bytes against the requested immutable source, not the checkout."""
    output = project / "output"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="packet-wheel-check-", dir=output) as temporary:
        root = Path(temporary)
        package = root / "jevdual"
        package.mkdir()
        entries = subprocess.check_output(
            ["git", "ls-tree", "-r", "-z", commit, "--", "jevdual/python/jevdual"], cwd=project
        ).split(b"\0")
        paths = ["LICENSE", "jevdual/pyproject.toml"]
        for entry in entries:
            if not entry:
                continue
            relative = entry.split(b"\t", 1)[1].decode()
            if relative.endswith(".py") or relative == "jevdual/python/jevdual/arbiter.toml":
                paths.append(relative)
        for relative in paths:
            entries = subprocess.check_output(
                ["git", "ls-tree", "-z", commit, "--", relative], cwd=project
            ).split(b"\0")
            entries = [entry for entry in entries if entry]
            if len(entries) != 1:
                raise ValueError("Committed wheel source file is absent: " + relative)
            metadata, path = entries[0].split(b"\t", 1)
            mode, kind, _ = metadata.split()
            if mode not in (b"100644", b"100755") or kind != b"blob" or path.decode() != relative:
                raise ValueError("Committed wheel source must be a regular file")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(["git", "show", commit + ":" + relative], cwd=project))
        wheel = root / Path(name).name
        wheel.write_bytes(data)
        verify_wheel(wheel, package)


def inventory(wheel: Path, source_commit: str | None = None) -> dict[str, bytes]:
    source_commit = (
        source_commit or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip()
    )
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("A full immutable source commit is required")
    if wheel.is_symlink() or not wheel.is_file():
        raise ValueError("Wheel must be a regular nonsymlink file")
    verify_committed_wheel(wheel.name, wheel.read_bytes(), source_commit, PROJECT)
    sources = {
        "footwork/LICENSE": PROJECT / "LICENSE",
        "footwork/README.md": PROJECT / "jevdual/docs/independent-onboarding.md",
        "footwork/vm-plan.md": PROJECT / "jevdual/docs/onboarding-vm-plan.md",
        "footwork/installation.md": PROJECT / "jevdual/docs/capability-packaging.md",
        "footwork/artifacts/" + wheel.name: wheel,
    }
    sources.update(
        {"footwork/jevdual/scripts/" + name: PROJECT / "jevdual/scripts" / name for name in HELPERS}
    )
    files = {}
    for name, path in sources.items():
        if path == wheel:
            if path.is_symlink() or not path.is_file():
                raise ValueError("Wheel must be a regular nonsymlink file")
            files[name] = path.read_bytes()
            continue
        relative = path.relative_to(PROJECT).as_posix()
        entry = subprocess.check_output(
            ["git", "ls-tree", source_commit, "--", relative],
            cwd=PROJECT,
            stderr=subprocess.PIPE,
            text=True,
        ).split()
        if len(entry) != 4 or entry[0] not in ("100644", "100755") or entry[1] != "blob":
            raise ValueError("Frozen packet source must be a regular file")
        files[name] = subprocess.check_output(
            ["git", "show", source_commit + ":" + relative], cwd=PROJECT, stderr=subprocess.PIPE
        )
    manifest = {
        "schema_version": "1",
        "source_commit": source_commit,
        "wheel_sha256": sha(wheel.read_bytes()),
        "qualification": "not_performed",
        "automatic_execution": False,
        "members": {name: sha(data) for name, data in sorted(files.items())},
    }
    files["footwork/MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return files


def verify(packet: Path, wheel: Path, source_commit: str | None = None) -> dict:
    expected = inventory(wheel, source_commit)
    with zipfile.ZipFile(packet) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Packet inventory differs from its permitted files")
        for name, data in expected.items():
            if archive.read(name) != data:
                raise ValueError("Packet member differs: " + name)
        manifest = json.loads(archive.read("footwork/MANIFEST.json"))
        for name, digest in manifest["members"].items():
            if sha(archive.read(name)) != digest:
                raise ValueError("Packet manifest digest differs")
    return {
        "verified": True,
        "members": len(expected),
        "sha256": sha(packet.read_bytes()),
        "source_commit": manifest["source_commit"],
    }


def build(wheel: Path, output: Path) -> Path:
    files = inventory(wheel)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    packet = output / "footwork-onboarding-u2.zip"
    with (
        packet.open("xb") as stream,
        zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive,
    ):
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    verify(packet, wheel, json.loads(files["footwork/MANIFEST.json"])["source_commit"])
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--verify", type=Path)
    parser.add_argument("--source-commit", help="Expected frozen commit for verification after later commits")
    args = parser.parse_args()
    if args.output and args.source_commit:
        parser.error("Builds record HEAD; --source-commit is for verification only")
    wheel = args.wheel.resolve()
    packet = args.verify or build(wheel, args.output)
    print(json.dumps({"packet": str(packet.resolve()), **verify(packet, wheel, args.source_commit)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
