"""Independent, read-only postconditions for the owned app qualification fixture.

These checks establish current artifact state, not which app caused it. The
manifest digest detects accidental changes; it does not authenticate a hostile
same-user producer. UI actions belong to the driver, never to these oracles.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

MAX_BYTES = 1024 * 1024
MAX_ENTRIES = 64
MANIFEST = "fixture.json"
PATHS = {
    "source": "inbox/asset.png",
    "original": "original/asset.png",
    "renamed": "inbox/renamed.png",
    "organized": "organized/renamed.png",
    "decoy": "decoy/asset.png",
}


class OracleError(ValueError):
    """The owned fixture cannot supply qualified bounded evidence."""


@dataclass(frozen=True)
class OracleCheck:
    ok: bool
    detail: str
    claims: tuple[str, ...] = ()
    artifact: str | None = None
    identity: dict[str, Any] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)
    limits: tuple[str, ...] = ("current artifact state does not establish historical UI execution",)

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _relative(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or "\\" in value:
        raise OracleError("a fixture-relative POSIX path is required")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(p in (".", "..") for p in path.parts):
        raise OracleError("path escapes or aliases the owned fixture")
    return path.parts


def _root_fd(root: Path, identity: dict[str, int]) -> int:
    if not root.is_absolute():
        raise OracleError("absolute fixture root required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        info = os.fstat(fd)
        if (info.st_dev, info.st_ino) != (identity["device"], identity["inode"]):
            raise OracleError("fixture root identity changed")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read(manifest: dict[str, Any], relative: str) -> tuple[bytes, dict[str, Any]]:
    root = Path(manifest["root"])
    parts = _relative(relative)
    parent = _root_fd(root, manifest["root_identity"])
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = nxt
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
                raise OracleError("artifact is not a bounded regular file")
            data = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        named = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)

        def signature(s: os.stat_result) -> tuple[int, ...]:
            return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

        if (
            len(data) > MAX_BYTES
            or signature(before) != signature(after)
            or signature(after) != signature(named)
        ):
            raise OracleError("artifact or pathname changed during read")
        return data, {
            "path": str(root / relative),
            "device": after.st_dev,
            "inode": after.st_ino,
            "size": after.st_size,
            "mtime_ns": after.st_mtime_ns,
            "sha256": _sha(data),
        }
    finally:
        os.close(parent)


def _validate(manifest: dict[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 1
    ):
        raise OracleError("unsupported fixture manifest")
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if _sha(_canonical(body)) != manifest.get("manifest_sha256"):
        raise OracleError("fixture manifest digest changed")
    root = Path(manifest["root"])
    if not root.is_absolute() or str(root) != str(root.resolve()):
        raise OracleError("fixture root is not canonical")
    disk, _ = _read(manifest, MANIFEST)
    if json.loads(disk) != manifest:
        raise OracleError("retained fixture manifest differs")
    if manifest["paths"] != PATHS or manifest["asset_directories"] != ["inbox", "organized"]:
        raise OracleError("unsupported fixture path policy")
    return manifest


def _inventory(manifest: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    seen = 0

    def visit(fd: int, prefix: str) -> None:
        nonlocal seen
        for name in os.listdir(fd):
            seen += 1
            if seen > MAX_ENTRIES:
                raise OracleError("fixture inventory exceeds bound")
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            relative = prefix + name
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    visit(child, relative + "/")
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode):
                # Finder may maintain its own directory display metadata.
                if name != ".DS_Store":
                    found.add(relative)
            else:
                raise OracleError("fixture contains symlink or nonregular entry")

    root = _root_fd(Path(manifest["root"]), manifest["root_identity"])
    try:
        visit(root, "")
    finally:
        os.close(root)
    return found


def _asset_path(manifest: dict[str, Any], path: str | Path) -> str:
    value = str(path)
    if Path(value).is_absolute():
        try:
            value = str(Path(value).relative_to(Path(manifest["root"])))
        except ValueError as exc:
            raise OracleError("artifact is outside the owned fixture") from exc
    parts = _relative(value)
    if len(parts) != 2 or parts[0] not in manifest["asset_directories"] or not parts[1].endswith(".png"):
        raise OracleError("artifact is not an allowed asset path")
    if value in manifest["protected"]:
        raise OracleError("artifact aliases a preserved sibling")
    return value


def _preserved(manifest: dict[str, Any], asset: str) -> None:
    for relative, digest in manifest["protected"].items():
        data, _ = _read(manifest, relative)
        if _sha(data) != digest:
            raise OracleError(f"preserved sibling changed: {relative}")
    expected = set(manifest["protected"]) | {asset, MANIFEST}
    if _inventory(manifest) != expected:
        raise OracleError("source, duplicate asset or unexpected sibling inventory differs")


def create_fixture(root: Path) -> dict[str, Any]:
    """Create setup data only, in a new directory; no qualification action is performed."""
    from PIL import Image

    root = Path(root).absolute()
    if root.exists() or root.is_symlink():
        raise OracleError("choose a fresh fixture directory")
    root = root.parent.resolve(strict=True) / root.name
    root.mkdir(mode=0o700)
    for directory in ("inbox", "organized", "original", "decoy"):
        (root / directory).mkdir(mode=0o700)
    width, height = 5, 3
    pixels = [
        [
            [(17 + x * 43 + y * 13) % 256, (29 + x * 7 + y * 71) % 256, (31 + x * 37 + y * 19) % 256]
            for x in range(width)
        ]
        for y in range(height)
    ]
    image = Image.new("RGB", (width, height))
    image.putdata([tuple(pixel) for row in pixels for pixel in row])
    image.save(root / PATHS["original"], format="PNG")
    original = (root / PATHS["original"]).read_bytes()
    (root / PATHS["source"]).write_bytes(original)
    image.putpixel((0, 0), (0, 0, 0))
    image.save(root / PATHS["decoy"], format="PNG")
    for directory in ("inbox", "organized"):
        (root / directory / "keep.bin").write_bytes(("preserve-" + directory).encode())
    info = root.stat()
    protected = {
        relative: _sha((root / relative).read_bytes())
        for relative in (
            PATHS["original"],
            PATHS["decoy"],
            "inbox/keep.bin",
            "organized/keep.bin",
        )
    }
    manifest = {
        "schema_version": 1,
        "fixture_id": uuid.uuid4().hex,
        "created_at": time.time(),
        "root": str(root),
        "root_identity": {"device": info.st_dev, "inode": info.st_ino},
        "paths": dict(PATHS),
        "asset_directories": ["inbox", "organized"],
        "original_sha256": _sha(original),
        "seed": {"width": width, "height": height, "pixels": pixels},
        "protected": protected,
        "encoding_policy": "single-frame PNG RGB or opaque RGBA; no orientation transform or ICC profile",
    }
    manifest["manifest_sha256"] = _sha(_canonical(manifest))
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def check_finder(manifest: dict[str, Any], expectedrelativepath: str) -> OracleCheck:
    """Check path, byte preservation and siblings; does not claim a historical rename/move."""
    try:
        _validate(manifest)
        asset = _asset_path(manifest, expectedrelativepath)
        _preserved(manifest, asset)
        _, identity = _read(manifest, asset)
        if identity["sha256"] != manifest["original_sha256"]:
            raise OracleError("organized asset bytes differ from the preserved original")
        return OracleCheck(
            True,
            "asset is at the exact expected path with unchanged bytes and siblings",
            ("current_asset_path", "unchanged_asset_bytes", "preserved_fixture_siblings"),
            str(Path(manifest["root"]) / asset),
            identity,
        )
    except (OracleError, OSError, ValueError, TypeError, KeyError) as exc:
        return OracleCheck(False, str(exc))


def check_preview(manifest: dict[str, Any], path: str | Path, clockwise: bool = True) -> OracleCheck:
    """Decode the saved image independently and compare samples with the seed matrix rotation."""
    from PIL import Image

    try:
        _validate(manifest)
        if type(clockwise) is not bool:
            raise OracleError("rotation direction must be an explicit boolean")
        asset = _asset_path(manifest, path)
        _preserved(manifest, asset)
        data, identity = _read(manifest, asset)
        seed = manifest["seed"]
        width, height, pixels = seed["width"], seed["height"], seed["pixels"]
        if type(width) is not int or type(height) is not int or not 0 < width * height <= 65_536:
            raise OracleError("unsupported seed dimensions")
        expected = []
        for y in range(width):
            for x in range(height):
                expected.append(tuple(pixels[height - 1 - x][y] if clockwise else pixels[x][width - 1 - y]))
        with Image.open(io.BytesIO(data)) as decoded:
            if (
                decoded.format != "PNG"
                or decoded.size != (height, width)
                or getattr(decoded, "n_frames", 1) != 1
            ):
                raise OracleError("saved image format, dimensions or frame count differs")
            if (
                decoded.mode not in ("RGB", "RGBA")
                or decoded.info.get("icc_profile")
                or decoded.getexif().get(274, 1) != 1
            ):
                raise OracleError("unsupported image color/orientation encoding")
            decoded.load()
            if decoded.mode == "RGBA" and decoded.getextrema()[3] != (255, 255):
                raise OracleError("saved image is not opaque")
            rgb = decoded.convert("RGB").tobytes()
            samples = [tuple(rgb[index : index + 3]) for index in range(0, len(rgb), 3)]
        if samples != expected:
            raise OracleError("decoded saved pixels differ from the specified rotation")
        identity.update(
            width=height, height=width, rgb_sha256=_sha(bytes(v for pixel in samples for v in pixel))
        )
        return OracleCheck(
            True,
            "decoded saved pixels and dimensions equal the prescribed rotation",
            (
                "current_rotated_pixels",
                "current_image_dimensions",
                "preserved_fixture_siblings",
                "rotation_clockwise90" if clockwise else "rotation_counterclockwise90",
            ),
            str(Path(manifest["root"]) / asset),
            identity,
            limits=("current pixels do not establish historical UI rotation/save", "finite RGB fixture only"),
        )
    except (
        OracleError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        Image.DecompressionBombError,
    ) as exc:
        return OracleCheck(False, str(exc))
