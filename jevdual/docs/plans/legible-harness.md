# Plan: one legible harness for browser and computer use

Written 2026-09-25 after Q11 (`results/q11-live-dev.md`). Companion to
`docs/plans/native-computer-use.md`, which it does not replace: the native phases P5 onward fold
into the phases below. Every phase that measures anything is a pre-registered Q under
`docs/experiments/` with the program's ground rules (numbers cite a run dir, amendments dated,
heldout never debugged).

## Goal

The same dual-process loop drives a web page through the DOM and a desktop app through the
accessibility tree with one contract, one authorization boundary, one receipt for every action,
and one verifier reading the same trajectory evidence, so that the agent never infers what the
harness already knows. The objective is the Legible Loop's: less avoidable driver work per unit of
progress, at no loss of verified completions and no effect beyond granted authority.

## What Q11 established

- Declaring the guard's contract raised driver requests 21% per task with completions unchanged.
  The cost was not deliberation. It was a click that changes nothing: the silent driver escaped to
  `evaluate` and the gate ended the run; the declared driver, told `evaluate` pauses, ground to the
  step cap. Both are failures; the count only favoured the one that died sooner.
- The harness knew. `jevdual.effects.diff` computes every step's effect (URL, title, elements
  added and removed, text ratio) and the arbiter and the delegation tool already act on
  `no_effect`; System 2 is told "Clicked". The native path returns the driver's receipt
  (confirmed, partial, unverifiable, suspected_noop, refused) on every action and the verifier reads
  it on the trajectory line.
- A requirements list in the system message makes the driver recite requirements in its done
  text, which the claim check then refuses. Declarations of what will be checked need a matching
  declaration of how the done text is read.
- Burden must be measured per unit of progress and by how the run ended, or a control that kills
  runs early looks efficient.

## Where the two backends disagree today

| the harness must | browser (DOM, browser-use) | native (Cua Driver) | closes in |
|---|---|---|---|
| return a receipt for every action | no: "Clicked" regardless | yes: driver effect words | Q12 |
| put the receipt on the verifier's trajectory line | labels only | labels, chords, text, effect | Q12 |
| declare the requirements it will check | no (Q11's arms, not adopted) | yes (`desktop_s2` prompt) | Q11b |
| pause when the destructive judgment fails | no: keyword fallback | yes: `Authorizer` | P2 below |
| stop a repeated no-effect sequence | arbiter rule for S1 only | not yet | Q12 / native rule |
| verify a save or submit from readback | URL or page text | none for hotkeys | native readback |
| carry secrets by placeholder | yes | yes | done |
| calibrated System 1 on the menu | Q1 | Q10 (AUROC 0.90) | done |

The table is the conformance manifest: each row is a rule, each cell a test that either exists or
is named by the phase that adds it. Rows are added only with a test.

## The operator's experience (added 2026-09-25)

A second agent experience sits above the driver's: an operator (a person, or another agent such as
a Claude Code session) pointing jevdual at a real job. One such session tried to drive Chrome to
the Apple developer portal through `scripts/spike_native.py` on 2026-09-25 and reported what it
met. Its findings, verbatim in substance, each with the phase that answers it:

