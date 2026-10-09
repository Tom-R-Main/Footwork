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
