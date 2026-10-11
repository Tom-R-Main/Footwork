"""Computer-side optical measurement worker; exact image in, durable SQLite row out."""
import argparse
import json
import os
import sqlite3
import stat
import sys
from pathlib import Path

import image_guided as vision
import order_protocol as protocol
import workcell as body

SCHEMA = """CREATE TABLE IF NOT EXISTS measurements (
 operation_id TEXT PRIMARY KEY, job_id TEXT UNIQUE NOT NULL, bench_id TEXT NOT NULL,
 generation INTEGER NOT NULL, image_sha256 TEXT NOT NULL, state_sha256 TEXT NOT NULL,
 receipt_json TEXT NOT NULL)"""


def image_and_location(content):
    try:
        image = vision.decode_png(content)
        return image, vision.locate(image)
    except vision.Refusal as exc:
        raise body.Refusal("RGB evidence is malformed or its required silhouettes are unavailable") from exc


def compute(packet, content):
    if body.sha(content) != packet["image_sha256"]:
        raise body.Refusal("measurement image digest changed")
    image, detected = image_and_location(content)
    located = detected["block"]
    red, green, blue = image.astype(float).transpose(2, 0, 1)
    mask = (red >= 80) & (red >= 1.3 * green) & (green >= 1.35 * blue)
    yy, xx = mask.nonzero()
    if len(xx) == 0:
        raise body.Refusal("orange measurement silhouette unavailable")
    return {"method": "simulated_orange_RGB_footprint", "orange_pixel_count": len(xx),
            "centroid_pixel_xy": [float(xx.mean()), float(yy.mean())],
            "block_box": located["box"], "block_center_xy": vision.image_world_center(located["box"]),
            "footprint_area_m2": float(len(xx) * packet["calibration"]["meters_per_pixel"] ** 2)}


def read_result(root, operation_id):
    path = protocol.directory(root) / "measurements.sqlite"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise body.Refusal("measurement database must be an owned private regular file")
    except OSError as exc:
        raise body.Refusal("measurement database is missing or symlinked") from exc
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT operation_id,job_id,bench_id,generation,image_sha256,state_sha256,receipt_json FROM measurements WHERE operation_id=?", (operation_id,)).fetchone()
    if row is None:
        raise body.Refusal("computer measurement has no durable receipt")
    result = body.decoded(row[6].encode())
    keys = ("operation_id", "job_id", "bench_id", "generation", "image_sha256", "state_sha256")
    if tuple(result.get(k) for k in keys) != row[:6]:
        raise body.Refusal("measurement database columns disagree with the durable receipt")
    body.fields(result, ("version", "source_kind", "operation_id", "bench_id", "job_id", "generation",
                        "native_time_s", "image_sha256", "state_sha256", "worker_pid", "measurement"), "measurement receipt")
    if (type(result["version"]) is not int or result["version"] != 1 or result["source_kind"] != body.SOURCE_KIND or
            type(result["generation"]) is not int or result["generation"] < 0 or
            type(result["worker_pid"]) is not int or result["worker_pid"] <= 0):
        raise body.Refusal("measurement receipt has invalid types")
    for key in ("operation_id", "bench_id", "job_id"):
        protocol.identity(result[key])
    for key in ("image_sha256", "state_sha256"):
        if not isinstance(result[key], str) or not body.DIGEST.fullmatch(result[key]):
            raise body.Refusal("measurement receipt digest is invalid")
    body.number(result["native_time_s"])
    measured = result["measurement"]
    body.fields(measured, ("method", "orange_pixel_count", "centroid_pixel_xy", "block_box", "block_center_xy",
                           "footprint_area_m2"), "optical measurement")
    if (measured["method"] != "simulated_orange_RGB_footprint" or type(measured["orange_pixel_count"]) is not int or
            not 0 < measured["orange_pixel_count"] <= 640 * 360):
        raise body.Refusal("optical measurement count or method is invalid")
    for key in ("centroid_pixel_xy", "block_center_xy"):
        if not isinstance(measured[key], list) or len(measured[key]) != 2:
            raise body.Refusal("measurement center schema is invalid")
        for value in measured[key]:
            body.number(value)
    if (not isinstance(measured["block_box"], list) or len(measured["block_box"]) != 4 or
            any(type(v) is not int for v in measured["block_box"]) or
            body.number(measured["footprint_area_m2"]) <= 0):
        raise body.Refusal("measurement footprint schema is invalid")
    return result


def run(root, operation_id, packet_file, packet_sha256):
    root = protocol.directory(root)
    protocol.identity(operation_id)
    packet_file = Path(packet_file)
    if packet_file.parent != root / "requests":
        raise body.Refusal("measurement request must be bench-owned")
    packet_bytes = body.read_bytes(packet_file)
    if body.sha(packet_bytes) != packet_sha256:
        raise body.Refusal("measurement packet digest changed")
    packet = body.decoded(packet_bytes)
    manifest = body.decoded(body.read_bytes(root / "bench.json"))
    busy = manifest.get("busy")
    if (not isinstance(busy, dict) or busy.get("operation_id") != operation_id or busy.get("kind") != "measure" or
            manifest["bench_id"] != packet["bench_id"] or manifest["generation"] != packet["generation"] or
            manifest["state_sha256"] != packet["state_sha256"] or manifest["active_job"]["job_id"] != packet["job_id"]):
        raise body.Refusal("measurement does not match the retained dispatch intent")
    image_path = Path(packet["image_path"])
    if image_path.parent != root / "images":
        raise body.Refusal("measurement image must be bench-owned")
    result = {"version": 1, "source_kind": body.SOURCE_KIND, "operation_id": operation_id, "bench_id": packet["bench_id"],
              "job_id": packet["job_id"], "generation": packet["generation"],
              "native_time_s": packet["native_time_s"], "image_sha256": packet["image_sha256"],
              "state_sha256": packet["state_sha256"], "worker_pid": os.getpid(),
              "measurement": compute(packet, body.read_bytes(image_path))}
    path = root / "measurements.sqlite"
    if path.is_symlink():
        raise body.Refusal("measurement database cannot be a symlink")
    with sqlite3.connect(path) as connection:
        connection.execute(SCHEMA)
        previous = connection.execute("SELECT receipt_json FROM measurements WHERE operation_id=?", (operation_id,)).fetchone()
        if previous:
            old = body.decoded(previous[0].encode())
            if any(old[k] != result[k] for k in ("bench_id", "job_id", "generation", "image_sha256", "state_sha256")):
                raise body.Refusal("measurement operation identity conflicts")
            return old
        connection.execute("INSERT INTO measurements VALUES (?,?,?,?,?,?,?)", (
            operation_id, result["job_id"], result["bench_id"], result["generation"], result["image_sha256"],
            result["state_sha256"], body.encoded(result).decode()))
    path.chmod(0o600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--packet-file", required=True, type=Path)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.root, args.operation_id, args.packet_file, args.packet_sha256), sort_keys=True))
        return 0
    except (body.Refusal, OSError, sqlite3.Error, KeyError, ValueError) as exc:
        print(json.dumps({"state": "refused", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
