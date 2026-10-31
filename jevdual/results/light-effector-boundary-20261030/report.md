# Lazy effector boundary: L1a

Checked 2026-10-30 on macOS arm64, Python 3.12.6. Current runtime source: `e32913b35fcddcff6b518fc61b3242b8ebe68f5a`, based on Linux reliability merge `5acf3b2`. Plan PR13 is merged; implementation PR14 requires final-head CI before landing.

CUA imports, driver construction, SDK inputs and browser authorization now live behind a lazy compatibility adapter. Original SDK records, driver objects, strict authorization predicates, options, effect mapping and awaited shutdown remain. Missing SDK checks retain their original position before external work. CUA remains required in metadata; this is preparation for the light runtime.

| Promise | Boundary exercised | Observed result |
|---|---|---|
| Optional SDK imports stay isolated | AST and subprocess-blocked CLI/module imports | Only effectors/cua.py imports CUA; catalog/schema/doctor remain usable |
| Existing contracts remain compatible | Full regression suite with the exact cleanup2 SDK | 2,504 passed, 100 skipped, 13 browser tests deselected |
| SDK objects and lifecycle stay intact | Real SDK seams plus adapter tests | 81 passed; original records/options retained, shutdown awaited, cancellation propagates |
| Absence precedes external effects | Audit of all 25 original SDK import sites; failing sentinels before correction | Browser/desktop launch, keys/output, human/permission probes and driver calls follow availability checks |
| Existing sessions survive absent SDK | Actual dependency-free installed CLI outside checkout | Four native/browser fresh/existing cases refuse; retained files/history preserved; fresh directories absent |
| Other entry paths refuse safely | Installed run command and direct browser API | No output created or browser launch attempted; six installed absence cases pass in total |
| Artifact contains the checked adapter | Reproducible pure wheel, inventory/RECORD, installed discovery | All 201 files match runtime source; package and unified CLI checks pass |
| Simulator cancellation test has a real precondition | Real MuJoCo worker, public cancel RPC, invalid-marker controls | All 29 controller tests pass independently; original stop/state/positive-step assertions retained |

Final wheel SHA256: `bc6d09d1387677b904ec717fb546ce4ed536198a56bdfeba0d2a45c9c82bf109`. Native test artifact: `cua_driver-0.38.0+footwork.d5373879.cleanup2-py3-none-macosx_13_0_arm64.whl` from final PR12 CI run `41131079404`. The isolated test interpreter borrows existing test dependencies through a .pth file and overlays that SDK; it is not a fresh dependency install. Package-check environments are fresh, offline and dependency-free. Earlier artifacts/logs remain as history; the final audit receipts identify the current candidate.

From jevdual with matching SDK/test dependencies: `JEVDUAL_PURE_PY=1 PYTHONPATH=python python -m pytest -q -m 'not browser'`; run `scripts/capability_package_check.py` in a new owned output directory, then `scripts/unified_cli_check.py` against its installed interpreter. Ruff, all 103 packaged resources and the notebook check pass. The installed absence harness is retained as installed_absence_audit.py; its original ignored run layout is recorded in the script.

## Retained failures and corrections

- The first pre-edit baseline found an outdated local SDK. A separate environment uses cleanup2; the primary environment was unchanged. Two new discovery-probe construction errors were repaired (missing-module find_spec behavior and explicit importlib.util import on Python 3.12).
- Moving imports too late initially removed session files or attempted launch before SDK absence was known. Public start tests fail before entry preflight and pass after it. A complete follow-up audit covered all 25 former import sites: seven constructor-entry sentinels and five native/helper sentinels exposed further ordering changes; five immediate-input paths already refused correctly. Import-only checks restore ordering without creating a driver. Transitive/native loader failures keep their real diagnostic.
- The first broad pytest invocation used the repository root: worker fixtures could not import tests and the redactor test could not locate its relative script. The documented jevdual invocation passes. No product assertion was weakened.
- Hosted head d10a35b passed core tests and all three binary-consumer jobs, then failed one of 332 simulator tests: fixed sleep after running intent did not establish a native step. A deliberate two-second pre-motion delay reproduces that zero-step failure. Test-only source `0d4dba8` waits for a bound marker after a real MuJoCo step, issues public cancel and releases the worker. Missing/malformed/nonfinite/zero-progress/foreign markers refuse. All original assertions remain. No simulator production code or stop threshold changed.
- The retained positive simulator run advances time 1.000 to1.002 and records one native step before cancel, verified stop, retained state and matching generation/hash. The marker is test synchronization, not stop evidence; the simulator's own retained receipt supplies that evidence. Local environment failures exposed missing/hardcoded checkout CLI paths; the independent test now honors the existing FOOTWORK_EXECUTABLE override. One malformed negative-fixture construction is also retained.

## Limits and next gate

This verifies import isolation, compatibility, missing-effector ordering, fixture behavior and installed discovery. It does not repeat PR12's live Linux stress qualification or exercise a new CDP backend. Browser durable authority still refuses. No CUA-free runtime, resource savings or performance floor is claimed. Browser-owned contracts, direct CDP, durable recovery, dependency profiles and profile-aware discovery remain separate packages. Final-head hosted Linux/macOS build and binary-consumer gates must pass before merge; earlier successful and failed heads are distinct evidence.
