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

## CR1-U1 · update · 2026-10-09 18:38
Resolves: CR1 = held
Observed: exact published Chrome1.10.1 staged under project output with lifecycle scripts disabled and pinned npm integrity. Install ran with uv's existing Node26.5.1; server help/version and all MCP probes ran on explicitly selected existing Node22.17.1. After the screen unlocked, the owned fixture exposed exact browser and AXDocument identities and its starting prefix. Live raw probe v2 read the exact source value through Chrome snapshot, wrote the owned native field through raw set_value, and independently read the exact expected prefix plus value; reset was verified. The first live probe used an incorrectly entered browser port and a string pageId, so its browser read failed while native write/reset passed. That failed probe is retained; the corrected probe requires a successful browser read before proceeding to native write.
Inferred: the two real pinned raw MCP backends can perform this scoped fixture task. This establishes prerequisites, not agent usability, restart behavior or comparative value.
Next: qualify the relay/host integration on development pairs, then freeze and run C1.
Refs: output/capability-baseline-20261009/runtime.json; output/capability-baseline-live-20261009-v2/receipt.json; output/capability-comparison-20261009-live/scope.json

## CR6-U1 · update · 2026-10-09 18:38
Resolves: CR6 = held
Observed: seven focused subprocess/fixture regression tests passed in 11.73 seconds. The independent file watcher killed the actual fake dispatch child; the host got one generic error, restart replayed initialization only, content appeared once, and a subsequent read succeeded. Catalog drift failed; an unchanged refused write was forwarded but labeled inconclusive. EOF reaped dispatch process groups. Fixture tests preserve exact identity and fail locked startup before files/resources.
Inferred: relay mechanics are established against a separate file-backed fake MCP process. Live AX watcher, real native dispatch, and Claude continuation remain unqualified until development host probes.
Next: commit harness and implementation clarifications before any development provider calls. Independently reviewed Opus5.5 consultation raised host restart, stale oracle and unknown-stop scoring gaps; retained exact oracle and original first-field-change kill trigger rather than its suggested normalization/reply-trigger change.
Refs: tests/test_capability_comparison_relay.py; tests/test_capability_fixture.py; output/capability-comparison-peer-20261009/transcript.jsonl; c547b97

## CR7 · prediction · 2026-10-09 18:38
Hypothesis: the existing Claude host can continue on the persistent relay after one native dispatch interruption with no built-in tools, and the raw host's disallowed-tool configuration removes out-of-scope browser tools from its actual init inventory.
Test: at most three development pairs (clean, interrupted, stale) using the committed runner, fixed first condition in each stratum, canonical Opus5.5/high and the declared budget. Inspect actual init tools/server/model inventories, relay held/dropped/restart events, exact AX oracle and supported final claims. Development pairs are not C1 measurements and are never pooled into its counts.
Predicts: exact four-tool Footwork/seven-tool raw inventories; both interrupted hosts receive the same generic error then can make a fresh read-only call through the restarted backend; stale injection is recorded and oracle preserves the new prefix. Honest stops remain stops.
Against: host loses the entire transport, raw capabilities leak into the offered inventory, a relay repeats an input, or the runner cannot distinguish failed treatment from a measured product failure.
Refs: scripts/capability_comparison_trial.py; docs/experiments/C1-capability-slice.md

## CR7-U1 · update · 2026-10-09 18:42
Resolves: CR7 = inconclusive
Observed: development v1 stopped after its clean pair: Footwork exact completion, raw truthful stop with unchanged document. Both actual host inventories matched the intended four/seven tools and Opus5.5 model. Raw relay repeatedly failed with asyncio StreamReader's 64KB line limit while receiving normal screenshot/tree responses; those errors mark the raw session and pair invalid. After reconnecting and requesting a bounded tree, the raw agent omitted window_id on token-addressed set_value and received the upstream manifest's application-level refusal, then stopped honestly. Total development spend $0.2545796; no C1 session ran.
Inferred: actual inventory isolation works; relay framing failed before recovery treatments could be qualified. The separate token/window manifest nuance is actual upstream behavior, not permission to broaden scope or silently rewrite raw requests.
Next: retain v1; reproduce the large-frame relay failure, increase the bounded transport limit, then start a new development version.
Refs: output/capability-comparison-dev-20261009-v1; e00818b

## CR8 · prediction · 2026-10-09 18:42
Hypothesis: asyncio's default 64KB stream limit, rather than native backend death, caused raw screenshot replies to terminate the relay; a 32MiB line limit can pass normal native responses unchanged while retaining a finite bound.
Test: add a fake-backend response over 64KB and observe it fail on the existing relay; configure the same bounded limit on child stdout and host stdin, then require exact payload and the existing interruption/no-replay/catalog-drift/EOF tests to pass.
Predicts: the large-response regression fails before the fix and passes after it without schema rewriting or content truncation; no-replay and cleanup tests remain green.
Against: the response still fails, changes content, or removing the 64KB limit allows an interrupted reply or duplicated input to reach the caller.
Refs: scripts/capability_comparison_relay.py; tests/test_capability_comparison_relay.py; output/capability-comparison-dev-20261009-v1/b01-raw/relay/events.jsonl

## CR8-U1 · update · 2026-10-09 18:43
Resolves: CR8 = held
Observed: large-response regression failed on e00818b with EOF after the relay's 64KB reader rejected the frame. With an explicit 32MiB bound on child stdout and host stdin, the exact 100,000-character payload passed. All eight relay/fixture regressions passed in 11.77 seconds; static lint passed. The old development pair remains invalid and retained, not counted or repaired.
Next: new development version to qualify actual host continuation and stale treatment.
Refs: output/capability-large-frame-before.log; tests/test_capability_comparison_relay.py:test_large_raw_response_preserves_every_byte

