"""Read-only, manifest-owned Finder targets independent of snapshot element numbers.

The file URL is resolved by Foundation, including Finder's file-reference URLs.
Neither the visible basename nor an old CUA element number establishes identity.
These helpers never perform file or UI mutations; native producers own input.
"""

from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jevdual import ax
from jevdual.app_oracles import OracleError, _asset_path, _read, _root_fd, _validate


class FinderTargetError(ax.AXError):
    """The owned target could not be established without guessing."""


def _attribute_names(element: Any) -> frozenset[str]:
    from ApplicationServices import AXUIElementCopyAttributeNames

    error, names = AXUIElementCopyAttributeNames(element, None)
    if error != 0 or names is None or isinstance(names, (str, bytes)):
        raise FinderTargetError("file_ax_unreadable", "Finder AX attribute inventory is unavailable")
    try:
        result = frozenset(names)
    except TypeError as exc:
        raise FinderTargetError("file_ax_unreadable", "Finder AX attribute inventory is invalid") from exc
    if len(result) > 256 or any(not isinstance(name, str) for name in result):
        raise FinderTargetError("file_ax_unreadable", "Finder AX attribute inventory is invalid")
    return result


def _read_attribute(element: Any, names: frozenset[str], name: str, *, optional: bool = False) -> Any:
    from ApplicationServices import AXUIElementCopyAttributeValue

    if name not in names:
        if optional:
            return None
        raise FinderTargetError("file_ax_unreadable", f"Finder AX element does not advertise {name}")
    error, value = AXUIElementCopyAttributeValue(element, name, None)
    # kAXErrorNoValue is an explicit absence only for optional attributes. In
    # particular, cannot-complete (-25204) must never hide an unreadable subtree.
    if optional and error == -25212:
        return None
    if error != 0 or (value is None and not optional):
        raise FinderTargetError("file_ax_unreadable", f"Finder AX {name} read failed ({error})")
    return value


def _element_identity(element: Any) -> int:
    import objc

    # Retaining wrappers during traversal keeps native pointer identity stable.
    return int(objc.pyobjc_id(element))


def _path(selector: str) -> str:
    if not isinstance(selector, str) or not selector.startswith("file:/"):
        raise FinderTargetError("file_selector_invalid", "use file:/ABSOLUTE/PATH")
    path = selector[5:]
    if "\x00" in path or not Path(path).is_absolute() or str(Path(path)) != path:
        raise FinderTargetError("file_selector_invalid", "file selector must be an exact absolute path")
    if any(part in (".", "..") for part in path.split("/")):
        raise FinderTargetError("file_selector_invalid", "file selector must not contain aliases")
    return path


