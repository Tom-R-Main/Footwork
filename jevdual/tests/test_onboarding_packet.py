"""Standalone qualification receipts must not require a guest Git installation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
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
