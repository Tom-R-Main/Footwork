"""Linux action-space safety: action names and independent text capability evidence."""

import pytest
from jevdual.linux_projection import PASSWORD_ROLES, TEXT_ROLES, normalize_role, project_element


@pytest.mark.parametrize("role", ["entry", "text", "textbox", "editbar", "search box"])
def test_readable_text_does_not_gain_input_from_actions_or_multiline(role):
    expected = "searchbox" if role == "search box" else "textbox"
    # GTK4 advertises editing commands even on text whose editability is unqualified.
    assert project_element(role, ["buffer.delete-line", "clipboard.paste", "activate"], multiline=True) == (
        expected, (),
    )


@pytest.mark.parametrize("unqualified", [None, False, "true", 1])
def test_editability_requires_a_qualified_boolean(unqualified):
    assert project_element("entry", ["set-text"], editable=unqualified) == ("textbox", ())


def test_multiline_is_separately_qualified_before_append_is_offered():
    assert project_element("text", editable=True) == ("textbox", ("type", "enter"))
    assert project_element("text", editable=True, multiline=True) == ("textbox", ("type", "enter", "append"))
    assert project_element("text", editable=True, multiline="true") == ("textbox", ("type", "enter"))


def test_password_is_distinguishable_from_readable_text_and_passive_password_is_omitted():
    assert "password text" in PASSWORD_ROLES <= TEXT_ROLES
    assert normalize_role(" Password Text ") in PASSWORD_ROLES
    assert project_element("password text", ["activate"]) is None
    assert project_element("password text", editable=True) == ("textbox", ("type", "enter"))


@pytest.mark.parametrize("action", ["buffer.delete-line", "clipboard.paste", "delete", "set_value", "0", ""])
def test_arbitrary_actions_never_become_click(action):
    assert project_element("push button", [action]) == ("button", ())
    assert project_element("paragraph", [action]) is None


@pytest.mark.parametrize("action", ["gtk.Activate", " widget.Do_Default ", "Click-Ancestor", "press"])
def test_named_activation_uses_pinned_driver_normalization(action):
    assert project_element("push button", [action]) == ("button", ("click",))


@pytest.mark.parametrize("role", ["check box", "checkbox"])
@pytest.mark.parametrize("action", ["check", "chromium.Un_Check"])
def test_check_and_uncheck_are_checkbox_only(role, action):
    assert project_element(role, [action]) == ("checkbox", ("click",))
    assert project_element("push button", [action]) == ("button", ())
    assert project_element("check menu item", [action]) == ("menuitemcheckbox", ())
    assert project_element("paragraph", [action]) is None


def test_activation_is_not_inferred_from_button_role_or_nonactivation_action_position():
    assert project_element("push button") == ("button", ())
    assert project_element("push button", ["buffer.delete-line", "activate"]) == ("button", ("click",))
    assert project_element("push button", ["buffer.delete-line"]) == ("button", ())


def test_unknown_passive_nodes_do_not_invent_actions():
    assert project_element("static") is None
    assert project_element("label") is None
    assert project_element("") is None
    assert project_element("AXButton", ["AXPress"]) is None


def test_role_names_and_action_names_have_distinct_normalization_rules():
    assert project_element(" CHECK BOX ", ["ui.CHECK"]) == ("checkbox", ("click",))
    # Raw role words are not stripped into broad aliases; only known roles permit check.
    assert project_element("check-box", ["check"]) is None
    assert project_element("push button", ["áactivate"]) == ("button", ("click",))
    assert project_element("push button", ["áctivate"]) == ("button", ())
