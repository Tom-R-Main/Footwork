# Independent combined PR review and remediation

This records the already-completed, same-context independent review and its remediation checks. Writing this artifact did not initiate another review or rerun tests. The reviewer made no production-source edits, commits, pushes, merges, network installs, live UI actions, paid provider calls, or heldout evaluations.

## Scope and verdict

- Base: `afe6d9493dc7d067ee67838b90650d59c902df17`.
- Initial reviewed target: `c9ba496eb201c23cc50d8b954756dd59616265fa`.
- Combined pending history: 268 commits and approximately 2,420 changed files, predominantly recorded research results.
- Review focus: changed production contracts and public callers, deterministic authorization and freshness, exact native append, write-ahead admission, no replay, process-crash reconciliation, completion evidence, advisory provider boundaries, and relevant local tests.
- Final remediation snapshot: seven uncommitted paths over `daa08466e2b79ba6891f1da51c241c18494c4997`, bound by the hashes below.
- Final verdict: **no residual actionable blocking findings in the inspected remediation**. All nine reproduced findings below are closed in that snapshot. Several follow-ups refine the same freshness defect rather than representing independent architectural defects.

The root agent owns full-suite checks, browser/native qualification on the new freeze, CI, packaging and Node/Rust checks, secret scanning, PR creation, and merge verification. The subsequent harness-only `4fb9a95` publication and actor checks are root-owned and were not reviewed here. This verdict does not claim that the final repository HEAD or that harness commit was independently requalified by this reviewer.

## Reproduced findings and resolutions

### 1. Exact content freshness lost at native append dispatch — P1, closed

Trigger: validate the exact field value `Invoice report`, then add a trailing space before dispatch. The scoped backend called the legacy native append path, whose `_norm_tail` comparison ignored the change. The actual AX insertion code, exercised over `TextWorld`, sent the append and reported confirmed; later scoped readback reported partial.

Resolution: `ScopedBackend.dispatch` supplies `AppendPrecondition` with the exact validated value. `NativeBridge._append` compares literal AX content with that baseline, and `ax.insert_at_end(expect=exact)` checks it again before insertion. The independently rerun whitespace case returned `not_sent` with no AX setters; unchanged literal whitespace in the payload remained preserved.

Code: `jevdual/python/jevdual/capability/backend.py::ScopedBackend.dispatch`; `jevdual/python/jevdual/native.py::AppendPrecondition`, `NativeBridge._append`; `jevdual/python/jevdual/ax.py::insert_at_end`. Coverage: `jevdual/tests/test_session_scenarios.py::test_capability_exact_preconditions_survive_native_dispatch`.

### 2. Original field geometry lost during live dispatch — P1, closed

Trigger: move the field from `(10, 20, 400, 300)` to `(110, 20, 400, 300)` after validation. `_live` retained a matching role/label/section and the append adopted the new geometry, sending and confirming input.

Resolution: the strict precondition retains the original AX role and frame. `_append` checks fresh projection geometry and the resolved AX element frame, then rechecks frame and insertion permission after the resource guard. The independently rerun moved-frame case returned `not_sent` with no AX setters. Lost insertion permission was checked alongside this contract and also refused without writes.

Code: `jevdual/python/jevdual/native.py::NativeBridge._append`; `jevdual/python/jevdual/capability/backend.py::ScopedBackend.dispatch`. Coverage: `jevdual/tests/test_session_scenarios.py::test_capability_exact_preconditions_survive_native_dispatch`.

### 3. Superseded field value remained usable as current evidence — P1, closed

Trigger: type Quantity `27`, then replace it with `28`. Both `field_holds` effects remained usable, `evidence_values` contained both values, and the deterministic floor did not reject the older value. This affects the opt-in `FOOTWORK_COMPLETION=effect_evidence` path.

Resolution: completion freshness follows receipt order. Potentially delivered later input on the same or unknown source limits earlier current-state evidence; a later qualified readback can establish its own new value. Explicit non-delivery and known other-source scope remain distinguishable.

Code: `jevdual/python/jevdual/completion.py::_possible_edit`, `effects`; actual callers in `jevdual/python/jevdual/session.py::cmd_done` and `jevdual/python/jevdual/verify.py::Verifier.verify`. Coverage includes persisted-session effects reaching the real verifier floor and claim check in `jevdual/tests/test_completion.py`.

