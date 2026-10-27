"""Allowlisted installed auxiliary tool routes; no device or provider starts on discovery."""
from __future__ import annotations

import importlib.resources
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Public operational entrypoints. Libraries are exported for injection into an
# existing permitted browser runtime; discovery never claims to attach a browser.
_FAMILIES = {
    "camera": ("camera-capture-experiment", "capture.py", ("doctor", "capture", "status")),
    "inbox": ("desk-inbox-experiment", "inbox.py", ("prepare", "accept", "status")),
    "workbench": ("workbench-notes", "workbench.py", ("link", "status", "list")),
}
_WORKCELL = {
    "body": "workcell.py", "episode": "episode_runner.py", "controller": "controller.py",
    "bench": "bench.py", "agent-bench": "agent_bench.py", "body-network": "body_network.py",
    "order-app": "order_app.py", "app-handoff": "app_handoff.py", "image-guided": "image_guided.py",
    "bench-runner": "bench_runner.py", "bench-operator": "bench_operator.py",
    "network-bench-operator": "network_bench_operator.py", "measurement": "measurement.py",
    "record-network-workbench": "record_network_workbench.py",
    **{name.replace("_", "-"): f"{name}.py" for name in (
        "qualify_bench", "qualify_network_body", "qualify_network_workbench", "qualify_order_handoff",
        "qualify_workbench_crashes", "qualify_workbench_health", "qualify_workbench_recovery",
        "qualify_workbench_restarts", "score_agent_bench", "score_network_body", "score_network_workbench",
        "score_operator", "score_workbench_crashes", "score_workbench_health", "score_workbench_recovery",
        "score_workbench_restarts",
    )},
}
_NODE = {
    "browser-inspection": {"summarize": "summarize.mjs"},
    "inspection-experiments": {
        "compare": "compare.mjs", "coverage": "coverage.mjs", "publication-gate": "publication-gate.mjs",
    },
    "inspection-transport": {},
}
_LIBRARIES = {
    "browser-inspection": ("capture.mjs", "frontend.mjs", "redaction.mjs"),
    "inspection-experiments": ("findings-ledger.mjs", "workflow-observer.mjs"),
    "inspection-transport": (
        "event-ring.mjs", "stream-probe.mjs", "protocol-envelope.mjs", "graphql-envelope.mjs",
        "playwright-cdp-bridge.mjs", "polling-supervisor.mjs",
    ),
}


def resource_root() -> Path:
    # Standard wheel installations unpack resources to the filesystem. Parent
    # modules and native companion files must retain their sibling layout.
    return Path(str(importlib.resources.files("jevdual").joinpath("_tool_resources")))


def output_root() -> Path:
    return Path(os.environ.get("FOOTWORK_TOOL_OUTPUT_ROOT", str(Path.cwd() / ".footwork" / "tools"))).absolute()


def catalog() -> list[dict]:
    root = resource_root()
    rows = []
    for family, (directory, script, commands) in _FAMILIES.items():
        rows.append({
            "name": family, "commands": list(commands), "status": "available" if (root / directory / script).is_file() else "not_packaged",
            "prerequisites": ["macOS and ffmpeg for live capture"] if family == "camera" else ["explicit reviewed input; macOS Swift/Vision for OCR"] if family == "inbox" else [],
            "missing": [] if (root / directory / script).is_file() else ["packaged runtime resources"],
            "output_root": str(output_root() / directory),
        })
    missing = [name for name in ("mujoco", "numpy") if importlib.util.find_spec(name) is None]
    rows.append({"name": "workcell", "commands": sorted(_WORKCELL), "status": "optional_dependencies_missing" if missing else "available",
                 "prerequisites": ["mujoco==3.15.0", "numpy", "headless rendering libraries for image operations", "qualification commands require owned fixture inputs"],
                 "missing": missing, "output_root": str(output_root() / "physical-workcell"),
                 "command_prerequisites": {name: ["matching source checkout for Git-frozen research qualification"]
                                           for name in _WORKCELL if name.startswith(("qualify-", "score-", "record-"))}})
    for family, commands in _NODE.items():
        rows.append({"name": family, "commands": [*commands, "export"],
                     "status": "available" if shutil.which("node") else "optional_dependencies_missing",
                     "prerequisites": ["Node.js for executable analyses", "caller-supplied permitted tab/CDP adapter for capture libraries"],
                     "missing": [] if shutil.which("node") else ["node"], "capture": "adapter_required"})
    return rows


