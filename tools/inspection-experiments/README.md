# Paired browser inspection experiments

This offline tool compares **two sealed captures of the same named workflow steps**. It never attaches to a browser or calls a site. Prepare control and variant runs with the sibling `browser-inspection` recorder, hold the fixture and environment as steady as possible, and change one variable at a time. A useful pair is a document with a planted claim and the same document with that claim corrected.

```sh
node tools/inspection-experiments/compare.mjs \
  output/browser-inspection/<control-run> \
  output/browser-inspection/<variant-run> \
  > output/browser-inspection/paired-comparison.json
```

The comparator verifies each run's manifest hashes before reading its four journals. It pairs `workflowId` and `stepId`, reports hashed method-and-endpoint identities with hop/status/count and request-shape changes, and compares response-body shape fingerprints at run level. Query values and body values never enter the report. The raw local run remains the place to resolve a fingerprint to a specific endpoint when needed. Output is derivative and stays outside the sealed run; do not commit live captures or reports.

The report deliberately uses `paired-intervals` rather than causal language. Background requests can occur within a step. Redirects can reuse a request ID. Response bodies lack reliable step identity, so their shapes are compared only across the whole run. A missing step is `incomparable-missing-step`; any capture gap marks the pair `limited`. The comparator cannot prove a successful write, persistence after reload, answer correctness, or backend implementation. It can make the next controlled experiment more precise.

Offline verification: `node --test tools/inspection-experiments/compare.test.mjs`.

Future Footwork integration can add operator checkpoints and post-reload readback to the sealed packet, then use deterministic evidence rules to promote `intended → request observed → response observed → visible state observed → persistence observed`. An AI analyst may propose explanations from those facts, while the packet and rules retain authority over what was actually observed.
