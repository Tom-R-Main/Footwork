# Durable owned-browser authority

The explicit `footwork browser cdp` route now retains guarded operations across CLI and holder restart. One holder owns the observed document refs and authority lock; it commits intent and start before activation. Repeating the original token retrieves its operation rather than clicking again. Browser evidence has its own versioned producer; native evidence allowlists remain unchanged.

Runtime source: `e4df2c6b04644c332c8a636c556ae2fee0822d28`.
Wheel SHA256: `ae780174a9f0dcfc0583dd9ed9c814f9f940fbfa54b6f64fdf50aad38233b059`.
The deterministic wheel has 211 entries; all 206 installed package files were byte-equal locally.

## What was checked

- **2,685 source regression tests passed**, 95 skipped, 60 browser/live deselected. This used the matching development environment with pure Python forced, not a fresh full installer.
- **201 installed checks passed locally** outside the checkout, without CUA or browser-use. Dependencies were installed as binaries and the source-matched wheel installed with `--no-deps`; this qualifies the runtime, not the future light package metadata.
- **201/201 installed VM checks passed**, with no skips or failures, on the same wheel and 12 unchanged test files. The host was Debian 13.6 x86-64, Python 3.12.14 and Chromium 154, with a quota of 4 CPUs and 16 GiB; this is not the proposed 2-CPU/8GB measurement. The outer test wrapper separately reaped 205 zombies, sent no extra signals and ended with no owned descendants.
- An independent inherited-model agent context reviewed the changed authority, holder, guard and CLI paths. Startup and schema findings were fixed and rechecked; the final retention-failure sensitivity control also passed independently. No actionable findings remained in that scope. This was not a model-diversity review.

The real CLI lost-client test observes independent fixture ingress before killing the client, then retrieves the same operation with ingress still one. Abrupt holder-exit tests interrupt real committed prepared, started and retained-execution boundaries: expected ingress is zero, zero and one. Prepared-only recovery is known not-sent; started and acknowledged execution remain unresolved. No DOM matching or acknowledgement becomes a completion claim.

Four real Chrome startup-signal cells cover TERM during launch, connection and navigation, plus INT during launch. They assert absence of captured live processes before test cleanup. A dedicated Linux test supervisor reaps adopted zombies separately; neither this nor a bounded inventory proves that product cleanup alone prevents every orphan or escaped descendant.

## Failures retained

The first CLI recovery cell exposed an exception-class mismatch, corrected before qualification. Readiness exception cleanup and the CDP schema prefix failed before their fixes. The old installed wheel failed the pre-readiness TERM cell with holder exit -15 and required test cleanup. Finally, an injected double retention failure exposed an incorrect no-send reply and swallowed cancellation; the fixed path reports delivery and retention uncertainty while preserving blocked custody. This last control is not a reproduced disk-full incident.

See the committed before-results, `review.json`, `verification.json`, the [engineering notebook](../../docs/notebook/2026-10-31-durable-cdp-authority.md), and the [final VM report and per-cell receipts](../durable-cdp-vm-20261031/e4df2c6/report.md).

## Reference grounding and release boundary

`grounding.json` records fresh file/range hashes from agent-browser, chromedp and tini. The transfers are no mutation replay after transport uncertainty, strict target pinning, actual child-handle ownership and separation of ordinary process cleanup from an init/subreaper role. Automatic daemon respawn, PID-name identity, locator fallback, raw CDP IDs as idempotency keys and DOM agreement as historical effect proof were rejected.

Typing remains disabled. An activation acknowledgement remains completion-unverified and blocks new mutations until a qualified operation-specific completion reader exists. Such a reader, process-owned pipe transport, the binary-only light metadata split and a measured small-VM resource profile remain open. The legacy CUA routes and their durable-browser refusal remain unchanged. No general exactly-once website guarantee, live Jev judgment-quality result, full Linux desktop reliability fix, deployment or package-registry release is claimed.

The installed `browser cdp guide`, `tools`, `doctor` and `schema` expose these boundaries. Start with the [owned CDP guide](../../docs/owned-cdp.md).
