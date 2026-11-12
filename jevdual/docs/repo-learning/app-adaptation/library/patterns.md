# Repository pattern library

Exported 2026-11-11T21:43:13.665618+00:00

Validation levels are author assertions. Inspect evidence and test transfer before reuse.

## Compute the capability report with the same function that gates dispatch, keyed by toolkit not application

ID: `capability-report-shares-dispatch-gate-v1`

**Problem:** A caller meeting an unfamiliar window cannot know which routes will work, and a separate capability table drifts from the code that actually refuses.

**Mechanism:** The observation of a window includes, per input route, available or refused with a reason, produced by calling the very decision function the action path calls. The report is advisory and every action rechecks. Route decisions key on runtime toolkit fingerprints (framework bundles, loaded images, web view detection), never on application names.

**When to use:** Session start on an unknown application; deciding between background, page-level and foreground delivery.

**When not to use:** As permission to act. Not for application-model quirks such as an editor whose accessibility value differs from its content; toolkit level does not see those.

**Tradeoffs:** Keeps core free of application names, but toolkit detection is incomplete (frameworks in the shared cache are invisible) and core still grows one branch per toolkit.

**Transfer:** application: Have look report per-route availability from posture and native dispatch gates. Classify the application-named branches in native.py: toolkit-level ones stay in core behind fingerprints, application-model ones (Finder rename and move, Preview save readback) move to recipes. Not implemented.; compatibility_checks: By inspection of the listed branches, about half are application-model and would not be removed by toolkit fingerprints; this card does not replace a recipe layer.; next_test: Compare the reported availability with the result of one background click on a Tk window and on an Electron app.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** In the reference, toolkit detection runs only on the pixel route, so a Tk window reports pointer delivery available and then refuses the click. The report states frame freshness as unknown.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised.

**Tags:** capability probe; toolkit; electron; route availability; unknown application; preflight

Evidence:

- `ev-841c4626f807bb4263436018`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/background_input.rs` lines 1–30; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `58f1628b1c69dd199b2af67fe20a4af37fad6dbd5b146892eb3182aebdf3d302`.
- `ev-c4b552986d9b50a27698526d`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/background_input.rs` lines 380–450; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `58f1628b1c69dd199b2af67fe20a4af37fad6dbd5b146892eb3182aebdf3d302`.
- `ev-7f14b1cc69869ea66e57e860`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/background_input.rs` lines 748–790; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `58f1628b1c69dd199b2af67fe20a4af37fad6dbd5b146892eb3182aebdf3d302`.
- `ev-dbd81d990083cc8af9ec5e82`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/platform-macos/src/tools/get_window_state.rs` lines 844–866; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `d10ceab78d3a2464fa242a11dd3aa4ca50766e1897141534e74866e270286c57`.
- `ev-9091b7ad19b7d57589de076e`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/platform-macos/src/input/pointer_toolkit.rs` lines 1–101; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `76a0ec4b1b9072498f5909783b7806e2b80f7cecd95d7a1cc62f70fece91749d`.
- `ev-d7b9ae4c7a7ef13ee7cd4ba7`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/platform-macos/src/tools/pixel_route.rs` lines 1–120; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `7a0f823e2c48d0d9d9699cfa65d34fa7e06138645f735efcd7e2b77e85d415b6`.

## Treat a single-use capture as provenance for a coordinate action, not as identity of the target

ID: `capture-identity-is-provenance-not-target-identity-v2`

**Problem:** Canvas, WebGL and custom-drawn surfaces have no element tree, so the only address is a point; a bare coordinate can be replayed against a different screen.

**Mechanism:** A coordinate action names the capture it was chosen from; the driver checks target, session, expiry and frame size, acts and deletes the capture. This prevents replay and records where the point came from. It does not show what is at the point now, so admission also needs a freshness and ambiguity policy, and the effect needs evidence from a non-visual channel.

**When to use:** Only where no accessibility or page reference exists. For web canvases prefer viewport coordinates in an exactly bound tab over screen coordinates.

**When not to use:** When a tree reference exists. Never treat a relocated template match as permission to act at the new point, and never treat identical pixels as identical state.

**Tradeoffs:** Gives every surface an address with weak identity. An independent effect check can find a wrong click only after its consequences.

**Transfer:** application: Web canvases first, through the pinned driver's pointer tool at viewport coordinates (hover, double-click, scroll, drag; no plain single click at coordinates). Screen-capture coordinates for native canvases only after the admission tests pass. The capture registry and pixel guard are already in the vendored archive. Not implemented.; compatibility_checks: The reference perception detector is AGPL and must not be vendored; the capture-binding contract is MIT. Screenshots are withheld under scope guards and after secrets, which removes this rung in those sessions.; next_test: Self-scrolling same-size surface and a repeated grid shifted one cell: capture identity alone is predicted to admit both; the added policy must refuse both.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** Admission compares identity and dimensions, not pixels: a surface that scrolls itself at the same size within the time limit is still admitted. A uniform grid shifted by one cell yields an identical crop and passes the pixel guard on the wrong item.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council round 1.

**Tags:** canvas; coordinates; pixel; vision; screenshot; studio; webgl; tree-less surface

Evidence:

- `ev-02424167da74b931c503a160`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/docs/perception-extension.md` lines 1–14; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `3cbb58f07e19988014de709e9015c9860cf36c4e85780e2fbf25666b0dade823`.
- `ev-8ae1afc05e2f9656eed6888c`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/docs/perception-extension.md` lines 140–195; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `3cbb58f07e19988014de709e9015c9860cf36c4e85780e2fbf25666b0dade823`.
- `ev-c7f8b491e3cd8670c816ac29`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/capture_registry.rs` lines 736–800; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `eae6f53a0ecd01c89326f59919de9b5b3c12f3aa75258c089c9b7aa5dad8431b`.
- `ev-3c7f274482946faf3bad279f`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/capture_registry.rs` lines 1411–1470; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `eae6f53a0ecd01c89326f59919de9b5b3c12f3aa75258c089c9b7aa5dad8431b`.
- `ev-47d5b765a8fb298775f9d7c6`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/fast_path/pixel_guard.rs` lines 74–172; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `9a11dd3d2edd2975adcc23d786290f65583e582aeec5c7da3aaa6da0d6d205bb`.
- `ev-5164f72bf49f1121f3b02766`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/fast_path/pixel_guard.rs` lines 220–260; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `9a11dd3d2edd2975adcc23d786290f65583e582aeec5c7da3aaa6da0d6d205bb`.

## Treat a single-use capture as provenance for a coordinate action, not as identity of the target

ID: `capture-identity-is-provenance-not-target-identity-v3`

**Problem:** Canvas, WebGL and custom-drawn surfaces have no element tree, so the only address is a point; a bare coordinate can be replayed against a different screen.

**Mechanism:** A coordinate action names the capture it was chosen from; the driver checks target, session, expiry and frame size, acts and deletes the capture. This prevents replay and records where the point came from. It does not show what is at the point now, so admission also needs a freshness and ambiguity policy, and the effect needs evidence from a non-visual channel.

**When to use:** Only where no accessibility or page reference exists, on web and native surfaces alike.

**When not to use:** When a tree reference exists. A bound tab identifies the document, not what sits at a viewport point after a scroll or redraw, so web coordinates get no exemption from the freshness and ambiguity policy.

