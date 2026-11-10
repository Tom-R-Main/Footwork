"""Public helper boundary tests; no real credentials or network calls."""

from __future__ import annotations

import base64
import importlib.util
import json
import urllib.error
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "openrouter_media_review.py"
spec = importlib.util.spec_from_file_location("openrouter_media_review", SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    media = tmp_path / "clip.wav"
    media.write_bytes(b"RIFF-fixture-bytes")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Describe only what you hear, with uncertainty.")
    env = tmp_path / "fixture.env"
    env.write_text("OPENROUTER_API_KEY='fixture-credential-do-not-print'\n")
    out = tmp_path / "review"
    argv = ["--media", str(media), "--prompt", str(prompt), "--out", str(out)]
    return media, prompt, env, out, argv


def response(content="Two sounds."):
    return json.dumps({"id": "req-fixture", "model": "dated-provider-model", "provider": "Alibaba",
                       "usage": {"total_tokens": 23, "cost": 0.0001},
                       "choices": [{"message": {"content": content}, "finish_reason": "stop"}]}).encode()


def test_dry_run_sends_nothing_and_does_not_read_key(setup, monkeypatch, capsys):
    media, _prompt, _env, out, argv = setup
    monkeypatch.setattr(review, "_post", lambda *a: pytest.fail("dry run sent a request"))
    monkeypatch.setattr(review, "_key", lambda *a: pytest.fail("dry run read a key"))
    assert review.main(argv) == 0
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["status"] == "dry_run"
    assert manifest["media"]["bytes"] == len(media.read_bytes())
    assert manifest["requested_model"] == review.MODEL
    assert not (out / "response.json").exists()
    assert "no credential read" in capsys.readouterr().out


@pytest.mark.parametrize("suffix", [".wav", ".mp3", ".mp4"])
def test_execute_delivers_media_once_and_preserves_provenance(setup, monkeypatch, suffix, capsys):
    media, prompt, env, out, argv = setup
    target = media.with_suffix(suffix)
    media.rename(target)
    argv[1] = str(target)
    calls = []

    def post(request, timeout):
        calls.append(request)
        assert request.full_url == review.ENDPOINT and request.method == "POST"
        assert request.get_header("Authorization") == "Bearer fixture-credential-do-not-print"
        data = json.loads(request.data)
        assert data["model"] == review.MODEL and data["provider"] == {"allow_fallbacks": False}
        assert data["max_tokens"] == 2000 and data["stream"] is False
        part, text = data["messages"][0]["content"]
        assert text == {"type": "text", "text": prompt.read_text()}
        if suffix == ".mp4":
            assert part["type"] == "video_url"
            encoded = part["video_url"]["url"].removeprefix("data:video/mp4;base64,")
        else:
            assert part["type"] == "input_audio" and part["input_audio"]["format"] == suffix[1:]
            encoded = part["input_audio"]["data"]
        assert base64.b64decode(encoded) == target.read_bytes()
        return response("Two sounds. fixture-credential-do-not-print " + encoded)

    monkeypatch.setattr(review, "_post", post)
    assert review.main([*argv, "--execute", "--env-file", str(env)]) == 0
    assert len(calls) == 1
    manifest = json.loads((out / "manifest.json").read_text())
    assert json.loads((out / "request-intent.json").read_text())["status"] == "pending"
    result = json.loads((out / "response.json").read_text())
    assert manifest["returned_model"] == "dated-provider-model" and manifest["returned_provider"] == "Alibaba"
    assert manifest["perception_verified"] is False and manifest["automatic_retries"] == 0
    assert result["usage"]["cost"] == 0.0001 and "[REDACTED]" in result["content"]
    retained = "".join(p.read_text() for p in out.iterdir()) + str(capsys.readouterr())
    assert "fixture-credential-do-not-print" not in retained
    assert base64.b64encode(target.read_bytes()).decode() not in retained
    assert (out / "response.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("failure", ["http", "transport", "json", "provider_error", "empty", "unexpected"])
def test_failed_request_has_no_retry_or_upstream_leak(setup, monkeypatch, capsys, failure):
    _media, _prompt, env, out, argv = setup
    calls = []

    def fail(request, timeout):
        calls.append(request)
        if failure == "http":
            raise urllib.error.HTTPError(review.ENDPOINT, 401, "fixture-credential-do-not-print", {}, None)
        if failure == "transport":
            raise urllib.error.URLError("fixture-credential-do-not-print")
        if failure == "json":
            return b"not-json fixture-credential-do-not-print"
        if failure == "provider_error":
            return b'{"error":{"message":"fixture-credential-do-not-print"}}'
        if failure == "unexpected":
            raise ValueError("fixture-credential-do-not-print")
        return b'{"choices":[{"message":{"content":""}}]}'

    monkeypatch.setattr(review, "_post", fail)
    assert review.main([*argv, "--execute", "--env-file", str(env)]) == 1
    assert len(calls) == 1 and not (out / "response.json").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["status"] == "failed" and manifest["provider_completion"] == "unknown"
    assert "fixture-credential-do-not-print" not in (out / "manifest.json").read_text() + str(capsys.readouterr())
    if failure == "http":
        assert manifest["error"]["http_status"] == 401


@pytest.mark.parametrize("options", [
    ["--max-tokens", "0"], ["--max-tokens", "4001"], ["--timeout", "nan"],
    ["--timeout", "0"], ["--timeout", "121"], ["--max-media-bytes", "0"],
    ["--max-media-bytes", "33554433"], ["--max-media-bytes", "1"],
])
def test_invalid_bounds_never_request_or_create_output(setup, monkeypatch, options):
    _media, _prompt, env, out, argv = setup
    monkeypatch.setattr(review, "_post", lambda *a: pytest.fail("invalid input sent a request"))
    assert review.main([*argv, *options, "--execute", "--env-file", str(env)]) == 1
    assert not out.exists()


def test_redirect_is_refused_without_following():
    request = review.urllib.request.Request(review.ENDPOINT, headers={"Authorization": "Bearer fixture-secret"})
    with pytest.raises(urllib.error.HTTPError) as error:
        review._NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://other.example/")
    assert error.value.code == 302


def test_existing_output_is_preserved(setup, monkeypatch):
    _media, _prompt, env, out, argv = setup
    out.mkdir()
    (out / "manifest.json").write_text("original")
    monkeypatch.setattr(review, "_post", lambda *a: pytest.fail("existing output sent request"))
    assert review.main([*argv, "--execute", "--env-file", str(env)]) == 1
    assert (out / "manifest.json").read_text() == "original"


@pytest.mark.parametrize("kind", ["unsupported", "outside", "missing_key", "duplicate_key", "blank_prompt"])
def test_invalid_inputs_never_request(setup, monkeypatch, kind, tmp_path):
    media, prompt, env, out, argv = setup
    if kind == "unsupported":
        target = media.with_suffix(".exe")
        media.rename(target)
        argv[1] = str(target)
    elif kind == "outside":
        argv[5] = str(tmp_path.parent / "outside-project-output")
    elif kind == "missing_key":
        env.write_text("OPENROUTER_API_KEY=\n")
    elif kind == "duplicate_key":
        env.write_text("OPENROUTER_API_KEY=a\nOPENROUTER_API_KEY=b\n")
    else:
        prompt.write_text(" \n")
    monkeypatch.setattr(review, "_post", lambda *a: pytest.fail("invalid input sent request"))
    assert review.main([*argv, "--execute", "--env-file", str(env)]) == 1
    assert not out.exists()
