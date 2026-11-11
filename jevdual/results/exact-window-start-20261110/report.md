# Explicit native CGWindow start selector

Preregistration `a571646`; frozen source `a64b6f2`. The parent-owned GoToWindow nested sheet has a complete SDK observation and exact CGWindow identity, but its SDK title is empty. The prior public start route filtered out untitled windows and only accepted a title substring. The separate read-only proof is `output/suno-20261110/{go-to-bindability,go-to-controls}.json`.

`start --pid PID --window-id CGWINDOWID` now selects one exact on-screen SDK window from that process, including untitled entries. It refuses absent or duplicate IDs without choosing a larger/titled parent. Both identifiers must be positive; the CGWindowID must fit unsigned32 bits. `--window-id` requires `--pid`; `--window`, `--browser` and `--url` are incompatible. Invalid combinations are rejected before driver creation or session reset. Existing observed app/PID/window verification, policy and action target checks remain intact. Finder-owned source selection is also constrained to the explicit ID. Default title-based selection is unchanged.

Baseline: five public CLI cases failed before the option existed (`baseline.txt`). All14 public boundary cases pass (`scenarios.txt`): exact untitled panel, stale ID, wrong PID, duplicate IDs, observed-identity drift and invalid selectors preserving an existing session without binding. Discovery reports the new argument. `focused.txt`:633 affected session/targeting/native/Finder/CLI/discovery/authorizer/operations and CUA contract tests pass; Ruff and diff checks pass.

Commands from `jevdual/`:

```sh
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k 'start_exact_window_id or start_invalid_exact_window_selector'
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_session.py tests/test_session_targeting_audit.py tests/test_native.py tests/test_session_file_targets.py tests/test_session_finder_move.py tests/test_cli.py tests/test_agent_cli.py tests/test_authorize.py tests/test_authorization_parity.py tests/test_session_operations.py tests/contract
.venv/bin/ruff check python/jevdual/{cli,session,native}.py tests/test_session_scenarios.py tests/test_agent_cli.py
```

Full default offline regression on frozena64b6f2 passed3256 tests with62 normal opt-in skips in213.96 seconds, exit0. `full-default.json` records command, timing and matching before/after hashes of ax.py/native.py/session.py/cli.py; `full-default.txt` contains pytest output. No live/browser opt-in was active. No SDK build, native-byte change, installation, worker input/focus/activation or session-JSON workaround occurred. A nested modal still requires an explicitly observed new binding; no parent-to-child input routing was added. Final folder/file save verification remains parent-owned.
