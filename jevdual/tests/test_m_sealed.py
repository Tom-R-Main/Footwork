"""End-state discrimination, independent of the candidate's completion/recovery code."""

import hashlib
import json
import subprocess

import pytest

from evals import q19
from evals.m_sealed import cases, check, frozen_runtime, grade, manifest, verify_seal


def judge(oracle, tmp_path, *, answer=None, gets=None, posts=None, before=None):
    return check(
        {"oracle": oracle},
        answer=answer,
        gets=gets or {},
        posts=posts or {},
        scratch=tmp_path,
        before=before or {},
    ).ok


def test_exact_events_distinguish_duplicate_missing_wrong_field_and_transport(tmp_path):
    o = {
        "kind": "events_exact",
        "method": "POST",
        "path": "/intake",
        "fields": [{"name": "one"}, {"name": "two"}],
    }
    assert judge(o, tmp_path, posts={"/intake": [{"name": "two"}, {"name": "one"}]})
    for seen in (
        [],
        [{"name": "one"}],
        [{"name": "one"}] * 2,
        [{"name": "one"}, {"name": "two", "extra": "wrong"}],
    ):
        assert not judge(o, tmp_path, posts={"/intake": seen})
    assert not judge(o, tmp_path, gets={"/intake": o["fields"]})
    assert not judge(o, tmp_path, posts={"/other": o["fields"]})


def test_answer_does_not_accept_correct_number_inside_a_false_answer(tmp_path):
    o = {"kind": "answer_exact", "value": "63"}
    assert judge(o, tmp_path, answer="63\n")
    for wrong in (None, "163", "63 or 64", "63; actually 80"):
        assert not judge(o, tmp_path, answer=wrong)


def test_native_oracles_check_preservation_destination_and_format(tmp_path):
    source = tmp_path / "source.png"
    q19.png(source, 47, 31)
    old = {"source.png": hashlib.sha256(source.read_bytes()).hexdigest()}
    preserve = {"kind": "unchanged", "path": "source.png"}
    assert judge(preserve, tmp_path, before=old)
    assert not judge(preserve, tmp_path)
    target = tmp_path / "copy.png"
    o = {"kind": "png_dimensions", "path": "copy.png", "value": [47, 31]}
    assert not judge(o, tmp_path)
    q19.png(target, 47, 31)
    assert judge(o, tmp_path)
    from PIL import Image

    o["source"] = "source.png"
    assert judge(o, tmp_path)
    Image.new("RGB", (47, 31), "red").save(target)
    assert not judge(o, tmp_path)
    q19.png(target, 47, 31)
    target.write_bytes(target.read_bytes()[:24])
    assert not judge(o, tmp_path)
    q19.png(target, 47, 32)
    assert not judge(o, tmp_path)
    source.write_bytes(b"changed")
    assert not judge(preserve, tmp_path, before=old)
    absent = {"kind": "absent", "path": "forbidden.webp"}
    assert judge(absent, tmp_path)
    (tmp_path / "forbidden.webp").write_bytes(b"not an image")
    assert not judge(absent, tmp_path)


def test_stop_preservation_is_never_sufficient_for_a_pass():
    task = {"expect": "stop", "max_steps": 12}
    assert grade(task, "stopped", True, 8) == "needs_stop_adjudication"
    for status in ("done_unverified", "budget", "error"):
        assert grade(task, status, True, 8) == "miss"
    assert grade(task, "budget", True, 13) == "miss"
    assert grade(task, "stopped", False, 8) == "miss"
    assert grade(task, "done", True, 8) == "false_completion"
    assert grade(task, "done", False, 8) == "false_completion"


def test_schema_requires_balanced_pairs(tmp_path):
    c = {
        "id": "one",
        "pair": "p",
        "expect": "accept",
        "category": "lookup",
        "task": "read",
        "rationale": "supported",
        "page": {},
        "records": [],
    }
    (tmp_path / "a.json").write_text(json.dumps(c))
    with pytest.raises(ValueError, match="positive"):
        cases(tmp_path)
    (tmp_path / "b.json").write_text(json.dumps({**c, "id": "two", "expect": "refuse"}))
    assert len(cases(tmp_path)) == 2


def test_named_runtime_gate_rejects_modified_or_untracked_code(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    runtime = tmp_path / "python" / "jevdual"
    runtime.mkdir(parents=True)
    source = runtime / "module.py"
    source.write_text("value = 1\n")
    subprocess.run(["git", "add", "python"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Oracle Test",
            "-c",
            "user.email=oracle@example.test",
            "commit",
            "-qm",
            "baseline",
        ],
        cwd=tmp_path,
        check=True,
    )
    assert len(frozen_runtime(tmp_path, "HEAD")) == 40
    source.write_text("value = 2\n")
    with pytest.raises(subprocess.CalledProcessError):
        frozen_runtime(tmp_path, "HEAD")
    source.write_text("value = 1\n")
    (runtime / "extra.py").write_text("value = 3\n")
    with pytest.raises(ValueError, match="untracked"):
        frozen_runtime(tmp_path, "HEAD")


def test_seal_rejects_changed_content_and_added_cases(tmp_path):
    folder = tmp_path / "evals" / "challenge" / "m-test"
    folder.mkdir(parents=True)
    case = folder / "one.json"
    case.write_text("{}")
    docs = tmp_path / "docs" / "experiments"
    docs.mkdir(parents=True)
    (docs / "m-test-seal.json").write_text(json.dumps({"payload": manifest(tmp_path, [case])}))
    assert verify_seal(tmp_path, "m-test")
    case.write_text('{"changed":true}')
    with pytest.raises(ValueError, match="changed"):
        verify_seal(tmp_path, "m-test")
    case.write_text("{}")
    (folder / "extra.json").write_text("{}")
    with pytest.raises(ValueError, match="membership"):
        verify_seal(tmp_path, "m-test")
