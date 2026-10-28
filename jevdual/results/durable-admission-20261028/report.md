# Durable native CLI admission

October 28, 2026. Baseline `deacfa9`; predictions/protocol committed before tests as `583cf6b`. This package implements the native CLI custody/replay portion of package 2, with explicitly limited reconciliation. No live app, provider, dependency installation or permission changes ran.

## Implemented

- Explicit `start --authority ABSOLUTE_DB` enrolls a fresh native session in one shared authority domain. Existing Journal transactions, operation rows and ownership locks are reused; Journal/MCP implementation was not modified.
- Required exact grants are reserved atomically with intent; ordinary policy-authorized operations need no artificial grant. Prepared/start markers precede input. Replay checks immutable raw request arguments before live binding, secrets, carries or authorization.
- Unknown operations block new mutations throughout the participating domain, including other sessions/apps. Qualified prepared-only recovery establishes no-send and releases once; started operations without a qualified result remain unknown.
- Reservation settlement remains distinct from effect completion. Unknown delivery holds authority. Qualified sent input spends it even when its effect remains unknown/blocked. SDK delivery counts are retained separately from attempted input.
- Session JSON replacement is atomic. Missing operation-log projections are repaired from the journal without sending input or resurrecting already-receipted pending operations. Status and exact replay work without the live app.
- Secret-bearing prepared records, errors and output are scrubbed. Frozen observation copying was corrected after the real secret scenario exposed an existing failure. Missing/short original secrets refuse fresh binding; replay/status remain available.

## Evidence

`tests/test_session_operations.py` uses synchronized subprocess SIGKILL at five boundaries with a separate fsynced fake-input ledger. The passing assertions establish:

| Killed at | Recovery and independent input count |
| --- | --- |
| Before intent | No operation; grant remains available; 0 inputs |
| Prepared | Qualified no-send; reservation released once; 0 inputs |
| Started | Unknown; reservation held; another session blocked; 0 inputs |
| Effect before finish | Unknown; reservation held; another session blocked; 1 retained input |
| Finish before response/projection | Final result and spent authority replay; 1 retained input |

Real CLI scenarios additionally exercise cancellation after an actual simulated granted press, exact replay with no additional press, new-token refusal, shared-domain blocking before secret resolution, changed process incarnation, preserved session history, lock contention without competing log writes, missing-projection repair, and secret-independent replay. Legacy interruption characterization remains explicitly outside durable mode.

The independent reviewer identified delivery/attempt conflation and secret-handling paths during implementation. Those findings were corrected; the final review reported no blocking findings in the stated scope. Earlier diagnostic outputs are retained, including failures that did not reach the intended driver boundary; those failures are not presented as admission/crash reproductions.

## Validation

Run from `jevdual/` using its existing `.venv`:

- Core plus existing capability journal/recovery slice: **75 passed** (worker verification).
- Integrated core/CLI/native/journal/recovery slice: **186 passed** (`focused.txt`).
- Final full `.venv/bin/pytest -q`: **1774 passed, 26 skipped** (`suite-final.txt`).
- `.venv/bin/ruff check python evals tests scripts`: passed (`lint.txt`).
- Notebook format and `git diff --check`: passed.

The final full-suite run includes the privacy gate and the short-secret refusal scenario. The earlier `suite.txt` predates these last controls; intermediate focused failures are retained separately. The source and final tests are committed together with this report.

Retained pytest transcripts have trailing whitespace normalized for repository diff checks; diagnostic text and results are preserved.

## Qualification limits

This is opt-in native CLI coordination within one configured authority database. Legacy sessions, MCP, browser mutation, older binaries, other databases and unrelated tools remain outside it. Process incarnation is qualified, but independent window-creation identity is not supplied by the current adapter. There is no general qualified reconciliation producer for started unknowns; their block is preserved rather than manually cleared. Direct AX routes lacking delivery evidence may remain unknown despite a matching current readback.

Secret observation assumes original values are restored: presence/length checks cannot detect rotation. Process-kill tests do not establish power-loss safety. Installed Finder, Preview, Chrome and independent onboarding remain unqualified. The next package supplies producer-backed evidence and qualified reconciliation before the installed portfolio.

Usage and migration limits: `docs/durable-native-operator.md`. Prediction/results: `docs/notebook/2026-10-28-durable-admission.md` and `docs/experiments/OA-durable-admission-20261028.md`.
