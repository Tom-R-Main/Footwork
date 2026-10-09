"""Adversarial corpus contracts use local images, never a model or sealed split."""

import copy
import hashlib
import io
import json
from pathlib import Path

import pytest
from jevdual.visual_checks import CropSpec
from jevdual.visual_evidence import Bounds, Surface, bind_visual
from PIL import Image

from evals.visual_qualification.corpus import CorpusError, load_corpus


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _png(color):
    stream = io.BytesIO()
    Image.new("RGB", (100, 80), color).save(stream, format="PNG")
    return stream.getvalue()


def _write(path, value):
    path.write_text(json.dumps(value))


def corpus_fixture(root, *, role="document_reference_match", split="development", group="g001", color="white"):
    root.mkdir()
    image = _png(color)
    (root / "capture.png").write_bytes(image)
    (root / "resource.png").write_bytes(image)
    (root / "source.json").write_bytes(b'{"source":"owned fixture"}')
    capture = bind_visual(png=image, surface=Surface("native", pid=1, window_id=2),
                          observation_id="observation-1", captured_at="2026-10-08T12:00:00-04:00",
                          viewport=Bounds(0, 0, 100, 80), target_id="1", target_token="opaque",
                          target_bounds=Bounds(10, 10, 50, 40), operation="inspect", postcondition="appearance")
    labels = {"version": 1, "labels": {"c001": True}}
    _write(root / "labels.json", labels)
    manifest = {"version": 1, "split": split,
                "labels": {"path": "labels.json", "sha256": _sha((root / "labels.json").read_bytes())},
                "cases": [{"id": "c001", "role": role, "source_group": group,
                           "input": {"criterion": "The explicit proposal is correct", "criterion_version": "v1",
                                     "accessible_text": "The offered candidate label",
                                     "capture": {"path": "capture.png", "sha256": _sha(image),
                                                 "dimensions": [100, 80], "binding": capture.to_dict()},
                                     "resource": {"path": "resource.png", "sha256": _sha(image),
                                                  "dimensions": [100, 80], "resource_id": "r1", "revision": "v1",
                                                  "page": 1, "render_recipe": "supplied_png"},
                                     "crop": CropSpec(Bounds(0, 0, 100, 80), Bounds(0, 0, 100, 80)).to_dict()
                                     if role == "crop_subject_containment" else None},
                           "provenance": {"kind": "independent_real" if split == "qualification" else "authored_fixture",
                                          "source_record": {"path": "source.json",
                                                            "sha256": _sha((root / "source.json").read_bytes())},
                                          "labelers": ["labeler-1", "labeler-2"], "adjudicated": True}}]}
    _write(root / "manifest.json", manifest)
    return manifest


@pytest.mark.parametrize("role", ["document_reference_match", "crop_subject_containment"])
def test_loads_both_production_bound_families_without_certifying_synthetic(tmp_path, role):
    root = tmp_path / "corpus"
    corpus_fixture(root, role=role)
    loaded = load_corpus(root / "manifest.json")
    assert loaded.root == root
    assert loaded.labels == {"c001": True}
    assert loaded.asset_bytes("capture.png") == (root / "capture.png").read_bytes()
    assert not loaded.eligibility["eligible"]
    assert {"development_only", "independent_real_required", "development_reference_required"} <= set(
        loaded.eligibility["reasons"])


def test_input_projection_is_a_copy_and_has_no_labels_provenance_or_case_metadata(tmp_path):
    root = tmp_path / "corpus"
    corpus_fixture(root)
    loaded = load_corpus(root)
    projection = loaded.input_for("c001")
    assert set(projection) == {"criterion", "criterion_version", "accessible_text", "capture", "resource", "crop"}
    projection["capture"]["binding"]["target"]["token"] = "changed"
    loaded.cases[0]["input"]["criterion"] = "another change"
    assert loaded.input_for("c001")["capture"]["binding"]["target"]["token"] == "opaque"
    assert loaded.input_for("c001")["criterion"] == "The explicit proposal is correct"
    with pytest.raises(CorpusError, match="case_unknown"):
        loaded.input_for("not-a-case")


