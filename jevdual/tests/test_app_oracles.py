"""Offline oracle sensitivity; filesystem/Pillow mutations here are NOT UI qualification."""

from __future__ import annotations

import copy
import json
import os
import struct
import zlib
from pathlib import Path

import pytest
from jevdual.app_oracles import MAX_BYTES, OracleError, check_finder, check_preview, create_fixture
from PIL import Image


@pytest.fixture
def fixture(tmp_path):
    return create_fixture(tmp_path / "owned")


def organize(manifest):
    root = Path(manifest["root"])
    source, destination = root / manifest["paths"]["source"], root / manifest["paths"]["organized"]
    source.rename(root / manifest["paths"]["renamed"])
    (root / manifest["paths"]["renamed"]).rename(destination)
    return destination


def rotate(path, clockwise=True):
    # Driver-double fixture mutation; oracle uses a separate manifest-matrix formula.
    with Image.open(path) as image:
        transformed = image.transpose(Image.Transpose.ROTATE_270 if clockwise else Image.Transpose.ROTATE_90)
        transformed.save(path)


def test_fresh_setup_has_asymmetric_seed_and_bound_manifest(fixture):
    root = Path(fixture["root"])
    assert fixture == json.loads((root / "fixture.json").read_text())
    assert fixture["seed"]["width"] != fixture["seed"]["height"]
    assert check_finder(fixture, fixture["paths"]["source"]).ok
    assert not check_finder(fixture, fixture["paths"]["organized"]).ok
    with pytest.raises(OracleError, match="fresh"):
        create_fixture(root)


def test_rename_move_checks_full_path_bytes_and_siblings(fixture):
    destination = organize(fixture)
    result = check_finder(fixture, fixture["paths"]["organized"])
    assert result.ok, result.detail
    assert result.artifact == str(destination)
    assert result.identity["sha256"] == fixture["original_sha256"]
    assert "historical" in result.limits[0]
    assert json.loads(json.dumps(result.to_record()))["ok"] is True
    assert not check_finder(fixture, "inbox/renamed.png").ok


@pytest.mark.parametrize("failure", ["bytes", "sibling", "original", "duplicate", "extra"])
def test_finder_oracle_falsifies_state_defects(fixture, failure):
    root = Path(fixture["root"])
    destination = organize(fixture)
    if failure == "bytes":
        destination.write_bytes(b"wrong asset")
    elif failure == "sibling":
        (root / "inbox/keep.bin").write_bytes(b"changed sibling")
    elif failure == "original":
        (root / fixture["paths"]["original"]).unlink()
    elif failure == "duplicate":
        (root / fixture["paths"]["source"]).write_bytes(destination.read_bytes())
    else:
        (root / "organized/unrequested.txt").write_text("extra effect")
    assert not check_finder(fixture, fixture["paths"]["organized"]).ok


def test_wrong_basename_folder_and_outside_destination_do_not_pass(fixture, tmp_path):
    destination = organize(fixture)
    assert not check_finder(fixture, "decoy/asset.png").ok
    assert not check_finder(fixture, "../organized/renamed.png").ok
    assert not check_preview(fixture, tmp_path / "renamed.png").ok
    assert not check_preview(fixture, destination.parent / ".." / "organized" / destination.name).ok


@pytest.mark.parametrize("where", ["file", "parent"])
def test_symlink_components_never_supply_evidence(fixture, tmp_path, where):
    root = Path(fixture["root"])
    destination = organize(fixture)
    if where == "file":
        destination.unlink()
        destination.symlink_to(root / fixture["paths"]["original"])
    else:
        (root / "organized").rename(tmp_path / "outside")
        (root / "organized").symlink_to(tmp_path / "outside", target_is_directory=True)
    assert not check_finder(fixture, fixture["paths"]["organized"]).ok


@pytest.mark.parametrize("clockwise", [True, False])
def test_preview_decodes_exact_rotated_pixels_independent_of_png_bytes(fixture, clockwise):
    destination = organize(fixture)
    rotate(destination, clockwise)
    result = check_preview(fixture, destination, clockwise=clockwise)
    assert result.ok, result.detail
    assert (result.identity["width"], result.identity["height"]) == (3, 5)
    assert result.identity["sha256"] != fixture["original_sha256"]
    assert result.identity["rgb_sha256"]
    assert not check_finder(fixture, fixture["paths"]["organized"]).ok
    assert not check_preview(fixture, destination, clockwise=not clockwise).ok


def test_unsaved_or_wrong_window_rotation_does_not_pass(fixture):
    root = Path(fixture["root"])
    destination = organize(fixture)
    assert not check_preview(fixture, destination).ok
    rotate(root / fixture["paths"]["decoy"])
    assert not check_preview(fixture, destination).ok


@pytest.mark.parametrize("failure", ["pixel", "alpha", "dimensions", "profile", "orientation"])
def test_preview_oracle_falsifies_pixel_and_encoding_defects(fixture, failure):
    destination = organize(fixture)
    rotate(destination)
    with Image.open(destination) as original:
        image = original.copy()
    if failure == "pixel":
        image.putpixel((0, 0), (0, 0, 0))
    elif failure == "alpha":
        image = image.convert("RGBA")
        image.putpixel((0, 0), (0, 0, 0, 0))
    elif failure == "dimensions":
        image = image.resize((4, 5))
    elif failure == "profile":
        image.save(destination, icc_profile=b"unsupported profile")
        assert not check_preview(fixture, destination).ok
        return
    else:
        metadata = Image.Exif()
        metadata[274] = 6
        image.save(destination, exif=metadata)
        assert not check_preview(fixture, destination).ok
        return
    image.save(destination)
    assert not check_preview(fixture, destination).ok


def test_oracle_does_not_change_the_assets_or_manifest(fixture):
    destination = organize(fixture)
    rotate(destination)
    root = Path(fixture["root"])
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert check_preview(fixture, destination).ok
    check_finder(fixture, fixture["paths"]["organized"])
    after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert before == after


def test_mutated_manifest_and_replaced_root_are_not_trusted(fixture, tmp_path):
    changed = copy.deepcopy(fixture)
    changed["seed"]["pixels"][0][0] = [0, 0, 0]
    assert not check_preview(changed, changed["paths"]["source"]).ok
    root = Path(fixture["root"])
    root.rename(tmp_path / "old-owned")
    root.mkdir()
    assert not check_finder(fixture, fixture["paths"]["source"]).ok


def test_bounded_reads_and_nonregular_entries(fixture):
    destination = organize(fixture)
    destination.write_bytes(b"x" * (MAX_BYTES + 1))
    assert not check_finder(fixture, fixture["paths"]["organized"]).ok
    assert not check_preview(fixture, destination).ok
    destination.unlink()
    os.mkfifo(destination)
    assert not check_preview(fixture, destination).ok


def test_finder_metadata_is_not_confused_with_asset_duplication(fixture):
    root = Path(fixture["root"])
    organize(fixture)
    (root / "inbox/.DS_Store").write_bytes(b"Finder-owned view metadata")
    assert check_finder(fixture, fixture["paths"]["organized"]).ok


def test_decompression_bomb_header_returns_a_failed_check(fixture):
    destination = organize(fixture)
    encoded = bytearray(destination.read_bytes())
    encoded[16:24] = struct.pack(">II", 65536, 65536)
    encoded[29:33] = struct.pack(">I", zlib.crc32(encoded[12:29]))
    destination.write_bytes(encoded)
    assert not check_preview(fixture, destination).ok
