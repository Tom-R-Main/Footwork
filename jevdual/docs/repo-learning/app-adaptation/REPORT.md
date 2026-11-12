# What Footwork should build next to adapt to unfamiliar applications

Review date: November 11, 2026. Target: local Footwork `0aa1373` on `codex/suno-end-to-end-20261110`.
Revision 6, after six council rounds. Rounds 1 and 2 had four independent reviewers each (Claude Opus
5.5, GPT-6.1 Sol, GPT-6 Astra, Gemini 4 Carbon) and judged revisions 1 and 2 not yet a satisfactory
basis for the decision. Round 3 had one reviewer; the others failed on an exhausted provider quota.
Rounds 4 to 6 had three: Gemini 4 Carbon stayed unavailable and has not seen a revision since the
second. In round 6 all three judged this revision a satisfactory basis for starting the "run now"
steps and committing to the order and gates, with no blockers. Their optional wording points were
applied afterwards and are listed last under Changes; no reviewer has read those edits. Reviewer
agreement is not a behavioural check: nothing here was run.

This is an analysis package. No runtime code, install, desktop action or test was run. Reference
checkouts were read-only. Every reference claim rests on reading source and test definitions. Claims
about the driver Footwork uses were re-read from the vendored archive of the pinned version
(`vendor/cua-driver/native-source.tar.gz`, 0.46.0), because the reference `cua` checkout is not an
ancestor of that pin. The cards' evidence snapshots were taken from the reference checkout; the four
driver files they cite (`capture_registry.rs`, `fast_path/pixel_guard.rs`, `background_input.rs`,
`recovery_hint.rs`) are byte-identical in the archive. Cards and 184 snapshots are in `library/`; the
highest-numbered version of each card is the current one.

## What is and is not established

Established from source:

- Desktop accessibility is a poor primary channel for web content. In the Suno lyrics case the
  accessibility value held 456 characters and 19 line feeds where 461 and 24 were sent, while the
  application's own copy kept all of them (`docs/notebook/2026-11-10-suno-end-to-end.md`, SUN28 to
  SUN30). The setter was sound; the reader was lossy.
- Footwork discards effect information its pinned driver already returns. The driver's page click
  reads the target back and answers `Confirmed` or `Unverifiable` with an escalation
  (`browser/tools.rs:86-190, 1457-1500` in the archive). Footwork's `_effect` maps every reply that is
  not a refusal to `"unverifiable"` (`browser_driver.py:474-492`). The effector's reply cannot say
  whether input was sent (`effectors/base.py:66-68`); the session records every reply that is not a
  refusal as dispatched (`browser_driver.py:359, 491`).
- Footwork calls five of the driver's ten browser tools (`effectors/cua.py:165-195`).
- DemoGeek drove its film with `park` on a native Footwork session for the pointer and its own
  DevTools client for everything else, on port 9333, Footwork's default browser port
  (`best-edit/takes.mjs`, `cdp.mjs`; `browser_driver.py:42`).