**Tradeoffs:** Gives every surface an address with weak identity. An independent effect check can find a wrong click only after its consequences.

**Transfer:** application: Web canvases through the pinned driver's click tool at viewport coordinates on its trusted route, and its pointer tool for drag, hover and double-click. Treat as a foreground step until probed: Footwork's 2026-09-25 note records zero trusted-route successes in background posture. Screen-capture coordinates for native canvases after the same admission tests. Not implemented.; compatibility_checks: The capture registry and pixel guard files are byte-identical in the vendored archive of the pinned driver and in the reference checkout the evidence was captured from. The reference perception detector is AGPL and must not be vendored.; next_test: On a web canvas and on a native surface: one that scrolls itself without resizing, and a repeated grid shifted one cell. Capture or tab identity alone is predicted to admit both; the added policy must refuse both.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** Admission compares identity and dimensions, not pixels: a surface that scrolls itself at the same size within the time limit is still admitted. A uniform grid shifted by one cell yields an identical crop and passes the pixel guard on the wrong item.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council rounds 1 and 2.

**Tags:** canvas; coordinates; pixel; vision; screenshot; studio; webgl; tree-less surface

Evidence:

- `ev-02424167da74b931c503a160`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/docs/perception-extension.md` lines 1–14; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `3cbb58f07e19988014de709e9015c9860cf36c4e85780e2fbf25666b0dade823`.
- `ev-8ae1afc05e2f9656eed6888c`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/docs/perception-extension.md` lines 140–195; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `3cbb58f07e19988014de709e9015c9860cf36c4e85780e2fbf25666b0dade823`.
- `ev-c7f8b491e3cd8670c816ac29`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/capture_registry.rs` lines 736–800; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `eae6f53a0ecd01c89326f59919de9b5b3c12f3aa75258c089c9b7aa5dad8431b`.
- `ev-3c7f274482946faf3bad279f`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/capture_registry.rs` lines 1411–1470; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `eae6f53a0ecd01c89326f59919de9b5b3c12f3aa75258c089c9b7aa5dad8431b`.
- `ev-47d5b765a8fb298775f9d7c6`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/fast_path/pixel_guard.rs` lines 74–172; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `9a11dd3d2edd2975adcc23d786290f65583e582aeec5c7da3aaa6da0d6d205bb`.
- `ev-5164f72bf49f1121f3b02766`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/fast_path/pixel_guard.rs` lines 220–260; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `9a11dd3d2edd2975adcc23d786290f65583e582aeec5c7da3aaa6da0d6d205bb`.

## Deliver once, then re-read the same element against a typed postcondition inside the caller's deadline

ID: `deliver-once-bounded-reread-typed-postcondition-v1`

**Problem:** A receipt that only says the screen changed cannot tell the requested effect from an unrelated change, and a fixed sleep either wastes time or reads too early.

**Mechanism:** The action carries a predicate over the target element that returns true, false or unknown. After one delivery the tool re-reads on a short interval under a hard cap, extending only while typed text is still changing. Unknown returns delivered-unverified with the reason and the post-state; false returns an error with the post-state. Numeric tolerance applies only to continuous-control roles; integers and text compare exactly. Steppers advance one step at a time with a readback after each.

**When to use:** Value writes, selection, toggles, numeric controls, text entry.

**When not to use:** Effects with no element-level readback (canvas, audio); commits debounced past the cap come back unverified and need a different evidence channel.

**Tradeoffs:** Needs a predicate per action kind rather than per application. A short cap misses slow commits; a long one slows every action.

**Transfer:** application: Extend the numeric observation in native.py from metadata into an action-bound predicate, and replace 'some change was seen' receipts with predicate outcomes. Not implemented.; compatibility_checks: Footwork receipts currently diff before and after observations; 'confirmed' means a change, not the requested effect. Check interaction with look --until.; next_test: A setter that reads back 50.0000004 verifies on a slider and is refused on a text field; reads of old, partial, new verify with one dispatch.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** In the reference, click is excluded from state readback, so clicks carry no change summary. An editor whose accessibility value differs from its content can only ever return a mismatch.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised.

**Tags:** readback; postcondition; settle; receipt; numeric; slider; wait

Evidence:

- `ev-45c8cf9def44189514f7e3ea`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/core/src/actions/post_action.rs` lines 1–150; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `392909adfa1ee66bf6b5bdc770f7f3bd8b19cd38552abd0320d413636de6f134`.
- `ev-6c938da2c240e759616d6f1b`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/core/src/actions/post_action.rs` lines 150–270; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `392909adfa1ee66bf6b5bdc770f7f3bd8b19cd38552abd0320d413636de6f134`.
- `ev-3dae4611def8153058739fcb`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/core/src/actions/post_action_budget_tests.rs` lines 1–42; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `4f39c613122d579d734532fcf8a1d60ff59ea2ccaced3c5c70839a8c449013dc`.
- `ev-d4898f70dd1d5edb4a6b998f`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/core/src/tree/value_matches.rs` lines 1–35; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `281dc416073ef5b0da6f8e329bcdcf413f7e97dc2e6f91389698734235a7ef04`.
- `ev-6bc608373374e28d8a304ce9`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_value_write.rs` lines 1–126; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `7d208a1cce401f93d3960d2f5ac6a49d1aca569856e583e5f4b3ca12fd4993d2`.
- `ev-453b85272421c73bf71270e8`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/core/src/actions/action.rs` lines 80–100; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `e6b558d231e27801aef785267d66963306d49291de6a23e62c11c233ae1e3e38`.

## Hit-test immediately before dispatch and refuse by naming what covers the target

ID: `hit-test-before-dispatch-names-cover-v1`

**Problem:** A click sent to an element that is hidden, disabled, off-screen or under an overlay lands on something else or nowhere, and a bare failure gives the caller nothing to act on.

**Mechanism:** Scroll the target into view; check disconnected, disabled, inert, hidden and outside-viewport; ask the page which element is at the target's centre; if it is neither the target nor inside it, retry once centred, then refuse and report the covering element's role and name. Only visible text is eligible to be quoted as evidence, because the accessibility tree keeps zero-opacity text such as pre-rendered success banners.

**When to use:** Page-level clicks beyond plain buttons; any reader that quotes page text as proof.

**When not to use:** When the check would run in the page's main world, where the page can override it. It does not replace a post-action readback: an overlay can appear between check and press.

**Tradeoffs:** One extra round trip per action; turns silent wrong clicks into refusals with a reason the caller can act on.

**Transfer:** application: Use as the admission check that lets the owned browser lane accept more than plain buttons, mapping a failed check to not-sent with the cover named. Covers the DemoGeek case where a hidden zero-size element came back only as outside the window. Not implemented.; compatibility_checks: Must run in an isolated world. Footwork already refuses on changed targets; this adds a reason.; next_test: Fixture with a cookie banner over a button: not-sent naming the banner. Fixture that inserts an overlay on pointer-down: the pre-check alone is predicted to misreport, showing the readback is still required.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** One reference passes silently when the node cannot be resolved; another counts the action as working when no events arrive at all.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised.

**Tags:** actionability; occlusion; overlay; hidden element; visibility; demogeek; refusal reason

Evidence:

