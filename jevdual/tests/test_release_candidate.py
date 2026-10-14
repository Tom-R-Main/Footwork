"""Offline immutable packet and release provenance boundary checks."""

from __future__ import annotations

import importlib.util
import json
import posixpath
import re
import stat
import warnings
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def builder(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("release_builder", scripts / "build_release_candidate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_archive(path, files):
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)


@pytest.fixture
def source_packet(builder, monkeypatch, tmp_path):
    files = {
        "footwork/LICENSE": b"MIT fixture license",
        "footwork/README.md": b"old instructions",
        "footwork/vm-plan.md": b"guest plan",
        "footwork/installation.md": b"old installation",
        "footwork/artifacts/jevdual-0.0.1-py3-none-any.whl": b"synthetic wheel",
    }
    files.update({"footwork/jevdual/scripts/" + name: name.encode() for name in builder.HELPERS})
    wheel_hash = builder.sha(b"synthetic wheel")
    files["footwork/MANIFEST.json"] = builder.encoded(
        {
            "source_commit": builder.QUALIFIED_PRODUCT_COMMIT,
            "automatic_execution": False,
            "wheel_sha256": wheel_hash,
            "members": {name: builder.sha(data) for name, data in files.items()},
        }
    )
    packet = tmp_path / "qualified.zip"
    save_archive(packet, files)
    monkeypatch.setattr(builder, "QUALIFIED_PACKET_SHA", builder.sha(packet.read_bytes()))
    return packet, files


@pytest.mark.parametrize(
    "name", ["/footwork/escape", "footwork/../escape", "footwork//escape", "footwork\\escape"]
)
def test_archive_rejects_unsafe_member_paths(builder, tmp_path, name):
    path = tmp_path / "unsafe.zip"
    save_archive(path, {name: b"unsafe"})
    with pytest.raises(ValueError, match="Unsafe"):
        builder.read_archive(path)


def test_duplicate_and_symlink_members_are_rejected(builder, tmp_path):
    duplicate = tmp_path / "duplicate.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(duplicate, "w") as archive:
            archive.writestr("footwork/file", b"first")
            archive.writestr("footwork/file", b"second")
    with pytest.raises(ValueError, match="duplicate"):
        builder.read_archive(duplicate)
    symlink = tmp_path / "symlink.zip"
    with zipfile.ZipFile(symlink, "w") as archive:
        entry = zipfile.ZipInfo("footwork/link")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(entry, "outside")
    with pytest.raises(ValueError, match="Unsafe"):
        builder.read_archive(symlink)


def test_frozen_packet_digest_rejects_self_consistent_replacement(builder, source_packet, tmp_path):
    packet, files = source_packet
    manifest = json.loads(files["footwork/MANIFEST.json"])
    files["footwork/LICENSE"] = b"different license"
    manifest["members"]["footwork/LICENSE"] = builder.sha(files["footwork/LICENSE"])
    files["footwork/MANIFEST.json"] = builder.encoded(manifest)
    replacement = tmp_path / "replacement.zip"
    save_archive(replacement, files)
    with pytest.raises(ValueError, match="immutable"):
        builder.qualification_packet(replacement)
    assert builder.qualification_packet(packet)[1]["source_commit"] == builder.QUALIFIED_PRODUCT_COMMIT


def test_packet_manifest_checks_every_payload_even_when_archive_pin_is_updated(
    builder, source_packet, monkeypatch, tmp_path
):
    _, files = source_packet
    files["footwork/LICENSE"] = b"tampered"
    tampered = tmp_path / "tampered.zip"
    save_archive(tampered, files)
    monkeypatch.setattr(builder, "QUALIFIED_PACKET_SHA", builder.sha(tampered.read_bytes()))
    with pytest.raises(ValueError, match="digest"):
        builder.qualification_packet(tampered)


@pytest.mark.parametrize(
    "summary",
    [
        {"passed": False, "independent_review": "approved"},
        {"passed": True, "independent_review": "pending"},
        {"passed": 1, "independent_review": "approved"},
    ],
)
def test_unqualified_or_unreviewed_evidence_cannot_release(builder, summary):
    with pytest.raises(ValueError, match="independent approval"):
        builder.approved_summary(json.dumps(summary).encode(), "installed_agent")


def mocked_release_source(builder, monkeypatch, agent_changes=None):
    commit = "f" * 40
    blobs = {path: ("committed " + path).encode() for path in builder.DOCS.values()}
    blobs.update({path: b"exact committed report" for path in builder.REPORTS.values()})
    blobs[builder.REPORTS["footwork/evidence/fresh-install/report.md"]] = (
        "\n".join("[Receipt](" + name + ")" for name in builder.LEGACY_INSTALL_ATTACHMENTS)
        + "\n[Consumer guide](../../docs/capability-packaging.md)"
    ).encode()
    blobs.update(
        {
            "jevdual/results/clean-installation-20261010/" + name: b'{"historical":true}'
            for name in builder.LEGACY_INSTALL_ATTACHMENTS
        }
    )
    blobs[builder.DOCS["footwork/installation.md"]] = "\n".join(
        "[Link](" + source + ")" for source in builder.DOCUMENT_LINKS
    ).encode()
    blobs[builder.DOCS["footwork/README.md"]] = (
        b"[Install](capability-packaging.md) [Host](installed-agent-host.md)"
    )
    blobs[builder.DOCS["footwork/agent-host.md"]] = (
        b"[Install](capability-packaging.md) [Remote](https://example.test) [Section](#setup)"
    )
    blobs[builder.EVIDENCE["permission_journey"]] = builder.encoded(
        {
            "passed": True,
            "independent_review": "approved",
            "packet_sha256": builder.QUALIFIED_PACKET_SHA,
            "source_commit": builder.QUALIFIED_PRODUCT_COMMIT,
            "classification": "fresh dependencies on provisioned guest",
            "disk_persistence": "not_checked",
        }
    )
    agent = {
        "passed": True,
        "independent_review": "approved",
        "packet_sha256": builder.QUALIFIED_PACKET_SHA,
        "source_commit": builder.QUALIFIED_PRODUCT_COMMIT,
        "wheel_sha256": builder.sha(b"synthetic wheel"),
        "host": "Claude Code",
        "limits": "one bounded fixture task",
    }
    agent.update(agent_changes or {})
    blobs[builder.EVIDENCE["installed_agent"]] = builder.encoded(agent)

    def committed(requested, relative):
        assert requested == commit
        return blobs[relative]

    monkeypatch.setattr(builder, "committed_bytes", committed)
    monkeypatch.setattr(
        builder,
        "commit_identity",
        lambda requested: commit if requested == commit else pytest.fail("unexpected fixture commit"),
    )
    monkeypatch.setattr(builder, "verify_committed_wheel", lambda name, data, requested: None)
    return commit


def test_qualification_packet_hash_and_parse_share_snapshot(builder, source_packet, monkeypatch):
    packet, files = source_packet
    original = packet.read_bytes()

    def read_then_replace(path):
        assert path == packet
        packet.write_bytes(b"concurrent replacement")
        return original

    monkeypatch.setattr(builder, "snapshot", read_then_replace)
    parsed, manifest = builder.qualification_packet(packet)
    assert parsed == files
    assert manifest["source_commit"] == builder.QUALIFIED_PRODUCT_COMMIT


def test_candidate_verifier_hash_and_parse_share_snapshot(builder, source_packet, monkeypatch, tmp_path):
    packet, _ = source_packet
    commit = mocked_release_source(builder, monkeypatch)
    candidate = builder.build(packet, tmp_path / "candidate", commit)
    original = candidate.read_bytes()
    expected_hash = builder.sha(original)
    real_snapshot = builder.snapshot

    def read_then_replace(path):
        data = real_snapshot(path)
        if path == candidate:
            candidate.write_bytes(b"concurrent replacement")
        return data

    monkeypatch.setattr(builder, "snapshot", read_then_replace)
    assert builder.verify(candidate, packet, commit)["sha256"] == expected_hash


def test_all_markdown_links_resolve_inside_final_bundle(
    builder,
    source_packet,
    monkeypatch,
):
    packet, _ = source_packet
    commit = mocked_release_source(builder, monkeypatch)
    files = builder.inventory(packet, commit)
    assert len(files) == 30
    checked = []
    for name in (name for name in files if name.endswith(".md")):
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", files[name].decode()):
            if link.startswith(("http://", "https://", "#")):
                continue
            relative = link.split("#", 1)[0]
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), relative))
            assert target in files, (name, link)
            checked.append(target)
    assert set(builder.REPORTS).issubset(checked)
    assert "footwork/agent-host.md" in checked
    assert b"](installation.md)" in files["footwork/README.md"]
    assert b"](agent-host.md)" in files["footwork/README.md"]
    assert b"](installation.md)" in files["footwork/agent-host.md"]
    for name in builder.REPORTS.keys() - {"footwork/evidence/fresh-install/report.md"}:
        assert files[name] == b"exact committed report"
    legacy = files["footwork/evidence/fresh-install/report.md"]
    assert b"](../../installation.md)" in legacy
    assert b"](../../docs/capability-packaging.md)" not in legacy
    for name in builder.LEGACY_INSTALL_ATTACHMENTS:
        assert json.loads(files["footwork/evidence/fresh-install/" + name]) == {"historical": True}
    qualification = json.loads(files["footwork/qualification.json"])
    assert qualification["legacy_evidence"]["role"] == "historical_context_only"


