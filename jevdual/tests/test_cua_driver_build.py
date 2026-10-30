"""Offline integrity and command-boundary checks for exact-source CUA wheels."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cua_build_support", ROOT / "vendor/cua-driver/build_support.py"
)
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


@pytest.mark.parametrize(
    ("system", "machine", "expected", "tag"),
    [
        ("Darwin", "arm64", ("darwin", "arm64"), "py3-none-macosx_13_0_arm64"),
        ("Darwin", "x86_64", ("darwin", "x86_64"), "py3-none-macosx_13_0_x86_64"),
        ("Linux", "aarch64", ("linux", "arm64"), "py3-none-linux_aarch64"),
        ("Linux", "x86_64", ("linux", "x86_64"), "py3-none-linux_x86_64"),
        ("Windows", "AMD64", ("windows", "x86_64"), "py3-none-win_amd64"),
        ("Windows", "ARM64", ("windows", "arm64"), "py3-none-win_arm64"),
    ],
)
def test_build_tags_actual_host_without_universal_or_manylinux_claim(
    monkeypatch, system, machine, expected, tag
):
    monkeypatch.setattr(BUILD.platform, "system", lambda: system)
    monkeypatch.setattr(BUILD.platform, "machine", lambda: machine)
    assert BUILD.native_target() == expected
    assert BUILD.wheel_tag(*expected) == tag


def test_unknown_platform_fails_closed(monkeypatch):
    monkeypatch.setattr(BUILD.platform, "system", lambda: "Linux")
    monkeypatch.setattr(BUILD.platform, "machine", lambda: "riscv64")
    with pytest.raises(RuntimeError, match="No CUA"):
        BUILD.native_target()


def test_source_archive_is_hash_pinned_and_contains_native_head_resources():
    archive = ROOT / "vendor/cua-driver/native-source.tar.gz"
    BUILD.verify(archive, BUILD.SOURCE_SHA256)
    with tarfile.open(archive) as bundle:
        names = set(bundle.getnames())
        assert "libs/cua-driver/rust/Cargo.lock" in names
        assert "libs/cua-driver/rust/rust-toolchain.toml" in names
        assert "libs/cua/crates/cua-telemetry/build.rs" in names
        assert "libs/images/sandbox-images.json" in names
        assert "libs/cua/crates/cua-teleport/src/ux/targets.json" in names
        assert not any("/target/" in name for name in names)
        data = bundle.extractfile("libs/cua-driver/rust/rust-toolchain.toml").read().decode()
        assert f'channel = "{BUILD.TOOLCHAIN}"' in data


def test_cached_archive_tampering_is_rejected(tmp_path):
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(b"source bytes")
    expected = hashlib.sha256(archive.read_bytes()).hexdigest()
    BUILD.verify(archive, expected)
    archive.write_bytes(b"different bytes")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        BUILD.verify(archive, expected)


def make_archive(path, name, content=b"source", symlink=False):
    with tarfile.open(path, "w:gz") as bundle:
        member = tarfile.TarInfo(name)
        if symlink:
            member.type = tarfile.SYMTYPE
            member.linkname = "/outside"
            bundle.addfile(member)
        else:
            member.size = len(content)
            bundle.addfile(member, io.BytesIO(content))


def test_source_restore_reverts_cache_edits_without_changing_correct_file_mtime(tmp_path):
    archive = tmp_path / "source.tar.gz"
    make_archive(archive, "file.rs")
    destination = tmp_path / "out"
    BUILD.extract_source(archive, destination)
    source = destination / "file.rs"
    original_mtime = source.stat().st_mtime_ns
    BUILD.extract_source(archive, destination)
    assert source.stat().st_mtime_ns == original_mtime
    source.write_bytes(b"edited")
    BUILD.extract_source(archive, destination)
    assert source.read_bytes() == b"source"


@pytest.mark.parametrize("name", ["../outside", "/outside", "dir\\outside"])
def test_source_archive_paths_cannot_escape_cache(tmp_path, name):
    archive = tmp_path / "source.tar.gz"
    make_archive(archive, name)
    with pytest.raises(RuntimeError, match="Unsafe"):
        BUILD.extract_source(archive, tmp_path / "out")


def test_source_symlinks_are_rejected(tmp_path):
    archive = tmp_path / "source.tar.gz"
    make_archive(archive, "link", symlink=True)
    with pytest.raises(RuntimeError, match="Non-regular"):
        BUILD.extract_source(archive, tmp_path / "out")


def test_cargo_build_is_versioned_locked_and_builds_cli_sdk_and_windows_worker():
    command = BUILD.cargo_command("darwin")
    assert command[:3] == ["cargo", "+1.97.1", "build"]
    assert "--locked" in command and "--release" in command
    assert command[command.index("--jobs") + 1] == "2"
    assert "cua-driver" in command and "cua-driver-sdk" in command
    assert "cua-driver-uia" not in command
    assert "cua-driver-uia" in BUILD.cargo_command("windows")


def test_missing_native_toolchain_fails_with_explicit_setup_instruction(tmp_path, monkeypatch):
    monkeypatch.setattr(BUILD.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="rustup toolchain install 1.97.1"):
        BUILD.build_native(tmp_path)


def test_untracked_build_script_in_source_cache_is_refused(tmp_path):
    archive = tmp_path / "source.tar.gz"
    make_archive(archive, "file.rs")
    destination = tmp_path / "out"
    BUILD.extract_source(archive, destination)
    (destination / "build.rs").write_text("fn main() {}")
    with pytest.raises(RuntimeError, match="Unexpected native source cache member"):
        BUILD.extract_source(archive, destination)


def test_local_native_patch_has_inspectable_hash_bound_provenance():
    import json

    vendor = ROOT / 'vendor/cua-driver'
    manifest = json.loads((vendor / 'patches/session-cleanup-join.json').read_text())
    assert manifest['upstream_commit'] == BUILD.SOURCE_COMMIT
    assert manifest['patched_archive_sha256'] == BUILD.SOURCE_SHA256
    patch = (vendor / 'patches/session-cleanup-join.patch').read_bytes()
    assert hashlib.sha256(patch).hexdigest() == manifest['patch_sha256']
    assert len(manifest['files']) == 4
    with tarfile.open(vendor / 'native-source.tar.gz') as source:
        for name, hashes in manifest['files'].items():
            assert hashlib.sha256(source.extractfile(name).read()).hexdigest() == hashes['after']
            assert hashes['before'] != hashes['after']
