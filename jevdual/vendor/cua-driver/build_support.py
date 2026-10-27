"""Package unchanged upstream Python bindings with checksum-pinned release binaries.

No native library is loaded or executable started during the build.
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import stat
import tarfile
import zipfile
from pathlib import Path

VERSION = "0.38.0"
BASE_URL = f"https://github.com/trycua/cua/releases/download/cua-driver-rs-v{VERSION}"
# Recorded from the versioned release's checksums.txt on 2026-10-27. Builds never
# retrieve a replacement checksum: a changed asset must fail closed.
TARGETS = {
    ("darwin", "universal"): (
        "tar.gz",
        "py3-none-macosx_13_0_universal2",
        "2bb8dc4a7e69185ffd04c4a9c0eab590bd2c54b72c2c1be13ab675be4f487732",
        ("cua-driver", "libcua_driver_sdk.dylib"),
    ),
    ("linux", "x86_64"): (
        "tar.gz",
        "py3-none-manylinux_2_31_x86_64",
        "31ab9709dd91ce73677e49b9f3e75c6f0d3e4d9625c286c9e58262bfbea698dd",
        ("cua-driver", "libcua_driver_sdk.so"),
    ),
    ("linux", "arm64"): (
        "tar.gz",
        "py3-none-manylinux_2_31_aarch64",
        "80c9ae66bc7322052dd426c6133c96086b33894bf06c972bca8215384400b33d",
        ("cua-driver", "libcua_driver_sdk.so"),
    ),
    ("windows", "x86_64"): (
        "zip",
        "py3-none-win_amd64",
        "5edaa74d0afa1b55a9668dbc4f32736507bd2bd4d75b18ca1dc8881bb12402b5",
        ("cua-driver.exe", "cua-driver-uia.exe", "cua_driver_sdk.dll"),
    ),
    ("windows", "arm64"): (
        "zip",
        "py3-none-win_arm64",
        "d25c8ebfffb34e4c095ea170baf47b87c35dc0d1116f42e46b39df2bcbff8700",
        ("cua-driver.exe", "cua-driver-uia.exe", "cua_driver_sdk.dll"),
    ),
}


def native_target() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    target = (system, "universal" if system == "darwin" and arch in {"arm64", "x86_64"} else arch)
    if target not in TARGETS:
        raise RuntimeError(f"No pinned CUA Driver {VERSION} native asset for {target}")
    return target


def verify(path: Path, expected: str) -> None:
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        actual = digest.hexdigest()
    if actual != expected:
        raise RuntimeError(f"CUA Driver archive checksum mismatch: {path.name}")


def extract_selected(archive: Path, names: tuple[str, ...], destination: Path) -> None:
    """Copy exact regular-file basenames; never extract archive-controlled paths."""
    seen = set()
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                name = Path(member.filename).name
                if (
                    name not in names
                    or member.is_dir()
                    or stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG)
                ):
                    continue
                if name in seen:
                    raise RuntimeError(f"Duplicate native artifact: {name}")
                seen.add(name)
                with bundle.open(member) as source, (destination / name).open("wb") as output:
                    shutil.copyfileobj(source, output)
    else:
        with tarfile.open(archive, "r:gz") as bundle:
            for member in bundle:
                name = Path(member.name).name
                if name not in names or not member.isfile():
                    continue
                if name in seen:
                    raise RuntimeError(f"Duplicate native artifact: {name}")
                seen.add(name)
                with bundle.extractfile(member) as source, (destination / name).open("wb") as output:
                    shutil.copyfileobj(source, output)
    if seen != set(names):
        raise RuntimeError(f"Missing native artifacts: {sorted(set(names) - seen)}")
    for name in names:
        (destination / name).chmod(0o755)
