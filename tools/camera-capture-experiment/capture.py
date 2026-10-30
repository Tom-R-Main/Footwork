"""Bounded native-camera acquisition; no Footwork runtime dependencies."""

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT = (Path(os.environ["FOOTWORK_TOOL_OUTPUT_ROOT"]) / BASE.name
          if os.environ.get("FOOTWORK_TOOL_OUTPUT_ROOT") else BASE / "output")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
AV_DEVICE = re.compile(r"\[AVFoundation indev @ [^]]+\] \[(\d+)\] (.+)$")
LINUX_DEVICE = re.compile(r"/dev/video(?:0|[1-9][0-9]*)\Z")


class Refusal(Exception):
    """An unmet prerequisite or unverifiable operation."""

    def __init__(self, reason, private_stderr=None):
        super().__init__(reason)
        self.private_stderr = private_stderr


def run_process(argv, timeout):
    """Start one owned process group; clean descendants on exit or interruption."""
    child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True, umask=0o077)
    try:
        stdout, stderr = child.communicate(timeout=timeout)
        return child.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except subprocess.TimeoutExpired as exc:
        detail = exc.stderr or b""
        if isinstance(detail, bytes):
            detail = detail.decode(errors="replace")
        raise Refusal("child process exceeded its time limit", private_stderr=detail) from exc
    finally:
        # The group may outlive its leader (including pipe-holding grandchildren).
        with contextlib.suppress(ProcessLookupError):
            os.killpg(child.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            child.communicate(timeout=2)


def private_directory(path):
    """Create private directories without following caller-selected symlinks."""
    raw = Path(os.path.abspath(os.fspath(path)))
    if raw == OUTPUT or OUTPUT not in raw.parents:
        raise Refusal("run directory must be a subdirectory of the experiment's output directory")
    current = OUTPUT
    for part in (None, *raw.relative_to(OUTPUT).parts):
        if part is not None:
            current = current / part
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            pass
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise Refusal("run directory must contain only owned directories, without symlinks")
        if info.st_mode & 0o077:
            raise Refusal("run directories must be private (permissions 0700)")
    return raw


@contextlib.contextmanager
def locked(root):
    fd = os.open(root / "lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Refusal("invalid lock file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal("another process owns this run directory") from exc
        yield
    finally:
        os.close(fd)


def read_json(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise Refusal("ledger is not a regular file")
            record = json.load(source)
            if (not isinstance(record, dict) or record.get("state") not in {"pending", "unknown", "acquired"}
                    or not isinstance(record.get("token"), str) or not TOKEN.fullmatch(record["token"])
                    or not isinstance(record.get("request"), dict)):
                raise Refusal("ledger structure is invalid; inspect this run directory")
            return record
    except (OSError, ValueError) as exc:
        raise Refusal("ledger cannot be read; inspect this run directory") from exc


def persist(path, record):
    staging = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as sink:
            json.dump(record, sink, indent=2, sort_keys=True)
            sink.write("\n")
            sink.flush()
            os.fsync(sink.fileno())
        os.replace(staging, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        with contextlib.suppress(FileNotFoundError):
            staging.unlink()


def private_diagnostic(path, stderr):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as sink:
        sink.write(stderr.encode(errors="replace")[:65536])
        sink.flush()
        os.fsync(sink.fileno())


def parse_physical(data):
    entries = data.get("SPCameraDataType")
    if not isinstance(entries, list):
        raise Refusal("system_profiler camera inventory is unavailable")
    # The system inventory may include software cameras: require a model identifier.
    result = []
    for item in entries:
        name = item.get("_name", "")
        model = item.get("spcamera_model-id", "")
        if name and model and not re.search(r"virtual|screen|obs|continuity", name + " " + model, re.IGNORECASE):
            result.append(name)
    return result


def parse_avfoundation(stderr):
    names = []
    in_video = False
    for line in stderr.splitlines():
        if "AVFoundation video devices:" in line:
            in_video = True
        elif "AVFoundation audio devices:" in line:
            in_video = False
        elif in_video:
            match = AV_DEVICE.search(line)
            if match:
                names.append(match.group(2).strip())
    return names


def binaries():
    found = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe", "swift", "system_profiler")}
    if not found["ffmpeg"] or not found["ffprobe"]:
        raise Refusal("installed ffmpeg and ffprobe are required; nothing will be installed")
    return found


def permission(root, programs):
    if not programs["swift"]:
        return "unavailable"
    cache = root / "swift-module-cache"
    if cache.is_symlink():
        raise Refusal("invalid Swift cache directory")
    cache.mkdir(mode=0o700, exist_ok=True)
    rc, stdout, _ = run_process([programs["swift"], "-module-cache-path", str(cache),
                                str(BASE / "permission.swift")], 20)
    status = stdout.strip()
    if rc or status not in {"authorized", "denied", "restricted", "not_determined", "unknown"}:
        return "unavailable"
    return status


def backend_name():
    if sys.platform == "linux":
        return "v4l2"
    if sys.platform == "darwin":
        return "avfoundation"
    raise Refusal("native camera capture is supported only on macOS and Linux")


def linux_device_identity(camera):
    """Inspect one exact node without opening it or claiming camera permission.

    A V4L2 node may be virtual or expose metadata rather than video. Only the
    explicit capture can establish that FFmpeg acquired a decodable frame.
    """
    if not isinstance(camera, str) or not LINUX_DEVICE.fullmatch(camera):
        raise Refusal("Linux camera must be an explicit /dev/videoN path")
    try:
        info = Path(camera).lstat()
    except OSError as exc:
        raise Refusal("selected Linux video node is unavailable") from exc
    if not stat.S_ISCHR(info.st_mode) or os.major(info.st_rdev) != 81:
        raise Refusal("selected Linux video node must be a V4L2 character device, without symlinks")
    return {"path": camera, "device": info.st_dev, "inode": info.st_ino,
            "rdev": info.st_rdev}


def linux_inventory(programs):
    devices = []
    for path in sorted(Path("/dev").glob("video*")):
        try:
            devices.append(linux_device_identity(str(path)))
        except Refusal:
            continue
    return {"backend": "v4l2", "video_devices": devices,
            "eligible_cameras": [device["path"] for device in devices],
            "permission_status": "not_checked",
            "permission_query": "device metadata only; no device opened or permission established",
            "device_kind": "unqualified; may be virtual or non-capture nodes", "programs": programs}


def doctor(root):
    programs = binaries()
    if backend_name() == "v4l2":
        return linux_inventory(programs)
    if not programs["system_profiler"]:
        raise Refusal("macOS system_profiler is required")
    rc, stdout, _ = run_process([programs["system_profiler"], "SPCameraDataType", "-json"], 15)
    if rc:
        raise Refusal("physical camera inventory failed")
    try:
        physical = parse_physical(json.loads(stdout))
    except ValueError as exc:
        raise Refusal("physical camera inventory was not valid JSON") from exc
    # AVFoundation enumeration returns a nonzero code because no input is opened.
    _, _, stderr = run_process([programs["ffmpeg"], "-hide_banner", "-nostdin", "-f",
                               "avfoundation", "-list_devices", "true", "-i", ""], 10)
    video = parse_avfoundation(stderr)
    if not video:
        raise Refusal("FFmpeg AVFoundation video inventory was unavailable")
    physical_unique = [name for name in physical if physical.count(name) == 1 and video.count(name) == 1]
    return {"backend": "avfoundation", "physical_cameras": physical, "avfoundation_video_devices": video,
            "eligible_cameras": physical_unique, "permission_status": permission(root, programs),
            "permission_query": "Swift AVFoundation authorizationStatus(.video); no request",
            "programs": programs}


def select_camera(camera, inventory, allow_permission_prompt=False):
    if backend_name() == "v4l2":
        if allow_permission_prompt:
            raise Refusal("--allow-permission-prompt applies only to macOS")
        current = linux_device_identity(camera)
        if inventory.get("backend") != "v4l2" or current not in inventory.get("video_devices", []):
            raise Refusal("selected Linux video node changed or was not in the observed inventory")
        return current
    if not camera or ":" in camera or camera.startswith("-"):
        raise Refusal("camera name is invalid")
    if camera not in inventory["eligible_cameras"]:
        raise Refusal("camera must exactly match one unique physical and AVFoundation device name")
    if inventory["permission_status"] in {"denied", "restricted"}:
        raise Refusal("camera permission query reports denied or restricted; inspect macOS privacy settings")
    if inventory["permission_status"] != "authorized" and not allow_permission_prompt:
        raise Refusal("camera permission is unestablished; explicit --allow-permission-prompt is required")


def artifact_info(path, ffprobe):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise Refusal("artifact is not a regular file")
        digest = hashlib.sha256()
        size = 0
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    if not size:
        raise Refusal("artifact is empty")
    rc, stdout, stderr = run_process([ffprobe, "-v", "error", "-count_frames", "-show_entries",
                                     "stream=codec_name,width,height,nb_read_frames", "-of", "json",
                                     str(path)], 10)
    if rc or stderr.strip():
        raise Refusal("ffprobe could not decode the artifact")
    try:
        streams = json.loads(stdout)["streams"]
        stream = streams[0]
        if (len(streams) != 1 or stream["codec_name"] != "png" or
                stream["width"] <= 0 or stream["height"] <= 0 or
                str(stream["nb_read_frames"]) != "1"):
            raise Refusal("artifact is not one decoded PNG frame")
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise Refusal("ffprobe returned incomplete artifact evidence") from exc
    return {"sha256": digest.hexdigest(), "bytes": size, "codec": "png",
            "width": stream["width"], "height": stream["height"]}


def paths(root, token):
    if not TOKEN.fullmatch(token):
        raise Refusal("token must be 1-128 letters, digits, underscores, periods or hyphens")
    key = hashlib.sha256(token.encode()).hexdigest()
    return root / f"{key}.json", root / f"{key}.png", root / f"{key}.pending.png"


def status(root, token):
    ledger, artifact, _ = paths(root, token)
    if not ledger.exists() and not ledger.is_symlink():
        return {"token": token, "state": "absent"}
    record = read_json(ledger)
    if record.get("token") != token:
        raise Refusal("ledger identity does not match requested operation")
    result = dict(record)
    if record.get("state") == "acquired":
        result["acquisition_outcome"] = "acquired"
        try:
            observed = artifact_info(artifact, binaries()["ffprobe"])
            if observed != record["artifact"]:
                raise Refusal("artifact no longer matches its receipt")
            result["artifact_status"] = "verified"
        except (OSError, KeyError, Refusal):
            # Preserve historical acquisition; current artifact usability is unresolved.
            result["state"] = "unknown"
            result["artifact_status"] = "invalid_or_unverifiable"
            result["reason"] = "retained artifact is missing, changed or unverifiable"
    if result.get("state") == "pending":
        result["state"] = "unknown"
        result["reason"] = "dispatch was recorded without a complete persisted receipt; inspect manually"
    result["claims"] = ["saved-frame acquisition", "retained artifact integrity"] if result["state"] == "acquired" else []
    return result


def capture(root, camera, token, timeout, allow_permission_prompt=False):
    ledger, artifact, staging = paths(root, token)
    diagnostic = ledger.with_suffix(".ffmpeg.stderr.log")
    backend = backend_name()
    request = {"camera": camera, "format": "png", "framerate_fps": 30, "timeout_seconds": timeout,
               "allow_permission_prompt": allow_permission_prompt}
    if backend == "v4l2":
        request["backend"] = backend
    if ledger.exists() or ledger.is_symlink():
        record = read_json(ledger)
        # Replays inspect the original operation, even after its device vanishes.
        # Retaining the original node identity never authorizes a new capture.
        if backend == "v4l2":
            request["device_identity"] = record["request"].get("device_identity")
        if record.get("request") != request:
            raise Refusal("token already belongs to different capture arguments")
        return status(root, token)
    for existing in root.glob("*.json"):
        record = read_json(existing)
        if record.get("state") != "acquired":
            raise Refusal("an unresolved operation blocks new captures; inspect this run directory")
        # Invalid retained artifacts also block conflicting captures.
        if status(root, record["token"])["state"] != "acquired":
            raise Refusal("an unverifiable artifact blocks new captures; inspect this run directory")
    if any(path.exists() or path.is_symlink() for path in (artifact, staging, diagnostic)):
        raise Refusal("an unreceipted artifact already exists; it will not be overwritten")
    inventory = doctor(root)
    device_identity = select_camera(camera, inventory, allow_permission_prompt)
    if backend == "v4l2":
        request["device_identity"] = device_identity
    programs = inventory["programs"]
    record = {"version": 1, "token": token, "request": request, "state": "pending",
              "intent_time_unix": time.time(), "artifact_name": artifact.name}
    persist(ledger, record)
    try:
        if backend == "v4l2" and linux_device_identity(camera) != device_identity:
            raise Refusal("selected Linux video node changed before capture")
        source = camera if backend == "v4l2" else f"{camera}:none"
        rc, _, stderr = run_process([programs["ffmpeg"], "-hide_banner", "-loglevel", "error",
                               "-nostdin", "-n", "-f", backend, "-framerate", "30",
                               "-i", source,
                               "-an", "-frames:v", "1", "-c:v", "png", str(staging)], timeout)
        private_diagnostic(diagnostic, stderr)
        record["diagnostic_name"] = diagnostic.name
        if rc:
            raise Refusal("FFmpeg capture failed; execution outcome remains unresolved")
        info = artifact_info(staging, programs["ffprobe"])
        # Hard-link publication cannot replace an existing capture.
        os.link(staging, artifact, follow_symlinks=False)
        staging.unlink()
        fd = os.open(artifact, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        record.update(state="acquired", acquisition_outcome="acquired", artifact=info,
                      receipt_time_unix=time.time())
        persist(ledger, record)
    # Every post-intent error must preserve uncertainty, including unexpected adapter errors.
    except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001
        if isinstance(exc, Refusal) and exc.private_stderr is not None:
            with contextlib.suppress(OSError):
                private_diagnostic(diagnostic, exc.private_stderr)
                record["diagnostic_name"] = diagnostic.name
        record["state"] = "unknown"
        record["acquisition_outcome"] = "unknown"
        record["reason"] = "capture or receipt did not complete; inspect artifacts before any further operation"
        with contextlib.suppress(OSError):
            persist(ledger, record)
        # A first response after intent must expose uncertainty, never imply no dispatch.
        return dict(record, claims=[])
    return status(root, token)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("doctor", "capture", "status"):
        child = sub.add_parser(command)
        child.add_argument("--run-dir", required=True)
        if command != "doctor":
            child.add_argument("--token", required=True)
        if command == "capture":
            child.add_argument("--camera", required=True)
            child.add_argument("--timeout", type=float, default=15)
            child.add_argument("--allow-permission-prompt", action="store_true",
                               help="allow an explicit capture to trigger macOS camera authorization")
    args = parser.parse_args(argv)
    try:
        if args.command == "capture" and not 1 <= args.timeout <= 60:
            raise Refusal("capture timeout must be between 1 and 60 seconds")
        root = private_directory(args.run_dir)
        with locked(root):
            if args.command == "doctor":
                result = doctor(root)
            elif args.command == "status":
                result = status(root, args.token)
            else:
                result = capture(root, args.camera, args.token, args.timeout, args.allow_permission_prompt)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("state", "acquired") in {"acquired", "absent"} else 2
    except (Refusal, OSError, KeyboardInterrupt) as exc:
        # Do not print raw process output, personal images, or native device IDs.
        reason = str(exc) if isinstance(exc, Refusal) else "operation interrupted or local resource unavailable"
        print(json.dumps({"state": "refused", "reason": reason}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
