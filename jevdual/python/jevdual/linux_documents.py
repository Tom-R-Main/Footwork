"""Application-specific Mousepad scope checks; no generic title-to-path inference.

The caller supplies an existing canonical absolute document path. The supported
Mousepad binary must name that exact path in its qualified top-level window.
This identifies the selected document under that application contract; it does
not prove that editor contents were saved. Saved bytes require separate readback.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from jevdual import linux_ax
from jevdual.ax import AXError

_EXECUTABLE = "/usr/bin/mousepad"
_TITLE_SUFFIX = " - Mousepad"


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    start: str
    executable: str
    name: str
    uid: int


@dataclass(frozen=True)
class FileIdentity:
    device: int
    inode: int


@dataclass(frozen=True)
class MousepadDocument:
    path: str
    process: ProcessIdentity
    window_id: int
    element: linux_ax.Element
    file: FileIdentity
    binding_basis: str = "mousepad_full_path_window_title"
    persistence: str = "not_checked"


def _process_identity(pid: int) -> ProcessIdentity:
    import psutil

    try:
        process = psutil.Process(pid)
        with process.oneshot():
            result = ProcessIdentity(pid, process.create_time().hex(), process.exe(),
                                     process.name(), process.uids().effective)
        if result.executable != _EXECUTABLE or result.name != "mousepad" or result.uid != os.getuid():
            raise AXError("application_unqualified", "only this user's /usr/bin/mousepad process is qualified")
        return result
    except (psutil.Error, OSError) as exc:
        raise AXError("lost_identity", "the scoped Mousepad process identity is unavailable") from exc


def _canonical_path(document: str | Path) -> Path:
    raw = str(document)
    if not raw or len(raw) > 4096 or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        raise AXError("document_unqualified", "the scoped document path must be bounded and contain no controls")
    path = Path(raw)
    try:
        if not path.is_absolute() or str(path) != raw or path.resolve(strict=True) != path:
            raise AXError("document_unqualified", "an existing canonical absolute document path is required")
    except (OSError, RuntimeError, ValueError) as exc:
        raise AXError("document_unqualified", "the scoped document path is unavailable") from exc
    return path


def _file_identity(path: Path) -> FileIdentity:
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise AXError("document_unqualified", "the scoped document must be an owned regular file")
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise AXError("lost_identity", "the scoped document changed while being checked")
        return FileIdentity(info.st_dev, info.st_ino)
    except OSError as exc:
        raise AXError("document_unqualified", "the scoped document cannot be checked without following links") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _window_title(element: linux_ax.Element) -> str:
    # A sister module uses the validated bus seam so generic linux_ax need not
    # acquire application/title conventions or publish unqualified path guesses.
    with linux_ax._bound(element) as bus:
        title = bus.prop(element.ref, linux_ax._ACCESSIBLE, "Name")
        if not isinstance(title, str) or len(title) > 8192:
            raise AXError("document_unqualified", "the exact Mousepad window title is unavailable")
        return title


def _require_title(title: str, path: Path) -> None:
    expected = str(path) + _TITLE_SUFFIX
    if title not in (expected, "*" + expected):
        raise AXError("lost_identity", "the selected Mousepad window does not name the exact scoped path")


def bind(pid: int, window_id: int, expected_document: str | Path) -> MousepadDocument:
    """Bind only an explicitly scoped document; discovery is not an authority source.

    Qualified titles are the full path and Mousepad suffix, optionally prefixed
    by one literal asterisk observed after editing. Basenames, tilde shortening,
    altered suffixes and other modified-title conventions refuse. The asterisk
    does not establish whether or where the buffer was persisted.
    """
    path = _canonical_path(expected_document)
    process = _process_identity(pid)
    before = _file_identity(path)
    element = linux_ax.resolve(pid, window_id, "frame", None)
    if len(element.chain) != 2 or element.process_start != process.start:
        raise AXError("lost_identity", "the Mousepad top-level does not match the original process")
    _require_title(_window_title(element), path)
    if _process_identity(pid) != process or _file_identity(path) != before:
        raise AXError("lost_identity", "the scoped process or document changed while binding")
    return MousepadDocument(str(path), process, window_id, element, before)


def revalidate(binding: MousepadDocument) -> None:
    """Pre-input check of the retained window/process/file, with no re-resolution.

    A legitimate atomic save can replace an inode; this check refuses that old
    binding. A new binding and independent saved-state readback are then needed.
    """
    path = _canonical_path(binding.path)
    if _process_identity(binding.process.pid) != binding.process or _file_identity(path) != binding.file:
        raise AXError("lost_identity", "the original Mousepad process or scoped document changed")
    _require_title(_window_title(binding.element), path)
    if _process_identity(binding.process.pid) != binding.process or _file_identity(path) != binding.file:
        raise AXError("lost_identity", "the original Mousepad process or scoped document changed")
