"""Build or verify a deterministic, reviewed local capability release candidate.

Offline only: preserve the qualified wheel/helpers, read release documentation
and evidence from an immutable commit, and never install or execute the product.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from build_onboarding_packet import HELPERS
from build_onboarding_packet import verify_committed_wheel as verify_packet_wheel

PROJECT = Path(__file__).resolve().parents[2]
QUALIFIED_PACKET_SHA = "205577ee0848e9e68c8a15a9f25e1d308e820a054be449f631274ba7a9c7151d"
QUALIFIED_PRODUCT_COMMIT = "445a348ff31243c2f3d90baae9ce209d89bd7eac"
ARCHIVE_NAME = "footwork-capability-0.0.1-macos-arm64-candidate.zip"
DOCS = {
    "footwork/README.md": "jevdual/docs/release-candidate.md",
    "footwork/installation.md": "jevdual/docs/capability-packaging.md",
    "footwork/agent-host.md": "jevdual/docs/installed-agent-host.md",
}
DOCUMENT_LINKS = {
    "../results/clean-installation-20261010/report.md": "evidence/fresh-install/report.md",
    "../results/u3-packet-v4-permission-20261012-v3/report.md": "evidence/permission_journey-report.md",
    "../results/installed-agent-release-20261012-v2/report.md": "evidence/installed_agent-report.md",
    "installed-agent-host.md": "agent-host.md",
}
CONSUMER_DOCUMENT_LINKS = {
    "footwork/README.md": {
        "capability-packaging.md": "installation.md",
        "installed-agent-host.md": "agent-host.md",
    },
    "footwork/agent-host.md": {"capability-packaging.md": "installation.md"},
    "footwork/installation.md": DOCUMENT_LINKS,
}
REPORTS = {
    "footwork/evidence/fresh-install/report.md": "jevdual/results/clean-installation-20261010/report.md",
    "footwork/evidence/permission_journey-report.md": "jevdual/results/u3-packet-v4-permission-20261012-v3/report.md",
    "footwork/evidence/installed_agent-report.md": "jevdual/results/installed-agent-release-20261012-v2/report.md",
}
LEGACY_INSTALL_ATTACHMENTS = (
    "summary.json",
    "py312-installation.json",
    "py314-installation.json",
    "py312-native.json",
    "py314-native.json",
    "unknown-report-negative.json",
    "missing-prerequisites.json",
    "retained-failures.json",
    "cwd-shadow-baseline.json",
    "cleanup.json",
)
EVIDENCE = {
    "permission_journey": "jevdual/results/u3-packet-v4-permission-20261012-v3/summary.json",
    "installed_agent": "jevdual/results/installed-agent-release-20261012-v2/summary.json",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def sanitized_legacy_json(data: bytes) -> bytes:
    """Derive shareable receipts from their content, never from host environment.

    URLs remain verbatim. Recognized Footwork project/worktree roots collapse to
    WORKTREE; other personal Unix home roots collapse to HOST_HOME. These aliases
    intentionally discard identity and are diagnostic copies, not raw evidence.
    """
    segment = r"[^/\s\\\"'<>]+"
    home = r"/(?:Users|home)/" + segment
    worktree = home + r"/(?:\.codex/worktrees/" + segment + r"/footwork|projects/footwork)"
    boundary = r"(?=/|$|[\s\\\"'<>])"
    pattern = re.compile(
        r"(?P<url>[A-Za-z][A-Za-z0-9+.-]*://[^\s\"'<>]+)"
        + r"|(?<![\w/])(?P<worktree>"
        + worktree
        + boundary
        + r")"
        + r"|(?<![\w/])(?P<home>"
        + home
        + r")"
    )

    def text(value: str) -> str:
        return pattern.sub(
            lambda match: (
                match.group(0)
                if match.group("url")
                else "<WORKTREE>"
                if match.group("worktree")
                else "<HOST_HOME>"
            ),
            value,
        )

    def clean(value):
        if isinstance(value, str):
            return text(value)
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                key = text(key)
                if key in result:
                    raise ValueError("Sanitized legacy JSON keys collide")
                result[key] = clean(item)
            return result
        return value

    return encoded(clean(json.loads(data)))


def commit_identity(commit: str | None) -> str:
    commit = commit or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full immutable source commit is required")
    return commit


def committed_bytes(commit: str, relative: str) -> bytes:
    entries = subprocess.check_output(
        ["git", "ls-tree", "-z", commit, "--", relative], cwd=PROJECT, stderr=subprocess.PIPE
    ).split(b"\0")
    entries = [entry for entry in entries if entry]
    if len(entries) != 1:
        raise ValueError("Committed source file is absent: " + relative)
    metadata, name = entries[0].split(b"\t", 1)
    mode, kind, _ = metadata.split()
    if mode not in (b"100644", b"100755") or kind != b"blob" or name.decode() != relative:
        raise ValueError("Committed source must be a regular file")
    return subprocess.check_output(
        ["git", "show", commit + ":" + relative], cwd=PROJECT, stderr=subprocess.PIPE
    )


def read_archive(path: Path) -> dict[str, bytes]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Archive must be a regular nonsymlink file")
    files = {}
    total = 0
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            name = entry.filename
            parts = PurePosixPath(name)
            mode = entry.external_attr >> 16
            if (
                name in files
                or parts.is_absolute()
                or ".." in parts.parts
                or parts.as_posix() != name
                or len(parts.parts) < 2
                or parts.parts[0] != "footwork"
                or "\\" in name
                or entry.is_dir()
                or stat.S_ISLNK(mode)
                or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
            ):
                raise ValueError("Unsafe or duplicate archive member")
            total += entry.file_size
            if entry.file_size > 8 * 1024 * 1024 or total > 16 * 1024 * 1024:
                raise ValueError("Archive exceeds bounded candidate size")
            files[name] = archive.read(entry)
    return files


def qualification_packet(path: Path) -> tuple[dict[str, bytes], dict]:
    files = read_archive(path)
    if sha(path.read_bytes()) != QUALIFIED_PACKET_SHA:
        raise ValueError("Qualification packet differs from the immutable reviewed packet")
    manifest = json.loads(files.get("footwork/MANIFEST.json", b"null"))
    if not isinstance(manifest, dict) or manifest.get("source_commit") != QUALIFIED_PRODUCT_COMMIT:
        raise ValueError("Qualification packet product source differs")
    wheels = [name for name in files if name.startswith("footwork/artifacts/") and name.endswith(".whl")]
    if len(wheels) != 1:
        raise ValueError("Qualification packet must contain exactly one wheel")
    expected = {
        "footwork/MANIFEST.json",
        "footwork/LICENSE",
        "footwork/README.md",
        "footwork/vm-plan.md",
        "footwork/installation.md",
        wheels[0],
        *("footwork/jevdual/scripts/" + name for name in HELPERS),
    }
    if len(files) != 14 or set(files) != expected:
        raise ValueError("Qualification packet inventory differs")
    payloads = {name: sha(data) for name, data in files.items() if name != "footwork/MANIFEST.json"}
    if manifest.get("members") != payloads or manifest.get("wheel_sha256") != sha(files[wheels[0]]):
        raise ValueError("Qualification packet manifest digest differs")
    if manifest.get("automatic_execution") is not False:
        raise ValueError("Qualification packet must not execute automatically")
    return files, manifest


def verify_committed_wheel(name: str, data: bytes, commit: str) -> None:
    """Compare against the release commit, even after later runtime changes."""
    verify_packet_wheel(name, data, commit, PROJECT)


def approved_summary(data: bytes, label: str) -> dict:
    summary = json.loads(data)
    if (
        not isinstance(summary, dict)
        or summary.get("passed") is not True
        or summary.get("independent_review") != "approved"
    ):
        raise ValueError("Qualification must have passing evidence and independent approval: " + label)
    return summary


def inventory(packet: Path, source_commit: str | None = None) -> dict[str, bytes]:
    commit = commit_identity(source_commit)
    packet_files, packet_manifest = qualification_packet(packet)
    wheel_name = next(name for name in packet_files if name.endswith(".whl"))
    verify_committed_wheel(wheel_name, packet_files[wheel_name], commit)
    files = {
        name: data
        for name, data in packet_files.items()
        if name == "footwork/LICENSE" or name == wheel_name or name.startswith("footwork/jevdual/scripts/")
    }
    files.update({name: committed_bytes(commit, relative) for name, relative in DOCS.items()})
    for name, rewrites in CONSUMER_DOCUMENT_LINKS.items():
        for source, target in rewrites.items():
            files[name] = files[name].replace(("](" + source + ")").encode(), ("](" + target + ")").encode())
    files.update({name: committed_bytes(commit, relative) for name, relative in REPORTS.items()})
    legacy_report = "footwork/evidence/fresh-install/report.md"
    files[legacy_report] = files[legacy_report].replace(
        b"](../../docs/capability-packaging.md)", b"](../../installation.md)"
    )
    legacy_attachments = ["footwork/evidence/fresh-install/" + name for name in LEGACY_INSTALL_ATTACHMENTS]
    legacy_derivations = {}
    for name, target in zip(LEGACY_INSTALL_ATTACHMENTS, legacy_attachments, strict=True):
        source = "jevdual/results/clean-installation-20261010/" + name
        original = committed_bytes(commit, source)
        files[target] = sanitized_legacy_json(original)
        legacy_derivations[target] = {
            "source": source,
            "original_sha256": sha(original),
            "derived_sha256": sha(files[target]),
        }
    summaries = {}
    summary_paths = {}
    for label, relative in EVIDENCE.items():
        data = committed_bytes(commit, relative)
        summaries[label] = approved_summary(data, label)
        target = "footwork/evidence/" + label + "-summary.json"
        files[target] = data
        summary_paths[label] = target
    guest = summaries["permission_journey"]
    if (
        guest.get("packet_sha256") != QUALIFIED_PACKET_SHA
        or guest.get("source_commit") != QUALIFIED_PRODUCT_COMMIT
    ):
        raise ValueError("Guest qualification does not refer to the frozen product")
    agent = summaries["installed_agent"]
    if (
        agent.get("packet_sha256") != QUALIFIED_PACKET_SHA
        or agent.get("source_commit") != QUALIFIED_PRODUCT_COMMIT
        or agent.get("wheel_sha256") != packet_manifest["wheel_sha256"]
    ):
        raise ValueError("Agent qualification does not refer to the frozen product")
    scope_keys = (
        "classification",
        "qualified_scope",
        "qualified_scopes",
        "platform",
        "os",
        "architecture",
        "python",
        "host",
        "model",
        "host_version",
    )
    limit_keys = ("limits", "limitations", "disk_persistence", "classification")
    qualification = {
        "qualification": "scoped_local_candidate",
        "qualified_product_source_commit": packet_manifest["source_commit"],
        "release_source_commit": commit,
        "wheel_sha256": packet_manifest["wheel_sha256"],
        "source_packet_sha256": QUALIFIED_PACKET_SHA,
        "evidence": summary_paths,
        "legacy_evidence": {
            "role": "historical_context_only",
            "report": legacy_report,
            "attachments": legacy_attachments,
            "derivations": legacy_derivations,
            "placeholder_semantics": {
                "<WORKTREE>": "Recognized personal Footwork project or Codex worktree root from evidence content.",
                "<HOST_HOME>": "Other /Users/<name> or /home/<name> roots from evidence content.",
                "identity": "Different original identities may share a placeholder; originals remain unchanged and are identified by SHA256.",
                "urls": "Preserved verbatim; placeholders normalize diagnostic paths only.",
            },
            "qualification": "Separate from current reviewed permission_journey and installed_agent evidence.",
        },
        "qualified_scopes": {
            label: {key: summary[key] for key in scope_keys if key in summary}
            for label, summary in summaries.items()
        },
        "limits": {
            label: {key: summary[key] for key in limit_keys if key in summary}
            for label, summary in summaries.items()
        },
    }
    files["footwork/qualification.json"] = encoded(qualification)
    manifest = {
        "schema_version": "1",
        "source_commit": commit,
        "wheel_sha256": packet_manifest["wheel_sha256"],
        "automatic_execution": False,
        "qualification": "scoped_local_candidate",
        "members": {name: sha(data) for name, data in sorted(files.items())},
    }
    files["footwork/MANIFEST.json"] = encoded(manifest)
    return files


def verify(candidate: Path, packet: Path, source_commit: str | None = None) -> dict:
    expected = inventory(packet, source_commit)
    actual = read_archive(candidate)
    if set(actual) != set(expected):
        raise ValueError("Release candidate inventory differs")
    for name, data in expected.items():
        if actual[name] != data:
            raise ValueError("Release candidate member differs: " + name)
    manifest = json.loads(actual["footwork/MANIFEST.json"])
    return {
        "verified": True,
        "sha256": sha(candidate.read_bytes()),
        "members": len(actual),
        "source_commit": manifest["source_commit"],
        "wheel_sha256": manifest["wheel_sha256"],
    }


def build(packet: Path, output: Path, source_commit: str | None = None) -> Path:
    files = inventory(packet, source_commit)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    candidate = output / ARCHIVE_NAME
    with candidate.open("xb") as stream, zipfile.ZipFile(stream, "w") as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification-packet", type=Path, required=True)
    parser.add_argument("--source-commit")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    commit = commit_identity(args.source_commit)
    packet = args.qualification_packet.absolute()
    candidate = args.verify or build(packet, args.output, commit)
    print(json.dumps({"candidate": str(candidate.absolute()), **verify(candidate, packet, commit)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
