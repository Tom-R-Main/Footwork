# Duplicate native-control identity

Prediction was committed in `7b326f2` before the resolving tests. Implementation starts from Footwork `7852bb7bb1106a7b00a1c15395bf19d99606a97a`; `verification.json` binds final file hashes and distinguishes the red source states from the final check.

## Result

The modeled public CLI demonstrated wrong backing delivery: selecting the second identical switch and then swapping backing objects caused the baseline to write setting-A; replacing the selected object caused a write to replacement-C. The fixture's backing identity and effect ledger are deliberately absent from the SDK snapshot. Distinct-label controls still wrote only the selected setting-B. See `red-behavior.txt`.

Pruning also hid collision evidence: five same-label toggles retained one offered row and the baseline dispatched to that row (`red-pruned.txt`). A transient-only repair then failed a save/load boundary: two identical ordinary buttons pruned to one, the original disappeared, and the next command dispatched to the surviving same-index lookalike (`red-historical-pruning.txt`). These are modeled reproductions, not observations of a live desktop.

## Change

- NativeMenu retains semantic collision IDs from before pruning. Generic native action dispatch refuses `target_ambiguous` before input; snapshot-local index/token, peer ordinal and mutable state are not promoted to backing identity.
- SessionState retains that native collision evidence with the previous observation. Numeric selection checks it before admission, even when the current offered menu has become a singleton. Missing legacy evidence requires fresh selection.
- Repeated controls remain visible for observation and effect comparison. Their old ordinal-based generic action path is intentionally withdrawn until a qualified identity seam exists. No native pointers, retained owner or daemon were introduced. Scoped file operations retain their existing separate identity route.

## Verification

Executed from `jevdual/`, using the existing environment and no install/fetch:

```sh
PYTHONPATH=/Users/thomasmain/projects/footwork/jevdual/python .venv/bin/python -m pytest tests/test_session_scenarios.py tests/test_control_state.py tests/test_native.py tests/test_session.py -q
.venv/bin/ruff check python/jevdual/native.py python/jevdual/session.py tests/test_session_scenarios.py tests/fixtures/native_world.py tests/test_control_state.py
```

**203 tests passed**, and Ruff passed. The scenarios cover same-count reorder/replacement, unchanged ambiguity, hidden/pruned peers, historical ordinary-button pruning/save-load, a sibling inserted during final live revalidation, peer disappearance, legacy refresh, and a unique-label positive control. Existing changed-process and unknown/no-replay cases pass within the affected suite. See `affected-final.txt`, `ruff.txt`, and `verification.json`.

The early historical guard returns a typed refusal before admission and creates no `do` record. A collision arising inside `act` preserves the existing CLI contract: exit0 can carry a typed not-dispatched receipt. Assertions inspect that delivery status and the independent backing-effect ledger rather than treating exit0 as delivery.

The first preliminary run failed a render-format assumption in a test precondition. It was corrected before the behavioral red; the preliminary output remains under `output/duplicate-controls-20261101/red.txt` and is not interpreted as evidence of a product defect.

## Limits and handoff

No live desktop, OS permission, provider, or heldout evaluation was exercised. This repair refuses positively observed duplicate collisions; it does not prove uniqueness in an incomplete backend tree with unseen peers. Mutable state cannot qualify known duplicate controls. Observational effect matching is not backing-object identity proof. Fresh label selection retains its existing current-query semantics.

Parent owns final integration, broad regression checks, commit identity and the lightweight installed-artifact qualification. No PR, push, merge or deployment was performed by this work package.
