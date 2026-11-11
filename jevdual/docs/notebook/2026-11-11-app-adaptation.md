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
