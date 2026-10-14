"""Standalone qualification receipts must not require a guest Git installation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
COMMIT = "a" * 40


def installer():
    spec = importlib.util.spec_from_file_location("packet_installer", SCRIPTS / "capability_clean_install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_packet_installer_writes_receipt_without_git(tmp_path, monkeypatch):
    module = installer()
    project = tmp_path / "footwork"
    project.mkdir()
    (project / "MANIFEST.json").write_text(json.dumps({"source_commit": COMMIT}))
    wheel = project / "fixture.whl"
    wheel.write_bytes(b"qualification fixture")
    monkeypatch.setattr(module, "PROJECT", project)
    monkeypatch.setattr(module.shutil, "which", lambda name: "fixture-uv")

    def no_git(*args, **kwargs):
        raise RuntimeError("Guest Git must never be invoked")

    monkeypatch.setattr(module.subprocess, "check_output", no_git)
    # Stop at the external uv boundary; execute the real installer receipt path.
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=17))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "install",
            "--python",
            sys.executable,
            "--wheel",
            str(wheel),
            "--run-dir",
            str(project / "output/install"),
        ],
    )
    assert module.main() == 1
    receipt = json.loads((project / "output/install/receipt.json").read_text())
    assert receipt["source_commit"] == COMMIT
    assert receipt["commands"][0]["stage"] == "venv"
    assert receipt["commands"][0]["returncode"] == 17


def test_manifest_overrides_enclosing_repository(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    project = tmp_path / "footwork"
    project.mkdir()
    (project / "MANIFEST.json").write_text(json.dumps({"source_commit": COMMIT}))
    assert installer().source_commit(project) == COMMIT


@pytest.mark.parametrize("value", ["bad", None, 123, "a" * 39])
def test_bad_packet_provenance_refuses_without_git(tmp_path, monkeypatch, value):
    module = installer()
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"source_commit": value}))
    monkeypatch.setattr(module.subprocess, "check_output", lambda *a, **k: pytest.fail("Git was invoked"))
    with pytest.raises(ValueError, match="source commit"):
        module.source_commit(tmp_path)


def test_no_manifest_or_owned_git_returns_unavailable(tmp_path, monkeypatch):
    module = installer()
    monkeypatch.setattr(module.subprocess, "check_output", lambda *a, **k: pytest.fail("Git was invoked"))
    assert module.source_commit(tmp_path) == "unavailable"


def test_checkout_provenance_remains_available():
    project = SCRIPTS.parents[1]
    expected = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip()
    assert installer().source_commit(project) == expected


def test_native_bad_manifest_refuses_before_resource_creation(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import capability_installed_trial as trial

    (tmp_path / "MANIFEST.json").write_text(json.dumps({"source_commit": "invalid"}))
    monkeypatch.setattr(trial, "PROJECT", tmp_path)
    monkeypatch.setattr(trial, "InstalledServer", lambda *a, **k: pytest.fail("Server must not start"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trial",
            "--python",
            sys.executable,
            "--scope",
            str(tmp_path / "absent-scope.json"),
            "--run-dir",
            str(tmp_path / "output/native"),
        ],
    )
    with pytest.raises(ValueError, match="source commit"):
        trial.main()
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("mutation", [None, "modified", "extra", "symlink", "escape"])
def test_guest_verifier_checks_extracted_payload(tmp_path, mutation):
    root = tmp_path / "footwork"
    (root / "artifacts").mkdir(parents=True)
    wheel = root / "artifacts/fixture.whl"
    wheel.write_bytes(b"fixture wheel")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    manifest = {
        "source_commit": COMMIT,
        "wheel_sha256": digest,
        "members": {"footwork/artifacts/fixture.whl": digest},
    }
    if mutation == "modified":
        wheel.write_bytes(b"modified wheel")
    elif mutation == "extra":
        (root / "unexpected.txt").write_text("extra")
    elif mutation == "symlink":
        outside = tmp_path / "outside.whl"
        wheel.rename(outside)
        wheel.symlink_to(outside)
    elif mutation == "escape":
        manifest["members"]["footwork/../outside.whl"] = digest
    (root / "MANIFEST.json").write_text(json.dumps(manifest))
    run = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS / "verify_onboarding_packet.py"), "--packet-root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if mutation is None:
        assert run.returncode == 0, run.stderr
        assert json.loads(run.stdout)["source_commit"] == COMMIT
    else:
        assert run.returncode == 1
        assert "verification failed" in run.stderr


def test_frozen_packet_uses_committed_runtime_after_later_changes(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import build_capability_wheel as wheels
    import build_onboarding_packet as packets

    project = tmp_path / "project"
    project.mkdir()
    package = project / "jevdual"
    package.mkdir()
    (project / "LICENSE").write_text("MIT fixture license")
    (package / "pyproject.toml").write_text(
        '[project]\nname="jevdual"\nversion="0.0.1"\ndescription="fixture"\n'
        'requires-python=">=3.11"\ndependencies=[]\n'
        '[project.scripts]\nfootwork-capability="jevdual.capability.cli:main"\n'
    )
    for relative in wheels.REQUIRED:
        path = package / "python" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# frozen runtime fixture\n")
    for relative in (
        "docs/independent-onboarding.md",
        "docs/onboarding-vm-plan.md",
        "docs/capability-packaging.md",
        *("scripts/" + name for name in packets.HELPERS),
    ):
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen helper or instructions\n")

    def git(*arguments):
        return subprocess.check_output(
            ["git", "-c", "user.name=Packet Fixture", "-c", "user.email=fixture@example.invalid", *arguments],
            cwd=project,
            text=True,
        ).strip()

    git("init", "--quiet")
    git("add", "LICENSE", "jevdual")
    git("commit", "--quiet", "-m", "freeze fixture")
    frozen = git("rev-parse", "HEAD")
    monkeypatch.setattr(packets, "PROJECT", project)
    wheel = wheels.build(package, tmp_path / "wheel")
    packet = packets.build(wheel, tmp_path / "packet")
    packet_bytes = packet.read_bytes()

    (package / "python/jevdual/capability/cli.py").write_text("# changed runtime\n")
    (package / "python/jevdual/later.py").write_text("# added after qualification\n")
    git("add", "jevdual")
    git("commit", "--quiet", "-m", "later runtime")
    with pytest.raises(ValueError, match="inventory"):
        wheels.verify(wheel, package)
    assert packets.verify(packet, wheel, frozen)["source_commit"] == frozen
    with pytest.raises(ValueError, match="inventory"):
        packets.verify(packet, wheel)

    # A replacement runtime with valid RECORD hashes still cannot borrow the old provenance.
    replacement = wheels.build(package, tmp_path / "replacement")
    with pytest.raises(ValueError, match="inventory"):
        packets.verify(packet, replacement, frozen)
    corrupted = tmp_path / "corrupted" / wheel.name
    corrupted.parent.mkdir()
    with zipfile.ZipFile(wheel) as original, zipfile.ZipFile(corrupted, "w") as modified:
        for name in original.namelist():
            data = original.read(name)
            if name == "jevdual/capability/cli.py":
                data += b"# tampered payload\n"
            modified.writestr(name, data)
    with pytest.raises(ValueError, match="Artifact bytes differ"):
        packets.verify(packet, corrupted, frozen)
    assert packet.read_bytes() == packet_bytes


def test_packet_inventory_uses_one_verified_wheel_snapshot(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import build_onboarding_packet as packets

    wheel = tmp_path / "fixture.whl"
    original = b"first immutable snapshot"
    wheel.write_bytes(original)
    monkeypatch.setattr(packets, "PROJECT", tmp_path)
    monkeypatch.setattr(packets, "commit_identity", lambda commit, project: COMMIT)
    monkeypatch.setattr(packets, "committed_bytes", lambda *args: b"fixture source")

    def verified_then_replaced(name, data, commit, project):
        assert data == original
        wheel.write_bytes(b"concurrent replacement")

    monkeypatch.setattr(packets, "verify_committed_wheel", verified_then_replaced)
    files = packets.inventory(wheel, COMMIT)
    assert files["footwork/artifacts/fixture.whl"] == original
    assert json.loads(files["footwork/MANIFEST.json"])["wheel_sha256"] == hashlib.sha256(original).hexdigest()


@pytest.mark.parametrize("mode", [stat.S_IFLNK, stat.S_IFDIR, stat.S_IFIFO, stat.S_IFCHR])
def test_packet_verifier_refuses_unsafe_member_modes(tmp_path, monkeypatch, mode):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import build_onboarding_packet as packets

    path = tmp_path / "packet.zip"
    entry = zipfile.ZipInfo("footwork/payload")
    entry.create_system = 3
    entry.external_attr = (mode | 0o600) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(entry, b"same expected bytes")
    monkeypatch.setattr(packets, "inventory", lambda *args: {entry.filename: b"same expected bytes"})
    with pytest.raises(ValueError, match="Unsafe"):
        packets.verify(path, tmp_path / "unused-wheel", COMMIT)


def test_snapshot_refuses_symlink_and_observed_mutation(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import build_onboarding_packet as packets

    path = tmp_path / "artifact"
    path.write_bytes(b"original")
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="nonsymlink"):
        packets.snapshot(link)
    directory = tmp_path / "directory"
    directory.mkdir()
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo, 0o600)
    for nonregular in (directory, fifo):
        with pytest.raises(ValueError, match="regular"):
            packets.snapshot(nonregular)
    original = packets.os.fdopen

    class MutatingRead:
        def __init__(self, *args):
            self.source = original(*args)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.source.close()

        def fileno(self):
            return self.source.fileno()

        def read(self, size):
            data = self.source.read(size)
            path.write_bytes(b"replacement after read")
            return data

    monkeypatch.setattr(packets.os, "fdopen", MutatingRead)
    with pytest.raises(ValueError, match="changed during snapshot"):
        packets.snapshot(path)


def test_source_identity_rejects_tree_and_blob_objects(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import build_onboarding_packet as packets
    import build_release_candidate as release

    project = SCRIPTS.parents[1]
    for expression in ("HEAD^{tree}", "HEAD:LICENSE"):
        identity = subprocess.check_output(["git", "rev-parse", expression], cwd=project, text=True).strip()
        with pytest.raises(ValueError, match="commit object"):
            packets.commit_identity(identity, project)
        with pytest.raises(ValueError, match="commit object"):
            release.commit_identity(identity)
        with pytest.raises(ValueError, match="commit object"):
            packets.committed_bytes(identity, "LICENSE", project)
        with pytest.raises(ValueError, match="commit object"):
            release.committed_bytes(identity, "LICENSE")


def test_archive_size_budget_refuses_compressed_oversize(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import build_onboarding_packet as packets

    path = tmp_path / "oversize.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("footwork/oversize", b"x" * (8 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="bounded candidate size"):
        packets.parse_archive(path.read_bytes())
