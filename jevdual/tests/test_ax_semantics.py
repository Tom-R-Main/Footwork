"""Explicit AX ancestor context survives the driver's collapsed-group projection."""

from jevdual import ax


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
