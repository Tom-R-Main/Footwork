# Pinned Linux Lightpanda preparation

Notebook times use America/Detroit; machine receipts retain UTC. Prior PR18 histories are unchanged; preparation uses a separate local evidence worktree/branch.

## LPVM0 · prediction · 2026-10-31 16:04
Hypothesis: public GitHub asset694146173 (lightpanda-io/browser, lightpanda-x86_64-linux) matches the pinned77,129,032-byte SHA25619f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3 and can report version/help on this native Linuxx86-64 VM without installation/source build or enabling any Footwork browser route.
Test: download only this public prebuilt into a new owned scratch directory, preserve metadata/download outcome, and verify exact size/hash BEFORE chmod/execution. Use LIGHTPANDA_DISABLE_TELEMETRY=true and LIGHTPANDA_DISABLE_CORE_DUMP=1 plus child-only RLIMIT_CORE0. Execute only --version and --help once each under10-second bounds, capture stdout/stderr/numeric exit and actual OS/CPU/memory/PID/cgroup facts. Do not use the nightly tag target as source identity: record binary-reported git version and actual digest. No system installs, source builds, permissions, models, new cloud/VM resources or candidate qualification; wait for exact Footwork SHA/wheel/recipe. No socket/read-target/action/reconnect probe is authorized in this preparation.
Predicts: the exact Linux artifact verifies and both metadata commands exit0; reported version/digest are retained independently of tag anchoring. Actual current4CPU/16GiB envelope remains recorded rather than assumed2CPU/8GB.
Against: size/hash mismatch prevents execution, wrong architecture, nonzero/signal/timeout on metadata commands, persistent owned residue, or source identity inferred from a mutable/nightly tag instead of observed binary data.
Refs: https://api.github.com/repos/lightpanda-io/browser/releases/assets/694146173; results/lightpanda-vm-20261031/preparation/; parent branch codex/lightpanda-readonly basedc85ac85 is not yet a qualified candidate

## LPVMU0 · update · 2026-10-31 16:06
Resolves: LPVM0 = failed
Observed: public API download returned200/octet-stream, exactly77129032 bytes/hash19f3fee2, ELF64 x86-64, all verified before execution. The guessed --version option exited1 with unknown-command/did_you_mean=version; --help exited0 and explicitly documents version as a subcommand. No signal/timeout, no owned descendants, binary hash unchanged. The helper correctly returned1 for the unsuccessful metadata invocation; this is not a Footwork candidate failure. Original outputs and numeric exits remain retained.
Next: execute only the documented version subcommand under unchanged safety flags/bounds; no help rerun, read route, socket, target or action probe.
Refs: results/lightpanda-vm-20261031/preparation/commands.json; results/lightpanda-vm-20261031/preparation/version.stderr.txt; preparation/help.stdout.txt

## LPVM1 · prediction · 2026-10-31 16:06
Revises: LPVM0
Hypothesis: this pinned binary reports its actual git version through the documented version subcommand rather than --version.
Test: reverify the same artifact size/hash before one invocation of version, retain the earlier rejected flag and successful help separately, use telemetry=true-disabled/core=1-disabled and child RLIMIT_CORE0 with10-second bound. No other program mode is invoked.
Predicts: version exits0 and reports a build/git version suitable for exact-binary provenance without assigning the nightly tag anchor as source.
Against: nonzero/signal/timeout, altered artifact hash or persistent owned residue.
Refs: pinned asset694146173; results/lightpanda-vm-20261031/preparation/version-subcommand.json

## LPVMU1 · update · 2026-10-31 16:08
Resolves: LPVM1 = held
Observed: documented version command exits0 and reports1.1.0-nightly.11423+56980afde. The original --version exit1 and --help exit0 are retained, all under identical telemetry/core settings and10-second bounds. Verified asset694146173 is77129032-byte ELF64x86-64/hash19f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3 before/after execution. No timeout/signal or owned descendants. Actual AMD EPYC9V74 model,5 visible CPUs/affinity0-4 but4-CPU quota,16GiB memory cap, uncapped cgroup PID/swap with observed pids.current62 and actual swap0 are recorded. No source build/install/system permission/model/resource change occurred.
Inferred: this exact Linux artifact is usable for CLI metadata in the current VM. Reported git suffix56980afde/digest are the identity, not the nightly tag target. This is not Footwork read-route or light-install qualification.
Next: keep the owned binary and local evidence separate from PR18, and await exact candidateSHA/wheel/test recipe before any socket/target/DOM/read test. No candidate was fetched or executed in this preparation.
Refs: results/lightpanda-vm-20261031/preparation/report.md; results/lightpanda-vm-20261031/preparation/version-subcommand.json; prior PR18 evidence7a874eb

