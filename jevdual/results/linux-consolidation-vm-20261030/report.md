# Cloud-base Linux consolidation — Debian VM, 2026-10-30

The grounded consolidation is implemented on the VM-tested cloud base `bd6f185`. The combined product revision is **`f16cc54`**. Its standalone installed acceptance, real SDK refusal, delayed-helper recovery, pinned-process checks and isolated readiness/lifecycle gates passed in this VM. **Repeated native multi-session reliability remains open:** two target-readiness timeouts and one nonzero native teardown after CLI JSON success are retained. The successful isolated runs do not erase those failures.

## Scope and provenance

The [consolidation manifest](consolidation-manifest.json) identifies the cloud base, source-backed handoff `0634a06`, exact combined implementation and file hashes. Only the handoff's learning document/notebook/evidence were imported from the competing branch. Compatible mechanisms were transferred into the existing cloud state machine; there is one packaged supervisor and one qualification/record contract. No competing runner was merged. CUA, browser-use, authorization and semantic refusal pins remain unchanged.

The [grounding](../../docs/linux-consolidation-learning.md) is a source study and mechanism model, not combined-product acceptance. Its unavailable kernel checkout remains unavailable; no kernel-source review is claimed here. These checks qualify the actual Debian VM/runtime and observed fixtures, not other kernels or desktops.

## Grounded fixes

**Custody, signal identity and wait ownership.** The old source-function model's stale numeric-recipient transition was reproduced in the [failing regression](grounded-before.txt). Cleanup now derives scope from group/ancestry observations and delivers to each observed member through its own pidfd. Before/after acquisition checks validate the intended observable start identity and owner; possession of a newly opened fd alone does not establish custody over a stale PID. Once acquired, the descriptor prevents signal retargeting. A start stamp is not described as a standalone race-free oracle, and a leader fd with flags zero is never described as tree cleanup.

There is **no numeric fallback** in the supervisor's individual signal path. Unsupported/denied/exhausted APIs have explicit outcomes with no pinned-delivery claim; unavailable capability refuses before launching components. Direct children retain their sole Popen wait owner. A new [partial-census regression](direct-child-before.txt) found that even initial direct-child adoption needed to be independent of the census; `f16cc54` corrects that lookup and preserves safely addressable child custody.

**Incomplete inventories.** Bounded enumeration reports truncation and opaque read failures. Omitted known processes are independently re-read rather than silently retired. Unreadable identities remain unknown. In the [native partial-inventory gate](first/faults.json), the runner invalidated readiness and terminated known live members, while explicitly retaining `inventory_complete=false` and `uncertain=true`. Empty observed survivors do not imply complete cleanup. Scope remains owned groups/ancestry and observed descendants; unseen escaped descendants and a non-atomic or hidden process view are not covered.

**Native readiness.** Xvfb reserves the display through `-displayfd`, with bounded allocation and initial handshake. The existing explicit-display conflict refusal remains. WM selection must have a valid root/check-window EWMH self-reference. Cloud-owned D-Bus, fresh profiles, exact editor/document checks and ongoing WM/accessibility-identity health remain. A failed or uncertain stage removes the active marker before cleanup. An [actual selection-only WM](first/faults.json) was rejected; a separate actual server occupying `:0` survived while native allocation selected `:1` in [primary acceptance](primary/acceptance.json).

**Transient Chrome helpers.** The actual executable/profile/port/UID discovery predicate remains strict. An invocation-owned forwarding helper must exit successfully and be reaped before root rediscovery; arbitrary matching processes are never excluded. Tests cover delayed/exited/failed helpers, a second root before or after helper completion, changed root incarnation and cancellation. The helper fake's wait method initially returned success regardless of its stored failure status; the fixture was corrected to preserve the real Popen contract, and the original failure is retained in `grounded-after.txt`.

In the real installed test, the exact persistent browser was paused after all windows closed. Its actual forwarding helper stayed live and matched the root predicate; an independent discovery control correctly reported ambiguity. After resuming the same owned root, the public CLI bound the new window and exited **0**, retaining PID/incarnation/profile. Helper acknowledgement alone did not substitute for window/browser readback ([primary receipt](primary/acceptance.json)).

## Exact combined artifact

[Installed byte verification](installed-identity.json) matched all **193** packaged files against the wheel, and [source-to-wheel verification](source-wheel.json) passed. Binary installation compiled no Rust. Product SHA256: `3a309ad45e7ec33a19fc87769aebb18ff254390f5f2f582e557b496d458ef556`. Native CUA SHA256: `0595b6042a98538b3c79ddef07301dd9481e477a5fbf64278b6cc63c2ed474c9`. Dependency versions and source/test hashes are retained.