Not established: how much of the Suno cost a page channel would have removed. The Suno results file
lists 29 frictions (`results/suno-20261110/report.md:27-57`). Tagged by layer from that table (the
tagging is this review's, not a recount of transcripts):

| Layer | Frictions | Count | Could a page channel change it? |
|---|---|---|---|
| Web content read or driven through accessibility | F1, F3, F8 to F12, F15 to F17, F21, F22 | 12 | Plausibly; untested |
| Native save panels and their windows | F18 to F20, F23, F29 | 5 | Only if downloads are taken at page level; inferred |
| Media decoding and judgment | F5, F13, F25 to F27 | 5 | No |
| Process binding, the person being active, and a guard-provider error | F2, F4, F14 | 3 | No |
| Command semantics and previews | F6, F7 | 2 | No |
| Canvas | F24 | 1 | No; needs coordinates |
| Application knowledge | F28 | 1 | No; a recipe |

So a page channel bears on at most 17 of 29 recorded frictions and plainly not on 12. That is an upper
bound on reach, not a prediction of benefit. The comparison arm in test 7 is the evidence.

## What Footwork has today

- **Routes.** One default route per operation, plus four caller flags that have accumulated
  (`--click-delivery`, `--web-text-delivery`, `--web-text-range`, `--route`; `cli.py:528-543`), and
  automatic fallbacks for same-process keyboard ambiguity, a refused scroll, and making a window key by
  a title-bar click.
- **Receipts.** `confirmed` means a change was seen. Effect-specific records exist and are the
  foundation: `saved`, `field_holds`, `read` (`completion.py:3-12`). A field readback compares after
  `.strip()` without saying so (`native.py:1987`).
- **Application-specific code.** Whole modules (`finder_targets.py`, 360 lines; `app_qualification.py`,
  852 lines) and producers in `native.py`. No recipe loader; `docs/app-extenders.md` records the
  intended boundary.
- **Custody, three rules.**
  - *Ordinary session* (no authority database; the Suno work ran this way, and so does
    `start --browser`). No mutation is blocked after an uncertain action. Completion is: `done` is
    refused while the last input was dispatched and either its effect is not confirmed or partial or
    it carries an error, in this session or a referenced one (`session.py:2838-2872`). Delivery does
    not enter that rule beyond "not refused before sending". The next observation that yields a
    receipt lifts the hold (`session.py:1084-1089`), whatever effect that receipt reports. `do`
    re-observes on its own after the action (`session.py:2629-2632`), so in normal use the hold
    survives only when that observation fails (exit 6, `session.py:2633-2654`). The pending record is
    saved only after the
    action returns (`session.py:2538-2625`); only the durable path writes one before dispatch
    (`session.py:2407-2420`). A process death between the input and that save leaves no record.
  - *Durable native session* (`--authority`). A sent action settles only when its effect is confirmed
    or partial and no error occurred. Every other outcome after a dispatch is `unknown`, including a
    confirmed effect whose delivery is ambiguous. Unknown blocks all mutation in that authority
    database, survives a crash, and clears only through `status --reconcile` from retained runtime
    evidence or a producer admitted in advance. A fresh observation does not clear it and manual
    resolution is refused (`session_operations.py:157-163, 338-363`;
    `docs/durable-native-operator.md:19`). There is no general reconciliation producer for
    application effects (`docs/durable-native-operator.md:63`).
  - *Durable browser session* (the `browser cdp` lane). Stricter: no sent action settles. Every
    acknowledged send is recorded as unverifiable, and a confirmed or partial effect is refused with
    "browser activation cannot establish application completion" (`browser_authority.py:111-124,
    212-215`). The module's stated contract is that neither an acknowledgement nor a changed DOM
    resolves an operation (`browser_authority.py:1-7`; `docs/owned-cdp.md:58-63`).
- **Browser lanes.** A third, read-only Lightpanda lane exists and does not affect the choice.

| | `start --browser` | `browser cdp` |
|---|---|---|
| Chrome | headed, persistent profile signed into once | fresh private profile per launch, headless by default (`effectors/cdp/launch.py:80-88`) |
| Endpoint | fixed `127.0.0.1:9333`; any local client can attach, as DemoGeek's did (`browser_driver.py:42, 136-137`) | ephemeral port, one holder |
| Driver lifetime | created and destroyed per command; refs are lost and the tab is re-found by URL | persistent holder process (`browser_holder.py`) |
| Transport | the driver's browser tools | Footwork's own WebSocket client; no driver tools |
| Actions | click, insert-text typing, navigate | plain `button[type=button]` only; typing disabled "because the focus race is unresolved" (`docs/owned-cdp.md:44-47`) |
| Custody | refuses durable sessions for three missing capabilities (`browser_driver.py:74-91`) | journal; an acknowledged delivery with unverified effect blocks further mutation; no completion reader (`docs/owned-cdp.md:51-63`) |
| Filming | none: browser sessions skip the filmed-pointer setup (`session.py:1524, 1589`) | none |
| Hazards | replacing held text selects the tab for about 100 ms and asks for foreground (`:511-520`); in background posture the trusted input route had zero successes on 2026-09-25 (`:502-507`); values clipped to 200 characters | snapshot collapses whitespace (`effectors/cdp/snapshot.py:145`) |

- **Pinned driver, unused parts.** `browser_click` accepts viewport coordinates on its trusted route;
  `browser_pointer` offers hover, right-click, double-click, scroll and drag at a ref or at
  coordinates. Background mode refuses trusted input where it would activate the window. The driver
  calls focus emulation throughout its input paths, which may or may not have changed the two hazards
  above since the 2026-09-25 probes. The capture registry and pixel guard are in the archive.
- **Not covered by any page channel.** Installed Electron and web-view applications, Safari, Firefox.
- **Dependencies.** Fifteen modules import `browser-use`, including sensitive-field detection in
  `menu.py`; upstream deleted those seams in a 1.0 rewrite.
- **State.** This branch is 160 commits ahead of `origin/main` and 23 behind; the installed release
  `eded45c` has none of the Suno repairs or the pointer records.

## What the reference repositories support

Mechanisms marked "synthesis" are combinations no reference implements.

| Reference | What the source shows | Limit |
|---|---|---|
| Pinned `cua` driver 0.46.0 | Typed effect and escalation per browser action; refs bound to frame and loader identity and re-proven before mutation; exact-or-refused tab binding; single-use captures for coordinate actions | Capture admission checks target, size and expiry, not content. A surface that scrolls itself at the same size is admitted; a repeated grid passes the pixel guard on the wrong cell |
| `agent-desktop` `54855b62` | Typed outcome per rung; the default chain stops on an unverified delivery (`chain_delivery.rs:35-37`); one delivery then bounded re-reads against a predicate | Its right-click chain continues after unverified delivery, guarded by a re-check for an open menu. Its "no effect" is a reading inside a short window, for selection controls only |
| `browser-use` 1.0.2 | Hit-test before dispatch that names the covering element; typed text read back from the target node; zero-opacity text excluded | A mismatch is only reported. A focus check combined with a refusing readback is a synthesis |
| `agent-browser`, `chrome-devtools-mcp`, `playwright` | Document-bound refs; flows that classify a network write as outcome-unknown and keep a ledger | Using write classification to confirm a live click is a synthesis |

No reference keeps per-application knowledge outside core, and none has a visual rung whose effect is
read back.

## Recommendation

**Run now, in parallel. None of these waits for the others or for the lane decision.**

- **A1. Converge and release.** Reconcile this branch, `origin/main` and the coordination work; update
  the installed command; add a version query that lists capabilities.
- **A2. Pre-register the measure and a held-out panel** of about ten browser surfaces with frozen
  tasks, budget and success criteria. Measures: verified completion, human interventions, wrong
  dispatches (target zero), operator time, core mechanisms changed, commits across all layers. Arm
  order alternates across surfaces so learning does not favour the second arm. Decision rule, fixed in
  advance: with the panel fixed at ten surfaces, a one-sided sign test on interventions, which passes at
  9 of 10 surfaces favouring the page
  arm (p ≈ 0.011) and fails at 8 of 10 (p ≈ 0.055). A tie counts as not favouring the page arm. That
  pushes the panel toward surfaces where the accessibility route is known to need help, so a pass
  says the page arm is better there, not everywhere. The panel is a coverage choice. It is not a
  random sample of applications and supports no population failure-rate claim.
- **A3. Three prerequisite checks**, tests 1 to 3: sign-in, node text, focus.
- **A4. Stop discarding the driver's effect.** Carry `Confirmed`, `Unverifiable` and the escalation
  through `_effect`. A driver `Confirmed` says the target's state differed before and after the
  action, whatever caused the difference (`browser/tools.rs:115-178` in the archive). It does not
  settle the business effect, which stays with the completion readers. On an ordinary session this
  gives browser actions the rule native actions already have: a confirmed driver effect leaves no
  pending uncertainty at `done` (`session.py:2496-2540, 2838-2845`). Because `do` re-observes at
  once, that difference shows at `done` only when the post-action observation fails; most of the
  value is in the record and the receipt. It changes nothing on a durable
  browser session, where a changed DOM settles nothing. It applies to the default page-click route
  only: the driver's trusted click returns no effect readback (`browser/tools.rs:1645-1658`), so
  `--route trusted` and the coordinate clicks in step E stay unverifiable and are settled by
  re-observation. One correction to make alongside: the `--route` help text says the default is
  trusted (`cli.py:539-542`), while the bridge defaults to the page route (`browser_driver.py:508`).

**Then, in order.**

- **B. Choose one browser lane and close its gaps.** Recommended (opinion): grow `start --browser`,
  because sign-in and the driver's tool set need the headed persistent profile. This is most of the
  work, not wiring. Deliverables:
  1. a persistent holder around the driver, as the CDP lane has, so refs and tab identity survive
     between commands;
  2. an exclusive endpoint, or detection and refusal when a second client attaches. An ephemeral
     port removes the hard-coded collision and looks compatible with the driver, which finds the
     endpoint from the profile's `DevToolsActivePort` file (`platform-macos/src/browser/platform.rs:785-819`
     in the archive; inferred, not run). It is not exclusive: any local process can read that file.
     Exclusion needs a pipe, which is unchecked, or detection;
  3. input bound to the document generation, using the driver's frame and loader identity;
  4. a qualified delivery record. The driver's action record carries `actual_delivery`
     (`action_record.rs:45-56`), which names the route used, not proof that input arrived; for a
     page click it is the constant `Background` (`browser/tools.rs:165-170`). Whether any reply can
     fill "sent" is unchecked;
  5. enrolment under the existing durable browser rule, unchanged, which this lane lacks;
  6. a sign-in handoff with capture paused;
  7. one session that binds both the native filmed pointer and the page to the same window, since
     browser sessions have no filmed pointer today.
  Items 1, 2, 3, 6 and 7 are what step D needs on ordinary sessions. Items 4 and 5 are the durable
  enrolment; step D does not wait for them.
  An eighth, optional item follows from the owner's ruling: opt-in attachment to the person's own
  Chrome (see "The product rule").
  Reopen the choice if test 1 fails on both the launched profile and the person's own Chrome, if
  item 2 has no solution on this lane, or if test 3 shows that both text replacement and coordinate
  input need the foreground.
