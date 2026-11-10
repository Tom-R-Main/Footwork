# Guarded foreground web text

## FWT1 · prediction · 2026-11-10 17:22
Question: can the pinned native driver fail closed on foreground field-focus failure and support an explicit Footwork web-text route without retrying an uncertain background write?
Hypothesis: gating text synthesis with the existing confirmed-key-focus helper inside foreground activation, then exposing only an explicit qualified native web-field route, preserves exact-window/field checks while providing renderer-visible foreground input.
Test: first reproduce missing foreground text focus refusal in the pinned Rust unit boundary and missing explicit option through public CLI simulated-Mac scenarios. Patch source, preserve cleanup fixes and ABI bindings, identify a new exact custom pin/archive, run offline release Rust regressions and Python scenarios/contracts, build the patched CLI/SDK using the existing owned target cache, and qualify a project-local wheel overlay. Root alone drives live Suno.
Predicts: failed or unverified target focus emits no text; explicit background_only and unsupported requests refuse without mutation; a qualified foreground request uses token/window scoped foreground delivery with structured metadata; field/roster changes after activation or selection stop before insertion; uncertain delivery is never retried. Default background behavior remains unchanged.
Against: text is synthesized after failed focus, the opt-in silently falls back after uncertainty, unsupported input binds a driver, a stale selection receives text, cleanup/ABI contracts change unintentionally, or the new source pin can run against old native bytes unnoticed.
Refs: vendor/cua-driver/native-source.tar.gz; vendor/cua-driver/PROVENANCE.md; output/cua-046-upgrade; docs/notebook/2026-11-10-suno-end-to-end.md

## FWT2 · prediction · 2026-11-10 17:48
Question: does the explicit foreground route still mistake an unreadable value for empty or permit the SDK's batched partial-tail synthesis after incomplete web ancestry?
Hypothesis: requiring the exact target in the fresh values map prevents typing into an unreadable nonempty field, and explicit positive character pacing disables the pinned SDK's batched tail retry without another native patch.
Test: add public CLI simulated-Mac counterexamples for a missing/unreadable nonempty value and a partial foreground reply under incomplete web ancestry; first run them against the current candidate, then require pre-type readable-value membership and positive delay_ms, and re-run the overlay scenarios/contracts.
Predicts: the current candidate sends text without a readable value and omits positive pacing; the repair refuses the unreadable target before selection/text and sends one positively paced request whose partial reply never produces another request. The native focus1 bytes remain unchanged.
Against: unreadable values still reach selection or synthesis, a partial result produces a second request, pacing remains zero/omitted or normal background behavior changes.
Refs: root independent review dated2026-11-10; output/foreground-web-text/runtime.json; tests/test_session_scenarios.py

## FWTU1 · update · 2026-11-10 17:49
Resolves: FWT1 = inconclusive; FWT2 = held
Observed: the synthesis-boundary Rust regressions first failed3 cases, then the guarded source passed33 focused tests including zero-settle foreground admission. Public CLI scenarios first rejected the missing option, then tested idle, replacement selection, identity changes, unknown delivery and zero-text refusal retention. Independent review found unreadable values treated as empty and omitted positive pacing; both public CLI counterexamples failed before repair. The final focus1 overlay passes84 focused CLI, ABI and source-provenance contracts. An earlier affected suite passed407 tests. Ruff, Rustfmt and notebook validation pass. Native CLI/SDK and canonical Hatchling wheel were built offline; all six Python binding files are unchanged and installed native bytes match the wheel and build target.
Changes: add the pinned foreground focus refusal, identify cleanup2.focus1 by archive/hash/pin, and expose an explicit native macOS type-only foreground option. Readable current value and independent full-selection readback are required. Positive delay_ms disables the SDK's batched partial-tail retry. Existing action gates and three-second shared-desktop idle admission remain. Default background and append paths are unchanged; this foreground option rejects append and unsupported routes.
Inferred: the local guard and one-request contracts are established, while renderer-visible Suno delivery remains untested and prevents resolving the overall FWT1 prediction as held.
Next: root runs the full default offline suite against the project overlay, then the separately committed SUN11 live signal and lyrics test. No global release activation or worker UI input occurred.
Refs: results/foreground-web-text-20261110/report.md; results/foreground-web-text-20261110/runtime.json; results/foreground-web-text-20261110/rust-red.txt; results/foreground-web-text-20261110/rust-green.txt; results/foreground-web-text-20261110/review-red.txt; results/foreground-web-text-20261110/overlay-contracts.txt

## FWTS1 · summary · 2026-11-10 17:49
Established: an addressed foreground text target must hold verified OS field focus before synthesis; a missing readable value refuses, replacement requires exact full-selection readback, and explicit positive pacing excludes batched tail retries even when web ancestry is incomplete. The exact project overlay imports and passes ABI/pin contracts. SDK zero-text refusal evidence survives separately from earlier preparation input.
Uncertain: full default regression results and live Suno renderer, server persistence and editing success remain for root. AX focus/value/selection evidence does not independently prove DOM acceptance. Foreground append and other platforms are unsupported. The global installed release is unchanged.
Decision: freeze and hand off this source/runtime candidate for root verification, without claiming the song workflow complete.
Refs: results/foreground-web-text-20261110/report.md; docs/unified-cli.md
