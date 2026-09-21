import importlib.metadata
import os

import jevdual
from jevdual import _native


def test_backend_matches_env():
    if os.environ.get(_native.PURE_PY_ENV) == "1":
        assert jevdual.BACKEND == "pure-python"
        assert not _native.native_available()
    else:
        assert jevdual.BACKEND.startswith("native ")
        assert _native.native_available()


def test_native_ping_round_trips():
    if not _native.native_available():
        return
    assert _native.core.ping(41) == 42


def test_browser_use_is_pinned():
    assert importlib.metadata.version("browser_use") == "0.13.10"


def test_typesafe_sdk_importable():
    import typesafe_sdk

    assert hasattr(typesafe_sdk, "AsyncTypeSafeClient")
