# Linux installed DOM-event click candidate qualification

Source: **`c1496ca57c4fe2f49f55e641bbebf8290e7d7ac8`**, `Tom-R-Main/Footwork`, branch `codex/light-cdp-click`. The detached source checkout `/workspace/footwork-cdp-click-c1496ca` was never edited. All VM notebook/results are on the separate **`codex/cdp-click-vm-evidence`** branch, based on the earlier baseline evidence through **`a763f994cce5dca7db2e4e80d7e3d344630237a3`**. This branch contains no runtime implementation. Parent owns review/PR/merge.

## Exact artifact and unchanged supplied batch

The candidate's existing `jevdual/scripts/build_capability_wheel.py` verified **207 wheel entries** and produced the exact supplied artifact:

`jevdual-0.0.1-py3-none-any.whl`

SHA256 **`bba6e946259390c3b89767f8e16f934604e5ccc8f38a36882dd1af22ed075269`**.

A fresh consumer under `/workspace/scratch/footwork-cdp-click-c1496ca/consumer` contains pytest8.4.2, psutil7.2.2, websockets15.0.1 and pytest's dependencies; product was installed with `--no-deps`. CUA/browser-use are absent. All **202 installed product package files** byte-match the wheel. Five copied tests byte-match candidate source and run outside both checkouts, with unset PYTHONPATH, `JEVDUAL_PURE_PY=1`, real ELF `/usr/lib/chromium/chromium`, registered browser marker, isolated Python/configuration and no external pytest plugins. This deliberately qualifies the effector, not public light installation.

One original full batch passed **111/111** in **29.92 seconds**, **zero failures/errors/skips**, no warnings, pytest exit **0**, wrapper exit **0**. Counts inspected from [JUnit](junit.xml):

| Module | Passed |
|---|---:|
| `test_cdp_effector.py` | 17 |
| `test_cdp_transport_deadline.py` | 21 |
| `test_cdp_launch_custody.py` | 10 |
| `test_cdp_click.py` | 30 |
| `test_cdp_click_contract.py` | 33 |

All **30 saved fixture ingress ledgers** were inspected: **25 empty**, **five containing exactly one `intended` record**, with **zero sentinel or pointer ingress**. [Saved ledger export](candidate-ingress.json), [per-case inspection](inspected-summary.json), [full test output](pytest.stdout.txt). The cases cover direct native-button activation without business-completion promotion, pointerdown-only semantics, page patches, changed/unsupported subjects, dropped acknowledgement/cancellation, concurrent ref reuse, same-URL reload, the explicitly modeled numeric alias control, document.open root replacement and the still-disabled routes. No test was edited, replaced or rerun. No environmental fault occurred requiring a replacement baseline: the separately preserved b03c448 baseline remains **48/48** ([baseline report](../linux-cdp-qualification-20261031/report.md)).

[Build receipt](build.json), [source/test/wheel hashes and installed origins](environment.json), [exact command](command.json). The source/measurement commit is c1496ca; the separately committed candidate runner was ee035ec. Prediction458327c preceded measurement; its time-heading transcription correction is append-only in the notebook.

## Bounded independent actual-handle exploration

Six scheduled fresh-browser attempts were completed in **two separately preregistered batches**, with every original attempt retained. These are separate from the 111-test batch.

1. **Four 2x2 attempts** varied zero/one setup world before observation and AX/DOM allocation order after a real cross-site `127.0.0.1 → localhost` navigation at the product's original `DOM.resolveNode` boundary, after preflight. [All four attempts](real-reuse/attempts.json).
2. **Two further attempts**, preregistered after the first batch's mismatch, tried a legitimate read-only script-node backend allocation before AX-first inspection. [Both attempts](real-reuse-script-allocation/attempts.json). The allocation hypothesis **failed**: the script already had backend3 and the intended button stayed backend8.

All **6/6** attempts produced `document_changed`, `dispatched=false`, zero saved ingress and **zero action-time marker calls**. Real context IDs **3/4 were reused**, with different unique context IDs, loader IDs and isolate IDs and a changed renderer-process set. The **unchanged original context/backend request** was sent to Chrome, and its **unmodified real response** was passed back to the product. It genuinely resolved old backend9 into a new-document object: a sentinel button in AX-first cases or script text in DOM-first cases. Read-only object inspection found no private marker. Original resolution and activation replies are retained in each receipt. No forged protocol response, replacement parameter or action-time marker was used.

**Reproduction boundary:** the identical intended button's backend was **8** (AX-first) or **11** (DOM-first), versus the original **9**. Thus **0/6** independently reproduced the parent's *identical-target* context/backend collision on this Chromium154 VM. Probe summaries' `actual_reuse` field counts that stricter identical-intended-target condition, not generic numeric aliasing into other new nodes. These refusals must not be presented as independent validation of the exact critical collision; the supplied deterministic alias case passed, and the parent has separate actual-Chrome evidence. The optional search is stopped; no attempts were discarded and no new runtime was introduced.

Exact measured probe sources are retained in [first probe source](harness/real_reuse-measured.py.txt) and [second probe source](harness/real_reuse_script_allocation-measured.py.txt), hash-bound to receipts and commits883443e/450e56f. Current runnable copies have only import-order/noqa hygiene; original helper lint findings are retained in [lint-before](harness-lint-before.txt), with [final helper lint](harness-lint.txt). No measurement was rerun after those cosmetic changes.

## Environment, exits and cleanup limits

Same working VM: Debian **13.6**, Linux **6.18.57**, native x86-64, CPython **3.12.14**, Chromium **154.0.8037.57**. Default Chrome sandbox arguments are unchanged. Visible cgroup: **4-CPU quota** (`400000 100000`), cpuset0-4, **16GiB** memory, PID/swap caps `max`, actual system SwapTotal0. No 2-CPU/8-GiB or earlier constrained-envelope claim is made. No system installs, VM/cloud resources or paid model calls occurred.

PID1 is `tail`; a test-only wrapper subreaper records the post-test boundary before waiting adopted children. The 111-case batch left **172 adopted zombies and zero live children** after pytest exit; the wrapper then reaped all172, issued **no extra signals**, and finished with **zero owned descendants**. [Snapshot](post-pytest-before-wrapper-reaping.json), [numeric pytest/adopted-wait receipt](cleanup.json). Each of the six optional probes recorded **five adopted zombies**, zero live children, no extra wrapper signals, and an empty final owned-descendant set. Root Popen waits remain with their existing stock-test/product owners; individual Chrome-root numeric exits are not separately instrumented by these unchanged test fixtures.

This is bounded captured-process cleanup, **not** atomic descendant inventory, proof against daemon escape, a product no-zombie guarantee or global process cleanliness. Exact owned snapshots remain truthful. Synthetic task profiles, installed consumers and exact wheel bytes remain in the two scratch directories for inspection. The original `/workspace/Footwork` worktree and detached candidate are preserved.

## Delivery boundary

The original candidate batch has no failed/skipped test; the failed optional allocation hypothesis and identical-target reproduction gap remain explicit. Baseline/candidate notebook validation, result redaction and source/harness hashes accompany this report. All published changes are notebook/results only; no candidate source, typing, trusted click, product navigation, public CLI selection or durable authority was enabled by this VM task. Parent owns the release decision, PR and merge.
