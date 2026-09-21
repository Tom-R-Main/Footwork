import json
import os

import pytest
from jevdual import patch


def test_orjson_decode_patch_is_idempotent_and_equivalent():
    from cdp_use import client

    if os.environ.get("JEVDUAL_PURE_PY") == "1":
        assert patch.install_orjson_decode() is False
        return
    assert patch.install_orjson_decode() is True
    assert patch.install_orjson_decode() is True
    assert patch.active_patches() == {"orjson_decode": True}
    msg = {"id": 7, "result": {"strings": ["a", "b"], "n": 1.5, "u": "é", "nested": [1, [2, 3]]}}
    raw = json.dumps(msg)
    assert client.json.loads(raw) == msg
    assert client.json.loads(raw.encode()) == msg
    assert isinstance(client.json.dumps(msg), str)


@pytest.mark.skipif(os.environ.get("JEVDUAL_PURE_PY") == "1", reason="pure-python mode")
def test_orjson_matches_stdlib_on_recorded_snapshot():
    import orjson

    from tests.fixtures.loader import load_fixture

    fx = load_fixture("wikipedia-python")
    raw = json.dumps({"id": 1, "result": fx.snapshot})
    assert orjson.loads(raw) == json.loads(raw)
