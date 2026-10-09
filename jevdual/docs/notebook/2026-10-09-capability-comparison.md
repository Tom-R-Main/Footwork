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

## CR3-U1 · update · 2026-10-09 18:26
Resolves: CR3 = inconclusive
Observed: the second owned fixture timed out after 30 seconds. A separate read-only posture probe reported Accessibility trusted true and CGSSessionScreenIsLocked true; no owned AXDocument was exposed. No scope was published, no append or provider call ran. Both launchers exited through cleanup. CR3's heading time was entered ahead of the clock; commit b9d7145 establishes prediction-before-retry ordering, and the actual write was at 18:25.
Inferred: locked-machine posture explains missing AX surfaces; the current evidence cannot establish the opening-window race hypothesis. Waiting for an unlocked desktop is a prerequisite, not a product comparison result.
Next: add a fail-before-launch posture check to the fixture helper; qualify server initialization and catalogs without UI, prepare C1 while waiting for Tom's unlock response.
Refs: output/capability-comparison-20261009-1826; output/capability-comparison-20261009-1828; scripts/capability_fixture.py

## CR4 · prediction · 2026-10-09 18:26
Hypothesis: checking the existing read-only screen lock state and Accessibility trust before creating files/apps prevents another locked-machine fixture launch without weakening its exact document identity requirement.
Test: add a fixture posture precondition and exercise it on the currently locked machine; require a typed readiness error before the requested new run directory exists. An unlocked run remains a separate prerequisite.
Predicts: locked posture refuses before opening Chrome/TextEdit or creating the run directory; no permission dialog is triggered.
Against: a run directory or app is created despite the locked posture, or the check prompts for permission.
Refs: scripts/capability_fixture.py

## CR4-U1 · update · 2026-10-09 18:29
Resolves: CR4 = held
Observed: the fixture launcher returned argparse exit 2 with the unlocked-desktop prerequisite and the requested capability-comparison-locked-check directory did not exist. No Chrome/TextEdit launch or permission prompt occurred. The changed helper also passes static lint.
Next: leave live fixture qualification pending unlock and continue raw MCP catalog qualification.
Refs: scripts/capability_fixture.py

## CR5 · prediction · 2026-10-09 18:29
Hypothesis: cua-driver's capability manifest enforces resource/tool authorization at invocation but does not filter tools/list; its separate immutable YAML policy layer can narrow the advertised catalog to the five permitted native observation/input tools without a custom proxy.
Test: retain the first full catalog (capability-baseline-catalog-20261009-v2), add a trusted project-owned policy containing only get_window_state, set_value, type_text, hotkey and press_key, initialize the same direct raw server and check its catalog. Issue a read-only get_window_state with nonexistent resource IDs outside the manifest; require explicit authorization refusal, never a surface payload.
Predicts: exact five-tool catalog; a call outside the approved window is rejected by bounded resource authorization before observation. Existing driver binary and native tool descriptions remain unchanged.
Against: the installed binary lacks YAML support, still advertises additional tools, or returns an observation for the outside-manifest call.
Refs: scripts/capability_baseline_probe.py; /Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/policy.rs

## CR5-U1 · update · 2026-10-09 18:32
Resolves: CR5 = held
Observed: actual raw MCP catalog probe v3 initialized Chrome DevTools MCP 1.10.1 and cua-driver 0.28.2. The native YAML policy yielded exactly five permitted tools. A read-only request using nonexistent IDs outside the manifest returned bounded_resource_outside_manifest with isError true and no surface payload. Probe v1 failed on this harness's obsolete SDK attribute spelling; corrected to SDK 2.1.1 snake_case fields. Probe v2 exposed the complete native catalog before the policy layer was added. No provider calls in any probe.
Inferred: native execution scope and advertised-tool scope are distinct controls. Both can be narrowed using real driver configuration, without rewriting its tool schemas or dispatcher.
Next: live browser/native read-write qualification remains pending unlock; continue the C1 relay.
Refs: output/capability-baseline-catalog-20261009-v3/receipt.json; 020c596; scripts/capability_baseline_probe.py

## CR6 · prediction · 2026-10-09 18:32
Question: can a persistent stdio relay carry identical lost-reply semantics across both real native backends without replaying an input?
Hypothesis: retaining the host transport while killing/reinitializing only the dispatch subprocess lets the host receive one generic connection-loss error and continue through the unchanged catalog; the relay never needs to re-send a tools/call.
Alternatives: host JSON-RPC IDs collide with relay initialization, catalog changes after restart, a buffered input is sent twice, or simultaneous replies leak the held result to the host.
Test: a subprocess fake MCP backend that writes an independently observed file, and a separate watcher process. Forward a native observation, send one mutating request, hold its reply, kill the backend on the first file change, restart with original initialize params, compare tools/list, and require exactly one host error plus subsequent read-only observation. Also exercise stale-prefix injection, EOF cleanup, unchanged/refused writes and a catalog drift refusal. Real raw-route qualification is separate.
Predicts: file changes once; no successful mutating reply reaches the host; exactly one error is returned; restart replays initialization only; the next observation reports the changed file; stale injection preserves the edited prefix; backend process groups are reaped.
Against: duplicated content, leaked held reply, mutation replay, silently accepted catalog drift, or a surviving child/watcher after host EOF.
Refs: scripts/capability_comparison_relay.py; tests/test_capability_comparison_relay.py; docs/experiments/C1-capability-slice.md
