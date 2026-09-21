# R2: DOMSnapshot lookup in Rust — equality proven, perf gate not met

Median of 15 runs, ms, Python 3.12, release wheel.

| fixture (nodes) | pure twin | Rust core (incl. reading CDP lists from Python) | Python dataclass rebuild | native total |
|---|---|---|---|---|
| wikipedia-python (18,234) | 69.5 | 10.3 | 76.8 | 89.4 |
| wikipedia, gc.collect() first | 29.9 | 10.7 | 26.5 | 39.3 |
| amazon-usb-c-hub (9,852) | 14.5 | 5.9 | 12.9 | 20.2 |

Criterion on the pure Rust algorithm over a synthetic 13.5k-node document: 1.2 ms.

Reading: upstream's cost is not the lookup logic, it is materializing ~18k
EnhancedSnapshotNode plus DOMRect plus a 10-key computed_styles dict per node. Rebuilding
the same objects in the adapter costs what the pure function costs, so the round trip
loses. The port only pays if the boundary changes:

(a) a frozen #[pyclass] lookup the tree builder reads by backend id, with sub-objects
    created lazily on access (requires patching `_construct_enhanced_node` and `__json__`,
    the R5 patch plus an R7 upstream hook), or
(b) one Rust pass over the raw DOMSnapshot message bytes producing compact arrays for
    R1 and R2 together, skipping Python lists entirely.

Decision deferred to R7. Until then the adapter is opt-in (JEVDUAL_NATIVE_SNAPSHOT=1);
equality and the sensitive-value test run in CI either way.