- `ev-f57b91387e5b3e22fc0f1c1b`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/ax.py` lines 199–260; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `94dae4a9f7bc8f5bae02e377e14df46c343277ff0313c13837873dc1b98188df`.
- `ev-d69a318fb6a7cb0ab8f4280a`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/ax.py` lines 704–765; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `94dae4a9f7bc8f5bae02e377e14df46c343277ff0313c13837873dc1b98188df`.
- `ev-9be1e529ed0406516c6b2554`: `/Volumes/External SSD/referencerepos/playwright/packages/injected/src/injectedScript.ts` lines 1153–1221; fresh; HEAD `3b438229c6a2ccdbe2d3572755935892203d83c3`; SHA-256 `dccf169ba8b883e1f55f88870899c8f5e90af2e4c17bf78e517a3e179734dad2`.
- `ev-808bf0a09621ff659497f042`: `/Volumes/External SSD/referencerepos/playwright/packages/playwright-core/src/server/dom.ts` lines 432–521; fresh; HEAD `3b438229c6a2ccdbe2d3572755935892203d83c3`; SHA-256 `65cb43c91893e5cb82869d37686ad1d1500f4719711015d10eaac7c0b04cfb66`.
- `ev-35f2533a9c45359639ba4663`: `/Volumes/External SSD/referencerepos/agent-browser/cli/src/native/element.rs` lines 612–675; fresh; HEAD `2f1649cefb82f417abbb2712f5397439d010698e`; SHA-256 `0b8b3eb65e8ce13abd68966184bd570a1788272a5a44d103b4e0a9aaa4618376`.
- `ev-3700a0203d30e947629e8716`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/ax.py` lines 105–197; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `94dae4a9f7bc8f5bae02e377e14df46c343277ff0313c13837873dc1b98188df`.
- `ev-b813355e11dbdc75e6e91616`: `/Volumes/External SSD/referencerepos/browser-use/tests/ci/test_ultrafast.py` lines 183–207; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `78f44ddced7b4ccfa8916cb4e089c41fd18499ed51802cd0319123bdba64b889`.

## Advance a fallback ladder only for repeat-safe operations whose effect was refuted after a declared bound

ID: `ladder-advances-only-for-repeat-safe-refuted-effects-v2`

**Problem:** A tool that falls back from a semantic action to a synthetic click whenever the first rung looks unsuccessful can act twice, and a tool with one fixed route per operation needs new code for every surface where that route fails.

**Mechanism:** Each rung returns a delivery outcome (not sent, sent, unknown) and an effect outcome (confirmed, refuted within a declared settle bound, unknown). Unknown delivery blocks further mutation. Another rung may run automatically only when the operation is declared repeat-safe, meaning it is expressed as a target state such as a field holding a value or a toggle being on, and its effect was read as refuted after that operation's bound. Presses, submissions and anything that spends money never advance automatically: the outcome and escalation advice go back to the caller. Every step records its mechanism.

**When to use:** Setters with a readable target state on surfaces where the first channel can fail silently.

**When not to use:** Any action whose effect may land after the bound or elsewhere than the target. A reading of 'not changed yet' is not evidence that nothing will happen.

**Tradeoffs:** Stops more often than the reference chains do. Needs a per-operation bound and a repeat-safe declaration.

**Transfer:** application: Define the delivery-by-effect outcome table before widening the browser lane; carry the pinned driver's Confirmed and Unverifiable effect and its escalation through browser_driver._effect instead of collapsing them. A general ladder for native routes is not proposed until this holds on the browser lane. Not implemented.; compatibility_checks: Footwork today has two automatic fallbacks (same-pid keyboard ambiguity to foreground; refused scroll to Page Down). Check that existing 'unverifiable' receipts map to delivered-unverified and that durable unknown-effect barriers still block a second dispatch.; next_test: Fixture whose effect lands after the bound, one with a lost acknowledgement, one interrupted by restart: one dispatch, unknown outcome, no advance in all three.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** The reference's own right-click chain continues after unverified delivery, made safe only by re-checking for an open menu before each step. Its no-effect reading for selection is taken inside a short settle window. An application slower than the bound would receive a second dispatch under the v1 wording.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council round 1.

**Tags:** fallback; escalation; action route; unverifiable; suno; app adaptation; channel ladder

Evidence:

- `ev-3d88ae816364a8a76d300fcb`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/mod.rs` lines 17–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `3937f0a04fbc7b90e47364f8c9dcc00ed48d3659b3d47473886d6aac43d218be`.
- `ev-6af3ead68870e6c536d1cf72`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_delivery.rs` lines 1–72; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `ea33feb3aba206533d9cf27587f527db570f9cb94e634adadf368e295e8e433b`.
- `ev-e223523288383250d3076ef3`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/press_selection.rs` lines 1–139; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `67604ea05c297214ef032659bef12f60c1654b3a65d63c7376442b3fbf084d95`.
- `ev-35ee441f125db3ebc8e80dd7`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_defs.rs` lines 1–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `a0d21b125f57f31ba413d6cb862b1ba8c9738871fd6b0c1911bfff313019c784`.
- `ev-9a65bbcb54dccfd51d407583`: `/Users/thomasmain/projects/demogeek/Peekaboo/Core/PeekabooAutomationKit/Sources/PeekabooAutomationKit/Strategy/DesktopOperationExecutor.swift` lines 47–159; fresh; HEAD `671455913a6e1ee8f6de278f0b3c55b8531036f3`; SHA-256 `af40cf288789828a3b44a7cb6640f5aa5eec65f42fb363a17131ce14c34f8a02`.
- `ev-8fe424e2f958236f2de4ce69`: `/Volumes/External SSD/referencerepos/typesafe-computer-use/typesafe_computer_use/actions.py` lines 52–70; fresh; HEAD `44ca11f0935b021b73020825da054b5c92cc1288`; SHA-256 `72f149792289be8c44a37f2a223f166a659ba5be58eed87f232f6d22214733bd`.

## Advance a fallback ladder only on not-delivered or a positively observed no-effect

ID: `ladder-advances-only-on-observed-no-effect-v1`

**Problem:** A tool that falls back from a semantic action to a synthetic click whenever the first rung looks unsuccessful can act twice, and a tool with one fixed route per operation needs new code for every surface where that route fails.

**Mechanism:** Each rung returns one typed outcome: not delivered, satisfied without delivery, delivered unverified, delivered without effect, delivered verified. Only not-delivered and delivered-without-effect continue to the next rung; delivered-unverified stops the chain so nothing is dispatched twice. Delivered-without-effect requires a positive readback (for example the selected attribute still false), never an unreadable one. Physical rungs run only under a caller policy that allows them. Every step records its mechanism so the caller sees which rung acted.

**When to use:** Any action whose first channel can fail silently on some surfaces: accessibility press on web content, value writes that echo without applying.

**When not to use:** When no channel can read the postcondition: the ladder then stops honestly at unverified and makes no progress, so a different readback channel is needed, not more rungs.

**Tradeoffs:** Stops more often than optimistic fallback; needs a per-action postcondition predicate. Removes the need for per-operation route branches.

**Transfer:** application: Replace the fixed route per operation in native.act with a declared ladder whose rungs return these outcomes; keep posture as the gate on physical rungs; put the acting rung on the receipt. Not implemented.; compatibility_checks: Footwork today has two automatic fallbacks (same-pid keyboard ambiguity to foreground; refused scroll to Page Down). Check that existing 'unverifiable' receipts map to delivered-unverified and that durable unknown-effect barriers still block a second dispatch.; next_test: Fake element whose press succeeds and whose selected state reads false: next rung recorded. Same element with the state unreadable: stop, exactly one dispatch.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** An accessibility press on a Chromium group returns success and changes nothing; with the attribute unreadable the chain stops at delivered-unverified. One reference tool reports 'pressed via accessibility' with no readback at all.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised.

**Tags:** fallback; escalation; action route; unverifiable; suno; app adaptation; channel ladder

Evidence:

- `ev-3d88ae816364a8a76d300fcb`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/mod.rs` lines 17–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `3937f0a04fbc7b90e47364f8c9dcc00ed48d3659b3d47473886d6aac43d218be`.
- `ev-6af3ead68870e6c536d1cf72`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_delivery.rs` lines 1–72; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `ea33feb3aba206533d9cf27587f527db570f9cb94e634adadf368e295e8e433b`.
- `ev-e223523288383250d3076ef3`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/press_selection.rs` lines 1–139; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `67604ea05c297214ef032659bef12f60c1654b3a65d63c7376442b3fbf084d95`.
- `ev-35ee441f125db3ebc8e80dd7`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_defs.rs` lines 1–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `a0d21b125f57f31ba413d6cb862b1ba8c9738871fd6b0c1911bfff313019c784`.
- `ev-9a65bbcb54dccfd51d407583`: `/Users/thomasmain/projects/demogeek/Peekaboo/Core/PeekabooAutomationKit/Sources/PeekabooAutomationKit/Strategy/DesktopOperationExecutor.swift` lines 47–159; fresh; HEAD `671455913a6e1ee8f6de278f0b3c55b8531036f3`; SHA-256 `af40cf288789828a3b44a7cb6640f5aa5eec65f42fb363a17131ce14c34f8a02`.
- `ev-8fe424e2f958236f2de4ce69`: `/Volumes/External SSD/referencerepos/typesafe-computer-use/typesafe_computer_use/actions.py` lines 52–70; fresh; HEAD `44ca11f0935b021b73020825da054b5c92cc1288`; SHA-256 `72f149792289be8c44a37f2a223f166a659ba5be58eed87f232f6d22214733bd`.

## Classify the network write as evidence of an outcome the page cannot show

ID: `network-write-classified-as-outcome-evidence-v1`

**Problem:** Edits on canvas or audio surfaces leave nothing in the element tree to read back.

**Mechanism:** Observe the write the action causes and classify its answer: a server error, timeout, challenge page or non-JSON success is outcome-unknown; a ledger keyed by the admitted operation prevents sending the same write twice.

**When to use:** Effects that persist through a first-party request and are invisible in the page.

**When not to use:** As proof the effect was applied: a success status means accepted. It needs a later read of the resource. Not available on a browser reached only through accessibility.

**Tradeoffs:** Adds an evidence channel independent of rendering; requires page-level access and care with private request data.

**Transfer:** application: Record requests around one admitted page action in the owned browser and bind the record to the operation token, as a completion reader for surfaces such as an audio editor. Not implemented.; compatibility_checks: Request bodies can hold private content; apply the existing redaction and withhold rules.; next_test: One fixture POST from an owned-browser click: the record binds to the operation token and a 5xx is reported as outcome unknown.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** The reference uses this to replay recorded flows; using it to confirm a live click is an inference from that design.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised.

**Tags:** network; completion reader; canvas; audio; outcome unknown; idempotency

Evidence:

- `ev-0f0d860693ea2bf9bb60f525`: `/Volumes/External SSD/referencerepos/agent-browser/cli/src/native/flow/outcome.rs` lines 1–60; fresh; HEAD `2f1649cefb82f417abbb2712f5397439d010698e`; SHA-256 `4353f0257375a8412590d4247ac70c4eb512c906fdc5dfe3bae839b347e1d88d`.
- `ev-3c10f7b04604e919b891a9d9`: `/Volumes/External SSD/referencerepos/agent-browser/cli/src/native/flow/outcome.rs` lines 569–606; fresh; HEAD `2f1649cefb82f417abbb2712f5397439d010698e`; SHA-256 `4353f0257375a8412590d4247ac70c4eb512c906fdc5dfe3bae839b347e1d88d`.
- `ev-1407f66de4600ca350950ebb`: `/Volumes/External SSD/referencerepos/agent-browser/cli/src/native/flow/send.rs` lines 10–60; fresh; HEAD `2f1649cefb82f417abbb2712f5397439d010698e`; SHA-256 `ad7964c623156afbb93710df0b014aa0b7851d8b356f4808af737750fb1d74c8`.

## Try another rung only when nothing was sent; after a send, an absent effect is unknown

ID: `no-automatic-dispatch-after-a-send-v3`

**Problem:** A fallback that fires when the first route shows no effect cannot tell a silent no-op from an effect that lands late, so it can act twice.

**Mechanism:** Each action returns a delivery outcome (not sent, sent, unknown) and an effect outcome (confirmed, absent at a declared bound, unreadable). Another rung may be tried automatically only when nothing was sent. After a send, an effect absent at the bound is an unknown outcome: no second dispatch, the typed outcome and escalation advice go to the caller. Sent with an unreadable effect blocks further mutation of that target until it is re-observed or acknowledged. Unknown delivery blocks all mutation in the domain and survives a crash.

**When to use:** Any surface where a route can report success without acting or can act late.

**When not to use:** As a way to make progress unattended on surfaces whose first route often no-ops: this rule hands those cases to the caller. A later extension for absolute setters, whose mechanism yields the same state whether or not an earlier application lands, needs its own test.

**Tradeoffs:** Stops more often than any reference chain. Wording a goal as a target state does not make its mechanism repeat-safe: a second click on a toggle flips it.

**Transfer:** application: Write the nine-cell delivery-by-effect table before widening the browser lane, and carry the pinned driver's Confirmed and Unverifiable effect through browser_driver._effect. A driver Confirmed is a target-state reading and does not settle the business effect. Not implemented.; compatibility_checks: The CDP lane already blocks mutation after an acknowledged delivery with unverified effect; start --browser records delivery as unknown for every driver reply and has no crash-durable barrier.; next_test: A click-toggle whose effect lands after the bound, a lost acknowledgement, an acknowledged action with unreadable effect, and a restart mid-action: exactly one dispatch in each, and a block on further mutation in the last three.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** The reference's right-click chain continues after unverified delivery, safe only because each step re-checks for an open menu. Its no-effect reading for selection sits inside a short settle window.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council rounds 1 and 2.

**Tags:** fallback; escalation; action route; unverifiable; suno; app adaptation; channel ladder

Evidence:

- `ev-3d88ae816364a8a76d300fcb`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/mod.rs` lines 17–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `3937f0a04fbc7b90e47364f8c9dcc00ed48d3659b3d47473886d6aac43d218be`.
- `ev-6af3ead68870e6c536d1cf72`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_delivery.rs` lines 1–72; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `ea33feb3aba206533d9cf27587f527db570f9cb94e634adadf368e295e8e433b`.
- `ev-e223523288383250d3076ef3`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/press_selection.rs` lines 1–139; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `67604ea05c297214ef032659bef12f60c1654b3a65d63c7376442b3fbf084d95`.
- `ev-35ee441f125db3ebc8e80dd7`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_defs.rs` lines 1–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `a0d21b125f57f31ba413d6cb862b1ba8c9738871fd6b0c1911bfff313019c784`.
- `ev-9a65bbcb54dccfd51d407583`: `/Users/thomasmain/projects/demogeek/Peekaboo/Core/PeekabooAutomationKit/Sources/PeekabooAutomationKit/Strategy/DesktopOperationExecutor.swift` lines 47–159; fresh; HEAD `671455913a6e1ee8f6de278f0b3c55b8531036f3`; SHA-256 `af40cf288789828a3b44a7cb6640f5aa5eec65f42fb363a17131ce14c34f8a02`.
- `ev-8fe424e2f958236f2de4ce69`: `/Volumes/External SSD/referencerepos/typesafe-computer-use/typesafe_computer_use/actions.py` lines 52–70; fresh; HEAD `44ca11f0935b021b73020825da054b5c92cc1288`; SHA-256 `72f149792289be8c44a37f2a223f166a659ba5be58eed87f232f6d22214733bd`.

## Try another rung only when nothing was sent; after a send, keep the custody the session already has

ID: `no-automatic-dispatch-after-a-send-v4`

**Problem:** A fallback that fires when the first route shows no effect cannot tell a silent no-op from an effect that lands late, so it can act twice.

**Mechanism:** Each action returns a delivery outcome (not sent, sent, unknown) and an effect outcome (confirmed, absent at a declared bound, unreadable). Another rung may be tried automatically only when nothing was sent. After a send, an effect absent at the bound is an unknown outcome and no second dispatch follows. What an unknown outcome then does is set by the session's existing custody level, not by this rule: an ordinary session reports it and the caller decides; a durable session blocks all mutation in its authority domain, across a crash, until a qualified reconciliation producer clears it. A fresh observation does not clear it. The effector's escalation advice is carried for diagnosis only, never offered as a next step.

**When to use:** Any surface where a route can report success without acting or can act late.

**When not to use:** As a way to make progress unattended on surfaces whose first route often no-ops: this rule hands those cases to the caller. A later extension for absolute setters, whose mechanism yields the same state whether or not an earlier application lands, needs its own test.

**Tradeoffs:** Stops more often than any reference chain. On a durable session with no general reconciliation producer, the session halts at the first unconfirmed effect, so durable multi-step work reaches only as far as effect readers confirm. Wording a goal as a target state does not make its mechanism repeat-safe: a second click on a toggle flips it.

**Transfer:** application: State the browser lane's outcomes in the two existing custody levels before widening it, and carry the pinned driver's Confirmed and Unverifiable effect through browser_driver._effect. Decide whether a driver Confirmed, which reads the target's state, may settle a durable operation; it never settles a business effect. Not implemented.; compatibility_checks: Footwork's durable rule (session_operations.py:338-349) makes every dispatched outcome other than sent-with-confirmed-or-partial-effect unknown, blocks the domain, and refuses manual resolution; owned-cdp.md says a new observation cannot clear an uncertain operation; durable-native-operator.md:63 says no general app-effect reconciliation producer exists. start --browser runs outside the durable authority and records delivery as unknown for every driver reply. The pinned driver advises retry_with_page_action for a page click whose target did not change.; next_test: A click-toggle whose effect lands after the bound, a lost acknowledgement, an acknowledged action with unreadable effect, and a restart mid-action: exactly one dispatch in each; on a durable session the next mutation is refused in all four and observation does not clear the block.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** The reference's right-click chain continues after unverified delivery, safe only because each step re-checks for an open menu. Its no-effect reading for selection sits inside a short settle window.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council rounds 1 and 2 and the one completed review of round 3.

**Tags:** fallback; escalation; action route; unverifiable; suno; app adaptation; channel ladder

Evidence:

- `ev-3d88ae816364a8a76d300fcb`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/mod.rs` lines 17–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `3937f0a04fbc7b90e47364f8c9dcc00ed48d3659b3d47473886d6aac43d218be`.
- `ev-6af3ead68870e6c536d1cf72`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_delivery.rs` lines 1–72; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `ea33feb3aba206533d9cf27587f527db570f9cb94e634adadf368e295e8e433b`.
- `ev-e223523288383250d3076ef3`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/press_selection.rs` lines 1–139; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `67604ea05c297214ef032659bef12f60c1654b3a65d63c7376442b3fbf084d95`.
- `ev-35ee441f125db3ebc8e80dd7`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_defs.rs` lines 1–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `a0d21b125f57f31ba413d6cb862b1ba8c9738871fd6b0c1911bfff313019c784`.
- `ev-9a65bbcb54dccfd51d407583`: `/Users/thomasmain/projects/demogeek/Peekaboo/Core/PeekabooAutomationKit/Sources/PeekabooAutomationKit/Strategy/DesktopOperationExecutor.swift` lines 47–159; fresh; HEAD `671455913a6e1ee8f6de278f0b3c55b8531036f3`; SHA-256 `af40cf288789828a3b44a7cb6640f5aa5eec65f42fb363a17131ce14c34f8a02`.
- `ev-8fe424e2f958236f2de4ce69`: `/Volumes/External SSD/referencerepos/typesafe-computer-use/typesafe_computer_use/actions.py` lines 52–70; fresh; HEAD `44ca11f0935b021b73020825da054b5c92cc1288`; SHA-256 `72f149792289be8c44a37f2a223f166a659ba5be58eed87f232f6d22214733bd`.

## Try another rung only when nothing was sent; after a send, keep the custody the session already has

ID: `no-automatic-dispatch-after-a-send-v5`

**Problem:** A fallback that fires when the first route shows no effect cannot tell a silent no-op from an effect that lands late, so it can act twice.

**Mechanism:** Each action returns a delivery outcome (not sent, sent, unknown) and an effect outcome (confirmed, absent at a declared bound, unreadable). Another rung may be tried automatically only when nothing was sent. After a send, an effect absent at the bound is an unknown outcome and no second dispatch follows. What an unknown outcome then does is set by the session's existing custody rule, not by this one. Footwork has three: an ordinary session blocks no mutation but refuses completion while the last input is unsettled, until it is re-observed; a durable native session blocks all mutation in its authority domain, across a crash, until a qualified reconciliation producer clears it; a durable browser session does the same and additionally never settles a sent action, because neither an acknowledgement nor a changed DOM establishes completion. The effector's escalation advice is carried for diagnosis only, never offered as a next step.

**When to use:** Any surface where a route can report success without acting or can act late.

**When not to use:** As a way to make progress unattended on surfaces whose first route often no-ops: this rule hands those cases to the caller. A later extension for absolute setters, whose mechanism yields the same state whether or not an earlier application lands, needs its own test.

**Tradeoffs:** Stops more often than any reference chain. A durable browser session stops at the first sent action, so it serves one action that must not be sent twice; durable multi-step browser work needs a completion reader bound to evidence independent of the page. Wording a goal as a target state does not make its mechanism repeat-safe: a second click on a toggle flips it.

**Transfer:** application: State the browser lane's outcomes under the three existing custody rules before widening it, changing none of them, and carry the pinned driver's Confirmed and Unverifiable effect through browser_driver._effect. A driver Confirmed means the target's state differed before and after; on an ordinary session it leaves no pending uncertainty at completion, as for native actions, and on a durable browser session it settles nothing. Not implemented.; compatibility_checks: session_operations.py:338-349 (native durable rule); browser_authority.py:1-7, 111-124, 212-215 (every acknowledged browser send is unverifiable and a confirmed or partial effect is refused); session.py:2838-2872 (done refused over unsettled pending input on any session) and 1084-1089 (the next observation with a receipt clears it); owned-cdp.md:39-63; durable-native-operator.md:63 (no general reconciliation producer). start --browser runs as an ordinary session and records delivery as unknown for every driver reply. The pinned driver advises retry_with_page_action for a page click whose target did not change.; next_test: Five cases: a click-toggle whose effect lands after the bound, a lost acknowledgement, an acknowledged action with unreadable effect, a restart mid-action, and a page click the driver reads back as Confirmed. Exactly one dispatch in each; on a durable browser session all five stay unknown and block the next mutation, and observation does not clear them; on an ordinary session the first four refuse completion until re-observed.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** The reference's right-click chain continues after unverified delivery, safe only because each step re-checks for an open menu. Its no-effect reading for selection sits inside a short settle window.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council rounds 1 to 4 (rounds 3 and 4 partial).

**Tags:** fallback; escalation; action route; unverifiable; suno; app adaptation; channel ladder

Evidence:

- `ev-3d88ae816364a8a76d300fcb`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/mod.rs` lines 17–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `3937f0a04fbc7b90e47364f8c9dcc00ed48d3659b3d47473886d6aac43d218be`.
- `ev-6af3ead68870e6c536d1cf72`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_delivery.rs` lines 1–72; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `ea33feb3aba206533d9cf27587f527db570f9cb94e634adadf368e295e8e433b`.
- `ev-e223523288383250d3076ef3`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/press_selection.rs` lines 1–139; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `67604ea05c297214ef032659bef12f60c1654b3a65d63c7376442b3fbf084d95`.
- `ev-35ee441f125db3ebc8e80dd7`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_defs.rs` lines 1–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `a0d21b125f57f31ba413d6cb862b1ba8c9738871fd6b0c1911bfff313019c784`.
- `ev-9a65bbcb54dccfd51d407583`: `/Users/thomasmain/projects/demogeek/Peekaboo/Core/PeekabooAutomationKit/Sources/PeekabooAutomationKit/Strategy/DesktopOperationExecutor.swift` lines 47–159; fresh; HEAD `671455913a6e1ee8f6de278f0b3c55b8531036f3`; SHA-256 `af40cf288789828a3b44a7cb6640f5aa5eec65f42fb363a17131ce14c34f8a02`.
- `ev-8fe424e2f958236f2de4ce69`: `/Volumes/External SSD/referencerepos/typesafe-computer-use/typesafe_computer_use/actions.py` lines 52–70; fresh; HEAD `44ca11f0935b021b73020825da054b5c92cc1288`; SHA-256 `72f149792289be8c44a37f2a223f166a659ba5be58eed87f232f6d22214733bd`.

## Try another rung only when nothing was sent; after a send, keep the custody the session already has

ID: `no-automatic-dispatch-after-a-send-v6`

**Problem:** A fallback that fires when the first route shows no effect cannot tell a silent no-op from an effect that lands late, so it can act twice.

**Mechanism:** Each action returns a delivery outcome (not sent, sent, unknown) and an effect outcome (confirmed, absent at a declared bound, unreadable). Another rung may be tried automatically only when nothing was sent. After a send, an effect absent at the bound is an unknown outcome and no second dispatch follows. What an unknown outcome then does is set by the session's existing custody rule, not by this one. Footwork has three. An ordinary session blocks no mutation; it refuses completion while the last dispatched input has an effect that is not confirmed or partial, or carries an error, until an observation yields a receipt; delivery does not enter that rule. A durable native session blocks all mutation in its authority domain, across a crash, until a qualified reconciliation producer clears it. A durable browser session does the same and additionally never settles a sent action, because neither an acknowledgement nor a changed DOM establishes completion. The effector's escalation advice is carried for diagnosis only, never offered as a next step.

**When to use:** Any surface where a route can report success without acting or can act late.

**When not to use:** As a way to make progress unattended on surfaces whose first route often no-ops: this rule hands those cases to the caller. A later extension for absolute setters, whose mechanism yields the same state whether or not an earlier application lands, needs its own test.

**Tradeoffs:** Stops more often than any reference chain. A durable browser session stops at the first sent action, so it serves one action that must not be sent twice; durable multi-step browser work needs a completion reader bound to evidence independent of the page. An ordinary session keeps no record of an action interrupted before its result is saved, so a crash mid-action is invisible there unless the pending record is written before dispatch. Wording a goal as a target state does not make its mechanism repeat-safe: a second click on a toggle flips it.

**Transfer:** application: State the browser lane's outcomes under the three existing custody rules before widening it, weakening none, and carry the pinned driver's Confirmed and Unverifiable effect through browser_driver._effect for the default page-click route (the trusted click returns no effect readback). Add one thing to the ordinary rule: save the pending record before dispatch. Not implemented.; compatibility_checks: session_operations.py:338-349 (native durable rule); browser_authority.py:1-7, 111-124, 212-215 (every acknowledged browser send is unverifiable and a confirmed or partial effect is refused); session.py:2838-2872 (done refused over unsettled pending input, keyed on effect and error), 1084-1089 (the next observation with a receipt clears it), 2407-2420 against 2538-2625 (only the durable path writes a record before dispatch); browser_driver.py:359 (a browser effect defaults to dispatched); owned-cdp.md:39-63; durable-native-operator.md:63 (no general reconciliation producer). The pinned driver advises retry_with_page_action for a page click whose target did not change.; next_test: Five cases: a click-toggle whose effect lands after the bound, a lost reply, an acknowledged action with unreadable effect, a process death between input and saved result, and a page click the driver reads back as Confirmed. Exactly one dispatch in each. Durable browser: all five stay unknown and block the next mutation; observation does not clear them. Ordinary: the first three refuse completion until re-observed; the Confirmed case is not held; the process-death case is run before and after the pre-dispatch save, predicting completion accepted before and refused after.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** The reference's right-click chain continues after unverified delivery, safe only because each step re-checks for an open menu. Its no-effect reading for selection sits inside a short settle window.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council rounds 1 to 5 (rounds 3 to 5 partial).

**Tags:** fallback; escalation; action route; unverifiable; suno; app adaptation; channel ladder

Evidence:

- `ev-3d88ae816364a8a76d300fcb`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/mod.rs` lines 17–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `3937f0a04fbc7b90e47364f8c9dcc00ed48d3659b3d47473886d6aac43d218be`.
- `ev-6af3ead68870e6c536d1cf72`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_delivery.rs` lines 1–72; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `ea33feb3aba206533d9cf27587f527db570f9cb94e634adadf368e295e8e433b`.
- `ev-e223523288383250d3076ef3`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/press_selection.rs` lines 1–139; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `67604ea05c297214ef032659bef12f60c1654b3a65d63c7376442b3fbf084d95`.
- `ev-35ee441f125db3ebc8e80dd7`: `/Volumes/External SSD/referencerepos/agent-desktop/crates/macos/src/actions/chain/chain_defs.rs` lines 1–140; fresh; HEAD `54855b6225aec00da4ac65e2d0362fd41cd9fcb3`; SHA-256 `a0d21b125f57f31ba413d6cb862b1ba8c9738871fd6b0c1911bfff313019c784`.
- `ev-9a65bbcb54dccfd51d407583`: `/Users/thomasmain/projects/demogeek/Peekaboo/Core/PeekabooAutomationKit/Sources/PeekabooAutomationKit/Strategy/DesktopOperationExecutor.swift` lines 47–159; fresh; HEAD `671455913a6e1ee8f6de278f0b3c55b8531036f3`; SHA-256 `af40cf288789828a3b44a7cb6640f5aa5eec65f42fb363a17131ce14c34f8a02`.
- `ev-8fe424e2f958236f2de4ce69`: `/Volumes/External SSD/referencerepos/typesafe-computer-use/typesafe_computer_use/actions.py` lines 52–70; fresh; HEAD `44ca11f0935b021b73020825da054b5c92cc1288`; SHA-256 `72f149792289be8c44a37f2a223f166a659ba5be58eed87f232f6d22214733bd`.