| finding | answer | phase |
|---|---|---|
| no way to just give it a task: eight steps of reading code before a runnable command | a `footwork run --app <App> "<task>"` entry point with defaults (guarded arm, receipts, trace, screenshots) | P0 |
| the native menu carries duplicates and unnamed items (two "New Tab", two `button 'button'`) | dedupe by role, label and frame; drop unnamed controls unless they carry an identifier hint | P0, P4 |
| no way to open a URL in native mode: the address bar has to be driven through the menu | a `navigate` operation on the native backend (Chrome and Safari open a URL from the menu bar or AppleScript, verified by the window title) | P0 |
| no way to pre-authorize the one approved change: `authorize.py` exists, the script ignores it, so every save pauses | `--authorize "<label>"` on the entry point, the same scoped authorization the runner gives tasks | P0 |
| a sign-in prompt ends the run as "paused"; there is no hand-back-and-resume | the pause returns a resumable run: the operator does the sign-in, the run continues from its ledger and trace (delivery custody, in the Legible Loop's terms) | P0 |
| the JSONL log has no screenshots, so the operator cannot show what it saw | a screenshot per step beside the trace, redacted like the trace | P0 |
| web pages read through the accessibility tree are thinner than the DOM, and the browser backend opens its own unsigned-in browser | P6 decides which input path the browser gets; until then the entry point can attach the DOM backend to a signed-in Chrome profile | P6 |

**P0, the operator surface.** These are not experiments; none needs a Q. They are the product-side
half of the Legible Loop's rule, applied to the person or agent holding the harness: do not make
the operator infer what the harness could declare. P0 is scheduled before P3 so that Q11b and Q13
run through the same entry point an operator would use.

### Driving it myself (2026-09-25, the same job, timed)

The operator's agent experience was measured by driving the Apple portal job by hand, one command at
a time, fixing each piece of friction as it came. What the harness hid before, in the order it was
found (each fix is in the commit that adds this section):

| what happened | seconds lost | fix |
|---|---|---|
| the verifier refused a correct done on the App ID page: `page_text` held 128 chars of a page showing the Team ID | two refusals, the run ended "s2 fatal" with the answer discarded | Chrome's markdown lines end in `[actions=[...]]`; the end-anchored static-text regex captured nothing on any web page. Fixed; the same page now yields 6,000 chars with the Team ID in it |
| the answer System 2 found was never printed: the run reported "done refused 2 times" and nothing else | the whole run | a refused done keeps its text (`NativeRun.answer`, marked unverified with the verifier's reason) and the trace carries it as a proposal |
| Chrome offered 296 candidates including 27 identical "More actions" and `button 'button'`; Jev refused the request twice per step as too large | about 1 s per step | dedupe by (role, label, value, section), drop unnamed non-text controls, cap at 160 |
| no way to open a URL: the address bar had to be found and driven by hand | 4 s by AppleScript, which then hit the wrong process (below) | `navigate_in_window` through the bound window; `--url` on `start` |
| AppleScript's `tell application "Google Chrome"` addressed a second Chrome process (pid 10143) whose windows the Driver never lists; the Driver lists one pid per bundle (18365) | two runs of 109 s and 183 s against the wrong window, with System 2 hunting for a tab it could not reach | bind by the Driver's own window list; refuse to run when the bound window's address bar does not show the URL's host |
| the Driver's window titles lag Chrome's tab switches (a window listed under its YouTube title while showing the Apple portal) | mis-binding by title | never bind by title; confirm from the snapshot |
| a scroll on a list with no frame was "refused" and cost a 6.7 s System 2 call | 7 s | Page Down fallback |
| no screenshots, so what the models saw at each step could not be checked | the diagnosis above took the screenshots to make | one PNG per observation beside the trace |
| a background key press is refused when the process owns other windows (`same_pid_keyboard_ambiguity`) and the driver's message says so; System 2 was left to discover the foreground route | one wasted step per key | key and enter fall back to the foreground route on that refusal |
| the session drove the person's active window; the active tab changed twice between two commands | a lost run | `start --url` opens the session its own window (Command-N through the bound window) and warns when the window changed since the last look |
| Muse as System 2 took 4 to 25 s per step and chose Down-arrow four times against an unverifiable effect | 60 s of a 109 s run | System 2 is whoever drives: `footwork start / look / s1 / do / done`, each action through the boundary with a receipt (the effect diff) printed next to the fresh observation |

**The limit reached.** With the person active in the same Chrome process, the Driver refuses
background keyboard input (it cannot prove which window a process-scoped key event reaches) and
the foreground route fails because the session window cannot become key ("exact target window did
not become focused"). Clicks by element token still work in the background, so a page can be driven
by clicks, but a URL cannot be typed and submitted. The Driver's browser mode (`browser_prepare`,
`get_browser_state`, `browser_navigate`, `browser_click`, `browser_type` over a DevTools endpoint)
exists for this and is P6's subject: a browser the Driver launches with a profile the person signs
into once, or the person's Chrome started with the existing-profile grant. Until then, browser jobs
through the accessibility route run in a window the person is not using and navigate by clicks, or
run when the person is away from the keyboard.

**Second batch, me as System 2 (2026-09-25, later the same day).**

| task | commands | wall | outcome |
|---|---|---|---|
| Calculator, 48 × 13 | start; `s1 --act` × 6; done "624" | 30 s | verifier accept p=0.98; every click a `confirmed` receipt with the display value in it; S1 proposed every step at p ≥ 0.94 and I only had to say done |
| TextEdit, append a line and save | start; `do append 1 "Second line."`; `do hotkey cmd s`; done | 9 s | file on disk verified; the receipt on Command-S read `confirmed (text changed)` from the window title losing its edited mark, the readback the Q10b append task lacked; verifier accept p=0.95 |
| Chrome, open a bookmark and report the heading | start; s1; `do click 16`; done | 15 s | the bookmark opened the Siftable app; S1 proposed the bookmark at p=1.00; verifier `verify` band (0.63) because my requirement said "the ExecuFunction page" and the page says Siftable, which is the right refusal |
| Chrome, click through to Knowledge | `do click 37` | 6 s | the page had changed under me (an overlay opened; 118 elements gone) and the guard let the click through to the element that now held id 37, a harmless no-op: the guard compared against the fresh observation, not the one I chose from. Fixed, nothing dispatches on a changed id and the fresh observation is printed instead |

Three bugs found by driving, none by the test suite: `Decision` has no `text` attribute (s1 --act crashed); an installed-but-not-running app surfaced as a Driver window-discovery error (now "installed but not running; open it first"); the staleness guard above. The person used both Chrome windows during the batch (the session window ended on YouTube), which is the sharing limit named above, not a harness fault: a session on a person's live desktop needs its own app instance or the person's absence.

**What a command costs now.** `start` 10 to 13 s (driver, new window, navigate, first observation
with screenshot); `look` 1 s; `do` 4 to 6 s (observe, dispatch, settle 1 to 3 s, reobserve); `s1`
about 2 s (one Jev call); `done` about 2 s (one verifier call). The Driver process starts fresh per
command at no visible cost.

## Phases

**P1. Q12, receipts.** Build: `jevdual.receipts` with one frozen `Receipt(action, label, route,
effect, evidence)` whose `effect` is the native driver's five words; the browser side is built from
`effects.diff` on the post-step state, computed on every System 2 step including the guarded arm.
Three deliveries: the driver's action result text ("Clicked 'Add to cart': no change, same URL, 0
elements added, text identical") replacing browser-use's wording; the trajectory line the verifier
reads (`click(Add to cart) -> suspected_noop`); the arbiter's repeat rule, unchanged. Arms `guarded`
and `guarded_receipts`, enforcement identical, three live-dev runs. Pre-registered predictions: on
saucedemo the step-cap runs become early informed stops or a changed route and requests per verified
pass fall; outside saucedemo nothing moves; `evaluate` pauses do not rise. Guardrails as Q11. New
measures, pre-registered in Q12 and added to `evals.paired`: `terminal_mode` (verified, unverified,
paused, cap, error) and requests per checkpoint reached. Cost: about one build day, then three runs
at Q11's price.

**P2. Q12b, the input defect, and the boundary parity.** Fix the trusted-input loss after
navigation (exf 9b9916a6, reproduced in `scripts/diag_trusted_input.py`) and re-run the saucedemo
tasks under the receipt arm; the fix is measured as a burden drop that receipts made visible. In the
same commit the browser `_destructive_judgment` fallback becomes a pause, matching the native
`Authorizer`, with a test that reproduces the audit's probe (judgment raises, nothing dispatches).
Reported, not measured: it affects every arm equally.

**P3. Q11b, the narrower declaration.** Requirements only, no gate text, plus one sentence that the
done text is checked against the page and should state only what it shows. Q11's rows give the
prediction: the Wikipedia-chain and docs gain stays (verified passes up outside saucedemo), the
narrative refusals go (no-fact refusals back to the guarded rate), requests unchanged now that
receipts exist. Runs only after P1, because without receipts removing the `evaluate` sentence
reverts to dying on a pause.

**P4. Native receipts complete.** The save with readback (window title or Edited indicator in the
end state, file mtime as an observation) so the append task's "saved" requirement can be met; the
repeated-sequence rule as the native form of the no-effect rule, measured alone on calc-percent;
identifier hints for unlabelled controls in the menu builder. Then tranche 2, the consent classes,
pre-registered as a Q10 amendment. These are `native-computer-use.md` P5 and the Q10b decision list,
unchanged in order.

**P5. Q13, one contract across two surfaces.** Five tasks that start on one surface and end on the
other: look a value up in the browser and paste it into TextEdit and save; download a file and open
it; read a number from Calculator and enter it in a form. A session that holds both bridges, System
2's closed action set gains `switch_surface`, and the contract, ledger and receipts must survive the
crossing. Oracles first, verifier probe second (Q10b stage 1), then arms. The predicate is end state
on the second surface. No measured claim before all five oracles pass.

**P6. Q14, the browser through the accessibility tree.** Run the live-dev tasks against Chrome via
the Cua Driver instead of CDP, same tasks, same arms, and pair against the DOM path. Q10 showed the
arbiter's calibration transfers between menu kinds. If the no-op clicks vanish under accessibility
input, the defect is browser-use's and the native backend becomes the one input path, the DOM menu
an enrichment. If they persist, it is the sites. Either answer decides whether jevdual keeps two
drivers.

**P7. The AX measurement layer.** `evals.taxonomy` already classifies trajectories; it gains the
terminal-mode split and requests-per-checkpoint from P1, plus the paired-ablation method from the
Legible Loop AX spec (`~/Documents/Codex/2026-09-24/aud/outputs/legible-loop-ax-measurement-spec.md`):
avoidable burden is the paired difference between arms, never an annotator's counterfactual. The ten
AX cases map onto Qs: unknown outcomes is Q12, preconditions is Q11b, verification receipts is P4's
readback. The Legible Loop v6 text is generated from this table and the Q results, not written
first.

## Order and cost

P1, P2, P3 in that order (each about one build day and three live-dev runs; a run is four hours and
about $1.30). P4 runs alongside on the native split at cents per run. P5 needs P1 and P4. P6 is
independent and can start once P1's receipt type exists. P7 accrues from P1 onward. The three human
audit sheets (`results/annotation/audit-sheet.csv`, `annotation/q10`, `annotation/q10b`) still gate
any calibration claim, and P1 adds a fourth.

## Risks

- Receipts reintroduce the narration problem in a new form: a driver that quotes receipts in its
  done text. The claim check reads the page, not the receipts, so this shows up as no-fact refusals;
  Q12 reports them.
- The effect diff has a text-ratio threshold (0.98) tuned for System 1's menus; a receipt that says
  "no change" when a badge changed is a false receipt, worse than none. Q12 records receipts against
  the predicate's later verdict, the same false-reject audit `evals.rejections` does for refusals.
- Two input paths for one browser (P6) doubles the driver surface; the phase exists to remove one,
  not to keep both.
- Cross-surface tasks (P5) need a foreground app switch, which the native path found brittle
  (`invoke_menu` refusals); the oracle-first rule keeps that out of the measured runs.
