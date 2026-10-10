"""Offline geometry/resource evidence tests; no desktop access or provider keys."""

import json

import pytest
from pypdf import PdfReader

from evals.d3_native import FAMILIES, VARIANTS, build_fixture, check_effect, digest, encoding_error


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("variant", VARIANTS)
def test_fixture_labels_are_explicit_and_oracle_separate(tmp_path, family, variant):
    case = build_fixture(tmp_path, family, variant)
    assert case["expected"] is (None if variant == "ambiguous" else variant != "near_miss")
    assert "oracle" in case
    config = json.loads((tmp_path / "config.json").read_text())
    assert "expected" not in config
    assert "supported" not in config["caption"]
    assert (tmp_path / "view.png").exists()


def test_document_pdf_is_raster_only_and_hash_matches_reference(tmp_path):
    case = build_fixture(tmp_path, "document_identity", "supported")
    reference = tmp_path / "source-0.pdf"
    assert PdfReader(reference).pages[0].extract_text() == ""
    assert digest(reference) == digest(tmp_path / "source-2.pdf")
    assert digest(reference) != digest(tmp_path / "source-1.pdf")
    config = json.loads((tmp_path / "config.json").read_text())
    import shutil

    shutil.copyfile(tmp_path / "source-2.pdf", tmp_path / "selected.pdf")
    (tmp_path / "effect.json").write_text(json.dumps({"selected_hash": config["source_hashes"][1]}))
    assert check_effect(tmp_path, case["family"], case["oracle"])
    (tmp_path / "effect.json").write_text(json.dumps({"selected_hash": config["source_hashes"][0]}))
    assert not check_effect(tmp_path, case["family"], case["oracle"])


def test_near_miss_document_positive_alternate_is_actual_source(tmp_path):
    case = build_fixture(tmp_path, "document_identity", "near_miss")
    assert case["oracle"]["reference_hash"] == digest(tmp_path / "source-1.pdf")
    assert case["oracle"]["reference_hash"] != digest(tmp_path / "source-2.pdf")


def test_wrong_crop_has_persisted_false_postcondition(tmp_path):
    from PIL import Image

    case = build_fixture(tmp_path, "crop_boundary", "near_miss")
    Image.open(tmp_path / "view.png").crop(case["proposal"]["rectangle"]).save(tmp_path / "cropped.png")
    (tmp_path / "effect.json").write_text(json.dumps({"saved_crop": case["proposal"]["rectangle"]}))
    assert not check_effect(tmp_path, case["family"], case["oracle"])
    (tmp_path / "effect.json").write_text(json.dumps({"saved_crop": case["oracle"]["valid_crop"]}))
    Image.open(tmp_path / "view.png").crop(case["oracle"]["valid_crop"]).save(tmp_path / "cropped.png")
    assert check_effect(tmp_path, case["family"], case["oracle"])


def test_export_100_percent_has_no_output_until_finished(tmp_path):
    build_fixture(tmp_path, "export_finalizing", "near_miss")
    assert not (tmp_path / "export.txt").exists()
    config = json.loads((tmp_path / "config.json").read_text())
    assert config["caption"] == "Export progress: 100%"
    assert config["phase"] == "finalizing"


def test_palette_error_uses_all_channels():
    from PIL import Image

    raw = Image.new("RGB", (1, 1), (10, 20, 30))
    changed = Image.new("RGB", (1, 1), (10, 20, 33))
    rmse, maximum = encoding_error(raw, changed)
    assert rmse == pytest.approx(3**0.5)
    assert maximum == 3
