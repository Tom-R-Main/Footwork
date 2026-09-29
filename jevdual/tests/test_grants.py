"""Package H: a grant clears one exact effect on one resource (docs/plans/grants.md)."""

from __future__ import annotations

from jevdual import grants
from jevdual.grants import Proposal, issue, why_not

BASE = Proposal(
    op="append",
    location="file:///Users/x/draft.txt",
    element_role="textbox",
    element_label="text area",
    arguments="£51.77",
    value="Price:",
)


def with_(**kw) -> Proposal:
    return Proposal(**({**BASE.__dict__} | kw))


def test_the_granted_effect_is_cleared():
    assert why_not(issue(BASE), BASE) is None


def test_permission_does_not_transfer():
    g = issue(BASE)
    assert "and this is file:///Users/x/other.txt" in why_not(g, with_(location="file:///Users/x/other.txt"))
    assert "and this is textbox 'Notes'" in why_not(g, with_(element_label="Notes"))
    assert why_not(g, with_(arguments="£99.00")) == "the arguments differ from the granted ones"
    assert why_not(g, with_(value="Price: £51.77")) == "the element's value changed since the grant"
    assert "not click" in why_not(g, with_(op="click"))
    # a browser tab that navigated is another resource
    web = issue(with_(location="https://shop.example/cart"))
    assert why_not(web, with_(location="https://shop.example/checkout")) is not None


def test_a_one_use_grant_does_not_clear_a_retry(tmp_path):
    grants.record(tmp_path, issue(BASE, uses=1))
    first, _ = grants.consume(tmp_path, BASE)
    assert first is not None
    again, why = grants.consume(tmp_path, BASE)
    assert again is None and "no uses left" in why[0]


def test_a_menu_grant_binds_the_selection():
    trash = Proposal(
        op="menu",
        location="file:///Users/x/scratch/",
        element_role=None,
        element_label=None,
        arguments="File > Move to Trash",
        value=None,
        selection=("a.txt",),
    )
    g = issue(trash)
    assert why_not(g, trash) is None
    other = Proposal(**({**trash.__dict__} | {"selection": ("b.txt",)}))
    assert "the selection is ['b.txt']" in why_not(g, other)


def test_a_grant_for_one_of_several_identical_rows_does_not_clear_another():
    """Q19 R2: three identical "Delete draft" links; a grant for the second must not clear the first."""
    second = Proposal(
        **({**BASE.__dict__} | {"op": "click", "arguments": None, "value": None, "element_ref": "2 of 3"})
    )
    g = issue(second)
    assert why_not(g, second) is None
    first = Proposal(**({**second.__dict__} | {"element_ref": "1 of 3"}))
    assert "2 of 3, and this is 1 of 3" in why_not(g, first)


def test_element_ref_counts_look_alikes():
    from types import SimpleNamespace

    from jevdual.menu import Candidate
    from jevdual.session import _element_ref

    links = [Candidate(id=i, label="Delete draft", role="link", operations=("click",)) for i in (0, 1, 2)]
    nm = SimpleNamespace(
        menu=SimpleNamespace(
            candidates=[*links, Candidate(id=5, label="Save", role="button", operations=("click",))]
        )
    )
    assert _element_ref(nm, links[1]) == "2 of 3" and _element_ref(nm, nm.menu.candidates[3]) == ""
