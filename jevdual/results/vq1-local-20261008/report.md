# VQ1 local qualification machinery

Observed: the corpus validator, frozen replay collector, grouped scorer and workflow timing recorder are built and checked locally on 4037830. Full offline suite: **1,143 passed, 26 skipped**, 85.54 seconds; 112 new qualification checks are included. Ruff and notebook checks pass. [Verification record](verification.json) binds source hashes, dependency versions, protocol, corpus and schedule.

## Actual local entry points

The CLI seed and preflight commands create/load authored inputs. Freeze records a randomized matched schedule and immutable source/prompt/evidence/model identities. The smoke command completes 96 slots over 24 cases, two arms and two replays: 48 production Decisions image requests through MockTransport and 48 fixed text callbacks. A separate score command reproduces the same summary in [recount/summary.json](recount/summary.json). All answers are fixed .5 and all costs simulated; the text callback does not exercise the Jev SDK. Ordinary HTTP transport is forbidden by a regression. No provider access, keys or live app capture is involved.

Every family/arm remains unqualified. The corpus is authored development material, the independent negative/positive/ambiguity counts are insufficient, useful positive support is absent with .5 answers, and workflow timing is unavailable. This is the intended result; complete means all slots are accounted for, not quality success. The proof also drives fresh-output refusal and changed-asset refusal through the actual CLI; the original committed corpus stays unchanged.

## Review and corrections

Independent inherited-model scrutiny found matched-speed dilution, impossible imported phase totals, incomplete production source pins and optimistic handling of a higher unknown-usage bound. Root reproductions fail before repair and pass after. Additional regressions expose small-sample coverage qualification and contradictory start/close metadata. Repairs use exact matched-success p95s, phase-to-wall validation, complete dependency/source pin sets, conservative uncertain-cost bounds, lower confidence bounds for positive/ambiguity coverage, and corresponding start/close metadata. The adequate text control also receives the explicit crop and target geometry.

The independent recheck passes 109 focused tests with no remaining blocking finding in those fixes. The final metadata hardening follows that review and passes its three failing-before-repair cases plus partial-cancellation regression; the final full suite covers it. Separate contexts used the same inherited model; this is independent scrutiny, not model diversity.

## Qualification and next scope

Quality counts related variants/replays as one source group per label stratum. It reports negative endorsement upper bounds, positive/ambiguity lower coverage bounds, conservative versus epistemic ambiguity, false rejection and descriptive calibration. Workflow speed requires actual complete paired measurements, preserved baseline-success cases and no additional mean intervention burden. Not-run slots are coverage gaps, not zero-duration measured attempts. Source independence, sampling representativeness, annotations, provider access and outcome readback still require external evidence; declarations alone cannot establish them.

The example .90/.10 interpretation and .01/.80/.95 quality targets are proposed experiment settings, not runtime admission thresholds. At .95 marginal confidence and no misses, the strata need at least 300 negative, 14 positive and 59 ambiguous independent groups per role. These can be overlapping group identities across label strata when related variants are correctly grouped; summing them does not prove 373 independent unique sources. Prefer disjoint strata for a clear initial collection and inspect representativeness. No actual independent visual accuracy, real-provider calibration or verified-workflow speed is established.

Next: collect and independently adjudicate one authorized real document/reference corpus, include every exposed development reference (converting legacy corpora to the supported manifest format), then inspect/freeze the concrete protocol and bounded spend before separately authorized provider-backed measurement. Only after quality passes should an app-specific measured workflow trial add operator review and independent document identity readback. Browser capture, crop execution, autonomous routing and general model agnosticism remain separate decisions.

Guide: [visual-qualification.md](../../docs/visual-qualification.md). No paid calls, key creation, installs, action authority, settings/factory changes, push, PR or deployment occurred. Unrelated architecture planning files were preserved.
