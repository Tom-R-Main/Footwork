"""Review explicit local media through one pinned OpenRouter request; dry-run by default.

This is an experimental operator helper, not proof that the model perceived the media correctly.
Never retain request bodies or Authorization headers. No automatic retries or redirects.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import math
import os
import signal
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MODEL = "qwen/qwen3.8-omni-flash"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_MEDIA_BYTES = 32 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
CLEANUP_GRACE_SECONDS = 2
FORMATS = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".mp4": "video/mp4"}


class ReviewError(Exception):
    """Safe, preselected diagnostic text only."""


class _TransportFailure(ReviewError):
    def __init__(self, error: dict[str, Any]):
        super().__init__(error["summary"])
        self.error = error


def _bounded_read(path: Path, cap: int, label: str) -> bytes:
    try:
        if not path.is_file() or path.stat().st_size > cap:
            raise ReviewError(f"{label} must be a regular file within its byte limit")
        with path.open("rb") as stream:
            data = stream.read(cap + 1)
    except OSError:
        raise ReviewError(f"cannot read {label}") from None
    if not data or len(data) > cap:
        raise ReviewError(f"{label} must be nonempty and within its byte limit")
    return data


def _key(path: Path | None) -> str:
    if path is None:
        raise ReviewError("--execute requires --env-file with OPENROUTER_API_KEY")
    try:
        text = _bounded_read(path, 64 * 1024, "credential file").decode("utf-8")
    except UnicodeError:
        raise ReviewError("credential file must be UTF-8") from None
    values = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "OPENROUTER_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values.append(value)
    if len(values) != 1 or not values[0] or any(not 33 <= ord(c) <= 126 for c in values[0]):
        raise ReviewError("credential file requires exactly one nonempty OPENROUTER_API_KEY")
    return values[0]


def _redact(value: Any, key: str, encoded_media: str = "", encoded_sidecar: str = "") -> Any:
    if isinstance(value, str):
        for sensitive in (key, encoded_media, encoded_sidecar):
            if sensitive:
                value = value.replace(sensitive, "[REDACTED]")
        return value
    if isinstance(value, dict):
        return {_redact(k, key, encoded_media, encoded_sidecar): _redact(v, key, encoded_media, encoded_sidecar)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, key, encoded_media, encoded_sidecar) for v in value]
    return value


def _write(path: Path, value: Any, key: str, encoded_media: str = "", encoded_sidecar: str = "") -> None:
    data = json.dumps(_redact(value, key, encoded_media, encoded_sidecar), ensure_ascii=False, indent=2) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(data)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def _tls_context() -> ssl.SSLContext:
    """Keep verification enabled with an installed CA bundle; never alter global trust."""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


class _TLSHandshakeVerificationError(OSError):
    def __init__(self, verify_code: int | None):
        super().__init__("TLS handshake certificate verification failed")
        self.verify_code = verify_code


class _VerifiedHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        try:
            super().connect()
        except ssl.SSLCertVerificationError as exc:
            code = getattr(exc, "verify_code", None)
            raise _TLSHandshakeVerificationError(code if isinstance(code, int) else None) from None


class _VerifiedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(_VerifiedHTTPSConnection, request, context=self._context)


def _transport_error(exc: BaseException) -> dict[str, Any]:
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(reason, (_TLSHandshakeVerificationError, ssl.SSLCertVerificationError)):
        handshake = isinstance(reason, _TLSHandshakeVerificationError)
        error = {"kind": "tls_certificate_verification_error", "exception_type": "SSLCertVerificationError",
                 "application_request_sent": False if handshake else "unknown",
                 "summary": "TLS certificate verification failed; no retry"}
        code = getattr(reason, "verify_code", None)
        if isinstance(code, int):
            error["ssl_verify_code"] = code
        return error
    return {"kind": "transport_or_filesystem_error", "application_request_sent": "unknown",
            "summary": "request or local I/O failed; no retry"}


def _post(request: urllib.request.Request, timeout: float) -> bytes:
    opener = urllib.request.build_opener(_NoRedirect(), _VerifiedHTTPSHandler(context=_tls_context()))
    with opener.open(request, timeout=timeout) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ReviewError("provider response exceeded byte limit")
    return data


def _cleanup_child(child: subprocess.Popen) -> bool:
    """Kill and reap this run's sole transport process; do not claim success on failure."""
    try:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=CLEANUP_GRACE_SECONDS)
        return child.poll() is not None
    except (OSError, subprocess.TimeoutExpired):
        return False