def _error(code: str, message: str) -> int:
    print(json.dumps({"error": code, "message": message}), file=sys.stderr)
    return 2


def _usage(family: str) -> None:
    row = next(row for row in catalog() if row["name"] == family)
    print(f"Usage: footwork {family} <command> [arguments]")
    print("Commands: " + ", ".join(row["commands"]))
    if "output_root" in row:
        print("Run directories: " + row["output_root"] + "/<run-name>")
    for prerequisite in row["prerequisites"]:
        print("Requires: " + prerequisite)


def run_tool(family: str, args: list[str]) -> int:
    """Execute one explicit tool command, preserving its existing exits and output."""
    if family not in {*_FAMILIES, "workcell", *_NODE}:
        return _error("unknown_tool", "Choose a tool family from footwork tools")
    if os.name == "nt" and family in {*_FAMILIES, "workcell"}:
        return _error("platform_unsupported", "These auxiliary filesystem/device adapters require POSIX; browser analysis libraries remain exportable")
    if not args or args == ["--help"] or args == ["-h"]:
        _usage(family)
        return 0
    root = resource_root()
    command, rest = args[0], args[1:]
    if family in _NODE and command == "export":
        if rest:
            return _error("invalid_arguments", "export takes no arguments; import the returned modules in your permitted runtime")
        modules = {name: str(root / family / name) for name in _LIBRARIES[family]}
        if not all(Path(path).is_file() for path in modules.values()):
            return _error("resources_missing", "Reinstall Footwork with its bundled tool resources")
        print(json.dumps({"family": family, "modules": modules, "capture": "adapter_required", "attaches_browser": False}))
        return 0
    if family in _FAMILIES:
        directory, script, commands = _FAMILIES[family]
        if command not in commands:
            return _error("unknown_command", "Choose a command from this family's help")
        argv = [sys.executable, str(root / directory / script), command, *rest]
    elif family == "workcell":
        script = _WORKCELL.get(command)
        if script is None:
            return _error("unknown_command", "Choose a command from footwork workcell --help")
        if command.startswith(("qualify-", "score-", "record-")):
            return _error("source_checkout_required", "Research qualification must run its Git-frozen source helper from a matching checkout; operational body/episode/controller commands are installed")
        streaming = command == "body-network" or (rest and rest[0] in {"serve", "server"})
        if streaming and not any(flag in rest for flag in ("--help", "-h")) and isinstance(sys.stdout, io.StringIO):
            return _error("streaming_protocol_required", "Run long-lived services without --json/invoke so readiness and line-protocol output stream immediately")
        missing = [name for name in ("mujoco", "numpy") if importlib.util.find_spec(name) is None]
        if missing:
            return _error("optional_dependencies_missing", "Install Footwork's workcell extra in this environment: " + ", ".join(missing))
        argv = [sys.executable, str(root / "physical-workcell" / script), *rest]
    else:
        script = _NODE[family].get(command)
        if script is None:
            return _error("unknown_command", "Choose a command from this family's help")
        if not shutil.which("node"):
            return _error("optional_dependencies_missing", "Node.js is required for this analysis")
        if rest in (["--help"], ["-h"]):
            usages = {"summarize": "<run-directory>", "compare": "<control-run> <variant-run>", "coverage": "<sealed-run-directory>", "publication-gate": "<repository> <base-ref> <policy-file>"}
            print(f"Usage: footwork {family} {command} {usages[command]}")
            return 0
        argv = [shutil.which("node"), str(root / family / script), *rest]
    if not Path(argv[1]).is_file():
        return _error("resources_missing", "Reinstall Footwork with its bundled tool resources")
    env = os.environ.copy()
    home = output_root()
    if family in {*_FAMILIES, "workcell"} and not any(flag in rest for flag in ("--help", "-h")):
        try:
            if any(path.is_symlink() for path in (home, *home.parents)):
                return _error("unsafe_output_root", "Choose a non-symlink tool output root")
            home.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Private captures and task state must not become source changes
            # when the installed CLI is used from another repository.
            try:
                fd = os.open(home / ".gitignore", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "w") as stream:
                    stream.write("*\n")
        except OSError:
            return _error("output_unavailable", "Cannot create the private tool output root")
    env["FOOTWORK_TOOL_OUTPUT_ROOT"] = str(home)
    env["FOOTWORK_PYTHON"] = sys.executable
    executable = Path(sys.executable).parent / ("footwork.exe" if os.name == "nt" else "footwork")
    env["FOOTWORK_EXECUTABLE"] = str(executable)
    # Child execution needs sibling imports, but never the caller's ambient
    # PYTHONPATH. The script's own directory is first through normal Python rules.
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    try:
        capture = isinstance(sys.stdout, io.StringIO)
        result = subprocess.run(argv, env=env, text=True, capture_output=capture, check=False)
    except OSError:
        return _error("runtime_unavailable", "The selected tool runtime could not be started")
    if capture:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


