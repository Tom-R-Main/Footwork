# R5: DOM pipeline CPU (replayed get_dom_tree + serializer), unpatched vs patched

Median of 10 runs, gc.collect() before each, Python 3.12.6, patches active: {'orjson_decode': True, 'paint_order': True}.
CDP round trips are excluded; this is the CPU that follows them per step.

| fixture | unpatched ms | patched ms | delta ms | paint order off/on ms | snapshot lookup off/on ms |
|---|---|---|---|---|---|
| amazon-usb-c-hub | 85.5 | 73.8 | -11.7 | 17.3/4.0 | 14.4/14.6 |
| dense-links | 37.4 | 19.1 | -18.3 | 19.8/1.8 | 2.8/2.9 |
| github-browser-use | 47.8 | 36.6 | -11.2 | 14.3/2.7 | 6.2/6.2 |
| hacker-news | 17.9 | 17.6 | -0.3 | 1.5/1.1 | 2.8/2.6 |
| ja-wikipedia-python | 85.0 | 78.7 | -6.3 | 9.0/1.7 | 17.3/17.2 |
| modal-over-content | 5.7 | 5.1 | -0.6 | 1.1/0.3 | 0.8/0.9 |
| sensitive-fields | 1.2 | 1.2 | +0.1 | 0.1/0.1 | 0.1/0.1 |
| virtual-list | 3.1 | 2.6 | -0.5 | 0.8/0.2 | 0.3/0.4 |
| w3schools-iframe | 79.3 | 75.2 | -4.1 | 5.4/1.1 | 10.7/11.1 |
| wikipedia-python | 145.9 | 136.0 | -9.9 | 10.0/2.5 | 30.5/30.2 |
| youtube-home | 17.9 | 17.1 | -0.8 | 0.5/0.3 | 2.1/2.1 |

Residual per phase with patches on, wikipedia-python: build_snapshot_lookup 30.2, construct_enhanced_tree 82.1, create_simplified_tree 12.3, calculate_paint_order 2.5, optimize_tree 0.4, assign_interactive_indices 2.8 ms.
Residual per phase with patches on, amazon-usb-c-hub: build_snapshot_lookup 14.6, construct_enhanced_tree 37.8, create_simplified_tree 7.6, calculate_paint_order 4.0, optimize_tree 0.9, assign_interactive_indices 4.7 ms.

G3 gate (DOM CPU < 50 ms on wikipedia and amazon with patches on): NOT MET.
