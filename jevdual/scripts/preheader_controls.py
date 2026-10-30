"""Diagnostic HTTP/owned-Chrome controls; never native input qualification.

Run with the existing project interpreter; no browser download or personal profile.
Raw CDP/NetLog captures stay in the private run directory. A sanitized summary
retains request counts, handler connections and Chromium retry event names.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import http.client
import json
import subprocess
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from jevdual.app_qualification import TicketFixture
from jevdual.ticket_evidence import form_body

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def debug_pages(port):
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        return json.load(response)


def network_summary(log):
    """Retain event identities/errors, never arbitrary headers or bodies."""
    names = {v: k for k, v in log["constants"]["logEventTypes"].items()}
    events = []
    for row in log["events"]:
        name = names.get(row["type"], str(row["type"]))
        if any(term in name for term in ("RESTART", "RETRY", "SEND_REQUEST_HEADERS", "READ_HEADERS")):
            params = row.get("params", {})
            events.append(
                {
                    "name": name,
                    "phase": row.get("phase"),
                    "time": row.get("time"),
                    "source": row.get("source"),
                    "params": {
                        k: v
                        for k, v in params.items()
                        if k in {"net_error", "error", "reason", "source_dependency"}
                    },
                }
            )
    return events


class CDP:
    def __init__(self, ws):
        self.ws, self.counter, self.pending, self.events = ws, 0, {}, []
        self.reader = asyncio.create_task(self.read())

    async def read(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                if "id" in msg:
                    future = self.pending.pop(msg["id"], None)
                    if future is not None:
                        future.set_result(msg)
                else:
                    self.events.append(msg)
        finally:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(RuntimeError("CDP closed"))

    async def call(self, method, params=None):
        self.counter += 1
        future = asyncio.get_running_loop().create_future()
        self.pending[self.counter] = future
        await self.ws.send(json.dumps({"id": self.counter, "method": method, "params": params or {}}))
        msg = await asyncio.wait_for(future, 15)
        if "error" in msg:
            raise RuntimeError(msg["error"])
        return msg.get("result", {})

    async def eval(self, expression):
        result = await self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result.get("result", {}).get("value")


async def chrome_control(fixture, expected, run, *, activation="form"):
    import websockets

    profile = run / "profile"
    netlog = run / "netlog.json"
    log = (run / "chrome.stderr").open("wb")
    child = await asyncio.to_thread(
        subprocess.Popen,
        [
            CHROME,
            "--headless=new",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            "--remote-debugging-port=0",
            "--user-data-dir=" + str(profile),
            "--log-net-log=" + str(netlog),
            "about:blank",
        ],
        stdout=log,
        stderr=log,
    )
    cdp = None
    try:
        for _ in range(200):
            active = profile / "DevToolsActivePort"
            if active.exists():
                break
            if child.poll() is not None:
                raise RuntimeError("owned Chrome exited")
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError("owned Chrome debug endpoint unavailable")
        port = int(active.read_text().splitlines()[0])
        pages = await asyncio.to_thread(debug_pages, port)
        endpoint = next(row["webSocketDebuggerUrl"] for row in pages if row["type"] == "page")
        async with websockets.connect(endpoint, max_size=8 * 1024 * 1024) as ws:
            cdp = CDP(ws)
            await cdp.call("Page.enable")
            await cdp.call("Network.enable")
            await cdp.call("Runtime.enable")
            await cdp.call("Runtime.addBinding", {"name": "footworkDiagnosticSubmit"})
            await cdp.call("Page.navigate", {"url": fixture.url})
            for _ in range(200):
                if await cdp.eval("document.querySelectorAll('form input').length") == 4:
                    break
                await asyncio.sleep(0.025)
            else:
                raise RuntimeError("form unavailable")
            await cdp.eval(
                "document.querySelector('form').addEventListener('submit', () => footworkDiagnosticSubmit('submit'))"
            )
            await cdp.eval(
                "Object.entries("
                + json.dumps(expected)
                + ").forEach(([k,v]) => document.querySelector('[name=\"'+k+'\"]').value=v)"
            )
            before = await cdp.eval("Object.fromEntries(new FormData(document.querySelector('form')))")
            if before != expected:
                raise RuntimeError("wrong pre-activation fields")
            # Exactly one diagnostic browser activation, not an admitted native action.
            if activation == "fetch":
                await cdp.eval(
                    "fetch('/tickets', {method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:"
                    + json.dumps(form_body(expected).decode())
                    + "}).then(r=>r.text()).catch(e=>{window.footworkFetchError=String(e)}); true"
                )
            else:
                await cdp.eval("document.querySelector('button').click(); true")
            await asyncio.sleep(2)
            events = list(cdp.events)
            write(run / "cdp.json", events)
            result = {
                "activation_calls": 1,
                "activation": activation,
                "submit_events": sum(
                    row.get("method") == "Runtime.bindingCalled"
                    and row.get("params", {}).get("name") == "footworkDiagnosticSubmit"
                    for row in events
                ),
                "post_requests": [
                    row["params"]["requestId"]
                    for row in events
                    if row.get("method") == "Network.requestWillBeSent"
                    and row["params"]["request"].get("method") == "POST"
                ],
                "network_failures": [
                    row["params"].get("errorText")
                    for row in events
                    if row.get("method") == "Network.loadingFailed"
                ],
                "browser_version": await cdp.call("Browser.getVersion"),
                "observation_limit": "two-second diagnostic observation; not a terminal service proof",
            }
            await cdp.call("Browser.close")
        child.wait(timeout=10)
        result["netlog_events"] = network_summary(json.loads(netlog.read_text()))
        return result
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=10)
        if cdp is not None:
            cdp.reader.cancel()
        log.close()


def handler_observer(fixture):
    events = []
    original = fixture.server.RequestHandlerClass.do_POST

    def do_post(handler):
        event = {"received": time.time(), "connection": list(handler.client_address), "path": handler.path}
        events.append(event)
        original(handler)
        event["returned"] = time.time()

    fixture.server.RequestHandlerClass.do_POST = do_post
    return events


def run_slot(kind, mode, run):
    run.mkdir()
    expected = {
        "request_id": uuid.uuid4().hex,
        "artifact": "control.png",
        "orientation": "clockwise90",
        "digest": hashlib.sha256(b"synthetic control").hexdigest(),
    }
    with TicketFixture(
        run / "service",
        lose_reply_once=mode != "normal",
        reply_loss=mode if mode != "normal" else "disconnect",
    ) as fixture:
        handlers = handler_observer(fixture)
        if kind == "http":
            try:
                with urlopen(
                    Request(fixture.url + "/tickets", data=form_body(expected), method="POST"), timeout=5
                ) as response:
                    response.read()
                error = None
            except (OSError, http.client.HTTPException) as exc:
                error = type(exc).__name__
            client = {"activation_calls": 1, "error": error}
        else:
            client = asyncio.run(
                chrome_control(
                    fixture, expected, run, activation="fetch" if kind == "chrome-fetch" else "form"
                )
            )
        snapshot = fixture.store.snapshot()
        write(run / "snapshot.json", snapshot)
        return {
            "kind": kind,
            "mode": mode,
            "client": client,
            "handlers": handlers,
            "ingresses": len(snapshot["ingress"]),
            "tickets": len(snapshot["tickets"]),
            "body_hashes": [row["body_sha"] for row in snapshot["ingress"]],
            "native_qualification": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--fetch-only", action="store_true", help="Two separately preregistered fetch/disconnect controls"
    )
    args = parser.parse_args()
    root = args.run_dir.absolute()
    root.mkdir(exist_ok=False, parents=True)
    schedule = [
        {"id": f"{kind}-{mode}-{repeat}", "kind": kind, "mode": mode, "state": "planned"}
        for kind in (("chrome-fetch",) if args.fetch_only else ("http", "chrome"))
        for mode in (("disconnect",) if args.fetch_only else ("normal", "truncated", "disconnect"))
        for repeat in (1, 2)
    ]
    write(root / "schedule.json", schedule)
    results = []
    for slot in schedule:
        slot["state"] = "running"
        write(root / "schedule.json", schedule)
        try:
            result = run_slot(slot["kind"], slot["mode"], root / slot["id"])
            slot["state"] = "observed"
        except Exception as exc:  # noqa: BLE001 — retain failed diagnostic slots before continuing
            result = {"kind": slot["kind"], "mode": slot["mode"], "error": str(exc)}
            slot["state"] = "failed"
        result["id"] = slot["id"]
        results.append(result)
        write(root / "results.json", results)
        write(root / "schedule.json", schedule)
        print(json.dumps({k: v for k, v in result.items() if k != "client"}), flush=True)
    return 0 if all(slot["state"] == "observed" for slot in schedule) else 1


if __name__ == "__main__":
    raise SystemExit(main())
