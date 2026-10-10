"""Bounded stdlib schemas and owned paths for the local versioned order app."""

import contextlib
import fcntl
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
MAX_BYTES = 64 * 1024
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
UUID = re.compile(r"[0-9a-f]{32}\Z")


class Refusal(ValueError):
    pass


def sha(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode(content):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refusal("duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(_):
        raise Refusal("nonfinite JSON value")

    if len(content) > MAX_BYTES:
        raise Refusal("JSON exceeds its bounded size")
    try:
        return json.loads(content, object_pairs_hook=unique, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Refusal("invalid UTF-8 JSON") from exc


def fields(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Refusal(f"{label} has invalid fields")


def identity(value):
    if not isinstance(value, str) or not IDENTITY.fullmatch(value):
        raise Refusal("identity must be an exact bounded safe string")
    return value


def revision(value):
    if type(value) is not int or not 1 <= value <= 2147483647:
        raise Refusal("revision must be a positive bounded integer")
    return value


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise Refusal("target coordinates must be finite numbers")
    return float(value)


def validate_zone(zone):
    fields(zone, ("x_min", "x_max", "y_min", "y_max"), "target zone")
    for value in zone.values():
        finite(value)
    if not (-.35 <= zone["x_min"] < zone["x_max"] <= .35 and -.2 <= zone["y_min"] < zone["y_max"] <= .2):
        raise Refusal("target zone must be a bounded nonempty tabletop rectangle")
    return zone


def validate_work_order(order):
    fields(order, ("version", "order_id", "project", "part_id", "target_zone"), "work order")
    if type(order["version"]) is not int or order["version"] != 1 or order["part_id"] != "block":
        raise Refusal("only version 1 block work orders are supported")
    fields(order["project"], ("namespace", "project_id"), "project identity")
    for value in (order["order_id"], *order["project"].values()):
        identity(value)
    validate_zone(order["target_zone"])
    return order


def validate_order(order):
    fields(order, ("version", "order_id", "project", "part_id", "target_zone", "revision", "state"), "application order")
    validate_work_order({key: value for key, value in order.items() if key not in {"revision", "state"}})
    revision(order["revision"])
    if order["state"] not in {"open", "cancelled", "fulfilled"}:
        raise Refusal("application order state is invalid")
    return order


def directory(path, create=False):
    root = Path(os.path.abspath(os.fspath(path)))
    if root == OUTPUT or OUTPUT not in root.parents:
        raise Refusal("owned directory must be under physical-workcell/output")
    current = OUTPUT
    for part in (None, *root.relative_to(OUTPUT).parts):
        if part is not None:
            current /= part
        if create:
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                pass
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Refusal("owned directories must be private and free of symlinks")
    return root


def read_bytes(path, maximum=MAX_BYTES):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
                raise Refusal("input must be a bounded regular file")
            content = source.read(maximum + 1)
            after = os.fstat(source.fileno())
        if len(content) > maximum or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise Refusal("input changed while reading")
        return content
    except OSError as exc:
        raise Refusal("input is missing, symlinked or unreadable") from exc


def create_file(path, content):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as sink:
        sink.write(content)
        sink.flush()
        os.fsync(sink.fileno())
    sync_directory(path.parent)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def persist(path, value):
    import uuid

    staging = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    try:
        create_file(staging, encoded(value))
        os.replace(staging, path)
        sync_directory(path.parent)
    finally:
        with contextlib.suppress(FileNotFoundError):
            staging.unlink()


@contextlib.contextmanager
def locked(root):
    fd = os.open(root / "app.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Refusal("invalid application lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal("another process owns this application directory") from exc
        yield
    finally:
        os.close(fd)


def paths_for(app_dir, lease_id):
    if not isinstance(lease_id, str) or not UUID.fullmatch(lease_id):
        raise Refusal("lease identity must be an exact UUID")
    workspace = app_dir / "workcells" / lease_id
    return {"app_dir": str(app_dir), "workspace_dir": str(workspace), "run_dir": str(workspace / "r"),
            "controller_dir": str(workspace / "c"), "handoff_dir": str(workspace / "h")}
