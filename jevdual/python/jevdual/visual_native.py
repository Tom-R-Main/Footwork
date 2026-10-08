"""Explicit native advisory checks. No dispatch, completion or consent authority."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from .visual_checks import (
    ROLES,
    CropSpec,
    ResourceImage,
    VisualCheckBudget,
    VisualCheckEvidence,
    VisualCheckRequest,
    VisualCheckResult,
    result_to_escalation,
)
from .visual_evidence import Bounds, Surface, VisualEvidenceError, bind_visual


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise VisualEvidenceError(reason)


def _scoped_file(root: Path, value: str) -> Path:
    _require(isinstance(value, str) and bool(value), "asset_path_missing")
    candidate = root / value
    _require(not candidate.is_absolute() or candidate.is_relative_to(root), "asset_outside_session")
    resolved = candidate.resolve()
    _require(resolved.is_relative_to(root), "asset_outside_session")
    # Reject symlink components even if their destination remains inside the session.
    for part in (candidate, *candidate.parents):
        if part == root.parent:
            break
        _require(not part.is_symlink(), "asset_path_unsafe")
    _require(resolved.is_file() and resolved.stat().st_size <= 32_000_000, "asset_unavailable")
    return resolved


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _asset(root: Path, spec: Any) -> tuple[ResourceImage, Path]:
    _require(isinstance(spec, dict), "asset_spec_missing")
    _require(set(spec) == {"path", "sha256", "resource_id", "revision", "page", "render_recipe"},
             "asset_spec_fields")
    path = _scoped_file(root, spec["path"])
    png = path.read_bytes()
    _require(hashlib.sha256(png).hexdigest() == spec["sha256"], "asset_hash_changed")
    return ResourceImage(png, spec["resource_id"], spec["revision"], spec["page"], spec["render_recipe"]), path


def _manifest(root: Path, filename: str) -> tuple[dict, Path]:
    path = _scoped_file(root, filename)
    _require(path.stat().st_size <= 32_000, "manifest_too_large")
    def unique(pairs):
        values = {}
        for key, value in pairs:
            _require(key not in values, "duplicate_manifest_field")
            values[key] = value
        return values

    try:
        spec = json.loads(path.read_text(), object_pairs_hook=unique)
    except VisualEvidenceError:
        raise
    except (ValueError, UnicodeError):
        raise VisualEvidenceError("invalid_manifest") from None
    _require(isinstance(spec, dict), "invalid_manifest")
    common = {"version", "role", "criterion", "criterion_version", "target"}
    _require(spec.get("role") in ROLES, "unsupported_role")
    extra = {"reference"} if spec["role"] == ROLES[0] else {"source", "rectangle", "displayed_bounds", "orientation"}
    _require(set(spec) == common | extra and type(spec["version"]) is int and spec["version"] == 1,
             "manifest_fields")
    _require(type(spec["target"]) is int and spec["target"] >= 0, "observed_id_required")
    _require(all(isinstance(spec[k], str) and spec[k].strip() for k in ("criterion", "criterion_version")),
             "criterion_missing")
    return spec, path


def _private_directory(path: Path) -> None:
    _require(not path.is_symlink(), "visual_path_unsafe")
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    _require(path.is_dir() and info.st_uid == os.getuid() and not info.st_mode & 0o077,
             "visual_path_unsafe")


async def capture_request(bridge: Any, *, root: Path, spec: dict, generation: str,
                          screenshot: Path, budget: VisualCheckBudget, timeout: float,
                          disclose: bool, previous: tuple | list = ()) -> tuple[VisualCheckRequest, Any, Path]:
    """Same service for explicit callers. Caller owns session/source and disclosure scope."""
    role = spec["role"]
    asset, asset_path = _asset(root, spec["reference" if role == ROLES[0] else "source"])
    crop = None
    if role == ROLES[1]:
        _require(all(isinstance(spec[k], list) and len(spec[k]) == 4 for k in ("rectangle", "displayed_bounds")),
                 "invalid_crop_bounds")
        crop = CropSpec(Bounds(*spec["rectangle"]), Bounds(*spec["displayed_bounds"]), spec["orientation"])
    started = time.monotonic()
    nm = await bridge.observe(screenshot_path=str(screenshot))
    finished = time.monotonic()
    _require(not (nm.truncated or nm.degraded or nm.menu.omitted.get("cap")), "observation_incomplete")
    candidate = nm.menu.candidate(spec["target"])
    _require(candidate is not None, "target_missing")
    previous_candidate = next((c for c in previous if c["id"] == candidate.id), None)
    _require(previous_candidate is None or
             (previous_candidate["label"], previous_candidate["role"]) == (candidate.label, candidate.role),
             "target_identity_changed")
    token, frame = nm.token(candidate.id), nm.frames.get(candidate.id)
    _require(bool(token) and frame is not None, "target_binding_missing")
    _require(nm.visual_capture is not None, nm.visual_capture_error or "capture_unavailable")
    capture = nm.visual_capture
    bound = bind_visual(png=screenshot.read_bytes(), surface=Surface("native", nm.pid, nm.window_id),
                        observation_id=nm.snapshot_id, captured_at=capture.captured_at,
                        viewport=Bounds(*capture.viewport), target_id=str(candidate.id), target_token=token,
                        target_bounds=Bounds(*frame), operation="inspect", postcondition=spec["criterion"])
    _require(bound.dimensions == (capture.width, capture.height), "capture_dimensions_mismatch")
    warning = "" if nm.elements_complete else "Observed candidate only; native AX projection is not exhaustive."
    evidence = VisualCheckEvidence(
        bound, generation, started, finished, (asset.resource_id,),
        reference=asset if role == ROLES[0] else None, source=asset if role == ROLES[1] else None, crop=crop,
        accessible_text=nm.menu.full_text or nm.menu.page_text, coverage_warning=warning,
        declared_resource_ownership="caller_supplied_unverified",
    )
    request = VisualCheckRequest(uuid.uuid4().hex, role, spec["criterion"], spec["criterion_version"],
                                 generation, started + timeout, evidence, disclose, budget)
    return request, nm, asset_path


def make_provider():
    """Only called after explicit provider opt-in and disclosure validation."""
    from .keys import load_keys
    from .visual_decisions import VisualDecisionsClient

    _require(load_keys().get("OPENAI_API_KEY", False), "provider_unconfigured")
    return VisualDecisionsClient(os.environ["OPENAI_API_KEY"])


def handoff_summary(request: VisualCheckRequest, result: VisualCheckResult, *, redactor=lambda s: s) -> dict:
    """Text-visible question association, not image visibility or resource proof."""
    def red(value):
        if isinstance(value, str):
            return redactor(value)
        if isinstance(value, dict):
            return {k: red(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [red(v) for v in value]
        return value

    evidence = request.evidence.to_dict()
    return red({"role": request.role, "criterion": request.criterion, "criterion_version": request.criterion_version,
                "target": evidence["capture"]["target"], "reference": evidence["reference"],
                "source": evidence["source"], "crop": evidence["crop"],
                "resource_ownership_proven": False, "display_transform_proven": False,
                "result": result.to_dict(), "image_visible_to_s2": False, "execution_authority": False})


async def cmd_visual_check(args: Any) -> int:
    from .session import SessionState, bind, session_dir
    from .visual_decisions import VisualCallLedger

    directory = session_dir(args.session).absolute()
    state = SessionState.load(directory)
    identifier = uuid.uuid4().hex

    def refused(reason: str) -> int:
        print(f"visual check unavailable: {reason}; no action authorized", file=sys.stderr)
        if state.path.resolve() == directory.resolve():
            state.log({"kind": "visual check unavailable", "reason": reason, "advisory_only": True})
        return 4

    if state.path.resolve() != directory.resolve() or directory.is_symlink():
        return refused("session_path_mismatch")
    if state.secret_names:
        return refused("pixels_withheld")
    if state.mode != "native":
        return refused("surface_unsupported")
    if args.provider and not args.disclose:
        return refused("pixels_withheld")
    root = directory.resolve()
    original_state_hash = _sha(root / "session.json")
    visual = root / "visual"
    if visual.is_symlink():
        return refused("visual_path_unsafe")
    driver = None
    request = None
    try:
        _require(type(args.timeout) in (int, float) and math.isfinite(args.timeout) and 0 < args.timeout <= 60,
                 "invalid_deadline")
        _require(type(args.max_bytes) is int and 0 < args.max_bytes <= 4_000_000, "invalid_body_limit")
        budget = VisualCheckBudget(args.max_bytes, args.max_input_tokens, args.max_calls, args.max_cost)
        spec, manifest_path = _manifest(root, args.request)
        manifest_hash = _sha(manifest_path)
        # Validate asset provenance before starting the native driver.
        _, asset_path = _asset(root, spec["reference" if spec["role"] == ROLES[0] else "source"])
        asset_hash = _sha(asset_path)
        _private_directory(visual)
        driver, bridge = await bind(state)
        request, nm, _ = await capture_request(
            bridge, root=root, spec=spec, generation=identifier, screenshot=visual / f"{identifier}.png",
            budget=budget, timeout=args.timeout, disclose=bool(args.disclose), previous=state.last_candidates,
        )
        _require((nm.pid, nm.window_id) == (state.pid, state.window_id), "surface_mismatch")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        return refused(getattr(exc, "code", "invalid_visual_request"))
    except Exception:  # noqa: BLE001 - raw native text/diagnostics must not reach model logs
        return refused("capture_failed")
    finally:
        if driver is not None:
            try:
                await driver.shutdown()
            except Exception:  # noqa: BLE001 - incomplete capture cleanup prevents dispatch
                request = None
    if request is None:
        return refused("capture_failed")
    if _sha(root / "session.json") != original_state_hash:
        return refused("generation_changed")
    state.remember(nm)
    state.visual_generation = identifier
    state.save()
    state_hash = _sha(root / "session.json")

    def current() -> bool:
        try:
            return (_sha(root / "session.json") == state_hash and _sha(manifest_path) == manifest_hash
                    and _sha(asset_path) == asset_hash and not asset_path.is_symlink())
        except OSError:
            return False

    result = VisualCheckResult(request.request_id, request.evidence.digest, identifier, request.role,
                               "unavailable", reason="provider_unconfigured", request_digest=request.digest)
    if args.provider:
        try:
            ledger = VisualCallLedger(visual / "budget.json", max_calls=args.max_calls,
                                      max_input_tokens=args.max_input_tokens * args.max_calls, max_cost_usd=args.max_cost)
            async with make_provider() as provider:
                result = await provider.check(request, ledger, is_current=current)
        except (ValueError, OSError) as exc:
            result = VisualCheckResult(request.request_id, request.evidence.digest, identifier, request.role,
                                       "unavailable", reason=getattr(exc, "code", "provider_unavailable"),
                                       request_digest=request.digest)
        except Exception:  # noqa: BLE001 - retain no raw provider or key diagnostics
            result = VisualCheckResult(request.request_id, request.evidence.digest, identifier, request.role,
                                       "error", reason="provider_failed", request_digest=request.digest)
    # Provider cleanup can yield or invalidate resources. Reconcile the final output,
    # not merely whether a stale positive can be persisted in the session.
    if result.status == "valid" and (not current() or not result.is_current(
        request, now=time.monotonic(), current_generation=identifier,
    )):
        result = replace(result, status="invalidated", p=None, reason="generation_changed_or_expired")
    escalation = result_to_escalation(request, result)
    question = handoff_summary(request, result)
    record = {"request": request.to_dict(), "question": question, "result": result.to_dict(), "escalation": escalation.to_dict(),
              "screenshot": f"{identifier}.png", "capture_atomic": False,
              "capture_time_basis": "native receipt time; monotonic interval brackets driver call",
              "retention": "private session evidence; retained until operator removes the session",
              "image_visible_to_s2": False, "execution_authority": False}
    receipt = visual / f"{identifier}.json"
    receipt.write_text(json.dumps(record, indent=2), encoding="utf-8")
    if current():
        fresh = SessionState.load(root)
        fresh.last_visual_check = {"question": question, "result": result.to_dict(), "escalation": escalation.to_dict(),
                                  "receipt": str(receipt), "image_visible_to_s2": False}
        fresh.save()
    state.log({"kind": "visual check", "receipt": str(receipt), "status": result.status,
               "reason": result.reason, "evidence_digest": request.evidence.digest, "advisory_only": True})
    print(f"visual check: {receipt}")
    print(json.dumps({"question": question, "result": result.to_dict(), "escalation": escalation.to_dict()}))
    print("Advisory evidence only; no action, grant or postcondition verified. Pixels unavailable to text System Two.")
    return 0 if result.status == "valid" else 4
