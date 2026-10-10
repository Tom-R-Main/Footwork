"""Actual SIGTERM closeout controls for the acceptance relay; no model or native UI."""

import importlib.util
import os
import time
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "relay_test_support", Path(__file__).with_name("test_capability_comparison_relay.py")
)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)


@pytest.mark.parametrize("active", [False, True])
def test_sigterm_only_qualifies_idle_closeout(tmp_path, monkeypatch, active):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    wrapper = tmp_path / "entry.py"
    wrapper.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        "p=Path(sys.argv[2]); c=json.loads(p.read_text()); c['case']='clean'\n"
        "p.write_text(json.dumps(c)); sys.argv[1]='--relay'\n"
        f"sys.path.insert(0,{str(scripts)!r})\n"
        "from capability_agent_restart_trial import main\nraise SystemExit(main())\n"
    )
    monkeypatch.setattr(original, "SCRIPT", wrapper)
    monkeypatch.setattr(original, "FAKE", original.FAKE.replace("time.sleep(0.3)", "time.sleep(600)"))
    client = original.Client(tmp_path, "clean")
    try:
        if active:
            client.send(
                {
                    "jsonrpc": "2.0",
                    "id": 99,
                    "method": "tools/call",
                    "params": {"name": "act", "arguments": {"text": "one-effect"}},
                }
            )
            deadline = time.monotonic() + 5
            while (tmp_path / "document").read_text() != "start\none-effect":
                assert time.monotonic() < deadline, "active-call boundary was not reached"
                time.sleep(0.01)
        else:
            client.tool("get_window_state")
        client.proc.terminate()
        client.proc.wait(timeout=8)
        events = client.events()
        assert any(e["kind"] == "closed" for e in events)
        assert any(e["kind"] == "invalid" for e in events) is active
        assert (client.proc.returncode != 0) is active
        for event in events:
            if event["kind"] == "spawn":
                with pytest.raises(ProcessLookupError):
                    os.kill(event["pid"], 0)
    finally:
        client.close()
