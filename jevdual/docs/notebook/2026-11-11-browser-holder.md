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

## BH6 · update · 2026-11-11 19:51
Resolves: BH3 = held
Observed: held arm (fresh profile, port 9466): start and all ten background commands exited 0; the page logged five clicks on the counter; after the restore the frontmost-application sampler (28703 samples, largest gap 48 ms) recorded no change, and the page logged no focus or visible event after it went hidden. The holder answered all 11 later prepare calls from its first and served 11 binds, 17 snapshots and 5 clicks through one driver. Control arm (fresh profile, no holder): start passed with the browser in front; the first background look refused with browser_prepare's background limitation and nothing was sent; the browser did not come forward (results/browser-holder-20261111/bh3-summary.json).
Inferred: the per-command driver is what made background page work impossible on this lane, and one held driver removes it for observation and page-route clicks. Typing, navigation after start and coordinate input were not exercised in the background; a 48 ms sampler gap cannot exclude a shorter activation.
Changes: none beyond BH5.
Next: B2 (refuse or detect a second DevTools client) and B3 (input bound to the document generation); typing through the holder in the background; DemoGeek's take primitives (rectangles, waits, per-character insertText, file inputs, window bounds) for step D.
Refs: results/browser-holder-20261111/bh3-summary.json; scripts/probe_browser_holder.py

## BH7 · prediction · 2026-11-11 20:44
Question: does typing through the holder stay in the background, and does the posture gate still refuse replacing held text?
Hypothesis: browser_type inserts without selecting the tab when it neither replaces nor uses keystrokes (the bridge's note from the 2026-09-25 tab probe); appending to a field and typing into an empty one take that route, so through the held driver they land with the page hidden. Typing into a field that holds text is a replacement, which selects the tab for about 100 ms, so in background_only the bridge refuses it before sending, as without a holder.
Alternatives: (a) insert_text without replace also makes the page visible or focused, or brings the browser forward; (b) it reaches the field but the value differs (lost or doubled characters); (c) the refusal is skipped or something is sent through the holder.
Test: scripts/probe_browser_holder.py --arm held --typing on a fresh isolated profile, port 9466, on the fixture extended with an empty field "Note": after the restore, three rounds of do append to "Name" with " +<round>", 20 s apart; then do type "first note" into "Note"; then do type "second" into "Note" again. Each command is its own process; the sampler and the page's own focus, visibility and input log run throughout.
Predicts: the three appends and the first type exit 0; the final observation shows Name "held text +1 +2 +3" and Note "first note"; the second type into Note is refused with nothing dispatched and the page logs no input for it; after the restore the frontmost application never becomes Chrome and the page logs no focus or visible event.
Against: any focus or visible page event, or Chrome frontmost, after the restore; either final value differing; any input event logged for the refused type.
Refs: docs/notebook/2026-11-11-browser-holder.md#bh6; python/jevdual/browser_driver.py BrowserBridge.act

## BH8 · update · 2026-11-11 21:27
Resolves: BH7 = failed
Observed: the append put its text at the start of the field: the page logged Name " +1held text" and Footwork's receipt said partial ("not its earlier value plus the insertion"), so nothing claimed success. The type into the empty Note gave exactly "first note". The type into Note while it held text was refused before sending (requires_foreground) and the page logged no input for it. Only one append ran: the Name control has id 0, which the probe treated as missing. The background clauses cannot be assessed: the person's own Chrome was frontmost when the probe started, and the probe records the frontmost application by name, so it neither restored anything nor can tell the two Chromes apart; the page logged a window focus during the type into Note, whose cause the run cannot distinguish (results/browser-holder-20261111/bh7-summary.json).
Inferred: without replace, browser_type focuses the node (DOM.focus) and inserts at the caret that focus leaves (cua-driver-core browser/tools.rs, the browser_type tool), which for this input is the start. So Footwork's append onto a field that holds text was never an append on this route; this predates the holder, and the receipt check catches it only after sending.
Changes: none yet.
Next: deliver an append onto held text as a replacement with the held value plus the text (a foreground step the posture gate refuses in background_only), and refuse it when the held value is truncated or a password; make the probe track the frontmost process by PID and restore by PID; then BH9.
Refs: results/browser-holder-20261111/bh7-summary.json

## BH9 · prediction · 2026-11-11 21:29
Question: through the holder in the background, does typing into an empty field land without the page taking focus, and are both unsafe edits now refused before sending?
Hypothesis: an append onto held text is refused by the bridge before any call (BH8 change); a type into an empty field is insert_text without replace, which does not select the tab; a type into held text is refused by the posture gate. BH7's window focus during the type came from something other than the driver (the person's own Chrome was in front, and the run could not tell the windows apart).
Alternatives: insert_text into an empty field focuses the page's window (BH7's focus event was the driver), which would make background typing a foreground disturbance.
Test: scripts/probe_browser_holder.py --arm held --typing --rounds 3 --spacing 20, fresh profile, port 9466, with the frontmost process sampled and restored by PID.
Predicts: the three appends onto Name are refused with append_unavailable and nothing dispatched; the type into the empty Note lands "first note"; the type into Note holding text is refused with requires_foreground; final values Name "held text" and Note "first note"; the page logs exactly one input event after the restore (the Note text) and no focus or visible event; the frontmost PID is never the owned Chrome's after the restore.
Against: a page focus or visible event after the restore, or the owned Chrome's PID frontmost after the restore; any input event for a refused command; either final value differing.
Refs: docs/notebook/2026-11-11-browser-holder.md#bh8

