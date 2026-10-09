# Capability slice: next work after C1

C1 requires diagnosing the interface before expanding the slice. Its fully qualified clean guardrail failed (Footwork 6/12, raw 9/12); the interrupted comparison is inconclusive after three untreated empty-field sessions. Stale preservation favored Footwork 6/6 versus raw 0/6. Evidence: results/capability-comparison-20261009/comparison/report.md, frozen c7c418c.

## 1. Make text semantics explicit

The current act schema says append text but NativeBridge._append inserts a newline when the existing field is nonempty and lacks one. Expose that exact separator policy in the offered move and tool contract so agents know whether to pass a line or literal insertion. Do not silently strip payloads, remove user newlines, or change the legacy native append behavior to rescue the benchmark.

Before changes, commit a notebook prediction. Reproduce the caller/backend double-separator behavior in a scenario that drives the real capability commands against the simulated native surface. State the intended contract explicitly. Qualify fresh host tasks with empty, newline-ended, no-newline and whitespace-preserving prefixes. Include a payload that deliberately begins with a newline, so the chosen contract cannot silently discard intended characters. Keep the original C1 results unchanged.

## 2. Offer targets only after exact empty-field qualification

ScopedBackend.observe currently checks candidate.id in snapshot.values before invoking its exact AX read. The raw preview omits an empty field, so that gate prevents the existing ax.value AXNumberOfCharacters check from running.

Read exact AX content for a scoped, writable candidate even when its preview value is absent. Offer a target when that read establishes a value (including proven empty). Missing AXValue without zero-character proof, an ambiguous element, changed document identity or a secure/nonwritable field must remain refused or explicitly unavailable. Preserve no-send preconditions and exact field readback. Add scenarios for proven empty versus unreadable, stale and ambiguous fields; then qualify an actual empty TextEdit append through the external host.

## 3. Qualify recovery records separately from host success

In C1, fresh readback let both agents recover without duplicate appends, while Footwork's operation records remained unknown. A durable attempt record needs sufficient original resource/incarnation/precondition/effect information for qualified read-only reconciliation after restart. Matching current text alone does not prove execution custody or causality.

Write a separate experiment before implementing this. Test actual SIGKILL before send, during dispatch and after final commit, with delayed delivery and resource/document replacement as counterexamples. Never promote unknown to applied without deterministic identity/effect evidence, and never redispatch to improve a receipt. Do not use C1's host readback success to claim durable reconciliation works.

## 4. Measure installation and first-use experience

The comparison used generated configs and an already-permitted Mac. It does not establish minimal configuration. After the two text fixes, qualify a fresh agent host with one MCP registration and no fixture-specific prompting. A doctor command should report actual driver availability, required permissions, scope and supported operations. Source and destination binding should produce opaque handles without making callers understand native PID/window and browser protocol differences.

Keep planning/model choice in the caller. Maintain a small deterministic execution layer with adapters, explicit capability/effect semantics and truthful receipts. Add an SDK/CLI path alongside MCP only when the same contract is qualified. MIT applies to Footwork's own code; retain required notices for Apache/other dependencies and avoid copying reference code without its license obligations.

## Delivery order and boundaries

Fix and qualify text semantics and empty-field targeting first. Then measure first-use setup and independently qualify durable reconciliation before widening actions/apps/platforms. Carry exact observations and stale preconditions forward: those provided the clearest live benefit here. Browser/computer adapters should share lifecycle and evidence contracts while expressing unsupported capabilities explicitly.

C1 does not select a new architecture or justify a larger planner/refactor. A new comparison needs a new frozen version, committed predictions/preregistration, the original exclusions visible, and fresh development qualification. No implementation, provider call, public release or global configuration change is performed by this plan.
