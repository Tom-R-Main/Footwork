from __future__ import annotations

import json
import os
import select
import subprocess
import sys
from types import SimpleNamespace

import pytest
from jevdual.capability.contracts import CapabilityError, DispatchOutcome, Validated
from jevdual.capability.journal import Journal
from jevdual.capability.mcp_server import ToolFacade, create_server
from jevdual.capability.service import CapabilityService


class SurfaceBackend:
    task = "task"

    def __init__(self):
        self.doc = "prefix\n"

    async def validate(self, resource, observation, target, move, args):
        return Validated(resource, observation, target, move, args, self.doc)

    async def dispatch(self, validated):
        self.doc += validated.args["text"]
        return DispatchOutcome("sent", "confirmed")

    async def readback(self, validated):
        return {"outcome": "applied" if self.doc == validated.context + validated.args["text"] else "partial"}

    def same_incarnation(self, resource):
        return True

    async def bind(self, name):
        return {"resource": name, "observation": "obs", "elements": []}

    async def observe(self, resource):
        return {"resource": resource, "text": self.doc}

    def offered(self, target):
        return SimpleNamespace(resource="native:3:4", observation="obs", move="append")


async def test_facade_requires_no_internal_binding_fields_and_token_repeat_skips_target_lookup(tmp_path):
    backend = SurfaceBackend()
    journal = Journal(tmp_path / "ops.sqlite")
    facade = ToolFacade(backend, CapabilityService(journal, backend))
    try:
        args = {"target": "target", "text": "17.25", "client_token": "call-1"}
        first = await facade.call("act", args)
        backend.offered = lambda target: (_ for _ in ()).throw(CapabilityError("stale_target", "expired"))
        second = await facade.call("act", args)
        assert first["operation_id"] == second["operation_id"] and second["repeat"]
        with pytest.raises(CapabilityError, match="different"):
            await facade.call("act", {**args, "text": "19.25"})
    finally:
        journal.close()


def test_real_stdio_catalog_errors_status_and_eof_shutdown(tmp_path):
    scope = tmp_path / "scope.json"
    scope.write_text(
        json.dumps(
            {
                "task": "fixture",
                "source": {"pid": 1, "window_id": 2, "url": "http://127.0.0.1:8000/"},
                "destination": {"pid": 3, "window_id": 4, "document": str(tmp_path / "doc.txt")},
            }
        )
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "jevdual.capability.mcp_server",
            "--scope",
            str(scope),
            "--journal",
            str(tmp_path / "ops.sqlite"),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    def send(method, params, request_id=None):
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        if request_id is not None:
            message["id"] = request_id
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
        if request_id is None:
            return None
        assert select.select([process.stdout], [], [], 8)[0], "MCP response timed out"
        response = json.loads(process.stdout.readline())
        assert response["id"] == request_id, response
        assert "error" not in response, response
        return response["result"]

    try:
        initialized = send(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "footwork-fixture-test", "version": "1"},
            },
            1,
        )
        assert initialized["serverInfo"]["name"] == "footwork-capability"
        send("notifications/initialized", {})
        catalog = send("tools/list", {}, 2)
        assert [t["name"] for t in catalog["tools"]] == ["bind", "observe", "act", "status"]
        refusal = send("tools/call", {"name": "act", "arguments": {"text": "x"}}, 3)
        assert refusal["isError"]
        assert json.loads(refusal["content"][0]["text"]) == refusal["structuredContent"]
        status = send("tools/call", {"name": "status", "arguments": {}}, 4)
        assert status["structuredContent"]["unresolved"] == []
        process.stdin.close()
        assert process.wait(timeout=8) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=8)


async def test_server_emits_matching_json_text_and_structured_error(tmp_path):
    from mcp import types

    backend = SurfaceBackend()
    journal = Journal(tmp_path / "ops.sqlite")
    server = create_server(ToolFacade(backend, CapabilityService(journal, backend)))
    # The SDK request handler is the transport-facing public contract; a
    # separate subprocess test exercises actual stdio framing and teardown.
    try:
        handler = server._request_handlers["tools/call"].handler
        result = await handler(None, types.CallToolRequestParams(name="act", arguments={"text": "17.25"}))
        assert result.is_error
        assert json.loads(result.content[0].text) == result.structured_content
        assert result.structured_content["error"]["code"] == "invalid_arguments"
    finally:
        journal.close()