@dataclass(frozen=True)
class FinderBinding:
    manifest_sha256: str
    root: str
    root_device: int
    root_inode: int
    path: str
    device: int
    inode: int

    def to_record(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> FinderBinding:
        try:
            binding = cls(**record)
            for name in ("manifest_sha256", "root", "path"):
                if not isinstance(getattr(binding, name), str) or not getattr(binding, name):
                    raise ValueError("invalid string")
            for name in ("root_device", "root_inode", "device", "inode"):
                if type(getattr(binding, name)) is not int or getattr(binding, name) < 0:
                    raise ValueError("invalid file identity")
            _path("file:" + binding.path)
            return binding
        except (TypeError, ValueError) as exc:
            raise FinderTargetError("file_binding_invalid", "retained Finder binding is invalid") from exc


def _identity(manifest: dict[str, Any], path: str) -> dict[str, Any]:
    try:
        _validate(manifest)
        relative = _asset_path(manifest, path)
        _, identity = _read(manifest, relative)
        return identity
    except (OracleError, OSError, ValueError, TypeError, KeyError) as exc:
        raise FinderTargetError("file_scope_invalid", "file is not an owned fixture asset") from exc


def bind(manifest: dict[str, Any], selector: str) -> FinderBinding:
    """Bootstrap ownership at the manifest's seeded source, before UI mutations."""
    path = _path(selector)
    identity = _identity(manifest, path)
    if path != str(Path(manifest["root"]) / manifest["paths"]["source"]):
        raise FinderTargetError("file_scope_invalid", "initial Finder target must be the seeded source")
    if identity["sha256"] != manifest["original_sha256"]:
        raise FinderTargetError("file_scope_invalid", "seeded source contents changed before binding")
    return FinderBinding(
        manifest["manifest_sha256"],
        manifest["root"],
        manifest["root_identity"]["device"],
        manifest["root_identity"]["inode"],
        path,
        identity["device"],
        identity["inode"],
    )


def rebind(binding: FinderBinding, manifest: dict[str, Any], selector: str) -> FinderBinding:
    """Read the same retained inode at an exact allowed path after a UI rename/move.

    This supplies current identity only; it does not establish how the path changed.
    """
    path = _path(selector)
    expected = (
        binding.manifest_sha256,
        binding.root,
        binding.root_device,
        binding.root_inode,
    )
    try:
        actual = (
            manifest["manifest_sha256"],
            manifest["root"],
            manifest["root_identity"]["device"],
            manifest["root_identity"]["inode"],
        )
    except (KeyError, TypeError) as exc:
        raise FinderTargetError("file_scope_changed", "retained fixture scope changed") from exc
    if actual != expected:
        raise FinderTargetError("file_scope_changed", "retained fixture scope changed")
    identity = _identity(manifest, path)
    if (identity["device"], identity["inode"]) != (binding.device, binding.inode):
        raise FinderTargetError("file_identity_changed", "the target path names a different file")
    return FinderBinding(*expected, path, binding.device, binding.inode)


def file_url_path(value: Any) -> str | None:
    """Resolve normal and file-reference AXURLs through macOS Foundation."""
    from Foundation import NSURL

    try:
        url = NSURL.URLWithString_(str(value))
        if url is None or not url.isFileURL() or url.host() not in (None, "", "localhost"):
            return None
        concrete = url.filePathURL()
        path = concrete.path() if concrete is not None else None
        return _path("file:" + str(path)) if path else None
    except (ValueError, TypeError, FinderTargetError):
        return None


@dataclass(frozen=True)
class FinderTarget:
    element: Any = field(repr=False, compare=False)
    pid: int
    window_id: int
    binding: FinderBinding
    ax_url: str
    role: str
    value: str
    frame: ax.Frame

    def to_record(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "window_id": self.window_id,
            "binding": self.binding.to_record(),
            "ax_url": self.ax_url,
            "role": self.role,
            "value": self.value,
            "frame": asdict(self.frame),
            "basis": "fresh_ax_file_url_and_owned_inode",
        }


def resolve(
    pid: int,
    window_id: int,
    binding: FinderBinding,
    manifest: dict[str, Any],
    *,
    limit: int = 4000,
) -> FinderTarget:
    """Read the exact one Finder filename field in the freshly bound AX window."""
    rebind(binding, manifest, "file:" + binding.path)
    matches = _filename_matches(pid, window_id, binding.path, limit=limit)
    if len(matches) != 1:
        raise FinderTargetError(
            "file_target_ambiguous" if matches else "file_target_missing",
            f"{len(matches)} Finder filename fields resolve to the exact owned file",
        )
    element, raw_url, role, value, frame = matches[0]
    rebind(binding, manifest, "file:" + binding.path)
    return FinderTarget(element, pid, window_id, binding, raw_url, role, value, frame)


def _filename_matches(pid: int, window_id: int, path: str, *, limit: int = 4000) -> list[tuple]:
    """Complete bounded AXURL search shared by source and destination-marker binding."""
    stack = [ax.window_element(pid, window_id)]
    matches: list[tuple] = []
    seen = 0
    identities: set[int] = set()
    retained: list[Any] = []
    while stack:
        if seen >= limit:
            raise FinderTargetError("file_tree_incomplete", "Finder AX traversal exceeded its bound")
        element = stack.pop()
        retained.append(element)
        identity = _element_identity(element)
        if identity in identities:
            raise FinderTargetError("file_tree_cycle", "Finder AX tree repeats an element")
        identities.add(identity)
        seen += 1
        names = _attribute_names(element)
        role = _read_attribute(element, names, "AXRole")
        if not isinstance(role, str) or not role.startswith("AX"):
            raise FinderTargetError("file_ax_unreadable", "Finder AX role is invalid")
        raw_url = _read_attribute(element, names, "AXURL", optional=True) if role == "AXTextField" else None
        if raw_url is not None and file_url_path(raw_url) == path:
            value = _read_attribute(element, names, "AXValue")
            frame = ax.frame_of(element)
            if (
                value != Path(path).name
                or frame is None
                or not all(math.isfinite(v) for v in (frame.x, frame.y, frame.w, frame.h))
                or frame.w <= 0
                or frame.h <= 0
            ):
                raise FinderTargetError(
                    "file_field_changed", "Finder file field has an unexpected value or frame"
                )
            matches.append((element, str(raw_url), role, value, frame))
        children = _read_attribute(element, names, "AXChildren", optional=True)
        if children is not None:
            if isinstance(children, (str, bytes)):
                raise FinderTargetError("file_ax_unreadable", "Finder AX children are invalid")
            try:
                children = list(children)
            except TypeError as exc:
                raise FinderTargetError("file_ax_unreadable", "Finder AX children are invalid") from exc
            if len(children) > limit - seen:
                raise FinderTargetError(
                    "file_tree_incomplete", "Finder AX children exceed the traversal bound"
                )
            stack.extend(reversed(children))
    return matches


def move_destination(manifest: dict[str, Any], directory: str) -> dict[str, Any]:
    """Bind only the declared organized directory and its protected marker, read-only."""
    path = _path("file:" + directory)
    try:
        _validate(manifest)
        expected = Path(manifest["root"]) / Path(manifest["paths"]["organized"]).parent
        if path != str(expected):
            raise ValueError("destination is not the declared organized directory")
        marker_relative = str(Path(manifest["paths"]["organized"]).parent / "keep.bin")
        _, marker = _read(manifest, marker_relative)
        if marker["sha256"] != manifest["protected"][marker_relative]:
            raise ValueError("destination marker changed")
        fd = _root_fd(Path(manifest["root"]), manifest["root_identity"])
        try:
            for part in expected.relative_to(manifest["root"]).parts:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
            info = os.fstat(fd)
        finally:
            os.close(fd)
        return {
            "path": path,
            "device": info.st_dev,
            "inode": info.st_ino,
            "sentinel_path": str(expected / "keep.bin"),
            "sentinel_identity": marker,
        }
    except (OracleError, OSError, ValueError, TypeError, KeyError) as exc:
        raise FinderTargetError(
            "file_destination_invalid", "the owned move destination is unavailable"
        ) from exc


def resolve_marker(pid: int, window_id: int, manifest: dict[str, Any], directory: str) -> dict[str, Any]:
    """Prove the same bound Finder window now exposes the exact owned destination marker."""
    destination = move_destination(manifest, directory)
    window = ax.window_element(pid, window_id)
    title = _read_attribute(window, _attribute_names(window), "AXTitle")
    if title != Path(directory).name:
        raise FinderTargetError(
            "file_destination_unverified", "Finder's bound window title is not the destination directory"
        )
    matches = _filename_matches(pid, window_id, destination["sentinel_path"])
    if len(matches) != 1:
        raise FinderTargetError(
            "file_destination_unverified", "the owned destination marker is missing or ambiguous"
        )
    if move_destination(manifest, directory) != destination:
        raise FinderTargetError(
            "file_destination_changed", "the owned destination changed during observation"
        )
    return {
        "pid": pid,
        "window_id": window_id,
        "window_title": title,
        **destination,
        "ax_url": matches[0][1],
        "basis": "fresh_ax_destination_marker_and_owned_directory",
    }


def file_identity(manifest: dict[str, Any], binding: FinderBinding) -> dict[str, Any]:
    """Read source bytes/identity without supplying any mutation route."""
    rebind(binding, manifest, "file:" + binding.path)
    return _identity(manifest, binding.path)


def candidate_id(target: FinderTarget, menu: Any) -> int:
    """Map the direct AX target to exactly one candidate in the current snapshot."""
    if (menu.pid, menu.window_id) != (target.pid, target.window_id):
        raise FinderTargetError("file_window_changed", "the snapshot names a different owned window")
    hits = []
    for candidate in menu.menu.candidates:
        frame = menu.frames.get(candidate.id)
        if (
            frame is not None
            and menu.ax_roles.get(candidate.id) == target.role
            and menu.values.get(candidate.id) == target.value
            and target.frame.near(ax.Frame(*frame))
        ):
            hits.append(candidate.id)
    if len(hits) != 1:
        raise FinderTargetError(
            "file_candidate_ambiguous" if hits else "file_candidate_missing",
            "the fresh snapshot does not identify exactly one direct AX file target",
        )
    return hits[0]
