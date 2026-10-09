"""Qualify actual raw MCP servers without an agent or provider call.

Catalog mode requires no UI. Live mode reads only the scoped fixture browser and
sets the exact owned TextEdit field, checking the result through the independent AX
oracle. Full responses stay in private output, including screenshots if returned.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from capability_host_trial import ax_document_text, ax_reset_text
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

NATIVE_TOOLS = ("get_window_state", "set_value", "type_text", "hotkey", "press_key")
NODE = "/Users/thomasmain/.nvm/versions/node/v22.17.1/bin/node"


def native_manifest(destination: dict[str, Any]) -> str:
    return (
        "version: 1\nmode: bounded\nexpires_after: 1h\nidle_timeout: 15m\n"
        "resources:\n  desktop:\n    windows:\n"
        f"      - pid: {destination['pid']}\n        window_id: {destination['window_id']}\n"
        f"allow:\n  tools: [{', '.join(NATIVE_TOOLS)}]\n"
    )


def raw_parameters(
    runtime: dict[str, Any], manifest: Path, browser_url: str
) -> dict[str, StdioServerParameters]:
    return {
        "chrome": StdioServerParameters(
            command=NODE,
            args=[
                runtime["cli"],
                "--browserUrl",
                browser_url,
                "--no-usage-statistics",
                "--no-performance-crux",
                "--no-javascript-evaluation",
            ],
        ),
        "native": StdioServerParameters(
            command=str(Path(sys.executable).parent / "cua-driver"),
            args=["mcp", "--direct"],
            env={
                **os.environ,
                "CUA_DRIVER_PERMISSION_MODE": "bounded",
                "CUA_DRIVER_CAPABILITY_MANIFEST_FILE": str(manifest),
                "CUA_DRIVER_CAPABILITY_MANIFEST_APPROVED": "1",
                "CUA_DRIVER_POLICY_FILE": str(manifest.with_name("native-policy.yaml")),
            },
        ),
    }


def dump_model(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json", by_alias=True, exclude_none=True)


async def probe(args: argparse.Namespace) -> dict[str, Any]:
    root = args.run_dir.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    runtime = json.loads(args.runtime.read_text())
    scope = json.loads(args.scope.read_text()) if args.scope else None
    destination = scope["destination"] if scope else {"pid": 424242, "window_id": 777}
    manifest = root / "native-manifest.yaml"
    manifest.write_text(native_manifest(destination))
    manifest.with_name("native-policy.yaml").write_text(f"allow:\n  tools: [{', '.join(NATIVE_TOOLS)}]\n")
    browser_url = args.browser_url or "http://127.0.0.1:1"
    parameters = raw_parameters(runtime, manifest, browser_url)
    report: dict[str, Any] = {"catalog_only": args.catalog_only, "servers": {}, "provider_calls": 0}
    for name, params in parameters.items():
        with (root / f"{name}-stderr.log").open("w") as error_log:
            async with (
                stdio_client(params, errlog=error_log) as (read, write),
                ClientSession(read, write) as session,
            ):
                init = await session.initialize()
                tools = await session.list_tools()
                catalog = [tool.name for tool in tools.tools]
                (root / f"{name}-initialize.json").write_text(json.dumps(dump_model(init), indent=2))
                (root / f"{name}-tools.json").write_text(json.dumps(dump_model(tools), indent=2))
                result: dict[str, Any] = {"server": dump_model(init.server_info), "tools": catalog}
                report["servers"][name] = result
                if name == "native":
                    outside = await session.call_tool(
                        "get_window_state",
                        {
                            "pid": 2147483647,
                            "window_id": 2147483647,
                            "include_screenshot": False,
                        },
                    )
                    outside_data = dump_model(outside)
                    (root / "native-outside-refusal.json").write_text(json.dumps(outside_data, indent=2))
                    result["outside_refusal"] = outside_data
                if args.catalog_only:
                    continue
                if name == "chrome":
                    listed = await session.call_tool("list_pages", {})
                    (root / "chrome-pages.json").write_text(json.dumps(dump_model(listed), indent=2))
                    page = await session.call_tool("take_snapshot", {"pageId": 1})
                    page_data = dump_model(page)
                    (root / "chrome-snapshot.json").write_text(json.dumps(page_data, indent=2))
                    result["expected_value_seen"] = args.expected_value in json.dumps(page_data)
                    result["snapshot_error"] = bool(page.is_error)
                    if not result["expected_value_seen"] or result["snapshot_error"]:
                        raise RuntimeError("raw browser did not observe the expected fixture value")
                else:
                    reset = args.start_text
                    ax_reset_text(destination["pid"], destination["document"], reset)
                    if ax_document_text(destination["pid"], destination["document"]) != reset:
                        raise RuntimeError("independent initial AX state mismatch")
                    observation = await session.call_tool(
                        "get_window_state",
                        {
                            "pid": destination["pid"],
                            "window_id": destination["window_id"],
                            "include_screenshot": False,
                        },
                    )
                    data = dump_model(observation)
                    (root / "native-observation.json").write_text(json.dumps(data, indent=2))
                    elements = (observation.structured_content or {}).get("elements", [])
                    areas = [el for el in elements if el.get("role") == "AXTextArea"]
                    if len(areas) != 1 or not areas[0].get("element_token"):
                        raise RuntimeError("raw native MCP did not offer one opaque TextEdit target")
                    expected = (
                        reset + ("" if not reset or reset.endswith("\n") else "\n") + args.expected_value
                    )
                    action = await session.call_tool(
                        "set_value",
                        {
                            "pid": destination["pid"],
                            "window_id": destination["window_id"],
                            "element_token": areas[0]["element_token"],
                            "value": expected,
                        },
                    )
                    (root / "native-action.json").write_text(json.dumps(dump_model(action), indent=2))
                    actual = ax_document_text(destination["pid"], destination["document"])
                    result["exact_independent_readback"] = actual == expected
                    result["action_error"] = bool(action.is_error)
                    ax_reset_text(destination["pid"], destination["document"], reset)
                    result["reset_verified"] = (
                        ax_document_text(destination["pid"], destination["document"]) == reset
                    )
    native_offered = set(report["servers"]["native"]["tools"])
    report["native_catalog_is_bounded"] = native_offered == set(NATIVE_TOOLS)
    report["runtime_receipt_sha256"] = hashlib.sha256(args.runtime.read_bytes()).hexdigest()
    (root / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--browser-url")
    parser.add_argument("--expected-value", default="17.25 USD")
    parser.add_argument("--start-text", default="Invoice report\n")
    parser.add_argument("--catalog-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.catalog_only and (not args.scope or not args.browser_url):
        parser.error("live probe requires --scope and --browser-url")
    project = Path(__file__).resolve().parents[2]
    if not args.run_dir.resolve().is_relative_to(project / "output"):
        parser.error("probe output must stay in the project's private output")
    if not args.execute:
        print(json.dumps({"catalog_only": args.catalog_only, "run_dir": str(args.run_dir)}))
        return
    if not args.catalog_only:
        from ApplicationServices import AXIsProcessTrusted
        from jevdual.posture import screen_locked

        if screen_locked() or not AXIsProcessTrusted():
            parser.error("live probe requires unlocked desktop and existing Accessibility permission")
    print(json.dumps(asyncio.run(asyncio.wait_for(probe(args), timeout=90)), indent=2))


if __name__ == "__main__":
    main()
