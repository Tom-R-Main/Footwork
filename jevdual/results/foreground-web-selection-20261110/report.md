# Explicit foreground selected-range edits

Preregistration: `db57ef6`, notebook WSR1. Baseline against `be8ea6b`: 14 public CLI scenarios failed because the requested range option did not exist (`baseline.txt`).

The new `--web-text-range START:LENGTH` option requires explicit foreground native macOS web typing and the existing exact focus-guarded CUA runtime. It edits an already matching UTF-16 selection, sends no selection-changing key, and never strips an AX terminal LF. Fresh identity, complete raw value, independent selected range and exact selected text must agree before one positively paced target-token text call. Both range boundaries must be complete Unicode boundaries. Values and resulting postconditions are bounded to 65536 UTF-16 units.

Immediate readback resolves the field independently again and records the full expected/observed values with preserved prefix/suffix. The receipt additionally requires successful fresh direct-AX supplementation, matching identity/role/frame, and exact corroboration of that earlier readback. SDK fallback, preview truncation, whitespace-equivalent mismatches, later changes, or missing readback cannot confirm. Secret readbacks are redacted and incomplete. Durable request replay includes the range; a changed range conflicts rather than dispatching again. Durable facts name `native.foreground_web_selection_readback`, not the older AX-insert acknowledgement source. The current completion consumer does not adopt this new source as whole-task completion proof.

`scenarios.txt`: 35 selected-range public CLI scenarios passed, including LF insertion, supplementary Unicode, long values, unreadable/changed selection, stale readback, SDK fallback, no retry, secret redaction, durable provenance and replay. Existing whole-field LF selection refusal remains unchanged. Focused source/contract validation is recorded in `focused.txt`; Ruff and notebook results are adjacent.

Commands, run from `jevdual/` without live UI:

```sh
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k foreground_web_range
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_session.py tests/test_native.py tests/test_native_foreground_intent.py tests/test_native_receipts.py tests/test_ax_semantics.py tests/test_cli.py tests/test_agent_cli.py tests/test_authorize.py tests/test_authorization_parity.py tests/test_session_evidence.py tests/test_session_operations.py tests/contract
.venv/bin/ruff check python/jevdual/{native,session,cli,ax}.py tests/test_session_scenarios.py tests/test_ax_semantics.py tests/test_agent_cli.py
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m evals.notebook docs/notebook --check
```

Limitations: simulated-Mac results do not establish Suno renderer or server acceptance. Native bytes and ABI are unchanged; no SDK rebuild, install or worker live input occurred. Selection qualification precedes the SDK's own focus guard, rather than forming an atomic renderer transaction; exact postcondition readback reports divergence without retry. Live qualification remains with the parent agent on a frozen source revision.
