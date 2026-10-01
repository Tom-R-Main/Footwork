# Inspection v2: cold entry, workflow proof, findings, publication

## XZ91 · prediction · 2026-10-01 16:34
Question: can a fresh disposable page's first navigation be captured without loosening the existing recorder's same-origin disk fence?
Hypothesis: an in-memory CDP bridge can attach to `about:blank`, enable Network before navigation, then release a sanitized cold-entry artifact only after the final page and main-frame document request match the declared HTTPS origin. A rejected redirect or ring truncation must leave no cold-entry artifact.
Alternatives: Playwright's page CDP session cannot observe the first document request, the main frame cannot be identified reliably, or third-party subframes make the origin check ambiguous.
Test: implement a separate pre-navigation bridge mode and artifact writer in the fork-owned transport module; test allowed/rejected navigation and redaction with synthetic CDP events, then run one isolated public browser calibration. Record page-only worker/frame coverage counts explicitly.
Predicts: the packet contains one or more first-document request events with verified same-origin main frame, no raw URL values outside the existing sanitizer, and an explicit unsupported-target count/status.
Against: a wrong-origin main document is written, event truncation is silent, a fresh run lacks the first document request while marked complete, or worker traffic is claimed without attachment.
Refs: tools/inspection-transport/playwright-cdp-bridge.mjs; tools/browser-inspection/capture.mjs

## W1 · prediction · 2026-10-01 16:34
Question: can public page actions become reviewable workflow tests rather than successful-click summaries?
Hypothesis: a small workflow observer can require typed precondition, immediate state, settled state, and readback checkpoints around one recorder step, persist only bounded boolean/enum receipts, and mark missing checks unknown or failed rather than infer success.
Test: implement the generic observer with synthetic success/failure cases and use it for a safe public validation/navigation flow. Preserve the recorder's action interval and private snapshots.
Predicts: each exercised step has distinct precondition/action/immediate/settled/readback statuses; an absent readback never becomes persisted success.
Against: a failed checkpoint reports completed workflow, sensitive DOM text enters a shareable receipt, or one UI action is retried silently.
Refs: tools/inspection-experiments/live-public-smoke.mjs

## F1 · prediction · 2026-10-01 16:34
Question: can the research note be audited claim by claim without exporting raw private capture?
Hypothesis: a deterministic private findings ledger with claim ID, evidence type, packet fingerprint, step interval, coverage limit, confidence, and falsifier can validate source links and reject unsupported `observed` claims. A Siftable note can cite its private IDs without pretending the local packet is remotely accessible.
Test: implement a generic ledger validator and report projection with synthetic valid/invalid cases; generate a private ledger for the next site run and reconcile the existing note's strongest claims.
Predicts: unsupported or unbounded claims fail validation, while documented/observed/inferred claims remain distinct.
Against: a claim can cite a nonexistent step or tampered packet, confidence replaces evidence, or private URLs/body values enter the shareable projection.
Refs: tools/inspection-experiments/coverage.mjs

## P1 · prediction · 2026-10-01 16:34
Question: can publication be blocked without putting target names into tracked source?
Hypothesis: a local Git publication check can read an ignored private denylist, scan the tracked tree plus commits in the proposed push range, and fail closed on a target name or missing base/config. It should not rewrite shared history or install a global hook.
Test: add a generic CLI and synthetic repository test with a private target token; run it against this branch using an ignored denylist. Report the existing leak boundary privately and make no push.
Predicts: tracked-file and commit-history hits both fail, a clean synthetic range passes, and report output uses generic paths/commit IDs without echoing the target token.
Against: history hits pass, the token appears in the gate's output, or a missing private policy is treated as success.
Refs: tools/inspection-experiments/README.md