- **C. Fix the outcome contract before widening.** This step weakens none of the three custody
  rules and adds one thing to the ordinary one. Delivery is not sent, sent or unknown. Effect is
  confirmed, absent at the declared bound, or unreadable. Absent at the bound is not a refutation: a
  silent no-op and a late effect look the same.

| Outcome | Ordinary session | Durable native session | Durable browser session |
|---|---|---|---|
| **Not sent** | another rung may be tried | final and released; another rung may be tried | final and released, on a retained qualified refusal or a recovered prepared-only record; another rung may be tried |
| **Sent; effect confirmed or partial; no error** | recorded; `done` is not held; a business effect still needs its reader | final; applied or partial | unknown and blocked: a browser activation cannot establish completion |
| **Sent; effect absent at the bound or unreadable, or any error** | reported unknown; no further automatic dispatch; `done` is refused until the action is re-observed | unknown; all mutation in the domain blocked; survives a crash; cleared only by qualified reconciliation | unknown and blocked, as above |
| **Delivery unknown, any effect** | delivery does not enter the ordinary rule: judged by effect and error, as in the two rows above | unknown and blocked, even when the effect reads confirmed | unknown and blocked |

  On an ordinary session an acknowledged browser reply counts as sent (`browser_driver.py:359`).
  Delivery is unknown there after a lost reply or an exception that carries no qualified evidence
  of no-send, which the session records as unverifiable with an error (`session.py:2521-2524`), so
  it falls in the third row. An exception that says nothing was sent is kept as not sent.

  What changes: the `start --browser` lane reports in these terms; another rung is tried only when
  nothing was sent; and the driver's escalation advice is carried for diagnosis only, as `next_call`
  already is (`effectors/base.py:62-64`). For a page click whose target did not change the driver
  advises `retry_with_page_action` (`browser/tools.rs:181-190`); offered as a next step on a
  click-toggle, that is the second click that flips it back.

  The one addition (opinion): save the pending record before dispatch on ordinary sessions, as the
  durable path does. Today a process death mid-action leaves an ordinary session with no record that
  anything was sent, so nothing holds `done` and nothing warns the caller. Step D widens on ordinary
  sessions, so that gap should close first. It strengthens the ordinary rule and touches neither
  durable rule.

  What does not change, and what that costs:
  - The driver's `Confirmed` is a changed-DOM reading, which the durable browser rule already says
    settles nothing. This plan does not ask for that to change.
  - So a durable browser session is one guarded action with a crash memory: it stops at the first
    sent action. Its use is a single action that must not be sent twice, such as a submission that
    spends credits. Durable multi-step browser work needs a completion reader that binds evidence
    independent of the page to the admitted operation, as the owned ticket producer does for the
    native lane (`docs/durable-native-operator.md:45-63`). That reader is outside this plan.
  - Widening in step D therefore happens on ordinary sessions, under their existing completion gate.

  An owner ruling could relax the durable browser rule so that a declared postcondition read from the
  page settles an operation. Not recommended here (opinion): a page reading is not independent of the
  page. If that ruling is made, the fifth case of test 4 must be re-registered first.

  Re-applying an absolute setter after an unknown outcome (one whose mechanism yields the same state
  whether or not the earlier application lands late) is a possible later extension with its own test.
  Click-toggles, inserts, presses and submissions are never repeat-safe.
