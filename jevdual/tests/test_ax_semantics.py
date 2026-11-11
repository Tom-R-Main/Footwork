"""Explicit AX ancestor context survives the driver's collapsed-group projection."""

import pytest
from jevdual import ax


def _install_modal_ax_tree(monkeypatch):
    import ctypes
    import sys
    from types import SimpleNamespace

    parent = {"AXRole": "AXWindow", "_pid": 77, "_wid": 40335}
    sheet = {"AXRole": "AXSheet", "AXDescription": "save", "_pid": 77, "_wid": 60066,
             "AXParent": parent, "AXWindow": parent, "AXChildren": []}
    parent["AXChildren"] = [sheet]
    app = {"AXWindows": [parent], "AXFocusedWindow": sheet}
    pointers, mutations = {}, []

    def pointer(element):
        pointers[id(element)] = element
        return id(element)

    def window(pointer, out):
        number = pointers[pointer].get("_wid", 0)
        ctypes.cast(out, ctypes.POINTER(ctypes.c_uint32))[0] = number
        return 0 if number else -25212

    monkeypatch.setitem(sys.modules, "objc", SimpleNamespace(pyobjc_id=pointer))
    monkeypatch.setitem(sys.modules, "CoreFoundation", SimpleNamespace(CFEqual=lambda left, right: left is right))
    monkeypatch.setitem(sys.modules, "ApplicationServices", SimpleNamespace(
        AXUIElementCreateApplication=lambda pid: app,
        AXUIElementGetPid=lambda element, out: (0, element.get("_pid")),
        AXUIElementSetAttributeValue=lambda *args: mutations.append(("set", args)) or 0,
        AXUIElementPerformAction=lambda *args: mutations.append(("action", args)) or 0,
    ))
    monkeypatch.setattr(ax, "_hi", lambda: window)
    monkeypatch.setattr(ax, "_attr", lambda element, name: element.get(name) if element is not None else None)
    return app, parent, sheet, mutations


def test_exact_sheet_resolution_preserves_requested_parent_and_skips_unneeded_sheet_raise(monkeypatch):
    _, parent, sheet, mutations = _install_modal_ax_tree(monkeypatch)
    assert ax.window_element(77, 40335) is parent
    assert ax.window_element(77, 60066) is sheet
    ax.raise_window(77, 60066)
    assert mutations == []
    ax.raise_window(77, 40335)
    assert [kind for kind, _ in mutations] == ["set", "action"]


def test_exact_sheet_may_use_focused_reference_only_with_direct_parent_proof(monkeypatch):
    _, parent, sheet, _ = _install_modal_ax_tree(monkeypatch)
    parent["AXChildren"] = []
    assert ax.window_element(77, 60066) is sheet


def test_non_key_sheet_is_not_raised_through_its_parent(monkeypatch):
    import pytest

    app, parent, _, mutations = _install_modal_ax_tree(monkeypatch)
    app["AXFocusedWindow"] = parent
    with pytest.raises(ax.AXError, match="not the exact key window"):
        ax.raise_window(77, 60066)
    assert mutations == []


def test_sheet_resolution_refuses_unproven_or_ambiguous_ownership(monkeypatch):
    import pytest

    _, parent, sheet, _ = _install_modal_ax_tree(monkeypatch)
    sheet["_pid"] = 88
    with pytest.raises(ax.AXError): ax.window_element(77, 60066)
    sheet["_pid"] = 77
    other = {"AXRole": "AXWindow", "_pid": 77, "_wid": 999}
    sheet["AXWindow"] = other
    with pytest.raises(ax.AXError): ax.window_element(77, 60066)
    sheet["AXWindow"] = parent
    sheet.pop("AXParent")
    with pytest.raises(ax.AXError): ax.window_element(77, 60066)
    sheet["AXParent"] = parent
    duplicate = {**sheet}
    parent["AXChildren"].append(duplicate)
    with pytest.raises(ax.AXError, match="multiple AXSheets"):
        ax.window_element(77, 60066)


def test_sheet_resolution_refuses_webarea_inference_and_overbound_traversal(monkeypatch):
    import pytest

    app, parent, sheet, _ = _install_modal_ax_tree(monkeypatch)
    sheet["AXParent"] = {"AXRole": "AXWebArea", "_pid": 77, "AXParent": parent}
    with pytest.raises(ax.AXError): ax.window_element(77, 60066)
    sheet["AXParent"] = parent
    parent["AXChildren"] = [{"AXRole": "AXGroup", "_pid": 77} for _ in range(513)]
    with pytest.raises(ax.AXError, match="enumeration exceeded"):
        ax.window_element(77, 60066)
    assert ax.window_element(77, 40335) is parent
    app["AXFocusedWindow"] = parent


