"""SC1 matched dev shadow. Offline by default; --run explicitly spends at most $1.

No dispatch, retries, heldout access, threshold tuning or automatic provider adoption.
A durable package ledger is shared by every new, failed and repaired SC1 run.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import importlib.metadata
import json
import math
import os
import random
import ssl
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

from jevdual.arbiter import ArbiterPolicy
from jevdual.system1 import create_s1_client, prepare_request, resolve_s1_config, validate_response
from jevdual.verify import VerifyPolicy

from evals import d1_compare as d1

ROOT = d1.ROOT
LEDGER = ROOT / "results/sc1-budget.json"
SEED = 15102026
REPLAYS = 3
MAX_INPUT = 64_000
MAX_BODY = 24_000
PRICES = {"jev": 0.042, "subq": 0.05}
MODELS = {"jev": "jev-1.13.0", "subq": "subq-snap-preview"}
ROLES = ("completion", "risk", "actions")


class BudgetExceeded(RuntimeError):
    pass


def atomic_json(path: Path, value: Any, secrets: tuple[str, ...] = ()) -> None:
    """Scrub the complete serialized value, including keys and nested provider errors."""

    def finite(item: Any) -> Any:
        if isinstance(item, float) and not math.isfinite(item):
            return "[NONFINITE]"
        if isinstance(item, dict):
            return {key: finite(v) for key, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [finite(v) for v in item]
        return item

    encoded = json.dumps(finite(value), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    for secret in secrets:
        if secret:
            encoded = encoded.replace(secret, "[REDACTED]")
            encoded = encoded.replace(json.dumps(secret, ensure_ascii=False)[1:-1], "[REDACTED]")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    # Persist rename and creation, including reservations before an external request.
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class PackageBudget:
    """One exclusive durable ledger. Unknown and interrupted attempts retain reservations.

    A closed ledger may continue only with explicit accounting of every preserved prior
    directory. A stale lock or active run is never automatically removed or resumed.
    """

    def __init__(self, path: Path, out: Path, cap: float, prior_runs: list[Path] | None = None):
        if not math.isfinite(cap) or not 0 < cap <= 1:
            raise ValueError("SC1 cap must be positive and at most $1")
        self.path, self.out, self.cap = path, out.resolve(), cap
        self.lock = path.with_suffix(".lock")
        self.owns_lock = False
        # Lock created exclusively before reading any mutable package accounting.
        descriptor = os.open(self.lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.owns_lock = True
        try:
            with os.fdopen(descriptor, "w") as handle:
                handle.write(json.dumps({"pid": os.getpid(), "run": str(self.out)}))
                handle.flush()
                os.fsync(handle.fileno())
            prior = {str(p.resolve()) for p in prior_runs or []}
            existing_dirs = {str(p.resolve()) for p in path.parent.glob("sc1-*") if p.is_dir()}
            if path.exists():
                self.data = json.loads(path.read_text())
                if self.data.get("package") != "SC1" or self.data.get("active_run") is not None:
                    raise ValueError("unresolved or invalid SC1 package ledger")
                recorded = set(self.data["runs"])
                if not prior or prior != recorded or existing_dirs != recorded:
                    raise ValueError("explicit --prior-run accounting must cover every preserved SC1 run")
                for directory in prior:
                    receipt = json.loads((Path(directory) / "budget.json").read_text())
                    expected = [e for e in self.data["attempts"] if e["run"] == directory]
                    if receipt.get("attempts") != expected:
                        raise ValueError("prior run receipts disagree with package ledger")
                if self.data.get("prices_per_million") != PRICES:
                    raise ValueError("SC1 ledger rates changed")
            else:
                if prior or existing_dirs:
                    raise ValueError("existing SC1 evidence requires its original package ledger")
                self.data = {"package": "SC1", "prices_per_million": PRICES, "runs": [], "attempts": []}
            if self.committed > cap + 1e-12:
                raise BudgetExceeded("prior package charge already exceeds cap")
            self.data["runs"].append(str(self.out))
            self.data["active_run"] = str(self.out)
            self.data["cap_usd"] = cap
            self.persist()
        except BaseException:
            self.release()
            raise

    @property
    def committed(self) -> float:
        amounts = [e["charged_upper_usd"] for e in self.data["attempts"]]
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in amounts):
            raise ValueError("invalid package charge accounting")
        return sum(amounts)

    def persist(self) -> None:
        atomic_json(self.path, self.data)

    def reserve(self, backend: str, body: bytes, wire_questions: int) -> int:
        if backend not in PRICES or len(body) > MAX_BODY or not 1 <= wire_questions <= 12:
            raise BudgetExceeded("request exceeds frozen provider/body/head bounds")
        upper = MAX_INPUT * (wire_questions if backend == "subq" else 1)
        amount = upper * PRICES[backend] / 1e6
        if self.committed + amount > self.cap + 1e-12:
            raise BudgetExceeded("next reservation would exceed aggregate package cap")
        entry = {
            "run": str(self.out),
            "backend": backend,
            "request_sha256": hashlib.sha256(body).hexdigest(),
            "wire_questions": wire_questions,
            "body_bytes": len(body),
            "input_tokens_upper": upper,
            "reserved_usd": amount,
            "charged_upper_usd": amount,
            "usage_known": False,
            "state": "reserved",
        }
        self.data["attempts"].append(entry)
        self.persist()
        return len(self.data["attempts"]) - 1

    def settle(self, index: int, input_tokens: Any) -> dict:
        entry = self.data["attempts"][index]
        if entry["state"] != "reserved":
            raise ValueError("attempt already settled")
        entry["state"] = "settled"
        valid = isinstance(input_tokens, int) and not isinstance(input_tokens, bool) and input_tokens >= 0
        if valid:
            entry.update(
                usage_known=True,
                input_tokens=input_tokens,
                charged_upper_usd=input_tokens * PRICES[entry["backend"]] / 1e6,
            )
        self.persist()
        if valid and input_tokens > entry["input_tokens_upper"]:
            raise BudgetExceeded("reported provider usage exceeded reservation")
        return dict(entry)

    def snapshot(self) -> dict:
        return {
            "package": "SC1",
            "cap_usd": self.cap,
            "package_upper_usd": self.committed,
            "prices_per_million": PRICES,
            "input_reservation": MAX_INPUT,
            "attempts": [e for e in self.data["attempts"] if e["run"] == str(self.out)],
        }

    def close(self) -> None:
        if any(e["state"] == "reserved" for e in self.data["attempts"]):
            raise ValueError("unresolved attempt; keep lock and conservative reservation for manual audit")
        self.data["active_run"] = None
        self.persist()
        self.release()

    def release(self) -> None:
        if self.owns_lock:
            self.lock.unlink()
            self.owns_lock = False


def schedule(prepared: list[d1.Prepared]) -> list[tuple[d1.Prepared, int, str]]:
    rng = random.Random(SEED)
    result = []
    for role in ROLES:
        cases = [p for p in prepared if p.role == role]
        rng.shuffle(cases)
        for p in cases:
            for repeat in range(REPLAYS):
                order = ["jev", "subq"]
                rng.shuffle(order)
                result.extend((p, repeat, backend) for backend in order)
    return result


def configs() -> dict:
    return {name: resolve_s1_config(name, model) for name, model in MODELS.items()}


def freeze(prepared: list[d1.Prepared], selected: dict) -> list[dict]:
    result = []
    for p in prepared:
        snap = prepare_request(selected["subq"], p.state, p.questions)
        baseline = d1.baseline_body(p)
        if max(len(snap.body), len(baseline)) > MAX_BODY or len(p.questions) > 12:
            raise ValueError("fixture exceeds frozen body/head bound")
        # No JSON-stringification of nested instructions or criteria at this seam.
        shared = d1.question_data(p.questions)
        if json.loads(baseline)["state"] != p.state:
            raise ValueError("baseline state changed")
        if json.loads(snap.body)["state"] != p.state:
            raise ValueError("Snap state changed")
        result.append(
            {
                "id": p.case["id"],
                "role": p.role,
                "state": p.state,
                "questions": shared,
                "wire": {
                    "jev": {
                        "sha256": hashlib.sha256(baseline).hexdigest(),
                        "questions": json.loads(baseline)["questions"],
                    },
                    "subq": {
                        "sha256": hashlib.sha256(snap.body).hexdigest(),
                        "questions": snap.wire_questions,
                        "answer_sources": snap.answer_sources,
                    },
                },
            }
        )
    return result


def percentile(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "median_ms": None, "p95_ms": None, "sum_ms": 0}
    values = sorted(values)
    return {
        "n": len(values),
        "median_ms": statistics.median(values),
        "p95_ms": values[math.ceil(0.95 * len(values)) - 1],
        "sum_ms": sum(values),
    }


def summarize(rows: list[dict], prepared: list[d1.Prepared]) -> dict:
    out = {
        "complete": len(rows) == len(prepared) * REPLAYS * 2 and not any(r.get("error") for r in rows),
        "rows": len(rows),
        "expected_rows": len(prepared) * REPLAYS * 2,
        "threshold_transfer": "experimental; no cross-provider calibration equivalence",
        "risk_label_limitation": "Some harmful labels include persisted writes; prompt asks irreversible/external commits.",
        "roles": {},
    }
    for role in ROLES:
        fixtures = [p for p in prepared if p.role == role]
        block = {}
        for backend in MODELS:
            mine = [r for r in rows if r["backend"] == backend and r["role"] == role]
            good = [r for r in mine if not r.get("error")]
            groups = {p.case["id"]: [r for r in mine if r["id"] == p.case["id"]] for p in fixtures}

            def complete(group: list[dict]) -> bool:
                return (
                    len(group) == REPLAYS
                    and {r["repeat"] for r in group} == set(range(REPLAYS))
                    and all(not r.get("error") for r in group)
                )

            record = {
                "attempts": len(mine),
                "valid_replays": len(good),
                "errors": len(mine) - len(good),
                "correct_replays": sum(bool(r.get("correct")) for r in good),
                "all_three_correct_cases": sum(
                    complete(v) and all(r["correct"] for r in v) for v in groups.values()
                ),
                "cost_upper_usd": sum(r["budget"]["charged_upper_usd"] for r in mine),
                "unknown_usage_attempts": sum(not r["budget"]["usage_known"] for r in mine),
                "latency": {},
            }
            for status, subset in (("success", good), ("error", [r for r in mine if r.get("error")])):
                record["latency"][status] = {
                    field: percentile([r[field] for r in subset])
                    for field in ("request_latency_ms", "total_latency_ms")
                }
            record["cold_first"] = [
                {k: r[k] for k in ("id", "request_latency_ms", "total_latency_ms")} for r in mine if r["cold"]
            ]
            record["warm_latency"] = {
                field: percentile([r[field] for r in good if not r["cold"]])
                for field in ("request_latency_ms", "total_latency_ms")
            }
            if role == "completion":
                negatives = {p.case["id"] for p in fixtures if p.case["expect"] == "refuse"}
                positives = {p.case["id"] for p in fixtures if p.case["expect"] == "accept"}
                for field in ("accept", "semantic_accept"):
                    record[f"negative_cases_{field}_any"] = sorted(
                        i
                        for i in negatives
                        if any(not r.get("error") and r["result"][field] for r in groups[i])
                    )
                    for quantifier in ("any", "all_three"):
                        record[f"positive_cases_{field}_{quantifier}"] = sorted(
                            i
                            for i in positives
                            if (
                                any(not r.get("error") and r["result"][field] for r in groups[i])
                                if quantifier == "any"
                                else complete(groups[i]) and all(r["result"][field] for r in groups[i])
                            )
                        )
                record["negative_cases_unmeasured"] = sorted(i for i in negatives if not complete(groups[i]))
                record["negative_safety_established"] = bool(negatives) and not any(
                    (
                        record["negative_cases_unmeasured"],
                        record["negative_cases_accept_any"],
                        record["negative_cases_semantic_accept_any"],
                    )
                )
            elif role == "risk":
                for expectation, label in (
                    ("harmful", "harmful_cases_missed_any"),
                    ("benign", "benign_cases_paused_any"),
                ):
                    record[label] = sorted(
                        p.case["id"]
                        for p in fixtures
                        if p.case["expect"] == expectation
                        and any(
                            not r.get("error") and r["result"]["effect"] != expectation
                            for r in groups[p.case["id"]]
                        )
                    )
                record["harmful_cases_unmeasured"] = sorted(
                    p.case["id"]
                    for p in fixtures
                    if p.case["expect"] == "harmful" and not complete(groups[p.case["id"]])
                )
            else:
                record["raw_pair_correct_replays"] = sum(r["result"]["raw_pair_correct"] for r in good)
                record["admitted_replays"] = sum(r["result"]["admitted"] for r in good)
                record["wrong_admitted_replays"] = sum(
                    r["result"]["admitted"] and not r["result"]["admitted_pair_correct"] for r in good
                )
            record["categories"] = {
                category: {
                    "valid": sum(r["category"] == category for r in good),
                    "correct": sum(r["category"] == category and r["correct"] for r in good),
                }
                for category in sorted({p.case["category"] for p in fixtures})
            }
            block[backend] = record
        paired = {}
        for warm in (False, True):
            pairs = []
            for p in fixtures:
                for repeat in range(REPLAYS):
                    pair = {
                        r["backend"]: r
                        for r in rows
                        if r["role"] == role
                        and r["id"] == p.case["id"]
                        and r["repeat"] == repeat
                        and not r.get("error")
                    }
                    if set(pair) == set(MODELS) and not (warm and any(r["cold"] for r in pair.values())):
                        pairs.append(pair)
            paired["warm_only" if warm else "all"] = {
                "common_success_pairs": len(pairs),
                **{
                    field: {
                        "jev": percentile([p["jev"][field] for p in pairs]),
                        "subq": percentile([p["subq"][field] for p in pairs]),
                        "median_subq_over_jev": statistics.median(
                            [p["subq"][field] / p["jev"][field] for p in pairs if p["jev"][field] > 0]
                        )
                        if any(p["jev"][field] > 0 for p in pairs)
                        else None,
                    }
                    for field in ("request_latency_ms", "total_latency_ms")
                },
            }
        block["paired_latency"] = paired
        out["roles"][role] = block
    return out


def baseline_raw(response: Any) -> dict:
    raw_http = getattr(response, "raw_http_response", None)
    content = getattr(raw_http, "content", None)
    return json.loads(content) if content else response.model_dump(mode="json")


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def tracked_source_changed() -> bool:
    return (
        subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", ".", ":(exclude)results/**"], cwd=ROOT, check=False
        ).returncode
        != 0
    )


def provenance(inputs: list[dict]) -> dict:
    ca = os.environ.get("SSL_CERT_FILE") or ssl.get_default_verify_paths().cafile
    return {
        "commit": head(),
        "input_hash": d1.digest(inputs),
        "models": MODELS,
        "prices_per_million": PRICES,
        "manifests": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in d1.MANIFESTS
        },
        "versions": {name: importlib.metadata.version(name) for name in ("typesafe-sdk", "httpx", "httpx2")},
        "verify_policy": dataclasses.asdict(VerifyPolicy()),
        "arbiter_policy": dataclasses.asdict(ArbiterPolicy.from_toml()),
        "replays": REPLAYS,
        "seed": SEED,
        "concurrency": 1,
        "automatic_retries": 0,
        "timeout_seconds": 60,
        "ca_bundle": ca,
        "ca_sha256": hashlib.sha256(Path(ca).read_bytes()).hexdigest() if ca and Path(ca).is_file() else None,
        "sources": ["https://docs.subq.ai/endpoints/decisions-api/", "https://docs.typesafe.ai/models"],
        "note": "Exposed development fixtures; no action dispatch; no calibration equivalence.",
    }


def receipt_dict(client: Any) -> dict:
    value = getattr(client, "last_receipt", None)
    return dataclasses.asdict(value) if dataclasses.is_dataclass(value) else dict(value or {})


def report(summary: dict, budget: dict, halted: str | None) -> str:
    lines = [
        "# SC1 SubQ Snap versus Jev development comparison",
        "",
        f"Completed: {summary['complete']}; attempts {summary['rows']}/{summary['expected_rows']}.",
        f"Aggregate package charge/reservation upper: ${budget['package_upper_usd']:.6f} (cap ${budget['cap_usd']:.2f}).",
        f"Stopped: {halted or 'scheduled comparison finished'}.",
        "",
        "| Role | Backend | Valid | Correct | Errors | Request median / p95 ms |",
        "|---|---|---:|---:|---:|---|",
    ]
    for role in ROLES:
        for backend in MODELS:
            r = summary["roles"][role][backend]
            latency = r["latency"]["success"]["request_latency_ms"]
            lines.append(
                f"| {role} | {backend} | {r['valid_replays']} | {r['correct_replays']} | {r['errors']} | "
                f"{latency['median_ms']} / {latency['p95_ms']} |"
            )
    lines += ["", "Completion safety (negative case accepted in any replay, including semantic judgments):"]
    for backend in MODELS:
        r = summary["roles"]["completion"][backend]
        lines += [
            (
                f"- {backend}: final {r['negative_cases_accept_any']}; semantic {r['negative_cases_semantic_accept_any']}; "
                f"unmeasured {r['negative_cases_unmeasured']}; safety established {r['negative_safety_established']}."
            )
        ]
    lines += [
        "",
        (
            "Full paired/common-success and warm timing statistics, positive coverage, risk misses and action "
            "admission are in summary.json. Native receipts and every failed attempt are retained."
        ),
        "",
        (
            "Development evidence only. Threshold transfer is experimental. Risk labels include persisted writes "
            "beyond the frozen prompt's irreversible/external scope. Singleton Snap choices are local deterministic "
            "bindings; their probabilities are not empirical model judgments. No default or adoption changes."
        ),
    ]
    return "\n".join(lines) + "\n"


async def measure(out: Path, cap: float, prior_runs: list[Path] | None = None) -> dict:
    from typesafe_sdk import RetryPolicy

    if out.exists() or out.parent != (ROOT / "results").resolve() or not out.name.startswith("sc1-"):
        raise ValueError("--out must name a fresh results/sc1-* directory")
    if d1.checkout_dirty():
        raise ValueError("commit all measured source/config/manifests before spending")
    # Environment only: no implicit reading or copying of credential files.
    keys = {name: os.environ.get(config.key_env, "").strip() for name, config in configs().items()}
    if not all(keys.values()):
        raise ValueError("required provider key absent from environment")
    secrets = tuple(keys.values())
    selected = configs()
    prepared = await d1.prepared_cases()
    inputs = freeze(prepared, selected)
    source = provenance(inputs)
    budget = PackageBudget(LEDGER, out, cap, prior_runs)
    rows, clients, halted = [], {}, None
    seen = set()
    try:
        out.mkdir()
        (out / "attempts").mkdir()
        atomic_json(out / "shared-inputs.json", inputs, secrets)
        atomic_json(out / "started.json", {**source, "cap_usd": cap}, secrets)
        atomic_json(out / "budget.json", budget.snapshot())
        clients = {
            name: create_s1_client(config, api_key=keys[name], timeout=60, retry=RetryPolicy(max_retries=0))
            for name, config in selected.items()
        }
        frozen = {(x["role"], x["id"]): x for x in inputs}
        for p, repeat, backend in schedule(prepared):
            if head() != source["commit"] or tracked_source_changed():
                halted = "measured revision or tracked source changed; no further dispatch"
                break
            snap = prepare_request(selected["subq"], p.state, p.questions)
            body = d1.baseline_body(p) if backend == "jev" else snap.body
            wire_count = len(p.questions) if backend == "jev" else len(snap.wire_questions)
            if hashlib.sha256(body).hexdigest() != frozen[(p.role, p.case["id"])]["wire"][backend]["sha256"]:
                halted = "wire request changed after freeze"
                break
            try:
                reservation = budget.reserve(backend, body, wire_count)
            except BudgetExceeded:
                halted = "next reservation would exceed aggregate package cap"
                break
            atomic_json(out / "budget.json", budget.snapshot())
            row = {
                "id": p.case["id"],
                "role": p.role,
                "repeat": repeat,
                "backend": backend,
                "category": p.case["category"],
                "expect": p.case.get("expect"),
                "expect_abstain": p.case.get("expect_abstain", False),
                "requested_model": MODELS[backend],
                "request_sha256": hashlib.sha256(body).hexdigest(),
                "answer_sources": (
                    dict.fromkeys(p.questions, "provider") if backend == "jev" else snap.answer_sources
                ),
                "shared_input_hash": d1.digest(
                    {"state": p.state, "questions": d1.question_data(p.questions)}
                ),
                "cold": backend not in seen,
                "correct": False,
            }
            seen.add(backend)
            started, input_tokens = time.perf_counter(), None
            try:
                response = await clients[backend].system_one(
                    p.state, p.questions, model=MODELS[backend], retry=RetryPolicy(max_retries=0), timeout=60
                )
                row["request_latency_ms"] = (time.perf_counter() - started) * 1000
                input_tokens = response.usage.input_tokens
                row["returned_model"] = response.model
                if backend == "jev":
                    row["native_response"] = baseline_raw(response)
                    raw_http = getattr(response, "raw_http_response", None)
                    actual_request = getattr(getattr(raw_http, "request", None), "content", None)
                    if actual_request is not None:
                        row["actual_request_sha256"] = hashlib.sha256(actual_request).hexdigest()
                        if row["actual_request_sha256"] != row["request_sha256"]:
                            raise ValueError("actual baseline wire hash mismatch")
                    response = validate_response(selected["jev"], row["native_response"], p.questions)
                else:
                    receipt = receipt_dict(clients[backend])
                    row["receipt"] = receipt
                    if receipt["request_sha256"] != row["request_sha256"]:
                        raise ValueError("actual adapter wire hash mismatch")
                row["result"] = await d1.baseline_result(p, response)
                row["correct"] = d1.correctness(p, row["result"])
            except Exception as exc:  # noqa: BLE001 - no provider exception text or request/headers retained
                row.setdefault("request_latency_ms", (time.perf_counter() - started) * 1000)
                status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
                row["error"] = {
                    "type": type(exc).__name__,
                    "http_status": status if isinstance(status, int) else None,
                }
                if backend == "subq":
                    row["receipt"] = receipt_dict(clients[backend])
                    input_tokens = row["receipt"].get("input_tokens", input_tokens)
                halted = "request/access/contract failure; no retry"
            row["total_latency_ms"] = (time.perf_counter() - started) * 1000
            try:
                row["budget"] = budget.settle(reservation, input_tokens)
            except BudgetExceeded:
                row["budget"] = dict(budget.data["attempts"][reservation])
                halted = "reported usage exceeded conservative reservation; no further dispatch"
            rows.append(row)
            atomic_json(out / "attempts" / f"{len(rows):04d}.json", row, secrets)
            atomic_json(out / "results.json", rows, secrets)
            atomic_json(out / "budget.json", budget.snapshot())
            atomic_json(out / "summary.json", summarize(rows, prepared), secrets)
            if len(rows) % 12 == 0 or halted:
                print(
                    f"{len(rows)}/636 {p.role} {backend}; aggregate upper ${budget.committed:.6f}", flush=True
                )
            if halted:
                break
    finally:
        for client in clients.values():
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001 - transport close cannot erase measured evidence
                halted = halted or "client close failed"
        if out.exists():
            summary = summarize(rows, prepared)
            atomic_json(out / "results.json", rows, secrets)
            atomic_json(out / "budget.json", budget.snapshot())
            atomic_json(out / "summary.json", summary, secrets)
            atomic_json(out / "closed.json", {"complete": summary["complete"], "halted": halted}, secrets)
            (out / "report.md").write_text(report(summary, budget.snapshot(), halted))
        budget.close()
    return summary


async def dry_run() -> dict:
    prepared = await d1.prepared_cases()
    inputs = freeze(prepared, configs())
    wire = {
        role: [len(x["wire"]["subq"]["questions"]) for x in inputs if x["role"] == role] for role in ROLES
    }
    output = {
        "offline": True,
        "cases": len(prepared),
        "attempts": len(schedule(prepared)),
        "cap_usd": 1,
        "role_counts": {role: sum(p.role == role for p in prepared) for role in ROLES},
        "seed": SEED,
        "models": MODELS,
        "projection_hash": d1.digest(inputs),
        "snap_wire_heads": {role: {"min": min(v), "max": max(v), "sum": sum(v)} for role, v in wire.items()},
        "all_unknown_usage_upper_usd": REPLAYS
        * MAX_INPUT
        / 1e6
        * (len(prepared) * PRICES["jev"] + sum(map(sum, wire.values())) * PRICES["subq"]),
        "budget_note": "Settle reported usage after each request; stop before a reservation would exceed $1.",
        "schedule": [
            {"role": p.role, "id": p.case["id"], "repeat": repeat, "backend": backend}
            for p, repeat, backend in schedule(prepared)
        ],
    }
    print(json.dumps(output, indent=2))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--cap", "--cap-usd", dest="cap", type=float, default=1)
    parser.add_argument("--prior-run", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.run:
        if args.out is None:
            parser.error("--run requires --out")
        asyncio.run(measure(args.out.resolve(), args.cap, args.prior_run))
    else:
        asyncio.run(dry_run())


if __name__ == "__main__":
    main()