## Enter text at page level and read the value back from the target node

ID: `page-typing-reads-back-target-node-v1`

**Problem:** Driving a rich web editor through the desktop accessibility tree loses text, selection and blank lines, and typing through keys needs window focus the person is using.

**Mechanism:** Confirm the intended node holds focus by checking the active element through shadow roots from an isolated world; select all with an editing command; insert the text through the protocol's insert-text call with the final character as a key event so editors see input; then read inner text (content-editable) or value (inputs) from that same node and compare with what was sent.

**When to use:** Text entry into inputs and content-editable editors in a browser the tool can reach at page level.

**When not to use:** When the editor's internal model can diverge from the page (model-driven editors): the node text is then evidence of rendering, not of the saved value, and a second channel (the application's own copy, a reload, a network write) is needed.

**Tradeoffs:** No focus or foreground needed. The reference only reports a mismatch; a verifying tool must refuse on it.

**Transfer:** application: Re-enable typing on the Footwork-owned browser lane with this focus check and readback; the isolated-world focus check addresses the focus race recorded as the reason typing is disabled. Not implemented.; compatibility_checks: Footwork's owned CDP lane disables typing and navigation; the older browser lane uses the driver's insert-text mode. Whether node inner text keeps the blank lines the accessibility value dropped in the Suno lyrics case is inferred, not observed.; next_test: Content-editable fixture with a sanitizing input handler: type 461 characters with 24 line feeds; compare node inner text with the accessibility value. If inner text also drops lines, this channel does not replace the clipboard verifier.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** A neighbouring tool clears a field by assigning an empty value, which does not clear a content-editable node, and never reads back.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised.