# The parser is inspected in an isolated child before parse_args can dispatch an
# operation. This reports the actual flags, required fields and nested commands.
_SCHEMA_PROBE = r'''
import argparse, contextlib, io, json, runpy, sys
from pathlib import Path
class Captured(BaseException): pass
captured = None
def capture(self, *args, **kwargs):
    global captured
    captured = self
    raise Captured()
argparse.ArgumentParser.parse_args = capture
path = Path(sys.argv[1]); sys.path.insert(0, str(path.parent))
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    try: runpy.run_path(str(path), run_name='__main__')
    except Captured: pass
def schema(parser):
    result = {'usage': parser.format_usage().strip(), 'description': parser.description, 'arguments': [], 'subcommands': {}}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            result['subcommands'] = {name: schema(child) for name, child in action.choices.items()}
        else:
            item = {'name': action.dest, 'flags': action.option_strings, 'required': action.required,
                    'nargs': action.nargs, 'help': action.help}
            if action.choices is not None: item['choices'] = list(action.choices)
            result['arguments'].append(item)
    return result
if captured is None: raise SystemExit(2)
result = schema(captured)
if len(sys.argv)>2: result = result['subcommands'][sys.argv[2]]
print(json.dumps(result))
'''


def command_schema(family: str, command: str) -> dict:
    """Inspect a concrete command's parser without executing its operation."""
    root = resource_root()
    selection = []
    if family in _FAMILIES:
        directory, script, commands = _FAMILIES[family]
        if command not in commands:
            return {"error": "unknown_command"}
        script_path = root / directory / script
        selection = [command]
    elif family == "workcell" and command in _WORKCELL:
        missing = [name for name in ("mujoco", "numpy") if importlib.util.find_spec(name) is None]
        if missing:
            return {"error": "optional_dependencies_missing", "missing": missing,
                    "help_command": ["footwork", family, command, "--help"]}
        script_path = root / "physical-workcell" / _WORKCELL[command]
    elif family in _NODE:
        if command == "export":
            return {"arguments": [], "adapter_required": True, "executes_browser": False}
        positions = {"summarize": ["run_directory"], "coverage": ["sealed_run_directory"],
                     "compare": ["control_run", "variant_run"],
                     "publication-gate": ["repository", "base_ref", "policy_file"]}
        if command not in _NODE[family]:
            return {"error": "unknown_command"}
        return {"arguments": [{"name": name, "flags": [], "required": True} for name in positions[command]],
                "runtime": "node"}
    else:
        return {"error": "unknown_command"}
    if not script_path.is_file():
        return {"error": "resources_missing"}
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    try:
        result = subprocess.run([sys.executable, "-I", "-c", _SCHEMA_PROBE, str(script_path), *selection],
                                env=environment, capture_output=True, text=True, check=False, timeout=30)
        if result.returncode:
            return {"error": "schema_unavailable", "help_command": ["footwork", family, command, "--help"]}
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"error": "schema_unavailable"}