## LPVMS0 · summary · 2026-10-31 16:08
Established: pinned public Linux prebuilt verifies exactly and reports1.1.0-nightly.11423+56980afde; original rejected flag and documented metadata results, digest, host policy and empty owned cleanup are retained. Preparation is ready without modifying prior artifacts or installing dependencies.
Uncertain: no pushed Footwork candidate, one-shot Unix socket/read semantics, DOM limits, source-build provenance or cross-architecture runtime parity has been tested. The current larger VM is not a2CPU8GB profile. The known OBS desktop/runtime limitation and Mac-only evidence remain separate.
Decision: stop at authorized metadata preparation and wait for exact Footwork candidate/recipe; parent owns source implementation/review/PR/merge. No further mode, mutation, script or reconnect probe is warranted now.
Refs: results/lightpanda-vm-20261031/preparation/report.md

## LPLINUX1 · prediction · 2026-10-31 16:35
Hypothesis: exact pushed d9ca03ee60d0f4f7f066a734113f361ae87cd2c3 with the pinned Linux engine supports a fresh process/private authenticated Unix socket and one explicit real target/connection for bounded DOM-only reads, without input authority/reconnect or regression of the existing installed CDP gate.
Test: isolate source unchanged, build the pure wheel and require SHA25690790706d08d4799dc4a9a0559a74d575b7a89026bf6cf4ca4e1f12db0052909. Fresh minimal consumer: binary pytest8.4.2/psutil7.2.2/websockets15.0.1/packaging26.3, product --no-deps, no CUA/browser-use. Copy exactly15 modules parsed from candidate .github/workflows/cdp-observation.yml unchanged outside checkout; set installed FOOTWORK_EXECUTABLE/matching Python, pinned FOOTWORK_LIGHTPANDA_EXECUTABLE, JEVDUAL_PURE_PY1 and real Chromium ELF, unset PYTHONPATH/no checkout conftest. Reverify engine size77129032/hash19f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3 before execution, with disabled telemetry/core and child RLIMIT_CORE0. Run one full batch under unchanged600-second wrapper bound; retain counts/all skips/failures, real public CLI observations/errors, fixture GET/POST lists, two password-length negatives, single navigation/method allowlist, slow timeout, SIGTERM client, captured forced-engine-loss cleanup uncertainty and all prior restart/startup controls. Extend only passive fixture receipt capture, never candidate/test code. Capture actual4CPU16GiB/PID facts and test-only nested/outer subreaping separately. Do not attempt optional2CPU8GiB without an already delegated reversible resource boundary; no new permissions/resources are needed.
Predicts: all collected supplied cases pass with no skips, exact installed origins/digests match, positive JavaScript text is readable without private/editable/password values or length, POSTs stay empty, no input/raw-script/reconnect fallback is exposed, and pre-test-cleanup liveness checks/owned final cleanup remain truthful.
Against: any failed/skipped case, leaked private data/length, POST/input/mutation authority, wrong source or artifact, replay/reconnect, fabricated layout/visibility/AX, or live owned residue. Failures must be preserved/reported without implementation patching.
Refs: candidate d9ca03ee60d0f4f7f066a734113f361ae87cd2c3; results/lightpanda-vm-20261031/d9ca03e/; pinned asset694146173; prior metadata prep135e124; prior PR18 histories7a874eb

## LPLINUXHTTPS1 · exploratory · 2026-10-31 16:35
Question: can this exact installed one-shot command read https://example.org/ through the VM's existing network/CA policy without retries, and what observation/cleanup can it actually attest?
Test: after the supplied module batch, issue exactly one installed browser lightpanda read https://example.org/ with --timeout30, explicit verified binary and a fresh private short owned work directory; independent outer watchdog70 seconds. Preserve complete stdout/stderr/numeric exit, protocol methods, engine identity, DOM scope/input/completion fields and pre/final owned cleanup. Existing proxy/CA settings are retained; no TLS bypass, network policy change, source/model/cloud operation, read retry or reconnection. A reachability/TLS/capture failure is a retained boundary rather than a reason to repeat website effects automatically.
Refs: exact installed d9ca03e/90790706 wheel; results/lightpanda-vm-20261031/d9ca03e/https-example/; existing network policy
