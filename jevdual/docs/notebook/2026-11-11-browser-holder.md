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