**Tags:** contenteditable; rich text; lyrics; suno; cdp; insert text; web editor; browser

Evidence:

- `ev-e77fea9a4bd8919233daf679`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/repl/worker.py` lines 763–896; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `79172a7c6907d3a7efbda61eef64c0aff7b1c369c1d237ecec980663cb01af28`.
- `ev-91e7f6c7d9626b98d2086eb6`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/ax.py` lines 767–868; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `94dae4a9f7bc8f5bae02e377e14df46c343277ff0313c13837873dc1b98188df`.
- `ev-40755ae03e014e2ce185eb62`: `/Volumes/External SSD/referencerepos/agent-browser/cli/src/native/interaction.rs` lines 155–220; fresh; HEAD `2f1649cefb82f417abbb2712f5397439d010698e`; SHA-256 `001a3fd213ee1001c6d2d6ac717f40a37b648b0fec88c78413b2ccda18ff564a`.
- `ev-5f90cdfa630a54f70ed7148e`: `/Volumes/External SSD/referencerepos/browser-use/tests/ci/test_ultrafast.py` lines 239–249; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `78f44ddced7b4ccfa8916cb4e089c41fd18499ed51802cd0319123bdba64b889`.
- `ev-13224c8135b7b9f3ff62f4cd`: `/Volumes/External SSD/referencerepos/browser-use/tests/ci/test_ultrafast.py` lines 352–373; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `78f44ddced7b4ccfa8916cb4e089c41fd18499ed51802cd0319123bdba64b889`.