## BH10 · update · 2026-11-11 21:34
Resolves: BH9 = failed
Observed: all three appends onto Name were refused with append_unavailable and nothing sent; the type into the empty Note landed and its receipt confirmed "first note"; the type into Note holding text was refused with requires_foreground; final values Name "held text", Note "first note"; the holder served one type_text in all. The frontmost PID was never the owned Chrome's after the restore (one change, to another application, 23 s in). The page stayed hidden, but it logged a window focus event at the same instant as the Note input (66.88 s after the restore), and that input was the only one (results/browser-holder-20261111/bh9-summary.json). The sampler's largest gap was 144 ms.
Inferred: the driver's DOM.focus before insert_text gives the occluded page window focus without activating the application, so BH7's focus event was the driver too. The person's keystrokes still go to the frontmost application, so this is not the tab-selection keystroke risk the posture gate guards, but a page that watches focus sees one. The refusals and the empty-field value hold.
Changes: none. Background typing into an empty field stays allowed; its page-visible focus is recorded in the report.
Next: B2, detection of a second DevTools client.
Refs: results/browser-holder-20261111/bh9-summary.json

## BH11 · prediction · 2026-11-11 21:36
Question: does the holder detect a second DevTools client on its browser and refuse to send while it is connected?
Hypothesis: the holder's driver holds the only established client connection to the browser's port; another process opening a websocket to the browser endpoint appears to lsof as a second client end, so the holder's pre-send check sees it and refuses, and passes again once it disconnects.
Alternatives: (a) the driver's own connection is not visible as a client end (for example it uses a pipe or a different port), so the holder refuses every send even alone; (b) lsof misses the second client's connection, so the click goes through; (c) the browser refuses or drops the second connection, so there is nothing to detect.
Test: scripts/probe_browser_holder.py --arm held --second-client, fresh profile, port 9466: after the restore, look and click alone; then a separate process opens a websocket to /json/version's webSocketDebuggerUrl and holds it; look and click; the process exits; look and click again.
Predicts: the first and third clicks land (the page logs two clicks in all); the second click is refused with browser_second_client naming the second process's PID, nothing dispatched, and no page click; the looks all succeed. Not predicted, recorded: whether the browser comes forward when the second client connects.
Against: the first or third click refused; the second click landing or refused for another reason.
Refs: python/jevdual/browser_session_holder.py devtools_clients

## BH12 · update · 2026-11-11 21:38
Resolves: BH11 = held
Observed: the click alone landed and its receipt confirmed it; with a separate process holding a websocket on the browser endpoint (connected 7.7 s after the restore), the next click was refused "browser_second_client: another DevTools client is connected to this browser: Python (pid 9219); nothing was sent" and the page logged no click; after that process exited, the next click landed. The page logged exactly two clicks; every look succeeded; the holder counted one refusal (results/browser-holder-20261111/bh11-summary.json). Unpredicted: the frontmost PID did not change when the second client connected, nor at any point after the restore (sampler largest gap 95 ms).
Inferred: the driver's own connection is a client end lsof attributes to the holder, and another process's connection is visible to it, so detection works on this lane. That a new DevTools connection did not bring this Footwork-launched browser forward is one observation; if it holds, the driver's static background refusal of browser_prepare is broader than this launch needs, which matters only for a session without a holder.
Changes: none.
Next: B3, input bound to the document generation.
Refs: results/browser-holder-20261111/bh11-summary.json
