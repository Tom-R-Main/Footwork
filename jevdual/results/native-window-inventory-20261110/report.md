# Read-only PID-scoped window inventory

Preregistered in commit `60a4d89`. The public baseline refused the absent command.

`footwork windows --pid POSITIVE` reports genuine SDK window IDs and titles,
including null/empty untitled titles. It reads no other process and has no session,
activation, screenshot, input, selection or automatic routing operation. Ownership,
ID and title validation precede all row output; failures emit no selectable rows.
It reports `read_only: true` and `association_verified: false`. PID/window binding
and subsequent action guards remain unchanged.

Validation: `scenarios.txt` contains 19 passing public inventory/discovery checks;
`focused.txt` contains 407 passing session/CLI/discovery tests. Ruff and notebook
validation pass. An actual shortened asyncio deadline test proves read cancellation
and cleanup; errors never disclose the fixture's foreign/private title. Existing
session JSON/log bytes remain unchanged. The list→exact untitled start scenario
completes with the intended ID and no input.

The affected test command from `jevdual/` was:
`PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_cli.py tests/test_agent_cli.py tests/test_tool_catalog.py`

No full-suite repeat was needed because only the standalone read-only CLI and its
discovery allowlist changed; no binding guard or SDK runtime changed. The worker
performed no live UI observation/input, installation or native build. Inventory
establishes neither key-window status nor parent/modal association. IDs can become
stale, so use a fresh list and retain existing start/preflight qualification.
