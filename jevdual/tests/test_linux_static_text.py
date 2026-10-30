"""Pinned Linux markdown is a passive preview, never action or exact-value authority."""

import tarfile
from pathlib import Path

import pytest
from jevdual.linux_static_text import project_static_text, static_text


def test_passive_text_keeps_order_but_not_controls_titles_descriptions_or_values():
    tree = '''- frame = "Window title"
  - static = "First visible text"
  - label = "Quantity"
  - paragraph = "Longer paragraph"
  - heading = "Heading"
  - static text = "Final visible text"
  - [0] push button "Button label" (description "Tooltip") [actions=[click]]
  - push button = "Disabled button" (disabled)
  - [1] text "Input label" value="Input value" [actions=[]]
  - image = "Image alternative"
  - menu = "File"
'''
    assert static_text(tree) == ["First visible text", "Quantity", "Longer paragraph", "Heading",
                                 "Final visible text"]
    result = project_static_text(tree)
    assert result.preview_only is True
    assert not result.input_truncated and not result.output_truncated


def test_password_roles_and_descendant_text_are_omitted():
    tree = '''- frame = "Application"
  - password text = "secret"
    - static = "nested secret"
  - [0] password text "Password label" value="secret2" [actions=[]]
    - label = "nested secret2"
  - static text = "Public text"
'''
    assert static_text(tree) == ["Public text"]


def test_multiline_control_name_does_not_create_fake_passive_node():
    tree = '''- [0] text "first line
  - static = "inner text"
last line" value="first line
  - static = "inner text"
last line" [actions=[]]
- static = "Real passive text"
'''
    assert static_text(tree) == ["Real passive text"]


def test_literal_unicode_whitespace_backslashes_and_multiline_preview():
    assert static_text('- static = "α🙂\\t  "\n- paragraph = "first\nsecond"\n') == ["α🙂\\t  ", "first\nsecond"]


def test_unescaped_embedded_quotes_are_marked_ambiguous_not_decoded():
    result = project_static_text('- static = "She said "hello""\n- static = "Clear text"\n')
    assert result.lines == ("Clear text",)
    assert result.ambiguous_records == 1 and result.preview_only


def test_unknown_or_indexed_static_variants_do_not_supply_text():
    tree = '- [3] label "Action label" [actions=[click]]\n- text = "Unqualified text field"\n'
    result = project_static_text(tree)
    assert result.lines == ()
    assert result.ambiguous_records == 1


@pytest.mark.parametrize("cap", [0, 1, 4, 6, 7])
def test_output_bound_includes_joining_newlines(cap):
    result = project_static_text('- static = "abc"\n- static = "def"\n', max_chars=cap)
    assert len("\n".join(result.lines)) <= cap
    assert result.output_truncated is (cap < 7)
    assert result.preview_only


def test_source_and_record_bounds_do_not_promote_a_cut_record():
    result = project_static_text('- static = "' + 'x' * 1_048_576 + '"\n')
    assert result.lines == () and result.input_truncated and result.ambiguous_records
    result = project_static_text('- static = "' + 'x' * 65536 + '"\n')
    assert result.lines == () and result.ambiguous_records


def test_missing_and_invalid_inputs():
    assert static_text(None) == []
    with pytest.raises(ValueError):
        static_text('', max_chars=True)
    with pytest.raises(TypeError):
        static_text({"text": "not markdown"})


def test_render_contract_is_in_pinned_native_source():
    archive = Path(__file__).resolve().parents[1] / "vendor/cua-driver/native-source.tar.gz"
    with tarfile.open(archive) as source:
        raw = source.extractfile("libs/cua-driver/rust/crates/platform-linux/src/atspi/native.rs").read().decode()
    assert '"{indent}- {role} = \\"{name}\\"{marker}' in raw
    assert '"label" | "static" | "static text"' in raw
    assert 'count.min(4096)' in raw
