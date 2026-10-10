# SIM5: Versioned browser work-order fulfillment

Mode: local application/physical-controller integration diagnostic, not hardware or market qualification.

## Hypothesis

A browser work order bound to an immutable application identity, order ID and revision can
be fulfilled through the image-guided simulator, then updated only when exact controller
evidence and the current application revision agree. Changed/cancelled orders and lost
application replies can remain truthful without duplicate fulfillment or invented physical
completion.

## Scope and interface

Keep a Python/SQLite local app, plain browser UI and a handoff CLI under tools/physical-workcell.
Reuse the frozen controller's public commands; do not change controller/body/vision semantics
or add robot capability-service protocols. The app binds only on IPv4 loopback and persists
an immutable app identity plus source/store binding. SQLite owns transactional order revision,
leases and idempotent fulfillment receipts. Order and mutation schemas are exact and finite.

The browser reads an order and binds its current revision. A lease retains the exact work
order snapshot/digest, app identity, operation ID and assigned private episode/controller
paths. The adapter prepares a case from that snapshot and explicitly bound scene input,
starts or reconnects an owned controller and exposes observe/submit/guard/status through its
public interface. The host retains target planning; no internal model API is added.

The browser fulfillment action references the lease and a stable completion operation ID.
The server independently checks the assigned controller's exact staged receipt, fresh
observation/task binding and current saved artifact evidence. Client-supplied success flags
or arbitrary receipt paths cannot grant completion. After physical verification, a SQLite
compare-and-swap requires the leased order to remain open at the expected revision. The order
update and software effect receipt commit in one transaction. Readback targets that same
app/order/operation identity and survives restart.

Each browser-origin write checks loopback/Origin and exact fields. No remote service,
production data, credentials, paid model call or external application write is required.
Browser use is through the host's available browser driver; Footwork's controller/receipt
and saved-byte checks supply the physical connection. Do not bypass a Footwork judge or
claim this qualifies its production browser/capability governance.

## Changes, cancellation and unknown replies

Editing/cancelling an order increments its revision. Guard detects a changed/cancelled
lease, withholds further submissions and requests cooperative cancellation for an active
bound controller goal. Motion already admitted may partially execute; cancellation must
not be treated as rollback. Server completion still refuses a stale lease even if a host
misses the guard. No atomic physical/software transaction is claimed.

A lost fulfillment reply is reconciled by exact operation readback. Identical operation
identity returns the committed receipt and current order; conflicting reuse refuses.
Missing current physical/software evidence stays unavailable. Historical application
fulfillment remains distinct from later physical/artifact integrity.

## Checks and measurement

Primary metric: required integration scenarios whose persisted app result and controller
history match the expected outcome, with all attempts and failures retained. Cover:

1. Actual browser read/bind, RGB-guided contact fulfillment, browser completion and saved
   application readback for the same identity/revision.
2. Order changed during admitted motion: guard stops further work, stale fulfillment refuses.
3. Order cancelled during admitted motion: partial movement remains explicit, app stays cancelled.
4. Lost application reply after committed completion: exact readback/repeat creates one effect.
5. Wrong order/app/lease, conflicting operation identity and unsupported physical evidence refuse.
6. Application/controller restart preserves binding/history without redispatch or implicit reset.
7. A staged receipt with altered/missing current artifact does not authorize new app fulfillment.

Run meaningful backend/adapter conformance, affected physical-workcell regressions and lint.
Freeze source before independent integration trials; retain browser observation/screenshots
and backend persistence readback separately. Use owned private fixtures and processes,
preserve failures and qualify any driver gaps. Recheck screen lock before desktop-dependent
verification; continue implementation/headless work if it locks. Installation downloads are
already authorized. Do not alter system lock/power settings or use personal browser profiles.

## Decision

Adopt only the bounded local application handoff supported by independent evidence. Keep
the deterministic controller for movement and the agent responsible for orchestration.
Hardware transfer, real operator demand and production adapter promotion remain subsequent work.

## Result

Pending.
