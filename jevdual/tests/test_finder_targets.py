"""Finder selector identity sensitivity using a fake AX boundary, never live input."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual import ax
from jevdual import finder_targets as finder
from jevdual.app_oracles import create_fixture


@pytest.fixture
def owned(tmp_path):
    manifest = create_fixture(tmp_path / "owned")
    selector = "file:" + str(Path(manifest["root"]) / manifest["paths"]["source"])
    return manifest, finder.bind(manifest, selector)


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setattr(
        ax,
        "_attr",
        lambda element, name: None if element.get("_errors", {}).get(name) else element.get(name),
    )
    monkeypatch.setattr(ax, "frame_of", lambda element: element.get("frame"))
    monkeypatch.setattr(finder, "file_url_path", lambda url: url.removeprefix("reference:"))
    monkeypatch.setattr(finder, "_element_identity", id, raising=False)

    def names(element, _):
        return element.get("_inventory_error", 0), [key for key in element if key.startswith("AX")]

    def read(element, name, _):
        return element.get("_errors", {}).get(name, 0), element.get(name)

    monkeypatch.setitem(
        sys.modules,
        "ApplicationServices",
        SimpleNamespace(AXUIElementCopyAttributeNames=names, AXUIElementCopyAttributeValue=read),
    )

    def install(children):
        window = {"AXRole": "AXWindow", "AXChildren": children}
        monkeypatch.setattr(ax, "window_element", lambda pid, window_id: window)
        return window

    return install


def file_field(path, *, x=10):
    return {
        "AXRole": "AXTextField",
        "AXURL": "reference:" + str(path),
        "AXValue": Path(path).name,
        "frame": ax.Frame(x, 20, 100, 20),
    }


def test_binding_is_serializable_and_scoped_to_seeded_source(owned):
    manifest, binding = owned
    assert finder.FinderBinding.from_record(json.loads(json.dumps(binding.to_record()))) == binding
    assert finder.rebind(binding, manifest, "file:" + binding.path) == binding
    for relative in ("decoy/asset.png", "original/asset.png", "inbox/keep.bin"):
        with pytest.raises(finder.FinderTargetError, match="owned|seeded"):
            finder.bind(manifest, "file:" + str(Path(manifest["root"]) / relative))


@pytest.mark.parametrize(
    "selector", ["asset.png", "file:relative", "file:/a/../b", "file:/a//b", "file:/a/./b"]
)
def test_selector_requires_exact_absolute_path(owned, selector):
    manifest, _ = owned
    with pytest.raises(finder.FinderTargetError, match="absolute|ABSOLUTE|aliases"):
        finder.bind(manifest, selector)


def test_same_name_in_another_directory_never_supplies_target(owned, boundary):
    manifest, binding = owned
    decoy = Path(manifest["root"]) / "decoy/asset.png"
    boundary([file_field(decoy)])
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.resolve(1, 2, binding, manifest)
    assert raised.value.reason == "file_target_missing"


def test_exact_url_wins_over_same_basename_and_id_renumbering(owned, boundary):
    manifest, binding = owned
    selected = file_field(binding.path)
    decoy = file_field(Path(manifest["root"]) / "decoy/asset.png", x=300)
    boundary([decoy, selected])
    target = finder.resolve(1, 2, binding, manifest)
    assert target.element is selected
    assert target.to_record()["binding"]["inode"] == binding.inode
    for new_id in (61, 60, 203):
        menu = SimpleNamespace(
            pid=1,
            window_id=2,
            menu=SimpleNamespace(candidates=[SimpleNamespace(id=new_id), SimpleNamespace(id=new_id + 1)]),
            frames={new_id: (10, 20, 100, 20), new_id + 1: (300, 20, 100, 20)},
            values={new_id: "asset.png", new_id + 1: "asset.png"},
            ax_roles={new_id: "AXTextField", new_id + 1: "AXTextField"},
        )
        assert finder.candidate_id(target, menu) == new_id


def test_duplicate_exact_file_urls_and_incomplete_tree_refuse(owned, boundary):
    manifest, binding = owned
    boundary([file_field(binding.path), file_field(binding.path, x=200)])
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.resolve(1, 2, binding, manifest)
    assert raised.value.reason == "file_target_ambiguous"
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.resolve(1, 2, binding, manifest, limit=2)
    assert raised.value.reason == "file_tree_incomplete"


def test_mismatched_value_or_missing_geometry_refuses(owned, boundary):
    manifest, binding = owned
    for key, value in (
        ("AXValue", "other.png"),
        ("frame", None),
        ("frame", ax.Frame(float("nan"), 20, 100, 20)),
    ):
        element = file_field(binding.path)
        element[key] = value
        boundary([element])
        with pytest.raises(finder.FinderTargetError) as raised:
            finder.resolve(1, 2, binding, manifest)
        assert raised.value.reason == "file_field_changed"


def test_rebind_requires_retained_inode_not_matching_bytes(owned):
    manifest, binding = owned
    # Simulate external mutation only: this is not an implementation UI action.
    source = Path(binding.path)
    source.rename(source.with_name("renamed.png"))
    rebound = finder.rebind(binding, manifest, "file:" + str(source.with_name("renamed.png")))
    assert rebound.inode == binding.inode
    assert rebound.path.endswith("/inbox/renamed.png")
    source.write_bytes(source.with_name("renamed.png").read_bytes())
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.rebind(binding, manifest, "file:" + str(source))
    assert raised.value.reason == "file_identity_changed"


def test_symlink_or_changed_manifest_cannot_widen_scope(owned):
    manifest, binding = owned
    source = Path(binding.path)
    source.rename(source.with_name("renamed.png"))
    source.symlink_to(source.with_name("renamed.png"))
    with pytest.raises(finder.FinderTargetError):
        finder.rebind(binding, manifest, "file:" + binding.path)
    modified = copy.deepcopy(manifest)
    modified["root_identity"]["inode"] += 1
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.rebind(binding, modified, "file:" + str(source.with_name("renamed.png")))
    assert raised.value.reason == "file_scope_changed"


def test_replacement_during_ax_read_is_detected(owned, boundary, monkeypatch):
    manifest, binding = owned
    boundary([file_field(binding.path)])
    original = finder.file_url_path

    def replace(url):
        source = Path(binding.path)
        source.rename(source.with_name("renamed.png"))
        source.write_bytes(source.with_name("renamed.png").read_bytes())
        return original(url)

    monkeypatch.setattr(finder, "file_url_path", replace)
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.resolve(1, 2, binding, manifest)
    assert raised.value.reason == "file_identity_changed"


def test_file_reference_url_uses_foundation_path_resolution(monkeypatch):
    calls = []

    class URL:
        def isFileURL(self):
            return True

        def host(self):
            return None

        def filePathURL(self):
            calls.append("resolved")
            return SimpleNamespace(path=lambda: "/owned/inbox/asset.png")

    monkeypatch.setitem(
        sys.modules, "Foundation", SimpleNamespace(NSURL=SimpleNamespace(URLWithString_=lambda value: URL()))
    )
    assert finder.file_url_path("file:///.file/id=6571367.387523412") == "/owned/inbox/asset.png"
    assert calls == ["resolved"]


def test_duplicate_current_candidate_geometry_is_not_guessed(owned, boundary):
    manifest, binding = owned
    boundary([file_field(binding.path)])
    target = finder.resolve(1, 2, binding, manifest)
    menu = SimpleNamespace(
        pid=1,
        window_id=2,
        menu=SimpleNamespace(candidates=[SimpleNamespace(id=1), SimpleNamespace(id=2)]),
        frames={1: (10, 20, 100, 20), 2: (10, 20, 100, 20)},
        values={1: "asset.png", 2: "asset.png"},
        ax_roles={1: "AXTextField", 2: "AXTextField"},
    )
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.candidate_id(target, menu)
    assert raised.value.reason == "file_candidate_ambiguous"
    menu.window_id = 3
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.candidate_id(target, menu)
    assert raised.value.reason == "file_window_changed"


@pytest.mark.parametrize("attribute", ["inventory", "AXRole", "AXChildren", "AXURL", "AXValue"])
def test_ax_read_failure_never_qualifies_a_partial_tree(owned, boundary, attribute):
    manifest, binding = owned
    found = file_field(binding.path)
    hidden_duplicate = file_field(binding.path, x=200)
    unreadable = {"AXRole": "AXGroup", "AXChildren": [hidden_duplicate]}
    if attribute == "inventory":
        unreadable["_inventory_error"] = -25204
    elif attribute in ("AXRole", "AXChildren"):
        unreadable["_errors"] = {attribute: -25204}
    else:
        hidden_duplicate["_errors"] = {attribute: -25204}
    boundary([found, unreadable])
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.resolve(1, 2, binding, manifest)
    assert raised.value.reason == "file_ax_unreadable"


def test_optional_no_value_differs_from_advertised_read_failure(owned, boundary):
    manifest, binding = owned
    leaf = {"AXRole": "AXGroup", "AXChildren": None, "_errors": {"AXChildren": -25212}}
    no_url = {
        "AXRole": "AXTextField",
        "AXURL": None,
        "_errors": {"AXURL": -25212},
    }
    boundary([file_field(binding.path), leaf, no_url])
    assert finder.resolve(1, 2, binding, manifest).binding == binding
    no_url["_errors"]["AXURL"] = -25204
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.resolve(1, 2, binding, manifest)
    assert raised.value.reason == "file_ax_unreadable"


def test_required_role_no_value_and_ax_cycles_refuse(owned, boundary):
    manifest, binding = owned
    unavailable_role = {"AXRole": None, "_errors": {"AXRole": -25212}}
    boundary([file_field(binding.path), unavailable_role])
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.resolve(1, 2, binding, manifest)
    assert raised.value.reason == "file_ax_unreadable"
    cyclic = {"AXRole": "AXGroup"}
    cyclic["AXChildren"] = [cyclic]
    boundary([file_field(binding.path), cyclic])
    with pytest.raises(finder.FinderTargetError) as raised:
        finder.resolve(1, 2, binding, manifest)
    assert raised.value.reason == "file_tree_cycle"