- **D. Widen the page channel on the chosen lane, for browser applications only.** Typing with a raw
  multiline readback and a declared equivalence; hit-test refusal with the cover named; file inputs,
  select and dialogs through the driver; targeting by name or selector with a visibility reason;
  waits. For DemoGeek, the primitives its take script uses: pointer travel to a page-resolved
  rectangle, typing paced one character at a time, rectangles for a text range, selecting a text
  range and typing over it (replacing held text, so a foreground step until test 3 shows otherwise),
  paced scrolling of the container that holds a target, window bounds as a parameter, page
  screenshots; and a stated record of target and result rectangles on the recorder's
  clock with uncertainty intervals, invalidated when layout changes
  (`demogeek/design/FILM-DIRECTION.md:75-81`).
- **E. Coordinates.** Web canvases use the driver's `browser_click` (single click) and
  `browser_pointer` (drag, hover, double-click) at viewport coordinates. Treat this as a foreground
  step until test 3 shows otherwise. A bound tab identifies the document, not what sits at a point
  after a scroll or redraw, so the admission policy in test 5 applies to web and screen coordinates
  alike. A capture identity records where a point came from, nothing more.
- **F. One small recipe during D**, to find the contract by use. A recipe states assumptions under
  which a result is checkable and supplies no evidence itself. The framework waits.

