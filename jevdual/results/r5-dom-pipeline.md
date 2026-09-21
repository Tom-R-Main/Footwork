# R5: DOM pipeline CPU (replayed get_dom_tree + serializer), unpatched vs patched

Median of 10 runs, gc.collect() before each, Python 3.12.6, patches active: {'orjson_decode': True, 'paint_order': True, 'lazy_uuid': True}.
CDP round trips are excluded; this is the CPU that follows them per step.

| fixture | unpatched ms | patched ms | delta ms | paint order off/on ms | snapshot lookup off/on ms |
|---|---|---|---|---|---|
| amazon-usb-c-hub | 88.5 | 61.3 | -27.2 | 17.6/4.0 | 14.6/14.5 |
| dense-links | 39.7 | 17.6 | -22.1 | 21.2/1.9 | 2.8/2.9 |
| github-browser-use | 50.0 | 30.9 | -19.1 | 14.8/2.7 | 6.4/6.4 |
| hacker-news | 18.5 | 15.4 | -3.1 | 1.5/1.2 | 2.7/2.7 |
| ja-wikipedia-python | 105.5 | 76.8 | -28.7 | 10.8/2.4 | 21.4/20.4 |
| modal-over-content | 7.0 | 4.5 | -2.5 | 1.1/0.3 | 0.9/0.9 |
| sensitive-fields | 1.4 | 1.2 | -0.2 | 0.1/0.1 | 0.1/0.1 |
| virtual-list | 3.3 | 2.4 | -0.8 | 0.8/0.2 | 0.4/0.4 |
| w3schools-iframe | 81.3 | 80.6 | -0.7 | 5.5/1.4 | 11.2/15.5 |
| wikipedia-python | 148.6 | 116.3 | -32.3 | 10.2/2.6 | 30.8/31.4 |
| youtube-home | 17.8 | 13.1 | -4.7 | 0.5/0.3 | 2.1/2.2 |

Residual per phase with patches on, wikipedia-python: build_snapshot_lookup 31.4, construct_enhanced_tree 60.0, create_simplified_tree 13.4, calculate_paint_order 2.6, optimize_tree 0.5, assign_interactive_indices 3.0 ms.
Residual per phase with patches on, amazon-usb-c-hub: build_snapshot_lookup 14.5, construct_enhanced_tree 25.1, create_simplified_tree 7.8, calculate_paint_order 4.0, optimize_tree 1.0, assign_interactive_indices 4.7 ms.

G3 gate (DOM CPU < 50 ms on wikipedia and amazon with patches on): NOT MET.
