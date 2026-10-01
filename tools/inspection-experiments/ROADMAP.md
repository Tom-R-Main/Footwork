# Footwork inspection lab

The useful Footwork feature is an **experiment lab**, not a network logger with an AI summary. A logger records that a request happened. The lab asks a falsifiable question, changes one input, joins UI and network evidence, and shows which competing explanations remain possible. Symbolic is the first subject; the design should work with any explicitly scoped account and origin.

## Evidence layers

1. **Capture packet.** The existing `browser-inspection` recorder observes the selected tab, records action marks, event journals, capture gaps and optional private UI artifacts, then seals their hashes. Keep it separate from Footwork's browser launcher. The browser operator still owns navigation and account mutations. A sealed hash detects local changes after capture; it does not authenticate Chrome, the website, or the recorder.
2. **Normalized observation graph.** Reconstruct network request *hops*, responses, stream frames, visible route changes and snapshots with stable identities. Preserve source target/session, event cursor, wall time and monotonic time separately. A request ID can be reused across redirects and targets. Unknown or evicted evidence becomes an explicit gap node. Never infer that a request caused a visible effect solely because it occurred during an action.
3. **Trial manifest.** Before a workflow run, specify the fixture, starting account state, named step sequence, one treatment variable, competing hypotheses and predictions. A fixture fingerprint should identify the input without copying its contents into a shareable report. Name account-created artifacts so cleanup and readback can target exact objects.
4. **Paired comparison.** The implemented `compare.mjs` is the first slice: verify both packets, pair named step intervals, compare opaque endpoint and shape fingerprints, and preserve coverage limits. Next, add baseline background captures and repeated trials. An endpoint seen only in a treatment run is a candidate signal until it survives background subtraction and repeat observation.
5. **Effect adjudication.** Add a separate, append-only assessment overlay referencing sealed packet hashes. The minimum typed ladder is `intended → request observed → response observed → visible state observed → persistence observed → correctness adjudicated`. Each promotion needs its own evidence reference. A 200 response cannot promote persistence; a rendered success toast cannot promote correctness. Operator or model assessments remain claims until deterministic rules verify their referenced artifacts.
6. **Hypothesis ledger.** For each claimed behavior, retain the prediction, discriminating intervention, observations for and against, capture coverage, alternative explanations and next experiment. The ledger can produce a workflow map and API catalog with “observed,” “inferred,” and “unknown” claims. Do not collapse these into a single confidence score.

## First controlled trials

Use the Symbolic runbook and prepared fixtures from the Best-Edit research folder. Record an idle baseline, then repeat one workflow with only one changed input. Good early pairs are: a planted incorrect claim versus a corrected one; the same draft with an explicit rewrite instruction versus a neutral one; the same audio with and without a deliberately spoken distinctive phrase. For each trial, inspect the UI result, the request/stream sequence and a fresh reopen/readback of the created object. A second repeat helps distinguish stable workflow requests from background activity.

For each workflow, produce a route-and-state diagram: entry point, form requirements, upload/processing states, generation states, errors, saving, reopening, sharing/exporting and deletion when exercised. Mark navigation or account state that could influence the result. Record any browser visibility gaps separately, including requests that occur before attachment, worker traffic and body eviction. CDN bundle hashes and frontend route/chunk inventories can support implementation hypotheses, but a minified component name is not proof of a backend architecture.

## Build gates

- **Now:** keep the capture tool and offline comparator as independent, dependency-free Footwork utilities. Verify with synthetic fixtures and explicit integrity tests. Keep live account packets in ignored private output.
- **After a real calibrated run:** compare the normalized journal against Chrome DevTools and the in-page recorder on the same benign action. Measure missed requests, lost stream frames, origin changes, event duplication and body availability before treating the packet as complete.
- **After two controlled pairs:** add the trial manifest and background subtraction. Require matching step IDs and fixture fingerprints; label environmental drift rather than silently joining incomparable runs.
- **After one reopen/readback workflow:** add the effect overlay and deterministic promotion rules. Test negative cases: response without UI change, UI change without persistence, and a capture gap covering the write.
- **After repeated multi-workflow use:** integrate the lab with Jevdual only through host-owned evidence references and typed effects. Keep model explanations advisory; deterministic code owns effect identity, authorization, verification and replay protection.

## Collection boundary

Default reports contain no request or response values, cookies, headers, storage or private DOM. Keep raw private captures out of Git and avoid sending them to a model by default. The comparator emits endpoint and structure hashes so two runs can be compared without publishing path values. A person reviewing the private packet can resolve a hash locally when an explanation requires it. Browser control and recorder instrumentation should remain visibly scoped to the declared origin and account session; optional deeper capture should be justified by a measured blind spot.