**Not addressed.** Electron and other installed web-view applications stay on the accessibility route
with the controlled clipboard verifier. Element-targeted key delivery for sliders remains open.
Retiring `browser-use` waits until the replacement passes the panel.

**Alternative considered.** A narrow page adapter beside the existing native core against a general
ladder across all channels. Steps A to D are the narrow version; no general ladder is proposed.

## The product rule

The standing rule: the shipped product may require only operating-system permission grants, never
configuration of a separate application. Owner ruling, 2026-11-11: attaching to the person's own
Chrome is fine when the user wants that. The rule is about what the product requires, not what a
user may choose.

| Route | What the user does | Status |
|---|---|---|
| Footwork-launched profile | signs in to the site being driven, once, in a window the product opens | Default. Within the rule: authentication to the target, not configuration of another application |
| The person's own Chrome | switches on remote debugging in their browser, approves a prompt; an automation banner shows | Allowed as an opt-in the user chooses (owner ruling). Never required |
| Browser extension | installs an extension into their browser | Not ruled, and not proposed. See below |

Consequences of the ruling. Own-Chrome attachment becomes an opt-in variant of the chosen lane,
through the driver's existing-profile strategy, which Footwork's `prepare` already names
(`effectors/cua.py:165-195`); that the consent flow works end to end is unchecked. It needs no
sign-in handoff. It makes endpoint exclusion (B2) harder, not easier: while the switch is on, the
person's whole browser, every tab and profile, is reachable by any local client. If test 1 fails for
a site, this route is the fallback for that site, and the lane choice is reopened only if both fail.

When an extension would come up. Only to reach the person's own Chrome where attachment is
unavailable or too broad (inferred from reading one reference, Playwright's `packages/extension`:
manifest version 3; permissions `debugger`, `activeTab`, `tabs`, `tabGroups`; all hosts; installed
from the Chrome Web Store; "connect to pages in your existing browser"):

- remote debugging is switched off by policy on a managed machine, or the browser build has no
  in-browser switch for it;
- the person wants to share one tab, not the whole browser: an extension can scope consent to the
  active tab, which attachment cannot;
- a Chromium browser other than Chrome that lacks the switch.

It is not needed for the Footwork-launched profile, and it is the clearest case of configuring a
separate application. Recommendation (opinion): build none now; revisit only if a user who wants
own-Chrome attachment cannot have it.

Residual dependency on the first route: Chrome must be installed unless the product ships its own
Chromium.

## Mathematics that changes what gets built