### 4. Receipt parsing corrupted literal Unicode — P2, closed

Trigger: the actual repr-style field receipt for `café` was decoded through UTF-8 bytes and `unicode_escape`, producing `cafÃ©` as usable evidence.

Resolution: a bounded canonical quoted-string parser uses `ast.literal_eval`, checks the result is a string, and requires a canonical `repr` round trip. It preserves Unicode, apostrophes, quotation marks, backslashes, and intentional whitespace while rejecting malformed or nonliteral receipt text.

Code: `jevdual/python/jevdual/completion.py::_literal`, `_HOLDS`, `effects`. Coverage: actual `_field_receipt` producer round trips and malformed-literal cases in `jevdual/tests/test_completion.py`.

### 5. Query navigation acquired unsupported submission authority — P1, closed

Trigger: a confirmed click on View report navigated to `/report?quantity=27`. The parser emitted a usable `submitted` event, and the floor for Submit one cutting request returned no blocking reason despite lacking submission identity or acknowledgement.

Resolution: query navigation emits no submission event and contributes no submitted values. The current receipt producer has no qualified submission acknowledgement. `repeat_of` separately retains a conservative observed-query-navigation repeat-risk guard, without converting that observation into execution evidence. Known absolute origins are retained in that guard.

Code: `jevdual/python/jevdual/completion.py::effects`, `repeat_of`, `floor`. Coverage: View report and submit-label navigation both remain insufficient submission evidence in `jevdual/tests/test_completion.py`.

### 6. Simultaneously changed label and ID escaped freshness invalidation — P1, closed

Trigger: the same source changed from Old dynamic label/id 1/value `27` to New dynamic label/id 2/value `28`. The first remediation treated different labels and IDs as proof of distinct fields, leaving both values usable. These are presentation identities that can both remap across observations.

Resolution: `_possible_edit` no longer uses differing presentation labels or IDs to preserve old evidence. Without a qualified stable field incarnation, potentially delivered same-source input conservatively overlaps prior field evidence.

Code: `jevdual/python/jevdual/completion.py::_possible_edit`, `_same_surface`, `effects`. Coverage: remapped labels/IDs and conservative same-source input cases in `jevdual/tests/test_completion.py`.

### 7. Saved current state survived later edits with equal/regressed time or paste — P1, closed

Trigger: a saved receipt at time 1 followed by a later field edit with timestamp 1 or 0.5 remained usable because save freshness compared wall-clock timestamps. A later potentially delivered paste chord was also missed. The save floor accepted these stale saved-state records.

Resolution: saved evidence uses receipt order and the same conservative possible-edit classification as field evidence. Later possible edits limit the saved record regardless of wall-clock ordering or route spelling. Historical observation remains recorded; it does not establish the current saved state.

Code: `jevdual/python/jevdual/completion.py::effects`, `_possible_edit`. Coverage: equal/regressed timestamp, save sequence, and paste cases in `jevdual/tests/test_completion.py`.

### 8. Editing hotkeys and menus retained earlier current-state authority — P1, closed

Trigger: `hotkey(cmd+x)` or `menu(Edit > Cut)` with a potentially delivered, unverifiable receipt left an earlier `field_holds` or `saved` record usable. Route-name coverage limited to paste did not cover the actual editing surfaces. A reset click or unclassified input can likewise change current content.

Resolution: every potentially delivered same/unknown-source input conservatively invalidates earlier current-state evidence. Only actual read-only operation names, explicit non-delivery, `dispatched=False`, or a known other-source scope exclude overlap. Independently rerun cmd+x and menu-cut cases limited both field and saved evidence and supplied no old value to `evidence_values`.

Code: `jevdual/python/jevdual/completion.py::_READ_ONLY`, `_possible_edit`. Coverage: cut, menu, reset click, unclassified input, and saved-state sequence cases in `jevdual/tests/test_completion.py`.

### 9. Document/resource identity could change during the awaited live observation — P1, closed

Trigger: replace AXDocument during `NativeBridge._live`'s awaited observation while preserving field role, frame, and content. The backend's document check had already completed; the strict field guard still sent and confirmed input into the replacement document. This was reproduced over the actual backend/native/AX code with the simulated boundary.

