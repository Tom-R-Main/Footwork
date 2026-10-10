"""Strict, local corpus loading; provenance declarations do not prove independence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from jevdual.visual_checks import ROLES, CropSpec, ResourceImage, VisualCheckEvidence
from jevdual.visual_evidence import Bounds, Surface, VisualEvidenceError, bind_visual


class CorpusError(ValueError):
    """Static error codes avoid including paths, labels or evidence content."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CorpusError(code)


def _fields(value: object, keys: set[str], code: str) -> dict:
    _require(type(value) is dict and set(value) == keys, code)
    return value


def _text(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()


def _unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate_json_field")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise CorpusError("nonfinite_json")


def _decode(data: bytes) -> dict:
    _require(len(data) <= 4_000_000, "json_too_large")
    try:
        value = json.loads(data, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except CorpusError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise CorpusError("invalid_json") from None
    _require(type(value) is dict, "json_object_required")
    # JSON permits exponent overflow (1e999) without invoking parse_constant.
    try:
        _json_bytes(value)
    except (ValueError, RecursionError):
        raise CorpusError("nonfinite_json") from None
    return value


def _safe_root(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    try:
        _require(not any(p.is_symlink() for p in (absolute, *absolute.parents)), "corpus_path_unsafe")
        _require(absolute.is_dir(), "corpus_unavailable")
    except OSError:
        raise CorpusError("corpus_unavailable") from None
    return absolute


def _read(root: Path, relative: str) -> bytes:
    _require(_text(relative) and "\\" not in relative and "\x00" not in relative, "asset_path_unsafe")
    parsed = PurePosixPath(relative)
    _require(not parsed.is_absolute() and relative == parsed.as_posix()
             and all(part not in (".", "..") for part in parsed.parts), "asset_path_unsafe")
    candidate = root / relative
    descriptors = []
    try:
        _require(not any(p.is_symlink() for p in (candidate, *candidate.parents)), "asset_path_unsafe")
        _require(candidate.resolve().is_relative_to(root) and candidate.is_file(), "asset_unavailable")
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(directory)
        for part in parsed.parts[:-1]:
            directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            descriptors.append(directory)
        descriptor = os.open(parsed.parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        descriptors.append(descriptor)
        _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "asset_unavailable")
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            data = stream.read(32_000_001)
        _require(len(data) <= 32_000_000, "asset_too_large")
        return data
    except OSError:
        raise CorpusError("asset_unavailable") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _record(root: Path, record: object, assets: dict[str, str]) -> bytes:
    value = _fields(record, {"path", "sha256"}, "asset_record_fields")
    _require(type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None,
             "asset_hash_invalid")
    data = _read(root, value["path"])
    _require(_sha(data) == value["sha256"], "asset_hash_changed")
    old = assets.get(value["path"])
    _require(old is None or old == value["sha256"], "asset_hash_conflict")
    assets[value["path"]] = value["sha256"]
    return data


def _bounds(value: object) -> Bounds:
    return Bounds(**_fields(value, {"x", "y", "width", "height"}, "bounds_fields"))


def _dimensions(value: object, actual: tuple[int, int]) -> None:
    _require(type(value) is list and len(value) == 2 and all(type(v) is int and v > 0 for v in value)
             and tuple(value) == actual, "image_dimensions_mismatch")


def _input(root: Path, role: str, value: object, assets: dict[str, str]) -> None:
    value = _fields(value, {"criterion", "criterion_version", "accessible_text", "capture", "resource", "crop"},
                    "input_fields")
    _require(_text(value["criterion"]) and _text(value["criterion_version"])
             and type(value["accessible_text"]) is str, "input_text_invalid")
    capture = _fields(value["capture"], {"path", "sha256", "dimensions", "binding"}, "capture_fields")
    png = _record(root, {k: capture[k] for k in ("path", "sha256")}, assets)
    binding = _fields(capture["binding"], {"version", "inspection_only", "surface", "observation_id",
                                        "captured_at", "image", "viewport", "target"}, "binding_fields")
    target = _fields(binding["target"], {"id", "token", "bounds", "operation", "postcondition", "pixel_bounds"},
                     "target_fields")
    surface = _fields(binding["surface"], {"kind", "pid", "window_id", "tab_id"}, "surface_fields")
    _fields(binding["image"], {"sha256", "width", "height", "scale_x", "scale_y"}, "binding_image_fields")
    _require(type(binding["version"]) is int and binding["version"] == 1
             and binding["inspection_only"] is True, "binding_version")
    _require(type(target["pixel_bounds"]) is list and len(target["pixel_bounds"]) == 4
             and all(type(v) is int for v in target["pixel_bounds"]), "pixel_bounds_invalid")
    for key in ("width", "height"):
        _require(type(binding["image"][key]) is int, "binding_image_fields")
    bound = bind_visual(png=png, surface=Surface(**surface), observation_id=binding["observation_id"],
                        captured_at=binding["captured_at"], viewport=_bounds(binding["viewport"]),
                        target_id=target["id"], target_token=target["token"], target_bounds=_bounds(target["bounds"]),
                        operation=target["operation"], postcondition=target["postcondition"])
    _require(_json_bytes(binding) == _json_bytes(bound.to_dict()), "capture_binding_mismatch")
    _dimensions(capture["dimensions"], bound.dimensions)
    resource = _fields(value["resource"], {"path", "sha256", "dimensions", "resource_id", "revision", "page",
                                           "render_recipe"}, "resource_fields")
    image = ResourceImage(_record(root, {k: resource[k] for k in ("path", "sha256")}, assets),
                          resource["resource_id"], resource["revision"], resource["page"], resource["render_recipe"])
    _dimensions(resource["dimensions"], image.dimensions)
    crop = None
    if role == ROLES[1]:
        spec = _fields(value["crop"], {"rectangle", "displayed_bounds", "orientation"}, "crop_fields")
        crop = CropSpec(_bounds(spec["rectangle"]), _bounds(spec["displayed_bounds"]), spec["orientation"])
    else:
        _require(value["crop"] is None, "unexpected_crop")
    VisualCheckEvidence(bound, "corpus-validation", 0., 0., (image.resource_id,),
                        reference=image if role == ROLES[0] else None,
                        source=image if role == ROLES[1] else None, crop=crop,
                        accessible_text=value["accessible_text"])


@dataclass(frozen=True)
class Corpus:
    root: Path
    manifest: dict
    labels: dict[str, bool | None]
    cases: list[dict]
    digest: str
    eligibility: dict
    _assets: dict[str, str] = field(repr=False)
    _inputs: dict[str, dict] = field(repr=False)

    def input_for(self, case_id: str) -> dict:
        _require(type(case_id) is str and case_id in self._inputs, "case_unknown")
        return copy.deepcopy(self._inputs[case_id])

    def asset_bytes(self, relative: str) -> bytes:
        _require(type(relative) is str and relative in self._assets, "asset_not_declared")
        data = _read(self.root, relative)
        _require(_sha(data) == self._assets[relative], "asset_hash_changed")
        return data


def load_corpus(path: Path, *, development_paths: tuple[Path, ...] = ()) -> Corpus:
    """Validate data and compute independence eligibility; never invoke a provider."""
    try:
        return _load(path, development_paths)
    except CorpusError:
        raise
    except VisualEvidenceError as error:
        raise CorpusError(error.code) from None
    except (TypeError, KeyError, AttributeError, OverflowError):
        raise CorpusError("corpus_structure_invalid") from None


def _load(path: Path, development_paths: tuple[Path, ...]) -> Corpus:
    path = Path(path)
    root = _safe_root(path if path.is_dir() else path.parent)
    filename = "manifest.json" if path.is_dir() else path.name
    assets: dict[str, str] = {}
    manifest_bytes = _read(root, filename)
    manifest = _fields(_decode(manifest_bytes), {"version", "split", "labels", "cases"}, "manifest_fields")
    _require(type(manifest["version"]) is int and manifest["version"] == 1, "manifest_version")
    _require(manifest["split"] in ("development", "qualification"), "manifest_split")
    label_spec = manifest["labels"]
    label_data = _fields(_decode(_record(root, label_spec, assets)), {"version", "labels"}, "labels_fields")
    _require(type(label_data["version"]) is int and label_data["version"] == 1, "labels_version")
    labels = label_data["labels"]
    _require(type(labels) is dict and all(v is None or type(v) is bool for v in labels.values()), "labels_invalid")
    cases = manifest["cases"]
    _require(type(cases) is list and 0 < len(cases) <= 100_000, "cases_invalid")
    ids, roles_by_group, groups_by_image, reasons = set(), {}, {}, set()
    for case in cases:
        _fields(case, {"id", "role", "source_group", "input", "provenance"}, "case_fields")
        _require(_text(case["id"]) and case["id"] not in ids, "case_duplicate_or_invalid")
        ids.add(case["id"])
        _require(case["role"] in ROLES and _text(case["source_group"]), "case_role_or_group_invalid")
        roles_by_group.setdefault(case["source_group"], set()).add(case["role"])
        _input(root, case["role"], case["input"], assets)
        for key in ("capture", "resource"):
            groups_by_image.setdefault(case["input"][key]["sha256"], set()).add(case["source_group"])
        provenance = _fields(case["provenance"], {"kind", "source_record", "labelers", "adjudicated"},
                             "provenance_fields")
        _require(provenance["kind"] in ("authored_fixture", "independent_real"), "provenance_kind")
        _require(type(provenance["labelers"]) is list and all(_text(v) for v in provenance["labelers"])
                 and len(provenance["labelers"]) == len(set(provenance["labelers"]))
                 and type(provenance["adjudicated"]) is bool, "provenance_annotations")
        if provenance["source_record"] is not None:
            _record(root, provenance["source_record"], assets)
        else:
            reasons.add("source_record_missing")
        if provenance["kind"] != "independent_real":
            reasons.add("independent_real_required")
        if not provenance["adjudicated"] or len({v.strip().casefold() for v in provenance["labelers"]}) < 2:
            reasons.add("independent_adjudication_required")
    _require(ids == set(labels), "label_coverage_mismatch")
    if any(len(roles) > 1 for roles in roles_by_group.values()):
        reasons.add("source_group_cross_role")
    if any(len(groups) > 1 for groups in groups_by_image.values()):
        reasons.add("image_reused_across_source_groups")
    if manifest["split"] != "qualification":
        reasons.add("development_only")
    if not development_paths:
        reasons.add("development_reference_required")
    evidence_shas = {case["input"][key]["sha256"] for case in cases for key in ("capture", "resource")}
    development_digests = []
    for development_path in development_paths:
        development = load_corpus(development_path)
        development_digests.append(development.digest)
        _require(development.manifest["split"] == "development", "development_reference_split")
        if set(roles_by_group) & {case["source_group"] for case in development.cases}:
            reasons.add("development_source_overlap")
        if evidence_shas & {case["input"][key]["sha256"] for case in development.cases
                            for key in ("capture", "resource")}:
            reasons.add("development_image_overlap")
    digest = _sha(_json_bytes({"manifest": manifest, "labels": label_data, "assets": assets,
                              "development_digests": sorted(development_digests)}))
    return Corpus(root, copy.deepcopy(manifest), copy.deepcopy(labels), copy.deepcopy(cases), digest,
                  {"eligible": not reasons, "reasons": sorted(reasons)}, dict(assets),
                  {case["id"]: copy.deepcopy(case["input"]) for case in cases})
