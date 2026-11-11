# Application adaptation: run-now steps

Work package for steps A1 to A4 of `docs/repo-learning/app-adaptation/REPORT.md` (revision 6). The
review that produced that report is in `2026-11-11-app-adaptation-review.md`.

## AAD1 · prediction · 2026-11-11 21:45
Question: can Footwork's browser lane report the effect its pinned driver already measures?
Hypothesis: on driver 0.46.0 a successful browser_click reply carries a typed result with an effect word, and Footwork loses it only because browser_driver._effect maps every reply that is not a refusal to unverifiable. Reading that word in effectors/cua.py and passing it through _effect is sufficient; no driver change is needed.
Alternatives: the typed result is not present on the wire Footwork uses, or it appears under a shape the reply parser cannot see, in which case the change has no effect on a live session.
Test: unit tests in tests/test_browser_contract.py with replies in the published shape (effect, route, delivery, evidence, escalation, hint, summary; no status): confirmed, partial, suspected_noop, unverifiable with an escalation, an unknown effect word, and a non-error reply whose effect is refused. Then one live run on an owned local fixture page in a Footwork-launched browser session: a page-route click on a checkbox, and one on an element whose state cannot change.
Predicts: the unit cases map confirmed, partial and suspected_noop to the same words, and everything else to unverifiable; the escalation is carried on the effect and in the session's action record as diagnosis and is never printed as a next step; the pinned six-effect contract test passes unchanged. Live: the checkbox click records driver effect confirmed; the inert click records unverifiable or suspected_noop with an escalation.
Against: the pinned contract test changes; a reply without a typed effect is reported as confirmed; the escalation appears as an instruction; or the live checkbox click still records unverifiable, which would mean the typed result does not reach Footwork.
Refs: docs/repo-learning/app-adaptation/REPORT.md; python/jevdual/browser_driver.py; python/jevdual/effectors/cua.py; vendor/cua-driver/PROVENANCE.md

## AAD2 · prediction · 2026-11-11 21:45
Question: can a person sign in to the sites Footwork must drive inside the browser Footwork launches?
Hypothesis: a headed Chrome launched by Footwork with its persistent profile and a loopback debugging port accepts an ordinary interactive sign-in, and the session persists in that profile.
Alternatives: the identity provider blocks sign-in in a browser started with a debugging port; or sign-in works but does not survive a restart or a token renewal.
Test: the owner signs in by hand, in the Footwork-launched window, to Suno and to one site that uses Google sign-in. Footwork sends no input during sign-in and captures nothing. Afterwards: read-only observation that the signed-in state is present; quit and relaunch the browser and observe again; observe again after at least one hour.
Predicts: both sign-ins complete without an error page, and the signed-in state is observed after the relaunch and after the wait.
Against: either provider refuses the sign-in in this browser, or the signed-in state is gone after the relaunch or the wait. Then that site falls back to opt-in attachment to the person's own Chrome, and the lane choice is reopened only if that fails too.
Refs: docs/repo-learning/app-adaptation/REPORT.md; python/jevdual/browser_driver.py

## AAD3 · prediction · 2026-11-11 21:45
Question: does page-level node text keep the characters the accessibility value dropped?
Hypothesis: the lyrics editor's inner text, read from the page, maps to the verified 461-character, 24-line-feed lyrics file under one declared equivalence, where the accessibility value held 456 characters and 19 line feeds (SUN28, SUNU34).
Alternatives: inner text loses or adds characters with no fixed mapping (for example blank paragraphs rendered as one or two line feeds depending on position), so only the application's own copy is a faithful reader.
Test: depends on AAD2. In the signed-in Footwork-launched profile, open the song that holds the verified lyrics; read the editor node's inner text and text content through a read-only page evaluation; compare byte for byte with the file and with the accessibility value. No input is sent.
Predicts: inner text equals the file after at most one declared normalisation (line-ending form, or one trailing line feed), with 461 characters and 24 line feeds preserved.
Against: characters are lost, or the difference from the file is not describable by one fixed rule. Then the controlled clipboard read stays the verifier for this editor and step D's typing readback must not rely on inner text.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; results/suno-20261110/report.md

