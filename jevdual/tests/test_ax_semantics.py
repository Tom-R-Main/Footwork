"""Explicit AX ancestor context survives the driver's collapsed-group projection."""

from jevdual import ax


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
