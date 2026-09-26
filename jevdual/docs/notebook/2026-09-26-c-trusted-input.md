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
