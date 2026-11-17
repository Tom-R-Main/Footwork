# Qualified native fullscreen control

## FS1 · prediction · 2026-11-17 03:54
Hypothesis: the existing public CLI cannot offer the bound window's unlabeled fullscreen button because the SDK omits subrole and projection prunes unnamed buttons; a separately qualified exact-window identity can expose only this button without weakening menu ambiguity or unnamed exclusions.
Test: first reproduce with public start/look/do against the existing simulated Mac, retaining red output on SSD before source changes. Then qualify exact PID/window, full-screen button subrole/enabled/AXPress/state, persist identity across CLI calls, requalify immediately before dispatch, and read back the actual transition. Exercise wrong PID/window, missing/duplicate/disabled/replaced control, state changes, token/index reassignment, no-transition acknowledgements and other unnamed controls.
Predicts: public CLI reproduction fails before repair with no available fullscreen candidate; after repair only the uniquely qualified fullscreen button is offered, mutations refuse without input, and only an observed state transition confirms effect. Duplicate menu paths still refuse.
Against: reproduction already offers a safe target; a mutation dispatches; ordinary unnamed controls become clickable; or acknowledgement without transition is reported confirmed.
Refs: /Volumes/External SSD/demoApps/demo/films/showcase-2026-11-17/workspace/capture/window-prep-002/CONTROL-DIAGNOSIS.md; tests/test_session_scenarios.py; tests/fixtures/native_world.py

## FS2 · update · 2026-11-17 03:55
Observed: the real public start/look scenario fails at saved candidate981 missing (KeyError), while unnamed close/minimize are excluded; no source changed before this reproduction.
Next: implement qualified window identity and failure/readback discrimination.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/red.txt; tests/test_session_scenarios.py::test_native_fullscreen_public_cli_offers_only_qualified_window_control

## FS3 · prediction · 2026-11-17 03:55
Hypothesis: CoreFoundation CFHash of the same window/button AX references is stable across separate observer processes, allowing a bounded additional replacement discriminator alongside exact PID/window/subrole and current state. It is not treated as a globally unique identity or sufficient dispatch authority.
Test: two independent read-only AX queries of the already authorized exact Chrome PID82786/window635573, compare window/button hashes without input; fixture mutations test changed hashes and same-process AX reference equality immediately before dispatch.
Predicts: the two independent observations agree on hashes and state, and replaced references are refused at dispatch.
Against: hashes vary across observers of the unchanged control, or a replaced reference passes fresh qualification.

## FS4 · update · 2026-11-17 04:03
Observed: two independent read-only installed-runtime AX observers returned matching window/button hashes and fullscreen state. The focused fullscreen scenarios initially exposed a second defect: generic visual diff confirmed a changed button label even when exact fullscreen readback failed. The new scoped receipt rule keeps that case unverifiable. All 28 fullscreen scenarios now pass, including replacement with unchanged hash during foreground preparation; the six affected native/session/menu test files pass 571 tests. The reproduction fixture's recorded Calculator PID was corrected to its simulated PID77, and qualification deliberately uses the complete native title-bar census rather than requiring a complete SDK page tree.
Inferred: the projection mechanism is reproduced and repaired in fixtures; CFHash agreement is bounded to two reads of this unchanged window, not a uniqueness guarantee. No fullscreen input or live qualification occurred.
Resolves: FS1 = held; FS3 = held
Next: independent Sol and Opus input-control reviews, then reviewed integration and installed byte/discovery qualification; live preparation remains held until installed receipt.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/red.txt; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/readonly-hash-stability.json; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/focused.txt; docs/native-fullscreen.md

## FS5 · update · 2026-11-17 04:13
Observed: independent Sol review reproduced a wrong-control dispatch by swapping current AX Close/Fullscreen geometry after SDK snapshot creation; the cached token still named Close. It also reproduced unreadable peer census acceptance and an ordinary CLI success receipt stuck at unverifiable. Same-hash replacement between commands and state drift after the last state check expose limits not covered by FS4. FS4's claim of a repaired general mechanism was too broad.
Resolves: FS1 = failed
Next: remove the SDK geometry/token join for this native-only control; project a distinct semantic window-action candidate and dispatch only a narrowly qualified AXPress through the existing look/do click route, with no generic AX endpoint.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-sol.md

