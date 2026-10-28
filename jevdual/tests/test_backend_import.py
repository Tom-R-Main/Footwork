"""A pure wheel lacks optional Jev acceleration; broken extensions remain diagnostic."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _import_backend(tmp_path: Path, extension: str | None = None, *, disabled: bool = False):
    source = Path(__file__).resolve().parents[1] / "python/jevdual"
    package = tmp_path / "jevdual"
    package.mkdir()
    for name in ("__init__.py", "_native.py"):
        shutil.copyfile(source / name, package / name)
    if extension is not None:
        (package / "_core.py").write_text(extension)
    environment = dict(os.environ)
    environment.pop("JEVDUAL_PURE_PY", None)
    if disabled:
        environment["JEVDUAL_PURE_PY"] = "1"
    # A clean copied package models the pure wheel rather than a source checkout
    # whose editable installation may expose a compiled extension.
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import json,sys; sys.path.insert(0,sys.argv[1]); "
                "import jevdual; from jevdual import _native; "
                "print(json.dumps(_native.acceleration_status()))"
            ),
            str(tmp_path),
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_expected_missing_extension_is_quiet_and_reported(tmp_path):
    result = _import_backend(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    status = json.loads(result.stdout)
    assert status["available"] is False and status["status"] == "not_installed"
    assert status["backend"] == "pure-python"


@pytest.mark.parametrize(
    "extension",
    [
        "raise ModuleNotFoundError('fixture dependency unavailable', name='fixture_dependency')\n",
        "raise ImportError('fixture extension ABI incompatible')\n",
    ],
)
def test_broken_extension_keeps_warning_and_fallback(tmp_path, extension):
    result = _import_backend(tmp_path, extension)
    assert result.returncode == 0, result.stderr
    assert "falling back to pure Python" in result.stderr
    assert "circular import" not in result.stderr
    assert json.loads(result.stdout)["status"] == "unavailable"


def test_forced_pure_backend_does_not_import_or_warn(tmp_path):
    result = _import_backend(tmp_path, "raise RuntimeError('must not import')\n", disabled=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout)["status"] == "disabled"


def test_available_extension_reports_its_backend(tmp_path):
    result = _import_backend(tmp_path, "def version(): return 'fixture-version'\n")
    assert result.returncode == 0, result.stderr
    status = json.loads(result.stdout)
    assert status["available"] is True and status["status"] == "available"
    assert status["backend"] == "native fixture-version"
