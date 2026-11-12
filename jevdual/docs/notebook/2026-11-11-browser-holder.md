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

## BH4 · prediction · 2026-11-11 19:58
Question: is the duplicated start page the window-recovery helper opening a second window on a launch whose own window has not appeared yet?
Hypothesis: both BH3 arms stopped at start with "initial browser page requires one unique exact URL"; the control arm, which never uses the holder, stopped the same way. A direct launch on a fresh profile (bind_footwork_chrome with a URL, port 9466) left two page targets on the fixture URL. bind_footwork_chrome starts the `open -na … --new-window <url>` helper on the first empty on-screen window list, which for a new launch can come before Chrome's own window is on screen. Waiting a bounded grace for a new launch's window before recovering would leave one page.
Alternatives: the duplicate comes from Chrome itself (the launch URL opened twice, or a restored session), so a grace period changes nothing.
Test: with the helper deferred for a new launch until 5 s after the driver is ready (an existing browser without a window still recovers at once), launch three times on fresh profiles through bind_footwork_chrome with the fixture URL, and count page targets on that URL in /json/list after binding.
Predicts: one page target on the URL in each of the three launches, and the helper never runs.
Against: two page targets on the URL in any launch with the helper not run.
Refs: python/jevdual/browser_driver.py bind_footwork_chrome

## BH5 · update · 2026-11-11 19:48
Resolves: BH4 = held
Observed: with a new launch given 5 s before window recovery, three launches on fresh profiles with the fixture URL each left one page target on it, and the recovery helper never ran; binding took 1.56 to 1.69 s (results/browser-holder-20261111/launch-duplicates.json). An offline test fails with the grace removed. The first BH3 attempt did not reach its question: both arms stopped at start on the duplicate page, before any background command (results/browser-holder-20261111/bh3-attempt-1-summary.json), so BH3 stays open.
Inferred: before this fix, start --browser --url on a newly launched browser would refuse whenever the recovery helper ran first, with or without the holder; the holder was not involved.
Changes: b32d81d. Correction to this file's headings, which ran ahead of the clock: BH1 was committed at 19:29 (heading 19:31), BH2 and BH3 at 19:42 (headings 19:44 and 19:46), BH4 at 19:46 (heading 19:58). Each prediction was still committed before its test.
Next: rerun BH3 unchanged.
Refs: results/browser-holder-20261111/launch-duplicates.json; results/browser-holder-20261111/bh3-attempt-1-summary.json