## U200 · update · 2026-10-01 16:52
Observed: the pre-navigation bridge observed the first main-frame Document request before recorder startup. A wrong-origin document and truncated ring are rejected in unit tests. The local packet `output/inspection-public-smoke/local-cold-1790887858706/` sealed a sanitized cold-entry artifact with five allowed network events and zero excluded events. Worker and out-of-process-frame traffic are explicitly unattached. An earlier fixture attempt stalled with an empty journal; a stage-logged rerun completed in under a second.
Changes: the prediction ID was corrected from C1 to XZ91 because C1 and IC1 belonged to older packages; the committed prediction text is otherwise unchanged.
Next: run an isolated live calibration only after the reserved next site session, and check redirects, workers and frames on that site.
Refs: tools/inspection-transport/playwright-cdp-bridge.test.mjs; output/inspection-public-smoke/local-cold-1790887858706/

## U201 · update · 2026-10-01 16:52
Observed: the local fixture's save action had distinct precondition, immediate, settled and reload/readback checks, all passed; the reload was its own recorded step. The sealed packet has five recorded network events, one request hop, zero reported gaps and a bounded `workflow-checkpoints.json`. Unit tests show a failed precondition skips the action and an absent readback cannot verify a workflow.
Inferred: the observer can represent a local persistence check but cannot establish causality from coincident traffic.
Next: apply the observer to a safe live workflow during the reserved site session.
Refs: tools/inspection-experiments/workflow-observer.test.mjs; output/inspection-public-smoke/local-cold-1790887858706/

## U202 · update · 2026-10-01 16:52
Observed: the ledger validator distinguishes observed, documented and inferred claims. An observed claim must cite a hash-verified packet, exact step cursors and an actual event sequence in the interval. Unit tests reject a forged packet and absent event, while the shareable projection omits claim prose, citations and falsifier text.
Inferred: this validates evidence references, not whether a sentence correctly describes the event.
Next: create a private ledger for the reserved site run and reconcile its strongest claims against the sealed packet.
Refs: tools/inspection-experiments/findings-ledger.test.mjs

## U203 · update · 2026-10-01 16:52
Resolves: P1 = held
Observed: synthetic Git repositories demonstrate that current tracked hits and deleted historical content both block, while a clean proposed range passes; output does not echo the private search term. The local scan against the current branch and its remote-main base found 13 tracked-file hits and 30 commits with hits across 189 proposed commits.
Next: coordinate removal of older named material before any push; do not rewrite shared history unilaterally.
Refs: tools/inspection-experiments/publication-gate.test.mjs; private local policy under output/

## U204 · update · 2026-10-01 16:53
Observed: `validateSealedFindings` accepted one local fixture claim after verifying manifest hashes, the readback step's exact cursor interval and a real Document request event inside it. The referenced packet reports zero capture gaps, but the event only establishes that a request occurred during the interval.
Next: apply the same ledger to the reserved site run, with every backend hypothesis labeled observed, documented or inferred and a disproof test.
Refs: output/inspection-public-smoke/local-cold-1790887858706/; tools/inspection-experiments/findings-ledger.mjs

## U205 · update · 2026-10-01 17:05
Resolves: XZ91 = inconclusive
Observed: the isolated local HTTPS fixture captured its first document request before navigation. The supported Chrome browser capability, however, requires a fresh tab to navigate before its first CDP command, so the real authenticated run began with a warm reload. Its polling paused on three transient origin-check failures; two event-buffer truncations and one unavailable body made the broad packet limited. A second bounded-step packet sealed with 154 events and zero reported gaps. Neither run attached worker or out-of-process-frame targets.
Inferred: the bridge's cold-entry mechanism is viable in disposable Playwright, but this Chrome connection cannot yet demonstrate true cold entry. A transient origin-check failure needs a safe recovery path that verifies the origin again before resuming writes.
Next: coordinate the original recorder owner before changing its polling behavior; add a browser-surface-specific cold-entry plan and worker/frame coverage proof.
Refs: output/inspection-private-site/db-evidence-20261001-1790888282863/; output/inspection-private-site/db-search-20261001-1790888525744/

