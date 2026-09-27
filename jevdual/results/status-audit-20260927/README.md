# Review of Claude's work through c2de17e

Reviewed 2026-09-27. Base: the prior audit of afe6d94. Local HEAD: c2de17e; main was clean and 55 commits ahead of the locally recorded origin/main. The remote was not refreshed. This is a source, notebook, and recorded-results review, with existing offline checks rerun. No new paid inference, live desktop/browser operation, product change, commit, or push was performed.

## Judgment

Substantial progress. The most convincing work identifies a broken execution mechanism, repairs it, and checks the resulting state independently: the Chrome password warning and TextEdit save readback. The notebook records failed diagnoses and preserves non-adoption decisions when guardrails fail. The next milestone should be a dependable, bounded workflow with durable evidence. The implementation does not yet justify an unrestricted claim that it always proves work or stops with a named reason.

## What the recorded evidence establishes

Counts below were recomputed from each named directory's results.json. Browser verified means predicate passed, is_done, and success. Historical native rows with null success use accepted done without error or pause. The native runner now populates success. Costs sum recorded Jev and LLM cost estimates, not an invoice.

| Study | Comparison | Verified completions | Meaning |
|---|---|---|---|
| Q12b, 177 rows per arm | guarded / delivered receipts | 137 / 133 | Receipt delivery reduced the primary progress-normalized request metric but breached the completion guardrail; not adopted. |
| Q16, 177 rows per arm | guarded / page-and-fields check | 137 / 148 | Promising check repair; identical predicate passes, 174 each. Primary interval includes zero; not adopted on dev. |
| Q16b, 24 rows per arm | guarded / page-and-fields check | 19 / 21 | One predicate-defined false completion on each, the same Rust-year task; original rule does not adopt. |
| Q11b, 177 rows per arm | guarded / narrow declaration | 133 / 123 | Predicate passes 172 / 174. More work rejected at completion; not adopted. |
| Q17, 18 rows per arm | dual / guarded | 15 / 15 | Costs $0.028352 / $0.026355; total wall seconds 557.5 / 808.4. Dual is faster on this small suite, with no demonstrated cost advantage. |
| G5 and G6, six rows each | dual and guarded saved append | 12 / 12 combined | Targeted native save-evidence recovery, versus 0 / 6 in Q17. Not a full native-suite rerun. |

