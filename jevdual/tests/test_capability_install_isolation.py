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


def test_installer_selects_built_cua_wheel_explicitly(tmp_path, monkeypatch):
    """A later PyPI wheel with the same version must not replace the checked native artifact."""
    import hashlib
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location("install", ROOT / "scripts/capability_clean_install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = tmp_path / "project"
    project.mkdir()
    wheel = project / "jevdual.whl"
    wheel.write_bytes(b"product")
    wheelhouse = project / "dependency-wheels"
    wheelhouse.mkdir()
    dependency = wheelhouse / "cua_driver-0.38.0-py3-none-test.whl"
    dependency.write_bytes(b"checked native artifact")
    monkeypatch.setattr(module, "PROJECT", project)
    monkeypatch.setattr(module.shutil, "which", lambda name: "owned-uv")
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if command[6] == "venv":
            venv = Path(command[-1])
            venv.mkdir()
            (venv / "pyvenv.cfg").write_text("include-system-site-packages = false")
            return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=1)  # Stop before importing the synthetic wheels.

    monkeypatch.setattr(module.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", [
        "install", "--python", sys.executable, "--wheel", str(wheel),
        "--find-links", str(wheelhouse), "--run-dir", str(project / "output/run"),
    ])
    assert module.main() == 1
    assert commands[-1][-2:] == [str(wheel), str(dependency)]
    receipt = json.loads((project / "output/run/receipt.json").read_text())
    assert receipt["local_dependency_wheels"] == {
        dependency.name: hashlib.sha256(dependency.read_bytes()).hexdigest()
    }


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


def test_generated_launches_isolate_interpreter_and_private_root(tmp_path, monkeypatch):
    from jevdual.capability.recovery import ExecutionStore
    from jevdual.capability.setup import make_config

    document = tmp_path / "doc.txt"
    document.write_text("prefix")
    manifest = make_config(
        tmp_path / "run",
        source_pid=1,
        source_window=2,
        source_url="http://127.0.0.1:8000/",
        destination_pid=3,
        destination_window=4,
        document=document,
    )
    server = json.loads(Path(manifest["host_config"]).read_text())["mcpServers"]["footwork"]
    assert server["args"][:3] == ["-I", "-m", "jevdual.capability.cli"]
    assert manifest["report_adapter"][1:4] == ["-I", "-m", "jevdual.capability.cli"]
    assert server["env"]["ANONYMIZED_TELEMETRY"] == server["env"]["BROWSER_USE_CLOUD_SYNC"] == "false"
    captured = []
    monkeypatch.setattr(
        "jevdual.capability.recovery.subprocess.Popen", lambda command, **kwargs: captured.append(command)
    )
    from types import SimpleNamespace

    store = ExecutionStore(tmp_path / "run/ops.sqlite")
    monkeypatch.setattr(store, "directory", lambda op_id: tmp_path / "run/packet")
    store._launch(SimpleNamespace(id="fixture"))
    assert captured[0][1:4] == ["-I", "-m", "jevdual.capability.execution_worker"]


def test_failed_install_reports_bounded_evidence_and_keeps_failure(tmp_path, monkeypatch, capsys):
    """The command users run must explain failure without opening a CI artifact."""
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location("install", ROOT / "scripts/capability_clean_install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = tmp_path / "project"
    project.mkdir()
    wheel = project / "product.whl"
    wheel.write_bytes(b"fixture")
    monkeypatch.setattr(module, "PROJECT", project)
    monkeypatch.setattr(module.shutil, "which", lambda name: "fixture-uv")
    for timed_out in (False, True):
        run_dir = project / "output" / str(timed_out)

        def run(command, timed_out=timed_out, **kwargs):
            if command[6] == "venv":
                venv = Path(command[-1])
                venv.mkdir()
                (venv / "pyvenv.cfg").write_text("include-system-site-packages = false")
                return SimpleNamespace(returncode=0)
            kwargs["stderr"].write("x" * 8000 + '\nDNS lookup failed\n::error::untrusted output\n')
            kwargs["stderr"].flush()
            if timed_out:
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            return SimpleNamespace(returncode=2)

        monkeypatch.setattr(module.subprocess, "run", run)
        monkeypatch.setattr(sys, "argv", [
            "install", "--python", sys.executable, "--wheel", str(wheel), "--run-dir", str(run_dir),
        ])
        assert module.main() == 1
        report = json.loads(capsys.readouterr().out.splitlines()[-1])
        assert report["stage"] == "install"
        assert report["returncode"] == (-1 if timed_out else 2)
        assert report["timed_out"] is timed_out
        assert "DNS lookup failed" in report["stderr_tail"]
        assert len(report["stderr_tail"]) <= 4096
        assert Path(report["stderr_log"]).read_text().endswith("::error::untrusted output\n")
        receipt = json.loads((run_dir / "receipt.json").read_text())
        assert receipt["passed"] is False
        assert receipt["commands"][-1]["timed_out"] is timed_out
        assert len(receipt["commands"]) == 2  # No retry or false qualification.
        assert not (run_dir / "origins.stdout.log").exists()
