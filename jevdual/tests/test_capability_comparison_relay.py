"""Subprocess proofs for C1's relay, independent of either product/backend."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/capability_comparison_relay.py"
FAKE = r"""
import json,sys,time
from pathlib import Path
root=Path(sys.argv[1])
generation=root/'generation'
n=int(generation.read_text())+1 if generation.exists() else 1
generation.write_text(str(n))
for line in sys.stdin:
    q=json.loads(line)
    with (root/'requests.jsonl').open('a') as log: log.write(json.dumps(q)+'\n')
    if 'id' not in q: continue
    m=q['method']
    if m=='initialize':
        result={'protocolVersion':'2025-11-25','capabilities':{},'serverInfo':{'name':'fake','version':'1'}}
    elif m=='tools/list':
        tools=['get_window_state','act']
        if n>1 and (root/'drift').exists(): tools.append('different')
        result={'tools':[{'name':t,'inputSchema':{'type':'object'}} for t in tools]}
    elif q['params']['name']=='get_window_state':
        result={'content':[{'type':'text','text':(root/'document').read_text()}]}
    else:
        args=q['params']['arguments']
        if args.get('refuse'):
            result={'content':[{'type':'text','text':'not sent'}],'isError':True}
        else:
            p=root/'document'
            p.write_text(p.read_text()+args['text'])
            time.sleep(0.3)
            result={'content':[{'type':'text','text':'applied'}]}
    print(json.dumps({'jsonrpc':'2.0','id':q['id'],'result':result}),flush=True)
"""


class Client:
    def __init__(self, root: Path, mode: str, *, drift: bool = False) -> None:
        self.root = root
        (root / "document").write_text("start\n")
        (root / "backend.py").write_text(FAKE)
        if drift:
            (root / "drift").touch()
        cfg = {
            "argv": [sys.executable, str(root / "backend.py"), str(root)],
            "mode": mode,
            "prefix": "start\n",
            "stale_prefix": "start\nexternal edit\n",
            "oracle": {"kind": "file", "path": str(root / "document")},
            "mutation_tools": ["act"],
            "observation_tools": ["get_window_state"],
        }
        path = root / "relay.json"
        path.write_text(json.dumps(cfg))
        self.stderr = (root / "relay-stderr.log").open("w")
        self.proc = subprocess.Popen(
            [sys.executable, str(SCRIPT), "--config", str(path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
        )
        self.seq = 0
        self.rpc(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        )
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.rpc("tools/list", {})

    def send(self, value: dict) -> None:
        assert self.proc.stdin
        self.proc.stdin.write((json.dumps(value) + "\n").encode())
        self.proc.stdin.flush()

    def rpc(self, method: str, params: dict) -> dict:
        self.seq += 1
        self.send({"jsonrpc": "2.0", "id": self.seq, "method": method, "params": params})
        assert self.proc.stdout
        ready, _, _ = select.select([self.proc.stdout], [], [], 15)
        assert ready, "relay response timed out"
        line = self.proc.stdout.readline()
        if not line:
            raise EOFError("relay ended")
        result = json.loads(line)
        assert result["id"] == self.seq
        return result

    def tool(self, name: str, **args) -> dict:
        return self.rpc("tools/call", {"name": name, "arguments": args})

    def events(self) -> list[dict]:
        return [json.loads(line) for line in (self.root / "events.jsonl").read_text().splitlines()]

    def close(self) -> None:
        assert self.proc.stdin
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(timeout=8)
        self.stderr.close()


def test_interruption_restarts_without_replaying_mutation_and_reaps_children(tmp_path):
    client = Client(tmp_path, "interrupted")
    try:
        client.tool("get_window_state")
        result = client.tool("act", text="17.25 USD")
        assert result["error"] == {"code": -32000, "message": "backend process exited; restarted"}
        assert client.tool("get_window_state")["result"]["content"][0]["text"] == "start\n17.25 USD"
        requests = [json.loads(x) for x in (tmp_path / "requests.jsonl").read_text().splitlines()]
        assert sum(x.get("params", {}).get("name") == "act" for x in requests) == 1
        assert sum(x["method"] == "initialize" for x in requests) == 2
        events = client.events()
        assert [e["kind"] for e in events].count("held") == 1
        assert [e["kind"] for e in events].count("dropped") == 1
        assert next(e for e in events if e["kind"] == "dropped")["child_returncode"] == -9
        assert not any(e["kind"] == "invalid" for e in events)
    finally:
        client.close()
    assert client.proc.returncode == 0
    for event in client.events():
        if event["kind"] == "spawn":
            with pytest.raises(ProcessLookupError):
                os.kill(event["pid"], 0)


def test_stale_treatment_changes_prefix_once_and_retains_external_edit(tmp_path):
    client = Client(tmp_path, "stale")
    try:
        client.tool("get_window_state")
        client.tool("act", text="17.25 USD")
        client.tool("act", text="later")
        assert (tmp_path / "document").read_text() == "start\nexternal edit\n17.25 USDlater"
        assert sum(e["kind"] == "stale_injected" for e in client.events()) == 1
    finally:
        client.close()


def test_catalog_drift_after_kill_is_invalid_and_does_not_replay(tmp_path):
    client = Client(tmp_path, "interrupted", drift=True)
    try:
        client.tool("get_window_state")
        with pytest.raises(EOFError):
            client.tool("act", text="17.25 USD")
        assert (tmp_path / "document").read_text() == "start\n17.25 USD"
        assert any(e.get("reason") == "catalog_drift" for e in client.events())
    finally:
        client.close()


def test_no_change_refusal_is_forwarded_but_treatment_is_inconclusive(tmp_path):
    client = Client(tmp_path, "interrupted")
    start = time.monotonic()
    try:
        client.tool("get_window_state")
        result = client.tool("act", refuse=True)
        assert result["result"]["isError"] is True
        assert (tmp_path / "document").read_text() == "start\n"
        assert any(e.get("reason") == "no_observed_change" for e in client.events())
        assert not any(e["kind"] == "dropped" for e in client.events())
        assert time.monotonic() - start < 14
    finally:
        client.close()
