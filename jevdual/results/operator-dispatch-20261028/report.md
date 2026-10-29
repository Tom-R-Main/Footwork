# Operator dispatch uncertainty: package 1

October 28, 2026. Baseline: `5d494c6`; prediction committed before tests as `322b214`. Scope: simulated native bridge and real CLI commands against a fake driver. No live app, model/provider run or permission change.

## Reproduction

- `cli-before.txt`: four safety regressions failed; the cancellation characterization passed. A completed press was labeled refused/not dispatched, and explicit uncertain input did not invalidate prior completion evidence.
- `native-before.txt`: four safety regressions failed. The independent fake-driver ledger recorded two presses for one command after an injected post-press `-25204` error. Opaque error replies were also treated as refusal.
- Cancellation consumed the exact grant without retaining a do record; after a new grant, another press occurred. This remains an open durable-admission defect, explicitly characterized rather than silently marked fixed.

## Correction

Native errors after possible input and opaque tool errors now remain unverifiable. Qualified pre-input refusals retain no-send. Automatic `-25204` retry is removed; uncertain scroll/selection cannot authorize fallback input. Foreground title-bar input, select-all, post-write readback loss and post-input observation errors preserve their input history. CLI receipt/completion metadata distinguishes qualified no-send from attempted or unknown input. Legacy receipts remain readable. Desktop loop reporting consumes the same distinction.

Independent review found and resolved select-all continuation, foreground preparation and append readback gaps. It reported no remaining blocking finding after those corrections.

## Verification

Commands ran from `jevdual/` with the existing `.venv`, without installation:

- `.venv/bin/pytest -q tests/test_session_scenarios.py tests/test_completion.py tests/test_desktop.py`: **233 passed** (`cli-after.txt`).
- Native/posture slice: **74 passed** (`native-after.txt`).
- `.venv/bin/pytest -q`: **1724 passed, 26 skipped** (`suite-final.txt`).
- `.venv/bin/ruff check python evals tests scripts`: passed (`lint.txt`).
- `git diff --check`: passed.

`suite.txt` retains an intermediate full-suite run with two old expectations that still assumed opaque errors proved refusal; the final run follows their correction and all runtime edits. Before/after logs are retained beside this report.

## Limits and next gate

This closes package 1's returned/caught-error and uncertain-retry slice. It does not establish durable grant reservation, token replay, cancellation/SIGKILL safety, cross-session exclusion or installed Finder/Preview/Chrome support. Package 2 must replace the cancellation characterization with durable admission and recovery assertions. Diversified app qualification remains required by the implementation plan.
