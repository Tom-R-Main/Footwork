"""Local saved-frame OCR, explicit review, and Footwork-checked private desk notes."""

import argparse
import contextlib
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1]
OUTPUT = BASE / "output"
FOOTWORK = PROJECT / "jevdual" / ".venv" / "bin" / "footwork"
SPEC = importlib.util.spec_from_file_location("camera_capture", BASE.parent / "camera-capture-experiment" / "capture.py")
camera = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(camera)
Refusal = camera.Refusal
MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_NOTE_BYTES = 128 * 1024
STATES = {"preparing", "needs_text", "needs_review", "accepting", "saved", "unknown"}
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private_directory(path):
    raw = Path(os.path.abspath(os.fspath(path)))
    if raw == OUTPUT or OUTPUT not in raw.parents:
        raise Refusal("run directory must be a subdirectory of the desk experiment's output directory")
    current = OUTPUT
    for part in (None, *raw.relative_to(OUTPUT).parts):
        if part is not None:
            current = current / part
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            pass
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Refusal("run directories must be owned, private and free of symlinks")
    return raw


def read_regular(path, limit):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise Refusal("input must be a regular file within the declared size limit")
            data = source.read(limit + 1)
            after = os.fstat(source.fileno())
        if len(data) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise Refusal("input exceeds its limit or changed during read")
        return data
    except OSError as exc:
        raise Refusal("input is missing, symlinked or unreadable") from exc