- **Round-trip laws.** Setting a value and reading it back must return it (PutGet); quotient lenses
  state the law up to a declared equivalence. Consequence: a receipt says "equal" or names the
  equivalence, and the silent `.strip()` and whitespace collapsing become declared canonizers. Probes
  are counterexample searches on disposable fixtures: they can refute a reader and never certify one.
  Pairs to try: whitespace-only differences, a trailing line feed, blank lines, length past the
  preview cap, composed against decomposed Unicode.
- **Three-valued verification.** For a finite observation the verdicts are true, false and
  inconclusive. "Absent at the bound" is inconclusive, which is why no row of the table in step C
  licenses a second dispatch after a send. A recipe's assumption makes a conclusion conditional; it
  does not establish it.
- **A pre-registered sign test** fixes the panel's decision rule in A2.

Sources: Foster et al., "Combinators for bidirectional tree transformations", ACM TOPLAS 2007,
doi:10.1145/1232420.1232424; Foster, Pilkiewicz and Pierce, "Quotient lenses", 2008,
doi:10.1145/1411203.1411257; Bauer, Leucker and Schallhart, "Runtime Verification for LTL and TLTL",
ACM TOSEM 2011, doi:10.1145/2000799.2000800; Cimatti, Tian and Tonetta, "Assumption-Based Runtime
Verification with Partial Observability and Resets", 2019, doi:10.1007/978-3-030-32079-9_10. Read at
abstract and excerpt level, not in full.

Removed after review: automata learning, sheaves, conformal calibration, and the binomial bound as a
reliability claim.

## Tests that would falsify this

Each prediction must be committed to the notebook before its test runs.

1. **Sign-in.** A Footwork-launched profile signs in to Suno and to one site using Google sign-in,
   and the session survives a browser restart and one token renewal. Against: sign-in is blocked for a
   debugging profile, or needs manual steps each run.
2. **Node text.** In that profile, open the song holding the verified lyrics; compare node inner text,
   the application's copy and the accessibility value with the 461-character file. Predicts inner text
   maps to the file under one declared equivalence. Against: characters are lost or no fixed mapping
   exists; then the clipboard stays the verifier.
3. **Focus.** On the pinned driver, with synthetic keystrokes running in another window: replace held
   text, and deliver a trusted click at viewport coordinates, both in background posture. Hypothesis:
   focus emulation removed the tab selection and the trusted route now lands. Against: a visibility
   change, a stray key in the agent's tab, or a no-op; then that operation is a foreground step.
4. **No second dispatch, and custody no weaker than today.** Five cases: (a) a click-toggle whose
   effect lands after the bound; (b) an action whose reply is lost; (c) one acknowledged with an
   unreadable effect; (d) a process death between the input and its saved result; (e) a page click
   whose driver readback is `Confirmed`. Predicts exactly one dispatch in each.
   - Durable browser session: all five leave the operation unknown, the next mutation in the domain
     is refused, a fresh observation does not clear it, and it survives the restart.
   - Ordinary session, run with the post-action observation made unavailable, because otherwise
     `do` re-observes at once and the gate is never exercised: (a), (b) and (c) are reported unknown,
     there is no further automatic dispatch, and `done` stops at the custody gate (exit 5) until an
     observation yields a receipt, which lifts the hold as designed. (e) is recorded as confirmed
     and passes the custody gate, although its delivery is unqualified. (d) is run twice: on the
     current build it predicts no retained record and the custody gate passed, which is the gap;
     with the pending record saved before dispatch it predicts exit 5. Passing the custody gate
     only lets completion verification proceed; the verifier's own verdict is not scored here.
   Against: a second dispatch anywhere. On a durable session, a mutation admitted past the barrier,
   an unknown cleared by observation, or (e) settling the operation. On an ordinary session, the
   custody gate passed over unsettled input in (a) to (c), or in (d) after the change.
5. **Coordinate admission**, run on a web canvas and on a native surface: one that scrolls itself
   without resizing, and a repeated grid shifted by one cell. Predicts capture or tab identity alone
   admits both, and the added freshness and ambiguity policy refuses both. Against: the policy admits
   either.
6. **DemoGeek acceptance.** Re-express `best-edit/takes.mjs` as Footwork commands. Predicts every step
   runs with a receipt and no raw DevTools call, and that a second client attaching during a held
   operation is refused or detected. Against: any step still needs the private client, or the second
   client goes unnoticed.
