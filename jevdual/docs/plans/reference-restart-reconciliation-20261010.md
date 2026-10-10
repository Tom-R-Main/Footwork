# Reference solutions for process restart reconciliation

Local source inspection only; no fetched updates or copied upstream implementations. Footwork remains MIT; ideas are independently implemented. Pins identify the local checkouts reviewed on 2026-10-10.

| Reference | Local revision | Relevant source | Adopted / rejected |
|---|---|---|---|
| hermes-agent (MIT) | a62979dc3601c9eae455bff5b35ba8f9bed0df30 | gateway/platforms/api_server_run_idempotency.py:122; tools/process_registry_results.py:48; tools/process_registry_checkpoint.py:77; utils.py:291 | Adopt transactional reservation, readonly restoration of completed results, private atomic files. Reject memory fallback, legacy PID-only liveness and invented exit status. |
| opencode (MIT) | 7b3d4ce3a7dbd2a6d3637722a0d5f22a7d086937 | packages/core/src/session/execution.ts:76; execution/restart.ts:47; persistent-pty/daemon.ts:201 | Adopt write-ahead admission and exclusive ownership. PTY reattachment does not prove a GUI effect. |
| cua (MIT) | ac967b9006aafa10870aadb5a645b038cba9721a | cua-driver-core/src/action_record.rs:252; cua-driver-sdk/src/runtime.rs:163; recording.rs:1017 | Separate effect, transport and attempt evidence. Drain is complementary. Recording rename without fsync is not a durable effect ledger. |
| mcp-rust-sdk (Apache license transition) | 4048ac40e958fb1a7d614617a2ae8d26666ee2fa | transport/streamable_http_server/session/store.rs:21; tower.rs:457 | Commit before reply/event delivery is reusable. Replayed SSE messages are not replayed side effects. |
| modelcontextprotocol (Apache/MIT code transition; CC-BY docs) | c518f7a927cff918bce35d3522fcdb046d264d7c | docs/specification/2025-11-25/basic/utilities/tasks.mdx:494; basic/transports.mdx:166 | Cancellation can leave execution running. No inference of no-send from transport closure. |
| codex-cli (Apache-2.0) | 806d9732c974bc8a51b8317c1bd8985544fe627c | codex-rs/exec-server/src/process.rs:88; utils/pty/src/process_group.rs:24 | Process-emitted events differ from client transport failure. macOS parent-death signal support is absent; owned cleanup is explicit. |
| arc-cua (MIT) | 6b353039111c08c2c64c5229083606941e364eaf | macos_changes.py:59; settling.py:20 | Structural notifications and quiet periods do not establish no future effect. |
| browser-use (MIT) | c75e8476e26d18b7617643bc2ae082fae8eae431 | agent/service.py:3451 | Saved-history action replay cannot reconcile an uncertain non-idempotent mutation. |
| open-codex-computer-use (MIT) | 3cfe4b1e52cad6a99f5f19a7e01fb279752eb2a8 | local recovery/effect search | No operation-bound durable native completion ledger found. |
| open-computer-use (Apache-2.0) | 610bac85d242b2fdf43fbe36bce2348658a2d4c9 | local recovery/effect search | No operation-bound durable native completion ledger found. |

No reference solves causal attribution from identical current text. Footwork therefore keeps started/no-receipt unknown, and resolves only from a qualified execution receipt. A worker completion is historical; current text/identity is a separate observation. A per-attempt flock supplies custody, with PID-start registration used only for cleanup. Absence of a lock before a spawned worker acquires it is not evidence that it can never execute.

Reference inspection: project-scoped explorer reference_text_semantics; implementation/review decisions: docs/plans/restart-reconciliation-20261010.md, Claude mailbox reviews 1791647977465490000, 1791648203802365000 and 1791648499247640000.