## Enter text at page level and read the value back from the target node

ID: `page-typing-reads-back-target-node-v2`

**Problem:** Driving a rich web editor through the desktop accessibility tree loses text, selection and blank lines, and typing through keys needs window focus the person is using.

**Mechanism:** After entering text at page level, read inner text (content-editable) or value (inputs) from the same node and compare with what was sent under a declared equivalence. The reference reads back and only reports a mismatch; it checks focus from an isolated world only for secret entry. Combining an isolated-world focus check with a readback that refuses on mismatch is a synthesis, not something a reference implements.

**When to use:** Text entry into inputs and content-editable editors in a browser the tool can reach at page level.

**When not to use:** When the editor's internal model can diverge from the page, the node text is evidence of rendering only. Not a route to focus independence: Footwork's own probe found the driver's typing selects the bound tab for about 100 ms unless inserting into an empty field.

**Tradeoffs:** No focus or foreground needed. The reference only reports a mismatch; a verifying tool must refuse on it.

**Transfer:** application: On the chosen browser lane, keep raw multiline values for verification instead of the clipped and whitespace-collapsed values used today, and name the equivalence on the receipt. Gated on the sign-in, node-text and tab-selection checks. Not implemented.; compatibility_checks: start --browser clips values to 200 characters and asks for foreground to replace held text; browser cdp disables typing for the focus race and collapses whitespace in snapshots. Paragraph blocks may double line feeds in inner text.; next_test: In a Footwork-launched signed-in profile, compare node inner text, the application's copy and the accessibility value against the verified 461-character, 24-line-feed lyrics; repeat the page-visibility probe for replacement on the pinned driver.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** A neighbouring tool clears a field by assigning an empty value, which does not clear a content-editable node, and never reads back.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council round 1.

