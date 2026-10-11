"""Verify extracted packet members before creating any qualification output."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


def verify(root: Path) -> dict:
    root = root.resolve()
    manifest_path = root / "MANIFEST.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Manifest must be a regular file")
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or not re.fullmatch(
        r"[0-9a-f]{40}", str(manifest.get("source_commit", ""))
    ):
        raise ValueError("Manifest requires a full immutable source commit")
    members = manifest.get("members")
    if not isinstance(members, dict) or not members:
        raise ValueError("Manifest requires payload member hashes")
    expected = {"MANIFEST.json"}
    for name, digest in members.items():
        relative = PurePosixPath(name)
        if (
            not relative.parts
            or relative.parts[0] != "footwork"
            or len(relative.parts) < 2
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != name
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ValueError("Invalid packet member or hash")
        path = root.joinpath(*relative.parts[1:])
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent):
            raise ValueError("Symlinked packet member")
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError("Missing or nonregular packet member")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Packet member hash mismatch: " + name)
        expected.add(path.relative_to(root).as_posix())
    actual = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() or path.is_symlink()
    }
    if actual != expected:
        raise ValueError("Extracted packet inventory differs from manifest")
    wheels = [
        digest
        for name, digest in members.items()
        if name.startswith("footwork/artifacts/") and name.endswith(".whl")
    ]
    if wheels != [manifest.get("wheel_sha256")]:
        raise ValueError("Manifest wheel hash differs")
    return {
        "verified": True,
        "members": len(actual),
        "source_commit": manifest["source_commit"],
        "wheel_sha256": manifest["wheel_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.packet_root)
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(1, "Packet verification failed: " + str(exc) + "\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