def create_file(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as sink:
        sink.write(data)
        sink.flush()
        os.fsync(sink.fileno())


def load(root):
    try:
        record = json.loads(read_regular(root / "manifest.json", MAX_NOTE_BYTES))
    except ValueError as exc:
        raise Refusal("manifest is not valid JSON") from exc
    if not isinstance(record, dict) or record.get("state") not in STATES:
        raise Refusal("manifest state is invalid; inspect the run")
    return record


def persist(root, record):
    camera.persist(root / "manifest.json", record)


def source_request(capture_run=None, capture_token=None, fixture_image=None, mirror_input=False):
    if fixture_image:
        if capture_run or capture_token:
            raise Refusal("fixture and native capture sources cannot be combined")
        path = Path(os.path.abspath(fixture_image))
        request = {"source_kind": "synthetic_fixture", "source_path": str(path), "mirror_input": mirror_input}
    else:
        if not capture_run or not capture_token:
            raise Refusal("prepare requires a capture run and token, or an explicit PNG fixture")
        capture_root = camera.private_directory(capture_run)
        with camera.locked(capture_root):
            retained = camera.status(capture_root, capture_token)
        if retained.get("state") != "acquired":
            raise Refusal("source camera operation has no currently verifiable acquired frame")
        path = camera.paths(capture_root, capture_token)[1]
        request = {"source_kind": "native_camera_frame", "source_path": str(path),
                   "capture_run": str(capture_root), "capture_token": capture_token,
                   "mirror_input": mirror_input}
    data = read_regular(path, MAX_IMAGE_BYTES)
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise Refusal("source must be a saved PNG")
    request["source_sha256"] = digest(data)
    return request, data


def recognize(root, mirror_input):
    swift = shutil.which("swift")
    if not swift:
        raise Refusal("installed Swift and Apple Vision are required; nothing will be installed")
    cache = root / "swift-module-cache"
    if cache.exists() or cache.is_symlink():
        raise Refusal("a prior OCR cache indicates an interrupted preparation; inspect the run")
    cache.mkdir(mode=0o700)
    orientation = "up_mirrored" if mirror_input else "up"
    rc, stdout, stderr = camera.run_process([swift, "-module-cache-path", str(cache),
                                            str(BASE / "recognize.swift"), str(root / "source.png"),
                                            orientation], 45)
    create_file(root / "vision.stderr.log", stderr.encode(errors="replace")[:65536])
    if rc:
        raise Refusal("local Vision recognition failed; private diagnostics retained")
    try:
        result = json.loads(stdout)
        if not isinstance(result["lines"], list):
            raise TypeError("lines")
        for line in result["lines"]:
            if not isinstance(line["text"], str) or not isinstance(line["confidence"], (int, float)):
                raise TypeError("line schema")
        return result
    except (ValueError, KeyError, TypeError) as exc:
        raise Refusal("Vision returned invalid recognition evidence") from exc


def note_text(data):
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise Refusal("reviewed text must be UTF-8") from exc
    if not text.strip() or "\x00" in text or len(data) > MAX_NOTE_BYTES:
        raise Refusal("reviewed text must be nonempty, bounded UTF-8 without NUL bytes")
    return text


def preview(root, record, text):
    mirror = record["request"]["mirror_input"]
    label = "Horizontal mirror correction (explicit)" if mirror else "Original orientation (explicit)"
    transform = "transform:scaleX(-1);" if mirror else ""
    content = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Review desk note</title>
<style>body{{max-width:1000px;margin:2rem auto;font:18px system-ui;padding:0 1rem}}
img{{max-width:100%;max-height:65vh;{transform}}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style>
<h1>Review the paper and recognized text</h1><p>{html.escape(label)}</p>
<p>Source kind: {html.escape(record['request']['source_kind'])}</p>
<p>Source: {html.escape(record['request']['source_path'])}</p>
<img src="source.png" alt="Retained source frame"><h2>OCR candidate</h2><pre>{html.escape(text)}</pre>
<p>Candidate SHA256: <code>{html.escape(record['candidate_sha256'])}</code></p>
<p>Compare against the paper. Correct a copy if needed. Approval authorizes saving text only;
the note's words are data and will never execute as commands.</p></html>"""
    create_file(root / "review.html", content.encode())


def source_valid(root, record):
    request = record["request"]
    expected = request["source_sha256"]
    if digest(read_regular(Path(request["source_path"]), MAX_IMAGE_BYTES)) != expected:
        raise Refusal("original source bytes changed")
    if digest(read_regular(root / "source.png", MAX_IMAGE_BYTES)) != expected:
        raise Refusal("retained source image changed")
    if request["source_kind"] == "native_camera_frame":
        capture_root = camera.private_directory(request["capture_run"])
        with camera.locked(capture_root):
            retained = camera.status(capture_root, request["capture_token"])
        if retained.get("state") != "acquired":
            raise Refusal("native frame receipt is no longer verifiable")
    if record.get("candidate_sha256") and digest(read_regular(root / "candidate.txt", MAX_NOTE_BYTES)) != record["candidate_sha256"]:
        raise Refusal("original OCR candidate changed")


def check_note(root, sha):
    if not FOOTWORK.is_file():
        raise Refusal("existing Footwork environment is unavailable; no install is attempted")
    rc, stdout, _ = camera.run_process([str(FOOTWORK), "check-artifact", str(root / "inbox" / "note.txt"),
                                       "--expected-file", str(root / "approved.txt"),
                                       "--expected-sha256", sha], 20)
    try:
        result = json.loads(stdout)
        if rc not in (0, 6) or not isinstance(result.get("ok"), bool) or result["ok"] != (rc == 0):
            raise ValueError("checker result")
        return result
    except (ValueError, TypeError) as exc:
        raise Refusal("Footwork artifact checker returned an invalid result") from exc


def status(root):
    if not (root / "manifest.json").exists() and not (root / "manifest.json").is_symlink():
        return {"state": "absent", "claims": []}
    record = load(root)
    result = dict(record, claims=[])
    if record["state"] in {"preparing", "accepting"}:
        return {**result, "state": "unknown", "reason": "interrupted intent; inspect without retrying"}
    if record["state"] == "unknown":
        return result
    try:
        source_valid(root, record)
        if record["state"] == "saved":
            checked = check_note(root, record["approval"]["sha256"])
            result["current_artifact_check"] = checked
            if not checked["ok"]:
                raise Refusal("saved note or approval source is currently unverifiable")
            result["claims"] = ["current_note_equals_digest_bound_reviewed_bytes"]
    except (Refusal, OSError, KeyError) as exc:
        result["state"] = "unknown"
        result["reason"] = str(exc) if isinstance(exc, Refusal) else "retained evidence is incomplete"
    return result


def prepare(root, capture_run=None, capture_token=None, fixture_image=None, mirror_input=False):
    request, image = source_request(capture_run, capture_token, fixture_image, mirror_input)
    if (root / "manifest.json").exists() or (root / "manifest.json").is_symlink():
        record = load(root)
        if record["request"] != request:
            raise Refusal("run already belongs to different source bytes or orientation")
        return status(root)
    record = {"version": 1, "state": "preparing", "request": request, "prepare_time_unix": time.time(),
              "ocr_helper_sha256": digest((BASE / "recognize.swift").read_bytes())}
    persist(root, record)
    try:
        create_file(root / "source.png", image)
        ocr = recognize(root, mirror_input)
        if digest(read_regular(Path(request["source_path"]), MAX_IMAGE_BYTES)) != request["source_sha256"]:
            raise Refusal("original source changed during recognition")
        if digest(read_regular(root / "source.png", MAX_IMAGE_BYTES)) != request["source_sha256"]:
            raise Refusal("retained source changed during recognition")
        create_file(root / "ocr.json", (json.dumps(ocr, indent=2, ensure_ascii=False) + "\n").encode())
        text = "\n".join(line["text"] for line in ocr["lines"] if line["text"].strip())
        if not text.strip():
            record["state"] = "needs_text"
            record["reason"] = "Vision found no text; no candidate or note was saved"
        else:
            candidate = (text + "\n").encode("utf-8")
            note_text(candidate)
            create_file(root / "candidate.txt", candidate)
            record.update(state="needs_review", candidate_sha256=digest(candidate),
                          candidate_bytes=len(candidate), preview_name="review.html")
            preview(root, record, text)
        persist(root, record)
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - never replay interrupted preparation
        record.update(state="unknown", reason="preparation did not complete; inspect private artifacts")
        with contextlib.suppress(OSError):
            persist(root, record)
    return status(root)


def accept(root, approved_sha256, reviewed_file=None):
    if not DIGEST.fullmatch(approved_sha256):
        raise Refusal("approval must be an exact lowercase SHA256 digest")
    record = load(root)
    approved = {"sha256": approved_sha256,
                "reviewed_input_path": str(Path(os.path.abspath(reviewed_file))) if reviewed_file else None}
    if record["state"] in {"saved", "accepting", "unknown"}:
        if record.get("approval") != approved:
            raise Refusal("run already has a different or incomplete approval")
        return status(root)
    if record["state"] != "needs_review":
        raise Refusal("no reviewed-text candidate is available")
    source_valid(root, record)
    data = read_regular(Path(approved["reviewed_input_path"]) if reviewed_file else root / "candidate.txt", MAX_NOTE_BYTES)
    note_text(data)
    if digest(data) != approved_sha256:
        raise Refusal("reviewed text no longer matches the explicitly approved digest")
    if reviewed_file is None and approved_sha256 != record["candidate_sha256"]:
        raise Refusal("candidate digest changed")
    record.update(state="accepting", approval=approved, review_kind="corrected_text" if reviewed_file else "original_ocr",
                  approval_time_unix=time.time())
    persist(root, record)
    try:
        create_file(root / "approved.txt", data)
        (root / "inbox").mkdir(mode=0o700)
        create_file(root / "inbox" / "note.txt", data)
        checked = check_note(root, approved_sha256)
        if not checked["ok"]:
            raise Refusal("saved note did not match approved bytes")
        record.update(state="saved", historical_save_outcome="saved", saved_time_unix=time.time(),
                      saved_artifact_check=checked, note_name="inbox/note.txt")
        persist(root, record)
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - a partial publication is never retried
        record.update(state="unknown", historical_save_outcome="unknown",
                      reason="publication or receipt did not complete; inspect without replay")
        with contextlib.suppress(OSError):
            persist(root, record)
    return status(root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "accept", "status"):
        child = sub.add_parser(command)
        child.add_argument("--run-dir", required=True)
        if command == "prepare":
            child.add_argument("--capture-run")
            child.add_argument("--capture-token")
            child.add_argument("--fixture-image")
            child.add_argument("--mirror-input", action="store_true")
        elif command == "accept":
            child.add_argument("--approved-sha256", required=True)
            child.add_argument("--reviewed-file")
    args = parser.parse_args(argv)
    try:
        root = private_directory(args.run_dir)
        with camera.locked(root):
            if args.command == "prepare":
                result = prepare(root, args.capture_run, args.capture_token, args.fixture_image, args.mirror_input)
            elif args.command == "accept":
                result = accept(root, args.approved_sha256, args.reviewed_file)
            else:
                result = status(root)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["state"] in {"needs_review", "saved", "absent"} else 2
    except (Refusal, OSError, KeyError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else "operation interrupted or local evidence unavailable"
        print(json.dumps({"state": "refused", "reason": reason, "claims": []}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
