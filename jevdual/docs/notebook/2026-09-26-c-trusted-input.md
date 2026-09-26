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
