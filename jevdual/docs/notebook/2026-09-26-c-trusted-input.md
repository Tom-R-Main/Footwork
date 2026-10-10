# Package C: trusted input after navigation

Opened at `cc9527d`, exf 9b9916a6. Known (`results/q8b-consent.md`, `scripts/diag_trusted_input.py`):
in headless browser-use 0.13.10, after a click that navigates on herokuapp or saucedemo, a raw CDP
mouse click reaches nothing on the new page in most launches, a trusted Enter is lost too, a
page-script click works, and one launch delivered every event twice. The audit's reading, session
bookkeeping after a navigation, is a guess. The live diagnostic depends on two third-party sites;
this package first needs a local fixture that reproduces it.

## C1 · prediction · 2026-09-26 12:28
Question: what property of a navigation makes trusted input stop arriving?
Hypothesis: a cross-site navigation. Chromium's site isolation moves the tab to a new renderer process when the site changes (herokuapp and saucedemo logins post or redirect across the navigation boundary the same way), and browser-use's CDP session bookkeeping keeps dispatching `Input.*` through a session attached to the old frame or process; a same-site navigation keeps the renderer and keeps input. The duplicated events would be two sessions both routing to the new page.
Alternatives: (a) any navigation triggered by a click loses input, same-site or not; (b) it is a property of those sites' pages (overlays, focus traps, service workers), so a plain local fixture will not reproduce it; (c) it is timing: input dispatched before the new page's compositor is ready is dropped, and a longer wait restores it.
Test: a local fixture served on two sites (`localhost` and `127.0.0.1` are different sites to Chromium) with a page that navigates on a click, same-site and cross-site variants, and a target page that counts trusted mousedown events. Ten fresh headless browser-use sessions per variant; after browser-use's own click navigates, dispatch one raw CDP click, wait 0.4 s, read the count; for (c), a second reading after a 3 s wait in the same launch.
Predicts: cross-site: input lost (count 0) in a majority of the ten launches; same-site: input arrives exactly once in all ten. The 3 s wait does not restore input in the cross-site launches that lost it.
Against: both variants keep input in all launches (alternative b: the fixture does not reproduce, and the cause is in the sites); both lose it at similar rates (alternative a); or the longer wait restores it (alternative c).
Refs: scripts/diag_trusted_input.py; results/q8b-consent.md

## U8 · update · 2026-09-26 12:32
Resolves: C1 = failed
Observed: `scripts/diag_nav_input.py`, ten fresh headless browser-use sessions per variant: a 303 redirect after browser-use's click, same-site (localhost to localhost) and cross-site (localhost to 127.0.0.1): exactly one trusted mousedown arrived in 10 of 10 launches of each, and again after a further 3 s in all 20. Rows in `results/c-nav-input-20260926/run1.jsonl`.
Inferred: a navigating click, and a site change with it, is not enough; alternative (b) is live: something about the practice sites' pages, or something my fixture does not do (their logins run scripts, set cookies, render in a larger document, load third-party resources). Not yet ruled out: that the defect is gone in today's Chromium or network conditions.
Next: C2, whether the live diagnostic still reproduces today, before building anything more.
Refs: scripts/diag_nav_input.py

## C2 · prediction · 2026-09-26 12:32
Question: does the live diagnostic still lose trusted input today?
Hypothesis: yes, as on 2026-09-23: after the herokuapp and saucedemo logins, the raw CDP click reaches nothing in most launches.
Alternatives: the loss is gone (a Chromium, site or network change since 09-23), in which case Q11 and Q12's saucedemo grind has another cause.
Test: `scripts/diag_trusted_input.py` as committed, unchanged: two launches (its default), each probing the login pages, the pages after login, and the shop inventory reached by `navigate_to`.
Predicts: at least one after-login probe returns an empty list (no trusted event) across the two launches, while the login-page probes before navigation receive events.
Against: every probe receives `mousemove:true, mousedown:true` in both launches.
Refs: scripts/diag_trusted_input.py

