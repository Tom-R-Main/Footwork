"""Read-only, digest-bound equality of external artifact bytes; no session provenance."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path

MAX_ARTIFACT_BYTES = 1024 * 1024
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class ArtifactError(Exception):
    """A file cannot supply stable, bounded evidence."""


def read_regular(path: Path, *, limit: int = MAX_ARTIFACT_BYTES) -> bytes:
    """Read a regular file without following a final symlink; detect concurrent mutation."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ArtifactError("not a regular file")
            if before.st_size > limit:
                raise ArtifactError(f"file exceeds {limit} byte limit")
            data = source.read(limit + 1)
            after = os.fstat(source.fileno())
        if len(data) > limit:
            raise ArtifactError(f"file exceeds {limit} byte limit")
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise ArtifactError("file changed during read")
        return data
    except OSError as exc:
        raise ArtifactError("file is missing, symlinked or unreadable") from exc


def check_artifact(path: Path, expected_file: Path, expected_sha256: str) -> dict:
    """Compare exact current bytes to a digest-bound source; never print artifact text."""
    result = {"ok": False, "path": str(path), "expected_file": str(expected_file),
              "expected_sha256": expected_sha256,
              "claims": [], "limit_bytes": MAX_ARTIFACT_BYTES}
    if not isinstance(expected_sha256, str) or not _DIGEST.fullmatch(expected_sha256):
        return {**result, "detail": "expected SHA256 must contain 64 lowercase hexadecimal characters"}
    try:
        expected = read_regular(expected_file)
        source_sha = hashlib.sha256(expected).hexdigest()
        result["source_sha256"] = source_sha
        result["expected_bytes"] = len(expected)
        if source_sha != expected_sha256:
            return {**result, "detail": "expected source no longer matches its bound digest"}
        observed = read_regular(path)
        result["observed_sha256"] = hashlib.sha256(observed).hexdigest()
        result["observed_bytes"] = len(observed)
        if observed != expected:
            return {**result, "detail": "destination bytes differ from the bound expected source"}
        # Recheck the source after destination read; mutable source cannot silently change approval.
        if hashlib.sha256(read_regular(expected_file)).hexdigest() != expected_sha256:
            return {**result, "detail": "expected source changed during verification"}
        return {**result, "ok": True, "detail": "current bytes equal the digest-bound expected source",
                "claims": ["current_artifact_byte_equality"]}
    except ArtifactError as exc:
        return {**result, "detail": str(exc)}
