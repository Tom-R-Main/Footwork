"""Offline boundary checks for the vendored CUA native-wheel packaging."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cua_build_support", ROOT / "vendor/cua-driver/build_support.py"
)
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Darwin", "arm64", ("darwin", "universal")),
        ("Darwin", "x86_64", ("darwin", "universal")),
        ("Linux", "aarch64", ("linux", "arm64")),
        ("Linux", "x86_64", ("linux", "x86_64")),
        ("Windows", "AMD64", ("windows", "x86_64")),
        ("Windows", "ARM64", ("windows", "arm64")),
    ],
)
def test_build_selects_host_native_asset(monkeypatch, system, machine, expected):
    monkeypatch.setattr(BUILD.platform, "system", lambda: system)
    monkeypatch.setattr(BUILD.platform, "machine", lambda: machine)
    assert BUILD.native_target() == expected


def test_unknown_platform_fails_closed(monkeypatch):
    monkeypatch.setattr(BUILD.platform, "system", lambda: "Linux")
    monkeypatch.setattr(BUILD.platform, "machine", lambda: "riscv64")
    with pytest.raises(RuntimeError, match="No pinned"):
        BUILD.native_target()


def test_cached_archive_tampering_is_rejected(tmp_path):
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(b"release bytes")
    expected = hashlib.sha256(archive.read_bytes()).hexdigest()
    BUILD.verify(archive, expected)
    archive.write_bytes(b"different bytes")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        BUILD.verify(archive, expected)


def test_tar_extracts_only_expected_regular_basenames(tmp_path):
    archive = tmp_path / "release.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name, data in [
            ("../../cua-driver", b"cli"),
            ("/libcua_driver_sdk.so", b"sdk"),
            ("other", b"skip"),
        ]:
            member = tarfile.TarInfo(name)
            member.size = len(data)
            bundle.addfile(member, io.BytesIO(data))
    output = tmp_path / "output"
    output.mkdir()
    BUILD.extract_selected(archive, ("cua-driver", "libcua_driver_sdk.so"), output)
    assert sorted(p.name for p in output.iterdir()) == ["cua-driver", "libcua_driver_sdk.so"]
    assert (output / "cua-driver").read_bytes() == b"cli"
    assert (output / "cua-driver").stat().st_mode & stat.S_IXUSR


def test_zip_duplicate_artifacts_are_rejected(tmp_path):
    archive = tmp_path / "release.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("first/cua-driver.exe", b"first")
        bundle.writestr("second/cua-driver.exe", b"second")
    with pytest.raises(RuntimeError, match="Duplicate"):
        BUILD.extract_selected(archive, ("cua-driver.exe",), tmp_path)


@pytest.mark.parametrize("kind", ["tar", "zip"])
def test_archive_symlinks_cannot_stand_in_for_native_artifacts(tmp_path, kind):
    archive = tmp_path / ("release.tar.gz" if kind == "tar" else "release.zip")
    if kind == "tar":
        with tarfile.open(archive, "w:gz") as bundle:
            member = tarfile.TarInfo("cua-driver")
            member.type = tarfile.SYMTYPE
            member.linkname = "/outside"
            bundle.addfile(member)
    else:
        with zipfile.ZipFile(archive, "w") as bundle:
            member = zipfile.ZipInfo("cua-driver")
            member.create_system = 3
            member.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(member, "/outside")
    with pytest.raises(RuntimeError, match="Missing"):
        BUILD.extract_selected(archive, ("cua-driver",), tmp_path)