@pytest.mark.parametrize(
    "changes",
    [
        {"packet_sha256": "0" * 64},
        {"source_commit": "0" * 40},
        {"wheel_sha256": "0" * 64},
    ],
)
def test_approved_agent_evidence_cannot_qualify_another_artifact(
    builder,
    source_packet,
    monkeypatch,
    changes,
):
    packet, _ = source_packet
    commit = mocked_release_source(builder, monkeypatch, changes)
    with pytest.raises(ValueError, match="Agent qualification"):
        builder.inventory(packet, commit)


def test_release_repeats_exactly_and_extracted_manifest_remains_compatible(
    builder, source_packet, monkeypatch, tmp_path
):
    packet, _ = source_packet
    commit = mocked_release_source(builder, monkeypatch)
    one = builder.build(packet, tmp_path / "one", commit)
    two = builder.build(packet, tmp_path / "two", commit)
    assert one.read_bytes() == two.read_bytes()
    assert builder.verify(one, packet, commit)["verified"]
    with pytest.raises(FileExistsError):
        builder.build(packet, tmp_path / "one", commit)
    root = tmp_path / "extracted"
    for name, data in builder.read_archive(one).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    from verify_onboarding_packet import verify

    assert verify(root / "footwork")["source_commit"] == commit
    qualification = json.loads((root / "footwork/qualification.json").read_text())
    assert qualification["qualified_product_source_commit"] == builder.QUALIFIED_PRODUCT_COMMIT
    assert qualification["release_source_commit"] == commit
    assert qualification["limits"]["installed_agent"] == {"limits": "one bounded fixture task"}


