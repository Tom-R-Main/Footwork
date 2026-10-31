# DOM-event native-button qualification

Source: `c1496ca57c4fe2f49f55e641bbebf8290e7d7ac8`, runtime correction `873b32f`.
Pure wheel: 207 files, SHA256 `bba6e946259390c3b89767f8e16f934604e5ccc8f38a36882dd1af22ed075269`.

## Qualified boundary

The opt-in CDP operations seam supports native activation of directly named main-document
`button[type=button]` controls on one connection. The actual route is
`dom_event_native_button`. CUA's `dom_event` sends a pointer/mouse sequence; this route instead calls
the isolated realm's intrinsic HTML activation function. A pointerdown-only application can receive
no business effect, and the acknowledgement remains **unverifiable**.

The supported button has a complete offered name of at most 120 characters, bounded complete
attribute/text/ancestor fingerprints, no child elements, external naming dependency, role override,
form owner or unsupported activation target. An isolated-realm marker created at observation binds
the observation token, document and root objects. Action-time validation checks the existing marker,
exact resolved node, connectedness, live eligibility and fingerprint in the same synchronous function
that invokes native activation. It never marks/adopts a new realm at action time.

Snapshot/action ownership is serialized. An attempted activation retires the current observation.
Loss, malformed acknowledgement or cancellation after admission preserves a connection-local unknown
gate; reobservation cannot clear it. There is no automatic pointer fallback, label replacement,
rebind or retry. This is not a durable operation ledger across connection/process restarts.

Typing remains disabled after the recorded focus-race reproduction. Trusted input, navigation,
public CDP CLI selection and durable browser authority also remain disabled. Existing CUA behavior
and authorizer/destructive gates are unchanged. The qualification API is a lower-level driver seam,
not a newly exposed agent mutation tool or a replacement for the guard.

## Observed checks

| Boundary | Result |
|---|---|
| Original b03c448 runtime, new positive ingress test | failed as predicted: backend refused, no activation |
| Final full regression suite, pure-Python twin excluding browser/live | 2,604 passed, 95 skipped, 51 deselected |
| Fresh installed macOS consumer outside checkout | 111 passed, including 33 real-Chrome cases; no CUA/browser-use installed |
| Installed Linux VM consumer, Debian 13.6 / Chromium 154 | 111 passed, zero failures/skips; same exact wheel; no CUA/browser-use installed |
| Ruff, notebook structure, offline lock consistency and 103 packaged resources | passed |

The full-suite interpreter is the previously prepared Python 3.12.6 SDK test environment with the
matching `.cleanup2` wheel and an absolute candidate source path. It is not a fresh full dependency
installation. The separate fresh consumer contains only pytest, psutil, websockets and this product
wheel installed with `--no-deps`; it exercises the bounded effector independently of CUA/browser-use.
This deliberately limited qualification environment is not the future public light-install recipe.

The unchanged test files are copied outside the checkout and run with `JEVDUAL_PURE_PY=1`, no
`PYTHONPATH`, an existing explicit Chrome executable and a registered browser marker. The five files
are `test_cdp_effector.py`, `test_cdp_transport_deadline.py`, `test_cdp_launch_custody.py`,
`test_cdp_click.py` and `test_cdp_click_contract.py`. Product wheel inventory/bytes/RECORD are verified
before installation. Fixture setup and readback use a separate connection; the HTTP server's saved
ingress records establish the requested fixture effect independently of driver acknowledgement.

## Retained identity failure and correction

Ordinary reload and same-node controls passed the initial numeric-only draft, but review found a
namespace gap after preflight. CDP numeric context/backend IDs can repeat in another renderer.

| Controlled real-Chrome run | Old and new IDs | Result |
|---|---|---|
| Before, runtime e91bca9 | context 3 / backend 9, different loaders | activated the new document; one unintended ingress |
| Reviewer replay after marker correction | context 3 / backend 9, different loaders | document_changed, not sent; zero ingress |
| Parent independent replay on corrected source | context 3 / backend 9, different loaders | document_changed, not sent; zero ingress |

