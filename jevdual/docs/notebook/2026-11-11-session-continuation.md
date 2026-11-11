# Session continuation across failed start and unavailable observation

## SCN1 · prediction · 2026-11-11 00:10
Hypothesis: failed native start currently deletes an existing session before exact-window lookup or initial observation can reject the replacement; preparing the replacement separately can preserve all existing session files until successful initialization.
Test: public CLI simulated-Mac replacement starts with stale exact ID, mismatched observed binding, driver observation/shutdown failure and successful replacement. Preserve existing JSON/log/carry/snapshot/grant bytes during and after failures; successful replacement inherits none of those authorities and retains its actual final directory.
Predicts: current failure scenarios erase old files; staged initialization followed by successful publication preserves old history on all pre-publication failures and normal exact binding on success.
Against: history changes before successful initialization, failed start retargets another window, staged paths remain in the saved session, or successful replacement inherits old authority.
Refs: results/session-continuation-20261111/

## SCN2 · prediction · 2026-11-11 00:10
Hypothesis: an action that closes its exact bound modal can deliver normally but the mandatory post-action observation throws, leaving a generic stopped command instead of useful continuation guidance despite retained pending delivery.
Test: public CLI simulated-Mac click or Return delivers once, then exact-window observation fails; preserve pending execution/delivery evidence, original binding and last baseline, report application outcome unverified and give read-only inventory/new exact-session guidance. Include generic observation failure and explicit no-send cases without inferring closure or Save success.
Predicts: current public route ends in generic stopped; repair reports unavailable post-action observation, retains reconciliation evidence and dispatches no retry or implicit parent/new-window action.
Against: closure confirms Save, pending evidence is cleared/rewritten, old observations become fresh, commands silently retarget, or an uncertain input retries.
Refs: results/session-continuation-20261111/
