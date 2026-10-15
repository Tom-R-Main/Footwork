"""SQ1 synthetic Decisions API probe. Dry-run by default; no runtime integration."""

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "subq-snap-preview"
BASE = "https://api.subq.ai/v1"
ROOT = Path(__file__).resolve().parents[2]
MEASURED = (
    "jevdual/scripts/subq_snap_smoke.py",
    "jevdual/tests/test_subq_snap_smoke.py",
    "jevdual/docs/experiments/SQ1-subq-snap.md",
    "jevdual/docs/notebook/2026-10-15-subq-snap.md",
)
RATE = 0.05 / 1_000_000
CAP = 0.20
ROUTES = ("act", "wait", "done", "escalate")
STATES = {
    "act": "No draft exists. The enabled Create draft control is available. No save is in progress.",
    "wait": "The draft is being saved. A busy indicator is active. No successful save receipt exists.",
    "done": 'The local draft contains exactly "Hello team." and has one successful durable save receipt.',
    "escalate": "A required draft title is missing. Only the user can supply it. Ask for clarification.",
}


class ProbeError(Exception):
    """A bounded probe failure; never includes unsanitized provider text."""


def encode(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def cases():
    for distractors in (0, 8000, 80000):
        history = ("Archived unrelated local draft inventory. " * 2100)[:distractors]
        for route in ROUTES:
            state = (
                f"HISTORICAL IRRELEVANT CONTEXT ({distractors} ASCII characters):\n{history}\n"
                'CURRENT AUTHORITATIVE STATE:\nUser requests a local draft containing exactly "Hello team." '
                "The draft must be saved durably. This is a synthetic local draft task. " + STATES[route]
            )
            request = {
                "model": MODEL,
                "state": state,
                "questions": {
                    "route": {
                        "type": "choice",
                        "instructions": "Choose the next route using only CURRENT AUTHORITATIVE STATE.",
                        "criteria": {
                            "act": "A safe enabled action can advance the requested draft.",
                            "wait": "A save is in progress with a busy indicator and no completion receipt.",
                            "done": "Exact requested content and a successful durable save receipt are present.",
                            "escalate": "A required value is missing and must be supplied by the user.",
                        },
                    },
                    "completion": {
                        "type": "noul",
                        "instructions": "Has the requested local draft been completed and durably saved?",
                        "criteria": {
                            "true": "Exact requested content and a successful durable save receipt are present.",
                            "false": "Required content or a successful durable save receipt is absent.",
                        },
                    },
                    "progress": {
                        "type": "score",
                        "instructions": "Score progress from the current authoritative evidence.",
                        "criteria": [
                            "Not started: no draft exists, or a required value needs user clarification.",
                            "Partial: the draft is being saved, with no successful durable save receipt.",
                            "Complete: exact requested content and a successful durable save receipt exist.",
                        ],
                    },
                },
            }
            body = encode(request)
            if not body.isascii() or len(body) > 90000:
                raise ProbeError("Synthetic request exceeds registered ASCII byte limit")
            yield {"id": f"{route}-{distractors}", "expected_route": route,
                   "distractor_characters": distractors, "request": request, "body": body}


def sanitize(value, key):
    """Redact before serialization, including provider object keys and transport errors."""
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, dict):
        return {sanitize(k, key): sanitize(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, key) for v in value]
    return value


