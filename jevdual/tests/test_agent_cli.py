"""Agent entry-point contracts: routing preserves payloads, authority and result semantics."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jevdual.agent_cli import route


def test_envelope_does_not_promote_exit_zero_to_effect_success(capsys):
    def legacy(args):
        assert args == ["do", "click", "12"]
        print('{"effect":"refused"}')
        return 0

    assert route(["--json", "do", "click", "12"], legacy) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["command_completed"] is True
    assert result["effect_verification"] == "not_asserted"
    assert result["data"] == {"effect": "refused"}
    assert result["output"] == ""
    assert "success" not in result


@pytest.mark.parametrize("payload", [None, [1, 2], "text", False, 0])
def test_json_envelope_keeps_structured_output_only_once(payload, capsys):
    def legacy(args):
        print(json.dumps(payload))
        print("diagnostic kept", file=sys.stderr)
        return 7

    assert route(["--json", "status"], legacy) == 7
    result = json.loads(capsys.readouterr().out)
    assert result["data"] == payload
    assert result["output"] == ""
    assert result["diagnostics"] == "diagnostic kept\n"
    assert result["command_completed"] is False


def test_json_envelope_keeps_non_json_stdout(capsys):
    def legacy(args):
        print("bound window\n{\"observation\":\"partial\"}")
        return 0

    assert route(["--json", "status"], legacy) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"] is None
    assert result["output"] == 'bound window\n{"observation":"partial"}\n'


def test_json_prefix_does_not_consume_literal_action_payload(capsys):
    seen = []
    assert route(["--json", "do", "type", "5", "--", "--json"], lambda args: seen.append(args)) == 0
    assert seen == [["do", "type", "5", "--", "--json"]]
    json.loads(capsys.readouterr().out)


def test_parser_failure_preserves_exit_code_and_json(capsys):
    def legacy(args):
        print("usage: invalid input", file=sys.stderr)
        raise SystemExit(2)

    assert route(["--json", "unknown"], legacy) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["exit_code"] == 2 and result["command_completed"] is False
    assert "usage" in result["diagnostics"]


def test_secret_diagnostics_are_redacted_without_copying_argv(capsys):
    def legacy(args):
        print("token: fixture-private-value", file=sys.stderr)
        return 7

    assert route(["--json", "run", "--secret", "TOKEN=fixture-private-value"], legacy) == 7
    text = capsys.readouterr().out
    assert "fixture-private-value" not in text
    assert "[REDACTED]" in text
    assert "argv" not in json.loads(text)


def test_browser_start_routes_to_existing_gate():
    seen = []
    assert (
        route(
            ["browser", "start", "Read title", "--url", "https://example.test"],
            lambda args: seen.append(args),
        )
        == 0
    )
    assert seen == [["start", "--browser", "Read title", "--url", "https://example.test"]]


def test_desktop_start_requires_explicit_app(capsys):
    called = []
    assert route(["--json", "desktop", "start", "Write text"], lambda args: called.append(args)) == 2
    assert not called
    assert "--app" in json.loads(capsys.readouterr().out)["diagnostics"]
    assert (
        route(["desktop", "start", "Write text", "--app", "TextEdit"], lambda args: called.append(args)) == 0
    )
    assert called == [["start", "Write text", "--app", "TextEdit"]]


def test_surface_alias_refuses_session_from_other_surface(tmp_path, capsys):
    from jevdual.session import SessionState

    SessionState(str(tmp_path), "TextEdit", 1, 2, "task", mode="native").save()
    called = []
    assert (
        route(
            ["--json", "browser", "do", "click", "1", "--session", str(tmp_path)],
            lambda args: called.append(args),
        )
        == 2
    )
    assert not called
    assert "different surface" in json.loads(capsys.readouterr().out)["diagnostics"]


def test_json_cannot_corrupt_mcp_stdout(capsys):
    assert route(["--json", "capability", "server", "--scope", "x", "--journal", "y"], lambda args: 0) == 2
    assert "MCP server owns stdout" in json.loads(capsys.readouterr().out)["diagnostics"]


def test_schema_reports_actual_required_arguments(capsys):
    assert route(["schema", "capability", "config"], lambda args: 99) == 0
    fields = {r["name"]: r for r in json.loads(capsys.readouterr().out)["arguments"]}
    assert fields["source_pid"]["required"]
    assert fields["document"]["required"]
    assert route(["schema", "browser", "start"], lambda args: 99) == 0
    assert any(
        r["name"] == "task" and r["required"] for r in json.loads(capsys.readouterr().out)["arguments"]
    )


def test_doctor_includes_optional_families_and_preserves_strict_code(monkeypatch, capsys):
    from jevdual import _native

    monkeypatch.setattr(_native, "core", None)

    def doctor(args):
        assert args == ["doctor", "--strict"]
        print('{"prerequisite_status":"blocked"}')
        return 1

    monkeypatch.setattr("jevdual.capability.cli.main", doctor)
    assert route(["--json", "doctor", "--strict"], lambda args: 99) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["prerequisite_status"] == "blocked"
    assert result["data"]["tool_families"]
    assert result["data"]["acceleration"]["available"] is False
    assert result["data"]["acceleration"]["component"] == "jevdual._core"
    assert "CUA" in result["data"]["acceleration"]["scope"]
    assert result["output"] == ""


@pytest.mark.parametrize(
    "args", [["--help"], ["tools"], ["--json", "schema"], ["schema", "capability", "config"]]
)
def test_public_executable_discovery_from_unrelated_cwd(tmp_path, args):
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-m", "jevdual.cli", *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert str(root) not in proc.stdout or args == ["tools"]
    if args != ["--help"]:
        json.loads(proc.stdout)


def test_json_request_uses_same_router_and_preserves_payload(monkeypatch, capsys):
    import io

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {"command": "browser", "args": ["start", "Read title", "--url", "https://example.test"]}
            )
        ),
    )
    seen = []
    assert route(["invoke", "--input", "-"], lambda args: seen.append(args)) == 0
    assert seen == [["start", "--browser", "Read title", "--url", "https://example.test"]]
    assert json.loads(capsys.readouterr().out)["effect_verification"] == "not_asserted"


@pytest.mark.parametrize(
    "payload",
    [
        {"command": "invoke", "args": []},
        {"command": "tools", "args": "not a list"},
        {"command": "tools", "args": [1]},
        {"command": "tools", "args": [], "env": {}},
        {"command": "tools", "args": ["x"] * 257},
        {"command": "--help", "args": []},
    ],
)
def test_json_request_rejects_bad_shapes_before_execution(payload, monkeypatch, capsys):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    seen = []
    assert route(["invoke"], lambda args: seen.append(args)) == 2
    assert not seen
    assert json.loads(capsys.readouterr().out)["exit_code"] == 2


def test_json_request_bounds_input_and_refuses_mcp_wrapping(monkeypatch, capsys):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO(" " * 65537))
    assert route(["invoke"], lambda args: 99) == 2
    assert "exceeds" in json.loads(capsys.readouterr().out)["diagnostics"]
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"command": "mcp", "args": []})))
    assert route(["invoke"], lambda args: 99) == 2
    assert "MCP server owns stdout" in json.loads(capsys.readouterr().out)["diagnostics"]


def test_auxiliary_schema_failure_remains_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(
        "jevdual.tool_catalog.command_schema",
        lambda family, command: {"error": "optional_dependencies_missing"},
    )
    assert route(["--json", "schema", "workcell", "body"], lambda args: 99) == 2
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["data"]["error"] == "optional_dependencies_missing"
    assert envelope["command_completed"] is False


def test_doctor_help_retains_captured_usage(capsys):
    assert route(["--json", "doctor", "--help"], lambda args: 99) == 0
    result = json.loads(capsys.readouterr().out)
    assert "--strict" in result["output"]
    assert result["exit_code"] == 0


@pytest.mark.parametrize("structured", [False, True])
def test_string_exit_retains_actual_parser_diagnostic(structured, capsys):
    from jevdual.session import parse_do

    words = ["do", "type", "3"]
    assert route((["--json"] if structured else []) + words, lambda args: parse_do(args[1:])) == 1
    captured = capsys.readouterr()
    message = json.loads(captured.out)["diagnostics"] if structured else captured.err
    assert "type needs text" in message


@pytest.mark.parametrize("structured", [False, True])
def test_string_exit_redacts_even_malformed_secret(structured, capsys):
    def legacy(args):
        raise SystemExit("--secret needs NAME=VALUE: opaque-test-credential")

    assert (
        route((["--json"] if structured else []) + ["run", "--secret", "opaque-test-credential"], legacy) == 1
    )
    captured = capsys.readouterr()
    assert "opaque-test-credential" not in captured.out + captured.err
    assert "[REDACTED]" in captured.out + captured.err


@pytest.mark.parametrize("structured", [False, True])
def test_actual_secret_parser_redacts_escaped_malformed_values(structured, capsys):
    from jevdual.cli import _secrets

    value = "opaque\ncredential"
    assert (
        route(
            (["--json"] if structured else []) + ["run", "--secret", value],
            lambda args: _secrets([value], "TextEdit"),
        )
        == 1
    )
    captured = capsys.readouterr()
    text = json.loads(captured.out)["diagnostics"] if structured else captured.err
    assert value not in text and repr(value)[1:-1] not in text
    assert "[REDACTED]" in text
