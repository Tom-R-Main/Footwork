# Pinned CUA replay path trace

Read-only source trace before runtime testing, November 1, 2026. Owning bytes are carried by `vendor/cua-driver/native-source.tar.gz`, SHA256 `5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401`, upstream `d5373879` plus cleanup2. Paths below are archive member paths under `libs/cua-driver/rust/crates/`. An inference from these branches is not a reproduced replay.

## Native AT-SPI mutation chains

- `platform-linux/src/atspi/native.rs:5260–5304`, `set_value_on`: build proxies; call `EditableText.SetTextContents`; `.await.unwrap_or(false)` treats error like false; then read caret and call `InsertText`; another error/false can fall through to numeric `Value.SetCurrentValue` when that interface is declared. Despite the fallback comment, the inspected body does not clear the field before insertion. Final value alone can hide the first applied mutation.
- `native.rs:2804–2826`, `write_through_editable_proxies`: `InsertText` error/false falls through to `SetTextContents`, each with `.unwrap_or(false)` and no delivered-state distinction.
- `native.rs:2764–2801`, `write_into_editable_acc`: if the helper returns false, optionally attempts `Component.GrabFocus`, then calls the mutation helper again even without Component. `native.rs:2857–2900` may additionally refresh the indexed tree and retry. `native.rs:3830–3848` suppresses focused-write errors into an optional success/miss, permitting later lookup paths.
- `native.rs:123–153`, `bounded_for`: an outer deadline plus500ms bounds unwrapped awaits; a timed-out mutation can therefore lose its result without establishing no delivery. Public timing can prevent an inner fallback while permitting a caller-level fallback, so both owners matter.
- `platform-linux/src/tools/impl_.rs:8278–8365`, `TypeTextTool`: AT-SPI attempt; on any non-success, optional Qt5 focus workaround+another AT-SPI attempt; then a later route again calls AT-SPI `insert_text` before Tk or keyboard routes. `impl_.rs:9384+`, `SetValueTool`, calls the cached/indexed native setter and has a separately conditioned keyboard fallback. Trace the exact refusal predicate before asserting it is reachable after any particular error.

These are distinct post-effect uncertainty channels: false/error response, missing reply until timeout, outer timeout, and a failed subsequent observation. A fixture must identify which it actually injected.

## Batch and script owners

- `cua-driver-core/src/batch_tools.rs:977–1019`, actual action execution: initial registry invocation; click-to-menu retry after stale classification; otherwise stale re-find and same-tool retry; then optional foreground retry. The menu/refind branches are mutually exclusive. No send-truth check was found in these retry gates in the carried source.
- Foreground retry additionally requires omitted action `delivery_mode` and enabled foreground fallback (`:993–996`). Batch-level delivery defaults can populate that field during parsing (`:542–545`); `foreground_fallback` defaults false. A bare exposed branch does not establish default replay.
- Batch reporting (`:1023–1048`) reports the final attempt and selected metadata; do not use that final receipt as the independent history of earlier attempts.
- `cua-driver-core/src/script_tool.rs`, `Api::act`→`Api::invoke` invokes the registry once. Script-authored catch/retry is separate from automatic internal replay. Its error projection can erase delivery details; this merits trace documentation, not an assertion of an automatic second call.

## Footwork reachability

- `python/jevdual/native.py:1426–1452`, Linux `type` uses `_type_linux`→`linux_ax.set_value_ack` once, followed by exact readback. `python/jevdual/linux_ax.py:385–396` makes one `SetTextContents` call and raises on missing/nontrue acknowledgement; no alternate route. Linux append likewise uses one `InsertText` (`linux_ax.py:399–415`).
- `native.py:1193–1244`, `_key_route`, permits foreground retry only from a structured, target-bound no-send refusal, not generic prose/errors. That cannot stop a dependency from replaying internally before it returns.
- `native.py:2156–2161`, non-Linux nonweb `type` calls CUA `set_value`; `_type_web` uses another platform-specific CUA typing path. A Linux reproduction does not qualify macOS behavior.
- No product call to `run_steps`, `run_actions` or `run_script` was found in the inspected Footwork Python source. Batch amplification is raw CUA surface exposure rather than current native CLI text reachability. Preserve this distinction in any finding.

Next: committed prediction in `docs/notebook/2026-11-01-cua-internal-replay.md` and protocol in `docs/experiments/IR1-cua-internal-replay.md`; first resolving execution in the user-selected Linux cloud chat. No runtime test has yet resolved these paths.