## U206 · update · 2026-10-01 17:05
Resolves: F1 = held
Observed: five private claims passed the sealed-ledger validator against a real authenticated capture. Two cite exact recorded GraphQL request sequences inside distinct search-step cursor intervals; documented and inferred claims remain separate. The validator rejected a forged packet and nonexistent event in synthetic tests. The shareable projection omits claim prose and source URLs.
Inferred: the ledger makes provenance reviewable but cannot judge whether the prose correctly interprets a request or proves hidden server architecture.
Next: extend the ledger to support verified UI-checkpoint artifact references, then compare findings across independent runs.
Refs: output/inspection-private-site/db-search-20261001-1790888525744/; tools/inspection-experiments/findings-ledger.test.mjs

## S220 · summary · 2026-10-01 17:05
Established: the generic cold-entry bridge, workflow observer, findings ledger and publication gate have focused tests; the local fixture verifies recorded reload/readback, and the private live search packet hash-verifies without reported gaps. The current publication range is blocked by tracked and historical named material.
Uncertain: first navigation in the user's Chrome, transient-origin polling recovery, worker/OOPIF traffic and semantic interpretation of server-side storage remain outside this package's proof.
Decision: hand the browser lane and private run packets back to the original audit; keep publishing blocked; preserve open workflow and cold-entry questions for a scoped next iteration.
Refs: tools/inspection-experiments/README.md; output/inspection-private-site/db-search-20261001-1790888525744/

## PS1 · prediction · 2026-10-01 17:07
Question: can polling resume after a transient origin-check failure without weakening the recorder's origin fence?
Hypothesis: an external supervisor can inspect only the recorder's safe status and a fresh tab URL, and call its existing `startPolling` only when the exact HTTPS origin is restored. It must never touch buffered events itself or resume after a foreign origin, explicit stop or sealed run.
Alternatives: a paused recorder cannot restart reliably, or the supervisor can race an active drain and duplicate events.
Test: implement a fork-owned supervisor around the existing capture public methods and test transient URL failure, same-origin recovery, foreign-origin refusal, explicit stop and sealed-run refusal with a synthetic capture. Keep the existing recorder unchanged.
Predicts: a transient failure yields a bounded resume attempt and later polling with no unsanctioned event access; wrong-origin and stopped states never call `startPolling`.
Against: any recovery attempt occurs before origin verification, duplicate starts occur, or supervisor output contains a URL value.
Refs: tools/browser-inspection/capture.mjs; output/inspection-private-site/db-evidence-20261001-1790888282863/

## U207 · update · 2026-10-01 17:12
Resolves: PS1 = held
Observed: five state/race tests and one actual-recorder fixture passed. The recorder paused on a synthetic transient origin failure, the supervisor verified the recovered exact HTTPS origin, and the recorder's own `startPolling` fence resumed polling. The sealed fixture logged two polling starts. A never-started recorder, foreign origin, other pause reason, stopped run, and stop during an in-flight URL check did not resume. Supervisor status contains counters rather than URL values.
Inferred: this resolves the local recovery mechanism but does not establish lossless capture during a pause or prove recovery in an authenticated browser session.
Next: have the original browser owner integrate and calibrate this optional supervisor within a bounded run; retain gap accounting and compare pre/post-pause event continuity.
Refs: tools/inspection-transport/polling-supervisor.test.mjs; tools/browser-inspection/capture.mjs

## S221 · summary · 2026-10-01 17:12
Established: the optional, origin-fenced polling supervisor recovers a paused recorder through its existing public method in synthetic and actual-recorder fixture tests. It neither reads buffered events nor owns recorder shutdown.
Uncertain: live browser recovery, event loss during the outage, and worker/frame coverage are unverified.
Decision: hand this generic utility to the original audit owner for a bounded live calibration; keep the browser lane released and the publication gate closed.
Refs: tools/inspection-transport/polling-supervisor.mjs; tools/inspection-transport/README.md
