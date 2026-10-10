"""Build a transportable, non-executing U2 qualification packet from fixed files."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from build_capability_wheel import verify as verify_wheel

PROJECT = Path(__file__).resolve().parents[2]
HELPERS = (
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


def inventory(wheel: Path) -> dict[str, bytes]:
    verify_wheel(wheel, PROJECT / "jevdual")
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
        if path.is_symlink() or not path.is_file():
            raise ValueError("Packet source must be a regular nonsymlink file")
        files[name] = path.read_bytes()
    manifest = {
        "schema_version": "1",
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True
        ).strip(),
        "wheel_sha256": sha(wheel.read_bytes()),
        "qualification": "not_performed",
        "automatic_execution": False,
        "members": {name: sha(data) for name, data in sorted(files.items())},
    }
    files["footwork/MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return files


def verify(packet: Path, wheel: Path) -> dict:
    expected = inventory(wheel)
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
    return {"verified": True, "members": len(expected), "sha256": sha(packet.read_bytes())}


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
    verify(packet, wheel)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--verify", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    packet = args.verify or build(wheel, args.output)
    print(json.dumps({"packet": str(packet.resolve()), **verify(packet, wheel)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
