"""The vendored CUA archive's patch chain rebuilds deterministically and refuses a wrong input."""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cua_source_chain", ROOT / "scripts/cua_source_chain.py")
CHAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHAIN)
VENDOR = ROOT / "vendor/cua-driver"
LAST = CHAIN.STEPS[-1]


def _patched_vendor(tmp_path: Path, record_change: dict) -> Path:
    """A vendor copy whose last step's manifest differs, for the refusal tests."""
    vendor = tmp_path / "vendor"
    (vendor / "patches").mkdir(parents=True)
    shutil.copy2(VENDOR / "build_support.py", vendor / "build_support.py")
    for step in CHAIN.STEPS:
        for suffix in (".json", ".patch"):
            shutil.copy2(VENDOR / f"patches/{step}{suffix}", vendor / f"patches/{step}{suffix}")
    path = vendor / f"patches/{LAST}.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), **record_change}))
    return vendor


def test_the_chain_ends_at_the_pinned_archive():
    records = CHAIN.manifests()
    for earlier, later in itertools.pairwise(records):
        assert earlier["patched_archive_sha256"] == later["base_archive_sha256"]
        assert earlier["version"] == later["base_version"]
    support = CHAIN._support(VENDOR)
    assert records[-1]["patched_archive_sha256"] == support.SOURCE_SHA256
    assert hashlib.sha256((VENDOR / "native-source.tar.gz").read_bytes()).hexdigest() == support.SOURCE_SHA256
    assert records[-1]["version"] == support.VERSION


def test_the_last_step_does_not_reapply_to_the_pinned_archive():
    """The pinned archive is the chain's end, not a base: rebuilding from it is refused."""
    with pytest.raises(ValueError, match="not a step of the chain"):
        CHAIN.rebuild((VENDOR / "native-source.tar.gz").read_bytes())


def test_a_step_refuses_a_base_or_patch_with_another_hash(tmp_path):
    record = CHAIN.manifests()[-1]
    patch = VENDOR / f"patches/{LAST}.patch"
    with pytest.raises(ValueError, match="base archive checksum mismatch"):
        CHAIN.apply_step(b"not the base", patch, record)
    altered = tmp_path / f"{LAST}.patch"
    altered.write_bytes(patch.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="patch checksum mismatch"):
        CHAIN.apply_step(b"", altered, {**record, "base_archive_sha256": hashlib.sha256(b"").hexdigest()})


def test_a_step_whose_result_differs_from_its_record_is_refused(tmp_path):
    """Rebuild the last step's base from the pinned archive by reversing the last step, then check that
    a manifest recording another result refuses the rebuilt archive."""
    import subprocess
    import tarfile

    support = CHAIN._support(VENDOR)
    record = CHAIN.manifests()[-1]
    source = tmp_path / "source"
    support.extract_source(VENDOR / "native-source.tar.gz", source)
    subprocess.run(["patch", "--batch", "--reverse", "--silent", "-p1", "-i",
                    str(VENDOR / f"patches/{LAST}.patch")], cwd=source, check=True)
    for name, hashes in record["files"].items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == hashes["before"]
    import gzip
    import io

    memory = io.BytesIO()
    with (
        tarfile.open(VENDOR / "native-source.tar.gz") as original,
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
    base = memory.getvalue()
    assert hashlib.sha256(base).hexdigest() == record["base_archive_sha256"]
    rebuilt = CHAIN.apply_step(base, VENDOR / f"patches/{LAST}.patch", record)
    assert rebuilt == (VENDOR / "native-source.tar.gz").read_bytes()
    vendor = _patched_vendor(tmp_path, {"patched_archive_sha256": "0" * 64})
    with pytest.raises(ValueError, match="patched archive checksum mismatch"):
        CHAIN.rebuild(base, vendor=vendor)