def test_asset_read_rechecks_content_and_rejects_undeclared_data(tmp_path):
    root = tmp_path / "corpus"
    corpus_fixture(root)
    loaded = load_corpus(root)
    (root / "capture.png").write_bytes(_png("red"))
    with pytest.raises(CorpusError, match="asset_hash_changed"):
        loaded.asset_bytes("capture.png")
    with pytest.raises(CorpusError, match="asset_not_declared"):
        loaded.asset_bytes("../private")


@pytest.mark.parametrize("relative", ["../outside.png", "/outside.png", "nested/../../outside.png",
                                      "nested/./capture.png", "nested//capture.png", "nested\\capture.png"])
def test_path_escape_and_noncanonical_paths_refuse(tmp_path, relative):
    root = tmp_path / "corpus"
    manifest = corpus_fixture(root)
    manifest["cases"][0]["input"]["capture"]["path"] = relative
    _write(root / "manifest.json", manifest)
    with pytest.raises(CorpusError, match="asset_path_unsafe"):
        load_corpus(root)


@pytest.mark.parametrize("component", ["asset", "directory", "root"])
def test_symlinks_refuse_even_inside_corpus(tmp_path, component):
    root = tmp_path / "corpus"
    manifest = corpus_fixture(root)
    path = root
    if component == "asset":
        (root / "alias.png").symlink_to(root / "capture.png")
        manifest["cases"][0]["input"]["capture"]["path"] = "alias.png"
    elif component == "directory":
        (root / "alias").symlink_to(root, target_is_directory=True)
        manifest["cases"][0]["input"]["capture"]["path"] = "alias/capture.png"
    else:
        path = tmp_path / "alias"
        path.symlink_to(root, target_is_directory=True)
    _write(root / "manifest.json", manifest)
    with pytest.raises(CorpusError, match="path_unsafe"):
        load_corpus(path)


@pytest.mark.parametrize("injection", ["label", "source_group", "provenance", "split", "id"])
def test_unrecognized_input_metadata_refuses_instead_of_leaking_labels(tmp_path, injection):
    root = tmp_path / "corpus"
    manifest = corpus_fixture(root)
    manifest["cases"][0]["input"][injection] = "secret annotation"
    _write(root / "manifest.json", manifest)
    with pytest.raises(CorpusError, match="input_fields"):
        load_corpus(root)


@pytest.mark.parametrize("raw", [b'{"version":1,"version":1}', b'{"value":NaN}',
                               b'{"value":Infinity}', b'{"value":1e999}', b'[]'])
def test_duplicate_nonfinite_and_nonobject_json_refuse(tmp_path, raw):
    root = tmp_path / "corpus"
    corpus_fixture(root)
    (root / "manifest.json").write_bytes(raw)
    with pytest.raises(CorpusError):
        load_corpus(root)


@pytest.mark.parametrize("mutation,code", [
    ("hash", "asset_hash_changed"), ("dimensions", "image_dimensions_mismatch"),
    ("pixels", "capture_binding_mismatch"), ("bounds", "target_outside_capture"),
    ("binding_unknown", "target_fields"), ("labels", "label_coverage_mismatch"),
    ("duplicate_case", "case_duplicate_or_invalid"),
])
def test_hash_geometry_coverage_and_case_mutations_refuse(tmp_path, mutation, code):
    root = tmp_path / "corpus"
    manifest = corpus_fixture(root)
    capture = manifest["cases"][0]["input"]["capture"]
    if mutation == "hash":
        capture["sha256"] = "0" * 64
    elif mutation == "dimensions":
        capture["dimensions"] = [80, 100]
    elif mutation == "pixels":
        capture["binding"]["target"]["pixel_bounds"] = [0, 0, 50, 40]
    elif mutation == "bounds":
        capture["binding"]["target"]["bounds"]["width"] = 200
    elif mutation == "binding_unknown":
        capture["binding"]["target"]["label"] = True
    elif mutation == "labels":
        _write(root / "labels.json", {"version": 1, "labels": {"other": True}})
        manifest["labels"]["sha256"] = _sha((root / "labels.json").read_bytes())
    else:
        manifest["cases"].append(copy.deepcopy(manifest["cases"][0]))
    _write(root / "manifest.json", manifest)
    with pytest.raises(CorpusError, match=code):
        load_corpus(root)


