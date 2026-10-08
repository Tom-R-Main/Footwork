# D2: visual information ablation

The registered visual rule holds: Decisions with images is confidently correct on all 12 synthetic fixtures in all three replays, versus zero confidently resolved fixtures from identical sparse text. This supports collecting independent real visual failure cases and validating a dedicated visual judgment role. It does not justify production adoption or full model agnosticism.

Measured commit: 84f3fd5. All 144 scheduled calls completed, no halt; 138 valid answers, six native text-only refusals. Fixtures were rendered, manually inspected and committed before requests. Evidence: started.json, fixtures.json, results.json, summary.json, budget.json and analysis.json in this directory; evals/visual/d2/ holds the committed PNGs and manifest.

| Arm | Confidently correct fixtures in all three replays | Unknown replays | Refusals | Confident true on negative, any replay | Median / p95 ms |
|---|---:|---:|---:|---:|---:|
| Jev sparse text | 0/12 | 36/36 | 0 | 0/6 | 133.42 / 215.43 |
| Decisions sparse text | 0/12 | 30/36 | 6 | 0/6 | 155.91 / 632.33 |
| Decisions image | 12/12 | 0/36 | 0 | 0/6 | 178.83 / 354.28 |
| Decisions text + image | 12/12 | 0/36 | 0 | 0/6 | 170.56 / 747.53 |

Six fixture pairs cover checkbox, radio, status color with visible legend, modal occlusion, chart bar height and padlock state. Sparse text is identical within each opposing pair and intentionally omits the discriminating visual feature. Unknown or refusal is an appropriate result from insufficient information; zero confidently correct text fixtures is not a text-model accuracy ranking. The six Decisions text refusals are the two checkbox fixtures, all three replays. Native refusal cause is unspecified.

Predicate bands were frozen at true >=0.80, false <=0.20, otherwise unknown. The combined image gain is +12 all-three cases, with no confident false positives. No oracle labels, case filenames or ground-truth metadata were sent: image arms receive inline base64 pixels and the predicate; combined also receives sparse text. Expected labels stay in the local renderer/manifest and reporting.

## Speed, quality and adoption limits

These are simple authored 480x300 screens, not independent real app captures. The same fixture authors chose the tasks and labels; a ceiling is possible. Three repeated requests per screen are not 36 independent screens. Models are reported as Jev-1.13.0 and gpt-6-luna; the OpenAI alias does not establish an immutable snapshot. No score calibration, source extraction, object localization, action dispatch or live task completion is established.

Reported times are pooled implementation wall latency, with cold requests and refusals retained, statistical medians and nearest-rank p95. Image+text's median is about 15 ms above Decisions text and 37 ms above Jev text, but its 748 ms tail exceeds either text arm in this run. Thirty-six attempts per arm from one site cannot establish stable tails or live-session latency; snapshot capture, encoding, routing and dispatch are not measured. Image-only's lower p95 here does not establish it as a faster general configuration.

Quality gain is added information rather than evidence-matched provider superiority. It qualifies the dedicated visual role for independent validation under the preregistration, with continued attention to speed and false positives. It cannot repair D1's unsafe completion substitutions. Screenshots cannot grant consent, establish source fidelity or prove that state is still current.

## Proposed placement

Keep Jev's existing text completion, risk and bounded-selection routes. Add a separately validated Decisions path for a bounded visual predicate only when required state is absent from the text observation: selection/check state, visual status, occlusion or chart/icon properties are candidate roles. Bind any screenshot to the same surface, observation revision and exact offered question. Preserve native probability, model, usage, latency and refusal; unknown/refusal/conflict escalates rather than becoming positive evidence. Footwork code owns permissions, scope, target identity, grounding, effect receipts and dispatch. System Two still handles open-ended reasoning and generated arguments.

Do not implement a broad neutralization now. A small semantic seam with typed predicates/choices, provider capability declarations and validated consumed dependencies would accommodate this useful specialized backend. Admission settings remain specific to role/model/prompt; they are not made interchangeable by identical field names. Next adoption evidence should use independently collected visual failures with adequate text as a control, blinded labels and actual capture-to-judgment latency. No live runtime defaults changed in this package.

## Accounting

D2 reported-input list-price estimate is $0.003561288. The complete pilot's reported-input estimate is $0.051255158; conservative reported-or-reserved upper is $0.192055158, including two earlier unknown-usage rejected calls. No D2 usage is unknown. These are estimates rather than invoice charges; all remain under the original $5 ceiling. Existing keys were reused, with no new credentials or dependency changes.
