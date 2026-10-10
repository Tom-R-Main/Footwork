"""Qualification cannot pass an inherited dependency path under optimization."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_optimized_installer_refuses_system_site_inheritance(tmp_path):
    project = tmp_path / "project"
    (project / "output").mkdir(parents=True)
    wheel = project / "test.whl"
    wheel.write_bytes(b"test")
    code = """
import importlib.util,sys,types
from pathlib import Path
spec=importlib.util.spec_from_file_location("install",sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.PROJECT=Path(sys.argv[2]);m.shutil.which=lambda name:"fake-uv"
m.subprocess.check_output=lambda *a,**k:"testcommit\\n"
def fake_run(command,**kw):
    env=Path(command[-1]);env.mkdir();(env/"pyvenv.cfg").write_text("include-system-site-packages = true")
    return types.SimpleNamespace(returncode=0)
m.subprocess.run=fake_run
sys.argv=["install","--python",sys.executable,"--wheel",str(m.PROJECT/"test.whl"),"--run-dir",str(m.PROJECT/"output/run")]
raise SystemExit(m.main())
"""
    run = subprocess.run(
        [sys.executable, "-O", "-c", code, str(ROOT / "scripts/capability_clean_install.py"), str(project)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 1, run.stderr
    result = json.loads((project / "output/run/receipt.json").read_text())
    assert result["passed"] is False and result["failed_gates"] == ["system_site_inheritance"]
    assert len(result["commands"]) == 1


def test_isolation_redirects_state_and_removes_overrides(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("install", ROOT / "scripts/capability_clean_install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("PYTHONPATH", "not-a-source")
    monkeypatch.setenv("PYTHONOPTIMIZE", "1")
    monkeypatch.setenv("UV_INDEX_URL", "not-a-registry")
    monkeypatch.setenv("TEST_PROVIDER_KEY", "fixture-never-print")
    env = module.isolated_environment(tmp_path)
    assert not any(
        key in env for key in ("PYTHONPATH", "PYTHONOPTIMIZE", "UV_INDEX_URL", "TEST_PROVIDER_KEY")
    )
    assert env["HOME"] == str(tmp_path / "private-home") and env["TMPDIR"] == str(tmp_path / "private-temp")
    assert env["ANONYMIZED_TELEMETRY"] == env["BROWSER_USE_CLOUD_SYNC"] == "false"


def test_runtime_audit_is_private_optional_and_not_a_receipt(tmp_path, monkeypatch):
    from jevdual.capability.runtime import emit_runtime_audit

    monkeypatch.delenv("FOOTWORK_RUNTIME_AUDIT_DIR", raising=False)
    emit_runtime_audit("worker", "fixture")
    assert list(tmp_path.iterdir()) == []
    directory = tmp_path / "audit"
    directory.mkdir(mode=0o700)
    monkeypatch.setenv("FOOTWORK_RUNTIME_AUDIT_DIR", str(directory))
    emit_runtime_audit("server")
    files = list(directory.iterdir())
    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o600
    context = json.loads(files[0].read_text())
    assert context["pid"] == os.getpid() and context["role"] == "server"
    assert "disposition" not in context and "text" not in context
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    monkeypatch.setenv("FOOTWORK_RUNTIME_AUDIT_DIR", str(public))
    emit_runtime_audit("worker", "fixture")
    assert list(public.iterdir()) == []