## AAD4 · prediction · 2026-11-11 21:45
Question: do replacing held text and a trusted click at viewport coordinates still disturb the foreground on the pinned driver?
Hypothesis: the driver's use of focus emulation since the 2026-09-25 probes has removed the roughly 100 ms tab selection when held text is replaced, and lets a trusted click at coordinates land while the browser window is in the background.
Alternatives: neither changed. Replacing held text still selects the tab and asks for the foreground, and the trusted route still does nothing in background posture.
Test: an owned local fixture page in a Footwork-launched browser session kept in the background while another application is frontmost. The page records focus, blur, visibility changes, key events and clicks with timestamps. Two operations through the driver: replace the held value of a text field; a trusted click at the viewport coordinates of a button. Before, during and after each, record the frontmost application and the page's event log. The probe sends no keystrokes of its own to any other application.
Predicts: for both operations the frontmost application does not change, the page records no visibility change, the field holds the replacement text, and the button records one click.
Against: the frontmost application changes or the page becomes visible or focused when it was not; or the field or button shows no effect. Either result makes that operation a foreground step in the plan; if both operations need the foreground the lane choice is reopened.
Refs: docs/repo-learning/app-adaptation/REPORT.md; python/jevdual/browser_driver.py

## AAD5 · prediction · 2026-11-11 21:45
Question: does a page channel reduce the help a browser task needs, compared with driving the same page through accessibility?
Hypothesis: on browser surfaces where the accessibility route is known to need help, the page arm completes with fewer human interventions.
Test: a panel fixed at ten browser surfaces, each with one frozen task, budget and success criterion, run once per arm with arm order alternating across surfaces. Measures: verified completion, human interventions, wrong dispatches, operator time, core mechanisms changed. The surface list and tasks are frozen in a later entry that revises this one, before either arm runs; this entry fixes only the measure and the rule.
Predicts: the page arm needs fewer interventions on at least 9 of the 10 surfaces (one-sided sign test, p about 0.011), with zero wrong dispatches and no core mechanism changed for an application quirk. A tie counts as not favouring the page arm.
Against: 8 or fewer surfaces favour the page arm, any wrong dispatch occurs on the page arm, or a core change is needed for one application. The panel is a coverage choice biased toward surfaces where accessibility struggles; a pass says the page arm is better there and supports no failure-rate claim about applications in general.
Refs: docs/repo-learning/app-adaptation/REPORT.md

## AADU1 · update · 2026-11-11 22:40
Resolves: AAD1 = held
Observed: six new cases in tests/test_browser_contract.py pass and three of them fail when the mapping is disabled; the pinned six-effect contract test is unchanged; the full suite gives 3440 passed, 62 skipped and one failure, tests/contract/test_cua_driver_seams.py::test_cua_driver_version_is_pinned, because this checkout's virtualenv holds driver build cleanup2 where the branch pins focus1 or helptag1. Live, with the pinned overlay first on the path, on an owned fixture in an isolated Footwork-launched Chrome (results/page-effects-20261111/run2/steps.jsonl): the page-route click on the checkbox returned effect confirmed with evidence "value_readback: bounded semantic target state changed", and the page logged the change; the click on a control with no handler returned unverifiable with escalation target page, reason effect_unconfirmed. Neither reply had a status field; both carried effect, route, delivery, hint, next_call and summary.
Inferred: the driver's typed result reaches Footwork on the route it uses, and the only loss was in _effect. The version failure predates this change and is an environment mismatch, not a regression; it does mean the checkout's plain virtualenv is not the runtime the branch expects.
Changes: effectors/base.py, effectors/cua.py and browser_driver.py carry effect, evidence and escalation; session.py keeps the escalation in the action record as diagnosis; cli.py's route help names the page route as the default, which is what the bridge does.
Next: AAD4.
Refs: results/page-effects-20261111/run2/steps.jsonl; results/page-effects-20261111/run2/page-events.jsonl; scripts/probe_page_effects.py