**Tags:** contenteditable; rich text; lyrics; suno; cdp; insert text; web editor; browser

Evidence:

- `ev-e77fea9a4bd8919233daf679`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/repl/worker.py` lines 763–896; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `79172a7c6907d3a7efbda61eef64c0aff7b1c369c1d237ecec980663cb01af28`.
- `ev-91e7f6c7d9626b98d2086eb6`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/ax.py` lines 767–868; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `94dae4a9f7bc8f5bae02e377e14df46c343277ff0313c13837873dc1b98188df`.
- `ev-40755ae03e014e2ce185eb62`: `/Volumes/External SSD/referencerepos/agent-browser/cli/src/native/interaction.rs` lines 155–220; fresh; HEAD `2f1649cefb82f417abbb2712f5397439d010698e`; SHA-256 `001a3fd213ee1001c6d2d6ac717f40a37b648b0fec88c78413b2ccda18ff564a`.
- `ev-5f90cdfa630a54f70ed7148e`: `/Volumes/External SSD/referencerepos/browser-use/tests/ci/test_ultrafast.py` lines 239–249; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `78f44ddced7b4ccfa8916cb4e089c41fd18499ed51802cd0319123bdba64b889`.
- `ev-13224c8135b7b9f3ff62f4cd`: `/Volumes/External SSD/referencerepos/browser-use/tests/ci/test_ultrafast.py` lines 352–373; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `78f44ddced7b4ccfa8916cb4e089c41fd18499ed51802cd0319123bdba64b889`.

