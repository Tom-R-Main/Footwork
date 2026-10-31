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