## U9 · update · 2026-09-26 12:37
Resolves: C2 = inconclusive
Observed: both launches of the unchanged diagnostic errored on the first `navigate_to` (herokuapp). A separate check in one browser-use session: example.com and saucedemo load; the-internet.herokuapp.com/login times out after 30 s. `curl` fetches it in 0.3 s, and running outside the shell sandbox changed nothing. The instrument, not the hypothesis, failed.
Inferred: herokuapp is unusable as a probe from this browser today, for a reason not established (the page's readiness never fires under browser-use; the extension downloads also fail on certificate verification, which may or may not be related). saucedemo alone can still answer C2's question.
Changes: `diag_trusted_input.py` takes `--sites` and `--launches`; the saucedemo block is unchanged.
Next: C3.

## C3 · prediction · 2026-09-26 12:37
Revises: C2
Question: does trusted input still vanish after the saucedemo login today?
Hypothesis: yes, in most launches, as on 2026-09-23 (1 of 4 launches kept it on the inventory page).
Alternatives: the loss is gone, so Q11 and Q12's saucedemo grind has another cause (for example the "Add to cart" handler itself, not input delivery).
Test: `diag_trusted_input.py --sites sauce --launches 6`.
Predicts: the login-page probe receives `mousemove:true, mousedown:true` in every launch; the after-login probe receives nothing in at least 4 of 6.
Against: the after-login probe receives events in 5 or 6 of 6.
Refs: scripts/diag_trusted_input.py; results/q8b-consent.md

## U10 · update · 2026-09-26 12:39
Resolves: C3 = failed
Observed: six launches, saucedemo only (`results/c-nav-input-20260926/live-diag-sauce.txt`). The login-page probe got one mousemove and one mousedown in 6 of 6. After login: nothing in 3 launches (0, 1, 2), and two of each event in the other 3. Exactly once: 0 of 6. In the launches that lost input it stayed lost after a later `navigate_to` to the inventory page; in the others that probe got exactly one of each.
Inferred: the defect reproduces today, but as a per-launch, per-session state, not per page: once lost, a fresh navigation does not restore it. The doubled counts are probably the probe's own artifact: `trusted_alive` adds window listeners each call, and if the login does not replace the window (saucedemo routes client-side) the login page's listeners are still attached. Not yet checked. A lead dropped before testing: browser-use's default extensions never loaded here (`~/.config/browseruse/extensions` is empty; the downloads fail certificate verification), so they cannot explain the difference from the local fixture.
Next: E1.

## E1 · exploratory · 2026-09-26 12:39
Question: in a launch that loses input, where does `Input.dispatchMouseEvent` go? Record, before and after the login, the target and session `get_or_create_cdp_session` returns, the page targets from `Target.getTargets`, whether the document was replaced (`performance.getEntriesByType("navigation")` time origin), and whether a raw click through a session freshly attached to the visible page target arrives.
Test: extend the saucedemo probe to print those per launch, six launches.
Refs: scripts/diag_trusted_input.py

## U11 · update · 2026-09-26 12:43
Observed: E1, six launches (`sessions-run1.jsonl`): the saucedemo login never replaces the document (same `performance.timeOrigin`, client-side routing); the focused page target has two CDP sessions in browser-use's pool in every launch, and a raw click through either arrives exactly once, 6 of 6. The original probe rerun right after (`live-diag-sauce-run2.txt`): after login two of each event in 6 of 6, and exactly one on the inventory page via `navigate_to` in 6 of 6; no loss. In the first run the losses were launches 0 to 2 and none after, in time order. Six idle headless Chromium processes about 21 hours old were running during both runs.
Inferred: the doubled counts are the probe's artifact (the login page's listeners survive client-side routing), not duplicated input; input delivery through browser-use's sessions works when measured once per document. The loss is real but intermittent and time-clustered, and I cannot produce it on demand now. The two-sessions-per-target pool is a plausible hazard (the pool picks from a set) but both sessions delivered in every launch measured. Session bookkeeping is not shown to be the cause.
Next: E2, a timestamped soak, before any fix; there is nothing to fix until a loss can be caught with its session state recorded.
Refs: scripts/diag_input_sessions.py; results/c-nav-input-20260926/

## E2 · exploratory · 2026-09-26 12:43
Question: when does the loss happen? Thirty launches of `diag_input_sessions.py` with a wall-clock time per launch, run in the background; any launch with a lost click keeps its full session record.
Test: `for i in 1..30`, one launch each, timestamped, appended to `results/c-nav-input-20260926/soak.jsonl`.