def test_link_url_decodes_complete_url_without_truncation_or_normalization(monkeypatch):
    from types import SimpleNamespace

    url = "https://example.test/song/" + "a" * 200 + "?v=1#part"
    for raw in (url, SimpleNamespace(absoluteString=lambda: url)):
        monkeypatch.setattr(ax, "_attr", lambda element, name, raw=raw:
                            raw if name == "AXURL" else "Generated song")
        assert ax.link_url("link", label="Generated song") == url
        assert ax.link_url("link", label="Replaced link") is None


def test_link_url_rejects_incomplete_unsafe_or_unsupported_values(monkeypatch):
    for raw in (None, "", "/song/a", "javascript:void(0)", "file:///tmp/song", "https:///song",
                "https://example.test:bad/song", "https://user:password@example.test/song",
                "https://example.test/white space", "https://example.test/\nend",
                "https://example.test/" + "a" * 2048, object()):
        monkeypatch.setattr(ax, "_attr", lambda element, name, raw=raw: raw)
        assert ax.link_url("link") is None


def test_control_identity_requires_exact_name_id_and_closest_direct_webarea(monkeypatch):
    monkeypatch.setattr(ax, "_attr", lambda element, name: element.get(name))
    page = {"AXRole": "AXWebArea", "AXURL": "https://example.test/song/a"}
    group = {"AXRole": "AXGroup", "AXParent": page}
    control = {"AXRole": "AXPopUpButton", "AXTitle": "More options", "AXDOMIdentifier": "base-ui-_R_hero_", "AXParent": group}
    proof = ax.control_identity(control, label="More options")
    assert proof == {"dom_id": "base-ui-_R_hero_", "document_url": "https://example.test/song/a", "web_area": page}
    assert ax.control_identity(control, label="Different options") is None
    control["AXParent"] = {"AXRole": "AXWebArea", "AXURL": "/relative", "AXParent": page}
    assert ax.control_identity(control, label="More options") is None  # never borrow the outer document
    control["AXParent"] = {"AXRole": "AXWindow", "AXURL": "https://example.test/not-a-document"}
    assert ax.control_identity(control, label="More options") is None
    control["AXParent"] = group
    for value in (None, "", "contains whitespace", "bad\nidentifier", "x" * 513):
        control["AXDOMIdentifier"] = value
        assert ax.control_identity(control, label="More options") is None
    control["AXDOMIdentifier"] = "x" * 512
    assert ax.control_identity(control, label="More options")["dom_id"] == "x" * 512


def test_control_identity_bounds_parent_walk_and_does_not_identify_main_play_without_id(monkeypatch):
    reads = []

    def attribute(element, name):
        reads.append(name)
        return element.get(name)

    monkeypatch.setattr(ax, "_attr", attribute)
    cyclic = {"AXRole": "AXGroup"}
    cyclic["AXParent"] = cyclic
    control = {"AXRole": "AXButton", "AXTitle": "Play", "AXDOMIdentifier": "play", "AXParent": cyclic}
    assert ax.control_identity(control, label="Play") is None
    assert reads.count("AXParent") == 32
    control["AXDOMIdentifier"] = ""
    reads.clear()
    assert ax.control_identity(control, label="Play") is None
    assert "AXParent" not in reads


def test_unqualified_browser_hrefs_do_not_refine_native_peer_identity():
    from jevdual.menu import Candidate, peer_position

    peers = [Candidate(index, "Song", "link", ("click",), href=f"https://example.test/{index}")
             for index in (1, 2)]
    assert peer_position(peers, 1) == (0, 2)
    saved = [{**candidate.to_state(), "href_qualified": True} for candidate in peers]
    assert peer_position(saved, 1) == (0, 1)


def test_selected_text_preserves_empty_and_whitespace_values(monkeypatch):
    import pytest

    for value in ("", "\n", " 😀 \t"):
        monkeypatch.setattr(ax, "_attr", lambda element, name, value=value: value if name == "AXSelectedText" else None)
        assert ax.selected_text("field") == value
    for value in (None, 0, False):
        monkeypatch.setattr(ax, "_attr", lambda element, name, value=value: value)
        with pytest.raises(ax.AXError, match="selected text is unavailable"):
            ax.selected_text("field")


