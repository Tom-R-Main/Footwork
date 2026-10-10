# Durable restart reconciliation: a bounded native dispatcher

User authorization: implement restart reconciliation, inspect the named reference repos and have Claude review. This extends the existing four-tool scoped TextEdit slice. It does not implement a planner, generic daemon, another surface, disk-saving verification, or a new C1 comparison. Reference and review details are recorded separately.

## Caller contract

A caller sends act once, then uses status(operation, reconcile=true) after a lost reply. Status never submits input, restarts an attempt or adopts another process for execution. A retained final record is historical evidence. A new readback is explicitly current-state evidence. An unknown attempt keeps the resource blocked even if current text matches, unless a qualified durable execution receipt justifies resolution.

## Alternatives

1. Persist the validated before/expected values and look again after restart. Rejected as authority: matching text cannot prove who wrote it or exclude late input.
2. Add a same-server dispatch-completed checkpoint. Useful for the post-return/pre-final gap, but a SIGKILL during native dispatch still destroys the only receipt writer. It cannot recover the motivating mid-server interruption.
3. Use one independent, fixed-action native dispatcher per admitted append. Chosen for implementation/review: it can retain execution custody and persist a receipt when the MCP front end dies. It executes one immutable authorized packet, then exits. No daemon, arbitrary command, model decision, worker retry or action replay is exposed.

## Durable records and ownership

- Extend the owner-only SQLite intent with a versioned recovery envelope and prepared/started execution stage. Intent remains committed before input; mark started before launching the dispatcher. Legacy rows migrate with no recovery envelope and stay conservative.
- Envelope: task/scope and resource fingerprints; random attempt nonce; route version; original boot session, application PID/start-time identity, canonical document path/device/inode, native AX role and required frame; exact before/expected content hashes and lengths; separator policy. The operation already stores the literal payload. Do not persist live Cua tokens, Python contexts, CF pointers or presentation labels as durable identity.
- Derive a private execution directory from the journal and operation ID. Packet/result paths are not caller arguments. Write immutable bounded JSON through exclusive private temporary files, fsync, atomic replacement and directory fsync. Packet digest and nonce bind registration/result to that single intent. Reject malformed, legacy, inconsistent or symlinked artifacts; storage failure never permits unrecorded input.
- The dispatcher uses the existing ScopedBackend/NativeBridge exact append route. It freshly checks identity, before text and insertion capability, performs the append once, checks exact effect/readback and identity again, and persists a terminal receipt before returning. Its only resource is the original scoped document; it does not bind/read a browser.
- Its process has independent lifetime from MCP. A registration records precise kernel PID-start identity, not PID/liveness alone. No parent cancellation/timeout is treated as proof of stopped execution. Pending/no receipt remains unknown; cleanup can target only attested owned workers. Persistent result retrieval does not reattach or execute.

## Reconciliation rules

| Evidence | Restart outcome |
|---|---|
| Valid prepared intent, never marked started | Known not_sent; no input was admitted |
| Started, no matching terminal receipt | Unknown and blocked; report pending/unknown custody and qualified current postcondition separately |
| Matching receipt definitively reports refusal/no send | Known refusal/not_sent; absence of text alone never substitutes for this receipt |
| Matching completed exact native effect receipt plus qualified same-scope current identity and expected text | Resolve applied by retained execution evidence + fresh readback; preserve unknown/history |
| Completed receipt, but app/document/field identity or current postcondition changed | Unknown and blocked; do not overwrite intervening edits or infer the same incarnation |
| Legacy/malformed/unknown-version/digest mismatch | Unknown and blocked; no fallback to best-effort PID or preview |
| Final commit already durable, reply lost | Return retained historical result without dispatch |

Current identity is deliberately bounded: boot session, application process start, document file identity and unique observed field role/frame. This is not a universal serialized GUI incarnation proof. Unsupported/missing identity stays unknown; tests challenge boot/PID start, document replacement, field role/frame/ambiguity and identical external writes. No global exactly-once guarantee follows from GUI accessibility APIs.

## Implementation sequence

