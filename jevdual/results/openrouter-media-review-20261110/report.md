# Bounded OpenRouter media review helper

Prediction: `76ea245`. This source-only helper supports the user-selected reviewer `qwen/qwen3.8-omni-flash` via the pinned OpenRouter Chat Completions endpoint.

From `jevdual/`, validate without credentials or a network request:

```sh
.venv/bin/python scripts/openrouter_media_review.py --media /absolute/clip.wav --prompt /absolute/review.txt --out /absolute/path/inside/footwork/jevdual/output/review-dry
```

Make exactly one explicitly authorized request with a fresh output directory:

```sh
.venv/bin/python scripts/openrouter_media_review.py --media /absolute/clip.wav --prompt /absolute/review.txt --out /absolute/path/inside/footwork/jevdual/output/review-live --env-file /absolute/path/inside/footwork/jevdual/.env --max-tokens 500 --execute
```

WAV/MP3 use base64 `input_audio`; MP4 uses a base64 `video_url` data URL. Defaults: 16MiB media cap, 2000 output tokens, 60-second HTTP timeout. Maximum settings: 32MiB, 4000 output tokens, 120 seconds. Prompt files are bounded to32KiB and responses to2MiB. These are operational caps, not model limits. The helper does not decode media or establish its duration; the caller must probe/capture and associate actual timeline ranges separately.

Output is restricted to a fresh directory inside this checkout. `request-intent.json` records pending intent before sending. `manifest.json` retains media/prompt hashes, size/type, requested and returned model/provider metadata, response identity and status; `response.json` retains text, finish reason and usage when available. Files use0600 permissions, directory0700. No request body or bearer header is retained. Credential strings and any exact echoed encoded media are redacted from retained response data. Provider/model identity is reported as returned rather than inferred.

The explicit dotenv reader accepts literal `OPENROUTER_API_KEY=value` or a quoted value (optional export prefix), without shell evaluation or interpolation. Dry-run never reads the credential file. Missing/duplicate/invalid credentials refuse before sending. HTTP and library errors are reported generically with HTTP status where available, without echoed upstream bodies. Redirects and automatic retries are disabled. After a request attempt fails, provider completion is conservatively unknown; inspect evidence before manually retrying.

`pytest.txt`:30 tests pass across the helper and notebook suites. Tests cover audio/video payload delivery, hashes/usage/model provenance, dry-run/no-key behavior, redaction of malicious echoes, errors/no retries, existing output preservation, bounds, invalid inputs and redirect refusal. Changed-file Ruff and `git diff --check` pass. Commands:

```sh
uv run --no-sync pytest tests/test_openrouter_media_review.py tests/test_notebook.py -q
uv run --no-sync ruff check scripts/openrouter_media_review.py tests/test_openrouter_media_review.py
uv run --no-sync python -m evals.notebook docs/notebook --check
```

All HTTP/model behavior here is mocked; no real credential file was read and no provider call was made by the worker. This does not qualify live audio/video delivery, correct perception, temporal localization, music taste or Suno completion. Parent performs those checks on the committed helper. New helper is invoked explicitly and is not installed into the user-local Footwork launcher.

## TLS follow-up

After the parent reported immediate certificate failures under the checkout interpreter, prediction `48cf800` preceded a verified-trust repair. The helper now builds a request-local SSL context from the already installed certifi CA bundle, falling back to platform defaults only if certifi is unavailable. Certificate verification and hostname checks remain enabled; no global trust or dependency installation is changed.

An HTTPS connection wrapper marks certificate-verification failure specifically during connection establishment. Only that typed handshake failure records `application_request_sent=false` and `provider_completion=not_sent_tls_handshake`. A certificate error of unqualified origin, generic URL error or timeout retains unknown delivery. Diagnostics retain only safe classification and numeric SSL verification code; arbitrary exception text is excluded. No redirects or automatic retries were added. A proxy CONNECT handshake, where applicable, is distinct from the target application's request.

`pytest-tls.txt`:39 helper/notebook tests pass, including explicit CA/verification settings, platform fallback, HTTPS opener/connection binding, safe handshake-code retention and unknown-delivery counterexamples. Ruff and diff checks pass. Worker did not read a real key or issue HTTPS/model requests; parent must independently verify public metadata with `_tls_context()` and re-drive fresh live probes. Original failed-run evidence is retained by the parent.

## Total deadline follow-up

The parent's MP4 request demonstrated that the old socket timeout did not bound the total exchange. `red-deadline.txt` independently reproduces that contract defect using baseline `e3eaecb` with a synthetic active stream and no network. Prediction `a5f1495` preceded this follow-up.

`--timeout` now bounds one isolated transport exchange, including child startup, private request transfer and response receipt. The parent supplies credentials/media over stdin, never argv or a new environment entry. The child uses the same verified TLS/no-redirect transport. Normal timeout or catchable interruption kills and reaps that sole child, with up to2 additional seconds for cleanup. The final manifest reports the timeout phase, observed child cleanup and unknown remote completion. There is no resubmission. An unconfirmed cleanup retains the child PID explicitly rather than claiming termination.

`transport-child.json` journals the child PID and start timestamp before the parent transfers the request. This is diagnostic evidence, not crash-proof custody: abrupt parent death/SIGKILL can defeat cleanup, and the small launch-to-journal gap remains. Reconcile retained intent/process evidence before any further submission. The deadline does not bound unrelated local media validation or filesystem writes.

`pytest-deadline.txt`:45 helper/notebook tests pass. A real local, no-network slow-drip child is killed and reaped by a0.15s deadline despite ongoing bytes; mocked cases verify private-pipe payloads, one attempt, cleanup-failure evidence, interruption cleanup and safe child diagnostics. Ruff/notebook/diff checks pass. No real key or provider call was accessed by this worker; original root-owned live processes and evidence were untouched.
