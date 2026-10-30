"""Offline integrity and native build plan for the exact CUA reference snapshot."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

VERSION = "0.38.0+footwork.d5373879.cleanup2"
SOURCE_COMMIT = "d5373879e9e0baf5a63999ac4d26902340c0ce20"
SOURCE_SHA256 = "5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401"
TOOLCHAIN = "1.97.1"


def native_target() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    if system not in {"darwin", "linux", "windows"} or arch not in {"arm64", "x86_64"}:
        raise RuntimeError(f"No CUA native build plan for {(system, arch)}")
    return system, arch


def wheel_tag(system: str, arch: str) -> str:
    if system == "darwin":
        return f"py3-none-macosx_13_0_{arch}"
    if system == "linux":
        # Local compilation is not an audited manylinux build.
        return f"py3-none-linux_{'aarch64' if arch == 'arm64' else arch}"
    return f"py3-none-win_{'arm64' if arch == 'arm64' else 'amd64'}"


def verify(path: Path, expected: str) -> None:
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise RuntimeError(f"CUA Driver source checksum mismatch: {path.name}")


def extract_source(archive: Path, destination: Path) -> None:
    """Restore every source member from the verified archive, retaining unchanged mtimes.

    No symlinks, hard links, devices or archive-controlled escapes are accepted.
    Restoring the contents each time prevents an edited extracted source from
    silently diverging from the pinned archive while allowing Cargo caching.
    """
    if destination.is_symlink():
        raise RuntimeError("Native source cache must not be a symlink")
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as bundle:
        seen = set()
        for member in bundle:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or "\\" in member.name:
                raise RuntimeError(f"Unsafe native source path: {member.name}")
            if member.name in seen:
                raise RuntimeError(f"Duplicate native source path: {member.name}")
            seen.add(member.name)
            if not member.isdir() and not member.isfile():
                raise RuntimeError(f"Non-regular native source member: {member.name}")
            target = destination.joinpath(*name.parts)
            # A caller-edited cache must not redirect a restore outside its root.
            if target.is_symlink() or not target.resolve().is_relative_to(destination.resolve()):
                raise RuntimeError(f"Native source cache escapes its root: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.extractfile(member) as source:
                content = source.read()
            if not target.exists() or target.read_bytes() != content:
                target.write_bytes(content)
            target.chmod(member.mode & 0o777)
    unexpected = [p for p in destination.rglob("*") if p.relative_to(destination).as_posix() not in seen]
    if unexpected:
        raise RuntimeError(f"Unexpected native source cache member: {unexpected[0]}")


def cargo_command(system: str) -> list[str]:
    command = [
        "cargo",
        f"+{TOOLCHAIN}",
        "build",
        "--release",
        "--locked",
        "--jobs",
        "2",
        "-p",
        "cua-driver",
        "-p",
        "cua-driver-sdk",
    ]
    if system == "windows":
        command.extend(["-p", "cua-driver-uia"])
    return command


def build_native(root: Path) -> tuple[str, dict[str, str]]:
    system, arch = native_target()
    if not shutil.which("cargo") or not shutil.which("rustup"):
        raise RuntimeError(
            f"CUA native source build requires Rust {TOOLCHAIN}: install rustup, then run "
            f"`rustup toolchain install {TOOLCHAIN} --profile minimal` before uv sync"
        )
    if os.environ.get("CARGO_BUILD_TARGET"):
        raise RuntimeError("CUA wheel builds do not support CARGO_BUILD_TARGET cross-compilation")
    available = subprocess.run(["rustup", "toolchain", "list"], capture_output=True, text=True, check=True)
    if not any(line.startswith(f"{TOOLCHAIN}-") for line in available.stdout.splitlines()):
        raise RuntimeError(
            f"Install the pinned compiler first: rustup toolchain install {TOOLCHAIN} --profile minimal"
        )
    archive = root / "native-source.tar.gz"
    verify(archive, SOURCE_SHA256)
    cache = root / ".native-cache"
    if cache.is_symlink():
        raise RuntimeError("Native build cache must not be a symlink")
    source = cache / f"source-{SOURCE_SHA256[:12]}"
    extract_source(archive, source)
    target = cache / "target"
    env = os.environ.copy()
    env["CUA_DRIVER_GIT_SHA"] = SOURCE_COMMIT
    env["CARGO_TARGET_DIR"] = str(target.resolve())
    if system == "darwin":
        env["MACOSX_DEPLOYMENT_TARGET"] = "13.0"
    subprocess.run(cargo_command(system), cwd=source / "libs/cua-driver/rust", env=env, check=True)
    names = {
        "darwin": ("cua-driver", "libcua_driver_sdk.dylib"),
        "linux": ("cua-driver", "libcua_driver_sdk.so"),
        "windows": ("cua-driver.exe", "cua-driver-uia.exe", "cua_driver_sdk.dll"),
    }[system]
    include = {}
    for name in names:
        artifact = target / "release" / name
        if not artifact.is_file():
            raise RuntimeError(f"CUA native build did not produce {artifact}")
        relative = (
            f"cua_driver/{name}" if name.endswith((".dylib", ".so", ".dll")) else f"cua_driver/bin/{name}"
        )
        include[str(artifact)] = relative
    return wheel_tag(system, arch), include
