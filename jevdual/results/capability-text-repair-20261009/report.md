# Capability text repair: both fixes qualified locally

The repaired four-tool capability interface passed **six fresh external-host development cases** on frozen **87d0de2**. Each actual canonical Opus5.5/high session offered only bind/observe/act/status, used no out-of-arm tool, had one final applied journal operation, reported supported requested-content completion and matched the independent exact AX oracle after backend retirement. No session was retried. These results do not replace or regrade C1.

| Case | Exact content | One applied operation | Supported content completion |
|---|---|---|---|
| Existing terminal newline | pass | pass | pass |
| No terminal newline | pass | pass | pass |
| Empty document | pass | pass | pass |
| Preserve tab, spaces and blank lines | pass | pass | pass |
| Deliberately add a blank line | pass | pass | pass |
| Whitespace-only prefix without final newline | pass | pass | pass |

## Changes

**Explicit separator contract.** Offered targets now expose append_separator; act and its text argument describe the automatic newline. A nonempty field lacking a terminal newline gets one separator, otherwise none. The supplied payload remains literal, including intentional leading/trailing whitespace. The ordinary no-newline host sent `17.25 USD`, while the deliberate blank-line host sent `\n17.25 USD`. Both produced their requested exact result. The legacy NativeBridge separator behavior did not change.

**Exact writable empty-field qualification.** A missing Cua preview no longer suppresses an append candidate. The adapter independently resolves/reads the AX field and qualifies both caret and insertion setters. It requires observed geometry and rechecks insertability alongside document/content before dispatch. Missing AXValue is empty only if the existing AX reader proves zero characters; absent/unreadable/readonly/secure/ambiguous/frameless fields get no append target. The real empty case qualified through exact AX reading despite its omitted Cua preview; the absent-AXValue zero-character fallback is additionally covered by real-core simulated scenarios.

**Readback identity.** Empty/placeholder-derived Cua labels can become “text area” after insertion. Readback uses the scoped document, AX role and unique original frame, preserving relevant role/frame/ambiguity failures as unknown and preventing redispatch. This is current field evidence, not durable incarnation reconciliation.

## Reference solutions

The local **arc-cua** checkout supplies the strongest optional-value and independent setter/editor-capability pattern. **browser-use** explicitly describes append versus replace and retains empty readbacks with is-not-None checks. Cua's low-level getter preserves CFString content, but its snapshot formatter drops/trims empty or whitespace values; **open-codex-computer-use** has a similar lossy snapshot and unsafe empty fallback. Chrome MCP/devtools-protocol make literal typing and optional values explicit, while stable target IDs alone do not prove freshness. No source was vendored or dependency bumped.

Precise paths, licenses, local SHAs and the patterns adopted/rejected are in `docs/plans/reference-text-repair-20261009.md`.

## Verification and provenance

Prediction commit **22c58bc** preceded reproductions. Six baseline public-tool scenario failures were preserved. The repair now has **19** public capability scenarios that run the real ScopedBackend, service, NativeBridge, menu parser, AX resolution/value/insertion and journal, replacing only external Cua/Mac primitives. They cover literal whitespace, missing versus empty, readonly setters and getter errors, missing geometry, stale document/content, setter loss, post-insertion role/frame/ambiguity loss and token/no-replay behavior. Existing CLI scenarios remain intact.

Final source passed **1217 tests with 26 skipped** in 90.91 seconds, and repository lint passed. Source/harness/dependency hashes, exact case manifest, private transcript/receipt hashes, tool inventories, actual act inputs, per-target contract observations and journal records are in summary.json, manifest.json and cases.json. Baseline/focused/full logs remain private, with hashes in offline.json. The earlier model-free real empty append on 50948c6 also passed; model-free-probe.json records its separate version/evidence and zero provider calls.

Independent tool-less **Opus5.5/high** reviewed the committed 50948c6 diff successfully, found no concrete blockers for the scoped checks, and prompted final geometry/error/prompt/prerequisite hardening before qualification. Its comment that every append changes the label is rejected: nonempty parser labels normalize stably; empty/placeholder labels were the problematic transition. The raw review remains private with hashes and adjudication in opus-review-receipt.json. Original mailbox Claude did not respond to this package; this review is an independent AI consultation, not reciprocal mailbox or human sign-off.

Reported list-basis model estimate: **$0.2989182** for the six host sessions plus **$0.3248590** for review, **$0.6237772** total. This is not invoice/billing evidence. Requested CLI session/review caps are soft; aggregate scheduling reserve stayed below $8. No installations or additional provider calls were needed for reference inspection, tests or the direct AX probe.

## Limits and cleanup

All six agent final messages still made unsupported ancillary saved/unsaved disk-state assertions. These are explicitly recorded in claim-review.json and not adopted. Content completion is supported; disk persistence remains unchecked. This package does not qualify another app/platform/host, minimal installation, durable restart reconciliation or a recovery advantage over raw tools. Original C1 files and outcomes are unchanged.

Cleanup readback found zero owned document windows, no owned browser and no surviving attested backend groups; five other TextEdit windows remain open. Their contents were not inspected or claimed unchanged. Results and private evidence remain readable. No global host configuration, OS permission, Git remote or public release changed.
