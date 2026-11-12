# Browser holder for start --browser

Step B1 of `docs/repo-learning/app-adaptation/REPORT.md`: keep one driver, and so one approved
DevTools connection, alive for a `start --browser` session, so commands after the first can run with
the browser in the background. Branch claude/browser-holder-20261111, stacked on PR #24.

## BH1 · prediction · 2026-11-11 19:31
Question: does holding one driver for the session let later commands observe and act on the page with the browser in the background?
Hypothesis: the background refusal is the driver's static check in browser_prepare (cua-driver-core browser/prepare.rs:1046-1075), and Chrome's self-activation follows only a new DevTools connection; the driver caches one connection per port for its own lifetime (platform-macos browser/cdp_client.rs:115-150). Footwork builds a new driver per command (session.py bind), so both recur on every command. A holder that runs browser_prepare once at start, answers later prepare calls from that result, and serves bind, snapshot, click, type_text and navigate through the same driver removes both.
Alternatives: (a) browser_bind or browser_snapshot also refuses, or brings Chrome forward, in the background on the held driver; (b) the cached connection is dropped between calls (an idle timeout or a target switch evicts it) and a later call opens a new one; (c) tab ids change between calls even on one driver.
Test: an isolated Chrome profile and port, not 9333 or 9555, on an owned local fixture page. Held arm: start a session through the holder (Chrome comes forward once, at launch), restore the previously frontmost application, wait 5 s, then run, each as its own process through the session's bind, five rounds of observe followed by a page-route click on the fixture's counter, spread over at least two minutes, while a sampler records every change of the frontmost application. Control arm, same profile after a Chrome restart: identical commands with each command building its own driver, as today.
Predicts: held arm: all ten commands succeed with no background_unavailable refusal; the counter reads 5 at the end; the frontmost application never becomes Chrome after the restore; every command binds the same tab id. Control arm: the first background command refuses with background_unavailable and nothing is dispatched.
Against: any held-arm refusal or any held-arm frontmost change to Chrome after the restore; or a tab id that differs between held commands; or the control arm succeeding in the background (then the holder is not what removes the refusal).
Refs: docs/repo-learning/app-adaptation/REPORT.md#first-results-2026-11-11; scripts/probe_page_effects.py

## BH2 · update · 2026-11-11 19:44
Resolves: BH1 = failed
Observed: the held arm stopped at start (results/browser-holder-20261111/held-1-summary.json). The holder launched, bound and kept its prepare; start's own attach then got a prepare answered from the holder and a bind whose only tab had a different id from the one the holder's attach saw, so start refused "the session's tab … is no longer in this window" and stopped the holder. No background command ran. A direct check on one held driver (scripts/probe_browser_tab_ids.py, isolated profile) gave four different tab ids for the same tab across four get_browser_state calls one second apart.
Inferred: alternative (c) holds and is stronger than stated: the driver mints tab ids per call, not per connection. Tab handles cannot carry a session's tab between commands even with one driver, so BH1's same-tab clause is false and B1's "tab identity survives" deliverable cannot come from the driver's handles.
Changes: held sessions rebind by page URL, as sessions without a holder do; start takes the active tab of the window the holder bound. The background question is untested.
Next: BH3 re-registers the background question without the tab clause.
Refs: results/browser-holder-20261111/held-1-summary.json; scripts/probe_browser_tab_ids.py

## BH3 · prediction · 2026-11-11 19:46
Question: with the holder rebinding by page, do later commands observe and act with the browser in the background?
Hypothesis: as BH1: the background refusal is browser_prepare's static check, which the holder answers from its first prepare; bind, snapshot and click on the held driver neither refuse nor bring Chrome forward, and the page-identity check reads only the HTTP target list.
Alternatives: (a) get_browser_state or browser_snapshot refuses, or Chrome comes forward, in the background on the held driver; (b) the cached connection is evicted between calls and a later call opens a new one.
Test: as BH1's held arm (scripts/probe_browser_holder.py --arm held), isolated profile and port 9466: five rounds of look and do click on the fixture's counter, 25 s apart, each its own process, with the frontmost-application sampler; then the control arm (--arm control) after the probe's Chrome exits.
Predicts: held: all ten commands exit 0 with no background_unavailable; the page log shows five clicks on the counter; the frontmost application is never Chrome after the restore. Control: the first background look refuses with background_unavailable.
Against: any held-arm refusal, or Chrome frontmost after the restore during the held arm; or the control arm's first background look succeeding.
Refs: docs/notebook/2026-11-11-browser-holder.md#bh1