- Bundle: `/workspace/scratch/fw-consolidated-final-bundle`.
- Consumer: `/workspace/scratch/fw-consolidated-final-consumer`.
- Product code is `f16cc54`; later commits contain documentation and evidence only.

The [kernel gate](pidfd-kernel.json) ran on this actual x86-64 Debian VM, Linux `6.18.57`, Python `3.12.14`: TERM through an owned child's fd terminated it; the retained fd returned ESRCH after exit; a separate sentinel survived; descriptors closed and children were joined. The [installed production primitive](installed-pidfd.json) also terminated only its target and left the sentinel alive. Unsupported, denied, descriptor-exhaustion and acquisition-time replacement branches were exercised through controlled API failures, not claimed as actual kernel denials. Tests distinguish individual delivery from separate group/descendant discovery and orphan reaping.

## Installed acceptance and constraints

All constrained runs used init, **512 PIDs, two CPUs, 3 GiB memory, zero swap**, 512 MiB shared memory, dropped capabilities, no-new-privileges and disabled external networking ([configurations](container-configurations.json)). The thin Debian image uses selected read-only mounts of this VM's public runtime/libraries, checkout, sysroot and consumer. Fixture UID records enable D-Bus; no host desktop or API credentials were supplied. This is VM acceptance, not a standalone release-image build or physical-seat qualification.

The [standalone primary run](primary/acceptance.json) passed installed public CLI append/browser read, public MCP append, duplicate prevention, restart agreement, direct scoped save and independent artifact verification. Saved content is 109 codepoints / 117 UTF-8 bytes, SHA256 `4c833c0e33e3cc5bde92d43db38d935f65dce6918d78e0ee88f4eec72edb7d3c` ([saved bytes](primary/saved-artifact.txt)). This is the documented direct native save route, not provider-backed planning.

The [same-wheel no-WM control](first/refusal.json) kept its changed editor buffer unsaved and returned `refused`, `dispatched=false`, zero delivered inputs and no save readback. Its [real public SDK envelope](first/refusal-sdk.json), independent unchanged disk bytes and clean pinned cleanup are retained. It deliberately creates a negative fixture without a ready marker; it is not a weakened supervisor admission path.

[Isolated critical faults](first/critical-atspi-result.json) and companion Xvfb/bus/editor result files passed: readiness was invalidated after component death or changed private accessibility-bus identity, with no known live survivors, zombies or signal uncertainty. [Native negative policies](first/faults.json) rejected selection-only WM, partial inventory and injected unsupported/denied/exhausted capability states. Partial inventory retained uncertainty; other successful cleanup controls reported complete observed coverage. TERM-ignoring children, orphan grandchildren and stalled handshake/allocation are separately tested under the PID ceiling.

## Validation and unresolved native behavior

| Check at combined product revision | Result | Evidence |
| --- | --- | --- |
| Full non-browser suite | **2,511 passed, 28 skipped**, 13 deselected | [output](final-full-tests.txt) |
| Browser suite | **13 passed**, no skips | [output](browser-tests.txt) |
| Process/readiness/resource tests within 512-PID init boundary | **55 passed** | [output](first/process-fault-tests.txt) |
| Source-wheel, Ruff, 103 resources, notebook validator/tests | Passed | [wheel](source-wheel.json), [lint](ruff.txt), [resources](resources.json), [notebook](notebook.txt), [tests](notebook-tests.txt) |

The initial broad run at predecessor `6f9d699` passed 2,510 tests; that result is not substituted for the final full-suite run after the direct-child correction.

Native failures remain material:

1. The first installed run completed its save journey and helper forwarding, then the recovery CLI printed success JSON but exited nonzero with `FATAL: exception not rethrown` ([stdout/stderr](first/browser-recovery.txt)). The first harness did not separately store that child's numeric exit code. This is retained as an acceptance failure, not converted to success from its JSON or window readback. The cause is unresolved; CUA was not bumped or patched speculatively.
2. A fresh default-probe repeat failed conservatively at target observation before readiness ([state](repeat/session.json)). A ten-second-probe diagnostic completed the full primary journey with process exit 0, then another fixture in its multi-session batch timed out at target observation ([batch output](container-diagnostic.txt)). Thus a simple three-second probe-budget diagnosis was not established. Exact-target guards and startup deadlines were not bypassed.
3. A standalone primary repeat, with the same product wheel and explicit ten-second probe cap under the thirty-second startup deadline, completed and returned success; isolated lifecycle fault containers also passed. These establish those runs. They do not establish reliable repeated multi-session startup or explain the earlier native teardown.

The [Linux guide](../../docs/linux-support.md) records operating policy and these limits. No model-backed evaluation, shared foreground, Wayland, new application contract or physical device was qualified. Owned temporary containers are stopped and removed after evidence capture. The combined implementation is ready for independent review with its repeated-native-session reliability limitation still open.
