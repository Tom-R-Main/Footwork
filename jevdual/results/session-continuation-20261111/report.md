# Generic session continuation

Predictions were committed in `78c43ae`. Failed-start evidence first landed in
`e456fd0`; actual failed-start source and public scenarios landed in `d8e8d30`.
Post-action continuation is a separate source change.

Replacement starts initialize in a temporary owned session while existing
JSON/log/carry/destination/grant bytes remain intact. Only successful initialization
and driver cleanup allow publication; publication errors roll back old files.
Successful replacement inherits no old carries/grants. The saved directory points
to the final session, browser tab identity remains correct, stdout/log/state contain
no staging paths, and old screenshots survive name collisions.

If mandatory post-action observation is unavailable, `do` now returns **6** with
explicit pending/reconciliation guidance. This nonzero result is not permission
to resend: input may already have been delivered. Pending delivery and any durable
authoritative execution remain unchanged. The exact original binding and last
pre-action baseline remain; no fresh readback or application-effect receipt is
invented, and no modal closure or Save success is inferred. The command performs
no automatic input retry, parent-window routing or replacement-tab selection.

Use `footwork status --session DIR` for retained delivery evidence. Native sessions
can use `footwork windows --pid PID` read-only; if a different observed exact window
must be addressed, start a **fresh session** with its exact ID. Artifact checks or
independent application observation must establish actual save/application results.

Validation with the existing focus1 overlay:

- `start-baseline.txt`: four public failure cases failed before repair.
- `start-scenarios.txt`: seven replacement cases pass, including native/browser
  publication, cleanup failure, stale binding and rollback.
- `continuation-baseline.txt`: three public readback cases failed before repair.
- `continuation-scenarios.txt`: six ordinary/durable delivered/no-send cases pass;
  durable replay reuses unchanged execution and sends no additional input.
- `focused.txt`:610 affected session/scenario/authority/CLI/inspection tests pass.
  Ruff, notebook validation and diff check pass.

Focused command from `jevdual/`:
`PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_session.py tests/test_session_operations.py tests/test_session_evidence.py tests/test_session_targeting_audit.py tests/test_visual_inspection_session.py tests/test_authorize.py tests/test_authorization_parity.py tests/test_cli.py tests/test_agent_cli.py tests/test_grants.py`

Root owns one integrated full regression after concurrent packages are stable.
No independent redundant full suite, UI calls, network, installs or global
activation were performed. These fixes contain no application-specific branch.
