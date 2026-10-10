# Package A: session identity, truthful receipts, secrets, short-document replacement

Opened 2026-09-26 at `afe6d94` from the status audit (`results/status-audit-20260926/`), whose
`probes.py` reproduces each defect offline with production functions and fake drivers. Each fix
starts as a failing scenario (CONTRIBUTING: a bug found by driving becomes a scenario first). The
browser-mode cases need a fake browser driver in `tests/fixtures/`; the audit's probe has one to
start from.

## A1 · prediction · 2026-09-26 16:05
Question: why do two `do` commands in one browser session click different tabs?
Hypothesis: `SessionState` persists pid and window id but not the tab; `session.bind` builds a new `BrowserBridge` per command and `BrowserBridge.attach` takes whichever tab is active (`browser_driver.py` attach, `tab_id = active["tab_id"]`).
Alternatives: the driver retargets on its own after a focus change, so persisting the tab would not be enough.
Test: scenario with a fake browser driver: `start --browser` on tab A, switch the active tab to B, then `do`. Fix: persist `target_id` and `tab_id` in `SessionState`, pass them to attach, and refuse when the bound tab is gone.
Predicts: before the fix the second click goes to tab B; after it the command refuses with a typed code (tab gone or not bound) and dispatches nothing, and every existing scenario in `test_session_scenarios.py` still passes.
Against: dispatch still reaches tab B with the tab persisted (the driver retargets), or a session whose tab did not change is refused.
Refs: results/status-audit-20260926/probes.json (browser_session_rebind_after_active_tab_switch)

## A2 · prediction · 2026-09-26 16:05
Question: how does a refused `type` come back as `confirmed`?
Hypothesis: `_field_receipt` recomputes the verdict from the field alone: it never checks whether the incoming receipt was `refused`, and it confirms by substring (`intended in holds`), so a field that already held the text confirms.
Alternatives: the refusal is lost earlier, in `receipt_for`, before `_field_receipt` sees it.
Test: scenarios for a refused `type` under `background_only` into a field already holding the text; `type "Ada"` into a field holding `Ada Lovelace`; `append` of text already present. Fix: return a refused receipt unchanged; `type` confirms on equality with the intended value, `append` on the before value plus the insertion.
Predicts: the refused case stays `refused` with its code; `Ada` into `Ada Lovelace` is not confirmed; the pre-existing append is not confirmed; the Wikipedia-search case the receipt was written for still confirms.
Against: an existing scenario that should confirm now fails because the driver changes the value it writes (Cua strips trailing whitespace from values), which would mean exact equality needs a stated normalisation, not a looser match.
Refs: results/status-audit-20260926/probes.json (field_receipt_overrides_refusal, type_accepts_substring_instead_of_exact_value, append_can_confirm_preexisting_text_without_new_insertion); session.py _field_receipt

## A3 · prediction · 2026-09-26 16:05
Question: where can a named secret typed into an ordinary field reach output?
Hypothesis: two places, not one. `_field_receipt` substitutes the placeholder in `shown` but puts the real value in `holds`, which goes into the evidence text; and `render_observation` prints every field's value, so the next `look` shows it too.
Alternatives: only the receipt; the menu does not carry the typed value for that field.
Test: scenario that types a named secret with a synthetic marker into a non-password field, then runs `look`, `done` and reads the session log and state file. Fix: the session keeps the set of fields holding a secret and masks them in receipts, rendering, the log and model inputs.
Predicts: before the fix the marker appears in the receipt and in the next `look`; after it the marker appears in no command output, log line or persisted file.
Against: the marker appears only in the receipt (the menu site is not a leak), or appears somewhere the fix does not touch (a screenshot path or trace), which would widen the fix.
Refs: results/status-audit-20260926/probes.json (secret_placeholder_in_nonpassword_field); session.py render_observation

## A4 · prediction · 2026-09-26 16:05
Question: why is replacing a 12-character document not paused?
Hypothesis: `NativeAction.replaces_content` uses length as a proxy for content that matters (`REPLACE_MIN_CHARS = 20`), so short documents are exempt.
Alternatives: none needed for the cause; the open question is the replacement rule.
Test: scenario replacing `First line.\n` with `Second line.` under the real `Authorizer`. Fix: a `type` into a non-empty textarea whose text neither equals nor extends the current value is a replacement at any length.
Predicts: the 12-character replacement pauses; typing into an empty document and appending do not; no existing native scenario or Q10b task definition starts pausing.
Against: existing scenarios or Q10b tasks start pausing (a legitimate short overwrite, such as a field the task says to clear), which would mean replacement needs the task's stated intent rather than a length rule or none.
Refs: results/status-audit-20260926/probes.json (short_document_replacement); authorize.py REPLACE_MIN_CHARS

