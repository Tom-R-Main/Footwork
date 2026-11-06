"""A minimal OBS WebSocket v5 client for filmed takes: one request per call, JSON in and out.

    OBS_WEBSOCKET_PASSWORD="$(cat FILE)" python scripts/obs_ws.py GetRecordStatus
    python scripts/obs_ws.py GetInputSettings '{"inputName": "Footwork take"}'
    python scripts/obs_ws.py --batch requests.json

The password comes only from OBS_WEBSOCKET_PASSWORD; it is never printed or written.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import sys
import uuid

import websockets

URL = os.environ.get("OBS_WEBSOCKET_URL", "ws://localhost:4455")


def _auth(password: str, salt: str, challenge: str) -> str:
    secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
    return base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()


async def call(requests: list[tuple[str, dict]]) -> list[dict]:
    async with websockets.connect(URL, subprotocols=["obswebsocket.json"], max_size=2**24) as ws:
        hello = json.loads(await ws.recv())["d"]
        identify: dict = {"rpcVersion": 1, "eventSubscriptions": 0}
        if "authentication" in hello:
            a = hello["authentication"]
            identify["authentication"] = _auth(
                os.environ["OBS_WEBSOCKET_PASSWORD"], a["salt"], a["challenge"]
            )
        await ws.send(json.dumps({"op": 1, "d": identify}))
        msg = json.loads(await ws.recv())
        if msg.get("op") != 2:
            raise SystemExit(f"OBS refused identification: {msg}")
        out = []
        for request_type, data in requests:
            rid = uuid.uuid4().hex
            await ws.send(
                json.dumps(
                    {"op": 6, "d": {"requestType": request_type, "requestId": rid, "requestData": data}}
                )
            )
            while True:
                reply = json.loads(await ws.recv())
                if reply.get("op") == 7 and reply["d"].get("requestId") == rid:
                    d = reply["d"]
                    out.append(
                        {
                            "request": request_type,
                            "ok": d["requestStatus"]["result"],
                            "status": d["requestStatus"],
                            "data": d.get("responseData"),
                        }
                    )
                    break
        return out


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--batch":
        with open(args[1]) as f:
            requests = [(r["requestType"], r.get("requestData", {})) for r in json.load(f)]
    else:
        requests = [(args[0], json.loads(args[1]) if len(args) > 1 else {})]
    results = asyncio.run(call(requests))
    print(json.dumps(results if len(results) > 1 else results[0], indent=1))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
