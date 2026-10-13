# SIM14: reusable body contract and interrupted host recovery

## Hypothesis

The workbench can repair a journal event published before its manifest index without replaying an effect. Durable planner ownership and a restart fence can retire a planner left by host SIGKILL before admitting fresh planning. A reusable body envelope contract can be separated from bench operations while preserving existing wire validation and recovery guards.

## Predictions

If true, an owned event-publication SIGKILL restarts paused with a contiguous validated journal, preserves command identity and native evidence, and resumes using a fresh observation. An active-planning SIGKILL retains the unfinished job, prevents its old result from dispatching, retires its recorded process ownership, and requires explicit Resume. Known uncertain commands recover by their exact receipt with one send; incomplete lower evidence remains blocked. A second minimal operation contract validates through the shared envelope seam without importing simulation modules, while invalid bench commands remain refused.

If false, journal files collide or disappear, partial data grants action authority, an abandoned planner survives with writable call ownership, an old decision becomes dispatchable, a command is replayed, or extraction changes body identity/lease/receipt semantics.

## Design

Use fresh run-owned roots under tools/physical-workcell/output. Preserve the previous product roots. Reproduce the event/index gap before changing its regression expectation. Exercise an actual child planner at a deterministic barrier with external host SIGKILL; cover malformed ownership, process identity mismatch, and incomplete journal tails without killing unrelated processes. Run focused existing body/client/operator/process suites, plus new negative contract checks. Freeze committed source before actual Codex trials. Drive publication and active-planning recovery in the browser and retain UI, journal, command-send and process ownership evidence. Recheck an uncertain receipt case and the native-receipt-gap refusal on the changed implementation. Diagnostic controls must not bypass effect admission.

## Primary metric

Zero repeated effect dispatches and zero stale planner admissions across the selected interruption/recovery trials, with every original uncertain command retained and reconciled or blocked.

## Guardrails

No pose-based success inference, silent resubmission, automatic Resume, weakened source pinning, unrelated process termination, or mutation of previous trial roots. Retain failed trials. Loopback simulation and process SIGKILL only; no claim of physical safety, power-loss durability, remote authentication or arbitrary-instruction crash completeness.

## Decision rule

Adopt only if focused regression and malformed-evidence checks pass and both new browser recovery cases preserve their original history without replay. Report any unsupported boundary explicitly. Separate contract reuse qualification from hardware support.

## Amendment before final-source qualification · 2026-10-12 22:45

The first publication run qualified its frozen source, and a planning run remains unqualified after a UI/readback timing race. The actual planning process tree included Codex shell-snapshot descendants outside the main planner group. Final qualification disables that startup feature and accounts for every recorded child identity and group before fresh planning. Existing single-send, exact-receipt, independent image and native measurement/reset criteria remain unchanged. The interrupted call and earlier attempts remain separately reported.