7. **Panel**, as pre-registered in A2, with the current accessibility route as the comparison arm.
   Predicts the sign test passes, with zero wrong dispatches and no core mechanism change on the page
   arm. Against: the test fails, or a core change is needed for an application quirk.

## First results, 2026-11-11

Run after the review, on an owned local fixture in an isolated Footwork-launched Chrome 157 with the
pinned driver (`docs/notebook/2026-11-11-app-adaptation.md`, `results/page-effects-20261111/`). Not
reviewed.

- **A4 is done.** The driver's typed result reaches Footwork: a page-route click on a checkbox reads
  back `confirmed` with its evidence, and one on a control with no handler reads `unverifiable` with
  an escalation. `_effect` now carries it (AAD1 held; 3440 tests pass).
- **Attaching is a foreground step.** With the browser in the background the driver refuses
  `browser_prepare` with `background_unavailable`: a new DevTools connection makes Chrome come
  forward for its "Allow remote debugging?" prompt, unless the window is on another Space. Footwork
  opens a new connection for every command. So the persistent holder (B1) is a precondition for
  background page work, and the launched profile and the person's own Chrome reach the page through
  the same consent mechanism. This was not in the review.
- **Test 3, held-text replacement: still disturbs the page.** An occluded page becomes visible and
  focused for 107 to 135 ms during the call, as on 2026-09-25. The browser did not become the
  frontmost application (sampled at under 40 ms). Whether a real keystroke can land in that interval
  is not shown. The posture gate stays (AAD4 inconclusive, AAD6 failed).
- **Test 3, trusted click at coordinates: lands in the background**, three of three, with the page
  visible for 31 to 37 ms and the frontmost application unchanged. Step E's "foreground step until
  test 3 shows otherwise" can be dropped for single clicks, subject to the admission policy in test 5.
- **Two defects found on the way.** Binding failed twice in seven launches with "owned Chrome identity
  changed": the window-recovery helper, which carries no debugging port, appears to win the profile
  singleton from a slow first launch. And launching the browser takes the foreground in the default
  background posture.

- **Test 1, sign-in: holds.** In a fresh profile launched with Footwork's arguments and a debugging
  port, sign-in to Suno, Notion and Google worked, and survived a restart and an hour with the tabs
  open (AAD7). Not tested in DemoGeek's default profile, by the owner's decision.
- **Test 2, node text: innerText is not a faithful reader.** With the verified lyrics entered by
  DevTools input, Suno's counter read 461, but innerText doubled the breaks between paragraphs (490
  characters, 53 line feeds) and textContent dropped them. Joining the editor's paragraphs with one
  line feed reproduced the file byte for byte; that reading was found after the data and needs a
  second rich editor before step D relies on it (AAD10, AAD11). A synthetic paste was ignored.
- **A1: converged and released.** PR #24 merges main; the release from its head passed 20 live
  criteria and is active, with `eded45c` kept for rollback. Its largest posting gap was 47.8 ms of
  the 50 ms limit (`results/converge-release-20261111/REPORT.md`).
- **A2: the panel is frozen** (AAD9): ten of the owner's own sites, each with a task that sends
  nothing. It runs once step D exists.

Neither reopening condition for the lane is met: text replacement needs care, coordinate input does
not need the foreground, and sign-in works in a launched profile.

## Limits of this review

No reference test was run. The friction tagging above is this review's reading of one results table.
Rounds 3 to 6 were partial: one of the four models has not seen a revision since the second. The
wording edits made after round 6 have not been reviewed.
Unchecked: whether the driver's existing-profile attachment can use an exclusive endpoint; whether its
replies report delivery; the `jev-for-chrome` and Playwright extension bridges; the browser-harness
under `browser-use` 1.0. Two reference claims come from single reviewers and were not rechecked
(`agent-desktop`'s headed click order; `browser-use`'s main-world typing).

## Changes

Revision 2 (after round 1): removed the claim that page-level input needs no focus; named the browser
lanes and a choice; replaced the ladder rule; moved measurement and prerequisite checks to the front;
re-read driver claims from the pinned archive; scoped the page channel to browser applications; added
the product-rule table and the DemoGeek contract; cut the mathematics.

Revision 3 (after round 2):

- Step C now has the nine-cell table. Absent at the bound is unknown, nothing advances automatically
  after a send, and the barrier for sent with unreadable effect is kept.