def save(path, value, key=""):
    """Publish a complete fsynced artifact; failed writes preserve its predecessor."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(sanitize(value, key), stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prompt_key():
    if sys.platform != "darwin":
        raise ProbeError("The hidden key dialog requires macOS")
    script = '''set result to display dialog "Paste your SubQ API key. It stays in process memory for this run." default answer "" with hidden answer buttons {"Cancel", "Run SQ1"} default button "Run SQ1" cancel button "Cancel" with title "SubQ Snap SQ1"
return text returned of result'''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ProbeError("Key entry cancelled or unavailable; no API requests sent")
    key = result.stdout.rstrip("\r\n")
    if not key or "\n" in key or "\r" in key:
        raise ProbeError("No valid single-line key entered; no API requests sent")
    return key


def source_revision(expected=None):
    def git(*args):
        result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False)
        if result.returncode:
            raise ProbeError("Cannot verify committed measured source")
        return result.stdout.strip()

    revision = git("rev-parse", "HEAD")
    if expected and revision != expected:
        raise ProbeError("Source revision changed during run")
    for path in MEASURED:
        git("ls-files", "--error-unmatch", path)
    if git("status", "--porcelain", "--", *MEASURED):
        raise ProbeError("Commit measured source files before live measurement")
    return revision


def transport(method, endpoint, key, body=None):
    request = urllib.request.Request(
        BASE + endpoint, method=method, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ProbeError("Provider response exceeds local size bound")
        def reject_constant(_):
            raise ValueError("Nonfinite JSON number")

        return json.loads(raw, parse_constant=reject_constant)
    except urllib.error.HTTPError as error:
        # Provider error bodies may echo headers or input. Retain only the status.
        raise ProbeError(f"HTTP {error.code}; stopped without retry") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProbeError("Transport failure; stopped without retry") from None
    except (ValueError, UnicodeError):
        raise ProbeError("Malformed provider JSON; stopped without retry") from None


def probability(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProbeError("Probability must be finite numeric")
    if not 0 <= value <= 1:
        raise ProbeError("Probability outside [0, 1]")
    return value


def distribution(value, labels):
    if not isinstance(value, dict) or set(value) != set(labels):
        raise ProbeError("Unexpected probability labels")
    values = {label: probability(value[label]) for label in labels}
    if abs(sum(values.values()) - 1) > 0.02:
        raise ProbeError("Probabilities do not sum to one within tolerance")
    return values


def validate_response(response):
    """Validate the documented Decisions shape without coercing malformed values."""
    if not isinstance(response, dict) or response.get("model") != MODEL:
        raise ProbeError("Unexpected response model")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != {"route", "completion", "progress"}:
        raise ProbeError("Unexpected answer fields")
    route, completion, progress = (answers[name] for name in ("route", "completion", "progress"))
    for answer, kind in ((route, "choice"), (completion, "noul"), (progress, "score")):
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise ProbeError("Unexpected answer type")
    route_probs = distribution(route.get("probabilities"), ROUTES)
    selected = route.get("choice")
    if selected not in ROUTES or route_probs[selected] < max(route_probs.values()):
        raise ProbeError("Choice inconsistent with probabilities")
    probability(route.get("confidence"))
    noul = probability(completion.get("noul"))
    score_probs = distribution(progress.get("probabilities"), ("0", "1", "2"))
    legend = progress.get("legend")
    if not isinstance(legend, dict) or set(legend) != {"0", "1", "2"}:
        raise ProbeError("Unexpected score legend")
    if not all(isinstance(v, str) and v.strip() for v in legend.values()):
        raise ProbeError("Invalid score legend")
    probability(progress.get("confidence"))
    score = progress.get("score")
    if (isinstance(score, bool) or not isinstance(score, (int, float))
            or not math.isfinite(score) or not 0 <= score <= 2):
        raise ProbeError("Invalid score")
    if abs(score - sum(int(k) * v for k, v in score_probs.items())) > 0.02:
        raise ProbeError("Score inconsistent with weighted probabilities")
    usage = response.get("usage")
    input_tokens = None
    if usage is not None:
        if not isinstance(usage, dict) or not {"input_tokens", "output_tokens"} <= usage.keys():
            raise ProbeError("Malformed usage")
        for value in usage.values():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ProbeError("Usage must contain nonnegative integers")
        if usage["output_tokens"] != 0:
            raise ProbeError("Unexpected nonzero output usage")
        input_tokens = usage["input_tokens"]
    return {"route": selected, "completion": noul, "score": score, "input_tokens": input_tokens}


def summary(records, revision, stop_reason):
    completed = [r for r in records if r.get("status") == "completed"]
    latencies = [r["latency_seconds"] for r in completed]
    known_usage = [r["input_tokens"] for r in records if r.get("input_tokens") is not None]
    return {
        "experiment": "SQ1", "model": MODEL, "source_commit": revision,
        "planned": 12, "attempted": len(records), "completed": len(completed),
        "contract_valid": sum(r.get("contract_valid", False) for r in records),
        "route_correct": sum(r.get("route_correct", False) for r in records),
        "route_accuracy_planned": sum(r.get("route_correct", False) for r in records) / 12,
        "completion_correct": sum(r.get("completion_correct", False) for r in records),
        "score_correct": sum(r.get("score_correct", False) for r in records),
        "reported_input_tokens": sum(known_usage),
        "reported_usage_available_calls": len(known_usage),
        "estimated_reported_charge_usd": sum(known_usage) * RATE,
        "reserved_or_settled_usd": sum(r["accounted_tokens"] for r in records) * RATE,
        "latency_median_seconds": statistics.median(latencies) if latencies else None,
        "latency_max_seconds": max(latencies) if latencies else None,
        "stop_reason": stop_reason,
        "decision": "larger separately registered study eligible" if (
            len(completed) == 12 and all(r["route_correct"] for r in completed)
        ) else "incomplete or failed; no adoption conclusion",
    }


def run(output, key, revision, send=transport, check_source=source_revision):
    """One access check, then at most twelve attempts; all failures stop the run."""
    records = []
    stop_reason = None
    try:
        check_source(revision)
        save(output / "access-attempt.json", {"method": "GET", "path": "/v1/models"}, key)
        models = sanitize(send("GET", "/models", key), key)
        save(output / "models.json", models, key)
        if not isinstance(models, dict) or not isinstance(models.get("data"), list):
            raise ProbeError("Malformed model list")
        if MODEL not in [m.get("id") for m in models["data"] if isinstance(m, dict)]:
            raise ProbeError("Requested model unavailable to this account")
        for case in cases():
            check_source(revision)
            reservation = len(case["body"]) * 3
            if (sum(r["accounted_tokens"] for r in records) + reservation) * RATE > CAP:
                raise ProbeError("Local cumulative cost reservation cap reached")
            record = {k: v for k, v in case.items() if k not in ("request", "body")}
            record.update({
                "status": "reserved", "request_bytes": len(case["body"]),
                "request_sha256": hashlib.sha256(case["body"]).hexdigest(),
                "reserved_input_tokens": reservation, "accounted_tokens": reservation,
            })
            records.append(record)
            save(output / "attempts.json", records, key)
            save(output / f"{case['id']}-request.json", case["request"], key)
            started = time.monotonic()
            try:
                response = sanitize(send("POST", "/systemone", key, case["body"]), key)
                record["latency_seconds"] = time.monotonic() - started
                record["response"] = response
                validated = validate_response(response)
                record["contract_valid"] = True
                record.update(validated)
                usage = validated["input_tokens"]
                if usage is not None:
                    record["accounted_tokens"] = max(usage, reservation) if usage > reservation else usage
                    if usage > reservation:
                        raise ProbeError("Reported input tokens exceed conservative reservation")
                expected = case["expected_route"]
                record.update({
                    "status": "completed", "route_correct": validated["route"] == expected,
                    "completion_correct": (validated["completion"] >= 0.5) == (expected == "done"),
                    "score_correct": abs(validated["score"] - {"act": 0, "wait": 1,
                                                               "done": 2, "escalate": 0}[expected]) <= 0.5,
                })
            except Exception:
                record["status"] = "error"
                record.setdefault("latency_seconds", time.monotonic() - started)
                raise
            finally:
                save(output / "attempts.json", records, key)
                save(output / "summary.json", summary(records, revision, "running"), key)
    except KeyboardInterrupt:
        stop_reason = "Cancelled; unknown attempt reservations retained"
    except Exception as error:  # noqa: BLE001 - stop every failure without leaking transport text
        # Arbitrary third-party transport errors are never interpolated into output.
        stop_reason = sanitize(str(error), key) if isinstance(error, ProbeError) else "Unexpected failure"
    result = summary(records, revision, stop_reason)
    save(output / "summary.json", result, key)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly permit bounded paid requests")
    parser.add_argument("--prompt-key", action="store_true", help="Use a hidden native macOS key dialog")
    parser.add_argument("--output", type=Path, help="Fresh results/subq-snap-* directory, required live")
    args = parser.parse_args(argv)
    if not args.live:
        requests = list(cases())
        print(json.dumps({"mode": "dry-run", "requests": len(requests),
                          "max_request_bytes": max(len(c["body"]) for c in requests),
                          "maximum_reserved_usd": sum(len(c["body"]) * 3 * RATE for c in requests),
                          "synthetic_cases": [c["id"] for c in requests]}, indent=2))
        return 0
    try:
        if args.output is None:
            raise ProbeError("--output is required for live measurement")
        output = args.output.resolve()
        if output.parent != (ROOT / "jevdual/results").resolve() or not output.name.startswith("subq-snap-"):
            raise ProbeError("Output must be a fresh direct child of jevdual/results named subq-snap-*")
        if output.exists():
            raise ProbeError("Refusing to overwrite an existing run")
        revision = source_revision()
        key = prompt_key() if args.prompt_key else os.environ.get("SUBQ_API_KEY", "")
        if not key:
            raise ProbeError("SUBQ_API_KEY absent; use --prompt-key for a hidden local dialog")
        output.mkdir(mode=0o700)
        result = run(output, key, revision)
        print(f"SQ1: {result['completed']}/12 complete; sanitized artifacts: {output}")
        return 1 if result["stop_reason"] else 0
    except ProbeError as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