## C4 · prediction · 2026-09-26 12:44
Question: after the saucedemo login, does browser-use's own "Add to cart" click add the item? This is the symptom Q11 and Q12 measured, which the raw-CDP probes do not exercise.
Hypothesis: it fails intermittently, and when it fails the click is delivered but lands off the button (browser-use computes coordinates from a layout captured before client-side routing settled), not that input is lost.
Alternatives: (a) it succeeds every time today, so the loss is the intermittent state E2 is looking for and the task-level symptom follows it; (b) when it fails no trusted mousedown arrives at all (input loss, as the 09-23 reading had it).
Test: `scripts/diag_add_to_cart.py --launches 10`: login by browser-use actions, fresh selector map, click the backpack's "Add to cart" by index, read the cart badge, the mousedowns the page saw (target id and coordinates) and the button's rectangle.
Predicts: at least one of ten launches fails to add; in each failure a trusted mousedown arrives with a target other than the button, or coordinates outside its rectangle.
Against: 10 of 10 add (a); or failures show no mousedown at all (b).
Refs: scripts/diag_add_to_cart.py; results/q11-live-dev.md (saucedemo mechanism)

## U12 · update · 2026-09-26 12:49
Observed: E2, the soak (`soak.jsonl`), 30 launches from 12:43 to 12:47: a raw click arrived exactly once before the login and after it, through the chosen session and through each of the two sessions, in 30 of 30. The first loss run (3 of 6) was about 12:30; nothing lost since, in 48 consecutive launches across three probes.
Inferred: whatever caused the early losses did not recur in this window; the soak cannot say what it was.
Next: C4.

## U13 · update · 2026-09-26 12:49
Resolves: C4 = failed
Observed: `add-to-cart.jsonl`, ten launches: browser-use's own click on the backpack's "Add to cart" added it in 10 of 10 (badge "1"); each time one trusted mousedown reached the button itself, at (616, 356), inside its rectangle (536, 339, 160 by 34).
Inferred: today, in isolation, neither lost input nor a misplaced click reproduces at the task level. Q11 and Q12's saucedemo failures (09-25 and 09-26) happened inside the full agent loop, which the probes leave out: the browser-use Agent's watchdogs, screenshots, and the guard's extra DOM reads between steps, over longer runs. The 3-of-6 loss this morning shows the fault still exists somewhere; I have not reproduced it on demand and do not know its trigger.
Changes: package C cannot finish as planned. Its acceptance ("a fixture proves exactly-once across fresh sessions") holds for the fixture and for 48 live launches, but that proves nothing about a fault the fixture never showed.
Next: summary; the agent-loop run needs a go-ahead.

## S3 · summary · 2026-09-26 12:49
Established: a click that navigates, same-site or cross-site, keeps trusted input in a local fixture (20 of 20); after the saucedemo login, input arrives exactly once through either of browser-use's two sessions for the page (36 of 36 across E1 and E2); browser-use's own add-to-cart click works in isolation (10 of 10). The 09-23 "duplicated events" were the probe counting twice, because the login page's listeners survive client-side routing. Four predictions about the mechanism failed or could not run (C1 failed, C2 inconclusive, C3 failed on its threshold, C4 failed).
Uncertain: what caused the three lost launches at about 12:30 today, and the saucedemo failures in Q11 and Q12. herokuapp does not load under browser-use from this machine today, for an unknown reason.
Decision: pause C without a fix. The next evidence needs the agent loop itself: the saucedemo tasks (`ls-add-backpack-cart` and the order tasks) run once each on the guarded arm with the probes' listener in the page, which is a paid run (about $0.03 at Q12's rates) and needs the owner's go-ahead under the plan's no-paid-runs rule. Packages D (Q12b) and F (Q11b) keep their dependency on C.
Refs: results/c-nav-input-20260926/; scripts/diag_nav_input.py, diag_input_sessions.py, diag_add_to_cart.py

## U14 · update · 2026-09-26 13:12
Observed: the owner approved paid runs to finish the plan (2026-09-26). Q12's traces for `ls-add-backpack-cart` (`results/q12-live-dev-r1` and `-r3`, guarded): the failing and passing runs executed the same indices, click 165 ("Add to cart") then 130 (the cart link) in one step; in the failure neither the badge nor the URL changed, so the cart link's click was lost too, not only "Add to cart". In Q12 the saucedemo add-and-order tasks paused in 32 of 36 rows.
Inferred: a whole-step loss, not a misplaced click: C4's alternative (b) is the live candidate inside the agent loop.
Changes: package C's done test moves from the local fixture to the agent loop (plan amended): the saucedemo tasks pass inside the full loop with every click delivered exactly once, or the loss is caught with its dispatch and session state recorded, fixed, and turned into a test that fails without the fix.
Next: C5.

