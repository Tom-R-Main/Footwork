"""Strict, bounded case inputs; no qualification-suite discovery or evaluation."""

import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path

MAX_CASE_BYTES = 64 * 1024
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")


class CaseError(ValueError):
    pass


def fields(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise CaseError(f"{label} has invalid fields")


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise CaseError("case coordinates/settings must be finite numbers")
    return float(value)


def validate(case):
    fields(case, ("version", "case_id", "scene", "max_actions", "work_order"), "episode case")
    if type(case["version"]) is not int or case["version"] != 1:
        raise CaseError("case must be version 1")
    if not isinstance(case["case_id"], str) or not ID.fullmatch(case["case_id"]):
        raise CaseError("case ID must be an exact bounded identifier")
    if type(case["max_actions"]) is not int or not 1 <= case["max_actions"] <= 8:
        raise CaseError("case action budget must be 1-8 admitted actions")
    scene = case["scene"]
    fields(scene, ("block_xy", "illumination_scale", "occlusion_fraction", "camera_offset_x_m"), "case scene")
    if not isinstance(scene["block_xy"], list) or len(scene["block_xy"]) != 2:
        raise CaseError("initial block position must contain two coordinates")
    x, y = (finite(value) for value in scene["block_xy"])
    if not -.24 <= x <= .2 or not -.10 <= y <= .10:
        raise CaseError("initial block must be within the bounded tabletop")
    if not 0 <= finite(scene["illumination_scale"]) <= 2:
        raise CaseError("illumination scale must be 0-2")
    if not 0 <= finite(scene["occlusion_fraction"]) <= 1:
        raise CaseError("occlusion fraction must be 0-1")
    if not -.10 <= finite(scene["camera_offset_x_m"]) <= .10:
        raise CaseError("camera offset exceeds the declared scene envelope")
    order = case["work_order"]
    fields(order, ("version", "order_id", "project", "part_id", "target_zone"), "case work order")
    if type(order["version"]) is not int or order["version"] != 1 or order["part_id"] != "block":
        raise CaseError("case must contain a version 1 block work order")
    fields(order["project"], ("namespace", "project_id"), "case project")
    for value in (order["order_id"], *order["project"].values()):
        if not isinstance(value, str) or not ID.fullmatch(value):
            raise CaseError("case work-order identities are invalid")
    zone = order["target_zone"]
    fields(zone, ("x_min", "x_max", "y_min", "y_max"), "case target zone")
    for value in zone.values():
        finite(value)
    if not (-.35 <= zone["x_min"] < zone["x_max"] <= .35 and -.2 <= zone["y_min"] < zone["y_max"] <= .2):
        raise CaseError("case target zone must be a bounded nonempty rectangle")
    return case


def read_bytes(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_CASE_BYTES:
                raise CaseError("case input is not a bounded regular file")
            data = source.read(MAX_CASE_BYTES + 1)
            after = os.fstat(source.fileno())
        if len(data) > MAX_CASE_BYTES or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise CaseError("case changed during read or exceeds its size limit")
        return data
    except OSError as exc:
        raise CaseError("case source is missing, symlinked or unreadable") from exc


def decode(data):
    def unique(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise CaseError("duplicate case JSON key")
            output[key] = value
        return output

    def nonfinite(value):
        raise CaseError("case JSON contains nonfinite values")

    try:
        return validate(json.loads(data, object_pairs_hook=unique, parse_constant=nonfinite))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CaseError("case source is not UTF-8 JSON") from exc


def load(path, expected_sha256):
    if not isinstance(expected_sha256, str) or not SHA.fullmatch(expected_sha256):
        raise CaseError("case SHA256 must be exact lowercase hexadecimal")
    path = Path(os.path.abspath(os.fspath(path)))
    try:
        if path != path.resolve(strict=True) or path.is_symlink():
            raise CaseError("case source must have a canonical path without symlinks")
    except OSError as exc:
        raise CaseError("case source is unavailable") from exc
    content = read_bytes(path)
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise CaseError("case source does not match its bound digest")
    return decode(content), path, content
