"""Real disposable Linux fixture: repeat fresh startup, cancel, and failed WM."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(mode=0o700)
runner = Path(__file__).with_name("desktop_session.py")
receipts = []
for case in ("first", "repeat", "missing-wm"):
    state = out / (case + "-state")
    environment = dict(os.environ)
    if case == "missing-wm":
        stub = out / "stubs"
        stub.mkdir()
        binary = stub / "openbox"
        binary.write_text("#!/bin/sh\nexit 2\n")
        binary.chmod(0o700)
        environment["PATH"] = str(stub) + ":" + environment.get("PATH", "")
    with (out / (case + ".log")).open("w") as log:
        process = subprocess.Popen(["dbus-run-session", "--", sys.executable, "-I", str(runner), str(state),
                                    "--timeout", "30", "--grace", "1"], env=environment,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic() + 35
        record = None
        while time.monotonic() < deadline:
            if (state / "session.json").exists():
                record = json.loads((state / "session.json").read_text())
                if record["state"] in {"ready", "stopped"}:
                    break
            if process.poll() is not None:
                break
            time.sleep(.1)
        assert record is not None
        if case != "missing-wm":
            assert record["state"] == "ready", record
            assert len(record["stages"]) == 4
            assert record["environment"]["XDG_CONFIG_HOME"] == str(state / "config")
            supervisor = record["supervisor"]
            current = Path(f"/proc/{supervisor['pid']}/stat").read_text().rsplit(")", 1)[1].split()[19]
            assert current == supervisor["start"]
            os.kill(supervisor["pid"], signal.SIGTERM)
        code = process.wait(timeout=5)
        final = json.loads((state / "session.json").read_text())
        assert final["state"] == "stopped" and not (state / "started").exists()
        if case == "missing-wm":
            assert code == 2 and "critical component exited: openbox" in final["stop_reason"]
            assert not any(r["stage"] == "editor" for r in final["stages"])
        else:
            assert code == 0 and final["cleanup"]["unresolved"] == []
        live = []
        for child in final["processes"]:
            try:
                fields = Path(f"/proc/{child['pid']}/stat").read_text().rsplit(")", 1)[1].split()
                if fields[19] == child["start"] and fields[0] != "Z":
                    live.append(child["name"])
            except FileNotFoundError:
                pass
        assert not live, live
        receipts.append({"case": case, "exit_code": code, "ready_stages": len(final["stages"]),
                         "stop_reason": final["stop_reason"], "cleanup": final["cleanup"],
                         "live_owned_components": live})
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
(out / "receipt.json").write_text(json.dumps(receipts, indent=2) + "\n")
print(json.dumps(receipts))