## FS6 · update · 2026-11-17 04:13
Observed: FS3's two-process hash stability prediction held for those observations, and reference continuity during one action is testable. It does not establish collision-free persisted object identity: Sol's same-hash replacement between commands passes. Neither a new controller nor serializing a private AX identity is authorized; persist the exact-window semantic action plus conservative hash discriminator, and state the limitation explicitly.
Resolves: FS3 = inconclusive
Next: require fresh exact-window semantics and reference continuity during action; never claim object continuity across CLI processes from CFHash alone.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-sol.md

## FS7 · prediction · 2026-11-17 04:13
Hypothesis: SDK token dispatch is unnecessary for this one native window action. A separately numbered native semantic candidate, projected from complete status-preserving AX reads, can use the existing internal AX adapter for a fixed AXPress after final ownership/reference/state requalification, eliminating the frame-to-cached-token seam without exposing a generic raw endpoint.
Test: retain Sol's mapping-race, unreadable-census and ordinary-receipt cases as failing public CLI scenarios before repair. Then verify SDK button tokens are never dispatched by this action, geometry swaps cannot click Close, unreadable census refuses, late observed state drift refuses, and exact state readback alone confirms both ordinary and durable receipts. Recheck focused tests and obtain both independent reviews of the final input diff.
Predicts: the mapping race either refuses or dispatches only the independently qualified fullscreen AX reference; neither Close nor SDK click is invoked. Unknown peer census and observed state drift refuse; valid ordinary receipt confirms while ack/no-transition remains unverified.
Against: any SDK token or wrong AX reference is dispatched, incomplete census is accepted, or success/no-op receipts cannot be distinguished.
Refs: python/jevdual/ax.py; python/jevdual/native.py; python/jevdual/session.py; tests/test_session_scenarios.py

## FS8 · update · 2026-11-17 04:28
Observed: all three Sol reproductions failed before repair (review-red-2.txt). The replacement route exposes a separate native semantic action ID, never an SDK token/frame; the cached Close ID refuses with zero input. Status-preserving AX census rejects unreadable peers and distinguishes unsupported/no-value subroles. Final AX reference/state validation precedes the fixed-purpose internal AXPress. Opus independently found durable basis rejection, ordinary receipt proof gaps and unintended drag/agent/partial-selector routes; those routes now refuse. Monitor explicitly authorized operator_evidence.py for a dedicated strict fullscreen predicate, and explicitly accepted fresh semantic identity across commands plus within-action reference continuity, not hash uniqueness or an atomic app-side toggle. Both ordinary and durable real CLI fixtures now confirm only acknowledged observed transitions; durable no-transition and unacknowledged outcomes retain unverifiable receipts without replaying input. Adversarial app-side state drift remains visibly unverified with one press.
Resolves: FS7 = held
Inferred: the revised route closes the cached-token seam structurally; this is fixture qualification, not installed or live fullscreen evidence. CFHash and app-side race limits remain explicit in docs/native-fullscreen.md.
Changes: fixed-purpose native AX route, complete census, operator-only/exact selector and drag exclusions, dedicated durable evidence validator and negative tests, truthful ordinary receipts.
Next: fresh independent Sol and Opus reviews of all five source files at the next commit; reviewed integration and installed receipt remain required before live preparation.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-sol.md; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-opus.md; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-red-2.txt; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/final-focused.txt (658 passed); /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/final-fullscreen.txt (78 passed after final narrow argument/receipt guard)

## FS9 · update · 2026-11-17 04:38
Observed: Sol's independent final review of ca371fc reproduced two missed seams: an exact fullscreen label resolves to an ordinary SDK control if native qualification disappears, and a dispatched reserved fullscreen operation accepts a generic basis when optional identity/readback metadata is removed. Its 659 affected tests passed, demonstrating those tests did not cover these changes together. FS8's structural closure claim was too broad for selector fallback and receipt classification.
Resolves: FS7 = failed
Next: preserve selected native intent across fresh label resolution, and classify dispatched reserved fullscreen operations from admitted operation identity, not optional producer metadata. Installation and live input remain held.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-sol-final-ca371fc.md; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/sol-final-ca371fc-probes.py