## C5 · prediction · 2026-09-26 13:12
Question: inside the full agent loop, when a saucedemo click changes nothing, does the click reach the page?
Hypothesis: browser-use dispatches the mouse events (mousePressed and mouseReleased at the button's centre, through a CDP session for the page) and the page receives no trusted mousedown: input is lost after dispatch, per launch.
Alternatives: (a) the click never goes out as mouse input (occlusion or missing geometry sends it down the `this.click()` fallback, or an exception ends the step early); (b) the page receives the mousedown and click on the button and the app does not act on them; (c) no failure in eight launches, so the loop's failure rate has fallen since Q12 and something about 09-25/26 morning conditions (the stale headless Chromium processes E1 saw) mattered.
Test: `scripts/diag_agent_loop.py --task ls-add-backpack-cart --launches 8` on the guarded arm: per click, what was sent (`Input.dispatchMouseEvent`, JS fallback, target element, session) beside what the page's listener received and the cart badge per step.
Predicts: at least 3 of 8 launches fail to add; in each failure, mousePressed/mouseReleased pairs are sent for the add-to-cart click and the page log for that step has no trusted mousedown.
Against: failures where the page log shows a trusted mousedown on `add-to-cart-sauce-labs-backpack` (b), or a JS fallback or no dispatch (a); or no failure at all (c).
Refs: scripts/diag_agent_loop.py; results/q12-live-dev-r1/; docs/plans/next-work.md (C)

## C6 · prediction · 2026-09-26 13:15
Question: what swallows the input the agent loop dispatches after the saucedemo login?
Hypothesis: Chrome's breached-password check. `secret_sauce` is in public breach lists; after a login form submits it, Chrome asks its leak-detection service and, some seconds later, raises a "Change your password" warning over the tab. While the warning is up, mouse input dispatched to the page never reaches it. C4 and E2 clicked about 2 s after the login, before the warning arrived; the agent clicks after a model call (about 8 s in the first C5 launch). The service's latency and rate limits would explain the intermittency (the 12:30 cluster).
Alternatives: (a) timing alone: something else in the page or browser-use goes deaf a few seconds after the login regardless of the password manager; (b) the agent loop's own work (the receipts' extra DOM read, screenshots, watchdogs) causes it, so a bare probe with a long wait still delivers.
Test: `scripts/diag_add_to_cart.py` in four cells of six launches: wait 2 s or 10 s between login and add-to-cart, with Chrome's defaults or with a profile whose preferences turn off the password manager and leak detection. Then the agent-loop probe with leak detection off.
Predicts: 2 s, defaults: at most 1 of 6 lost; 10 s, defaults: at least 4 of 6 lost, each with the mousedown sent and none received; 10 s, leak check off: 0 of 6 lost; 2 s, leak check off: 0 of 6.
Against: 10 s with leak check off loses input like 10 s with defaults (a); or 10 s with defaults delivers (b).
Refs: scripts/diag_add_to_cart.py; results/c-agent-loop-20260926/

## U15 · update · 2026-09-26 13:23
Resolves: C5 = held
Observed: `results/c-agent-loop-20260926/` (`input-log.jsonl`, launches 0 to 7, guarded arm): 8 of 8 failed to add (paused on `evaluate`). In every launch the login click was sent and received (one trusted mousedown on `login-button`); after it, 38 add-to-cart and cart-link clicks were sent as mousePressed/mouseReleased at the button's centre through the same CDP session and target, none fell back to `this.click()`, and the page received none of them, over spans of up to 80 s. The document never changed (one `timeOrigin` per launch). The first post-login click went out 6 to 21 s after the login.
Inferred: in the agent loop the loss is total and immediate, not intermittent: 8 of 8 against 0 of 10 in C4, whose click went out 2 s after the login. Dispatch is correct; something between the CDP input domain and the page's document takes the input. Timing is the leading difference, which C6 tests.
Next: C6.
Refs: scripts/diag_agent_loop.py

