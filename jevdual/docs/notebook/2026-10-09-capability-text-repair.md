# Capability text interface repair

Tom explicitly authorized both fixes and reference-repository investigation. C1 stays frozen and its original results unchanged. This is a bounded repair and developmental qualification, not a rerun/adoption of C1 or a heldout split.

## TR1 · prediction · 2026-10-09 19:52
Hypothesis: the double-newline failures arise from a hidden automatic separator contract, not inaccurate AX text; an explicit per-target append_separator plus tool/argument descriptions lets an external caller supply just new content while preserving intentionally supplied whitespace literally.
Test: real capability-tool scenarios against the simulated native surface for no-newline, newline-ended, empty and whitespace prefixes, including a deliberately leading-newline payload. Before product edits, require a no-newline scenario to expose missing separator metadata; afterward check metadata against exact final content and preservation through the NativeBridge route. Fresh isolated host sessions use the existing task wording without repair-specific prompting.
Predicts: prefix without terminal newline advertises one automatic separator; newline-ended and proven empty prefixes advertise none; user payload is never stripped or normalized, including deliberate leading/trailing whitespace. Fresh host no-newline tasks produce one separator and report supported content completion.
Against: metadata disagrees with the actual insertion, the caller adds another separator despite the explicit contract, or a legitimate leading newline is silently removed.
Refs: results/capability-comparison-20261009/comparison/report.md; python/jevdual/capability/contracts.py; python/jevdual/capability/observations.py; python/jevdual/native.py:_append

## TR2 · prediction · 2026-10-09 19:52
Hypothesis: snapshot.values membership wrongly suppresses empty native targets, and a legitimate empty-to-nonempty edit changes Cua's derived text-area label; exact independent AX value/insertability qualification and structural scoped-field readback can make empty appends available and verifiable without weakening unreadable, stale or ambiguous-field refusals.
Test: commit real public capability-tool scenarios before product edits. Use a native driver world that omits empty preview values but whose exact AX read proves zero characters. Counterexamples include missing AXValue without zero-character proof, read-only setters, changed document/content, secure fields and multiple matching fields. Drive NativeBridge append and capability journal/readback, not a fake append implementation. Qualify the real empty TextEdit field afterward.
Predicts: the original empty scenario has no offered target; the repair offers one only after independent readable/insertable proof and ends with exact content/applied field evidence despite presentation-label change. Unreadable/noninsertable/secure/ambiguous fields offer no action; stale content/document identity sends nothing.
Against: a missing value is assumed empty, a readonly/secure or ambiguous field becomes writable, an external edit is erased, or legitimate label change leaves a correctly delivered empty append unknown.
Refs: python/jevdual/capability/backend.py; python/jevdual/ax.py:value; tests/fixtures/native_world.py; tests/test_session_scenarios.py; results/capability-comparison-20261009

## TR3 · prediction · 2026-10-09 19:52
Hypothesis: the fixes remain intuitive through the actual four-tool MCP interface rather than only in simulated scenarios.
Test: after committed source and required offline checks, fresh canonical Opus5.5/high sessions on owned browser/TextEdit fixtures with fixed newline-ended, no-newline, empty, whitespace and deliberate-leading-newline cases. Use strict MCP inventory, no built-in tools, unchanged task semantics, independent exact AX reset/readback, and truthful persistence limits. Read-only independent Opus review is optional if evidence benefits; original mailbox collaboration remains authorized. Requested CLI caps are soft; schedule at most six host sessions and one bounded review, reserve $8 aggregate for this repair, count actual reported costs and stop on missing costs/invalid environment. No install, permission change or measured C1 retry.
Predicts: every fixed development case reaches supported exact nonduplicated completion with four offered tools; empty field gets an offered target and verified applied journal, and no-newline case has one separator.
Against: any required case fails content/claim qualification, any out-of-arm tool is offered/used, a fixture cannot be independently reset/read, or unexplained transport/ownership failure occurs.
Refs: scripts/capability_host_trial.py; scripts/capability_comparison_trial.py; scripts/capability_fixture.py

## TR1-U1 · update · 2026-10-09 20:00
Resolves: TR1 = held
Observed: on prediction commit 22c58bc, the real capability-tool scenarios failed on missing automatic-separator metadata for three payload cases. The repaired observations expose append_separator computed from exact field content, and tool/argument descriptions explain its automatic insertion while preserving literal payload. The focused post-fix suite passed 61 tests in 1.75 seconds, including intentionally leading/trailing whitespace and existing CLI paths. No legacy NativeBridge append rule changed.
Inferred: the caller-visible contract now agrees with the actual insertion route in these offline scenarios. Fresh host interpretation is still tested under TR3.
Next: full required checks, committed source and actual host qualification.
Refs: output/capability-text-repair-before.log; output/capability-text-repair-focused-final.log; tests/test_session_scenarios.py

## TR2-U1 · update · 2026-10-09 20:00
Resolves: TR2 = held
Observed: baseline public scenarios also failed to offer a proven empty target, incorrectly offered a noninsertable target, and raised on ambiguous exact resolution. The repair independently reads exact AX value and qualifies both caret/insertion setters before offering a target and again during validation. Known unreadable/noninsertable/ambiguous fields expose no target and an unavailable reason. Secure fields remain non-appendable. Sixteen new real-core scenarios cover empty-to-nonempty label changes, readonly and unreadable values, stale document/content, setter loss, post-send role/frame/ambiguity changes, status/reconcile, and no replay. The focused full subset passed 61 tests.
Inferred: Cua presentation labels cannot serve as post-insertion field identity. Scoped document, AX role and unique original frame allow legitimate content-derived label changes while retaining tested identity-loss refusals. This is not durable incarnation reconciliation.
Next: full checks and a real empty TextEdit append through the four-tool external host.
Refs: output/capability-text-repair-before.log; output/capability-text-repair-focused-final.log; python/jevdual/ax.py:can_insert; tests/fixtures/native_world.py; tests/test_session_scenarios.py

## TR-R1 · update · 2026-10-09 20:05
Observed: full suite on 50948c6 passed 1214 tests with 26 skipped in 93.81 seconds; lint passed. A model-free real empty TextEdit probe offered one target, appended once with an applied receipt and passed independent exact AX readback. Independent tool-less Opus5.5/high diff review completed successfully ($0.324859 reported), found no concrete blockers for scoped live checks and suggested adjacent frameless/setter-error/prompt/prerequisite coverage. It incorrectly generalized label change to every append; only empty/placeholder-derived labels require this new handling in the observed native parser. Original mailbox peer has not replied.
Changes: before any fresh paid host qualification, require observed field geometry for insertion targets, add setter-error/frameless and whitespace-only-without-terminal-newline scenarios, use an unconditional prompt-drift guard and preserve pre-host fixture errors in the qualification summary. The six-case development manifest's whitespace-only prefix is now two spaces plus tab, without a terminal newline. No original C1 changes or heldout runs.
Next: final checks and a new committed host-qualification version; use actual review cost as the prior-cost reservation.
Refs: output/capability-text-repair-full-suite.log; output/capability-text-repair-model-free-20261009/receipt.json; output/capability-text-repair-opus-review-20261009/transcript.jsonl; scripts/capability_text_qualification.py; 50948c6
