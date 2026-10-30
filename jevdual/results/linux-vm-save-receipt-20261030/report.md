# Debian VM retest of 045fc5d — 2026-10-30

**The real refused-save case still fails at `045fc5d`.** The new recognizer rejects the actual pinned SDK response because its structured record contains two additional recovery fields. The normal installed CLI/MCP/save journey passes with a working desktop. No product code, tests or identity/focus predicates were changed in this VM retest.

## Exact failure

The [captured real SDK result](045fc5d-refused-profile-sdk.json) has `is_error=true`, `error_code=foreground_unavailable`, no ActionResult and structured `effect=none`. Its fields are:

```text
code, detail, effect, hint, next_call, suggestion
```

The implementation in `python/jevdual/native.py::_linux_foreground_no_send` requires the keys to equal `{code, detail, effect, suggestion}`. The pinned native driver's `cua-driver-core/src/recovery_hint.rs` also supplies `hint` and `next_call` for this refusal. Consequently the recognizer returns false for the real envelope.

[Offline replay](sdk-replay.json) constructs an actual `cua_driver.ToolResult` from the captured public SDK reply, without starting a driver or sending input. The complete reply is rejected; an otherwise identical diagnostic control containing only the four expected fields is recognized. The [assertion fails](sdk-replay.txt) on the complete real reply. The [replay program](replay-footwork-sdk-refusal.py) is retained for a regression against the public SDK envelope.

Both the original uninstrumented [retest receipt](045fc5d-refused/driver-save.json) and fresh-profile [diagnostic receipt](045fc5d-refused-profile/driver-save.json) still report `effect=unverifiable`, `dispatched=true`, `delivered_count=null` and added save-readback evidence, despite the qualified foreground gate saying no input was sent. The independent file comparison catches the absent save. The [diagnostic run](045fc5d-refused-profile.json) confirms the on-disk fixture bytes stayed unchanged.

The diagnostic wrapper records `call_tool` arguments and the returned SDK object, then returns that same object unchanged. It does not alter fields, dispatch extra input, bypass a guard or weaken a target check. The original uninstrumented failure is retained separately.

## Successful control and separate setup failure

The first working-desktop control stopped at native append because Mousepad showed its previous-session recovery dialog. [The current observation](045fc5d-working/native-start.txt) contains only Yes/No controls; the public command correctly refused to find the requested text area. This result did not reach save.

The next two fixtures used separate XDG config/cache/data/state directories, preserving the earlier profile and its dialog. The no-window-manager case still reproduced the reporting bug. The working-desktop case completed the unchanged documented qualification: public CLI append/browser read, MCP append, duplicate prevention, server restart agreement, direct scoped Control-S and independent saved-byte checking. The [receipt](045fc5d-working-profile/receipt.json) and [artifact check](045fc5d-working-profile/saved-artifact.txt) confirm 109 codepoints / 117 UTF-8 bytes, SHA256 `4c833c0e33e3cc5bde92d43db38d935f65dce6918d78e0ee88f4eec72edb7d3c`.

Temporary desktop, editor, browser and loopback fixture processes were stopped. The initial tests and modal-dialog failure remain in the evidence; they are not relabeled as passing runs.

## Build and validation

A fresh bundle and consumer environment were built using the same cached pinned CUA wheel as the earlier Debian acceptance. [Installed identity](installed-identity.json) verifies all 191 packaged files; only `jevdual/native.py` changed from the `0b1e82c` package inventory. The installed package, scripts and test sources match the implementation at `045fc5d`; local additional commits contain only notebook/evidence and their history integration.

- Product wheel SHA256: `587ff557620f63a915e0a788ff34016150448c27ad482f593056bb1f751f245a`.
- Pinned CUA wheel SHA256: `0595b6042a98538b3c79ddef07301dd9481e477a5fbf64278b6cc63c2ed474c9`.
- Consumer environment: `/workspace/scratch/footwork-debian-consumer-045fc5d`.
- [Focused native/session/SDK/notebook tests](focused.txt): **226 passed**.
- [Additional receipt tests](receipts.txt): **7 passed**.
- Ruff and 103 packaged resource comparisons passed; final notebook validation/tests also passed.

The focused tests' passing synthetic replies do not establish the corrected behavior with the full real SDK envelope. This retest leaves the correction **unqualified**. The next regression needs the pinned recovery-hint enrichment as observed through public `ToolResult`, retaining all contradictory-action and uncertain-delivery checks.

The [earlier Debian acceptance](../linux-vm-acceptance-20261030/report.md), including commit `bd0acb1`, remains distinct from this retest. Its 2,434-test and 13-browser-test results were not rerun for `045fc5d`. Wayland, shared foreground coexistence, physical devices and provider-backed planning remain outside this test.