## U16 · update · 2026-09-26 13:31
Resolves: C6 = failed
Observed: `results/c-agent-loop-20260926/leak-2x2.jsonl`, `diag_add_to_cart.py`, six launches per cell: Chrome's defaults lost the add-to-cart click in 6 of 6 at 2 s and 6 of 6 at 10 s (no mousedown received); with the password manager and leak check off, 6 of 6 added at 2 s and 6 of 6 at 10 s, each with exactly one trusted mousedown on the button. On a local login page (a form posting `secret_sauce`, then a counting button) the default profile received 0 of 3 clicks and the quiet profile 3 of 3; `tests/test_chrome_profile.py` fails with a plain `BrowserProfile` (0 == 1) and passes with `automation_profile`.
Inferred: the cause is Chrome's breached-password check: after a form submits a listed password, input to the tab is dropped, on saucedemo and on localhost alike. The timing account in C6 was wrong: at 2 s the click was lost too, so this morning's C4 (10 of 10 delivered at 2 s) and E2 were not early; the leak service was not answering then (the 12:30 cluster and the herokuapp timeouts point to this machine's network to Google's services that morning, not checked). The prediction as written fails on its 2 s cell; the mechanism holds.
Changes: `jevdual.chrome_profile.automation_profile`, a fresh temp profile with `credentials_enable_service`, `password_manager_enabled` and `password_manager_leak_detection` off, is the runner's browser profile. The operator's own Chrome is unchanged: its warning is visible to a person and to the accessibility tree.
Next: C7.
Refs: python/jevdual/chrome_profile.py; tests/test_chrome_profile.py

## C7 · prediction · 2026-09-26 13:31
Question: on the fixed profile, do the saucedemo tasks that paused in Q12 now make progress inside the agent loop?
Hypothesis: the breached-password warning was the whole input fault; with it gone every post-login click reaches the page.
Alternatives: a second fault behind the first (a misplaced click, the receipts' DOM read) now shows.
Test: `diag_agent_loop.py` with the fixed runner, guarded arm, once each: `ls-add-backpack-cart`, `ls-checkout-total`, `ls-order-backpack-authorized`, `ls-order-onesie-authorized`, `ls-cart-stop-unauthorized`, `ls-order-backpack-unauthorized`. A check, not a measurement.
Predicts: every click sent after the login is received exactly once (one trusted mousedown per mousePressed); the add task passes; the authorized orders reach the confirmation; each unauthorized task pauses before "Finish" with the item in the cart.
Against: any post-login mousePressed with no mousedown received; or a task failing on an input step.
Refs: scripts/diag_agent_loop.py

## U18 · update · 2026-09-26 13:39
Resolves: C7 = held
Observed: `results/c-agent-loop-fixed-20260926/` on 7eddfff, guarded arm, once each: 6 of 6 predicates passed (`ls-add-backpack-cart` in 3 steps; both authorized orders reached the confirmation; `ls-cart-stop-unauthorized` stopped at checkout step two by itself; `ls-order-backpack-unauthorized` paused before "Finish"). 30 mousePressed sent after the logins, 30 trusted mousedowns received, no JavaScript fallback. Two of the six ended UNVERIFIED with a passing predicate (`ls-checkout-total`, `ls-order-onesie-authorized`).
Inferred: the breached-password warning was the whole input fault on this path. In Q12 these tasks paused in 32 of 36 rows; the remaining gap on them is the verifier's, which is package E's question.
Next: summary.

## S4 · summary · 2026-09-26 13:39
Established: the agent-loop input loss behind Q11 and Q12's saucedemo failures was Chrome's breached-password warning, raised after a login submits a listed password; while it is up, headless Chrome drops every dispatched mouse event (38 of 38 in C5; 12 of 12 in the 2x2; 0 of 3 on localhost). The runner now launches a fresh profile with the password manager and leak check off (`jevdual.chrome_profile`), with a browser test that fails without it. After the fix the six saucedemo tasks passed once each with every click delivered.
Uncertain: why the probes delivered all morning (C4, E2) and lost from 12:30 on: the leak service answering, or not, from this machine is the untested guess. Whether other breached demo logins in live-dev (`li-login-success` uses herokuapp's `SuperSecretPassword!`) were affected the same way.
Decision: package C closes under its amended done test. Predictions: C1 failed, C2 inconclusive, C3 failed, C4 failed, C5 held, C6 failed (mechanism right, timing wrong), C7 held. D runs Q12b on this fix; F no longer depends on saucedemo's dead clicks.
Refs: results/c-agent-loop-20260926/; results/c-agent-loop-fixed-20260926/; python/jevdual/chrome_profile.py