def test_focus_preparation_acknowledgement_is_not_independent_focus_proof(monkeypatch):
    import sys
    from types import SimpleNamespace

    import pytest

    writes, comparisons = [], []
    target, fresh_reference, sibling = {"resource": "field"}, {"resource": "field"}, {"resource": "other"}
    focused = [fresh_reference]
    error = [0]

    def write(element, attribute, value):
        writes.append((element, attribute, value))
        return error[0]

    def equal(left, right):
        comparisons.append((left, right))
        return left["resource"] == right["resource"]

    monkeypatch.setitem(sys.modules, "ApplicationServices", SimpleNamespace(
        AXUIElementSetAttributeValue=write, AXUIElementCreateApplication=lambda pid: ("app", pid),
    ))
    monkeypatch.setitem(sys.modules, "CoreFoundation", SimpleNamespace(CFEqual=equal))
    monkeypatch.setattr(ax, "_attr", lambda element, name: focused[0] if name == "AXFocusedUIElement" else None)
    monkeypatch.setattr(ax, "focused_window_id", lambda pid: 42)
    ax.focus_text_field_ack(target)
    assert writes == [(target, "AXFocused", True)]
    assert ax.focused_element_matches(77, 42, target) is True
    assert comparisons == [(fresh_reference, target)]  # CFEqual, not Python reference identity
    assert ax.focused_element_matches(77, 43, target) is False
    focused[0] = sibling
    assert ax.focused_element_matches(77, 42, target) is False
    focused[0] = None
    assert ax.focused_element_matches(77, 42, target) is False
    error[0] = -25205
    with pytest.raises(ax.AXError, match="did not acknowledge"):
        ax.focus_text_field_ack(target)


def test_collapsed_group_name_comes_from_actual_parent_not_siblings(monkeypatch):
    monkeypatch.setattr(ax, "_attr", lambda node, key: node.get(key))
    group = {"AXRole": "AXGroup", "AXDescription": "example.test"}
    link = {"AXRole": "AXLink", "AXTitle": "MANAGE", "AXParent": group}
    assert ax.semantic_section(link) == "example.test"
    group.pop("AXDescription")
    group["AXChildren"] = [{"AXRole": "AXStaticText", "AXValue": "nearby.test"}, link]
    assert ax.semantic_section(link) is None


def test_semantic_section_stops_at_web_area_and_bounds_cycles(monkeypatch):
    reads = []

    def attribute(node, key):
        reads.append(key)
        return node.get(key)

    monkeypatch.setattr(ax, "_attr", attribute)
    page = {"AXRole": "AXWebArea", "AXTitle": "Page title"}
    assert ax.semantic_section({"AXParent": page}) is None
    cyclic = {"AXRole": "AXGroup"}
    cyclic["AXParent"] = cyclic
    reads.clear()
    assert ax.semantic_section(cyclic) is None
    assert len(reads) <= 32 * 4


@pytest.mark.parametrize('role', ['AXButton', 'AXPopUpButton'])
@pytest.mark.parametrize('change', ['none', 'absent_id', 'unreadable_id', 'bad_id', 'named', 'unknown_name',
                                   'wrong_pid', 'wrong_window', 'wrong_role', 'bad_url', 'cycle'])
def test_opaque_control_backing_requires_independent_bound_scope(monkeypatch, role, change):
    import sys
    from types import SimpleNamespace

    window = {'AXRole': 'AXWindow'}
    page = {'AXRole': 'AXWebArea', 'AXURL': 'https://example.test/edit/a', 'AXParent': window}
    control = {'AXRole': role, 'AXTitle': '', 'AXDescription': '', 'AXDOMIdentifier': 'literal-id', 'AXParent': page}
    monkeypatch.setattr(ax, '_attr', lambda element, key: element.get(key))
    monkeypatch.setattr(ax, 'same_element', lambda left, right: left is right)
    monkeypatch.setitem(sys.modules, 'ApplicationServices', SimpleNamespace(
        AXUIElementGetPid=lambda element, _: (0, 78 if change == 'wrong_pid' else 77)))
    if change == 'absent_id': control['AXDOMIdentifier'] = ''
    if change == 'unreadable_id': control['AXDOMIdentifier'] = None
    if change == 'bad_id': control['AXDOMIdentifier'] = 'bad id'
    if change == 'named': control['AXTitle'] = 'Play'
    if change == 'unknown_name': control['AXDescription'] = None
    if change == 'wrong_window': page['AXParent'] = {'AXRole': 'AXWindow'}
    if change == 'wrong_role': control['AXRole'] = 'AXGroup'
    if change == 'bad_url': page['AXURL'] = '/relative'
    if change == 'cycle': page['AXParent'] = page
    proof = ax.control_backing(control, pid=77, window=window, role=role)
    if change in ('none', 'absent_id', 'named', 'unknown_name'):
        assert proof['dom_id'] == control['AXDOMIdentifier']
        assert proof['unnamed'] is (change in ('none', 'absent_id'))
    else:
        assert proof is None
