"""Evidence must identify a capture and an exact proposal without granting authority."""
import io
from dataclasses import FrozenInstanceError, replace

import pytest
from jevdual.visual_evidence import Bounds, Surface, VisualEvidenceError, bind_visual
from PIL import Image


def image(width=200, height=100, color="white"):
    stream = io.BytesIO()
    Image.new("RGB", (width, height), color).save(stream, format="PNG")
    return stream.getvalue()


def bound(**changes):
    args = {"png": image(), "surface": Surface("native", 12, 24), "observation_id": "observation-1",
            "captured_at": "2026-10-08T20:00:00+00:00", "viewport": Bounds(-50, 100, 100, 50),
            "target_id": "2", "target_token": "driver-token", "target_bounds": Bounds(-40, 110, 20, 10),
            "operation": "click", "postcondition": "The editor enters crop mode"}
    return bind_visual(**(args | changes))


def test_screen_origin_and_actual_image_scale_bind_exact_region():
    evidence = bound()
    assert evidence.target.pixel_bounds == (20, 20, 60, 40)
    assert evidence.to_dict()["image"]["scale_x"] == 2
    assert evidence.to_dict()["inspection_only"] is True
    assert "png" not in evidence.to_dict()
    assert len(evidence.image_sha256) == 64
    assert evidence.binding_sha256 == bound().binding_sha256
    evidence.assert_matches(bound())


def test_downscaled_native_capture_uses_actual_pixels_not_reported_retina_scale():
    evidence = bound(png=image(100, 50))
    assert evidence.target.pixel_bounds == (10, 10, 30, 20)
    assert evidence.to_dict()["image"]["scale_x"] == 1


def test_fractional_bounds_round_outward_to_preserve_complete_target():
    evidence = bound(target_bounds=Bounds(-40.2, 110.2, 20, 10))
    assert evidence.target.pixel_bounds == (19, 20, 60, 41)


@pytest.mark.parametrize("changes", [
    {"surface": Surface("native", 13, 24)}, {"surface": Surface("native", 12, 25)},
    {"surface": Surface("browser", tab_id="tab-1")}, {"observation_id": "observation-2"},
    {"png": image(color="black")}, {"target_id": "3"}, {"target_token": "new-token"},
    {"target_bounds": Bounds(-35, 110, 20, 10)}, {"operation": "hover"},
    {"postcondition": "The editor rotates the image"},
    {"captured_at": "2026-10-08T20:00:01+00:00"},
])
def test_changed_capture_or_proposal_invalidates_binding(changes):
    with pytest.raises(VisualEvidenceError, match="visual_binding_changed"):
        bound().assert_matches(bound(**changes))


@pytest.mark.parametrize("bounds", [Bounds(-51, 110, 20, 10), Bounds(-40, 99, 20, 10),
                                      Bounds(40, 110, 20, 10), Bounds(-40, 145, 20, 10)])
def test_partially_clipped_target_is_not_a_complete_bound_capture(bounds):
    with pytest.raises(VisualEvidenceError, match="target_outside_capture"):
        bound(target_bounds=bounds)


@pytest.mark.parametrize("changes", [{"target_id": ""}, {"target_token": ""}, {"operation": ""},
                                      {"postcondition": ""}, {"observation_id": ""},
                                      {"captured_at": "bad"}, {"captured_at": "2026-10-08T20:00:00"},
                                      {"png": b"not a PNG"}, {"png": image()[:-12]}])
def test_missing_or_corrupt_evidence_fails_closed(changes):
    with pytest.raises(VisualEvidenceError):
        bound(**changes)


def test_non_png_image_cannot_claim_png_provenance():
    stream = io.BytesIO()
    Image.new("RGB", (20, 20)).save(stream, format="JPEG")
    with pytest.raises(VisualEvidenceError, match="not_png"):
        bound(png=stream.getvalue())


def test_types_are_immutable_and_pixel_claim_is_revalidated():
    evidence = bound()
    with pytest.raises(FrozenInstanceError):
        evidence.observation_id = "changed"
    with pytest.raises(VisualEvidenceError, match="pixel_binding_mismatch"):
        replace(evidence, target=replace(evidence.target, pixel_bounds=(1, 1, 5, 5)))


@pytest.mark.parametrize("args", [(0, 0, 0, 1), (0, 0, -1, 1), (float("nan"), 0, 1, 1),
                                  (True, 0, 1, 1)])
def test_invalid_numeric_geometry(args):
    with pytest.raises(VisualEvidenceError):
        Bounds(*args)


@pytest.mark.parametrize("kwargs", [{"kind": "unknown"}, {"kind": "native"},
                                    {"kind": "native", "pid": True, "window_id": 1},
                                    {"kind": "browser", "tab_id": ""}])
def test_missing_surface_identity(kwargs):
    with pytest.raises(VisualEvidenceError):
        Surface(**kwargs)
