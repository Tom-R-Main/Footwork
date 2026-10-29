# RV3 durable recovery and completion remediation

Prediction: RV3 in `jevdual/docs/notebook/2026-10-29-review-merge.md`, committed by root as `706a3f8` before reproduction. Integration base: `e4b7199`. This worker made no commits and ran no live apps, network, or providers.

## Changes

- `session.py`: authority-owned commands preserve the complete damaged JSONL bytes in a private `session.interrupted-*.jsonl` quarantine, atomically replace the display log with all readable records and an explicit repair record, then reconstruct missing operation projections from canonical authority state. Valid records after a corrupt middle line remain present. A complete last record missing its newline is also separated safely.
- `session_operations.py`: legacy capability rows get an explicitly legacy status receipt with no operator projection/proof. Domain unresolved reporting queries all blocking rows rather than the recent-history window.
- `session.py`: `done` rejects unresolved primary/domain/explicit-context custody before loading keys, binding an app or calling a verifier. Legacy/unprojected pending uncertainty also blocks. Each distinct explicit context authority remains locked through verifier acceptance and state save; the existing Journal lock is nonblocking, and a shared primary/context domain is not locked twice.
- `session_operations.py`: coordinated RV4 correction prevents a retained historical v1 ticket receipt from releasing unknown custody under the new v2 response-boundary contract. Historical final-receipt reading is unchanged. Ticket regression ownership remains with the evidence worker.

## Reproduction and verification

Initial red command:

```sh
uv run --project jevdual pytest jevdual/tests/test_session_scenarios.py -q -k 'partial_projection_is_quarantined or reports_legacy_unknown or refuses_unresolved_custody'
```

Observed: **7 failed, 97 deselected**. See `red.txt`. Failures reproduce the actual partial projection, legacy status failure, and verifier acceptance closing unresolved own/domain/context/legacy pending state.

Final focused command:

```sh
uv run --project jevdual pytest jevdual/tests/test_session_scenarios.py jevdual/tests/test_session_operations.py jevdual/tests/test_session.py jevdual/tests/test_completion.py -q
```

Observed: **340 passed**. See `green-core.txt`. Public regressions cover replay/new click/done without repeating the first input; exact quarantine preservation; legacy status with 0 and 101 later final rows; refusal before key/app/verifier calls across eight custody scopes; and positive context-lock retention/release in separate and shared domains. Unit coverage preserves a valid receipt after corrupt middle bytes and handles a complete record missing its terminal newline.

Root's additional context review identified that explicit durable context logs also require recovery before strict cross-context reads. The bounded follow-up reproduction (`pytest ...test_session_scenarios.py -q -k 'repairs_settled_durable_context or refuses_corrupt_legacy_context'`) produced **2 failed, 110 deselected** before the correction; see `red-context.txt`. `done` now repairs and reprojects every durable source under its already-held authority ownership before reading its evidence. The positive CLI regression retains valid context receipts, quarantines the exact malformed bytes, accepts completion, and preserves the single input count. Unreadable legacy context evidence instead receives a typed `context_evidence_unreadable` completion refusal before keys/app/provider work, with bytes unchanged. The final 340-test pass includes both regressions.

Ruff check passed for the four changed source/test files; Ruff format left all four formatted. `git diff --check` passed for these files. See `lint.txt`. Root owns full-suite, docs, notebook outcome, hosted checks and commits.

## Owned files and freeze

Only `jevdual/python/jevdual/session.py`, `jevdual/python/jevdual/session_operations.py`, `jevdual/tests/test_session.py`, and `jevdual/tests/test_session_scenarios.py` were edited by this worker. `completion.py` required no change: repairing the non-authoritative log once under ownership keeps its strict readers usable without silently discarding malformed evidence during every read.

Files frozen after the 340-test focused pass; coordinated ticket gate is included in that pass, while its new v1/v2 ticket regressions are owned by the evidence worker.
