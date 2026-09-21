# R7: the Python/Rust boundary decision for the DOM pipeline

## What is measured (observed)

Replayed DOM CPU per step, median, gc.collect() before each run, `scripts/bench_dom_pipeline.py`:

| fixture | unpatched | R5 patches (paint order + orjson) | + lazy uuid (this commit) | 50 ms gate |
|---|---|---|---|---|
| wikipedia-python (18k nodes) | 146–164 | 136 | 118 | not met |
| amazon-usb-c-hub (10k nodes) | 86–90 | 74 | 64 | not met |

Run-to-run spread on the unpatched baseline is about 10%; the deltas are larger than that.

Residual with everything on, wikipedia: `construct_enhanced_tree` ~60 ms, `build_snapshot_lookup`
~31 ms, `create_simplified_tree` ~12 ms, paint order 2.7 ms. Amazon: ~30 / 15 / 8 / 4.

Where a System 1 step's wall time goes (observed on the same pages): CDP round trips 60–500 ms,
Jev 150–460 ms, DOM CPU 64–118 ms. DOM CPU is therefore 10–25% of an S1 step.

## What the ports showed

- R1 paint order: the algorithm was the cost; Rust removes it (5–11x, byte-identical).
- R2 snapshot lookup: the algorithm is ~1 ms in Rust; the cost is building 18k
  `EnhancedSnapshotNode` + `DOMRect` + a 10-key dict per node in Python. Rebuilding them in
  the adapter loses. Opt-in only.
- R3 hashes: 2x; Python string assembly is 87% of what remains.
- Lazy uuid: the only per-node Python cost that was pure waste; removed locally, drafted upstream.

Inference from these: every remaining millisecond is Python object construction that
downstream code (serializer, tools, history hashing) reads attribute by attribute. A Rust port
pays off only where it stops those objects from being built, not where it recomputes them faster.

## Options

(a) Frozen `#[pyclass]` snapshot lookup consumed by the tree builder, with `bounds` as a
    lightweight pyclass and `computed_styles` built on access. The tree builder reads
    `snapshot_node.bounds` for every node (19 call sites), so the saving is the dict and
    dataclass construction only: inferred 15–20 ms of the 31 ms snapshot phase on wikipedia.
    Bounded: the R5 patch seam already rebinds `build_snapshot_lookup`; the contract test
    would pin the five attribute names the builder reads.

(b) Rust-owned enhanced tree: construct + snapshot + simplified tree in Rust, exposing lazy
    node views. Inferred to be the only route below 50 ms on wikipedia, but every consumer of
    `EnhancedDOMTreeNode` (serializer, hashing, tools, history) would read through pyclass
    getters, and upstream's `__json__` and `asdict` paths would need shims. Large boundary;
    tracks a fast-moving upstream module.

(c) Upstream: drop the unused uuid (drafted in `docs/upstream/`), then propose a DomService
    backend hook so (a) needs no monkeypatch.

## Recommendation

Do (a) as a bounded follow-up after E1, keep (b) deferred until S1 step latency is shown to be
the bottleneck on real tasks (it is not today: Jev and CDP dominate), and offer (c) upstream when
the numbers are in the README. Keep G3 recorded as not met rather than moving the gate.
Net: the Rust work that paid was the work that deleted Python objects or Python algorithms;
the work that recomputed results into Python objects did not, and that is the rule for any
further port.
