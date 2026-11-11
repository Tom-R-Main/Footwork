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

## SCN3 · update · 2026-11-11 00:14
Resolves: SCN1 = held
Observed: all four public failed-replacement scenarios failed before the fix. Replacement initialization now runs in an owned temporary session, preserving existing JSON/log/carry/destination/grant bytes during binding, observation and driver cleanup. Six focused replacement cases cover failures, successful publication without old authority, and publication rollback. All 49 affected start/schema checks and Ruff pass.
Next: freeze the failed-start preservation change separately, then resolve SCN2. Root will run integrated regression after concurrent packages are stable.
Refs: results/session-continuation-20261111/start-baseline.txt; results/session-continuation-20261111/start-focused.txt

## SCN4 · update · 2026-11-11 00:19
Resolves: SCN2 = held
Observed: three public post-action readback scenarios initially stopped generically with exit 7. Six ordinary/durable cases now return explicit unresolved exit 6 after one delivered or refused action, retain pending delivery and the last pre-action observation, log observation unavailable without raw driver detail, and give exact inventory/fresh-session guidance. Durable replay reuses the unchanged authoritative execution without another driver read or input. No receipt or closure/Save-success inference is created. All 610 affected checks and Ruff pass.
Changes: failed-start source is d8e8d30; the earlier e456fd0 contains only its notebook/results. Seven replacement scenarios additionally qualify browser directory/tab and screenshot preservation, successful publication without prior authority, and rollback. Numeric integration is independently committed as fad0bb2 and was preserved.
Next: freeze post-action continuation for root-owned integrated regression; do not run a redundant independent full suite.
Refs: results/session-continuation-20261111/continuation-baseline.txt; results/session-continuation-20261111/continuation-scenarios.txt; results/session-continuation-20261111/focused.txt

## SCN5 · summary · 2026-11-11 00:19
Established: refused or failed replacement starts preserve old session records until successful initialization/cleanup/publication, with rollback on publication failure. Unavailable post-action observation preserves pending delivery, exact binding and stale-baseline status, emits no application-effect receipt and performs no automatic retry or retarget. Seven replacement and six continuation cases pass; 610 affected tests pass.
Uncertain: the worker performed no live native UI. A missing observation does not prove modal closure, a saved artifact or a successful application operation. Generic failure reasons remain deliberately separate from retained authoritative delivery; root owns integrated regression and actual Studio qualification.
Decision: close the two generic lifecycle fixes in separate source commits, with no native.py/parser changes, app-specific branches, UI/network/install/global activation or targeted-key expansion.
Refs: results/session-continuation-20261111/report.md
