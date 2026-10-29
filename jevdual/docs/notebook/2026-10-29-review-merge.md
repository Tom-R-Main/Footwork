# October 28 operator review and PR integration

## RV1 · prediction · 2026-10-29 14:15
Hypothesis: integrating main's merged control-state/blocker and installer-diagnostic work with the October 28 native operator preserves both durable custody semantics and complete observed control state.
Test: inspect each merge overlap against both parents, run current key-free unit/CLI/package checks and targeted control-state plus admission/replay/evidence regressions. Bind final review/CI to the actual PR head; retain yesterday's installed evidence as historical proof rather than a claim about changed runtime.
Predicts: unresolved mutation still blocks new admission; original-token replay and qualified reconciliation send no input; repeated controls preserve observed state and strict identity. Current installed CLI/package and source-resource checks remain usable.
Against: integration drops either parent's state/coverage/authority fields, admits or retries uncertain input, falsely qualifies a receipt, or passes only by removing a meaningful assertion.
Refs: base 5d494c6a22921d092e67399badce708e8418bf2a; reviewed target a9b260180980e305ebc414568cf92ab02987f941; main 8de9c9ab797e0daafd8b897df61ec03006bde31f; results/move-submit-20261028/report.md

## RV2 · prediction · 2026-10-29 14:18
Hypothesis: A native fallback must require qualified structured no-send, and Finder rename must recheck owned window/selection immediately before its delayed menu leaf and editor write.
Test: Reproduce opaque/mixed delivered keyboard errors and a focus/selection switch during Rename enablement, then repair the narrow gates.
Predicts: Opaque or positively delivered failures send no second key; switched Finder ownership receives no Rename/write; documented structured no-send can still take its permitted fallback.
Against: A text-only error authorizes retry, or another window/editor receives input.
Refs: independent read-only reviews of a9b260180980e305ebc414568cf92ab02987f941; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md

## RV3 · prediction · 2026-10-29 14:18
Hypothesis: Durable public recovery and completion remain usable after interrupted JSONL projection and when the shared authority contains legacy unknown operations.
Test: Reproduce truncated projection followed by replay/new click/done, reused legacy-journal status, and a verifier accept while own/domain/context custody is unresolved. Keep authority decisions independent from corrupt display logs and provider votes.
Predicts: Status reports conservative legacy unknowns, repaired projection readers remain usable, and done refuses unresolved custody before provider/native work.
Against: Corrupt logs prevent canonical recovery, legacy state disappears or status crashes, or verifier acceptance closes unresolved custody.
Refs: independent read-only reviews of a9b260180980e305ebc414568cf92ab02987f941; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md

## RV4 · prediction · 2026-10-29 14:18
Hypothesis: Ticket qualification must bind a supported completed response boundary and its exact admitted service source into the Chrome handoff.
Test: Pause a handler after first ingress before pre-header disconnect and attempt reconciliation; challenge Chrome completion with another database/nonce. Add explicit producer response provenance and exact scope/oracle binding without diagnosing or suppressing transport duplication.
Predicts: Transient first ingress or unsupported disconnect never seals a success; supported completed response and matching admission may qualify; an unrelated ledger/nonce cannot advance Chrome.
Against: An early snapshot irreversibly qualifies a later-duplicating fault, or evidence from submission B completes submission A.
Refs: independent read-only reviews of a9b260180980e305ebc414568cf92ab02987f941; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md

## RV5 · prediction · 2026-10-29 14:26
Hypothesis: foreground handback must preserve the requested candidate ID in the returned NativeEffect; reusing its target variable for a restoration PID currently replaces that identity.
Test: run the foreground helper with an acknowledged action on candidate 4 and a handback to PID 77; assert both the activation and the original receipt target. Then use a distinct restoration variable and rerun native regressions.
Predicts: the red case returns target 77 before repair and target 4 afterward, while foreground restoration still activates PID 77.
Against: the original candidate target is already preserved, or separating handback metadata changes delivery/refusal behavior.
Refs: python/jevdual/native.py NativeBridge._foreground; RV2

## RVU1 · update · 2026-10-29 14:33
Observed: independent review findings reproduced before repair: eleven native cases, seven core recovery/completion cases, two context-log cases and three service/handoff cases failed. The integrated frozen a4646a5 suite passed 2238 tests, 26 skipped; package isolation, resource snapshot and 97 Node tests passed. Its first installed rename retained two acknowledged inputs then stopped before Rename because the owned File menu cleared AXFocusedWindow while front/main window and sole selection stayed exact; focused role was AXApplication. The partial operation remains unknown.
Inferred: focused-window absence in this proven owned menu transition is not evidence of a foreign key window. Keep strict initial focus and changed-window/selection refusals, and recognize only the narrow post-menu application-focus state before the Rename leaf.
Next: reproduce that actual state in the public scenario, correct the narrow guard, then fresh installed qualification.
Refs: output/review-merge-20261029/live-nominal/authority.json; output/review-merge-20261029/full-suite.txt

## RV6 · prediction · 2026-10-29 14:33
Hypothesis: a freshly validated bound main window and sole owned selection remain sufficient to target Rename when this operation's acknowledged File menu reports AXApplication focus and no focused-window ID.
Test: simulate null focused window only after owned File menu opening, with AXApplication focus. Confirm exact rename succeeds; null focus with another role or changed front/main/selection still refuses before Rename. Rerun the fresh installed workflow without repeating the uncertain fixture.
Predicts: the supported menu state passes without relaxing file URL/inode or initial key-window checks; foreign or unverified ownership receives no Rename/editor input.
Against: generic null focus becomes authority, a switched window/selection passes, or the live owned menu still blocks the route.

