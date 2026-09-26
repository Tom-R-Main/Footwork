"""Package D: delivery and the changes the element diff cannot see (jevdual.delivery), and how they
reach the receipt."""

from __future__ import annotations

from jevdual.delivery import (
    DELIVERY_WORDS,
    PageProbe,
    delivery_between,
    expects_input,
    navigated_between_steps,
)
from jevdual.effects import Effect
from jevdual.receipts import receipt_from_effect, receipt_text


def probe(**kw) -> PageProbe:
    base = {"origin": 1.0, "url": "https://s/inventory.html", "trusted": 0, "untrusted": 0}
    base |= {"scrolls": 0, "x": 0, "y": 0, "focus": ""} | kw
    return PageProbe(**base)


def noop() -> Effect:
    return Effect(False, False, 0, 0, 0, 1.0, False, False, "no visible change")


def test_a_dispatched_click_the_page_never_received_is_not_delivered():
    d = delivery_between(probe(trusted=2), probe(trusted=2), dispatched_input=True)
    assert d.word == "not_delivered"


def test_trusted_input_counts_as_delivered_and_script_clicks_are_named():
    assert delivery_between(probe(), probe(trusted=3), True).word == "delivered"
    assert delivery_between(probe(), probe(untrusted=1), True).word == "by_script"


def test_a_new_document_or_a_frame_is_not_guessed():
    assert delivery_between(probe(), probe(origin=2.0), True).word == "new_document"
    assert delivery_between(probe(), probe(frame_focus=True), True).word == "unknown"
    assert delivery_between(None, probe(), True).word == "unknown"
    assert delivery_between(probe(), probe(), False).word == "not_applicable"


def test_scroll_and_focus_are_observed():
    d = delivery_between(probe(), probe(trusted=1, y=400, focus="input#search"), True)
    assert d.observed == ("scrolled down 400px", "focus moved to input#search")
    assert delivery_between(probe(), probe(scrolls=2), False).observed == ("an inner region scrolled",)


def test_navigation_between_steps():
    assert navigated_between_steps(probe(), probe(url="https://s/cart.html")) == "https://s/cart.html"
    assert navigated_between_steps(probe(), probe()) is None


def test_expects_input():
    assert expects_input(["input", "click"]) and not expects_input(["navigate", "scroll", "done"])


def test_a_noop_whose_input_never_arrived_says_so():
    d = delivery_between(probe(), probe(), True)
    r = receipt_from_effect(
        2, ("click(button 'Add to cart')",), noop(), url_after="https://s/inventory.html", delivery=d
    )
    assert r.effect == "suspected_noop" and r.delivery == "not_delivered"
    assert "input dispatched, the page received none of it" in receipt_text(r)


def test_a_noop_whose_input_arrived_says_that_too():
    d = delivery_between(probe(), probe(trusted=2), True)
    r = receipt_from_effect(2, ("click(button 'Sort')",), noop(), delivery=d)
    assert r.effect == "suspected_noop" and "the page received the input" in receipt_text(r)


def test_a_click_that_only_focused_its_target_is_still_a_noop():
    d = delivery_between(probe(), probe(trusted=1, focus="button#add"), True)
    r = receipt_from_effect(3, ("click(button 'Add')",), noop(), url_after="https://s/", delivery=d)
    assert r.effect == "suspected_noop" and "also focus moved to button#add" in r.evidence


def test_a_scroll_action_that_scrolled_is_confirmed():
    d = delivery_between(probe(), probe(y=600), False)
    r = receipt_from_effect(3, ("scroll(down)",), noop(), url_after="https://s/", delivery=d)
    assert r.effect == "confirmed" and "scrolled down 600px" in r.evidence
    assert "received" not in receipt_text(r)  # a confirmed receipt states the change only


def test_a_delayed_navigation_is_reported_not_credited_to_this_step():
    r = receipt_from_effect(4, ("click(x)",), noop(), between="https://s/checkout-complete.html")
    assert r.effect == "suspected_noop"
    assert "before this step the page moved to /checkout-complete.html on its own" in r.evidence


def test_words_are_closed():
    assert set(DELIVERY_WORDS) >= {"delivered", "not_delivered", "by_script", "new_document", "unknown"}
