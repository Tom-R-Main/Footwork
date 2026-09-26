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