- Step B lists its real deliverables: persistent holder, exclusive endpoint, crash-durable barrier,
  and a session joining the filmed pointer to the page. "As today" was wrong for this lane.
- Step E names the right driver tools, treats web coordinates as a foreground step until tested, and
  applies the admission policy to web coordinates too.
- Test 6 targets DemoGeek's take script, and step D lists the primitives it uses.
- The panel has an arm order and a decision rule; the population bound is withdrawn.
- Added the friction-by-layer table from the Suno results file, the endpoint and lifetime rows in the
  lane table, and the provenance of the cards' driver evidence.

Revision 4 (after the one completed review of round 3):

- Step C no longer invents a custody level between the two that exist. Its table now sets ordinary
  and durable sessions side by side and keeps the durable rule unchanged. Revision 3's table let a
  sent action with an absent effect pass without a block, cleared a sent-and-unreadable outcome by
  re-observation, and let unknown delivery proceed when the effect read confirmed; each was weaker
  than `session_operations.py:338-349` and `docs/owned-cdp.md:39-58`.
- The driver's escalation advice is diagnosis only. Test 4 predicts a durable block in all four cases.
- Step C names what it costs: a durable browser session stops at the first unconfirmed effect because
  no general reconciliation producer exists, and whether the driver's `Confirmed` may settle a durable
  operation is a decision to make.
- Step D adds selecting and typing over a text range and paced container scrolling, both used by
  DemoGeek's take script (`takes.mjs:31-35, 123, 146-147`).
- B2 says an ephemeral port is not exclusive; B4 notes the driver's `actual_delivery` field; A2 says
  how ties count and what that does to the panel.

Revision 5 (after round 4, three of four reviewers):

- Step C described two custody levels; there are three rules, and two were misdescribed. Ordinary
  sessions block no mutation but do refuse `done` over unsettled input (`session.py:2838-2872`). The
  durable browser rule is stricter than the native one: no sent action settles, and a changed DOM
  settles nothing (`browser_authority.py:1-7, 111-124, 212-215`). Revision 4 filed the browser lane
  under the native rule and offered, as an opinion, that the driver's `Confirmed` might settle a
  durable operation; that would have relaxed an existing rule while claiming to weaken none.
- The table has a column per rule. The cost is stated plainly: a durable browser session stops at
  the first sent action, and widening happens on ordinary sessions.
- Test 4 gains a fifth case (driver readback `Confirmed`) and the ordinary completion gate.
- A4 says what carrying the driver's effect changes on ordinary sessions and that it changes nothing
  on durable browser sessions. Step B says which deliverables step D waits for.
- F14 is a guard-provider error, not media; the counts of 17 and 12 are unchanged. The panel is fixed
  at ten surfaces. One line reference corrected.

Revision 6 (after round 5, three of four reviewers):

- The ordinary column of step C's table contradicted step A4. The ordinary completion gate keys on
  effect and error, not delivery, so an error-free confirmed effect is not held whatever is known
  about delivery (`session.py:2838-2845`). The table now says so.
- Test 4 predicted that an ordinary session refuses `done` after a restart mid-action. It cannot: the
  pending record is saved only after the action returns. The gap is now stated, step C proposes
  saving the record before dispatch on ordinary sessions, and the case is run before and after.
  "Cleared by observation" counts against the prediction on durable sessions only.
- "Delivery is recorded as unknown for every driver reply" was true of the effector's reply, not of
  the session, which records every reply that is not a refusal as dispatched.
- A4 says its benefit reaches the default page-click route only, and notes a help text that names the
  wrong default route. The durable browser "not sent" cell includes recovery of a prepared-only
  record.

After round 6 (three of three satisfied; optional points applied, not re-reviewed):

- The custody description and A4 say that `do` re-observes on its own, so the ordinary completion
  hold survives in normal use only when that observation fails.
- Test 4's ordinary cases run with the post-action observation unavailable, and are scored at the
  custody gate (exit 5 or not), not at the verifier's verdict.
- "No further automatic dispatch" replaces "sends nothing further" in the ordinary column, and the
  exception wording keeps an exception's explicit no-send.

After the owner's ruling (2026-11-11, not reviewed): attaching to the person's own Chrome is allowed
as an opt-in; the product-rule section, step B and its reopening condition say so, and the section
says when an extension would come up.
