# RV2 native review remediation

Prediction: `jevdual/docs/notebook/2026-10-29-review-merge.md`, RV2, committed by root as `706a3f8` before reproduction.

## Red

From `jevdual/`:

```sh
.venv/bin/python -m pytest tests/test_posture.py tests/test_session_file_targets.py -q -k 'ambiguous_keyboard_error_cannot or rename_rechecks'
```

`red.txt`: 11 failed, 53 deselected in 1.16s. The independent simulated input ledgers recorded a forbidden second key for opaque replies, opaque exceptions and mixed positively delivered errors; they also recorded Rename after delayed front/window/selection changes and AXValue after editor ownership changed. Production code was unchanged for this run.

## Repair

- `native.py`: fallback requires typed qualified no-send with the exact ambiguity code, or the pinned SDK's exact target-bound structured pre-actuator refusal. Opaque prose, exceptions, wrong targets and mixed positive delivery do not authorize a second input.
- Local pinned source check: `external/cua/libs/cua-driver/rust/crates/platform-macos/src/tools/mod.rs`, `background_refusal_result`, supplies `code`, `effect: refused`, PID and window before any actuator. `cua-driver-sdk/src/lib.rs` retains that error reply's structured JSON but leaves `action=None`. The gate preserves this real legacy contract and the typed refusal contract.
- Finder rechecks exact front PID, main/focused window and sole owned row immediately before the delayed Rename leaf. It revalidates the same current editor, window ownership and selection immediately before AXValue. The documented exact Finder transient-editor case can retain a null focused window only with the owned current editor and exact main window.
- Existing ambiguity escalation fixture now models the real structured SDK refusal; regressions also preserve typed refusal escalation and challenge malformed/contradictory structured evidence.

## Green

From `jevdual/`:

```sh
.venv/bin/python -m pytest tests/test_posture.py tests/test_session_file_targets.py tests/test_session_finder_move.py tests/test_finder_move.py tests/test_native_foreground_intent.py tests/test_native_receipts.py -q
.venv/bin/python -m ruff check python/jevdual/native.py tests/test_posture.py tests/test_session_file_targets.py
.venv/bin/python -m ruff format --check python/jevdual/native.py tests/test_posture.py tests/test_session_file_targets.py
```

`green.txt`: 141 passed in 19.80s. `lint.txt`: all checks passed. Own files formatted; repository `git diff --check` passed.

Changed only `jevdual/python/jevdual/native.py`, `jevdual/tests/test_posture.py`, `jevdual/tests/test_session_file_targets.py` and these ignored evidence outputs. No commits, GUI, network, provider calls or installed-app qualification. Root owns the notebook result, full suite, independent review and commit.
