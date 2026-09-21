import json
import os

import pytest
from jevdual import patch


def test_orjson_decode_patch_is_idempotent_and_equivalent():
    from cdp_use import client

    if os.environ.get("JEVDUAL_PURE_PY") == "1":
        assert patch.install_orjson_decode() is False
        return
    assert patch.install_orjson_decode() is True
    assert patch.install_orjson_decode() is True
    assert patch.active_patches() == {"orjson_decode": True}
    msg = {"id": 7, "result": {"strings": ["a", "b"], "n": 1.5, "u": "é", "nested": [1, [2, 3]]}}
    raw = json.dumps(msg)
    assert client.json.loads(raw) == msg
    assert client.json.loads(raw.encode()) == msg
    assert isinstance(client.json.dumps(msg), str)


@pytest.mark.skipif(os.environ.get("JEVDUAL_PURE_PY") == "1", reason="pure-python mode")
def test_orjson_matches_stdlib_on_recorded_snapshot():
    import orjson

    from tests.fixtures.loader import load_fixture

    fx = load_fixture("wikipedia-python")
    raw = json.dumps({"id": 1, "result": fx.snapshot})
    assert orjson.loads(raw) == json.loads(raw)


def _pipeline(slug):
    from tests.fixtures import replay

    # Bypass replay's @cache so the patched run really re-executes the pipeline.
    state, _root, timing = replay.replay_serialized.__wrapped__(slug)
    return sorted(state.selector_map), state.llm_representation(), timing


@pytest.mark.skipif(os.environ.get("JEVDUAL_PURE_PY") == "1", reason="pure-python mode")
def test_paint_order_patch_rebinds_the_serializer_import():
    from browser_use.dom.serializer import paint_order as po_mod
    from browser_use.dom.serializer import serializer as ser_mod
    from jevdual import _native

    if _native.native("paint_order") is None:
        pytest.skip("native paint_order not built")
    try:
        assert patch.install_paint_order() is True
        assert patch.install_paint_order() is True
        assert ser_mod.PaintOrderRemover is patch._NativePaintOrderRemover
        assert po_mod.PaintOrderRemover is patch._NativePaintOrderRemover
        assert patch.active_patches()["paint_order"] is True
    finally:
        patch.uninstall()
    assert ser_mod.PaintOrderRemover is po_mod.PaintOrderRemover
    assert "paint_order" not in patch.active_patches()


def test_snapshot_patch_is_opt_in(monkeypatch):
    from jevdual._adapters import snapshot_lookup as adapter

    monkeypatch.delenv("JEVDUAL_NATIVE_SNAPSHOT", raising=False)
    assert adapter.available() is False
    assert patch.install_snapshot_lookup() is False
    assert "snapshot_lookup" not in patch.active_patches()


@pytest.mark.skipif(os.environ.get("JEVDUAL_PURE_PY") == "1", reason="pure-python mode")
def test_snapshot_patch_rebinds_service_import_when_opted_in(monkeypatch):
    from browser_use.dom import enhanced_snapshot as es_mod
    from browser_use.dom import service as svc_mod
    from jevdual._adapters import snapshot_lookup as adapter

    monkeypatch.setenv("JEVDUAL_NATIVE_SNAPSHOT", "1")
    if not adapter.available():
        pytest.skip("native snapshot_lookup not built")
    try:
        assert patch.install_snapshot_lookup() is True
        assert svc_mod.build_snapshot_lookup is adapter.snapshot_lookup
        assert es_mod.build_snapshot_lookup is adapter.snapshot_lookup
    finally:
        patch.uninstall()
    assert svc_mod.build_snapshot_lookup is es_mod.build_snapshot_lookup


@pytest.mark.skipif(os.environ.get("JEVDUAL_PURE_PY") == "1", reason="pure-python mode")
def test_patched_pipeline_equals_unpatched_on_every_fixture(monkeypatch):
    """The whole replayed DOM pipeline (get_dom_tree + serializer) is identical with patches on."""
    from jevdual import _native

    from tests.fixtures.loader import fixture_slugs

    if _native.native("paint_order") is None:
        pytest.skip("native paint_order not built")
    monkeypatch.setenv("JEVDUAL_NATIVE_SNAPSHOT", "1")
    patch.uninstall()
    before = {slug: _pipeline(slug)[:2] for slug in fixture_slugs()}
    try:
        active = patch.install()
        assert active.get("paint_order") is True
        after = {slug: _pipeline(slug)[:2] for slug in fixture_slugs()}
    finally:
        patch.uninstall()
    for slug in before:
        assert before[slug][0] == after[slug][0], f"{slug}: selector_map keys differ"
        assert before[slug][1] == after[slug][1], f"{slug}: llm_representation differs"


def test_describe_shape():
    d = patch.describe()
    assert set(d) == {"patches", "backends"}
    assert set(d["backends"]) >= {"paint_order", "snapshot_lookup", "element_hashes", "evidence_match"}


@pytest.mark.skipif(os.environ.get("JEVDUAL_PURE_PY") == "1", reason="pure-python mode")
def test_lazy_uuid_patch_keeps_pipeline_equal():
    from browser_use.dom import service, views

    from tests.fixtures.replay import replay_serialized

    patch.uninstall()
    before, _, _ = replay_serialized.__wrapped__("modal-over-content")
    assert patch.install_lazy_uuid() is True
    try:
        after, root, _ = replay_serialized.__wrapped__("modal-over-content")
        assert isinstance(root, views.EnhancedDOMTreeNode)
        assert root.uuid == ""
        # history matching hashes nodes; the subclass must keep upstream's __hash__ and __eq__
        node = next(iter(after.selector_map.values()))
        assert isinstance(hash(node), int) and node == node and {node: 1}[node] == 1
        assert before.selector_map.keys() == after.selector_map.keys()
        assert before.llm_representation() == after.llm_representation()
    finally:
        patch.uninstall()
    assert service.EnhancedDOMTreeNode is views.EnhancedDOMTreeNode
