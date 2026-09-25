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
