"""CLI startup owns its direct child even when readiness probing raises."""

import argparse
import tempfile
from pathlib import Path

import pytest
from jevdual import browser_cli


@pytest.fixture
def short_root():
    with tempfile.TemporaryDirectory(prefix="fw-start-", dir="/tmp") as directory:
        yield Path(directory)


def test_start_closes_actual_child_on_readiness_exception(short_root, monkeypatch):
    tmp_path = short_root
    session = tmp_path / "s"

    class Child:
        terminated = waited = False

        def poll(self):
            return None if not self.waited else 0

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            self.waited = True
            return 0

    child = Child()

    def spawn(*args, **kwargs):
        (session / "holder.json").touch()
        return child

    async def unavailable(*args, **kwargs):
        raise RuntimeError("readiness RPC unavailable")

    monkeypatch.setattr(browser_cli.subprocess, "Popen", spawn)
    monkeypatch.setattr(browser_cli, "_remote", unavailable)
    # No actual browser process or network operation is created by this test.
    args = argparse.Namespace(task="Observe", session=session, authority=tmp_path / "authority.db",
                              url="http://127.0.0.1/", chrome="/unused/chrome", guard_command=None)
    with pytest.raises(RuntimeError):
        browser_cli._start(args)
    assert child.terminated and child.waited


def test_cdp_schema_names_an_invocable_command():
    from jevdual.agent_cli import _schema

    schema = _schema(["browser", "cdp", "click"])
    assert schema["command"] == ["browser", "cdp", "click"]


def test_successful_start_does_not_stop_established_holder(short_root, monkeypatch):
    class Child:
        def poll(self):
            return None

        def terminate(self):
            pytest.fail("successful holder must remain owned by its session")

    session = short_root / "s"

    def spawn(*args, **kwargs):
        (session / "holder.json").touch()
        return Child()

    async def ready(*args, **kwargs):
        return {"ok": True, "operations": []}

    monkeypatch.setattr(browser_cli.subprocess, "Popen", spawn)
    monkeypatch.setattr(browser_cli, "_remote", ready)
    args = argparse.Namespace(task="Observe", session=session, authority=short_root / "authority.db",
                              url="http://127.0.0.1/", chrome="/unused/chrome", guard_command=None)
    assert browser_cli._start(args)["ok"] is True
