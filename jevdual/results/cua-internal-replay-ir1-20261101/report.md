# Pinned CUA internal replay: first Linux run

Status: **second mutations observed at actual native-helper boundaries; complete cloud closeout unavailable**. This is a partial first-run record, not a completed public-tool or Footwork runtime qualification. No fix or dependency change was made.

## Source and ordering

- Local prediction/preregistration/source trace committed first: `56df6cf6a56a10bfe8e16e4f0174ad57405a5676`, on Footwork baseline `2ea51b30c71c3135a895103615005d14fd26f0ca`.
- First execution was in the user-selected Linux cloud chat `01a18d7f-d0d0-733c-93c9-8f554f4190df`, host `durable`, title `Test project in VM`. No resolving test ran on the Mac.
- Cloud used existing Footwork base `2b5325edfbab95e095343d0c36ad5544db92d114` because the local parent commit was unavailable offline. Exact preregistration blobs were reproduced and committed as `d7f8881`; native archive identity matched independently.
- Carried CUA: `d5373879e9e0baf5a63999ac4d26902340c0ce20` plus cleanup2; archive SHA256 `5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401`. Preflight compared all796 extracted archive files.
- Test package: initial `02cb57e`; fixture prose corrected before execution in `27511b54a2514d3d01669f2a0a3efa73e9687c0e`; bounded supervisor committed in frozen execution head `48f93946b39e9f51f45b291b57152692e0d55033`.
- Both offline compile/link attempts succeeded using Rust1.97.1 and40 fingerprint-selected existing dependency artifacts, default feature fingerprint. The full pinned platform-linux source was compiled with an appended test-only cfg child module. Production function bytes remained unchanged. This is a test source build, not proof of equivalence to every published release feature configuration.
- Executed probe SHA256: `fe767c90d60e62f368d8c96d802359e4b8fc066251d5ceb9fb1de86959cefbbd`. The recorded build assertion also checked unchanged production prefix and Cargo.lock SHA256 `3a75d89d3f2fc53cf9e910beb3a754b28f27d29f2a2d4feed632b3959eed557f`.

## What the recovered output shows

The private D-Bus target is a separate Python process that imports neither CUA nor Footwork. It logs method receipt, applies text, fsyncs its independent effect journal, and then acknowledges, rejects before effect, returns an error after effect, or withholds its reply while continuing to service later calls. The parent inspected its complete captured source and the actual helper calls in the probe. It does not change the CUA mutation functions.

| Actual helper | Fixture condition | Attempts | Applied effects | Evidence scope |
| --- | --- | ---: | ---: | --- |
| `set_value_on` | Normal acknowledgement | 1 | 1 | Complete receipt recovered |
| `set_value_on` | False reply before effect | 2 | 1 | Complete receipt recovered; legitimate fallback control |
| `set_value_on` | Apply, then error reply | 2 | 2 | Complete receipt recovered; default client configuration |
| `set_value_on` | Apply, then withhold reply | 2 | 2 | Compact case output; declared100ms client timeout |
| `write_through_editable_proxies` | Normal acknowledgement | 1 | 1 | Compact case output |
| `write_through_editable_proxies` | False reply before effect | 2 | 1 | Compact case output; legitimate fallback control |
| `write_through_editable_proxies` | Apply, then error reply | 2 | 2 | Compact case output |
| `write_through_editable_proxies` | Apply, then withhold reply | 2 | 2 | Compact case output; full final receipt not imported |
| `set_value_on` | Withheld reply, ordinary configuration case | 1 | 1 | Compact output only; completion/watchdog classification unavailable |

In the complete post-effect-error `set_value_on` receipt, the target journal-derived transitions are `"" → TOKEN → TOKENTOKEN`, methods `SetTextContents → InsertText`. The helper returned success despite the second mutation. The acknowledged control applied once. The explicit false-before-effect control made two attempts but applied once, distinguishing fallback attempts from duplicate effects.