## FS10 · prediction · 2026-11-17 04:38
Hypothesis: both remaining counterexamples arise because routing decides whether an action is fullscreen from fresh or optional metadata instead of retaining admitted semantic intent. Retaining the prior selected fullscreen identity and requiring proof for dispatched reserved target -2 will close these fallbacks without changing ordinary labels or pre-dispatch refusals.
Test: first add Sol's two label downgrade scenarios to the public CLI fixtures and both stripped-proof basis variants to evidence tests; preserve their red results. Then test numeric and exact-label refusal with zero SDK/AX dispatch, fresh-look ordinary selection, and reserved-target evidence rejection while ordinary evidence and pre-dispatch refusal/interrupted-unknown records remain accepted where valid.
Predicts: the two exact labels refuse after native qualification disappears; a fresh explicit look can establish an ordinary control; all dispatched reserved-target records require the dedicated predicate even if metadata is erased. Existing no-send/unknown receipts remain truthful.
Against: any stale fullscreen selector dispatches SDK input, stripped proof is accepted as confirmed, an ordinary fresh selection is unnecessarily blocked, or valid no-send/unknown records lose their representation.
Refs: tests/test_session_scenarios.py; tests/test_operator_evidence.py; python/jevdual/session.py; python/jevdual/operator_evidence.py

## FS11 · update · 2026-11-17 04:41
Observed: final-review-red-2.txt records six expected failures (two public label downgrades and four stripped-proof/basis/count combinations), with six negative controls passing. A further unknown-dispatch/confirmed stripped-proof case failed before its guard extension. The first attempted test run used the wrong relative paths and ran no selected tests; final-review-red.txt is retained but is not reproduction evidence. The repair retains prior native selector intent before fresh label resolution and classifies fullscreen proof requirements from the admitted reserved target, including claimed effects with unknown dispatch. Focused validation passes 672 tests; lint and notebook checks pass. Explicit fresh-look ordinary selection, numeric refusal, valid no-send and interrupted-unknown records remain covered.
Resolves: FS10 = held
Inferred: these retained counterexamples are closed by narrow selector and evidence guards; independent review conclusions remain bound to their actual source commits. No installed or live behavior is proven.
Next: reconcile the pending independent Opus result and close final-source review gates before integration and installed delivery. No live input or installation while review findings remain unresolved.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/final-review-red-2.txt; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/final-review-unknown-red.txt; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-corrections-focused.txt; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-corrections-notebook.txt

## FS12 · prediction · 2026-11-17 04:43
Hypothesis: Opus B1 is caused by generic exception-to-effect defaults, not by input dispatch. The fixed fullscreen route's on_dispatch flag can authoritatively distinguish all pre-press failures from uncertain post-press outcomes without changing the shared foreground adapter or input timing.
Test: retain Opus's in-action census failure and press-boundary coordination preemption as ordinary and durable public-CLI red scenarios, then map only not-attempted results to qualified no-send refusals. Include post-dispatch failure as a negative control. Also bind ordinary fullscreen readback to the independent session PID/window for O2 and test mismatched proof. O1 remains a required fresh target SDK title-bar census before live preparation, not a claim from fixture rows; O3 is the documented conservative readback stop and O4 was fixed in f93c8c9.
Predicts: both pre-press failures yield dispatched=false, refused receipts and no stopped row in ordinary/durable sessions; post-press errors remain unverifiable with one attempted press. An ordinary proof with a different PID/window cannot confirm.
Against: any pre-press case claims dispatch or stops durable journaling, a post-press case claims not-sent, or self-consistent wrong-window proof confirms an ordinary receipt.
Refs: /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/review-opus-final-ca371fc.md; /Volumes/External SSD/Footwork-native-fullscreen-evidence-20261117/opus-final-probes/test_opus_final_probes.py
