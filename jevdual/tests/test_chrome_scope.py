from __future__ import annotations

import weakref

import pytest
from jevdual import ax
from jevdual.chrome_scope import METHOD, capture_tree


class Reader:
    def __init__(self, fail=None):
        self.fail = fail
        self.reads = []

    def key(self, element):
        return id(element)

    def attributes(self, element):
        if self.fail == (element.get("id"), "names"):
            raise ax.AXError("scope_read_failed", "fixture refusal")
        return frozenset(element)

    def read(self, element, name):
        self.reads.append((element.get("id"), name))
        if self.fail == (element.get("id"), name):
            raise ax.AXError("scope_read_failed", "fixture refusal")
        return element[name]


def node(role, *children, **attrs):
    return {"AXRole": role, **({"AXChildren": list(children)} if children else {}), **attrs}


def bar(value="127.0.0.1:1234", **attrs):
    return node("AXTextField", AXDescription="Address and search bar", AXValue=value, id="bar", **attrs)


def capture(root, **kwargs):
    return capture_tree(root, pid=123, window_id=456, reader=kwargs.pop("reader", Reader()), **kwargs)


def test_complete_toolbar_independent_of_unreadable_web_subtree():
    page = node("AXWebArea", {"broken": "page tree"}, id="page")
    reader = Reader(fail=("page", "AXChildren"))
    result = capture(node("AXWindow", node("AXToolbar", bar()), page), reader=reader)
    assert result.complete
    assert result.method == METHOD
    assert result.excluded_web_areas == 1
    assert len(result.address_bars) == 1
    assert result.address_bars[0].value == "127.0.0.1:1234"
    assert ("page", "AXChildren") not in reader.reads
    assert result.to_record()["pid"] == 123


def test_web_content_cannot_impersonate_toolbar_or_address_field():
    page = node("AXWebArea", node("AXToolbar", bar("evil.example")))
    result = capture(node("AXWindow", page, node("AXToolbar", bar())))
    assert result.complete
    assert [b.value for b in result.address_bars] == ["127.0.0.1:1234"]


def test_field_outside_toolbar_not_scope():
    result = capture(node("AXWindow", bar()))
    assert result.complete and not result.address_bars


def test_duplicate_native_address_fields_retained_for_guard_refusal():
    result = capture(node("AXWindow", node("AXToolbar", bar(), bar())))
    assert result.complete and len(result.address_bars) == 2


@pytest.mark.parametrize("failure", [("bar", "names"), ("bar", "AXRole"), ("bar", "AXValue")])
def test_trusted_region_read_failure_is_incomplete(failure):
    result = capture(node("AXWindow", node("AXToolbar", bar())), reader=Reader(fail=failure))
    assert not result.complete and result.errors == ("scope_read_failed",)


def test_error_in_unrelated_native_subtree_cannot_hide_second_bar():
    broken = node("AXGroup", id="broken")
    result = capture(
        node("AXWindow", node("AXToolbar", bar()), broken), reader=Reader(fail=("broken", "names"))
    )
    assert not result.complete


def test_node_and_depth_budgets_fail_closed():
    root = node("AXWindow", node("AXGroup", node("AXToolbar", bar())))
    assert capture(root, max_nodes=3).errors == ("node_limit",)
    assert capture(root, max_depth=2).errors == ("depth_limit",)
    assert capture(root, max_nodes=4, max_depth=3).complete


def test_cycle_fails_closed():
    root = node("AXWindow")
    root["AXChildren"] = [root]
    assert capture(root).errors == ("repeated_element",)


def test_transient_ax_wrappers_stay_alive_until_capture_finishes():
    class Element:
        def __init__(self, depth):
            self.depth = depth

    class TransientReader:
        def __init__(self):
            self.previous = []

        def key(self, element):
            assert all(previous() is not None for previous in self.previous)
            self.previous.append(weakref.ref(element))
            return id(element)

        def attributes(self, element):
            return frozenset({"AXRole", "AXChildren"}) if element.depth < 5 else frozenset({"AXRole"})

        def read(self, element, name):
            if name == "AXRole":
                return "AXWindow" if element.depth == 0 else "AXGroup"
            return [Element(element.depth + 1)]

    result = capture_tree(Element(0), pid=123, window_id=456, reader=TransientReader())
    assert result.complete and result.visited == 6


@pytest.mark.parametrize("bad", [{}, node("AXGroup"), {"AXRole": "AXWindow", "AXChildren": None}])
def test_invalid_native_tree_fails_closed(bad):
    assert not capture(bad).complete


def test_unreadable_value_is_not_a_url_claim():
    result = capture(node("AXWindow", node("AXToolbar", bar(value=123))))
    assert result.complete and result.address_bars[0].value is None


def test_unknown_label_not_guessed_from_url_value():
    result = capture(node("AXWindow", node("AXToolbar", node("AXTextField", AXValue="127.0.0.1:1234"))))
    assert result.complete and not result.address_bars


@pytest.mark.parametrize("kwargs", [{"max_nodes": 0}, {"max_nodes": True}, {"max_depth": -1}])
def test_invalid_budget_rejected(kwargs):
    with pytest.raises(ValueError):
        capture(node("AXWindow"), **kwargs)
