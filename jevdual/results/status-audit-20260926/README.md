# Footwork status audit — 2026-09-26

Footwork has a working research harness and useful supervised computer-use primitives. The best-supported default remains System 2 behind the guard. The operator surface is a substantial advance, but its target identity, receipt semantics and secret handling need correction before broader use. System 1 reduces model requests on some tasks; it has not established better total cost or completion than guarded execution.

This review inspected the supplied handoff, current implementation, recent commit history, experiment definitions, stored result rows, annotation records, coexistence evidence, tests and GitHub CI. It did not run paid inference, access credential files, launch a browser or operate native apps. Only this audit directory was added; product code and original results were not edited.

**Repository and verification.** Local main and GitHub main matched `afe6d9493dc7d067ee67838b90650d59c902df17` at inspection, and the worktree was initially clean. [CI for that revision](https://github.com/Tom-R-Main/Footwork/actions/runs/36252177173) succeeded. Local `.venv/bin/python -m pytest -q -m 'not browser and not live' tests` returned **473 passed, 21 skipped, 14 deselected in 14.52 s**; Ruff passed. Linux CI runs lint, Rust checks and offline Python tests; it does not establish live macOS or browser behavior. The fresh probes below exercise production functions with fake drivers, never the desktop.

**What is now implemented.**

| Area | Current state | Evidence boundary |
|---|---|---|
| browser-use autonomous loop | Guard, verifier, ledger, optional reactive S1 and experimental delegation; action receipts can be recorded or delivered | Most quantitative browser results come from this path, using browser-use 0.13.10 |
| Native autonomous loop | Cua accessibility menus, S1/S2, shared native authorizer, exact append, live target checks, execution posture | Q10b: six tasks, Calculator and TextEdit, three repetitions per arm; later operator fixes are not a new Q10b measurement |
| Operator CLI | `start`, `look`, `do`, `s1`, `done`, status, persisted observation and history | Useful supervised interface; `s1 --act` dispatches a proposal via `do`, not the autonomous arbiter policy |
| Operator browser mode | Footwork-owned Chrome profile, Cua DevTools route, label addressing, DOM click by default | Separate adapter from browser-use; targeted live examples and Q15 C3, not a paired replacement-backend benchmark |
| Machine coexistence | Background-only default, explicit foreground permission, idle check, hand-back, conflicting-append refusal | Q15 passes within its stated app, action and timing limits |
| Engineering safeguards | Pinned browser-use and cua-driver versions, seam tests, CLI scenario tests, Rust/Python equality tests | API shape and simulated behavior are covered better than before; gaps below survive the green suite |
| Cross-surface workflow | Planned in Q13 | No implemented shared multi-surface session or measured Q13 result located |

There are three execution paths, with shared types and some shared logic, rather than one fully conforming execution contract. `footwork start --browser` uses the Cua browser adapter. `footwork run` builds a native `NativeAgent`; it has no corresponding `--browser` switch or guarded-only arm flag. Despite its docstring calling the default “guarded,” it enables S1 and escalates to S2: that is reactive dual in the experiment vocabulary. Paused autonomous runs currently print a rerun instruction; this is distinct from resuming the same run and ledger. The manual session does retain state across commands.

**Measured status, recomputed from retained rows.** Costs are the recorded model-cost estimates, not invoices or total operating costs. Repeated runs are not independent new task types. Historical experiment rows do not certify the current revision.

| Measurement | Results | Decision supported |
|---|---|---|
| Q9e repaired delegation, 59 tasks | Delegate 36 verified, $0.644; earlier same-day guarded 41, $0.424; dual 44, $0.496. Delegate reached 3/27 assignments | Keep delegation experimental. Baselines were not interleaved with this repaired run and had model timeouts |
| Q10b second native run, 18 trials/arm | S1-only 9 verified, $0.01385; dual 13, $0.03217; guarded 15, $0.02495 | Native improved; guarded still wins dual on both completion and total cost |
| Q11, 177 trials/arm | Guarded 126 verified / 821 requests; declared 126 / 993; legible 129 / 974 | Broad declaration and typed rejection feedback were not adopted |
| Q12, 177 trials/arm | Guarded 121 verified / 798 requests / 190 no-op receipts / $1.1804; receipt arm 117 / 761 / 156 / $1.1171; both 28 pauses | Receipts reduced retries and raw requests, without a demonstrated primary-metric win |
| Q15 | 15/15 accepted cases; additional corrected C3 attribution run 3/3 | Support the tested background behaviors; preserve scope and concurrency limitations |

Q10b dual uses 44 LLM calls against guarded's 130, but about 29% more total model cost and about 49% more cost per verified completion. Its remaining two-trial deficit is on calc-percent. Every arm still failed to verify the append-and-save task in this measured run; subsequent supervised TextEdit save/readback success is useful evidence, not a rerun of the autonomous comparison. Do not mix Q10 and Q10b denominators: tasks and requirements changed.

Q12's primary difference is **−0.02 requests per progress unit, 95% interval [−0.14, +0.10]**. The four fewer verified completions also breach its preregistered −2 guardrail, even though the paired interval includes zero. Its correct conclusion is non-adoption as a burden improvement. The fact that failed runs became cheaper is not task success.

There is an additional metric-description issue: `evals.burden.progress_rows` includes every row carrying `checkpoints_reached`; the runner sets that field even for tasks without declared checkpoints. Only 19/59 tasks declare nonempty checkpoints. The reported 53-task comparison is the common set with positive mean `(checkpoints reached + predicate pass)` in both arms, not 53 tasks with declared checkpoints. Six tasks are excluded for zero progress in at least one arm. The arithmetic reproduces, but its label and population need to be explicit. Keep all-task completion and zero-progress counts beside this conditional ratio.

**Earlier audit findings have received meaningful fixes.** Native routes now enter `Authorizer`; failed native judgments default to a pause. Append inserts against exact AX values and requires exact readback, instead of rebuilding documents from model previews. The append predicate checks preserved content. Annotation protocol 2 carries display state and prior effects while hiding scores. The operator's input posture and compound-action target handling have dedicated tests. These are substantive changes, not merely prompt adjustments.

The corrections are not complete across all callers. The new probes in [probes.py](probes.py), with output in [probes.json](probes.json), establish the following current defects:

1. **Browser session identity changes across commands.** `session.SessionState` persists PID and window ID, not browser target/tab identity. `session.bind` creates a new bridge each command; `BrowserBridge.attach` selects whichever tab is active. A fake driver changing active tab from A to B causes consecutive binds and clicks to target A then B under the same session. Matching labels on the other tab defeat the label-only check. C3 keeps one bridge bound, so that successful live test does not cover reconnecting CLI commands. Persist the bound tab/target and refuse if missing; never silently replace it with the active tab. Relevant source: `session.py:40`, `session.py:192`, `browser_driver.py:291`.

2. **Text receipts can assert the wrong outcome.** `_field_receipt` confirms `type` by substring containment: requesting `Ada` confirms a field holding `Ada Lovelace`. An append confirms if the intended text was already present, without proving insertion or preservation. It also replaces an existing `refused` receipt with `confirmed` when that substring is present. The probe returns `confirmed` while retaining error `requires_foreground`. It selects the first same-label field, or falls back to a numeric ID, so identity is weak here too. Preserve dispatch/refusal status, require action-specific postconditions, and bind before/after evidence to the same field. Relevant source: `session.py:137–164`. Native exact-append readback is stronger than the operator receipt that summarizes it; retain that evidence rather than weakening it.

3. **Named secrets can enter receipt output.** For a non-password field and `pending.secret=True`, `_field_receipt` sets `shown` to a placeholder but leaves `holds` as the actual value and interpolates it into evidence. A synthetic marker survives into the receipt. `observe` logs and returns the receipt, and the menu renderer also prints ordinary field values. No real secrets were read or exposed in this audit. Secret classification must travel with the field through observation, persistence, receipts and model inputs, independent of whether the UI uses a password control. Relevant source: `session.py:155–162`, `session.py:168`, `session.py:216`.

4. **Browser judgment failures still allow continuation.** `DualProcessAgent._destructive_judgment` catches a judge exception and returns no pause. The fresh fake-judge probe reproduces this known P2 gap. Native's corrected behavior does not protect browser-use. Missing/unavailable required judgment and malformed output need an explicit conservative outcome, consistently across surfaces. Relevant source: `agent.py:247–273`.

5. **Short document replacement is still allowed by the native gate.** `REPLACE_MIN_CHARS=20` exempts a 12-character `First line.\n` document. Proposing `type "Second line."` receives no pause under the real Authorizer. The native bridge's type branch writes the whole value. No real write was performed. Correct append usage prevents the original measured failure, but the gate still cannot claim to protect all existing content. Make replacement intent and ownership explicit instead of inferring importance from length. Relevant source: `authorize.py:54–81`, `native.py:924–929`.

The authorizer also still represents grants as label substrings, including persistent start-time grants; it is not yet an operation/resource/effect-bound authorization token. This is a design limitation visible in source, distinct from the five demonstrated cases above. Native key/Enter routes share the boundary but do not all receive the same semantic judgment as click/menu/hotkey routes. Treat “one boundary” as a routing property, not proof that every action's meaning is understood.

**The input defect remains the major execution blocker.** The retained Q8b diagnostic and Q11/Q12 records show trusted input disappearing after navigation in browser-use, sometimes with duplicated events. A page-script click works in those observations. The repository still points to P2 and contains the diagnostic; no repair or post-repair measurement was located. This review did not rerun the live diagnostic. Session bookkeeping is a plausible diagnosis, not a root cause established by this review. Cua browser mode's successful DOM clicks do not prove the browser-use trusted path is fixed, and they do not establish that synthetic events work on all sites.

**Native breadth is useful discovery, not broad readiness.** Calculator and TextEdit have quantitative runs and supervised examples; Notes append worked after a bridge correction. Safari field entry gained readback, but its AX snapshot did not expose the JSON response needed for verification. System Settings' clicked sidebar row did not navigate and search results appeared outside the window. Finder rename remains unreachable in the tested bridge: the edit control is outside the target window and a later Return could not acquire the key window. Finder Move to Trash did execute after the authorization and posture gates, while its absence-based completion remained unverified. These outcomes identify missing capability and observation coverage; lowering a verifier threshold does not repair them.

**Q15 has a narrower meaning than the headline.** Five scenarios were repeated three times on this Mac with a scripted person, fresh app instances and owned documents. They provide valuable evidence for exact append, refusing ambiguous background keys, retaining the person's tab and declining foreground input while active. The foreground holds measured 36–65 ms, sampled at roughly 30 ms intervals. The person's move overlapped a step in **0/3** C4(c) attempts; the actual overlap policy remains unit-tested rather than live-demonstrated. Background-only and foreground-permitted should retain separate claims. Repeated CLI reattachment, arbitrary apps, fast races and typing into the agent's own document are not established by this suite.

**Human annotation has progressed, but calibration remains provisional.** Twelve Q10b decisions are recorded separately in `human-decisions.jsonl`, selected as three model disagreements, five agreed-wrong and four agreed-right. The person agreed with pass A on 9/12 and B on 8/12; two unnamed-button rows both models called wrong were human-unclear. Of nine model-agreed rows, seven matched the person. This is a valuable targeted audit, not a representative population sample. The original web, Q10 and Q10b 40-row CSV audit-label columns are still blank; the separate 12-row JSONL must not be overlooked when describing the human work as pending. The prior 80-row AI audit is also separate and is not human validation.

Q10b's agreement and AUROC are substantially more defensible than Q10's score-visible, display-poor packets. Nevertheless its 21 agreed wrong rows come from only two tasks. AUROC measures ranking, not calibrated probabilities or transfer to unfamiliar apps. Keep the Q10b write-up's careful “ranking result” wording; retire the README's unconditional “calibration transfers” wording. Do not adjust thresholds from these data and then evaluate on the same task families as if untouched.

**Documentation currently overstates or lags the evidence.**

- README: Q12 is marked running; it is completed and not adopted for burden reduction.
- README: repaired delegation is described as not remeasured; Q9e measured it and found no advantage.
- README: “zero false completions on every split and run” contradicts the retained dual row `li-add-then-delete-authorized` in `q8-q9e-live-dev-20260922-162350`: `passed=false`, `is_done=true`, `success=true`. Q11/Q12's zero counts on their predicates are valid narrower statements.
- README and CLI: distinguish research-selected guarded baseline from the S1-enabled `footwork run` default.
- Plan: P6's practical browser route exists, but Q14's planned paired comparison did not thereby occur. Q13/Q14 have no experiment files yet. Earlier conformance-table cells have not all caught up with subsequent implementations.
- Q12: “53 tasks with checkpoints” misdescribes the conditional progress comparison described above.

**Recommended next work, in dependency order.**

| Work package | Why now | Acceptance evidence |
|---|---|---|
| A. Fix session and evidence correctness | Current probes show target drift, false confirmation and secret disclosure | Failing CLI scenarios first, then passing scenarios across reconnect/tab changes, duplicate labels, refused input, exact replace/append, short documents and synthetic secrets; no real credentials required |
| B. Make authorization behavior consistent | Browser fallback remains permissive; string grants and route differences constrain current claims | Same semantic action through browser/native click, key, Enter, menu and text routes yields the same decision; unavailable judge dispatches nothing; approval scoped to an explicit action/resource |
| C. Isolate and repair trusted input after navigation | Both Q11 and Q12 are constrained by unreachable actions | Deterministic local navigation fixture, event arrival and exactly-once assertions, reproduction across fresh browser sessions; targeted authorized/unauthorized practice-task checks after the fix is frozen |
| D. Improve receipt observations and run Q12b | A useful receipt must describe an actual action outcome | Scroll/focus/expanded-state readback, late-navigation handling, separate dispatch and postcondition fields; preregister the fixed-input receipt-on/off comparison before running |
| E. Address verifier evidence and recovery | Existing native gaps involve save/read/absence evidence and S1/S2 loops | Oracle end-state probes before full runs; typed save/persistence evidence; bounded S2 recovery until a progress condition is met; untouched task variants for percent/repeated-action tests |
| F. Cross-surface pilot | Valuable only when identity, authority and receipts survive a handoff | One browser-to-TextEdit oracle with typed data provenance and exact saved-file predicate, then the preregistered five-task Q13 study |

Keep A/B as correctness changes and C as an execution repair, each reviewable separately. Do not attribute an input repair's gains to receipts. For Q12b, compare receipt delivery on/off on the same fixed input implementation; compare input repair separately if needed. Freeze task definitions, interleave arms, average repetitions within task, and report all-task verified completion, false acceptance, false refusal/appropriate pause, zero-progress rate, cost and wall time alongside conditional progress ratios. Inspect the difficult zero-progress tasks explicitly.

I would bring focused Q3 verifier work ahead of another broad prompt-declaration experiment. Q11b can remain a narrow ablation after execution and evidence are dependable. Do not lower thresholds to compensate for missing save, absence or page evidence. Record historical process claims against the trajectory and final-state claims against current observations, with insufficient evidence a distinct outcome. Deterministic observables should be checked by code where possible.

For System 1, the next useful experiment is recovery ownership and action eligibility, not more indiscriminate fan-out. Let S1 select mechanical actions where target, arguments, permission and expected effect are already specified. Let S2 retain control of interpretation, content generation and multi-step repair until a named progress condition holds. Rank success by cost and latency per correctly completed, authorized task. Fewer S2 calls alone have repeatedly failed to imply that win. Keep general delegation, adaptive threshold tuning, model replacement and more Rust optimization behind this work.

The immediate milestone should be: **the same command stays on the same resource, executes only its approved effect, preserves user data, and returns evidence that cannot overstate what happened.** Once that holds, Q12b and a focused verifier/recovery study can answer whether the improved execution contract actually reduces work.

**Reproduction.** From `jevdual/`:

```sh
.venv/bin/python results/status-audit-20260926/probes.py
PYTHONPATH=. .venv/bin/python results/status-audit-20260926/recompute.py
.venv/bin/python -m evals.burden results/q12-live-dev-pooled --vs guarded
```

`metrics.json` includes hashes of the result files used. The probes characterize current defects; they are not fixes or new end-to-end performance measurements. Source references refer to the audited revision. Historical live outcomes above were checked against retained artifacts and notes, not repeated live in this audit.
