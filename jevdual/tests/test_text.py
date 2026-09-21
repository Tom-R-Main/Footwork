import asyncio

from jevdual.menu import Candidate, Menu
from jevdual.text import MAX_TEXT_CHARS, TextHelper, TextSource, literal_from_task

MENU = Menu(url="http://s/form.html", title="Form", page_text="", candidates=(), by_operation={})
NAME = Candidate(id=1, label="Name", role="input", operations=("type", "click", "enter"), input_type="text")
EMAIL = Candidate(id=2, label="Email address", role="input", operations=("type", "click", "enter"), input_type="email")
PW = Candidate(id=3, label="Password", role="input", operations=("type", "click", "enter"), input_type="password")
TOPIC = Candidate(id=4, label="Topic", role="select", operations=("select", "click"), options=("Billing", "Support"))


def test_single_literal():
    assert literal_from_task('Search the catalog for "lantern" and show results.', NAME) == "lantern"
    assert literal_from_task("Search for lanterns", NAME) is None


def test_multiple_literals_bind_by_label():
    task = 'Fill the form with name "Ada Lovelace" and email "ada@example.com", then submit.'
    assert literal_from_task(task, NAME) == "Ada Lovelace"
    assert literal_from_task(task, EMAIL) == "ada@example.com"
    assert literal_from_task(task, TOPIC) is None


def test_source_order_and_counters():
    async def helper(task, target, menu):
        return "Support"

    src = TextSource(helper=helper, secret_placeholder=lambda c: "<secret>pw</secret>" if c.input_type == "password" else None)
    assert asyncio.run(src.compose('Type "hi" in name', NAME, MENU)) == "hi"
    assert asyncio.run(src.compose("log in", PW, MENU)) == "<secret>pw</secret>"
    assert asyncio.run(src.compose("choose the support topic", TOPIC, MENU)) == "Support"
    assert src.calls == {"literal": 1, "secret": 1, "helper": 1, "none": 0}
    assert asyncio.run(TextSource().compose("choose the support topic", TOPIC, MENU)) is None


def test_literal_not_in_options_is_rejected():
    assert asyncio.run(TextSource().compose('Pick "Sales"', TOPIC, MENU)) is None


def test_strict_contract():
    p = TextHelper.parse_field_text
    assert p('{"text": "hello"}') == "hello"
    assert p('Sure! {"text": "hello"}') is None
    assert p('{"text": "hello", "note": "x"}') is None
    assert p('{"text": 5}') is None
    assert p('{"text": ""}') is None
    assert p(json_long := '{"text": "' + "x" * (MAX_TEXT_CHARS + 1) + '"}') is None and json_long


def test_password_never_typed_from_literal():
    assert asyncio.run(TextSource().compose('use password "hunter2"', PW, MENU)) is None
