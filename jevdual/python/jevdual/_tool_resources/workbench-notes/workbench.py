"""Project-bound reviewed notes and proposed checks; no task execution."""

import argparse
import contextlib
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
OUTPUT = (Path(os.environ["FOOTWORK_TOOL_OUTPUT_ROOT"]) / BASE.name
          if os.environ.get("FOOTWORK_TOOL_OUTPUT_ROOT") else BASE / "output")
SPEC = importlib.util.spec_from_file_location("desk_inbox", BASE.parent / "desk-inbox-experiment" / "inbox.py")
desk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(desk)
Refusal = desk.Refusal
MAX_JSON = 128 * 1024
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
KINDS = {"observation", "question", "experiment", "decision", "blocker"}
EXCLUDED = {"node_modules", "build", "dist", "__pycache__", ".venv", "venv", "target", "data", ".git", ".ssh"}


def private_directory(path, create=False):
    raw = Path(os.path.abspath(os.fspath(path)))
    if raw != OUTPUT and OUTPUT not in raw.parents:
        raise Refusal("workbench directory must remain inside this package's output directory")
    current = OUTPUT
    for part in (None, *raw.relative_to(OUTPUT).parts):
        if part is not None:
            current = current / part
        if create:
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                pass
        try:
            info = current.lstat()
        except OSError as exc:
            raise Refusal("workbench directory is unavailable") from exc
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Refusal("workbench directories must be owned, private and free of symlinks")
    return raw


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def decode_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refusal("JSON contains duplicate keys")
            result[key] = value
        return result

    try:
        return json.loads(data, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise Refusal("input is not valid UTF-8 JSON") from exc


def fields(value, required, label):
    if not isinstance(value, dict) or set(value) != set(required):
        raise Refusal(f"{label} has invalid fields")


def text(value, label, limit=4096):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise Refusal(f"{label} must be nonempty bounded text without NUL bytes")
    return value


def project_identity(value):
    fields(value, ("namespace", "project_id"), "project identity")
    if any(not isinstance(value[key], str) or not IDENTITY.fullmatch(value[key]) for key in value):
        raise Refusal("project identity must contain exact bounded namespace and ID")
    return value


def validate_record(record):
    fields(record, ("project", "kind", "title", "question", "interpretation", "proposed_next_check",
                    "expected_result", "references"), "caller record")
    project_identity(record["project"])
    if not isinstance(record["kind"], str) or record["kind"] not in KINDS:
        raise Refusal("record kind is unsupported")
    for key in ("title", "question", "interpretation", "proposed_next_check", "expected_result"):
        text(record[key], key, 160 if key == "title" else 4096)
    if "\n" in record["title"] or "\r" in record["title"]:
        raise Refusal("title must be one line")
    if not isinstance(record["references"], list) or len(record["references"]) > 32:
        raise Refusal("references must be a list with at most 32 entries")
    for ref in record["references"]:
        fields(ref, ("path", "line"), "reference")
        text(ref["path"], "reference path", 512)
        if type(ref["line"]) is not int or ref["line"] <= 0:
            raise Refusal("reference line must be a positive integer")
    return record


def selected_project(catalog, identity):
    fields(catalog, ("version", "projects"), "project catalog")
    if type(catalog["version"]) is not int or catalog["version"] != 1 or not isinstance(catalog["projects"], list):
        raise Refusal("catalog must be version 1 with a project list")
    if not 1 <= len(catalog["projects"]) <= 100:
        raise Refusal("catalog must contain 1-100 projects")
    seen = set()
    selected = None
    for project in catalog["projects"]:
        fields(project, ("namespace", "project_id", "label", "root"), "catalog project")
        key = project_identity({k: project[k] for k in ("namespace", "project_id")})
        pair = (key["namespace"], key["project_id"])
        if pair in seen:
            raise Refusal("catalog contains a duplicate namespaced project identity")
        seen.add(pair)
        text(project["label"], "project label", 160)
        text(project["root"], "project root", 2048)
        if not Path(project["root"]).is_absolute():
            raise Refusal("project root must be absolute")
        if key == identity:
            selected = dict(project)
    if selected is None:
        raise Refusal("exact namespaced project ID is absent from catalog")
    root = Path(selected["root"])
    try:
        if not root.is_dir() or root.is_symlink() or str(root.resolve(strict=True)) != selected["root"]:
            raise Refusal("selected checkout root must be an existing canonical directory")
    except OSError as exc:
        raise Refusal("selected checkout root is unavailable") from exc
    return selected


def reference_info(root, ref):
    relative = Path(ref["path"])
    if relative.is_absolute() or any(part in {"..", "."} for part in ref["path"].split("/")):
        raise Refusal("reference must be a contained repository-relative path")
    if any(part.lower() in EXCLUDED or part.lower().startswith(".env") or part.lower().endswith((".pem", ".key", ".p12"))
           for part in relative.parts):
        raise Refusal("reference selects a secret or excluded path")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise Refusal("reference may not traverse symlinks")
    try:
        if root not in current.resolve(strict=True).parents:
            raise Refusal("reference escapes selected checkout")
    except OSError as exc:
        raise Refusal("reference is unavailable") from exc
    data = desk.read_regular(current, 1024 * 1024)
    if ref["line"] > len(data.splitlines()):
        raise Refusal("reference line lies outside the retained file")
    return {**ref, "sha256": desk.digest(data), "bytes": len(data)}


def git_head(root):
    git = shutil.which("git")
    if not git:
        return None
    try:
        rc, stdout, _ = desk.camera.run_process([git, "--no-optional-locks", "-C", str(root),
                                                "rev-parse", "--verify", "HEAD"], 5)
        head = stdout.strip()
        return head if rc == 0 and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head) else None
    except (Refusal, OSError):
        return None


