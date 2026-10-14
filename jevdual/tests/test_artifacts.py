"""External artifacts never acquire native/browser session provenance."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

from jevdual.artifacts import MAX_ARTIFACT_BYTES, check_artifact
from jevdual.cli import main


def test_exact_multiline_bytes_and_no_normalization(tmp_path):
    expected = tmp_path / "reviewed.txt"
    target = tmp_path / "note.txt"
    text = b"PRIVATE_NOTE_LINE\nsecond line\n"
    expected.write_bytes(text)
    target.write_bytes(text)
    digest = hashlib.sha256(text).hexdigest()
    result = check_artifact(target, expected, digest)
    assert result["ok"] and result["claims"] == ["current_artifact_byte_equality"]
    assert "PRIVATE_NOTE_LINE" not in json.dumps(result)
    for changed in (text.replace(b"\n", b"\r\n"), text[:-1], text + b" "):
        target.write_bytes(changed)
        assert not check_artifact(target, expected, digest)["ok"]


def test_source_digest_change_and_invalid_digest_fail_closed(tmp_path):
    expected = tmp_path / "reviewed.txt"
    target = tmp_path / "note.txt"
    expected.write_bytes(b"before\n")
    digest = hashlib.sha256(expected.read_bytes()).hexdigest()
    expected.write_bytes(b"after\n")
    target.write_bytes(expected.read_bytes())
    result = check_artifact(target, expected, digest)
    assert not result["ok"] and "bound digest" in result["detail"]
    for bad in ("invalid", "a" * 63, "A" * 64):
        assert not check_artifact(target, expected, bad)["ok"]


def test_missing_symlink_nonregular_and_oversize_files(tmp_path):
    expected = tmp_path / "expected"
    target = tmp_path / "target"
    expected.write_bytes(b"same")
    digest = hashlib.sha256(b"same").hexdigest()
    assert not check_artifact(target, expected, digest)["ok"]
    target.symlink_to(expected)
    assert not check_artifact(target, expected, digest)["ok"]
    target.unlink()
    target.mkdir()
    assert not check_artifact(target, expected, digest)["ok"]
    target.rmdir()
    os.mkfifo(target)
    assert not check_artifact(target, expected, digest)["ok"]
    target.unlink()
    target.write_bytes(b"x" * (MAX_ARTIFACT_BYTES + 1))
    assert not check_artifact(target, expected, digest)["ok"]
    expected.write_bytes(target.read_bytes())
    digest = hashlib.sha256(expected.read_bytes()).hexdigest()
    assert not check_artifact(target, expected, digest)["ok"]


def test_public_cli_exit_codes_and_output_do_not_contain_text(tmp_path, capsys):
    expected, target = tmp_path / "expected", tmp_path / "target"
    expected.write_bytes(b"PRIVATE_NOTE\n")
    target.write_bytes(expected.read_bytes())
    digest = hashlib.sha256(expected.read_bytes()).hexdigest()
    args = ["check-artifact", str(target), "--expected-file", str(expected), "--expected-sha256", digest]
    assert main(args) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["ok"] and "PRIVATE_NOTE" not in output
    target.write_bytes(b"different")
    assert main(args) == 6
    assert not json.loads(capsys.readouterr().out)["ok"]
    assert not (tmp_path / "session.json").exists()


def test_cli_fresh_process_without_credentials_or_native_driver(tmp_path):
    expected, target = tmp_path / "expected", tmp_path / "target"
    expected.write_bytes(b"multiline\nartifact\n")
    target.write_bytes(expected.read_bytes())
    digest = hashlib.sha256(expected.read_bytes()).hexdigest()
    code = "from jevdual.cli import main; import sys; sys.exit(main(sys.argv[1:]))"
    # No credentials are read by this command and no Driver/model is constructed.
    result = subprocess.run([sys.executable, "-c", code, "check-artifact", str(target), "--expected-file",
                             str(expected), "--expected-sha256", digest], capture_output=True,
                            text=True, check=False, timeout=15)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"]
