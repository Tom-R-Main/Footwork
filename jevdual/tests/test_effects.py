from jevdual.effects import diff
from jevdual.menu import Candidate, Menu


def menu(url="http://x/", title="Home", text="hello world " * 50, cands=None, tabs=()):
    cands = tuple(cands or [])
    return Menu(url=url, title=title, page_text=text, candidates=cands, by_operation={}, tabs=tabs)


def link(i, label, href=None):
    return Candidate(id=i, label=label, role="link", operations=("click",), href=href or f"/{label.lower()}")


def field(i, label, value=None):
    return Candidate(id=i, label=label, role="textbox", operations=("type", "click", "enter"), value=value, input_type="text")


def test_identical_is_no_effect():
    m = menu(cands=[link(1, "About"), field(2, "Search")])
    e = diff(m, m)
    assert e.no_effect and e.summary == "no visible change"


def test_reindexed_same_elements_is_no_effect():
    a = menu(cands=[link(1, "About"), link(2, "List")])
    b = menu(cands=[link(7, "About"), link(9, "List")])  # selector indices reallocated
    assert diff(a, b).no_effect


def test_navigation_is_effect():
    a = menu(url="http://x/", cands=[link(1, "About")])
    b = menu(url="http://x/about.html", title="About", text="about page " * 50, cands=[link(1, "Home")])
    e = diff(a, b)
    assert e.url_changed and not e.no_effect
    assert "navigated / -> /about.html" in e.summary


def test_typing_changes_value_is_effect():
    a = menu(cands=[field(2, "Search", value="")])
    b = menu(cands=[field(2, "Search", value="hello")])
    e = diff(a, b)
    assert e.changed == 1 and not e.no_effect and "values changed" in e.summary


def test_dialog_and_tabs():
    a = menu(cands=[link(1, "About")])
    b = menu(cands=[link(1, "About"), link(3, "Close")])
    e = diff(a, b, prev_dialog=None, cur_dialog={"type": "alert"})
    assert e.dialog_changed and e.added == 1 and "dialog opened" in e.summary
    t = diff(a, menu(cands=[link(1, "About")], tabs=({"id": 1}, {"id": 2})))
    assert t.tabs_changed and not t.no_effect


def test_small_text_drift_is_not_an_effect():
    base = "row " * 400
    a = menu(text=base)
    b = menu(text=base + "x")
    assert diff(a, b).no_effect


def test_first_observation():
    e = diff(None, menu(cands=[link(1, "About")]))
    assert e.url_changed and e.added == 1 and e.summary.startswith("first observation")
