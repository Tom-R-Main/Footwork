# Product recommendation after the Decisions/Jev experiments

**Improve Footwork as a verified execution product. Keep Jev as the active text guard and mechanical policy. Add scoped visual inspection as an experimental capability, starting with document/image preparation. Defer a broad model-agnostic rewrite and automatic visual action approval.**

This recommendation incorporates D1–D4 and the implemented private native inspection capability. Six of twenty proposed visual task families were implemented; fourteen remain proposed. These are authored development fixtures and controlled native/browser observations, not independent real-app adoption evidence. Runtime routing and settings remain unchanged.

The next package is specified in the [reviewed visual System One plan](visual-system-one-plan.md). It remediates invocation and escalation gaps in the initial proposal: explicit role requests, separate reference/crop provenance, temporal validity distinct from immutable binding, disclosure before upload, structured System Two handoff and bounded recovery. Native advisory checks come first; browser capture and reviewed execution require separate qualification. This is a plan revision, not newly implemented functionality.

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
| D4: marked/region views approve 0/4 invalid cases and retain 4/4 supported; original control produces one wrong effect, but D3 B02 does not reproduce | Target grounding merits independent testing; causal repair attribution remains inconclusive |

Sources: [D1](../results/d1-v2-dev-20261008/report.md), [D2](../results/d2-dev-20261008/report.md), [D3](../results/d3-dev-20261008/report.md), [D4](../results/d4-dev-20261008/report.md). Timing estimates, repetitions, refusals and corpus limits are detailed there. The product position is consistent with Footwork's existing README: the guard is the core product, while System One acting is optional.

## Priority 1: make the proposed target unmistakable

**Implemented locally:** `footwork inspect-target` records a fresh native observation, immutable source/target/operation/postcondition binding, original PNG and static HTML review with an exact target outline. Actual CLI/Cua SDK verification on a task-owned AppKit window confirms correct pixel mapping and no action. Secret sessions withhold capture; invalid/mismatched observations refuse. Numeric target inspection preserves the incomplete AX warning; label resolution refuses without uniqueness proof. Browser operator inspection explicitly refuses until screenshot geometry is qualified. See [qualification](../results/visual-inspection-20261008/report.md) and [saved preview](../results/visual-inspection-20261008/preview/45acf06c2fa1465a98d270f84cfe2a49.html).

D4 completed the registered full-frame/marked/region comparison. Marked and region arms retained all supported cases without invalid approvals; region evidence also expressed uncertainty on every ambiguous replay. The exact D3 B02 failure did not reproduce, so repair attribution is inconclusive. Capture-to-judgment median estimates were 237 / 302 / 297 ms; region request p95 was 715 ms. Keep the visual role unactivated and collect independent cases before reviewed execution. Binding equality itself does not query the live screen or grant authority.

The implemented envelope records surface/window/tab identity, observation token, timestamp, image hash, dimensions/scale, exact offered target ID and bounds, intended operation, and required postcondition. The preview shows which element the proposal concerns and the required result. Future reviewed execution must invalidate a changed view and require a fresh observation instead of carrying approval forward.

Further evaluation should combine the exact target region with relevant context, including neighboring glyphs and changed-after-capture cases. D4 does not establish the cause or repair of B02. Preserve ordinary accessible text; visual input should add missing information rather than benefit from removed useful labels.

Existing scope, token and live target checks stay in place. They passed B02 and still allowed the wrong semantic effect, so stronger freshness alone cannot repair icon interpretation. Keep unqualified visual judgments advisory. Permission to act and independently confirmed completion remain separate from the visual model's probability.

Implemented seam: NativeMenu/native.py supplies correlated native capture metadata to visual_evidence.py; session.py records the binding and static preview. Browser capture and carrying the binding through reviewed dispatch/receipt remain future work; no driver replacement was needed for private native inspection.

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

1. **Completed locally:** preserve B02 and add target-bound evidence in private native inspection. No new default authority; browser inspection remains unsupported.
2. **D4 comparison completed; repair attribution inconclusive.** Next collect an independent real document/crop corpus with blinded labels and harder target-grounding cases. Include near misses, missing evidence, duplicate-looking sources, layout changes and actual saved-artifact checks. Keep existing sealed adoption data untouched.
3. Add reviewed execution for a qualified family, with the exact reviewed revision and outcome readback. Validate actual Finder/Preview or the chosen app separately from the AppKit fixtures.
4. Consider autonomous use only for a narrowly scoped family after it improves useful verified coverage without wrong accepted effects and meets the workflow's preregistered end-to-end latency criterion. Calibrate on development data and validate independently; zero errors in a small corpus is not a universal guarantee.
5. Broaden backend interchangeability only when another role earns it on both quality and speed. Expand the remaining task families where they resolve a real product decision, rather than build all fourteen before testing a useful workflow.

Beyond the implemented read-only inspection and completed D4 study, the release gates and workflow remain recommendations rather than completed functionality or authority to activate them. The completed experiments support an additional visual observation capability and a better evidence/target contract; they do not support turning Footwork into a universally interchangeable model-driven executor.