1. Commit experiment/predictions before scenarios. Reproduce restart loss on the public capability boundary.
2. Implement bounded recovery schema/identity and immutable private execution artifacts, then compatible journal stage/migration.
3. Implement one-action worker and backend read-only recovery; wire service admission and receipt-only reconciliation. Generic backends retain conservative legacy behavior.
4. Run public scenarios, real subprocess parent/worker death tests, delayed worker and identical-external-write counterexamples, migration/privacy/invalid-artifact tests and required suite/lint.
5. Claude reviews design and final implementation independently through the authorized mailbox. Retain disagreements and repair concrete findings before qualifying.
6. Freeze code and run real owned TextEdit/MCP interruption cases. Keep originals and failures, no heldout or C1 rerun. Clean only owned UI/processes and preserve evidence.

## Acceptance and limitations

Required: no input from status/restart; no duplicate launch for a repeated token; no unknown-to-applied transition from text alone; incomplete/delayed execution remains blocked; qualified receipt allows a parent-crash recovery; replacements/malformed records are refused; legacy journal opens safely; private files and durable writes are verified. No success is claimed if live interruption is unreachable. File persistence and broad installation/platform support remain unqualified.

## Amendment · 2026-10-10 12:10 · Claude design review

Adopt P1/R3/D6: a matching qualified completion receipt establishes **historical applied**, even after a later edit, application restart or document replacement. Fresh current agreement (yes/no/unverifiable) is separate and never the gate for that historical result. This supersedes the current-identity/current-text gates above. The worker itself must qualify identity and exact before/after at execution time. Retain the receipt and unknown transition in history. New actions still require fresh targets and exact validation.

Adopt P2: before schema/dispatcher implementation, run a model-free detached-child AX append probe on an owned fixture; measure startup and total append latency. Failure of TCC/AX access blocks this design, rather than producing an apparent pass in mocks.

Adopt P3 with a caveat: a per-attempt flock supplies readonly execution custody; registration also records PID/start-time solely for attested fixture cleanup. An unlocked attempt with no receipt is still unknown after launch admission: a not-yet-scheduled child could run later. Never infer not_sent from absent lock/receipt. Adopt P5: normal and restarted paths consume the same immutable receipt. A worker input_started marker improves diagnostics but absence alone cannot resolve a launched attempt.

Retain D1 as a complementary future option: graceful drain reduces interrupted replies, but does not cover the explicitly authorized parent SIGKILL case. Continue the independent fixed-action dispatcher if the feasibility probe succeeds. Process crash qualification only: neither fsync nor SQLite FULL here claims power-loss protection or universal exactly-once GUI behavior. A worker death before its completion record remains unknown.

Claude source: mailbox messages 1791647977465490000, 1791648203802365000 and 1791648499247640000. Claude also reviewed the earlier C1/text repairs: no blockers; condition-level analysis, non-discriminating interruption fixture and long-document frame changes belong in future comparison/probing, not a rewrite of frozen C1 outcomes.

## Amendment · 2026-10-10 12:23 · implementation review

Claude B1: NSDocument safe-save can replace inode without replacing the live document. Keep exact device/inode identity as a **pre-input** guard (replacement there refuses). After confirmed input, qualify boot/process start/canonical document path and the original field/readback, while retaining changed disk metadata as information. A safe-save must not turn affirmative execution evidence into unknown. Current agreement concerns the AX field, with persistence still not_checked. This supersedes strict post-input/current inode equality. Add a simulated safe-save inode change after input; historical applied and current agreement remain qualified when the scoped live document/field is unchanged. Same-path replacement before input still refuses.

Claude B2/M1: parent wait is bounded (30 seconds) and returns unknown without killing the effect owner. Worker self-deadline (30 seconds) has a synchronized admission fence: before input, timeout can retain not_sent and exit; once the fence admits input, timeout retains unknown and exits. A watchdog must never publish not_sent while another thread can still enter input. Declare the already-installed/pinned psutil dependency without fetching. Per-operation retention/pruning is deferred; retained packets are private task content and must be kept with their journal until an explicit retention policy exists.

## Amendment · 2026-10-10 12:27 · deadline ordering before qualification

Worker deadline is 25 seconds; parent wait is 35 seconds. The separate bounds allow a worker timeout receipt to arrive before the caller wait expires. They replace the earlier equal 30-second values, are recorded starting settings rather than tuned test thresholds, and preserve unknown on any remaining launch/transport gap. Refused as well as not_sent receipts direct callers to observe again and use a new token for a newly intended action; repeating an old token only retrieves its refusal. Live results record unexpected identity_changed refusals rather than retrying them away.
