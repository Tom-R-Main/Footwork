"""Four-tool MCP stdio facade for one preconfigured local fixture task.

Launch with ``python -m jevdual.capability.mcp_server --scope scope.json
--journal operations.sqlite``. This registers no host configuration and starts
no browser/app; scope and fixture ownership are established by the caller.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from .backend import ScopedBackend
from .contracts import TOOL_SCHEMAS, CapabilityError, check_arguments
from .journal import Journal, JournalError
from .service import CapabilityService


class ToolFacade:
    def __init__(self, backend: ScopedBackend, service: CapabilityService) -> None:
        self.backend = backend
        self.service = service
        self._surface_busy = False

    async def call(self, name: str, arguments: Any) -> dict[str, Any]:
        args = check_arguments(name, arguments)
        if name == "status":
            return await self.service.status(task=self.backend.task, **args)
        # One surface owner in this thin process; never queue an append decided
        # against an old snapshot behind another caller's mutation/observation.
        if self._surface_busy:
            raise CapabilityError("busy", "A surface call is in progress. Call status, then observe again.")
        self._surface_busy = True
        try:
            if name == "bind":
                return await self.backend.bind(args["name"])
            if name == "observe":
                return await self.backend.observe(args["resource"])
            token = args.get("client_token")
            prior = self.service.journal.by_token(self.backend.task, token) if token else None
            if prior is not None:
                resource, observation, move = prior.resource, prior.observation, prior.move
            else:
                offered = self.backend.offered(args["target"])
                resource, observation, move = offered.resource, offered.observation, offered.move
            return await self.service.act(
                task=self.backend.task,
                resource=resource,
                observation=observation,
                target=args["target"],
                move=move,
                args={"text": args["text"]},
                client_token=token,
            )
        finally:
            self._surface_busy = False


def create_server(facade: ToolFacade) -> Any:
    # Optional transport dependency: importing/core diagnostics need no provider.
    from mcp import types
    from mcp.server import Server

    server = Server("footwork-capability", version="0.1.0")

    async def list_tools(_context: Any, _params: Any) -> Any:
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name=name, description=definition["description"], input_schema=definition["inputSchema"]
                )
                for name, definition in TOOL_SCHEMAS.items()
            ]
        )

    async def call_tool(_context: Any, params: Any) -> Any:
        is_error = False
        try:
            # The SDK's stdio transport owns fd1 and diverts diagnostics to
            # stderr. Avoid process-global redirection across concurrent calls.
            result = await facade.call(params.name, params.arguments or {})
        except CapabilityError as exc:
            result, is_error = exc.to_result(), True
        except Exception as exc:  # noqa: BLE001 - public diagnostics do not expose arbitrary exception content
            logging.getLogger(__name__).error("Tool %s failed (%s)", params.name, type(exc).__name__)
            result = CapabilityError(
                "tool_unavailable", "The tool could not finish. Call status for any unresolved operation."
            ).to_result()
            is_error = True
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
            structured_content=result,
            is_error=is_error,
        )

    server.add_request_handler("tools/list", types.PaginatedRequestParams, list_tools)
    server.add_request_handler("tools/call", types.CallToolRequestParams, call_tool)
    return server


async def serve(scope: dict[str, Any], journal_path: Path) -> None:
    from mcp.server.stdio import stdio_server

    backend = ScopedBackend(scope, durable=True)
    journal = Journal(journal_path)
    facade = ToolFacade(backend, CapabilityService(journal, backend))
    server = create_server(facade)
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        try:
            await backend.close()
        finally:
            journal.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True, type=Path)
    parser.add_argument("--journal", required=True, type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    try:
        scope = json.loads(args.scope.read_text())
        asyncio.run(serve(scope, args.journal))
    except (CapabilityError, JournalError) as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"invalid_configuration: {type(exc).__name__}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
