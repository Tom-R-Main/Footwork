# Raw-backend comparison prerequisites and C1

## CR1 · prediction · 2026-10-09 18:23
Question: can the real Chrome DevTools MCP baseline be made reproducible without changing the reference checkout or installing a global runtime?
Hypothesis: the exact published chrome-devtools-mcp 1.10.1 package includes its compiled server and bundled dependencies, and an isolated project-owned npm install with lifecycle scripts disabled can run on the existing Node 22.17.1 and attach to our dedicated fixture Chrome instance.
Alternatives: the published package requires a lifecycle build or an unavailable dependency; its browser attachment differs from the documented browserUrl interface; the native raw MCP cannot be isolated or killed at the actual input-dispatch process.
Test: stage only version 1.10.1 under ignored project output, retain package-lock integrity and executable hashes, inspect the CLI version/help and MCP initialize/tool catalog, then bind/read the owned fixture browser. Qualify the pinned cua-driver 0.28.2 native MCP separately against the same scoped TextEdit document through its public observations/action/readback. No provider calls during prerequisite qualification.
Predicts: the release initializes over stdio with its true server identity, exposes a usable page snapshot, reads the exact fixture value, and the native baseline can append/read the exact expected value using only task-owned resources. No global install/config changes or reference checkout edits are needed.
Against: startup requires scripts/global changes, fails on the existing Node version, cannot attach/read the exact fixture, or raw native execution cannot be scoped and identified for the interruption gate.
Refs: docs/experiments/C1-capability-slice.md; docs/notebook/2026-10-09-capability-slice.md:S-CS; /Volumes/External SSD/referencerepos/chrome-devtools-mcp/package.json; scripts/capability_baseline_runtime.py

## CR2 · exploratory · 2026-10-09 18:23
Question: can the fixed C1 lost-reply interruption and stale-target treatments be implemented fairly through the real Claude host for both arms?
Test: independent peer audit of C1, actual host restart behavior, arm-neutral relay and owned-fixture interference. Commit the runner, fixed task manifest, model/effort, counterbalanced schedule and budget before paid measurement. Record setup interventions, failures and exclusions; do not fix either measured product mid-run. Ceiling: $1 per session, $30 total CLI-reported spend, with a stop when costs are unavailable or the aggregate budget is exhausted.
Refs: docs/experiments/C1-capability-slice.md; scripts/capability_host_trial.py; scripts/capability_interrupt_trial.py

## CR3 · prediction · 2026-10-09 18:27
Question: why did the first comparison fixture fail before publishing scope?
Hypothesis: WindowServer briefly lists a newly opening TextEdit window before Accessibility can resolve it; the fixture's readiness loop treats that transient window_missing exception as fatal rather than waiting for the exact AXDocument identity.
Alternatives: the fixture can never be resolved through AX on this host, or permissions/document identity are wrong rather than temporarily absent.
Test: retain the first failed launch (output/capability-comparison-20261009-1826), catch only ax.AXError with reason window_missing during discovery, then launch a fresh owned fixture and require its exact document identity and independent AX prefix readback. Other AX errors still fail and the existing 30-second deadline remains.
Predicts: the fresh fixture reaches ready with exactly one owned browser window and one exact AXDocument match; independent AX reads the original prefix without any permission change or input action.
Against: discovery still times out, identifies another document, or needs a permission/configuration change.
Refs: scripts/capability_fixture.py:scope_for; output/capability-comparison-20261009-1826