def desk_source(path):
    try:
        if not Path(path).is_dir():
            raise Refusal("desk source directory is unavailable")
        root = desk.private_directory(path)
        with desk.camera.locked(root):
            source = desk.status(root)
            if source.get("state") != "saved":
                raise Refusal("desk source is not currently verified saved text")
            manifest = desk.read_regular(root / "manifest.json", MAX_JSON)
            note = desk.read_regular(root / "inbox" / "note.txt", desk.MAX_NOTE_BYTES)
            if desk.digest(note) != source["approval"]["sha256"]:
                raise Refusal("source note does not match its approval")
            source_request = source["request"]
            if source_request["source_kind"] not in {"native_camera_frame", "synthetic_fixture"}:
                raise Refusal("source kind is not supported")
            evidence = {"desk_run": str(root), "desk_manifest_sha256": desk.digest(manifest),
                        "note_sha256": desk.digest(note), "source_kind": source_request["source_kind"],
                        "raw_frame": source_request, "review_kind": source["review_kind"],
                        "approved_sha256": source["approval"]["sha256"]}
            desk.note_text(note)
            return evidence, note
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise Refusal("desk source has malformed provenance") from exc


def context_snapshot(project, refs):
    root = Path(project["root"])
    return {"git_head": git_head(root), "references": [reference_info(root, ref) for ref in refs]}


def context_status(project, snapshot):
    root = Path(project["root"])
    head = git_head(root)
    previous = snapshot["git_head"]
    state = "unavailable" if head is None or previous is None else "unchanged" if head == previous else "changed"
    references = []
    for ref in snapshot["references"]:
        try:
            current = reference_info(root, {k: ref[k] for k in ("path", "line")})
            ref_state = "unchanged" if current["sha256"] == ref["sha256"] else "changed"
        except (Refusal, OSError):
            current = {"path": ref["path"], "line": ref["line"]}
            ref_state = "unavailable"
        references.append({**current, "state": ref_state, "recorded_sha256": ref["sha256"]})
    combined = [state, *(ref["state"] for ref in references)]
    return {"state": "changed" if "changed" in combined else "unavailable" if "unavailable" in combined else "unchanged",
            "head_state": state, "current_git_head": head, "recorded_git_head": previous, "references": references}


