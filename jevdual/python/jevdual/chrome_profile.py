"""The Chrome profile the browser-use path launches with.

Chrome checks a submitted password against its breach list and, when it is listed, raises a
"Change your password" warning over the tab. In headless Chrome nobody sees the warning, and while it
is up every mouse event dispatched to the page is dropped: CDP accepts it and the page never receives
it. saucedemo's demo password is on the list, so after its login every click the agent made reported
success and changed nothing (package C, notebook C5 and C6, ``results/c-agent-loop-20260926``).

The agent's browser is a fresh, throwaway profile that nobody signs in to, so its password manager has
nothing to protect: :func:`automation_profile` starts it with the password manager and the leak check
off. The operator's own Chrome (``jevdual.browser_driver``) is left alone; a person may use it, and there
the warning is visible and readable through the accessibility tree.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

#: Chrome preferences that keep the password manager and its breach check from ever running.
QUIET_PREFS: dict[str, Any] = {
    "credentials_enable_service": False,
    "profile": {"password_manager_enabled": False, "password_manager_leak_detection": False},
}

#: browser-use's own prefix for a temp profile, so the runner's cleanup removes ours too.
TEMP_PREFIX = "browser-use-user-data-dir-"


def quiet_profile_dir() -> Path:
    """A new temp user-data dir whose default profile carries :data:`QUIET_PREFS`."""
    d = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
    (d / "Default").mkdir()
    (d / "Default" / "Preferences").write_text(json.dumps(QUIET_PREFS))
    return d


def automation_profile(**kwargs: Any) -> Any:
    """A ``BrowserProfile`` on a fresh quiet profile; keyword arguments pass through."""
    from browser_use.browser.profile import BrowserProfile

    kwargs.setdefault("user_data_dir", str(quiet_profile_dir()))
    return BrowserProfile(**kwargs)