def test_candidate_member_tampering_is_rejected(builder, source_packet, monkeypatch, tmp_path):
    packet, _ = source_packet
    commit = mocked_release_source(builder, monkeypatch)
    candidate = builder.build(packet, tmp_path / "original", commit)
    files = builder.read_archive(candidate)
    files["footwork/agent-host.md"] = b"unreviewed change"
    tampered = tmp_path / "tampered-candidate.zip"
    save_archive(tampered, files)
    with pytest.raises(ValueError, match="member differs"):
        builder.verify(tampered, packet, commit)


def test_distributed_legacy_receipts_do_not_expose_personal_home_paths(
    builder,
    source_packet,
    monkeypatch,
):
    packet, packet_files = source_packet
    commit = mocked_release_source(builder, monkeypatch)
    committed = builder.committed_bytes
    original = json.dumps(
        {
            "python": "/Users/alice/.codex/worktrees/trial-one/footwork/output/install/venv/bin/python",
            "nested": [{"argv": ["/home/bob/projects/footwork/output/install/venv/bin/python"]}],
            "log": 'context={"home":"/Users/alice","cache":"/home/bob/.cache"}',
            "oracle_actual": "Invoice report\n17.25 USD",
        }
    ).encode()

    def with_personal_paths(requested, relative):
        if relative == "jevdual/results/clean-installation-20261010/py312-installation.json":
            return original
        return committed(requested, relative)

    monkeypatch.setattr(builder, "committed_bytes", with_personal_paths)
    files = builder.inventory(packet, commit)
    distributed = files["footwork/evidence/fresh-install/py312-installation.json"]
    assert b"/Users/alice" not in distributed
    assert b"/home/bob" not in distributed
    assert json.loads(distributed)["oracle_actual"] == "Invoice report\n17.25 USD"
    qualification = json.loads(files["footwork/qualification.json"])
    derivation = qualification["legacy_evidence"]["derivations"][
        "footwork/evidence/fresh-install/py312-installation.json"
    ]
    assert derivation["original_sha256"] == builder.sha(original)
    assert derivation["derived_sha256"] == builder.sha(distributed)
    assert (
        builder.committed_bytes(commit, "jevdual/results/clean-installation-20261010/py312-installation.json")
        == original
    )
    for name, data in packet_files.items():
        if name.endswith(".whl") or "/scripts/" in name or name == "footwork/LICENSE":
            assert files[name] == data


def test_sanitized_json_preserves_urls_oracles_nonpath_text_and_multiple_identities(builder):
    original = {
        "first": "/Users/alice/.codex/worktrees/first/footwork/output/run.json",
        "second": "/home/bob/projects/footwork/output/run.json",
        "nested": [{"home": "/Users/charlie", "cache": "/home/dana/.cache/file"}],
        "embedded": 'log={"path":"/Users/erin/projects/footwork/output/a.json"}',
        "url": "https://example.test/Users/alice/path",
        "file_url": "file:///Users/bob/path",
        "text": "Users Alice, home Bob and Invoice report are ordinary words.",
        "oracle": "Invoice report\n17.25 USD",
        "number": 17.25,
        "flag": False,
        "none": None,
    }
    data = json.dumps(original).encode()
    normalized = builder.sanitized_legacy_json(data)
    result = json.loads(normalized)
    assert result["first"] == "<WORKTREE>/output/run.json"
    assert result["second"] == "<WORKTREE>/output/run.json"
    assert result["nested"] == [{"home": "<HOST_HOME>", "cache": "<HOST_HOME>/.cache/file"}]
    assert result["embedded"] == 'log={"path":"<WORKTREE>/output/a.json"}'
    for key in ("url", "file_url", "text", "oracle", "number", "flag", "none"):
        assert result[key] == original[key]
    assert builder.sanitized_legacy_json(data) == normalized
    assert json.loads(data) == original


def test_sanitized_json_refuses_key_collision_instead_of_losing_evidence(builder):
    data = json.dumps({"/Users/alice/file": "first", "/home/bob/file": "second"}).encode()
    with pytest.raises(ValueError, match="keys collide"):
        builder.sanitized_legacy_json(data)
