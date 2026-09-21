"""Key loading for the eval rig.

Keys are materialized from the Sift vault into 0400 files under
``~/.config/jevdual`` (outside any git worktree). ``load_keys`` exports them as
environment variables when the variables are not already set, and never logs
or returns the values.

Files and the variables they feed:
  TYPESAFE_API_KEY     -> TYPESAFE_API_KEY   (System 1: Jev)
  META_MODEL_API_KEY   -> MODEL_API_KEY      (System 2: Meta Model API, Muse Spark)
  OPENAI_API_KEY       -> OPENAI_API_KEY     (optional text helper)
"""

from __future__ import annotations

import os
from pathlib import Path

KEY_DIR = Path(os.environ.get("JEVDUAL_KEY_DIR", Path.home() / ".config" / "jevdual"))
FILES = {"TYPESAFE_API_KEY": "TYPESAFE_API_KEY", "META_MODEL_API_KEY": "MODEL_API_KEY", "OPENAI_API_KEY": "OPENAI_API_KEY"}

META_BASE_URL = "https://api.meta.ai/v1"
MUSE_CONTRIBUTOR = "muse-spark-1.3-contributor"


def load_keys() -> dict[str, bool]:
    """Export each available key file as its env var; returns {var: present}."""
    present: dict[str, bool] = {}
    for filename, var in FILES.items():
        if os.environ.get(var):
            present[var] = True
            continue
        path = KEY_DIR / filename
        try:
            value = path.read_text().strip()
        except OSError:
            present[var] = False
            continue
        if value:
            os.environ[var] = value
            present[var] = True
        else:
            present[var] = False
    # The text helper defaults to Muse over the Meta Model API when nothing else is configured.
    if present.get("MODEL_API_KEY") and not os.environ.get("JEVDUAL_TEXT_BASE_URL"):
        os.environ.setdefault("JEVDUAL_TEXT_BASE_URL", META_BASE_URL)
        os.environ.setdefault("JEVDUAL_TEXT_API_KEY", os.environ["MODEL_API_KEY"])
        os.environ.setdefault("JEVDUAL_TEXT_MODEL", MUSE_CONTRIBUTOR)
    return present