## CR7B · prediction · 2026-10-09 18:43
Revises: CR7
Hypothesis: the bounded large-frame repair removes the raw host's transport failures while preserving exact four/seven tool inventory and first-field-change restart semantics.
Test: new development run with up to three fixed pairs, identical products/resources/model/budget, never pooled into C1 or replacing the invalid v1 pair. Review init inventories, treatment evidence, exact oracle and supported claims.
Predicts: clean raw observations pass through without connection-close errors; interrupted hosts can call a fresh observation after the relay's generic error; both stale treatments are applied to the predeclared edited prefix. Raw refusal for omitted window identity remains a real tool outcome, not repaired by widening scope.
Against: any transport/framing failure, replayed write, incorrect treatment labeling, or an observation/effect outside the owned resource.
Refs: scripts/capability_comparison_trial.py; scripts/capability_comparison_relay.py; output/capability-comparison-dev-20261009-v1

## CR7B-U1 · update · 2026-10-09 18:47
Resolves: CR7B = failed
Observed: development v2 passed inventory isolation and large-response transport. Clean Footwork completed, raw stopped truthfully on the upstream token/window manifest refusal. The interrupted Footwork call was killed with dispatching intent and one observed insertion, but the relay failed restart because no legacy initialize request was cached; the host independently reconnected and read the exact result. This is an invalid harness trial, not a C1 completion. Total v2 development spend $0.4412844. Independent Opus5.5 code review ($0.5507608, exact model/init recorded) identified candidate-mutation consumption, teardown/oracle races, bidirectional JSON-RPC handling and budget/provenance gaps. Full offline suite passed 1196 tests with 26 skipped on 1c97f94.
Inferred: actual modern MCP uses server/discover with per-request metadata; legacy-only mock startup concealed this restart gap. Bind(destination) does return an observation in this product (one reviewer assumption was incorrect), so it remains a valid destination snapshot.
Next: repair/qualify both lifecycle eras and peer-review blockers before another development run. Products remain unchanged.
Refs: output/capability-comparison-dev-20261009-v2; output/capability-comparison-harness-review-20261009; output/capability-comparison-full-suite.log; python/jevdual/capability/backend.py:bind

## CR9 · prediction · 2026-10-09 18:47
Hypothesis: caching the successful lifecycle request (legacy initialize or modern server/discover) and the original tools/list envelope allows restart without losing protocol metadata; leaving no-change candidate calls untreated avoids arm-dependent exclusions from caret movement or refused attempts.
Test: subprocess regressions for discovery-era restart, candidate no-change followed by a real write, Return/key-based text change, bidirectional roots/list, and teardown before stable readback. Preserve first-field-change kill, complete catalog equality and zero tools/call replay. Add explicit cost upper bounds, pair completeness, clean-tree/module hashes and two equal post-teardown oracle reads. Require all affected checks before a new development version.
Predicts: both lifecycle eras restart transparently; a caret/no-send response is forwarded promptly and does not spend the one interruption; every actual first text change is eligible for the same watcher; host requests/replies cannot deadlock the relay; cleanup precedes reset/readback; partial pairs and unknown cost never produce an eligible comparison decision.
Against: a new handshake changes catalogs, a candidate triggers duplicate dispatch, a backend survives into the next reset, or an invalid/partial run is presented as decision-eligible.
Refs: scripts/capability_comparison_relay.py; scripts/capability_comparison_trial.py; docs/experiments/C1-capability-slice.md

## CR9-U1 · update · 2026-10-09 18:52
Resolves: CR9 = held
Observed: ten relay/fixture tests passed in 2.61 seconds, including modern discovery with preserved catalog metadata, independent first-change kill, no-change candidate followed by one real insertion, roots/list backchannel, large frame, catalog drift and EOF retirement. Both native input keys are now eligible mutation candidates; destination observation is scoped; missing cost has an explicit upper bound/stop and partial pairs have named completeness. Runner hashes core/harness/lock modules and refuses dirty measurement. Product code remains unchanged.
Inferred: repaired mechanics address the independent Opus code-review blockers on subprocess cases. Actual host/AX continuation is still a development prerequisite. The common prompt adds explicit PID+window binding rather than broadening the raw manifest or rewriting raw tool arguments.
Next: freeze a new development version and run one clean/interrupted/stale pair; prior paid spend $1.4595798 is recorded toward the aggregate ceiling.
Refs: tests/test_capability_comparison_relay.py; scripts/capability_comparison_trial.py; docs/experiments/C1-capability-slice.md

## CR10 · prediction · 2026-10-09 18:52
Hypothesis: the repaired relay and identical explicit resource-binding task instruction let both actual hosts reach the intended live treatments without transport loss or widened authorization.
Test: development v3, at most three fixed pairs, same real fixture and products, canonical Opus5.5/high, $1/session and $30 aggregate including prior spend. Inspect actual lifecycle eras, inventory, kill-time content, catalog equality, backend retirement, stable independent readback and claim evidence.
Predicts: both arms operate only on the scoped document; interruption reaches a qualified held/dropped event and the same persistent transport permits later read-only calls; stale treatment preserves its predeclared oracle prefix. Honest stops and incorrect content remain visible.
Against: missed treatment due framing/handshake/configuration, leaked capability, replayed input, ambiguous retirement/readback or unsupported completion promoted to success.
Refs: scripts/capability_comparison_trial.py; scripts/capability_comparison_relay.py
