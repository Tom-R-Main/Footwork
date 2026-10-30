"""Browser ownership must survive platform discovery without widening attachment."""

from types import SimpleNamespace

import pytest
from jevdual import browser_driver as browser


def test_explicit_browser_is_resolved_and_must_be_executable(tmp_path, monkeypatch):
    binary = tmp_path / "chrome"
    binary.write_text("browser fixture")
    monkeypatch.setenv("FOOTWORK_CHROME_EXECUTABLE", str(binary))
    with pytest.raises(RuntimeError, match="executable"):
        browser.chrome_executable()
    binary.chmod(0o700)
    assert browser.chrome_executable() == str(binary.resolve())


def test_linux_discovers_chromium_without_a_mac_path(tmp_path, monkeypatch):
    binary = tmp_path / "chromium"
    binary.write_text("browser fixture")
    binary.chmod(0o700)
    monkeypatch.delenv("FOOTWORK_CHROME_EXECUTABLE", raising=False)
    monkeypatch.setattr(browser.sys, "platform", "linux")
    monkeypatch.setattr(browser, "_browser_candidates", lambda: [str(binary)])
    assert browser.chrome_executable() == str(binary)


def test_invalid_explicit_browser_never_falls_back(monkeypatch):
    monkeypatch.setenv("FOOTWORK_CHROME_EXECUTABLE", "/missing/explicit-browser")
    monkeypatch.setattr(browser, "_browser_candidates", lambda: pytest.fail("must not fall back"))
    with pytest.raises(RuntimeError, match="executable"):
        browser.chrome_executable()


def process(pid, args, exe="/test/chrome"):
    return SimpleNamespace(info={"pid": pid, "cmdline": args, "exe": exe, "uids": SimpleNamespace(real=42)})


def test_process_discovery_requires_exact_profile_port_executable_and_owner(monkeypatch):
    import psutil

    profile = f"--user-data-dir={browser.PROFILE_DIR}"
    port = f"--remote-debugging-port={browser.PORT}"
    candidates = [
        process(1, ["chrome", profile + "-other", port]),
        process(2, ["chrome", profile, port], exe="/other/chrome"),
        process(3, ["chrome", profile, port, "--type=renderer"]),
        process(4, ["chrome", profile, "--remote-debugging-port=1"]),
        process(5, ["chrome", profile, port]),
    ]
    candidates[4].info["uids"] = SimpleNamespace(real=99)
    monkeypatch.setattr(browser.os, "getuid", lambda: 42)
    monkeypatch.setattr(browser, "chrome_executable", lambda: "/test/chrome")
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: iter(candidates))
    assert browser.chrome_pid() is None
    candidates.append(process(6, ["chrome", profile, port]))
    assert browser.chrome_pid() == 6
    candidates.append(process(7, ["chrome", profile, port]))
    with pytest.raises(RuntimeError, match="multiple"):
        browser.chrome_pid()


@pytest.mark.asyncio
async def test_attachment_requires_fingerprint_and_same_process_incarnation(monkeypatch):
    import json
    import sys

    import psutil

    class Host:
        pass

    fake = SimpleNamespace(
        DriverAuthorizationHost=Host,
        DriverAuthorizationAction=SimpleNamespace(ALLOW="allow", DENY="deny"),
        DriverAuthorizationDecision=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setitem(sys.modules, "cua_driver", fake)
    monkeypatch.setattr(browser, "chrome_executable", lambda: "/test/chrome")
    monkeypatch.setattr(browser, "chrome_pid", lambda: 12)
    start = [1.0]
    monkeypatch.setattr(psutil, "Process", lambda pid: SimpleNamespace(create_time=lambda: start[0]))
    host = browser._host_class(12)()

    async def decision(resource):
        return (await host.authorize(SimpleNamespace(
            resource_json=json.dumps(resource), human_summary="fixture", request_digest="request"
        ))).action

    resource = {"pid": 12, "endpoint_owner_pid": 12, "process_fingerprint": {"executable": "/test/chrome"}}
    assert await decision(resource) == "allow"
    assert await decision({"pid": 12}) == "deny"
    assert await decision({**resource, "endpoint_owner_pid": 13}) == "deny"
    assert await decision([]) == "deny"
    start[0] = 2.0
    assert await decision(resource) == "deny"
