# Exact owned AXSheet modal resolution

Read-only exploration preregistration `d79128b`; repair preregistration `9d0aaa8`; frozen production source `16a67f4`.

The authorized bounded probe found Chrome's owned Save AXSheet325928 directly associated with parent306787. Chrome's AXFocusedWindow was the sheet while AXMainWindow remained the parent. SDK observation could bind325928, but the previous direct AX resolver searched only top-level AXWindows. No remote save-service PID was implicated or queried. These observations are in `output/suno-20261110/{save-modal-observation,modal-bindability}.json`.

The AX-only repair resolves the exact requested CGWindowID as a same-PID AXSheet with a direct parent chain to one of that application's top-level AXWindows. Any AXWindow attribute must agree with that association. Searches exclude WebArea inference and remote PIDs, reject ambiguous sheets, and are bounded to64 roots,512 descendants, depth16 and32 parent links. A requested parent still returns its own AXWindow. An already exact-key sheet needs no AXMain/AXRaise write; a non-key sheet refuses instead of raising its parent. Existing `_front_and_key` checks remain unchanged.

The first public fixture attempt had an inconsistent SDK PID and failed at start; that is not the behavioral reproducer. After correction, the unmodified prior ax.py snapshot fails only the intended modal hotkey (one failure/five guard passes, `baseline.txt`). The repair passes all6 public cases (`scenarios.txt`): correct modal, parent, wrong PID, unrelated association, non-key sheet and traversal bound. The broader AX cases also cover missing/contradictory association, duplicate sheet objects, focused-sheet references and unchanged parent raising. `focused.txt`:595 affected tests and CUA contracts pass; Ruff passes.

Full default offline validation on frozen16a67f4 passed3242 tests with62 normal opt-in skips in203.13 seconds. `full-default.json` records command, source hash, exit code and timing; `full-default.txt` is the pytest output. No live/browser opt-in was active. The parent separately reported actual GoToFolder success using the frozen repair; its evidence is `output/suno-20261110/save-b-go-folder-16a67f4.txt`. That live operation was not performed by this worker.

The subsequent bounded read-only probe found nested GoToWindow AXSheet326559, directly parented to Save325928 and then original306787. Both SDK observation and the repaired resolver can bind326559. Its SDK title is empty, motivating the separate explicit-CGWindow start package. Fresh nested control index2 is AXTextField. These probes made no input/focus/activation changes: `output/suno-20261110/{go-to-modal-observation,go-to-bindability,go-to-controls}.json`.

Commands from `jevdual/`:

```sh
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k public_save_modal_session
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_ax_semantics.py tests/test_session.py tests/test_posture.py tests/test_native_foreground_intent.py tests/test_native.py tests/test_native_receipts.py tests/test_session_file_targets.py tests/test_session_finder_move.py tests/test_authorize.py tests/test_cli.py tests/contract
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q
.venv/bin/ruff check python/jevdual/ax.py tests/test_ax_semantics.py tests/test_session_scenarios.py
```

No SDK build, native-byte change or installation occurred. No worker input, activation, pointer motion, clipboard access or Save occurred. Parent-window requests never implicitly route to a child; project-only destination verification and final Save remain parent-owned workflow actions.
