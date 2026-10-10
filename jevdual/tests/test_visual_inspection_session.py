"""Fresh read-only inspection through the real CLI, with a stateful native Driver double."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pytest
from PIL import Image

cd = pytest.importorskip("cua_driver")

from jevdual import cli

from tests.fixtures.native_world import World


class CaptureWorld(World):
    complete = False
    truncated = False
    degraded = False
    missing_png = False
    bad_png = False
    missing_frame = False
    valid_frame = True
    mismatch_dimensions = False
    capture_calls = 0

    async def get_window_state(self, inp):
        snapshot = await super().get_window_state(inp)
        snapshot.update(
            pid=77,
            window_id=self.window_id,
            elements_complete=self.complete,
            truncated=self.truncated,
            degraded=self.degraded,
            window_bounds={"x": 429.0, "y": 358.0, "width": 230.0, "height": 408.0},
        )
        if self.missing_frame:
            for element in snapshot["elements"]:
                element["frame"] = None
        if inp.include_screenshot:
            self.capture_calls += 1
            path = Path(inp.screenshot_out_file)
            if not self.missing_png:
                if self.bad_png:
                    path.write_bytes(b"this is not a PNG")
                else:
                    Image.new("RGB", (460, 816), "white").save(path)
            snapshot.update(
                screenshot_file_path=str(path.resolve()),
                screenshot_width=461 if self.mismatch_dimensions else 460,
                screenshot_height=816,
                screenshot_scale=2.0,
                screenshot_mime_type="image/png",
                screenshot_frame_valid=self.valid_frame,
            )
        return snapshot


@pytest.fixture
def operator(tmp_path, monkeypatch, capsys):
    import jevdual.keys
    import jevdual.verify

    world = CaptureWorld()
    monkeypatch.setattr(cd.CuaDriver, "create", staticmethod(world.create))

    def forbidden(*args, **kwargs):
        raise AssertionError("inspection must not load keys, contact models, or execute")

    monkeypatch.setattr(jevdual.keys, "load_keys", forbidden)
    monkeypatch.setattr(jevdual.verify.Verifier, "judge_destructive", forbidden)
    monkeypatch.setattr(world, "click", forbidden)
    path = tmp_path / "session"

    def run(*args):
        code = cli.main([*args, "--session", str(path)])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    assert run("start", "Inspect calculator controls", "--app", "Calculator")[0] == 0
    return world, path, run


def inspect(run, target="2"):
    return run("inspect-target", target, "--postcondition", "The display is cleared")


def manifest(path):
    return json.loads(next((path / "inspection").glob("*.json")).read_text())


def test_fresh_exact_id_records_binding_without_models_or_dispatch(operator):
    world, path, run = operator
    before = world.n
    code, out, err = inspect(run)
    assert code == 0, err
    assert world.n == before + 1
    evidence = manifest(path)
    assert evidence["observation_id"] == f"s{world.n:08x}"
    assert evidence["inspection"]["elements_complete"] is False
    assert evidence["inspection"]["coverage_warning"]
    assert evidence["inspection"]["target_label"] == "All Clear"
    assert "no action" in out
    assert world.presses == []
    assert not world.tool_calls


def test_preview_outlines_exact_pixel_binding_and_preserves_original_png(operator):
    import hashlib

    world, path, run = operator
    assert inspect(run)[0] == 0
    evidence = manifest(path)
    preview = (path / "inspection" / evidence["inspection"]["preview"]).read_text()
    assert "<h1>Target 2: All Clear</h1>" in preview
    assert "The display is cleared" in preview
    assert "AX projection proves" in preview
    assert "<script" not in preview
    assert evidence["target"]["token"] not in preview
    match = re.search(
        r'class="target-outline" style="left:([\d.]+)%;top:([\d.]+)%;width:([\d.]+)%;height:([\d.]+)%',
        preview,
    )
    assert match is not None
    left, top, right, bottom = evidence["target"]["pixel_bounds"]
    width, height = evidence["image"]["width"], evidence["image"]["height"]
    assert tuple(map(float, match.groups())) == pytest.approx(
        (left / width * 100, top / height * 100, (right - left) / width * 100, (bottom - top) / height * 100),
        abs=1e-8,
    )
    screenshot = path / "inspection" / evidence["inspection"]["screenshot"]
    assert hashlib.sha256(screenshot.read_bytes()).hexdigest() == evidence["image"]["sha256"]
    assert world.presses == []


def test_preview_escapes_native_labels_and_postconditions(operator):
    world, path, run = operator
    label = '<img src=x onerror="window.evil()"> & Clear'
    postcondition = 'Preserve "<neighbors>" & the original image'
    world.relabels[2] = label
    assert run("look")[0] == 0
    code, _, error = run("inspect-target", "2", "--postcondition", postcondition)
    assert code == 0, error
    evidence = manifest(path)
    preview = (path / "inspection" / evidence["inspection"]["preview"]).read_text()
    assert label not in preview and postcondition not in preview
    assert html.escape(label) in preview and html.escape(postcondition) in preview
    assert world.presses == []


def test_secret_session_withholds_before_driver_creation_or_capture(operator, monkeypatch):
    world, path, run = operator
    state_path = path / "session.json"
    state = json.loads(state_path.read_text())
    state["secret_names"] = ["FIXTURE_SECRET"]
    state_path.write_text(json.dumps(state))
    before = world.capture_calls
    monkeypatch.setattr(
        cd.CuaDriver, "create", staticmethod(lambda: pytest.fail("driver created after secret guard"))
    )
    code, _, error = inspect(run)
    assert code == 4 and "screenshot_withheld" in error
    assert world.capture_calls == before
    assert not (path / "inspection").exists()


def test_label_on_partial_tree_cannot_claim_uniqueness(operator):
    _, path, run = operator
    code, _, error = inspect(run, "All Clear")
    assert code == 4 and "label_search_incomplete" in error
    assert not list((path / "inspection").glob("*.json"))


def test_unique_label_on_complete_tree_can_bind(operator):
    world, path, run = operator
    world.complete = True
    assert inspect(run, "All Clear")[0] == 0
    assert manifest(path)["inspection"]["coverage_warning"] is None


def test_duplicate_label_pruning_does_not_falsely_prove_uniqueness(operator):
    world, _, run = operator
    world.complete = True
    world.relabels[3] = "All Clear"
    code, _, error = inspect(run, "All Clear")
    assert code == 4 and "label_search_incomplete" in error


def test_tampered_session_path_cannot_write_outside_loaded_session(operator, tmp_path):
    _, path, run = operator
    state_path = path / "session.json"
    state = json.loads(state_path.read_text())
    outside = tmp_path / "unowned"
    outside.mkdir()
    state["dir"] = str(outside)
    state_path.write_text(json.dumps(state))
    code, _, error = inspect(run)
    assert code == 4 and "session_path_mismatch" in error
    assert not (outside / "session.jsonl").exists()
    assert not list(outside.iterdir())


def test_capture_failure_is_safe_and_keeps_previous_preview_distinct(operator, monkeypatch):
    world, path, run = operator
    assert inspect(run)[0] == 0

    async def broken_capture(*args, **kwargs):
        raise RuntimeError("sensitive raw driver diagnostic")

    monkeypatch.setattr(world, "get_window_state", broken_capture)
    code, _, error = inspect(run)
    assert code == 4 and "capture_failed" in error
    assert "sensitive raw" not in error
    assert "sensitive raw" not in (path / "session.jsonl").read_text()
    assert len(list((path / "inspection").glob("*.html"))) == 1


@pytest.mark.parametrize(
    "attribute,reason",
    [
        ("truncated", "observation_incomplete"),
        ("degraded", "observation_incomplete"),
        ("missing_frame", "target_binding_missing"),
        ("missing_png", "capture_png_missing"),
        ("bad_png", "invalid_png"),
        ("valid_frame", "capture_frame_unverified"),
        ("mismatch_dimensions", "capture_dimensions_mismatch"),
    ],
)
def test_capture_failures_never_fall_back_to_previous_image(operator, attribute, reason):
    world, path, run = operator
    # A successful previous inspection leaves a PNG that must not satisfy the next request.
    assert inspect(run)[0] == 0
    setattr(world, attribute, attribute != "valid_frame")
    code, _, error = inspect(run)
    assert code == 4 and reason in error
    assert len(list((path / "inspection").glob("*.json"))) == 1


def test_renumbered_target_identity_is_refused(operator):
    world, _, run = operator
    world.relabels[2] = "Different control"
    code, _, error = inspect(run)
    assert code == 4 and "target_identity_changed" in error


def test_unknown_id_cannot_create_evidence(operator):
    _, _, run = operator
    code, _, error = inspect(run, "999")
    assert code == 4 and "target_missing" in error


def test_operation_must_be_offered_by_fresh_target(operator):
    _, _, run = operator
    code, _, error = run("inspect-target", "2", "--operation", "append", "--postcondition", "Text appended")
    assert code == 4 and "operation_unsupported" in error


def test_browser_unqualified_geometry_fails_before_capture(operator, monkeypatch):
    _, path, run = operator
    state_path = path / "session.json"
    state = json.loads(state_path.read_text())
    state["mode"] = "browser"
    state_path.write_text(json.dumps(state))
    monkeypatch.setattr(
        cd.CuaDriver, "create", staticmethod(lambda: pytest.fail("unqualified browser captured"))
    )
    code, _, error = inspect(run)
    assert code == 4 and "surface_unsupported" in error
