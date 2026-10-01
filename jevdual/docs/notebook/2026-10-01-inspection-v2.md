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
