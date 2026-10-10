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
