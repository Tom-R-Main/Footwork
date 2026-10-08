# D4: offered-target grounding

**Target marking and region views improved this authored development comparison, but repair of the original D3 failure is inconclusive: the original control did not reproduce it. Keep provider-backed visual action approval disabled.** The separate read-only native inspection capability is implemented and verified.

Measured commit: `5d67e88639f4ce57af9a77a23fd4142115a7f54a`. Preregistration: [D4](../../docs/experiments/D4-target-grounding.md). Frozen captures: [manifest](../d4-capture-20261008/manifest.json). All 108 scheduled Decisions calls completed, with known usage, no provider errors or refusals, and 36 first-replay reconstructed effect checks without coverage errors. The twelve exposed toolbar cases comprise four layouts/styles with supported, near-miss and ambiguous proposals. These are browser fixtures, not independent real-app adoption data.

## Quality and effects

| Metric | Original full frame | Marked full frame | Target region |
|---|---:|---:|---:|
| Invalid proposal cases accepted in any replay (primary) | 1/4 | 0/4 | 0/4 |
| Supported cases correct in all three replays | 3/4 | 4/4 | 4/4 |
| Wrong actual effects in twelve first-replay checks | 1 | 0 | 0 |
| Ambiguous replays answered unknown | 0/12 | 3/12 | 12/12 |
| Ambiguous replays conservatively false | 12/12 | 9/12 | 0/12 |
| Strict correctness in all three replays | 5/12 | 9/12 | 11/12 |
| Strict correct replays | 15/36 | 27/36 | 33/36 |

The unmarked swapped-layout G05 was approved at p=.85 in all three replays and actually activated Rotate when Crop was proposed. Marked evidence rejected it. Region evidence stayed uncertain at p=.22 in all three replays: safe abstention, but not strict negative correctness. All ambiguous inputs withheld execution in every arm; a confident false on an ambiguous support predicate does not establish knowledge of the hidden function.

G02 preserves D3 B02's original PNG, source HTML, target bounds and question. The original full-frame arm now returns p=0 in all three replays, whereas D3 combined returned p=.99 in all three. The observed text differs only in the fresh capture timestamp and browser tab identity. This fails the registered reproduction condition. No causal explanation for that change is established, and no claim that target marking repaired that particular failure is warranted. The other variants supply promising paired development evidence only; the preserved D3 counterexample remains valid evidence against broad visual admission.

## Evidence and timing

All three arms receive the same observed DOM/AX text and question within each case. The marker identifies only the offered target and its bounds. Region images use direct CDP clipping, with source-frame hashes, coordinates and scale retained. Region rasterization can differ from a pixel slice of the full screenshot; capture receipts disclose those differences. No truth labels, fixture variant or oracle enters provider evidence. Reconstructed dispatch uses model probability and source/target guards; expected answers score effects independently and do not gate dispatch.

| Milliseconds, median / p95 | Original | Marked | Region |
|---|---:|---:|---:|
| Provider request | 189 / 386 | 192 / 282 | 185 / 715 |
| Capture-to-judgment estimate | 237 / 427 | 302 / 396 | 297 / 776 |
| Reconstructed execution wall time | 648 / 847 | 665 / 816 | 667 / 1,069 |

Capture-to-judgment adds recorded capture/extraction/encoding/annotation phases to replay request time; it is an estimate, not measured autonomous workflow speed. Marking and region capture add approximately 60–65 ms to the median estimate here. The smaller region payload uses fewer billed tokens but does not provide a universal speed advantage; its request tail is worse. Reconstruction includes setup, capture, validation, conditional dispatch and independent readback. It does not establish native concurrency freshness or real workflow latency.

## Accounting and product decision

D4 reported-input estimate is $0.0118962 (original and marked $0.0042471 each; region $0.003402). Cumulative pilot estimate is $0.087013922, with conservative upper $0.227813922 under the authorized $5 cap. The upper still retains $0.1408 for two earlier rejected requests with unknown usage. These are usage-based estimates, not invoice reconciliation. No credentials were created or exposed.

Resolve DAPI5 as **inconclusive**. Both bound views meet this small comparison's zero-invalid-acceptance and supported-coverage guardrails, but the original failure was not reproduced and all cases were exposed authored fixtures. Advance target grounding to independently collected visual cases, including neighboring glyphs, layout changes and missing evidence; do not activate automatic visual admission or broader model agnosticism.

Ship the verified local [read-only native inspection](../visual-inspection-20261008/report.md): immutable image/surface/target/proposal binding and an exact target review preview, with no provider call or action. Browser operator inspection remains explicitly unsupported pending qualified screenshot geometry. Jev stays active for text; existing factories, thresholds, consent and dispatch guards remain unchanged. Document/image preparation with reviewed execution is the next recommended product package, not completed functionality.

Raw evidence: results.json, summary.json, budget.json, started.json, frozen-inputs.json, closed.json and execution/ receipts. Reproduce the offline recount with `python analyze.py`; [analysis.json](analysis.json) retains its counts and costs. Full source validation before paid calls passed 919 tests with 26 skipped, plus Ruff and notebook checks. An independent recount confirmed the reported quality, effects, reproduction limit and accounting.
