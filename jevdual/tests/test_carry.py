"""Package G: carried values (jevdual.carry)."""

from __future__ import annotations

import pytest
from jevdual import carry
from jevdual.menu import Candidate

META = {"surface": "browser", "app": "Chrome", "location": "https://s/item", "title": "Item"} | {
    "step": 3,
    "session": "A",
}


def cand(**kw) -> Candidate:
    base = {"id": 7, "label": "Price", "role": "textbox", "operations": ("type",)}
    return Candidate(**(base | kw))


def test_a_value_is_carried_with_its_source():
    c = carry.take("price", cand(value="$9.99"), **META)
    assert c.text == "$9.99" and c.part == "value" and c.element_label == "Price"
    assert (
        "read from browser Chrome at https://s/item (textbox 'Price', its value) at step 3" in c.provenance()
    )


def test_secrets_are_never_carried():
    with pytest.raises(carry.CarryError, match="secure field"):
        carry.take("pw", cand(input_type="password", value="x"), **META)
    with pytest.raises(carry.CarryError, match="secure field"):
        carry.take("pw", cand(has_value=True), **META)
    with pytest.raises(carry.CarryError, match="scrubbed secret"):
        carry.take("pw", cand(value="token {secret}"), **META)
    with pytest.raises(carry.CarryError, match="scrubbed secret"):
        carry.take_match("pw", r"token (\S+)", "token {secret}", **META)


def test_names_and_references():
    with pytest.raises(carry.CarryError, match="not a name"):
        carry.take("9 lives", cand(value="x"), **META)
    assert (
        carry.is_ref("@price") == "price" and carry.is_ref("price") is None and carry.is_ref("@a b") is None
    )


def test_a_carry_is_loaded_from_the_session_that_read_it(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    carry.store(a, carry.take("price", cand(value="$9.99"), **META))
    assert carry.load(a, "price").text == "$9.99"
    with pytest.raises(carry.CarryError, match="@price was not read in session"):
        carry.load(b, "price")


def test_a_match_carries_its_group_and_its_line():
    c = carry.take_match("total", r"Total: (\$[\d.]+)", "Items\nTotal: $32.39\nFinish", **META)
    assert c.text == "$32.39" and c.element_label == "Total: $32.39" and c.part == "match"


def test_the_file_oracle_is_byte_exact(tmp_path):
    c = carry.take("price", cand(value="$9.99"), **META)
    f = tmp_path / "f.txt"
    f.write_text("Bike light\r\n$9.99\r\n")
    assert carry.check_file(f, c).ok and carry.check_file(f, c).line == 2
    f.write_text("$9.99 \n")
    r = carry.check_file(f, c)
    assert not r.ok and "not equal" in r.detail
    assert not carry.check_file(tmp_path / "none.txt", c).ok


def test_the_append_oracle_names_what_went_wrong(tmp_path):
    c = carry.take("price", cand(value="£51.77"), **META)
    f = tmp_path / "doc.txt"
    f.write_text("Price carried:\n")
    before = carry.snapshot(tmp_path, f)
    assert carry.load_snapshot(tmp_path, f)["sha256"] == before["sha256"]
    f.write_text("Price carried:\n£51.77")
    r = carry.check_append(f, c, before)
    assert r.ok and r.line == 2
    f.write_text("Price carried:\n£51.77\n£51.77\n")  # a retry that inserted twice
    assert "inserted 2 times" in carry.check_append(f, c, before).detail
    f.write_text("£51.77\n")  # the earlier line was replaced
    assert "not preserved" in carry.check_append(f, c, before).detail
    f.write_text("Price carried:\nTotal £51.77\n")  # in the file, not as the value's own line
    assert "does not hold the value as a line" in carry.check_append(f, c, before).detail
    g = tmp_path / "other.txt"
    with pytest.raises(carry.CarryError, match="no snapshot"):
        carry.load_snapshot(tmp_path, g)
