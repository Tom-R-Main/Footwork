# Legible Loop v6: evidence from packages C to G (2026-09-26)

For the owner to fold into `the-legible-loop-v6-draft.md` (outside this repo). Each line is a status
change a v6 rule can cite, with its source. Nothing here is a new rule.

## L2. Receipts report the observed outcome, not the dispatch

- **New field, tested:** a browser receipt now says whether the page received the input (`delivered`,
  `not_delivered`, `by_script`, `new_document`, `unknown`) apart from what changed, and reports scroll,
  focus, a control's value change and navigation between steps (`jevdual.delivery`; package D, D1 held).
  Focus and scroll never confirm a click (a click focuses its own target; D1's first rule said
  "confirmed" on a no-handler button).
- **Found a false receipt of its own:** Q12b's delivery guardrail caught `not_delivered` on every
  working `select_dropdown` (script-set values); fixed, with a browser test that fails on the old probe.
- **Native save by readback, built:** a save's effect is the file the window names read against the
  window's text (`jevdual.native.save_readback`). The cross-surface pilot showed both directions: a
  failed save read `partial` and the oracle agreed (G2); a good save read `confirmed ... holds the
  window's text exactly` (G3). v6's "hotkey save pending (P4)" is no longer pending on the session path;
  on the native agent path it is built and untested live (G4 ran on a locked screen).
- **Burden:** Q12b (`results/q12b-live-dev.md`): delivered receipts lowered requests per unit of progress
  (−0.28 [−0.69, −0.01]) and cost 4 verified passes pooled with no-fact refusals up: H0(c). Status stays
  "kept for honesty, no burden claim".

## L3. Fix the route before judging the declaration

- **Measured a second time, and the cause found:** the saucedemo "dead click" was Chrome's
  breached-password warning, which drops every dispatched click after a login with a listed password
  (package C: 38 of 38 lost in the agent loop, 12 of 12 in the 2x2, 0 of 3 on localhost; fixed by a
  quiet profile). With the route fixed, `guarded` verified passes went from 121 (Q12) to 137 (Q12b)
  pooled, and saucedemo from 9 to 22 of 36 (descriptive, different days). More than any declaration or
  receipt has moved.

## L6. Completion is earned against observed state

- **Blind spot named with mechanisms:** no-fact refusals come from the claim check, not the driver
  (package E, V1 open until Q16): a status label turned into one unmatchable atom, parenthetical asides,
  form values outside innerText, prices split across text nodes. Q16 measures a strict check against
  the current one.
- **Native:** Q17's six failures on `dual` and `guarded` are all the verifier refusing a correct, saved
  append; the save readback (L2) is the evidence it lacked (G4 pending).
- **Recorded, not only counted:** refused claims are now in the trace (`unsupported_claims`), and a run
  that ends UNVERIFIED says why (`unverified_reason`: no_evidence, unmet, uncertain).

## L7. Declare and enforce the execution posture

- **New refusal, tested:** `screen_locked`. A native run on a locked screen now stops at its first
  observation with the reason; before, G4 pressed keys for 25 steps against a screen nobody could see.

## L9. Whoever drives gets the same contract

- **First cross-surface route, driven once:** two sessions and a carried value (`footwork read --as`,
  `@NAME --from`, `footwork check-file`), each carry holding its source (surface, URL or app, element or
  matched line, step). One browser-to-TextEdit transfer ended with every receipt true and the saved line
  proven byte for byte (G3). Q13's five tasks are not pre-registered: their oracles come first.

## Measurement (section 4)

- **Q17** (`results/q17-native-dev.md`): on the native path, `guarded` and `dual` verified the same 15 of
  18; `guarded` 7% cheaper per verified task (interval includes zero), `dual` 31% faster. The old reading
  (36 against 137 System 2 calls) would have called `dual` a saving. Supports the section's rule: decide
  on cost and time per verified task, never on call counts.
- **The notebook (N1)** failed as written: conformance predictions (package B) all held. Kept, with
  predictions required for unknowns only.

## Added after Q16b and Q11b

- **L1 (declare):** Q11b, the narrow declaration (requirements plus "state only what the page shows"),
  cost 10 verified passes pooled through no-fact refusals (91 against 68) with the work itself done
  (predicate passes +2): H0(b), not adopted (`results/q11b-live-dev.md`). With Q11 this is two
  declarations that raised refusals; what the driver is told about the done text interacts with the
  claim check, so L1 is not separable from L6 on the browser path.
- **L6 (completion):** the strict claim check held on the live heldout on verified passes (21 against
  19) and no-fact refusals (3 against 7); its one false completion is shared with the default check and
  is a stale oracle (`lhw-rust-year`: the predicate says 2015, Wikipedia's infobox, quoted by both arms,
  says 2012). Not adopted by the pre-registered rule; the oracle is the owner's call
  (`results/q16b-live-heldout.md`).