## AADU2 · update · 2026-11-11 22:40
Resolves: AAD4 = inconclusive
Observed: run2, with another application frontmost throughout the steps. Replacing held text: the reply said "typed 11 char(s) ... replacing 9 char(s)" with effect unverifiable; the field then held the replacement; the page logged a window focus event during the call and no blur afterwards, no visibility change and no key event; the frontmost-application log shows no change. Trusted click at viewport coordinates (84, 125): the page logged one click on the button with isTrusted true; the frontmost application did not change. The frontmost application was sampled by a loop of two subprocess lookups with a 50 ms wait, so a change shorter than roughly 100 ms could fall between samples. Nobody typed during the run.
Inferred: the trusted click at coordinates lands in background posture on this driver, which the 2026-09-25 probes of the trusted route did not see for other controls. For held-text replacement all four predicted observations occurred, but the test cannot tell the two explanations apart: a tab selection of about 100 ms is exactly what the sampler could miss. The page's focus event without a later blur is consistent with focus emulation and does not show real key-window status. The stray-keystroke hazard is therefore not excluded.
Changes: the probe's sampler now loops on one lookup without a wait and writes its sample count and largest gap.
Next: AAD6 with the finer sampler. Two findings from getting the probe to run, both outside AAD4. First (run1-bind-failed): on a fresh profile bind_footwork_chrome failed with "owned Chrome identity changed during window binding"; the surviving browser process carried the window-recovery helper's arguments, which have no debugging port, so the helper appears to have won the profile singleton from the slower first launch. Second: launching the browser took the foreground from the application in use, in the default background posture; the probe now hands it back.
Refs: results/page-effects-20261111/run2/steps.jsonl; results/page-effects-20261111/run2/page-events.jsonl; results/page-effects-20261111/run2/front-app.jsonl; results/page-effects-20261111/run1-bind-failed/front-app.jsonl

## AAD6 · prediction · 2026-11-11 22:40
Revises: AAD4
Question: does replacing held text bring the browser to the front for any interval the operating system reports?
Hypothesis: it does not. The pinned driver replaces held text under focus emulation without selecting the tab or activating the window.
Alternatives: the driver still selects the tab for about 100 ms, as on 2026-09-25, and the earlier sampler missed it.
Test: the same probe and fixture with the frontmost application sampled in a loop of single lookups with no wait, recording the sample count and the largest gap between samples. Run it three times.
Predicts: in all three runs the frontmost application does not change between the background-restored step and the final observation, with a largest sampling gap during the replace step well under 100 ms; the field holds the replacement each time.
Against: any run records the browser as frontmost during or after the replace step. If the largest gap is 100 ms or more the runs are inconclusive, not support. This test still cannot show where a real keystroke would land; a pass makes replacement a candidate for background use, to be confirmed with an owned key sink before the posture gate is relaxed.
Refs: scripts/probe_page_effects.py; results/page-effects-20261111/run2/front-app.jsonl

## AADU3 · update · 2026-11-11 23:05
Observed: three AAD6 runs and one repeat did not reach their steps. With the isolated browser already running in the background and its debugging port listening, the driver refused browser_prepare each time with code background_unavailable: Chrome brings itself to the front to show an "Allow remote debugging?" prompt whenever a new DevTools connection opens, sessions then share that one connection, and a background attach requires the browser window to be on another Space (results/page-effects-20261111/attach-refused/prepare-reply.json). No DevToolsActivePort file was present in that profile although the port was listening. Run2 had attached without a refusal; in run2 the browser had just been launched and was frontmost at the moment of attachment.
Inferred: on this driver and Chrome 157, attaching the page channel is itself a foreground step unless the browser was already in front or sits on another Space. Footwork's browser sessions build and destroy a driver for every command, so every command opens a new DevTools connection and meets this condition again. A persistent holder that keeps one connection is therefore a precondition for background page work, not only a way to keep refs. This also means the Footwork-launched profile and the person's own Chrome reach the page through the same consent mechanism. AAD6 is still open: its question is about replacement after attachment, and these runs never attached.
Changes: none to code.
Next: run AAD6 with the isolated browser relaunched before each run, so attachment happens while it is frontmost, started only after three seconds without input from the person, and with the foreground handed back before the steps.
Refs: results/page-effects-20261111/attach-refused/prepare-reply.json; docs/repo-learning/app-adaptation/REPORT.md
