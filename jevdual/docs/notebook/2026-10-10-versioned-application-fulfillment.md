# Versioned browser work-order fulfillment

## SIM5 · prediction · 2026-10-10 19:17
Hypothesis: an immutable leased order snapshot plus a current-revision compare-and-swap and exact controller evidence can connect simulated fulfillment to saved browser application state without stale or duplicate completion.
Test: local Python/SQLite app and public controller adapter, actual browser read/bind/complete, native RGB contact, changed/cancelled order during motion, lost reply and restart/conflicting identity/current artifact faults; freeze source before independent trials.
Predicts: only the same open app/order revision with supported current staged evidence commits fulfillment; changed/cancelled orders stay unfulfilled, exact repeated operation creates no second effect, and current/history remain distinct across restarts.
Against: client success flags or arbitrary paths authorize completion, wrong/stale order changes, duplicate update after lost reply, physical cancellation becomes rollback, missing current evidence becomes success, or restart loses identity and redispatches.
Refs: docs/experiments/SIM5-versioned-application-fulfillment.md; results/independent-controller-20261010/report.md; tools/physical-workcell/CONTROLLER.md