@pytest.mark.parametrize("value", [1, "true", {}, []])
def test_labels_require_native_booleans_or_null(tmp_path, value):
    root = tmp_path / "corpus"
    manifest = corpus_fixture(root)
    _write(root / "labels.json", {"version": 1, "labels": {"c001": value}})
    manifest["labels"]["sha256"] = _sha((root / "labels.json").read_bytes())
    _write(root / "manifest.json", manifest)
    with pytest.raises(CorpusError, match="labels_invalid"):
        load_corpus(root)


@pytest.mark.parametrize("mutation,code", [("outside", "crop_outside_source"),
                                           ("aspect", "display_aspect_mismatch"),
                                           ("rotation", "unsupported_orientation")])
def test_crop_uses_production_source_transform_checks(tmp_path, mutation, code):
    root = tmp_path / "corpus"
    manifest = corpus_fixture(root, role="crop_subject_containment")
    crop = manifest["cases"][0]["input"]["crop"]
    if mutation == "outside":
        crop["rectangle"]["width"] = 101
    elif mutation == "aspect":
        crop["displayed_bounds"]["width"] = 90
    else:
        crop["orientation"] = "rotated"
    _write(root / "manifest.json", manifest)
    with pytest.raises(CorpusError, match=code):
        load_corpus(root)


def test_qualification_requires_development_reference_and_independent_declarations(tmp_path):
    dev = tmp_path / "dev"
    target = tmp_path / "target"
    corpus_fixture(dev, color="red")
    manifest = corpus_fixture(target, split="qualification", group="g002")
    assert not load_corpus(target).eligibility["eligible"]
    assert load_corpus(target, development_paths=(dev,)).eligibility == {"eligible": True, "reasons": []}
    manifest["cases"][0]["provenance"].update(source_record=None, labelers=[], adjudicated=False)
    _write(target / "manifest.json", manifest)
    eligibility = load_corpus(target, development_paths=(dev,)).eligibility
    assert not eligibility["eligible"]
    assert {"source_record_missing", "independent_adjudication_required"} <= set(eligibility["reasons"])


@pytest.mark.parametrize("overlap", ["source", "image"])
def test_development_overlap_refuses_independence(tmp_path, overlap):
    dev = tmp_path / "dev"
    target = tmp_path / "target"
    corpus_fixture(dev)
    corpus_fixture(target, split="qualification", group="g001" if overlap == "source" else "g002",
                   color="red" if overlap == "source" else "white")
    eligibility = load_corpus(target, development_paths=(dev,)).eligibility
    assert not eligibility["eligible"]
    assert f"development_{'source' if overlap == 'source' else 'image'}_overlap" in eligibility["reasons"]


def test_source_group_shared_across_roles_is_not_eligible(tmp_path):
    dev = tmp_path / "dev"
    root = tmp_path / "corpus"
    corpus_fixture(dev, color="red")
    manifest = corpus_fixture(root, split="qualification", group="g002")
    case = copy.deepcopy(manifest["cases"][0])
    case.update(id="c002", role="crop_subject_containment")
    case["input"]["crop"] = CropSpec(Bounds(0, 0, 100, 80), Bounds(0, 0, 100, 80)).to_dict()
    manifest["cases"].append(case)
    _write(root / "labels.json", {"version": 1, "labels": {"c001": True, "c002": None}})
    manifest["labels"]["sha256"] = _sha((root / "labels.json").read_bytes())
    _write(root / "manifest.json", manifest)
    assert "source_group_cross_role" in load_corpus(root, development_paths=(dev,)).eligibility["reasons"]


