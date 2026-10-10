# R1: qualified read-only restart reconciliation

A developmental correctness qualification of the scoped native TextEdit append capability. User authorized implementation/reference inspection/Claude review. No heldout split, C1 regrade or general recovery benchmark.

## Hypothesis
An independently owned fixed-action dispatcher can preserve a qualified receipt across MCP parent death. Restarted status can reconcile supported operations without sending input. Matching current text without a causal execution receipt remains insufficient.

## Design and primary criterion
Required cases: parent death at prepared-before-start, during dispatcher execution, after durable dispatcher receipt but before journal finalization, and after final journal commit. Include worker death before receipt; delayed worker with an identical externally written target; receipt digest/nonce/version corruption; original process-start/document inode/AX role/frame/ambiguity replacement; private/migrated legacy journals. Offline scenarios/subprocesses qualify mechanisms first; real owned TextEdit cases qualify the native boundary. Record exact committed implementation/harness hashes, original stages, owner identities, artifact durability, receipt match, public status/repeat behavior and an independent AX oracle.

Primary criterion: every required outcome obeys the preregistered rule, with zero incorrect applied resolutions and zero repeated input from restart/status/token collection. Parent mid-dispatch with completed qualified worker receipt must recover; started/no receipt and identity loss must remain unknown and blocked even when current text matches. Prepared-only or explicit no-send receipt is the only basis for non-delivery. Original final records return historical results.

## Guardrails and decision
No overwrite of an external edit, no effect outside the owned document, no adoption/kill based on PID alone, no fallbacks to absent-as-empty, no automatic retries, and no unknown-to-known claim based on quiet intervals. An unmet required live case is unverified/inconclusive, not passed by mocks. Proceed only when all required cases pass and concrete Claude findings are addressed. Preserve failures and start a new version after source changes; never prune counterexamples or tune thresholds. New examples supplement rather than replace failed cases.

Model-free checks are primary. Mailbox Claude review is authorized; if unavailable, at most two fresh tool-less canonical Opus5.5/high reviews with requested $1 soft CLI cap and $6 aggregate scheduling reserve may be used. Account for actual reported cost; missing cost stops further calls. No install/fetch/global configuration/permission change/push/public release.

## Result

Appended after qualification.

## Amendment · 2026-10-10 12:10 · before runs

A valid qualified completion receipt resolves **historical applied** even if current identity/content changes afterward. Current agreement is reported separately; this supersedes current-match gating in the original design and expected rules. Add the counterexample: completed receipt followed by external edit must resolve historical applied without changing that edit. Started/no receipt, including identical external text, remains unknown. Before implementation, detached worker feasibility and startup latency are measured on the owned native fixture. Custody uses a per-attempt flock; absence of a lock or input_started marker does not prove a launched worker will never run.

## Amendment · 2026-10-10 12:23 · before safe-save/deadline tests

Strict inode/device matching applies before input. After input and in current AX agreement, boot/process start/document path plus qualified field suffice; autosave metadata is retained separately. Add a post-input safe-save identity case and pre-input same-path inode replacement refusal. Add bounded parent wait and a synchronized worker self-deadline: timeout before admission reports not_sent only if later admission is fenced out; timeout after input admission reports unknown. A deadline must not be confused with stopped OS delivery.

## Amendment · 2026-10-10 12:27 · deadline ordering before qualification

Worker deadline is 25 seconds; parent wait is 35 seconds. The separate bounds allow a worker timeout receipt to arrive before the caller wait expires. They replace the earlier equal 30-second values, are recorded starting settings rather than tuned test thresholds, and preserve unknown on any remaining launch/transport gap. Refused as well as not_sent receipts direct callers to observe again and use a new token for a newly intended action; repeating an old token only retrieves its refusal. Live results record unexpected identity_changed refusals rather than retrying them away.