Sources: results/q12b-live-dev-pooled, q16-live-dev-pooled, q16b-live-heldout, q11b-live-dev-pooled, q17-native-dev, g5-native-append, g6-native-append. Experiment interpretations: corresponding results/*.md and docs/experiments/Q*.md.

Across 25 newly committed, non-pooled results.json directories, recorded estimated cost totals $7.715330. This supports “about $8”; it does not reconcile provider billing or unrecorded calls. Pooled duplicates were excluded.

The Q12-to-Q12b guarded increase, 121 to 137 verified and 9 to 22 of 36 saucedemo trials, is descriptive across different runs/days. Controlled input diagnostics support the password-warning mechanism, but the entire 16-completion difference is not a randomized estimate of that one fix. No-op counts also changed because read-only steps stopped receiving receipts. The Chrome regression test itself notes its negative control depends on the external leak service; it is not a universally deterministic reproduction when that service cannot answer.

The fresh quiet profile is scoped to the automation browser; it does not disable protections in the operator's personal Chrome. This is an appropriate boundary for that fix.

Q17 actually contains six distinct tasks and 54 rows, despite the preregistration and result text saying seven. Its existing dual arm resumes System 1 each iteration; it did not implement and compare a new policy where System 2 retains recovery until a named progress condition. It answers dual-versus-guarded on the existing suite, not the entire recovery-ownership design question.

## Source findings that should precede broader claims

These are static control-flow findings, not new live reproductions. The existing passing suite does not cover these complete paths.

### 1. Authorization parity stops short of the CLI and browser routes

`python/jevdual/session.py:624` constructs a semantic judge only for click, menu, hotkey, and navigate. `key` and `enter` still pass `judge=None`, although `authorize.py` now includes them in JUDGED_ROUTES. A keyword-free destructive default button can therefore be judged when clicked and missed when reached by Return. The new tests inject a judge directly into Authorizer; they do not prove that cmd_do wires one in. The notebook correctly acknowledges the missing judge-enabled scenario, but the package's broad parity claim overstates the boundary actually tested.

The browser-use route also remains asymmetric: `_destructive_hit_any` keyword-checks Enter, while `_destructive_judgment` gets only `_click_targets` (`agent.py:215`, `:224`, `:261`). Failure handling is improved for calls made; that does not cover calls never made.

Fix direction: real CLI scenarios with a fake semantic judge, and browser action-path tests for click versus Enter, both allowed and refused. Define the outcome for a required but unconfigured judge. Keep explicitly authorized no-judge operation distinct. Grants still lack resource/effect identity: native grants are exact action labels, while browser grants remain substring scopes. Changing a document or page can retain the same authorized label.

### 2. A handled driver exception can now crash before the refusal is recorded

`session.py:697` catches NativeBridgeError or RuntimeError from dispatch and sets a named error. The new `getattr(eff, "readback", None)` at line 714 executes afterwards even when the failed await never assigned `eff`. That path raises UnboundLocalError before state.log/state.save.

Fix direction: initialize the effect or branch on successful dispatch; exercise the real command with a bridge that raises. Assert named refusal, no dispatch, durable record, driver shutdown, and no traceback. A returned refusal object and a raised bridge exception are different test cases.

### 3. Secret scrubbing does not cover persisted native screenshots

`session.observe` requests a screenshot file at `session.py:353` and only scrubs the observation afterwards. `native.py:594-595` asks the driver to write that screenshot. When a named secret is visibly typed into an ordinary field, text scrubbing cannot remove it from the already-written image. No real secret or screenshot was opened for this review.

The notebook also states that values shorter than three characters are not scrubbed, and later commands resolve scrub values from the environment. The supported protection should name these limits; “never persisted” is too broad.

Fix direction: explicit treatment of sensitive observations before image persistence or model delivery—suppress capture when it cannot be safely redacted, or redact before writing. Test synthetic markers only. Do not treat the session's JSON/log test as proof about image artifacts.

### 4. The experimental claim check can erase factual qualifications and keep the original claim

`verify.py:153-161` removes every parenthetical, including factual ones, before extracting atoms. `check_claims` grades the shortened form but stores the original sentence (`:233`). `supported_answer` then joins the original supported sentences (`:509-511`).

For example, the structure of “Price: $9.99 (shipping $50)” causes the shipping claim to disappear from the strict check while remaining in the retained sentence. A separate model judgment may reject an answer, but the deterministic support record no longer validates everything it labels supported. The six-word cutoff similarly treats long colon clauses as narrative. These are evidence-policy changes, not only normalization fixes.

Fix direction: preserve factual parentheticals; strip only explicitly recognized status/process material. Keep support attached to checked spans, entities and fields, and never return unchecked text as supported. Add negative controls for wrong qualifiers, wrong product/price pairings, wrong fields and mixed true/false claims before adopting this arm. “Found somewhere on the page” is not equivalent to the requested fact being supported.

## Other boundaries to keep explicit

- Browser `confirmed` still means an observed page change in the generic diff branch (`receipts.py:129`). An unrelated update can coexist with undelivered input. Delivery and effect are distinct, but the effect is not generally an action-specific postcondition. The page-level event counter also does not establish per-action target identity or exactly-once dispatch in a multi-action step.
- Native save readback proves the named file's text equals the window at the read. It does not prove which command caused the save, persistence across every storage failure, or rich-text equivalence. G6 supports moving to File > Save on the tested TextEdit path; Cmd-S remains unreliable there.
- `carry.check_file` proves that some line equals the carried value. It does not establish the intended destination line, uniqueness, preservation of earlier content, or that this run wrote it. A pre-existing matching line can satisfy it. The function's specific receipt says what it observed; the wider workflow must not infer more.
- Carry metadata records source context; it is not an immutable source snapshot or complete transformation history. One successful browser-to-TextEdit pilot is a useful primitive, not Q13 or general cross-app autonomy. The source title was known to lag navigation in the driver.
- The Legible Loop evidence file retains earlier “G4 pending” and native-save-untested statements despite G5/G6. Reconcile the current status while retaining the historical notebook.

## Rust oracle adjudication

Both stored answers quote Wikipedia's infobox as January 20, 2012; the frozen predicate expects 2015. On this review date the linked article still gives 2012. Rust's official 2015 announcement explicitly announces version 1.0. The original task asks when Rust first appeared according to Wikipedia. The predicate is incorrect for that task; this result does not demonstrate a new strict-check false acceptance.

Sources: https://en.wikipedia.org/wiki/Rust_(programming_language), https://blog.rust-lang.org/2015/05/15/Rust-1.0/, evals/tasks/live-heldout.yaml:4, results/q16b-live-heldout/results.json.

Recommended disposition: preserve the frozen file, raw result and original non-adoption decision; add a versioned oracle erratum with source evidence; regrade both arms symmetrically without rerunning. Correcting only this oracle yields 20/24 versus 22/24 verified and zero predicate-defined false completions on both. Label this an adjudicated analysis, not the original preregistered result. Retiring the task instead yields 19/23 versus 21/23. Neither treatment repairs the independent claim-check issue above. Subsequent implementation changes need fresh evaluation tasks; the exposed task is no longer fresh heldout evidence.

## What should come next

1. **Close the reachable contract gaps.** Real-command authorization wiring, raised-driver failures, screenshot handling, and exact resource/effect scope. Start with scenarios; give conformance work a notebook summary. Commit a prediction before any unknown-mechanism experiment. Done means a changed target, missing judge, locked screen, driver failure, or sensitive observation has a defined and tested outcome through the actual caller.
2. **Settle completion evidence offline.** Record the oracle erratum, repair the unsafe claim normalization, and build a fixed positive/negative corpus from dev failures plus new counterexamples. Score false acceptance and false rejection independently, including wrong entities, unsupported qualifiers, stale carries, partial writes and missing persistence. This is a focused Q3-style audit. AI can prepare and label an explicitly AI-reviewed set; it must not be described as independent human validation.
3. **Prove one useful end-to-end workflow.** Browser value → identified document/location → exact update → save → independent disk read. Preserve prior bytes, check insertion count and destination, and attach source evidence. Include duplicate/retry, stale source, wrong document, denied authorization and failed save cases. Establish five oracles, then preregister Q13 on fresh tasks. Keep each session's identity boundary rather than building a general surface-switching agent first.
4. **Measure System 1 where it is eligible.** Compare guarded System 2, current reactive dual, and a bounded policy whose target, arguments, authority and postcondition are fixed before System 1 executes. On mismatch, System 2 retains repair until a named progress condition. Score total cost, latency, correct authorized completion and interventions; report uncertainty, not only call savings. Q17 is a latency signal on six dev tasks, not a general speed or cost guarantee.
5. **Revisit receipt delivery only after the check is frozen.** The final dropdown fix postdates Q12b, and the old completion check confounds interpretation of driver-facing receipts. One registered comparison on the repaired/frozen base is useful. A third prompt-declaration experiment is lower priority than the contract and verifier work above.

The immediate milestone is: **Footwork completes a small, explicit workflow with evidence tied to the right resource, or stops with a durable, truthful reason.** It is not yet necessary to widen app coverage or change models.

## Review checks

From jevdual: `.venv/bin/python -m pytest -q -m 'not browser and not live' tests` → 551 passed, 21 skipped, 17 deselected. This is an offline subset, not a contradiction of Claude's broader 563-test report. `.venv/bin/ruff check python evals tests scripts` passed. Notebook check before this review summary: 61 entries, 23 predictions, 12 held, 8 failed, 3 inconclusive, none open. `git diff --check` passed. New findings above were identified by source inspection; no new reproduction harness or browser/live test was run.