## Enter text at page level and read the value back from the target node

ID: `page-typing-reads-back-target-node-v3`

**Problem:** Driving a rich web editor through the desktop accessibility tree loses text, selection and blank lines, and typing through keys needs window focus the person is using.

**Mechanism:** After entering text at page level, read inner text (content-editable) or value (inputs) from the same node and compare with what was sent under a declared equivalence. The reference reads back and only reports a mismatch; it checks focus from an isolated world only for secret entry. Combining an isolated-world focus check with a readback that refuses on mismatch is a synthesis, not something a reference implements.

**When to use:** Text entry into inputs and content-editable editors in a browser the tool can reach at page level.

**When not to use:** When the editor's internal model can diverge from the page, the node text is evidence of rendering only. Not a route to focus independence: Footwork's own probe found the driver's typing selects the bound tab for about 100 ms unless inserting into an empty field.

**Tradeoffs:** Reads the text the page actually holds, with line structure, where the accessibility value can be lossy. It does not remove the need for focus: replacing held text is a foreground step on the current lane until a probe shows otherwise. The reference only reports a mismatch; a verifying tool must refuse on it.

**Transfer:** application: On the chosen browser lane, keep raw multiline values for verification instead of the clipped and whitespace-collapsed values used today, and name the equivalence on the receipt. Gated on the sign-in, node-text and tab-selection checks. Not implemented.; compatibility_checks: start --browser clips values to 200 characters and asks for foreground to replace held text; browser cdp disables typing for the focus race and collapses whitespace in snapshots. Paragraph blocks may double line feeds in inner text.; next_test: In a Footwork-launched signed-in profile, compare node inner text, the application's copy and the accessibility value against the verified 461-character, 24-line-feed lyrics; repeat the page-visibility probe for replacement on the pinned driver.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** A neighbouring tool clears a field by assigning an empty value, which does not clear a content-editable node, and never reads back.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised. Revised after council rounds 1 and 2.

**Tags:** contenteditable; rich text; lyrics; suno; cdp; insert text; web editor; browser

Evidence:

- `ev-e77fea9a4bd8919233daf679`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/repl/worker.py` lines 763–896; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `79172a7c6907d3a7efbda61eef64c0aff7b1c369c1d237ecec980663cb01af28`.
- `ev-91e7f6c7d9626b98d2086eb6`: `/Volumes/External SSD/referencerepos/browser-use/browser_use/ax.py` lines 767–868; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `94dae4a9f7bc8f5bae02e377e14df46c343277ff0313c13837873dc1b98188df`.
- `ev-40755ae03e014e2ce185eb62`: `/Volumes/External SSD/referencerepos/agent-browser/cli/src/native/interaction.rs` lines 155–220; fresh; HEAD `2f1649cefb82f417abbb2712f5397439d010698e`; SHA-256 `001a3fd213ee1001c6d2d6ac717f40a37b648b0fec88c78413b2ccda18ff564a`.
- `ev-5f90cdfa630a54f70ed7148e`: `/Volumes/External SSD/referencerepos/browser-use/tests/ci/test_ultrafast.py` lines 239–249; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `78f44ddced7b4ccfa8916cb4e089c41fd18499ed51802cd0319123bdba64b889`.
- `ev-13224c8135b7b9f3ff62f4cd`: `/Volumes/External SSD/referencerepos/browser-use/tests/ci/test_ultrafast.py` lines 352–373; fresh; HEAD `7fdd63c03fd342aab4fe44507c77c3221ffd43c6`; SHA-256 `78f44ddced7b4ccfa8916cb4e089c41fd18499ed51802cd0319123bdba64b889`.

## Bind a coordinate action to one capture and consume the capture on use

ID: `pixel-action-bound-to-single-use-capture-v1`

**Problem:** Canvas, WebGL and custom-drawn surfaces have no element tree, so the only address is a point; a bare coordinate can be replayed against a different screen.

**Mechanism:** A coordinate action must name the capture it was chosen from. The driver checks the capture against target, session, expiry and native frame size, maps the point, acts, and deletes the capture. Optionally two crops taken shortly before dispatch are compared with the crop at read time and a difference refuses.

**When to use:** Only where no accessibility or page reference exists for the target.

**When not to use:** When a tree reference exists. Never treat a relocated template match as permission to act at the new point, and never treat identical pixels as identical state.

**Tradeoffs:** Gives every surface an address at the cost of weaker identity; the effect still needs evidence from another channel (file, network, page state) or must be labelled model-observed.

**Transfer:** application: Add a coordinate rung to the ladder for tree-less surfaces such as the Suno Studio waveform and fade control, admitted only with a capture identity and an independent effect check. Not implemented; Footwork callers cannot click at coordinates today.; compatibility_checks: The reference perception detector is AGPL and must not be vendored; the capture-binding contract is MIT. Screenshots are withheld under scope guards and after secrets, which removes this rung in those sessions.; next_test: Fixture page that scrolls on a timer without resizing: capture, wait, act with the capture identity; admission is the predicted weakness. Grid fixture shifted one row: the guard is predicted to pass wrongly.; target: Footwork 0aa1373 (branch codex/suno-end-to-end-20261110); source inspected, runtime not exercised

**Counterexample:** Admission compares identity and dimensions, not pixels: a surface that scrolls itself at the same size within the time limit is still admitted. A uniform grid shifted by one cell yields an identical crop and passes the pixel guard on the wrong item.

**Validation:** level: source; result: Reference source and test definitions read; no reference test run; Footwork runtime not exercised.

**Tags:** canvas; coordinates; pixel; vision; screenshot; studio; webgl; tree-less surface

Evidence:

- `ev-02424167da74b931c503a160`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/docs/perception-extension.md` lines 1–14; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `3cbb58f07e19988014de709e9015c9860cf36c4e85780e2fbf25666b0dade823`.
- `ev-8ae1afc05e2f9656eed6888c`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/docs/perception-extension.md` lines 140–195; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `3cbb58f07e19988014de709e9015c9860cf36c4e85780e2fbf25666b0dade823`.
- `ev-c7f8b491e3cd8670c816ac29`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/capture_registry.rs` lines 736–800; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `eae6f53a0ecd01c89326f59919de9b5b3c12f3aa75258c089c9b7aa5dad8431b`.
- `ev-3c7f274482946faf3bad279f`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/capture_registry.rs` lines 1411–1470; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `eae6f53a0ecd01c89326f59919de9b5b3c12f3aa75258c089c9b7aa5dad8431b`.
- `ev-47d5b765a8fb298775f9d7c6`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/fast_path/pixel_guard.rs` lines 74–172; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `9a11dd3d2edd2975adcc23d786290f65583e582aeec5c7da3aaa6da0d6d205bb`.
- `ev-5164f72bf49f1121f3b02766`: `/Volumes/External SSD/referencerepos/cua/libs/cua-driver/rust/crates/cua-driver-core/src/fast_path/pixel_guard.rs` lines 220–260; fresh; HEAD `ca31ba8ca2c6c54c596f1bb151d6e5e2ed16545d`; SHA-256 `9a11dd3d2edd2975adcc23d786290f65583e582aeec5c7da3aaa6da0d6d205bb`.
