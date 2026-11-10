"""Public helper boundary tests; no real credentials or network calls."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import ssl
import subprocess
import sys
import time
import urllib.error
from pathlib import Path
from types import SimpleNamespace

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
    monkeypatch.setattr(review, "_request_with_deadline", lambda *a: pytest.fail("dry run sent a request"))
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

    def post(request, timeout, journal=None):
        calls.append(request)
        assert request.full_url == review.ENDPOINT and request.method == "POST"
        assert request.get_header("Authorization") == "Bearer fixture-credential-do-not-print"
        data = json.loads(request.data)
        assert data["model"] == review.MODEL and data["provider"] == {"allow_fallbacks": False}
        assert data["max_tokens"] == 2000 and data["stream"] is False
        assert data["reasoning"] == {"enabled": False}
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

    monkeypatch.setattr(review, "_request_with_deadline", post)
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


@pytest.mark.parametrize("failure", ["http", "transport", "json", "provider_error", "unexpected"])
def test_failed_request_has_no_retry_or_upstream_leak(setup, monkeypatch, capsys, failure):
    _media, _prompt, env, out, argv = setup
    calls = []

    def fail(request, timeout, journal=None):
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
        pytest.fail("unhandled fixture failure type")

    monkeypatch.setattr(review, "_request_with_deadline", fail)
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
    monkeypatch.setattr(review, "_request_with_deadline", lambda *a: pytest.fail("invalid input sent a request"))
    assert review.main([*argv, *options, "--execute", "--env-file", str(env)]) == 1
    assert not out.exists()


def test_redirect_is_refused_without_following():
    request = review.urllib.request.Request(review.ENDPOINT, headers={"Authorization": "Bearer fixture-secret"})
    with pytest.raises(urllib.error.HTTPError) as error:
        review._NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://other.example/")
    assert error.value.code == 302


def test_tls_context_loads_installed_ca_with_verification(monkeypatch):
    import certifi

    seen = []
    create = ssl.create_default_context

    def record(**kwargs):
        seen.append(kwargs)
        return create(**kwargs)

    monkeypatch.setattr(review.ssl, "create_default_context", record)
    context = review._tls_context()
    assert seen == [{"cafile": certifi.where()}]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True


def test_tls_context_falls_back_without_disabling_verification(monkeypatch):
    seen = []
    create = ssl.create_default_context

    def record(**kwargs):
        seen.append(kwargs)
        return create(**kwargs)

    monkeypatch.setitem(sys.modules, "certifi", None)
    monkeypatch.setattr(review.ssl, "create_default_context", record)
    context = review._tls_context()
    assert seen == [{}]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True


def test_post_uses_verified_https_handler_and_no_redirect(monkeypatch):
    context = review._tls_context()
    monkeypatch.setattr(review, "_tls_context", lambda: context)
    calls = []
    request = review.urllib.request.Request(review.ENDPOINT)

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, limit):
            assert limit == review.MAX_RESPONSE_BYTES + 1
            return b"{}"

    class Opener:
        def open(self, req, timeout):
            assert req is request and timeout == 9
            calls.append("open")
            return Reply()

    def build(*handlers):
        assert any(isinstance(h, review._NoRedirect) for h in handlers)
        https = [h for h in handlers if isinstance(h, review.urllib.request.HTTPSHandler)]
        assert len(https) == 1 and https[0]._context is context
        return Opener()

    monkeypatch.setattr(review.urllib.request, "build_opener", build)
    assert review._post(request, 9) == b"{}" and calls == ["open"]


@pytest.mark.parametrize("wrapped", [False, True])
def test_tls_certificate_failure_is_safe_and_not_sent(setup, monkeypatch, capsys, wrapped):
    _media, _prompt, env, out, argv = setup
    calls = []
    certificate_error = review._TLSHandshakeVerificationError(20)

    def fail(request, timeout, journal=None):
        calls.append(request)
        if wrapped:
            raise urllib.error.URLError(certificate_error)
        raise certificate_error

    monkeypatch.setattr(review, "_request_with_deadline", fail)
    assert review.main([*argv, "--execute", "--env-file", str(env)]) == 1
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["request_attempted"] is True and manifest["provider_completion"] == "not_sent_tls_handshake"
    assert manifest["error"]["ssl_verify_code"] == 20
    assert manifest["error"]["application_request_sent"] is False
    assert len(calls) == 1
    assert "fixture-credential-do-not-print" not in (out / "manifest.json").read_text() + str(capsys.readouterr())


def test_url_error_text_does_not_establish_tls_non_delivery():
    error = review._transport_error(urllib.error.URLError("CERTIFICATE_VERIFY_FAILED fixture-secret"))
    assert error["application_request_sent"] == "unknown"
    assert error["kind"] == "transport_or_filesystem_error" and "fixture-secret" not in str(error)


def test_connection_labels_only_certificate_failure_at_connect(monkeypatch):
    certificate_error = ssl.SSLCertVerificationError(1, "fixture-secret")
    certificate_error.verify_code = 20

    def fail(self):
        raise certificate_error

    monkeypatch.setattr(review.http.client.HTTPSConnection, "connect", fail)
    connection = review._VerifiedHTTPSConnection("example.invalid", context=review._tls_context())
    with pytest.raises(review._TLSHandshakeVerificationError) as error:
        connection.connect()
    assert error.value.verify_code == 20 and "fixture-secret" not in str(error.value)


def test_unqualified_certificate_error_retains_delivery_uncertainty():
    error = review._transport_error(ssl.SSLCertVerificationError(1, "fixture-secret"))
    assert error["application_request_sent"] == "unknown"
    assert "fixture-secret" not in str(error)


def test_verified_handler_uses_handshake_aware_connection(monkeypatch):
    context = review._tls_context()
    handler = review._VerifiedHTTPSHandler(context=context)
    request = review.urllib.request.Request(review.ENDPOINT)
    calls = []

    def open_connection(connection, req, **kwargs):
        calls.append((connection, req, kwargs))
        return "fixture response"

    monkeypatch.setattr(handler, "do_open", open_connection)
    assert handler.https_open(request) == "fixture response"
    assert calls == [(review._VerifiedHTTPSConnection, request, {"context": context})]


def test_total_deadline_kills_and_reaps_real_slow_drip_child(monkeypatch):
    actual_popen = subprocess.Popen
    children = []

    def start(_argv, **kwargs):
        # A real local process consumes private stdin, then keeps emitting bytes. No network.
        child = actual_popen([sys.executable, "-c", (
            "import sys,time;sys.stdin.buffer.read();"
            "[(sys.stdout.write(' '),sys.stdout.flush(),time.sleep(.05)) for _ in range(100)]")], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(review.subprocess, "Popen", start)
    request = review.urllib.request.Request(review.ENDPOINT, data=b"{}", headers={"Authorization": "Bearer fixture"})
    started = time.monotonic()
    with pytest.raises(review._TransportFailure) as error:
        review._request_with_deadline(request, .15)
    assert time.monotonic() - started < 2
    assert error.value.error["kind"] == "total_request_deadline"
    assert error.value.error["application_request_sent"] == "unknown"
    assert error.value.error["child_reaped"] is True
    assert len(children) == 1 and children[0].poll() is not None


def test_isolated_exchange_uses_private_stdin_not_arguments(monkeypatch, tmp_path):
    secret = "fixture-credential-do-not-print"
    request = review.urllib.request.Request(review.ENDPOINT, data=b'{"payload":"fixture-media"}',
                                          headers={"Authorization": f"Bearer {secret}"})
    calls = []

    class Child:
        returncode = 0
        pid = 45678

        def communicate(self, input=None, timeout=None):
            data = json.loads(input)
            assert data["authorization"] == f"Bearer {secret}" and data["body"] == request.data.decode()
            assert 0 < timeout <= 1
            calls.append("communicate")
            return json.dumps({"ok": True, "response": base64.b64encode(b"{}").decode()}).encode(), None

    def start(argv, **kwargs):
        assert secret not in str(argv) and "fixture-media" not in str(argv)
        assert argv[-1] == "--transport-child" and "-I" in argv
        assert kwargs["stdin"] == subprocess.PIPE and kwargs["stderr"] == subprocess.DEVNULL
        assert "env" not in kwargs
        calls.append("start")
        return Child()

    monkeypatch.setattr(review.subprocess, "Popen", start)
    assert review._request_with_deadline(request, 1, tmp_path) == b"{}"
    assert calls == ["start", "communicate"]
    assert json.loads((tmp_path / "transport-child.json").read_text())["pid"] == 45678


def test_child_keeps_diagnostics_safe_and_handshake_scope(monkeypatch):
    data = {"body": "{}", "authorization": "Bearer fixture-secret", "timeout": 1}
    monkeypatch.setattr(review.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(data).encode())))
    stdout = io.StringIO()
    monkeypatch.setattr(review.sys, "stdout", stdout)

    def fail(request, timeout, journal=None):
        raise urllib.error.URLError(review._TLSHandshakeVerificationError(20))

    monkeypatch.setattr(review, "_post", fail)
    assert review._transport_child() == 0
    result = json.loads(stdout.getvalue())
    assert result["ok"] is False and result["error"]["phase"] == "tls_handshake"
    assert result["error"]["application_request_sent"] is False
    assert "fixture-secret" not in stdout.getvalue()


def test_total_deadline_public_result_preserves_unknown_completion(setup, monkeypatch):
    _media, _prompt, env, out, argv = setup
    calls = []

    def deadline(*args):
        calls.append(args)
        raise review._TransportFailure({"kind": "total_request_deadline", "phase": "transport_exchange",
                                       "child_reaped": True, "application_request_sent": "unknown",
                                       "summary": "total request deadline reached; no retry"})

    monkeypatch.setattr(review, "_request_with_deadline", deadline)
    assert review.main([*argv, "--execute", "--env-file", str(env)]) == 1
    result = json.loads((out / "manifest.json").read_text())
    assert result["provider_completion"] == "unknown" and result["error"]["child_reaped"] is True
    assert result["timeout_kind"] == "total_transport_exchange" and len(calls) == 1


def test_cleanup_failure_is_explicit_and_not_confirmed(monkeypatch):
    calls = []

    class Child:
        pid = 45678

        def communicate(self, input=None, timeout=None):
            calls.append("communicate")
            raise subprocess.TimeoutExpired("fixture-child", timeout)

        def poll(self):
            return None

        def kill(self):
            calls.append("kill")

    monkeypatch.setattr(review.subprocess, "Popen", lambda *args, **kwargs: Child())
    request = review.urllib.request.Request(review.ENDPOINT, data=b"{}")
    with pytest.raises(review._TransportFailure) as error:
        review._request_with_deadline(request, 1)
    assert error.value.error["child_reaped"] is False
    assert error.value.error["cleanup_pending_pid"] == 45678
    assert calls == ["communicate", "kill", "communicate"]


def test_interruption_kills_and_reaps_child_before_propagating(monkeypatch):
    calls = []

    class Child:
        returncode = None

        def communicate(self, input=None, timeout=None):
            calls.append("communicate")
            if len(calls) == 1:
                raise KeyboardInterrupt
            return b"", None

        def poll(self):
            return self.returncode

        def kill(self):
            calls.append("kill")
            self.returncode = -9

    child = Child()
    monkeypatch.setattr(review.subprocess, "Popen", lambda *args, **kwargs: child)
    request = review.urllib.request.Request(review.ENDPOINT, data=b"{}")
    with pytest.raises(KeyboardInterrupt):
        review._request_with_deadline(request, 1)
    assert calls == ["communicate", "kill", "communicate"] and child.returncode == -9


@pytest.mark.parametrize("mode", ["off", "provider-default"])
def test_explicit_reasoning_mode_payload_and_manifest(setup, monkeypatch, mode):
    _media, _prompt, env, out, argv = setup
    calls = []

    def post(request, timeout, journal=None):
        payload = json.loads(request.data)
        if mode == "off":
            assert payload["reasoning"] == {"enabled": False}
        else:
            assert "reasoning" not in payload
        calls.append(request)
        return response()

    monkeypatch.setattr(review, "_request_with_deadline", post)
    assert review.main([*argv, "--execute", "--env-file", str(env), "--reasoning", mode]) == 0
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["reasoning_mode"] == mode
    assert manifest["reasoning_request"] == ({"enabled": False} if mode == "off" else None)
    assert manifest["budget_report"]["reasoning_disable_status"] == ("unknown" if mode == "off" else "not_requested")
    assert len(calls) == 1


@pytest.mark.parametrize("tokens,status,overrun", [(0, "reported_zero", False), (20, "not_honored", True)])
def test_provider_reasoning_and_completion_overrun_visible_without_retry(setup, monkeypatch, capsys,
                                                                       tokens, status, overrun):
    _media, _prompt, env, out, argv = setup
    calls = []

    def post(*args):
        calls.append(args)
        result = json.loads(response())
        result["usage"] = {"completion_tokens": 30 if overrun else 5,
                           "completion_tokens_details": {"reasoning_tokens": tokens}, "cost": .003}
        return json.dumps(result).encode()

    monkeypatch.setattr(review, "_request_with_deadline", post)
    assert review.main([*argv, "--execute", "--env-file", str(env), "--max-tokens", "10"]) == 0
    budget = json.loads((out / "manifest.json").read_text())["budget_report"]
    assert budget["reported_reasoning_tokens"] == tokens and budget["reasoning_disable_status"] == status
    assert budget["completion_tokens_exceed_requested_max"] is overrun
    assert budget["hard_spend_cap_enforced"] is False and budget["reported_cost"] == .003
    assert len(calls) == 1
    if overrun:
        assert "Warning:" in capsys.readouterr().err


@pytest.mark.parametrize("usage", [None, {}, {"completion_tokens": True},
                                  {"completion_tokens_details": {"reasoning_tokens": -1}},
                                  {"completion_tokens_details": "invalid"}])
def test_missing_or_malformed_usage_does_not_prove_disable_or_budget(usage):
    budget = review._budget_report(usage, 500, "off")
    assert budget["reasoning_disable_status"] == "unknown"
    assert budget["completion_tokens_exceed_requested_max"] == "unknown"
    assert budget["hard_spend_cap_enforced"] is False


@pytest.mark.parametrize("content", [None, ""])
def test_no_final_text_preserves_length_usage_and_does_not_retry(setup, monkeypatch, content):
    _media, _prompt, env, out, argv = setup
    calls = []

    def post(*args):
        calls.append(args)
        data = json.loads(response())
        data["choices"][0] = {"message": {"content": content}, "finish_reason": "length"}
        data["usage"] = {"completion_tokens": 30, "completion_tokens_details": {"reasoning_tokens": 30}, "cost": .003}
        return json.dumps(data).encode()

    monkeypatch.setattr(review, "_request_with_deadline", post)
    assert review.main([*argv, "--execute", "--env-file", str(env), "--max-tokens", "10"]) == 1
    manifest = json.loads((out / "manifest.json").read_text())
    result = json.loads((out / "response.json").read_text())
    assert manifest["status"] == "response_no_text" and manifest["provider_completion"] == "response_received"
    assert result["finish_reason"] == "length" and result["usage"]["cost"] == .003
    assert result["budget_report"]["reasoning_disable_status"] == "not_honored" and len(calls) == 1


@pytest.mark.parametrize("suffix", [".wav", ".mp3"])
def test_mp4_audio_sidecar_delivered_and_hashed_without_sync_claim(setup, monkeypatch, suffix, capsys):
    media, prompt, env, out, argv = setup
    video = media.with_suffix(".mp4")
    media.rename(video)
    argv[1] = str(video)
    sidecar = video.parent / ("sound" + suffix)
    sidecar.write_bytes(b"different-sidecar-audio-bytes")
    encoded = base64.b64encode(sidecar.read_bytes()).decode()
    calls = []

    def post(request, timeout, journal=None):
        calls.append(request)
        parts = json.loads(request.data)["messages"][0]["content"]
        assert len(parts) == 3 and parts[0]["type"] == "video_url"
        assert parts[1] == {"type": "input_audio", "input_audio": {"data": encoded, "format": suffix[1:]}}
        assert parts[2] == {"type": "text", "text": prompt.read_text()}
        return response("Audio review " + encoded + " fixture-credential-do-not-print")

    monkeypatch.setattr(review, "_request_with_deadline", post)
    limit = len(video.read_bytes()) + len(sidecar.read_bytes())
    assert review.main([*argv, "--execute", "--env-file", str(env), "--audio-sidecar", str(sidecar),
                        "--max-media-bytes", str(limit)]) == 0
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["aggregate_media_bytes"] == limit
    assert manifest["audio_sidecar"]["bytes"] == len(sidecar.read_bytes())
    assert manifest["audio_sidecar"]["sha256"] == review.hashlib.sha256(sidecar.read_bytes()).hexdigest()
    assert manifest["audio_sidecar"]["mime_type"] == review.FORMATS[suffix]
    assert manifest["audio_sidecar"]["synchronization_verified"] is False and len(calls) == 1
    retained = "".join(p.read_text() for p in out.iterdir()) + str(capsys.readouterr())
    assert encoded not in retained and "fixture-credential-do-not-print" not in retained


@pytest.mark.parametrize("kind", ["primary_audio", "wrong_format", "missing", "aggregate_limit"])
def test_invalid_sidecar_refuses_before_key_or_request(setup, monkeypatch, kind):
    media, _prompt, env, out, argv = setup
    sidecar = media.parent / "sound.wav"
    sidecar.write_bytes(b"sidecar-fixture")
    options = ["--audio-sidecar", str(sidecar)]
    if kind != "primary_audio":
        video = media.with_suffix(".mp4")
        media.rename(video)
        argv[1] = str(video)
    if kind == "wrong_format":
        target = sidecar.with_suffix(".mp4")
        sidecar.rename(target)
        options[1] = str(target)
    elif kind == "missing":
        sidecar.unlink()
    elif kind == "aggregate_limit":
        options += ["--max-media-bytes", str(len(video.read_bytes()) + len(sidecar.read_bytes()) - 1)]
    monkeypatch.setattr(review, "_key", lambda *a: pytest.fail("invalid media read a key"))
    monkeypatch.setattr(review, "_request_with_deadline", lambda *a: pytest.fail("invalid media sent request"))
    assert review.main([*argv, "--execute", "--env-file", str(env), *options]) == 1
    assert not out.exists()


def test_existing_output_is_preserved(setup, monkeypatch):
    _media, _prompt, env, out, argv = setup
    out.mkdir()
    (out / "manifest.json").write_text("original")
    monkeypatch.setattr(review, "_request_with_deadline", lambda *a: pytest.fail("existing output sent request"))
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
    monkeypatch.setattr(review, "_request_with_deadline", lambda *a: pytest.fail("invalid input sent request"))
    assert review.main([*argv, "--execute", "--env-file", str(env)]) == 1
    assert not out.exists()
