# Durable restart reconciliation: qualified scoped native recovery

Implementation and harness: `8a407f1`. Pre-registration: `7a11341`, with dated amendments before the corresponding tests. Fixture-prerequisite correction: `320c3b0`. This is a model-free correctness qualification of the TextEdit append slice; original C1 and heldout results are unchanged.

The MCP parent now commits an intent and launch admission, then starts one detached fixed-action worker. The worker checks the original scope, exact prefix, app/process/document/field identity, appends once and retains a private completion receipt. Normal calls and restarted status consume the same receipt. A qualified receipt confirms historical execution; fresh current agreement is separate. Matching current text alone cannot clear uncertainty. Status and repeated tokens never launch input.

## Evidence

- Full offline suite: **1265 passed, 26 skipped**, 94.67 seconds. Ruff, notebook validation and offline lock consistency pass (`checks.json`). Forty-eight new store/public-native/subprocess cases exercise migration, private immutable records, binding corruption, identity changes, cancellation, worker exceptions and pre-/post-admission deadlines.
- Both deliberate branch mutations failed the corresponding tests; original worker source was restored byte for byte (`mutations.json`).
- Detached actual AX feasibility: exact independent oracle passed. Spawn-to-import 0.0574 seconds; total bind/validate/append/readback 2.2170 seconds (`detached-probe.json`). No in-process matched latency comparison was run, so this is the measured worker total, not an estimated overhead difference.
- Fresh actual MCP/native matrix: **12/12 passed** (`native-v2.json`). Every case's owned worker cleanup passed. No duplicate append or overwrite of the external edit was observed. No unexpected identity refusal occurred in this matrix; this does not estimate a population refusal rate.

| Actual parent/worker boundary or counterexample | Collected result |
|---|---|
| Parent dies after prepared intent, before launch admission | not_sent; same token retrieves only |
| Parent dies after launch admission, before spawn | unknown; conflicting append blocked |
| Parent dies with original native dispatch return held after actual append | applied from surviving worker receipt |
| Parent dies after durable worker receipt, before journal finish | applied from retained receipt |
| Parent dies after final journal commit, reply uncollected | retained applied; no new input |
| Parent dies while worker remains delayed | unknown while active; applied after completion |
| Worker dies before its receipt | unknown; no-send is not inferred |
| Dead worker plus identical external text | unknown with current agreement yes; conflicting append blocked |
| Completed receipt followed by later user edit | historical applied, current agreement no; edit preserved |
| Completed receipt's nonce corrupted | unknown and blocked |
| Same-path file replaced before worker verification | authoritative refused; no append |
| Delayed live worker plus identical external text | unknown/current yes/active before release; authoritative refused after exact precondition guard; no duplicate |

The delayed workers' estimated start-to-first-release durations were 2.520 and 2.487 seconds, derived from kernel process-start time and APFS release-file birth time. Both were below the 25-second worker deadline. Source hashes, derivation and the final owned-window sheet count (zero) are in `qualification.json`. The case following file replacement successfully reset/read the exact scoped field and completed its full counterexample; no sheet impeded that case.

## Preserved failures and corrections

Native v1 passed ten cases, then stopped **before replacement** at a harness safety guard: the owned fixture was under results, while replacement is permitted only under project output. The final delayed-identical case was not attempted. `native-v1.json` retains this invalid run. A new output fixture and the same frozen source ran the entire twelve-case v2 matrix; individual cases were not retried or dropped.

The first moved-frame scenario exposed that AX resolve ignores frame for a sole role candidate. Current agreement now explicitly checks the frame. The first after-input deadline test used a packet frame that did not match its simulated field and therefore refused before the intended deadline; aligning the fixture made both deadline branches reachable. Earlier baseline teardown had a double-close error. These failures and corrections remain referenced in the notebook and private output logs.

Owned v1 and v2 AX windows and browser processes are confirmed gone; every trial worker is attested and gone (`fixture-v1-cleanup.json`, `fixture-v2-cleanup-correction.json`). An additional cleanup comparison failed because it used an on-screen-only window inventory, which changes when closing a window exposes another. That observer failure remains in `fixture-v2-cleanup.json`. Preservation of all unrelated window identities/content was not measured; no such claim is made. The cleanup route closes only the exact run-owned document and browser.

## Review and reference basis

Claude Code independently reviewed design, implementation and branches through the authorized Footwork mailbox. The reviewer attested its configured model as `claude-opus-5-5` (Opus 5.5). Design corrections adopted before tests: historical completion separated from current state, safe-save inode changes separated from live post-input identity, bounded worker/caller deadlines and refusal guidance. Final implementation review of `696a641..8a407f1` found no blockers, conditional on this live evidence. Final evidence sign-off is recorded separately after review.

Reference solutions and exact local revisions are recorded in `docs/plans/reference-restart-reconciliation-20261010.md`: Hermes transactional admission/read-only result restoration; Opencode write-ahead execution ownership; Cua effect/transport separation; MCP cancellation/replay boundaries; Codex process custody. These are independently implemented ideas, not copied reference code. Footwork remains MIT; existing dependency licenses still apply. psutil 7.2.2 is now explicitly declared; its already-locked package/version was unchanged and lock consistency was checked offline. No install/fetch, new provider trial, global config, permission change, push or public release was performed.

## Limits and next work

Actual parent SIGKILL is tested at controlled operation boundaries. The delivered case holds the original native dispatch return after one real append; killing inside the AXSelectedText OS call itself was not separately synchronized. Boot/app replacement and malformed/version/digest/role/frame/ambiguity cases are challenged at simulated OS boundaries. Worker timeouts use real subprocesses with simulated unresponsive OS reads; no live shared app was frozen.

A worker death after input but before its receipt remains unknown. No power-loss, disk-save, arbitrary-app, parallel-host, hostile-local-owner or exactly-once GUI guarantee follows. Strict pre-input inode checking can refuse legitimate autosave replacement; re-observe and use a new token for a newly intended action. Execution packets remain private beside the journal; retention/pruning and a reusable warm worker are future design work.

The four public tools are unchanged, but a fresh agent usability trial on the new receipt wording and latency has not run. The next package is first-use setup and a doctor command, before widening actions, apps or platforms.

Final evidence review: Claude Opus5.5 approved R1 in mailbox message1791650633854041000 after independently checking the hashes, all twelve outcomes/token identities, busy guards and independent oracle values. See `review.md`. Codex also signs off the scoped amended contract; the listed limits and future work remain.