def _request_with_deadline(request: urllib.request.Request, timeout: float, journal: Path | None = None) -> bytes:
    started = time.monotonic()
    # The helper supplies authentication/media only over stdin, never argv or a new environment entry.
    envelope = json.dumps({"body": request.data.decode("utf-8"),
                           "authorization": request.get_header("Authorization"), "timeout": timeout}).encode()
    child = subprocess.Popen(
        [sys.executable, "-I", str(Path(__file__).resolve()), "--transport-child"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    previous_handler = None
    handler_installed = False

    def interrupted(_signum, _frame):
        raise KeyboardInterrupt

    try:
        if journal is not None:
            _write(journal / "transport-child.json", {"pid": child.pid,
                   "started_at": datetime.now(UTC).isoformat(), "scope": "single transport child",
                   "deadline_seconds": timeout, "cleanup_grace_seconds": CLEANUP_GRACE_SECONDS}, "")
        previous_handler = signal.signal(signal.SIGTERM, interrupted)
        handler_installed = True
        remaining = max(0, timeout - (time.monotonic() - started))
        result, _ = child.communicate(input=envelope, timeout=remaining)
    except subprocess.TimeoutExpired:
        reaped = _cleanup_child(child)
        error = {"kind": "total_request_deadline", "phase": "transport_exchange",
                 "application_request_sent": "unknown", "child_reaped": reaped,
                 "summary": "total request deadline reached; remote completion unknown; no retry"}
        if not reaped:
            error["cleanup_pending_pid"] = child.pid
        raise _TransportFailure(error) from None
    except BaseException:
        reaped = _cleanup_child(child)
        if not reaped:
            raise _TransportFailure({"kind": "transport_cleanup_failed", "phase": "transport_cleanup",
                                     "application_request_sent": "unknown", "child_reaped": False,
                                     "cleanup_pending_pid": child.pid,
                                     "summary": "transport interruption cleanup unconfirmed; no retry"}) from None
        raise
    finally:
        if handler_installed:
            signal.signal(signal.SIGTERM, previous_handler)
    if child.returncode != 0:
        raise ReviewError("isolated transport exited without a result; remote completion unknown; no retry")
    try:
        data = json.loads(result)
        if data.get("ok") is not True:
            raise _TransportFailure(data["error"])
        return base64.b64decode(data["response"], validate=True)
    except _TransportFailure:
        raise
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ReviewError("isolated transport returned invalid data; no retry") from None


def _transport_child() -> int:
    """Private subprocess protocol; only the parent consumes stdout, and stderr is discarded."""
    try:
        raw = sys.stdin.buffer.read(MAX_MEDIA_BYTES * 2 + 128 * 1024 + 1)
        if len(raw) > MAX_MEDIA_BYTES * 2 + 128 * 1024:
            raise ReviewError("transport input exceeded byte limit")
        data = json.loads(raw)
        request = urllib.request.Request(
            ENDPOINT, data=data["body"].encode("utf-8"),
            headers={"Authorization": data["authorization"], "Content-Type": "application/json"}, method="POST",
        )
        response = _post(request, data["timeout"])
        result = {"ok": True, "response": base64.b64encode(response).decode("ascii")}
    except urllib.error.HTTPError as exc:
        result = {"ok": False, "error": {"kind": "http_error", "http_status": exc.code,
                  "phase": "http_response", "summary": "provider HTTP request failed; no retry"}}
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        error = _transport_error(exc)
        error["phase"] = "tls_handshake" if error.get("application_request_sent") is False else "socket_io"
        result = {"ok": False, "error": error}
    except Exception:  # noqa: BLE001 -- subprocess must not print payload-bearing exceptions
        result = {"ok": False, "error": {"kind": "transport_child_error", "phase": "transport_exchange",
                  "summary": "isolated transport failed; no retry"}}
    sys.stdout.write(json.dumps(result))
    return 0


def _payload(media: bytes, suffix: str, prompt: str, max_tokens: int, *,
             sidecar: tuple[bytes, str] | None = None, reasoning: str = "off") -> dict[str, Any]:
    encoded = base64.b64encode(media).decode("ascii")
    part = (
        {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{encoded}"}}
        if suffix == ".mp4" else
        {"type": "input_audio", "input_audio": {"data": encoded, "format": suffix[1:]}}
    )
    parts = [part]
    if sidecar is not None:
        audio, audio_suffix = sidecar
        parts.append({"type": "input_audio", "input_audio": {
            "data": base64.b64encode(audio).decode("ascii"), "format": audio_suffix[1:]}})
    parts.append({"type": "text", "text": prompt})
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": parts}],
        "max_tokens": max_tokens,
        "provider": {"allow_fallbacks": False},
        "stream": False,
    }
    if reasoning == "off":
        payload["reasoning"] = {"enabled": False}
    return payload


def _budget_report(usage: Any, requested: int, reasoning: str) -> dict[str, Any]:
    usage = usage if isinstance(usage, dict) else {}
    details = usage.get("completion_tokens_details")
    details = details if isinstance(details, dict) else {}

    def count(value):
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

    reasoning_tokens = count(details.get("reasoning_tokens"))
    completion_tokens = count(usage.get("completion_tokens"))
    disable_status = "not_requested" if reasoning == "provider-default" else "unknown"
    if reasoning == "off" and reasoning_tokens is not None:
        disable_status = "reported_zero" if reasoning_tokens == 0 else "not_honored"
    cost = usage.get("cost")
    cost = cost if isinstance(cost, (float, int)) and not isinstance(cost, bool) and math.isfinite(cost) else None
    return {"reasoning_disable_status": disable_status, "reported_reasoning_tokens": reasoning_tokens,
            "reported_completion_tokens": completion_tokens, "reported_cost": cost,
            "completion_tokens_exceed_requested_max": (
                completion_tokens > requested if completion_tokens is not None else "unknown"),
            "hard_spend_cap_enforced": False}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--media", type=Path, required=True)
    p.add_argument("--prompt", type=Path, required=True)
    p.add_argument("--audio-sidecar", type=Path, help="explicit WAV/MP3 alongside MP4; pairing is caller-owned")
    p.add_argument("--out", type=Path, required=True, help="new directory inside this project")
    p.add_argument("--env-file", type=Path, help="explicit local dotenv file; never evaluated as shell")
    p.add_argument("--max-media-bytes", type=int, default=16 * 1024 * 1024, help="aggregate primary + sidecar byte limit")
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--timeout", type=float, default=60, help="total transport deadline; cleanup may add up to 2 seconds")
    p.add_argument("--reasoning", choices=("off", "provider-default"), default="off",
                   help="default off requests reasoning disabled; provider compliance must be checked")
    p.add_argument("--execute", action="store_true", help="send exactly one paid request; default is dry-run")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    out = None
    manifest = None
    key = ""
    encoded_media = ""
    encoded_sidecar = ""
    request_attempted = False
    try:
        if not 1 <= args.max_media_bytes <= MAX_MEDIA_BYTES:
            raise ReviewError("--max-media-bytes must be between 1 and 33554432")
        if not 1 <= args.max_tokens <= 4000:
            raise ReviewError("--max-tokens must be between 1 and 4000")
        if not math.isfinite(args.timeout) or not 1 <= args.timeout <= 120:
            raise ReviewError("--timeout must be finite and between 1 and 120 seconds")
        out = args.out.resolve()
        if not out.is_relative_to(PROJECT_ROOT) or out == PROJECT_ROOT or out.exists():
            raise ReviewError("--out must be a new directory inside this project")
        suffix = args.media.suffix.lower()
        if suffix not in FORMATS:
            raise ReviewError("media must be WAV, MP3 or MP4")
        audio_suffix = args.audio_sidecar.suffix.lower() if args.audio_sidecar is not None else None
        if args.audio_sidecar is not None and (suffix != ".mp4" or audio_suffix not in {".wav", ".mp3"}):
            raise ReviewError("--audio-sidecar requires MP4 primary media and a WAV or MP3 sidecar")
        media = _bounded_read(args.media, args.max_media_bytes, "media")
        audio = (_bounded_read(args.audio_sidecar, args.max_media_bytes - len(media), "audio sidecar")
                 if args.audio_sidecar is not None else None)
        encoded_media = base64.b64encode(media).decode("ascii")
        encoded_sidecar = base64.b64encode(audio).decode("ascii") if audio is not None else ""
        prompt_bytes = _bounded_read(args.prompt, 32 * 1024, "prompt")
        try:
            prompt = prompt_bytes.decode("utf-8")
        except UnicodeError:
            raise ReviewError("prompt must be UTF-8") from None
        if not prompt.strip():
            raise ReviewError("prompt must contain non-whitespace text")
        if args.execute:
            key = _key(args.env_file)
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "status": "pending" if args.execute else "dry_run",
            "media": {"filename": args.media.name, "sha256": hashlib.sha256(media).hexdigest(),
                      "bytes": len(media), "mime_type": FORMATS[suffix]},
            "audio_sidecar": ({"filename": args.audio_sidecar.name, "sha256": hashlib.sha256(audio).hexdigest(),
                               "bytes": len(audio), "mime_type": FORMATS[audio_suffix],
                               "association": "caller_supplied", "synchronization_verified": False}
                              if audio is not None else None),
            "aggregate_media_bytes": len(media) + (len(audio) if audio is not None else 0),
            "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
            "requested_model": MODEL,
            "transport": "openrouter_chat_completions",
            "endpoint": ENDPOINT,
            "max_tokens": args.max_tokens,
            "reasoning_mode": args.reasoning,
            "reasoning_request": {"enabled": False} if args.reasoning == "off" else None,
            "timeout_seconds": args.timeout,
            "timeout_kind": "total_transport_exchange",
            "cleanup_grace_seconds": CLEANUP_GRACE_SECONDS,
            "automatic_retries": 0,
            "perception_verified": False,
        }
        out.mkdir(mode=0o700, parents=True, exist_ok=False)
        if not args.execute:
            _write(out / "manifest.json", manifest, key, encoded_media, encoded_sidecar)
            print("Dry-run: media validated; no credential read or provider request sent.")
            return 0
        request = urllib.request.Request(
            ENDPOINT, data=json.dumps(_payload(media, suffix, prompt, args.max_tokens,
                sidecar=(audio, audio_suffix) if audio is not None else None, reasoning=args.reasoning)).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST",
        )
        _write(out / "request-intent.json", manifest, key, encoded_media, encoded_sidecar)
        request_attempted = True
        try:
            response = json.loads(_request_with_deadline(request, args.timeout, out))
        except (json.JSONDecodeError, UnicodeError):
            raise ReviewError("provider returned invalid JSON") from None
        if not isinstance(response, dict) or "error" in response:
            raise ReviewError("provider returned an error or invalid response shape")
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ReviewError("provider response has no completion choice")
        message = choices[0].get("message")
        if not isinstance(message, dict) or (message.get("content") is not None
                                             and not isinstance(message.get("content"), str)):
            raise ReviewError("provider response has invalid message content")
        has_text = isinstance(message.get("content"), str) and bool(message["content"].strip())
        result = {
            "content": message.get("content"), "usage": response.get("usage"),
            "model": response.get("model"), "provider": response.get("provider"),
            "id": response.get("id"), "finish_reason": choices[0].get("finish_reason"),
        }
        budget = _budget_report(response.get("usage"), args.max_tokens, args.reasoning)
        result["budget_report"] = budget
        manifest.update(status="response_received" if has_text else "response_no_text",
                        provider_completion="response_received", request_attempted=True, returned_model=response.get("model"),
                        returned_provider=response.get("provider"), response_id=response.get("id"), budget_report=budget)
        _write(out / "response.json", result, key, encoded_media, encoded_sidecar)
        _write(out / "manifest.json", manifest, key, encoded_media, encoded_sidecar)
        if budget["reasoning_disable_status"] == "not_honored":
            print("Warning: provider reported reasoning tokens despite disable request; no retry.", file=sys.stderr)
        if budget["completion_tokens_exceed_requested_max"] is True:
            print("Warning: reported completion tokens exceed requested maximum; no hard spend cap.", file=sys.stderr)
        print("One provider response saved; media perception remains unverified." if has_text
              else "Provider response saved without final text; usage retained; no retry.")
        return 0 if has_text else 1
    except _TransportFailure as exc:
        error = exc.error
    except KeyboardInterrupt:
        error = {"kind": "interrupted", "phase": "transport_exchange",
                 "summary": "media review interrupted; remote completion unknown; no retry"}
    except urllib.error.HTTPError as exc:
        error = {"kind": "http_error", "http_status": exc.code, "summary": "provider HTTP request failed; no retry"}
    except ReviewError as exc:
        error = {"kind": "validation_or_response_error", "summary": str(exc)}
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        error = _transport_error(exc)
    except Exception:  # noqa: BLE001 -- final CLI boundary must not expose headers in library exceptions
        # Never expose a library exception that could contain request headers or response bytes.
        error = {"kind": "unexpected_error", "summary": "media review failed; no retry"}
    if manifest is not None and out is not None and out.is_dir():
        completion = "unknown" if request_attempted else "not_attempted"
        if error.get("application_request_sent") is False:
            completion = "not_sent_tls_handshake"
        manifest.update(status="failed", request_attempted=request_attempted,
                        provider_completion=completion, error=error)
        try:
            _write(out / "manifest.json", manifest, key, encoded_media, encoded_sidecar)
        except OSError:
            pass
    print(json.dumps(error), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(_transport_child() if sys.argv[1:] == ["--transport-child"] else main())
