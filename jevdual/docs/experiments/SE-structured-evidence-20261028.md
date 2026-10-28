# SE: structured evidence and qualified reconciliation

October 28, 2026; baseline `47ed7ad`. Commit this protocol before substantive tests.

## Design and primary metric

The native runtime retains an immutable execution capsule after its awaited bridge call returns, before normal operation finalization. Bind capsule schema, producer/check version, operation/session/request/resource/target/observation, native binding, capture interval and returned custody. Reconciliation reads only that retained record in the owned authority database; it accepts no arbitrary caller-supplied file or manual truth flag. Independent primary metric: input count on replay/reconciliation after loss between receipt persistence and finalization; the count must remain unchanged.

Fault tests distinguish death before receipt (unknown), after receipt (eligible only with qualified terminal evidence) and after finish (idempotent replay). Tampered or missing receipts stay blocking. Sent input with unknown effect can spend authority while preserving unresolved effect. Current matching state alone cannot establish historical execution. Existing MCP recovery remains compatible and independently scoped.

Structured observation/current-state/persistence facts retain provenance, versions, resource/binding, generation, interval, coverage, predicate, values, references and limits. Test long field values, incomplete/clipped projections, malformed typed records, wrong identities, later edits, secret redaction and legacy compatibility. Browser source metadata must be computed before the 6000-character slice. Direct AX delivery claims require the actual write/menu acknowledgement, not a matching screenshot.

## Guardrails and decision

No live app, provider, installation, heldout grading, permission change or public transport. Preserve old predictions/results and legacy records. Do not infer independent window birth or task correctness from the new record shape. Adopt only if real command fault/replay tests, meaningful negative cases and repository checks pass. Retain failures and append results below rather than changing the protocol after evidence.