def test_digest_changes_when_labels_or_source_metadata_change(tmp_path):
    root = tmp_path / "corpus"
    manifest = corpus_fixture(root)
    before = load_corpus(root).digest
    _write(root / "labels.json", {"version": 1, "labels": {"c001": False}})
    manifest["labels"]["sha256"] = _sha((root / "labels.json").read_bytes())
    _write(root / "manifest.json", manifest)
    assert load_corpus(root).digest != before


def test_error_codes_do_not_contain_evidence_values(tmp_path):
    root = tmp_path / "corpus"
    manifest = corpus_fixture(root)
    manifest["cases"][0]["input"]["capture"]["path"] = "../DO_NOT_PRINT_THIS"
    _write(root / "manifest.json", manifest)
    with pytest.raises(CorpusError) as failure:
        load_corpus(root)
    assert str(failure.value) == "asset_path_unsafe"


def test_symlink_replacement_between_validation_and_open_cannot_read_outside(tmp_path, monkeypatch):
    root = tmp_path / "corpus"
    corpus_fixture(root)
    loaded = load_corpus(root)
    outside = tmp_path / "private.png"
    outside.write_bytes((root / "capture.png").read_bytes())
    original = Path.is_file
    swapped = False

    def swap_after_check(path):
        nonlocal swapped
        result = original(path)
        if path == root / "capture.png" and not swapped:
            swapped = True
            path.unlink()
            path.symlink_to(outside)
        return result

    monkeypatch.setattr(Path, "is_file", swap_after_check)
    with pytest.raises(CorpusError, match="asset_unavailable"):
        loaded.asset_bytes("capture.png")
    assert swapped


def test_relabeling_an_identical_image_as_a_new_source_group_is_ineligible(tmp_path):
    dev = tmp_path / "dev"
    root = tmp_path / "corpus"
    corpus_fixture(dev, color="red")
    manifest = corpus_fixture(root, split="qualification", group="g002")
    second = copy.deepcopy(manifest["cases"][0])
    second.update(id="c002", source_group="g003")
    manifest["cases"].append(second)
    _write(root / "labels.json", {"version": 1, "labels": {"c001": True, "c002": False}})
    manifest["labels"]["sha256"] = _sha((root / "labels.json").read_bytes())
    _write(root / "manifest.json", manifest)
    eligibility = load_corpus(root, development_paths=(dev,)).eligibility
    assert not eligibility["eligible"]
    assert "image_reused_across_source_groups" in eligibility["reasons"]


def test_annotation_aliases_do_not_count_as_distinct_labelers(tmp_path):
    dev = tmp_path / "dev"
    root = tmp_path / "corpus"
    corpus_fixture(dev, color="red")
    manifest = corpus_fixture(root, split="qualification", group="g002")
    manifest["cases"][0]["provenance"]["labelers"] = ["Annotator", " annotator "]
    _write(root / "manifest.json", manifest)
    assert "independent_adjudication_required" in load_corpus(root, development_paths=(dev,)).eligibility["reasons"]


def test_source_records_are_hash_checked_even_for_authored_development(tmp_path):
    root = tmp_path / "corpus"
    corpus_fixture(root)
    (root / "source.json").write_text("changed source record")
    with pytest.raises(CorpusError, match="asset_hash_changed"):
        load_corpus(root)


def test_digest_binds_development_reference_contents(tmp_path):
    dev = tmp_path / "dev"
    root = tmp_path / "corpus"
    development = corpus_fixture(dev, color="red")
    corpus_fixture(root, split="qualification", group="g002")
    before = load_corpus(root, development_paths=(dev,)).digest
    development["cases"][0]["input"]["criterion_version"] = "v2"
    _write(dev / "manifest.json", development)
    assert load_corpus(root, development_paths=(dev,)).digest != before


def test_supplied_reference_must_be_a_development_corpus(tmp_path):
    reference = tmp_path / "reference"
    root = tmp_path / "corpus"
    corpus_fixture(reference, split="qualification", color="red")
    corpus_fixture(root, split="qualification", group="g002")
    with pytest.raises(CorpusError, match="development_reference_split"):
        load_corpus(root, development_paths=(reference,))
