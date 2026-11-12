# Guarded selected-range focus preparation

Preregistration `f7dcb32`; baseline on `e802740`: eight public CLI cases failed because there was no field-focus preparation (`baseline.txt`).

Only the explicit foreground selected-range type route now performs one AXFocused=true preparation on its freshly resolved bound text field. It requires independent application AXFocusedUIElement equality through CFEqual plus exact focused-window identity, with a 0.2-second cooperative readback deadline and no setter retry. It then reobserves/rematches the target and unchanged raw value, resolves the field anew, and proves focus again before checking the requested UTF-16 range and exact selected text. No pixel click, key or whitespace normalization is introduced. Whole-field replacement remains unchanged.

The new native readback records preparation attempted/acknowledged/confirmed separately. Any failed preparation or subsequent selection guard withholds text. If preparation was attempted, the overall input is uncertain; a code-boundary proof states zero dispatched text characters only when type_text was never called. Unknown text delivery never acquires that zero-character claim. Existing genuine SDK zero-text refusals retain their own producer evidence.

`scenarios.txt`: 43 selection/focus public CLI cases pass, including unreadable-until-focused selection, failed setter, acknowledged-but-unproven focus, wrong window, post-focus raw whitespace/value/identity/selection changes and lost focus. AX helper tests prove CFEqual is used for fresh references, missing/sibling focused elements refuse, wrong key windows refuse, and setter errors are retained. `focused.txt`: 695 affected session/native/menu/posture/AX/CLI/authorization/evidence/operations and CUA contract tests pass. Ruff, notebook and diff checks pass. `bridge-imports.txt` confirms the actual host bridge symbols import and are callable without accessing UI state.

Commands from `jevdual/`:

```sh
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k foreground_range_prepares_focus
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k 'foreground_range_prepares_focus or foreground_web_range'
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_session.py tests/test_session_targeting_audit.py tests/test_native.py tests/test_menu.py tests/test_control_state.py tests/test_posture.py tests/test_ax_semantics.py tests/test_native_foreground_intent.py tests/test_native_receipts.py tests/test_cli.py tests/test_agent_cli.py tests/test_authorize.py tests/test_authorization_parity.py tests/test_session_evidence.py tests/test_session_operations.py tests/contract
.venv/bin/ruff check python/jevdual/{native,ax}.py tests/test_session_scenarios.py tests/test_ax_semantics.py
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m evals.notebook docs/notebook --check
```

No worker UI input/probe, SDK rebuild, native-byte change or installation occurred. Bridge availability is not native behavioral qualification. Parent-owned live tests must independently inspect the rendered result and preserve earlier uncertain receipts. Selection and SDK synthesis remain sequential guarded operations, not an atomic renderer transaction.
