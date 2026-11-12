"""Rebuild the vendored CUA native source archive from an earlier one through the patch chain.

Each step's manifest under vendor/cua-driver/patches binds its base archive, patch and patched
archive by SHA256. A step extracts the base with the build hook's own extractor, applies the patch
with ``patch -p1`` and re-packs the base's member list deterministically (path-sorted PAX tar, zero
mtime/uid/gid, empty owner names, the base's modes, Python gzip at level nine with no name or
mtime). Every hash is checked before anything is written. Standard library only.

    python3 scripts/cua_source_chain.py --base PATH --output PATH

``--base`` is any archive the chain starts from or passes through: the focus1 archive from Git
history (``git show 6e8bb5e:jevdual/vendor/cua-driver/native-source.tar.gz``) rebuilds the
vendored archive through every step.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "vendor/cua-driver"
#: Applied in order on top of the cleanup2.focus1 archive; the last one produces the pinned archive.
STEPS = ("ordinary-helptag", "connected-click", "ref-locate")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifests(vendor: Path = VENDOR) -> list[dict]:
    return [json.loads((vendor / f"patches/{step}.json").read_text()) for step in STEPS]


def _support(vendor: Path):
    spec = importlib.util.spec_from_file_location("cua_build_support", vendor / "build_support.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_step(base: bytes, patch: Path, record: dict, *, vendor: Path = VENDOR) -> bytes:
    """The patched archive bytes for one step, after checking the step's three hashes."""
    if sha(base) != record["base_archive_sha256"]:
        raise ValueError(f"{patch.name}: base archive checksum mismatch")
    if sha(patch.read_bytes()) != record["patch_sha256"]:
        raise ValueError(f"{patch.name}: patch checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="cua-chain-") as temporary:
        source = Path(temporary) / "source"
        archive = Path(temporary) / "base.tar.gz"
        archive.write_bytes(base)
        _support(vendor).extract_source(archive, source)
        subprocess.run(["patch", "--batch", "--forward", "--silent", "-p1", "-i", str(patch.resolve())],
                       cwd=source, check=True)
        memory = io.BytesIO()
        with (
            tarfile.open(fileobj=io.BytesIO(base), mode="r:gz") as original,
            gzip.GzipFile(filename="", fileobj=memory, mode="wb", mtime=0, compresslevel=9) as compressed,
            tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as bundle,
        ):
            for member in sorted(original.getmembers(), key=lambda item: item.name):
                info = tarfile.TarInfo(member.name)
                info.mode = member.mode
                if member.isdir():
                    info.type = tarfile.DIRTYPE
                    bundle.addfile(info)
                    continue
                content = (source / member.name).read_bytes()
                info.size = len(content)
                bundle.addfile(info, io.BytesIO(content))
        for name, hashes in record["files"].items():
            if sha((source / name).read_bytes()) != hashes["after"]:
                raise ValueError(f"{patch.name}: {name} does not match its recorded result")
    patched = memory.getvalue()
    if sha(patched) != record["patched_archive_sha256"]:
        raise ValueError(f"{patch.name}: patched archive checksum mismatch")
    return patched


def rebuild(base: bytes, *, vendor: Path = VENDOR) -> bytes:
    """Apply every step from the one whose base ``base`` is; the result is the final archive."""
    records = manifests(vendor)
    starts = [index for index, record in enumerate(records) if record["base_archive_sha256"] == sha(base)]
    if not starts:
        raise ValueError("the base archive is not a step of the chain")
    archive = base
    for step, record in zip(STEPS[starts[0]:], records[starts[0]:], strict=True):
        archive = apply_step(archive, vendor / f"patches/{step}.patch", record, vendor=vendor)
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = rebuild(args.base.read_bytes())
    args.output.write_bytes(result)
    print(json.dumps({"output": str(args.output), "sha256": sha(result), "bytes": len(result)}))