These real namespace-collision probes used valid setup allocations and unchanged fixture responses,
not forged protocol replies. Allocation order was controlled; natural collision frequency was not
measured. The portable regression also models aliasing by substituting a real new-document object
after preflight, and is labeled as a model. The `document.open` control replaces the root while
retaining/reinserting the original button, checking the marker's root boundary.

Before evidence is preserved with its original source identities. The original prediction LCDC1 is
recorded as failed; the private-marker correction is a separate committed prediction, LCDC2.
An initial test import error was fixed before the positive baseline run and is not counted as a
product failure. Final evidence is not relabeled as the unsafe draft's result.

## Reference transfer

The existing repo-learn library was queried first. Stale agent-browser anchors were recaptured.
Source-grounding and target integration are separate records.

| Source | Adopted or rejected mechanism |
|---|---|
| Playwright deb7e862, crPage.ts:505–541 /1223–1252 | separate per-frame utility realm and context-specific backend resolution; no universal-access permission |
| Agent-browser 5868f7c0, element.rs:696–758 | exact-node resolution adopted; replacement by role/name rejected |
| Agent-browser interaction.rs:568–596 | readback-driven alternate-route retry rejected; unchanged state does not establish non-delivery |
| Playwright page-click.spec.ts:940–971 | locator retries through navigation fit a different subject contract and are rejected here |
| CUA 189df9d2, tools.rs:1602–1644; pinned archive agrees | pointer/mouse sequence differs from intrinsic activation; no parity claim |

Source anchors and rejection conditions are retained in
`/Users/thomasmain/projects/footwork/output/repo-learning/linux-consolidation/library`, pattern
`browser-action-refs-expire-with-document-generation-v2`, and task assessment
`output/repo-learning/cdp-click/assessment.md`. No upstream runtime or upstream test suite was run.

## Limits and next work

Qualification covers the recorded headless macOS/Linux fixture envelope. Headed behavior, other
control types, generic application compatibility and production business effects are unqualified.
The HTTP ledger proves these fixture ingresses; a native activation acknowledgement alone proves
none of them. Known-process cleanup and external reaping remain distinct from an atomic whole-tree
or no-zombie guarantee. No 2-CPU/8-GB footprint or throughput claim is made.

L3c still owns durable admission, retained unknowns and restart/no-replay recovery. The public light
metadata/profile split remains gated on that qualification; typing remains gated on target-local
delivery proof. Native SDK and existing browser-session authority producers are unchanged.

## Linux VM receipts

The [VM report](../linux-cdp-click-vm-20261031/report.md) retains the original 111-case batch,
all 30 saved ingress ledgers and six optional probes. The candidate batch's independent ledgers show
25 empty cases and five with exactly one intended ingress; there is no sentinel/pointer ingress.
The VM ran Python 3.12.14 and Chromium 154.0.8037.57 on Debian 13.6 x86-64 with a four-CPU quota and
16 GiB memory ceiling. The earlier 2-CPU/8-GB environment is not this qualification envelope.

All six additional Linux probes refused with zero ingress, but none forced the exact identical-button
ID collision reproduced on macOS. The failed allocation hypothesis and every attempt remain recorded;
the Linux probes do not claim that stronger reproduction. The portable modeled-alias test passed in
the 111-case batch.

VM PID1 is tail. A test-only subreaper recorded 172 adopted zombies after the candidate batch and
30 across the extra probes, then reaped all of them without extra signals; no live owned residue
remained. Product stop alone did not establish that no-zombie outcome. The wrapper, identities,
numeric exits and pre/post-reaping snapshots are retained in the VM result directories. No system
install, new VM/cloud resource, paid model call or candidate source change occurred.

VM evidence was published at `9aa195bea98d5120d7ecd64aaa6f04e8c63261da` and imported with
cherry-pick provenance, preserving original prediction/measurement order on its retained evidence
branch. Parent inspected reports, JUnit, wheel/source bindings and cleanup limitations.

## Release gate at report publication

The source and tests match the qualified c1496ca candidate; only notebook/results were added. Final
PR CI and review remain pending at publication and are tracked on the PR. Merge requires their
success. No source merge or public light-install delivery is implied by this checked artifact.
