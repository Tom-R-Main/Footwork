"""Arm-neutral C1 stdio relay. Never replay a tools/call, including after death.

Trusted configuration selects the child and a fixture-only oracle. Requests are
serialized in both arms. The relay keeps host stdio alive, drops one interrupted
reply, restarts only the child, and replays initialization plus catalog discovery.
Its generic error contains no oracle result, operation ID, or recovery advice.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import signal
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

LOST = {"code": -32000, "message": "backend process exited; restarted"}
WATCH_TIMEOUT = 10.0
FRAME_LIMIT = 32 * 1024 * 1024


def oracle_read(spec: dict[str, Any]) -> str:
    if spec["kind"] == "file":  # subprocess tests only
        return Path(spec["path"]).read_text()
    if spec["kind"] != "ax":
        raise ValueError("unknown oracle kind")
    from capability_host_trial import ax_document_text

    return ax_document_text(spec["pid"], spec["document"])


def oracle_edit(spec: dict[str, Any], text: str) -> None:
    if spec["kind"] == "file":
        Path(spec["path"]).write_text(text)
        return
    from capability_host_trial import ax_reset_text

    ax_reset_text(spec["pid"], spec["document"], text)
    if oracle_read(spec) != text:
        raise RuntimeError("stale fixture edit did not read back exactly")


def watch(path: Path) -> None:
    cfg = json.loads(path.read_text())
    before = oracle_read(cfg["oracle"])
    if before != cfg["prefix"]:
        raise RuntimeError("watcher prerequisite prefix mismatch")
    print(json.dumps({"ready": True}), flush=True)
    deadline = time.monotonic() + WATCH_TIMEOUT
    while time.monotonic() < deadline:
        after = oracle_read(cfg["oracle"])
        if after != before:
            os.killpg(cfg["child_pid"], signal.SIGKILL)
            print(json.dumps({"changed": True, "time_ns": time.time_ns()}), flush=True)
            return
        time.sleep(0.005)
    print(json.dumps({"changed": False, "time_ns": time.time_ns()}), flush=True)


def catalog_hash(result: dict[str, Any]) -> str:
    # Ignore transport metadata but preserve every tool schema and description.
    tools = sorted(result["tools"], key=lambda tool: tool["name"])
    return hashlib.sha256(json.dumps(tools, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Relay:
    def __init__(self, cfg: dict[str, Any], root: Path) -> None:
        self.cfg, self.root = cfg, root
        self.proc: asyncio.subprocess.Process | None = None
        self.watcher: asyncio.subprocess.Process | None = None
        self.error_log: Any = None
        self.init: dict[str, Any] | None = None
        self.catalog: str | None = None
        self.interfered = False
        self.destination_observed = False
        self.spawn_count = 0

    def event(self, kind: str, **fields: Any) -> None:
        with (self.root / "events.jsonl").open("a") as stream:
            stream.write(json.dumps({"kind": kind, "time_ns": time.time_ns(), **fields}) + "\n")

    async def spawn(self) -> None:
        self.spawn_count += 1
        self.error_log = (self.root / f"child-{self.spawn_count}-stderr.log").open("w")
        self.proc = await asyncio.create_subprocess_exec(
            *self.cfg["argv"],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=self.error_log,
            env={**os.environ, **self.cfg.get("env", {})},
            start_new_session=True,
            limit=FRAME_LIMIT,
        )
        self.event("spawn", pid=self.proc.pid, generation=self.spawn_count)

    async def stop(self) -> None:
        if self.watcher and self.watcher.returncode is None:
            self.watcher.terminate()
            await self.watcher.wait()
        if self.proc and self.proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                await asyncio.wait_for(self.proc.wait(), timeout=5)
            except TimeoutError:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(self.proc.pid, signal.SIGKILL)
                await self.proc.wait()
        if self.error_log:
            self.error_log.close()

    async def request(self, msg: dict[str, Any], *, forward_notifications: bool = True) -> dict[str, Any]:
        assert self.proc and self.proc.stdin and self.proc.stdout
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()
        while True:
            line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=45)
            if not line:
                raise EOFError("backend stdout ended")
            response = json.loads(line)
            if response.get("id") == msg["id"]:
                return response
            if "method" in response:
                if forward_notifications:
                    self.output(response)
                else:
                    self.event("held_notification", method=response["method"])
            else:
                raise RuntimeError("unexpected backend response id")

    def output(self, msg: dict[str, Any]) -> None:
        print(json.dumps(msg), flush=True)

    async def notify(self, msg: dict[str, Any]) -> None:
        assert self.proc and self.proc.stdin
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()

    async def restart(self) -> None:
        if not self.init or not self.catalog:
            raise RuntimeError("restart requires prior initialize and catalog")
        await self.stop()
        await self.spawn()
        initialized = await self.request(
            {**self.init, "id": "__relay_initialize"}, forward_notifications=False
        )
        if "error" in initialized:
            raise RuntimeError("backend reinitialization failed")
        await self.notify({"jsonrpc": "2.0", "method": "notifications/initialized"})
        listed = await self.request(
            {"jsonrpc": "2.0", "id": "__relay_catalog", "method": "tools/list"}, forward_notifications=False
        )
        fresh = catalog_hash(listed["result"])
        if fresh != self.catalog:
            self.event("invalid", reason="catalog_drift", before=self.catalog, after=fresh)
            raise RuntimeError("catalog changed after restart")
        self.event("restarted", catalog_sha256=fresh)

    def journal_state(self) -> list[dict[str, Any]]:
        journal = self.cfg.get("journal")
        if not journal or not Path(journal).exists():
            return []
        with sqlite3.connect(f"file:{journal}?mode=ro", uri=True) as db:
            return [
                dict(zip(("id", "state", "disposition"), row, strict=True))
                for row in db.execute("SELECT id,state,disposition FROM operations")
            ]

    async def interrupted(self, msg: dict[str, Any]) -> dict[str, Any]:
        assert self.proc
        watcher_cfg = self.root / "watcher.json"
        watcher_cfg.write_text(
            json.dumps(
                {"oracle": self.cfg["oracle"], "prefix": self.cfg["prefix"], "child_pid": self.proc.pid}
            )
        )
        self.watcher = await asyncio.create_subprocess_exec(
            sys.executable,
            str(Path(__file__).resolve()),
            "--watch",
            str(watcher_cfg),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert self.watcher.stdout
        ready = await asyncio.wait_for(self.watcher.stdout.readline(), timeout=5)
        if not ready or not json.loads(ready).get("ready"):
            raise RuntimeError("independent watcher failed readiness")
        self.event("held", request_id=msg["id"], tool=msg["params"]["name"])
        response: dict[str, Any] | None = None
        try:
            response = await self.request(msg, forward_notifications=False)
            self.event("reply_received_held", request_id=msg["id"])
        except EOFError:
            pass
        result_line = await asyncio.wait_for(self.watcher.stdout.readline(), timeout=WATCH_TIMEOUT + 2)
        await self.watcher.wait()
        evidence = json.loads(result_line) if result_line else {}
        if not evidence.get("changed") or self.watcher.returncode:
            self.event("invalid", reason="no_observed_change", watcher_returncode=self.watcher.returncode)
            if response is None:
                raise RuntimeError("backend died without qualified interruption")
            return response
        await self.proc.wait()
        self.event(
            "dropped",
            request_id=msg["id"],
            received_reply=response is not None,
            child_returncode=self.proc.returncode,
            journal=self.journal_state(),
            watcher=evidence,
        )
        await self.restart()
        return {"jsonrpc": "2.0", "id": msg["id"], "error": LOST}

    async def handle(self, msg: dict[str, Any]) -> None:
        if "id" not in msg:
            await self.notify(msg)
            return
        method, params = msg.get("method"), msg.get("params", {})
        tool = params.get("name") if method == "tools/call" else None
        mutation = tool in self.cfg.get("mutation_tools", [])
        observation = tool in self.cfg.get("observation_tools", [])
        if tool == "bind":
            observation = params.get("arguments", {}).get("name") == "destination"
        if mutation and not self.interfered and self.cfg["mode"] != "clean":
            if not self.destination_observed:
                self.event("invalid", reason="mutation_before_destination_observation")
                raise RuntimeError("no successful destination observation before treatment")
            self.interfered = True
            if self.cfg["mode"] == "interrupted":
                response = await self.interrupted(msg)
            else:
                before = oracle_read(self.cfg["oracle"])
                if before != self.cfg["prefix"]:
                    raise RuntimeError("stale injection prerequisite prefix mismatch")
                oracle_edit(self.cfg["oracle"], self.cfg["stale_prefix"])
                self.event("stale_injected", request_id=msg["id"])
                response = await self.request(msg)
        else:
            response = await self.request(msg)
        if method == "initialize":
            self.init = msg
        if method == "tools/list" and "result" in response:
            self.catalog = catalog_hash(response["result"])
            self.event("catalog", sha256=self.catalog)
        if observation and "result" in response and not response["result"].get("isError", False):
            self.destination_observed = True
        self.output(response)

    async def run(self) -> None:
        await self.spawn()
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader(limit=FRAME_LIMIT)
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        task = asyncio.current_task()
        assert task
        loop.add_signal_handler(signal.SIGTERM, task.cancel)
        try:
            while line := await reader.readline():
                await self.handle(json.loads(line))
        finally:
            await self.stop()
            self.event("closed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--watch", type=Path)
    args = parser.parse_args()
    if args.watch:
        watch(args.watch)
        return
    if not args.config:
        parser.error("--config is required")
    cfg = json.loads(args.config.read_text())
    if cfg["mode"] not in ("clean", "interrupted", "stale"):
        parser.error("invalid mode")
    root = args.config.resolve().parent
    relay = Relay(cfg, root)
    try:
        asyncio.run(relay.run())
    except (Exception, asyncio.CancelledError) as exc:
        relay.event("invalid", reason=str(exc)[:200])
        raise


if __name__ == "__main__":
    main()