## U0 · update · 2026-09-26 12:22
Observed: the headings of A1 to A4 (and N1 in the practice file) read 16:05 and 16:10; the clock at this entry reads 12:22 the same day, and commit e5fb462, which holds them, was made at 12:10. The earlier times were written without reading a clock.
Inferred: a heading time is only as good as its source. The commit time is the authoritative record of when a prediction existed; the heading is a convenience.
Changes: headings are written from `date`, and the README says the commit time is authoritative. The committed headings are left as they are, since the notebook is append-only; this entry is the correction.
Next: record A1 to A4's outcomes.

## U1 · update · 2026-09-26 12:22
Resolves: A1 = held
Observed: `test_a_later_command_stays_on_the_bound_tab` dispatched to tab-A then tab-B before the change and to tab-A twice after; `test_a_closed_bound_tab_refuses_and_dispatches_nothing` raises naming the tab and records one dispatch. The audit probe now shows two tab-A dispatches. No scenario in `test_session_scenarios.py` changed.
Inferred: the driver does not retarget on its own; persisting `browser_tab` and passing it to `BrowserBridge.attach` is enough. Not shown: behaviour against the real Cua DevTools route, which a live `start --browser` check should confirm before this is claimed beyond the fake.
Next: A2.
Refs: tests/test_session_evidence.py; results/status-audit-20260926/probes.py

## U2 · update · 2026-09-26 12:22
Resolves: A2 = held
Observed: the substring, pre-existing append and refusal tests failed before the change and pass after; the Wikipedia-search test still confirms. Rerunning the audit probe after my tests were green showed `field_receipt_overrides_refusal` returning `partial`: my first fix checked the pending action for a refusal, and the probe carries it on the incoming receipt (`Receipt.error`). The hypothesis named exactly that ("never checks whether the incoming receipt was refused"); the implementation drifted from it and my tests did not cover the form the hypothesis described. Fixed, with `test_a_refusal_carried_on_the_receipt_is_kept`.
Inferred: the probe caught what the new tests missed. Rerun the original reproduction after every fix, not only the tests written for it.
Changes: two semantics beyond the prediction. Trailing whitespace is not compared, written in from the known Cua stripping rather than discovered, so the Against case was pre-empted, not tested against a real driver. A password field now returns `unverifiable` instead of `confirmed` (it shows that it holds something, never what); `test_secret_and_password_receipts_never_show_the_value` changed with it.
Next: A3.
Refs: tests/test_session_evidence.py, tests/test_session.py

## U3 · update · 2026-09-26 12:22
Resolves: A3 = failed
Observed: running the afe6d94 `session.py` against a synthetic marker put it in four places: the receipt, the rendered observation, the persisted `session.json` (the remembered candidates and page text) and the `session.jsonl` log. The prediction named two, the receipt and the rendering.
Inferred: the leak is not in any one printer; every observation carried the value, and everything downstream (rendering, persistence, logs, System 1 and the verifier in later commands) received it. Masking at each printer would have missed the two persisted sites.
Changes: the fix moved from masking printers to scrubbing the observation once, in `observe`, before it is rendered, remembered, diffed or passed on. The session records secret names (never values) and resolves them from the environment to scrub later observations; the value in hand is compared during the typing command only, then dropped. Values under three characters are not scrubbed, a stated limit.
Next: A4.
Refs: tests/test_session_evidence.py::test_a_secret_in_an_ordinary_field_reaches_no_output

## U4 · update · 2026-09-26 12:22
Resolves: A4 = held
Observed: with the 20-character floor replaced by "any non-blank content", the 12-character replacement pauses; typing into an empty document and extending existing text do not; the full suite (500) passes. Of the Q10b TextEdit tasks, `textedit-type-sentence` starts empty and `textedit-append-line` is solved by `append`, so neither pauses; a `type` over its "First line." now pauses, which is the failure the gate exists for.
Inferred: no legitimate short overwrite in the current tasks. A task that says to clear a field will need `--authorize replace` or a stated intent; none exists yet.
Next: package summary.

## S1 · summary · 2026-09-26 12:22
Established: the audit's four session defects are fixed and each has a test that failed on afe6d94: the browser session stays on its bound tab and refuses when the tab is gone; a field receipt states the postcondition for `type` and `append`, binds to the chosen field when labels repeat, and never upgrades a refusal; a named secret is scrubbed from every observation before rendering, persistence, logs or model input; replacing non-empty content pauses at any length. The audit probes report the corrected behaviour except `browser_use_judge_failure`, which is package B.
Uncertain: A1 is shown against a fake DevTools route only; the whitespace normalisation was assumed, not observed; secrets under three characters are not scrubbed; the password-field change may surface as fewer `confirmed` receipts in live operator runs.
Decision: adopt. Next is package B (authorization parity), starting from the browser judge failure. For N1: one failed prediction (A3, which widened the fix) and one implementation drift caught by rerunning the probe (U2).
Refs: tests/test_session_evidence.py; results/status-audit-20260926/probes.py