## RVU2 · update · 2026-10-29 14:37
Observed: a20205f's fresh live run passed the corrected owned File-menu check and entered its exact rename editor. Before the value write, the old filename field no longer had an AXRow ancestor (file_row_missing). Current front/main window and the exact focused editor still matched; no value was written. The partial operation remains unknown.
Inferred: the editor replaces its filename row during this legitimate transition. Allow only that explicit old-row absence when current editor/name/window/geometry and original inode remain qualified; other selection failures must remain refusals.
Next: a public transient-row regression, exact original-file check immediately before editor write, and fresh installed verification.
Refs: output/review-merge-20261029/live-nominal-final/authority.json

## RV7 · prediction · 2026-10-29 14:37
Hypothesis: qualified current editor ownership plus a fresh original-file inode check safely handles file_row_missing after this operation entered Rename, without weakening selection checks before Rename.
Test: simulate row replacement only while its exact editor is active; require successful rename. A different selection failure, wrong editor/window/value or replaced original inode must stop before the value write.
Predicts: the specific old-row replacement passes only with all remaining identity checks; arbitrary selection/read failures and foreign state receive no editor write.
Against: missing row alone authorizes input, a replaced inode or editor passes, or the real transient-editor route still blocks.

## RVU3 · update · 2026-10-29 14:50
Resolves: RV1 = held
Observed: Main integration retained control-state, blocker and installer behavior. Final suite: 2245 passed, 26 skipped; 97 Node tests, isolated offline package, installed discovery and 103-file resource snapshot passed.
Next: retain the bounded support claim and follow the exact PR head through hosted checks and merge.
Refs: results/review-merge-20261029/report.md

## RVU4 · update · 2026-10-29 14:50
Resolves: RV2 = held
Observed: Opaque/mixed key and delayed Finder ownership red cases passed after qualified no-send and current-target repairs. Final installed Finder rename/move passed twice.
Next: retain the bounded support claim and follow the exact PR head through hosted checks and merge.
Refs: results/review-merge-20261029/report.md

## RVU5 · update · 2026-10-29 14:50
Resolves: RV3 = held
Observed: Own/context log corruption, legacy blockers beyond the display limit and unresolved completion cases passed after repair; quarantines preserve original bytes.
Next: retain the bounded support claim and follow the exact PR head through hosted checks and merge.
Refs: results/review-merge-20261029/report.md

## RVU6 · update · 2026-10-29 14:50
Resolves: RV4 = held
Observed: The early-ingress and unrelated ledger/nonce red cases now refuse. V2 response provenance and exact source binding passed both final installed chains; v1 final reads remain supported but v1 unknown cannot newly finalize.
Next: retain the bounded support claim and follow the exact PR head through hosted checks and merge.
Refs: results/review-merge-20261029/report.md

## RVU7 · update · 2026-10-29 14:50
Resolves: RV5 = held
Observed: Foreground handback returned PID 77 as the effect target before repair, then preserved candidate 4 while still restoring PID 77 afterward.
Next: retain the bounded support claim and follow the exact PR head through hosted checks and merge.
Refs: results/review-merge-20261029/report.md

## RVU8 · update · 2026-10-29 14:50
Resolves: RV6 = held
Observed: The owned File-menu/null-window case failed before correction and passed the narrow stage-specific predicate in public and final installed runs.
Next: retain the bounded support claim and follow the exact PR head through hosted checks and merge.
Refs: results/review-merge-20261029/report.md

## RVU9 · update · 2026-10-29 14:50
Resolves: RV7 = held
Observed: The transient-row case failed before correction; exact editor plus original-inode checks now pass it and reject arbitrary read failures/replaced inode before write. Both final installed chains passed.
Next: retain the bounded support claim and follow the exact PR head through hosted checks and merge.
Refs: results/review-merge-20261029/report.md

## RVS · summary · 2026-10-29 14:50
Established: full October 28 operator review, eight repaired findings, preserved main integration, source ddf133f, full local checks and fresh v2 nominal/interrupted-truncated installed chains. Both conservative live guard regressions are retained and corrected by public scenarios.
Uncertain: pre-header duplicate-ingress cause and full-portfolio qualification remain open; hosted CI and merge have not yet been observed. AX helpers can classify a read failure as file_row_missing, so no authority depends on that label alone.
Decision: publish the review and PR with explicit limits, follow CI/reviews through the authorized merge, and keep duplication diagnosis separate. Cleanup preserved eleven historical and two new uncertain operations.
Refs: results/review-merge-20261029/report.md; results/review-merge-20261029/cleanup.json

## RV8 · prediction · 2026-10-29 15:12
Hypothesis: prefix comparison of a fresh raw field value incorrectly preserves an earlier exact completion fact after clearing or shortening; the display preview is not current exact-value authority.
Test: reproduce empty, shortened-prefix, whitespace-only difference and absent-raw-value cases through structured receipts and completion effects. Preserve a long full raw value with a shortened display preview as usable. Require full raw equality before leaving the earlier fact unlimited.
Predicts: the changed-value and missing-raw regressions fail before repair and pass afterward; complete matching raw values still qualify independently of display truncation.
Against: shortened or unavailable raw values remain usable, or display truncation alone invalidates matching complete raw values.
Refs: PR 9 review comment 4416606138; tests/test_session.py
