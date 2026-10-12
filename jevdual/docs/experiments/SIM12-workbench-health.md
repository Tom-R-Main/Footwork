# SIM12: Healthy work must survive a delayed health read

Hypothesis: the workbench interprets a health-read deadline as confirmed body loss too early, cancelling otherwise healthy image-guided jobs. A bounded probe that distinguishes delayed observation from confirmed unsafe state can preserve progress without granting authority from old health evidence.

Predictions if true: a live, unchanged body with a delayed health reply reproduces the original pause; a mechanism-level repair avoids that pause while preserving command admission checks. Identity/source changes, boot changes, unresolved effects, explicit disconnect, Pause and genuinely unavailable transport still suppress successor actions. An uncertain dispatch remains single-send until exact historical receipt recovery and explicit Resume.

Predictions if false: the failure is caused by an actual body outage, already-closed ownership, a stale overlapping probe or an invalid body state; the repair hides loss, delays invalidation of known unsafe identity/epoch, grants admission on stale health, retries an effect or silently resumes a paused or uncertain job.

Design: retain the previous paused product and SIM11 evidence. Inspect historical event timing and source independently for health-decision, transport/locking and probe-cost explanations. Record direct-body versus link probe timings and narrowly scoped instrumentation if needed. Commit a concrete causal prediction before its reproduction and repair. Reproduce through real sockets, preserve original failing output, repair the smallest demonstrated mechanism and run affected outage/reboot/uncertainty/pause tests. Freeze measured source before actual Codex calls. Drive two successive jobs in the browser with deterministic delayed health replies using an owned diagnostic harness; include explicit loss and exact receipt recovery. Independently verify placement, measurement, contact reset, model images, command sends and complete process cleanup.

Primary metric: two independently verified actual-model jobs complete with zero unrequested pauses or cancelled decisions caused by the tested healthy health delay; injected health-delay intervals cannot admit commands without fresh pinned proof.

Secondary checks: real unavailable transport still blocks effects; fast reboot invalidates old decisions; stale probes cannot overwrite newer controls/results; unknown commands remain uniquely indexed; receipt recovery stays read-only and requires Resume; UI accurately distinguishes waiting for health proof from disconnected or uncertain work.

Guardrails: no retries of effect commands; no stale-image or stale-health authority; no relaxed identity/source/lease/freshness limits; no threshold increase to mask an unexplained delay; bounded owned probes and processes; no new remote exposure or hardware actuation; preserve failed attempts; commit predictions before substantive tests and freeze paid runs. Report uncertainty about the historical incident separately from a reproduced mechanism.

Decision rule: adopt only after the original healthy-delay reproduction passes without unrequested Pause, recovery guards pass and the frozen browser/model trial independently passes. Otherwise retain evidence and report the exact unresolved boundary.

Scope: same-Mac loopback simulation. The observed SIM11 health timeouts are historical evidence; their precise physical scheduling cause is not assumed.