def markdown(packet):
    esc = html.escape
    project, caller, check, evidence = packet["project"], packet["caller_interpretation"], packet["proposed_check"], packet["source_evidence"]
    output = ["# Workbench record", f"<h2>{esc(packet['title'])}</h2>",
              f"Project: <code>{esc(project['namespace'])}:{esc(project['project_id'])}</code>",
              f"Label: <code>{esc(project['label'])}</code>", f"Checkout: <code>{esc(project['root'])}</code>",
              f"Kind: <code>{esc(packet['kind'])}</code>", "## Reviewed source note", f"<pre>{esc(evidence['note_text'])}</pre>",
              f"Source kind: <code>{esc(evidence['source_kind'])}</code>",
              f"Note SHA256: <code>{esc(evidence['note_sha256'])}</code>",
              f"Raw frame: <code>{esc(evidence['raw_frame']['source_path'])}</code>",
              f"Raw frame SHA256: <code>{esc(evidence['raw_frame']['source_sha256'])}</code>",
              "## Caller interpretation", "Question:", f"<pre>{esc(caller['question'])}</pre>",
              "Interpretation:", f"<pre>{esc(caller['interpretation'])}</pre>",
              "## Proposed next check — not run", f"<pre>{esc(check['description'])}</pre>",
              "Acceptance criterion:", f"<pre>{esc(check['expected_result'])}</pre>",
              "## Repository context", f"Recorded HEAD: <code>{esc(packet['context_snapshot']['git_head'] or 'unavailable')}</code>"]
    for ref in packet["context_snapshot"]["references"]:
        output.append(f"Reference: <code>{esc(ref['path'])}:{ref['line']}</code>, SHA256 <code>{ref['sha256']}</code>")
    output.append("File equality verifies this retained packet. It does not verify interpretation, run the check, or establish current repository context.")
    return ("\n\n".join(output) + "\n").encode()


def check_packet(root, suffix, sha):
    rc, stdout, _ = desk.camera.run_process([str(desk.FOOTWORK), "check-artifact", str(root / f"record.{suffix}"),
                                            "--expected-file", str(root / f"expected-record.{suffix}"),
                                            "--expected-sha256", sha], 20)
    try:
        checked = decode_json(stdout.encode())
        if not isinstance(checked, dict) or not isinstance(checked.get("ok"), bool) or rc not in (0, 6) or checked["ok"] != (rc == 0):
            raise Refusal("Footwork artifact check returned an invalid result")
        return checked
    except (UnicodeError, ValueError, TypeError) as exc:
        raise Refusal("Footwork artifact check returned invalid JSON") from exc