The fully recovered post-effect-error case used `client_timeout_ms:null`. The partially recovered withheld-reply receipt declares100ms. The compact ordinary-configuration record reports one effect, but its complete result is unavailable: do not infer default timeout semantics or that a production guard prevented replay from that count alone. The probe's `ordinary_zbus_timeout_ms:25000` is a hard-coded diagnostic label, not independent evidence that the connection actually timed out at that value.

## Causal trace and reachability

The source matches the observed chain: `platform-linux/src/atspi/native.rs:5260+`, `set_value_on`, reduces `SetTextContents` error/false with `unwrap_or(false)` and continues to `InsertText`. `write_through_editable_proxies:2804+` similarly tries `InsertText` then `SetTextContents`. No no-delivery proof is required between those mutation attempts.

**Supported:** actual pinned native-helper code can send a second mutation after an independently applied first mutation and failed acknowledgement. A missing-reply variant is observed under a declared shortened client timeout; the full post-effect-error receipt shows replay without that shortened setting.

**Not established:** ordinary-deadline public retained-reference calls, complete CUA ToolRegistry/set_value/type_text behavior, the batch retry matrix, or a current Footwork public CLI defect. Those paths were included or planned in the cloud package, but their complete results were not recovered. The private-helper tests do not include their outer admission/deadline guards.

Current Footwork Linux `type` and `append` use its own `linux_ax` single-write route rather than these CUA text helpers. It also does not call CUA batch tools in the inspected product source. Its source therefore avoids these specific paths, but no current-source product runtime control was imported from the cloud. The cloud `ax_control.py` deliberately stubs identity/writability checks; even a successful result there would qualify only the single-write owner, not X11 binding or the complete product.

The batch source trace remains separate: stale/menu/optional foreground recovery can issue more registry invocations without a send-truth gate; foreground fallback defaults false and explicit delivery mode blocks that branch. No batch runtime result is claimed here. `run_script` performs one registry invocation per explicit action; script-authored recovery is another boundary.

## Interruption and cleanup evidence

The cloud runner returned exit1. The supervisor reported `whole_run_timeout:false`, empty monitor errors, no cleanup signals/adopted waits, and `final_owned_descendants:[]`. This is actual captured supervisor output, but the complete per-case fixture cleanup receipts and final grading summary remain in the cloud. Exit1 alone does not establish which assertion failed or that every planned case completed.

After execution the cloud agent turn was interrupted by an automated check stating possible cybersecurity risk. No blocked operation was rerun. A recovery-only follow-up requested saved output and owned-helper closeout, then the Codex thread tools and native app fallback returned `Transport closed`. No filter bypass, new test run, source patch, install/fetch or public push was attempted.

## Evidence and next boundary

- [Captured cloud observations](cloud-observations.json): three complete receipts, nine compact case counts, original truncated-output flags, build/source assertions and supervisor result.
- [Captured source review](captured-test-source-review.json): complete target and selected helper/build/supervisor previews, with missing/truncated sections explicit. This is not a complete runnable package.
- Full cloud package: `/workspace/footwork-cua-replay-audit-vm/jevdual/scripts/ir1_replay_audit/` at `48f9394`.
- Full cloud evidence: `/workspace/footwork-cua-replay-audit-vm/jevdual/results/cua-internal-replay-ir1-20261101/`; build record `/workspace/scratch/cua-internal-replay-ir1-v2/build.json`.

Next is read-only recovery of the complete package, independent target journals, ordinary-budget/public-call outcomes, batch controls and cleanup records when the selected chat connection is available. Only then decide the smallest fix or a further experiment. Preserve this first run and its limited positive result; do not promote it to an overall Footwork replay defect or safety qualification.

Delegated source/storage contexts used the inherited session model; the cloud retained its existing model settings. Exact model identifiers were not exposed in the returned execution metadata, and these contexts are not model diversity.
