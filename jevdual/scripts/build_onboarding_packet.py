"""Build a transportable, non-executing U2 qualification packet from fixed files."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

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


def snapshot(path: Path, *, limit: int = 16 * 1024 * 1024) -> bytes:
    """Read one bounded regular file without following its final symlink."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            source = os.fdopen(fd, "rb")
        except OSError:
            os.close(fd)
            raise
        with source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise ValueError("Artifact must be a bounded regular nonsymlink file")
            data = source.read(limit + 1)
            after = os.fstat(source.fileno())
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(data) != before.st_size or len(data) > limit or identity(before) != identity(after):
            raise ValueError("Artifact changed during snapshot")
        return data
    except OSError as exc:
        raise ValueError("Artifact must be a readable regular nonsymlink file") from exc


def parse_archive(data: bytes, *, prefix: str | None = "footwork") -> dict[str, bytes]:
    """Parse the same frozen bytes that are hashed and compared; never extract."""
    if len(data) > 16 * 1024 * 1024:
        raise ValueError("Archive exceeds bounded candidate size")
    files = {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for entry in archive.infolist():
                name = entry.filename
                parts = PurePosixPath(name)
                mode = entry.external_attr >> 16
                if (
                    name in files
                    or not parts.parts
                    or parts.is_absolute()
                    or ".." in parts.parts
                    or parts.as_posix() != name
                    or (prefix is not None and (len(parts.parts) < 2 or parts.parts[0] != prefix))
                    or "\\" in name
                    or entry.is_dir()
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                ):
                    raise ValueError("Unsafe or duplicate archive member")
                total += entry.file_size
                if entry.file_size > 8 * 1024 * 1024 or total > 16 * 1024 * 1024:
                    raise ValueError("Archive exceeds bounded candidate size")
                files[name] = archive.read(entry)
    except zipfile.BadZipFile as exc:
        raise ValueError("Malformed archive") from exc
    return files


def commit_identity(commit: str | None, project: Path) -> str:
    commit = commit or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full immutable source commit is required")
    try:
        kind = subprocess.check_output(["git", "cat-file", "-t", commit], cwd=project, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        raise ValueError("Source identity must resolve to a commit object") from exc
    if kind.strip() != b"commit":
        raise ValueError("Source identity must resolve to a commit object")
    return commit


def committed_bytes(commit: str, relative: str, project: Path) -> bytes:
    commit = commit_identity(commit, project)
    entries = subprocess.check_output(
        ["git", "ls-tree", "-z", commit, "--", relative], cwd=project, stderr=subprocess.PIPE
    ).split(b"\0")
    entries = [entry for entry in entries if entry]
    if len(entries) != 1:
        raise ValueError("Committed source file is absent: " + relative)
    metadata, name = entries[0].split(b"\t", 1)
    mode, kind, blob = metadata.split()
    if mode not in (b"100644", b"100755") or kind != b"blob" or name.decode() != relative:
        raise ValueError("Committed source must be a regular file")
    return subprocess.check_output(
        ["git", "cat-file", "blob", blob.decode()], cwd=project, stderr=subprocess.PIPE
    )


def verify_committed_wheel(name: str, data: bytes, commit: str, project: Path) -> None:
    """Verify runtime bytes against the requested immutable source, not the checkout."""
    commit = commit_identity(commit, project)
    parse_archive(data, prefix=None)
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
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(committed_bytes(commit, relative, project))
        wheel = root / Path(name).name
        wheel.write_bytes(data)
        verify_wheel(wheel, package)


def inventory(wheel: Path, source_commit: str | None = None) -> dict[str, bytes]:
    source_commit = commit_identity(source_commit, PROJECT)
    wheel_data = snapshot(wheel, limit=8 * 1024 * 1024)
    verify_committed_wheel(wheel.name, wheel_data, source_commit, PROJECT)
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
            files[name] = wheel_data
            continue
        relative = path.relative_to(PROJECT).as_posix()
        files[name] = committed_bytes(source_commit, relative, PROJECT)
    manifest = {
        "schema_version": "1",
        "source_commit": source_commit,
        "wheel_sha256": sha(wheel_data),
        "qualification": "not_performed",
        "automatic_execution": False,
        "members": {name: sha(data) for name, data in sorted(files.items())},
    }
    files["footwork/MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return files


def verify(packet: Path, wheel: Path, source_commit: str | None = None) -> dict:
    expected = inventory(wheel, source_commit)
    packet_data = snapshot(packet)
    actual = parse_archive(packet_data)
    if set(actual) != set(expected):
        raise ValueError("Packet inventory differs from its permitted files")
    for name, data in expected.items():
        if actual[name] != data:
            raise ValueError("Packet member differs: " + name)
    manifest = json.loads(actual["footwork/MANIFEST.json"])
    for name, digest in manifest["members"].items():
        if sha(actual[name]) != digest:
            raise ValueError("Packet manifest digest differs")
    return {
        "verified": True,
        "members": len(expected),
        "sha256": sha(packet_data),
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
    wheel = args.wheel.absolute()
    packet = args.verify or build(wheel, args.output)
    print(json.dumps({"packet": str(packet.resolve()), **verify(packet, wheel, args.source_commit)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