def validate_manifest(record):
    if not isinstance(record, dict) or record.get("version") != 1 or not isinstance(record.get("state"), str) or record["state"] not in {"linking", "recorded", "unknown"}:
        raise Refusal("workbench manifest state is invalid")
    request = record.get("request")
    fields(request, ("project", "record_path", "record_sha256", "source"), "retained request")
    project = request["project"]
    fields(project, ("namespace", "project_id", "label", "root"), "retained project")
    project_identity({k: project[k] for k in ("namespace", "project_id")})
    text(project["root"], "retained root", 2048)
    if not Path(project["root"]).is_absolute() or os.path.abspath(project["root"]) != project["root"]:
        raise Refusal("retained checkout root is not canonical absolute syntax")
    text(project["label"], "retained label", 160)
    text(record.get("title"), "retained title", 160)
    if not isinstance(record.get("kind"), str) or record["kind"] not in KINDS:
        raise Refusal("retained kind is invalid")
    text(request["record_path"], "retained record path", 2048)
    if not Path(request["record_path"]).is_absolute():
        raise Refusal("retained caller record path must be absolute")
    source = request["source"]
    fields(source, ("desk_run", "desk_manifest_sha256", "note_sha256", "source_kind", "raw_frame",
                    "review_kind", "approved_sha256"), "retained source")
    text(source["desk_run"], "retained desk run", 2048)
    if not isinstance(source["source_kind"], str) or source["source_kind"] not in {"native_camera_frame", "synthetic_fixture"}:
        raise Refusal("retained source kind is invalid")
    if not isinstance(source["review_kind"], str) or source["review_kind"] not in {"original_ocr", "corrected_text"}:
        raise Refusal("retained review kind is invalid")
    raw = source["raw_frame"]
    raw_keys = ["source_kind", "source_path", "source_sha256", "mirror_input"]
    if source["source_kind"] == "native_camera_frame":
        raw_keys.extend(("capture_run", "capture_token"))
    fields(raw, raw_keys, "retained frame")
    if raw["source_kind"] != source["source_kind"] or type(raw["mirror_input"]) is not bool:
        raise Refusal("retained frame provenance is invalid")
    text(raw["source_path"], "retained frame path", 2048)
    if source["source_kind"] == "native_camera_frame":
        text(raw["capture_run"], "retained capture run", 2048)
        text(raw["capture_token"], "retained capture token", 128)
    for sha in (request["record_sha256"], source["desk_manifest_sha256"], source["note_sha256"],
                source["approved_sha256"], raw["source_sha256"]):
        if not isinstance(sha, str) or not desk.DIGEST.fullmatch(sha):
            raise Refusal("retained source digest is invalid")
    snapshot = record.get("context_snapshot")
    fields(snapshot, ("git_head", "references"), "retained context")
    if snapshot["git_head"] is not None and (not isinstance(snapshot["git_head"], str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", snapshot["git_head"])):
        raise Refusal("retained revision is invalid")
    if not isinstance(snapshot["references"], list) or len(snapshot["references"]) > 32:
        raise Refusal("retained references are invalid")
    for ref in snapshot["references"]:
        fields(ref, ("path", "line", "sha256", "bytes"), "retained reference")
        text(ref["path"], "retained reference path", 512)
        if type(ref["line"]) is not int or ref["line"] <= 0 or not isinstance(ref["sha256"], str) or not desk.DIGEST.fullmatch(ref["sha256"]):
            raise Refusal("retained reference identity is invalid")
        if type(ref["bytes"]) is not int or not 0 <= ref["bytes"] <= 1024 * 1024:
            raise Refusal("retained reference size is invalid")
    if record["state"] == "recorded":
        if not isinstance(record.get("packet_sha256"), dict) or set(record["packet_sha256"]) != {"json", "md"}:
            raise Refusal("packet digest fields are invalid")
        if any(not isinstance(sha, str) or not desk.DIGEST.fullmatch(sha) for sha in record["packet_sha256"].values()):
            raise Refusal("packet digest is invalid")
    return record


def load(root):
    return validate_manifest(decode_json(desk.read_regular(root / "manifest.json", MAX_JSON)))


def status(root):
    if not (root / "manifest.json").exists() and not (root / "manifest.json").is_symlink():
        return {"state": "absent", "claims": []}
    record = load(root)
    result = {k: record[k] for k in ("state", "request", "title", "kind", "context_snapshot")}
    result.update(claims=[], run_dir=str(root), historical_recorded_outcome=record.get("historical_recorded_outcome", "unknown"),
                  context=context_status(record["request"]["project"], record["context_snapshot"]))
    if record["state"] in {"linking", "unknown"}:
        return {**result, "state": "unknown", "reason": "recording intent is unresolved; inspect without replay"}
    try:
        source, _ = desk_source(record["request"]["source"]["desk_run"])
        if source != record["request"]["source"]:
            raise Refusal("reviewed desk source provenance changed")
        if desk.digest(desk.read_regular(root / "source-note.txt", desk.MAX_NOTE_BYTES)) != source["note_sha256"]:
            raise Refusal("retained source note changed")
        if desk.digest(desk.read_regular(root / "caller-record.json", MAX_JSON)) != record["request"]["record_sha256"]:
            raise Refusal("retained caller metadata changed")
        if desk.digest(desk.read_regular(Path(record["request"]["record_path"]), MAX_JSON)) != record["request"]["record_sha256"]:
            raise Refusal("original caller metadata changed")
        checks = {suffix: check_packet(root, suffix, sha) for suffix, sha in record["packet_sha256"].items()}
        result["artifact_checks"] = checks
        if not all(check["ok"] for check in checks.values()):
            raise Refusal("a retained packet is missing, changed or unverifiable")
        result["claims"] = ["current_packet_bytes_equal_bound_expected_sources"]
        result["packet_paths"] = {suffix: str(root / f"record.{suffix}") for suffix in ("json", "md")}
    except (Refusal, OSError):
        result.update(state="unknown", claims=[], reason="retained packet or source is currently unverifiable")
    return result


def link(root, desk_run, catalog_path, record_path, record_sha256):
    if not desk.DIGEST.fullmatch(record_sha256):
        raise Refusal("record approval must be an exact lowercase SHA256 digest")
    record_bytes = desk.read_regular(Path(record_path), MAX_JSON)
    if desk.digest(record_bytes) != record_sha256:
        raise Refusal("caller record no longer matches its bound digest")
    caller = validate_record(decode_json(record_bytes))
    catalog = decode_json(desk.read_regular(Path(catalog_path), MAX_JSON))
    project = selected_project(catalog, caller["project"])
    source, note = desk_source(desk_run)
    request = {"project": project, "record_path": str(Path(os.path.abspath(record_path))),
               "record_sha256": record_sha256, "source": source}
    if (root / "manifest.json").exists() or (root / "manifest.json").is_symlink():
        retained = load(root)
        if retained["request"] != request:
            raise Refusal("run already belongs to different project, source or caller metadata")
        return status(root)
    context = context_snapshot(project, caller["references"])
    manifest = {"version": 1, "state": "linking", "request": request, "title": caller["title"],
                "kind": caller["kind"], "context_snapshot": context, "intent_time_unix": time.time()}
    packet = {"version": 1, "project": project, "title": caller["title"], "kind": caller["kind"],
              "source_evidence": {**source, "note_text": note.decode("utf-8")}, "metadata_authorship": "caller_supplied",
              "caller_interpretation": {k: caller[k] for k in ("question", "interpretation")},
              "proposed_check": {"description": caller["proposed_next_check"], "expected_result": caller["expected_result"], "outcome": "not_run"},
              "context_snapshot": context, "recorded_at_unix": manifest["intent_time_unix"]}
    packets = {"json": json_bytes(packet), "md": markdown(packet)}
    desk.camera.persist(root / "manifest.json", manifest)
    try:
        desk.create_file(root / "source-note.txt", note)
        desk.create_file(root / "caller-record.json", record_bytes)
        for suffix, data in packets.items():
            if len(data) > 1024 * 1024:
                raise Refusal("packet exceeds Footwork artifact limit")
            desk.create_file(root / f"expected-record.{suffix}", data)
            desk.create_file(root / f"record.{suffix}", data)
        hashes = {suffix: desk.digest(data) for suffix, data in packets.items()}
        checks = {suffix: check_packet(root, suffix, sha) for suffix, sha in hashes.items()}
        if not all(check["ok"] for check in checks.values()):
            raise Refusal("packet verification failed")
        manifest.update(state="recorded", historical_recorded_outcome="recorded", packet_sha256=hashes,
                        recorded_time_unix=time.time(), recorded_artifact_checks=checks)
        desk.camera.persist(root / "manifest.json", manifest)
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - unresolved publication never replays
        manifest.update(state="unknown", historical_recorded_outcome="unknown")
        with contextlib.suppress(OSError):
            desk.camera.persist(root / "manifest.json", manifest)
    return status(root)


def list_records(scope, namespace, project_id):
    project_identity({"namespace": namespace, "project_id": project_id})
    records, errors = [], []
    visited = 0
    for directory, names, files in os.walk(scope, followlinks=False):
        visited += 1
        if visited > 1000:
            raise Refusal("listing exceeds the 1000-directory limit")
        root = private_directory(directory)
        for name in names:
            if (root / name).is_symlink():
                errors.append({"run_dir": str(root / name), "state": "symlink_excluded"})
        names[:] = sorted(name for name in names if not (root / name).is_symlink())
        if "manifest.json" not in files:
            continue
        try:
            with desk.camera.locked(root):
                retained = load(root)
                project = retained["request"]["project"]
                if (project["namespace"], project["project_id"]) != (namespace, project_id):
                    continue
                result = status(root)
            records.append({"run_dir": str(root), "title": result["title"], "kind": result["kind"],
                            "state": result["state"], "context": result["context"]["state"],
                            "project": {"namespace": namespace, "project_id": project_id}})
        except (Refusal, OSError):
            errors.append({"run_dir": str(root), "state": "unreadable_or_locked"})
    return {"records": records, "errors": errors, "complete": not errors,
            "project": {"namespace": namespace, "project_id": project_id}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("link", "status", "list"):
        child = sub.add_parser(command)
        if command == "list":
            child.add_argument("--output-root", required=True)
            child.add_argument("--project-namespace", required=True)
            child.add_argument("--project-id", required=True)
        else:
            child.add_argument("--run-dir", required=True)
        if command == "link":
            child.add_argument("--desk-run", required=True)
            child.add_argument("--catalog", required=True)
            child.add_argument("--record-file", required=True)
            child.add_argument("--record-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            result = list_records(private_directory(args.output_root), args.project_namespace, args.project_id)
            code = 0 if result["complete"] else 2
        else:
            root = private_directory(args.run_dir, create=args.command == "link")
            if root == OUTPUT:
                raise Refusal("one operation must use its own output subdirectory")
            with desk.camera.locked(root):
                result = link(root, args.desk_run, args.catalog, args.record_file, args.record_sha256) if args.command == "link" else status(root)
            code = 0 if result["state"] in {"recorded", "absent"} else 2
        print(json.dumps(result, indent=2, sort_keys=True))
        return code
    except (Refusal, OSError, KeyError, TypeError, ValueError, AttributeError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else "input or retained evidence is malformed or unavailable"
        print(json.dumps({"state": "refused", "reason": reason, "claims": []}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
