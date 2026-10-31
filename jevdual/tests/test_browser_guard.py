"""The browser adapter supplies judgment, never a keyword/threshold bypass."""

import asyncio
import sys

import pytest
from jevdual.browser_guard import GuardRefused, authorize


def call(tmp_path, *, label="Commit fixture", probability=0.01, malformed=False, failing=False):
    adapter = tmp_path / "guard.py"
    digest_expression = "str(0)" if malformed else "r['digest']"
    adapter.write_text(
        "import json,sys\nr=json.load(sys.stdin)\n" +
        ("raise SystemExit(1)\n" if failing else
         f"print(json.dumps({{'producer':'footwork.browser.guard','version':1,'digest':"
         f"{digest_expression},'probabilities':[{probability!r}]}}))\n")
    )
    config = {"session_id": "s", "task": "Commit once", "guard_command": [sys.executable, str(adapter)]}
    snapshot = {"page": {"title": "Fixture", "url": "http://127.0.0.1/"},
                "refs": [{"ref": "opaque", "name": label}]}
    return asyncio.run(authorize(config, {"pid": 1}, snapshot, "opaque", "a" * 64))


def test_configured_guard_binding(tmp_path):
    assert call(tmp_path) == {"producer": "footwork.browser.guard", "version": 1,
                              "decision": "allow", "digest": "a" * 64}


@pytest.mark.parametrize("kwargs", [{"probability": 0.99}, {"malformed": True}, {"failing": True},
                                   {"probability": "invalid"}, {"label": "Delete account"}])
def test_guard_failure_never_allows(tmp_path, kwargs):
    with pytest.raises(GuardRefused):
        call(tmp_path, **kwargs)
