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
