"""Review explicit local media through one pinned OpenRouter request; dry-run by default.

This is an experimental operator helper, not proof that the model perceived the media correctly.
Never retain request bodies or Authorization headers. No automatic retries or redirects.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import sys
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
FORMATS = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".mp4": "video/mp4"}


class ReviewError(Exception):
    """Safe, preselected diagnostic text only."""


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


def _redact(value: Any, key: str, encoded_media: str = "") -> Any:
    if isinstance(value, str):
        for sensitive in (key, encoded_media):
            if sensitive:
                value = value.replace(sensitive, "[REDACTED]")
        return value
    if isinstance(value, dict):
        return {_redact(k, key, encoded_media): _redact(v, key, encoded_media) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, key, encoded_media) for v in value]
    return value


def _write(path: Path, value: Any, key: str, encoded_media: str = "") -> None:
    data = json.dumps(_redact(value, key, encoded_media), ensure_ascii=False, indent=2) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(data)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def _post(request: urllib.request.Request, timeout: float) -> bytes:
    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(request, timeout=timeout) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ReviewError("provider response exceeded byte limit")
    return data


def _payload(media: bytes, suffix: str, prompt: str, max_tokens: int) -> dict[str, Any]:
    encoded = base64.b64encode(media).decode("ascii")
    part = (
        {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{encoded}"}}
        if suffix == ".mp4" else
        {"type": "input_audio", "input_audio": {"data": encoded, "format": suffix[1:]}}
    )
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": [part, {"type": "text", "text": prompt}]}],
        "max_tokens": max_tokens,
        "provider": {"allow_fallbacks": False},
        "stream": False,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--media", type=Path, required=True)
    p.add_argument("--prompt", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True, help="new directory inside this project")
    p.add_argument("--env-file", type=Path, help="explicit local dotenv file; never evaluated as shell")
    p.add_argument("--max-media-bytes", type=int, default=16 * 1024 * 1024)
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--timeout", type=float, default=60)
    p.add_argument("--execute", action="store_true", help="send exactly one paid request; default is dry-run")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    out = None
    manifest = None
    key = ""
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
        media = _bounded_read(args.media, args.max_media_bytes, "media")
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
            "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
            "requested_model": MODEL,
            "transport": "openrouter_chat_completions",
            "endpoint": ENDPOINT,
            "max_tokens": args.max_tokens,
            "timeout_seconds": args.timeout,
            "automatic_retries": 0,
            "perception_verified": False,
        }
        out.mkdir(mode=0o700, parents=True, exist_ok=False)
        if not args.execute:
            _write(out / "manifest.json", manifest, key)
            print("Dry-run: media validated; no credential read or provider request sent.")
            return 0
        request = urllib.request.Request(
            ENDPOINT, data=json.dumps(_payload(media, suffix, prompt, args.max_tokens)).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST",
        )
        _write(out / "request-intent.json", manifest, key)
        request_attempted = True
        try:
            response = json.loads(_post(request, args.timeout))
        except (json.JSONDecodeError, UnicodeError):
            raise ReviewError("provider returned invalid JSON") from None
        if not isinstance(response, dict) or "error" in response:
            raise ReviewError("provider returned an error or invalid response shape")
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ReviewError("provider response has no completion choice")
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str) or not message["content"].strip():
            raise ReviewError("provider response has no text content")
        result = {
            "content": message["content"], "usage": response.get("usage"),
            "model": response.get("model"), "provider": response.get("provider"),
            "id": response.get("id"), "finish_reason": choices[0].get("finish_reason"),
        }
        manifest.update(status="response_received", request_attempted=True, returned_model=response.get("model"),
                        returned_provider=response.get("provider"), response_id=response.get("id"))
        _write(out / "response.json", result, key, base64.b64encode(media).decode("ascii"))
        _write(out / "manifest.json", manifest, key)
        print("One provider response saved; media perception remains unverified.")
        return 0
    except urllib.error.HTTPError as exc:
        error = {"kind": "http_error", "http_status": exc.code, "summary": "provider HTTP request failed; no retry"}
    except ReviewError as exc:
        error = {"kind": "validation_or_response_error", "summary": str(exc)}
    except (OSError, urllib.error.URLError, TimeoutError):
        error = {"kind": "transport_or_filesystem_error", "summary": "request or local I/O failed; no retry"}
    except Exception:  # noqa: BLE001 -- final CLI boundary must not expose headers in library exceptions
        # Never expose a library exception that could contain request headers or response bytes.
        error = {"kind": "unexpected_error", "summary": "media review failed; no retry"}
    if manifest is not None and out is not None and out.is_dir():
        manifest.update(status="failed", request_attempted=request_attempted,
                        provider_completion="unknown" if request_attempted else "not_attempted", error=error)
        try:
            _write(out / "manifest.json", manifest, key)
        except OSError:
            pass
    print(json.dumps(error), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