Resolution: `AppendPrecondition` carries the expected document and a trusted read-only resource check. Durable preparation retains the original recovery identity in private `Validated.context`; the fixed worker attaches the admitted packet identity after validation. The callback requires strict native identity equality before input. `_append` then checks canonical AXDocument and repeats frame/permission checks; insertion retains its literal value guard. The independently rerun document-replacement case returned `not_sent` with no AX setters. The scenario suite also covers same-path inode and process-start replacement during live observation.

Code: `jevdual/python/jevdual/capability/backend.py::ScopedBackend.prepare_recovery`, `ScopedBackend.dispatch`; `jevdual/python/jevdual/capability/execution_worker.py::run`; `jevdual/python/jevdual/native.py::AppendPrecondition`, `NativeBridge._append`. Coverage: `jevdual/tests/test_session_scenarios.py::test_capability_resource_replacement_during_live_observation_sends_nothing`.

The post-input safe-save policy remains separate: historical qualified execution can survive an NSDocument inode replacement, while current agreement and disk persistence remain distinct facts. This correction does not claim an atomic transaction shared by AX and SQLite.

## Verification performed

- Initial targeted checks: 323 tests passed across capability, native scenarios, completion, authorization parity, and advisory provider modules.
- Final remediation checks: **309 tests passed in 3.98 seconds**, using installed dependencies and `uv run --no-sync pytest -q` over `test_capability_backend.py`, `test_session_scenarios.py`, `test_capability_recovery.py`, `test_capability_service.py`, `test_native.py`, `test_completion.py`, `test_verify.py`, and `test_session_evidence.py`.
- Independent small reproducers exercised pure completion functions and the actual scoped backend/native/AX insertion code over the installed `TextWorld` boundary. They created no native windows or document files.
- The new `append_precondition` keyword initially broke two backend test doubles. Their `**kwargs` compatibility correction was included in the final passing checks.
- Retained execution receipts, write-ahead admission, unknown blocking, no status replay, and historical/current separation were inspected through production code and focused tests. The prior recorded native qualification was not independently rerun by this reviewer.

## Final checked content hashes

SHA-256 values bind the inspected remediation snapshot, rather than an inferred final HEAD:

| Path | SHA-256 |
| --- | --- |
| `jevdual/python/jevdual/capability/backend.py` | `4ef489e5e28ac378043efbd081a537eba519b2fe6d4b5c29ae61fcdc9d744c0a` |
| `jevdual/python/jevdual/capability/execution_worker.py` | `0c0d00e3858d336bd14e588e9a22fd5ec0ec4fb959ba5942cb6adf10489fbb73` |
| `jevdual/python/jevdual/native.py` | `d89afbedcf592ef8fe0e699d11c273c4c45df4a2c9039922c77e5907ffd33bfd` |
| `jevdual/python/jevdual/completion.py` | `f1a83212e279acba7c2e8cd9bbac981797c17035467a1a7f16e88c1f36921d0e` |
| `jevdual/tests/test_capability_backend.py` | `ada3dbf5b6fa151f021105e3113fb9dba31cde383f58e13418b3ad5e7ee3c3be` |
| `jevdual/tests/test_completion.py` | `e525d967af96a64d7c0958ad700579db69f265306cae5de38e164f4e84c3f3b8` |
| `jevdual/tests/test_session_scenarios.py` | `d5fbcaa707e9022a5a6ecee2cff071ca4e50dd47efe15c224178b25437136b7e` |

## Limits and independence

The reviewer was independent of implementation ownership, but used an inherited model/context. This is a single coordinated reviewer context, **not model diversity**. Remediation was reassessed in that same context; no fresh reviewer or paid exact-head review was invoked.

Large frozen research-data artifacts were sampled through relevant summaries, provenance, and test contracts; the reviewer did not reread every experimental JSON record or independently recreate research results. The deep production-boundary inspection does not constitute exhaustive data validation.

The native execution contract is qualified for the bounded macOS route and the tested simulated/native evidence surfaces. This review provides no additional qualification for arbitrary apps or platforms, power loss, an OS-call-interior interruption, a shared AX/SQLite transaction, disk persistence, hostile-owner tampering, or general parallel-host execution. Linux/packaging, Node/Rust, browser, current-freeze live checks, and CI evidence remain separately owned and reported by root.
