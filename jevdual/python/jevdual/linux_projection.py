"""Conservative AT-SPI role/action projection for the pinned CUA Linux driver.

This module grants no target identity or input authority. The caller must already
have a fresh driver token and must qualify editability and multiline behavior
independently; a text role, value, or advertised action is not that proof.
"""

from __future__ import annotations

from collections.abc import Iterable

from jevdual.menu import Operation

TEXT_ROLES = frozenset({"entry", "text", "textbox", "search box", "editbar", "password text"})
PASSWORD_ROLES = frozenset({"password text"})
CHECKBOX_ROLES = frozenset({"check box", "checkbox"})

# These are semantic aliases, not assertions that a widget can be actuated.
_MENU_ROLES = {
    "button": "button",
    "push button": "button",
    "toggle button": "button",
    "check box": "checkbox",
    "checkbox": "checkbox",
    "radio button": "radio",
    "radio": "radio",
    "combo box": "combobox",
    "menu item": "menuitem",
    "check menu item": "menuitemcheckbox",
    "radio menu item": "menuitemradio",
    "page tab": "tab",
    "tab": "tab",
    "link": "link",
    "list item": "option",
    "table cell": "option",
    "tree item": "treeitem",
    "slider": "slider",
    "spin button": "spinbutton",
}

# Match platform-linux/src/atspi/native.rs in the pinned native-source archive.
# In particular, an arbitrary action (or merely action index zero) is not a click.
_ACTIVATION_VERBS = frozenset({
    "click", "clickancestor", "activate", "press", "invoke", "toggle", "open", "jump", "dodefault",
})
_CHECKBOX_VERBS = frozenset({"check", "uncheck"})


def normalize_role(role: str) -> str:
    """Keep AT-SPI word boundaries; do not confuse its roles with AX role names."""
    return role.strip().lower() if isinstance(role, str) else ""


def normalized_action_verb(action: str) -> str:
    """Use the driver's last-segment, ASCII-alphanumeric normalization exactly."""
    if not isinstance(action, str):
        return ""
    return "".join(c.lower() for c in action.rsplit(".", 1)[-1].strip() if c.isascii() and c.isalnum())


def project_element(
    raw_role: str,
    actions: Iterable[str] | None = None,
    *,
    editable: bool = False,
    multiline: bool = False,
) -> tuple[str, tuple[Operation, ...]] | None:
    """Project one token-bearing element without inventing input capabilities.

    Readable text can remain a passive candidate for readback. A password field
    without qualified editability is omitted; callers must redact all fields in
    PASSWORD_ROLES even when this function offers input operations. A known
    nontext control can remain passive, while unrecognized passive roles return
    None. Static tree nodes must not acquire action IDs through this helper.
    """
    role = normalize_role(raw_role)
    if not role:
        return None
    if role in TEXT_ROLES:
        menu_role = "searchbox" if role == "search box" else "textbox"
        if editable is not True:
            return None if role in PASSWORD_ROLES else (menu_role, ())
        operations: tuple[Operation, ...] = ("type", "enter")
        if multiline is True:
            operations += ("append",)
        return menu_role, operations

    names = (actions,) if isinstance(actions, str) else (actions or ())
    allowed = _ACTIVATION_VERBS | _CHECKBOX_VERBS if role in CHECKBOX_ROLES else _ACTIVATION_VERBS
    activation = any(normalized_action_verb(name) in allowed for name in names)
    menu_role = _MENU_ROLES.get(role)
    if activation:
        return menu_role or role, ("click",)
    return (menu_role, ()) if menu_role is not None else None
