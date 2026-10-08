# Product recommendation after the Decisions/Jev experiments

**Improve Footwork as a verified execution product. Keep Jev as the active text guard and mechanical policy. Add scoped visual inspection as an experimental capability, starting with document/image preparation. Defer a broad model-agnostic rewrite and automatic visual action approval.**

This recommendation closes the completed D1–D3 development package. Six of twenty proposed visual task families were implemented; fourteen remain proposed. These are authored development fixtures and controlled native/browser observations, not independent real-app adoption evidence. Runtime routing and settings remain unchanged.

## What the evidence earns

| Evidence | Product consequence |
|---|---|
| D1: Decisions finally accepted 5/18 unsupported completion cases, Jev 0/18 | Keep the existing text completion backend; a new native probability API is not a drop-in trust improvement |
| D1: nine unused target-head refusals recover useful decisions offline | Preserve refusal per answer and validate all dependencies actually consumed; do not lose a useful decision because an unrelated speculative target refused |
| D2: pixels resolve twelve simple states missing from sparse text | Visual inspection is technically useful; sparse-text uncertainty is appropriate, not inferior reasoning |
| D3: combined 19/24 registered cases, Jev 14/24; document and crop families each 4/4 combined | Prioritize source identity and crop/subject inspection for further independent testing |
| D3: Rotate approved as Crop at p=.99 in all three replays; a real wrong fixture effect follows | Bind every visual question to the exact offered target and test that binding; confidence alone cannot approve an action |
| D3: freshness 4/4 Jev, 2/4 combined; visible100% still requires artifact readback | Keep freshness and completion authority in code; images do not replace resource/effect evidence |
| D3: request medians 148ms Jev,163ms combined; native capture-to-judgment estimates around550ms | Optimize the whole observation path and call visual inspection selectively; model latency alone does not determine task speed |

Sources: [D1](../results/d1-v2-dev-20261008/report.md), [D2](../results/d2-dev-20261008/report.md), [D3](../results/d3-dev-20261008/report.md). Timing estimates, repetitions, refusals and corpus limits are detailed there. The product position is consistent with Footwork's existing README: the guard is the core product, while System One acting is optional.

## Priority 1: make the proposed target unmistakable

Introduce an observation-bound visual evidence envelope: surface/window/tab identity, observation token, timestamp, image hash, dimensions/scale, exact offered target ID and bounds, intended operation, and required postcondition. The UI should show which element or source the proposal concerns and the expected result. A changed view invalidates the proposal and prompts a fresh observation rather than carrying approval forward.

Evaluate the exact target region alongside the relevant context. Treat this as a hypothesis for repairing the B02 failure, not a proven fix: the experiment establishes wrong offered-target interpretation but not its cause. Compare full-frame, explicitly marked target and target-region evidence under a new preregistration, including similar neighboring glyphs and changed-after-capture cases. Preserve ordinary accessible text; do not make visual input appear valuable by removing useful labels.

Existing scope, token and live target checks stay in place. They passed B02 and still allowed the wrong semantic effect, so stronger freshness alone cannot repair icon interpretation. Keep unqualified visual judgments advisory. Permission to act and independently confirmed completion remain separate from the visual model's probability.

Implementation seam: NativeMenu/native.py and browser observation metadata feed a small visual check boundary; operator session/desktop proposals carry the binding through dispatch and receipt. No need to replace the driver to add this envelope.

## Priority 2: offer a bounded visual inspection capability

Start with one workflow: **prepare a document or image for review and save it to an explicitly scoped destination**. Footwork identifies a source from previews, proposes a crop or selection, shows the source and proposed result, and verifies the saved artifact after authorized execution. The initial private trial exposes suggestions for review; it does not silently grant autonomous visual control.

The operator should see the source preview, proposed region/change and the observed saved result. Unavailable or conflicting evidence should produce a concrete request for a better observation or escalation. A probability of .99 is a diagnostic value, not an assurance to the operator. Preserve source identity before edits; after an edit verify the intended output's location, decodability, dimensions/content and the approved change. A screenshot alone cannot prove persistence or preservation of the subject.

First candidate checks: document/reference visual match and crop/subject containment. Map containment is a secondary candidate requiring harder boundary cases. Keep generic icon approval, free-form pixel clicking, broad completion replacement and model-judged freshness outside initial activation. System Two retains open-ended interpretation and argument generation; Jev retains existing text completion/risk/bounded-choice roles; code retains consent, scope, target identity, freshness and effect verification.

## Priority 3: introduce only the semantic seam the workflow needs

Use typed predicate/choice requests and answers with explicit modality capabilities, native probability/distribution, separate native confidence, per-answer refusal/error, deterministic singleton provenance, model/prompt/evidence identity, usage and latency. Validate the complete response envelope and every consumed dependency. Refusal or missing data on a required check prevents its use; a missing visual answer must never inherit an earlier text positive.

Keep provider adapters behind qualified roles. Jev remains the text default; the visual role remains disabled until its independent validation gate passes. Admission settings belong to the model, role and prompt version. Do not present a general model picker as the product or pretend identical output fields mean identical calibration.

arc-cua demonstrates a feasible shared ChoicePolicy/transport boundary and required-head refusal handling. Borrow those small patterns while retaining Footwork's strict parsing, forced-answer provenance and completion floors. Its snapshot revision excludes pixels, its native OCR freshness is weaker than a visual precondition check, and its missing image-check merge can retain an old text answer. Its source-reported driver benchmarks are not an adoption reason. See [reference audit](arc-cua-decisions-reference.md).

## Optimize useful work rather than screenshot volume

Read AX/DOM first and use local OCR when it supplies needed text. Invoke image inspection only for a question that still lacks adequate evidence. Reuse a retained capture within one observation; invalidate it after action/reobservation and apply an explicit visual freshness policy where pixel-only state matters. Accessibility revisions alone cannot prove that pixels stayed unchanged. Keep warm sessions and encode lazily when they help, but measure their effect rather than assume savings.

Report verified completion time, dangerous or wrong effects, useful coverage, escalation burden and cost per verified outcome. Break latency into capture, AX/DOM/OCR, encoding, provider, validation, dispatch, settle and independent readback. Retain failures and cold starts. Do not trade missed delayed UI changes for a faster return time or count fewer model calls as a customer benefit without better verified outcomes.

## Release sequence and acceptance

1. Preserve the B02 counterexample and add target-bound visual evidence in a private inspection mode. No new default authority.
2. Run a registered target-grounding comparison and an independently collected real document/crop corpus with blinded labels. Include near misses, missing evidence, duplicate-looking sources, layout changes and actual saved-artifact checks. Keep existing sealed adoption data untouched.
3. Add reviewed execution for a qualified family, with the exact reviewed revision and outcome readback. Validate actual Finder/Preview or the chosen app separately from the AppKit fixtures.
4. Consider autonomous use only for a narrowly scoped family after it improves useful verified coverage without wrong accepted effects and meets the workflow's preregistered end-to-end latency criterion. Calibrate on development data and validate independently; zero errors in a small corpus is not a universal guarantee.
5. Broaden backend interchangeability only when another role earns it on both quality and speed. Expand the remaining task families where they resolve a real product decision, rather than build all fourteen before testing a useful workflow.

The release gates and workflow are recommendations, not newly measured results or an approval to activate them. The completed experiments support an additional visual observation capability and a better evidence/target contract; they do not support turning Footwork into a universally interchangeable model-driven executor.
