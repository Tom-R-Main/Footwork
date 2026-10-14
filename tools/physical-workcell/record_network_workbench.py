"""Retain a browser observation with a read-only public-state and journal readback."""

import argparse
import time
import urllib.request
from pathlib import Path

import body_client
import order_protocol as protocol


def record(root, name, text_file, action, screenshot=None):
    root = protocol.directory(root)
    ready = protocol.decode(protocol.read_bytes(root / "ready.json"))
    with urllib.request.urlopen(ready["browser_origin"] + "/api/state", timeout=20) as response:
        state = protocol.decode(response.read(protocol.MAX_BYTES + 1))
    if state["app_id"] != ready["app_id"]:
        raise protocol.Refusal("browser trial application identity changed")
    selected = {key: state[key] for key in ("app_id", "runner_status", "jobs", "connection", "recovery",
                                           "model_request_pending", "active_job_id", "current_frame")}
    text_file = Path(text_file).resolve()
    if root not in text_file.parents:
        raise protocol.Refusal("browser observation must be inside the trial root")
    visible_text = protocol.read_bytes(text_file, maximum=16000).decode("utf-8")
    client = body_client.read_journal(root / "operator" / "client" / "client.json")
    path = root / "ui-ledger.json"
    ledger = protocol.decode(protocol.read_bytes(path)) if path.exists() else {"steps": []}
    if any(step["name"] == name for step in ledger["steps"]):
        raise protocol.Refusal("browser observation identity already retained")
    step = {"name": name, "time": time.time(), "browser_action": action,
            "visible_text": visible_text, "state": selected, "client_commands": len(client["commands"]),
            "pending_command_ids": client["pending_command_ids"], "screenshot": screenshot}
    ledger["steps"].append(step)
    if len(protocol.encoded(ledger)) > protocol.MAX_BYTES:
        raise protocol.Refusal("browser observation ledger exceeded its 64 KiB bound")
    protocol.persist(path, ledger)
    print(name, selected["runner_status"], selected["connection"]["state"], selected["recovery"]["state"],
          "commands=" + str(step["client_commands"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--screenshot")
    args = parser.parse_args()
    record(args.root, args.name, args.text_file, args.action, args.screenshot)


if __name__ == "__main__":
    main()
