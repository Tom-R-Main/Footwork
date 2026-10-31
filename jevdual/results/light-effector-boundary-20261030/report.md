# Lazy effector boundary: L1a

Checked 2026-10-30 on macOS arm64, Python 3.12.6. Product source: `dda70d06848d802bd35393f46c14381d2874486b`, based on Linux reliability merge `5acf3b2`. Plan: `docs/plans/light-profile-20261030.md`.

The package isolates CUA behind a lazy compatibility adapter. It preserves the original SDK records, driver objects, browser authorization predicates, options, effect mapping and awaited shutdown. It does not remove CUA from metadata or implement a new browser backend.

| Promise | Boundary exercised | Observed result |
|---|---|---|
| Optional SDK imports stay isolated | AST plus subprocess-blocked CLI/module imports | Only effectors/cua.py imports CUA; catalog/schema/doctor work with optional imports blocked |
| Existing bridge behavior remains compatible | Full existing regression suite with exact cleanup2 SDK; real SDK seam checks | 2,487 passed, 100 skipped, 13 browser tests deselected; focused SDK/adapter checks 64 passed |
| Missing CUA cannot reset a session or launch Chrome | Public CLI, native/browser, fresh/existing session; real dependency-free installed wheel | Four installed cases refuse with effector_unavailable; retained state stays intact; fresh directories stay absent |
| Missing package differs from broken install | Adapter negative controls | Missing cua_driver is typed; transitive ModuleNotFoundError is preserved |
| Adapter keeps lifecycle semantics | Identity/object/kwargs tests; waiting and cancellation controls | Original driver and SDK records returned; shutdown remains awaited and cancellation propagates |
| Artifact contains the new adapter | Reproducible pure wheel build, byte inventory/RECORD, outside-checkout discovery | 201 files match source; package and unified CLI checks passed |

Wheel SHA256: `f1a67ce77bff88c0ed3e94940b56d57f5dff2f5a407493cd184bb440856726db`. Native test artifact: `cua_driver-0.38.0+footwork.d5373879.cleanup2-py3-none-macosx_13_0_arm64.whl` from final PR12 CI run `41131079404`. The isolated test interpreter borrows existing test dependencies through a .pth file and overlays that exact SDK; it is not a fresh dependency install. The package-check environment is fresh, offline and dependency-free.

Reproduce from the repository's jevdual directory with the matching SDK and test dependencies: `JEVDUAL_PURE_PY=1 PYTHONPATH=python python -m pytest -q -m 'not browser'`; run `python scripts/capability_package_check.py --run-dir <new project output directory>` and `python scripts/unified_cli_check.py --python <run>/venv/bin/python`. Ruff and all 103 packaged-resource checks pass. Notebook check passes after correcting a duplicate prediction identifier.

## Retained failures

- The first pre-edit focused baseline found the old local SDK version, not a product regression. A separate environment uses the final cleanup2 artifact; the primary environment was unchanged.
- Two new discovery-probe construction failures were repaired: availability checks need missing-module find_spec results rather than a raising finder, and Python 3.12 needs explicit importlib.util import. Logs remain.
- Review caught a real refactor regression: moving the missing-SDK check after session reset removed retained files and could attempt a Chrome launch. All four public-command cases fail before the import-only preflight and pass after it. No driver is created by that preflight. Existing session history may gain its normal stopped record; prior bytes remain retained.
- The first broad invocation ran from the repository root; four worker fixtures could not import tests and the redactor test could not find its relative script. Running from the documented jevdual directory passes the full suite. No product assertion was weakened.

## Limits and next gate

This checks import isolation, compatibility records, fixture behavior and installed discovery. It does not repeat PR12's live Linux desktop stress qualification or exercise a new live CDP backend. Existing browser durable authority remains unavailable. No resource savings or CUA-free runtime is claimed. L1b owned contracts, direct CDP, durable browser recovery, dependency profiles and profile-aware guide/discovery remain separate packages. Hosted final-head Linux/macOS build and binary-consumer jobs must pass before landing.

## Hosted simulator gate remediation

The first hosted implementation head `d10a35b` passed its core tests and all three binary-consumer jobs, then failed one of 332 simulator tests: cancellation was requested after a fixed sleep but before any native step. The same simulator source passed plan PR13; running intent is written before native initialization/stepping. A deliberate two-second pre-motion delay reproduces the exact zero-step failure.

Test-only fix `0d4dba8`: an actual-process timing fixture waits for a bound marker emitted after a real MuJoCo step advances simulation time, sends the public cancel RPC, then releases the worker. All original positive-step, verified-stop, retained generation/hash and duplicate-cancel assertions remain. Missing, malformed, nonfinite, zero-progress and foreign-operation/controller markers refuse. The marker is test synchronization; the simulator's own retained stop receipt remains the evidence. No simulator production code or stop threshold changed. The independent artifact-check fixture now honors the same FOOTWORK_EXECUTABLE override as production, preserving its default.

Observed locally: all 29 controller tests pass in the parent's independent run with MuJoCo 3.15.0 and the real installed artifact CLI; three focused checks also pass. The retained positive run advances native time 1.000 to1.002 before cancellation and records native_steps_before_cancel=1 with verified stop/state retention. Earlier local environment failures (missing checkout .venv, then a hardcoded test-side CLI path) and one malformed negative-fixture construction remain classified in their logs. The product wheel still matches the unchanged runtime source. Hosted checks must pass on the new head before merge; the failed first head remains retained.
