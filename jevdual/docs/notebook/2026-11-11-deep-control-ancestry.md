# Deep exact-window control ancestry

## ANC1 · prediction · 2026-11-11 00:20
Hypothesis: the opaque-control backing read refuses complete valid parent chains of33or34nodes because its32node bound expires before reaching the exact bound native window; a64node walk with explicit native-object cycle detection restores those reads without relaxing ownership, closest-document, exact-window or all-peer requirements.
Test: first reproduce opaque-target loss through the real public CLI simulator using actual control_backing over two complete33/34node trees. Then repair only this read-only traversal. Check33/34/64node chains succeed,65plus remain refused, cycles terminate early, and foreign owners, unreadable roles/parents, invalid closest URLs or another window still fail. Keep all-peer census qualification and named-control traversal limits unchanged. No live UI, model, network or posture change.
Predicts: baseline public CLI withholds the otherwise qualified literal IDs; repaired CLI offers them only when all observed peers have complete scope proof. The exact64node boundary holds and negative cases remain refused without dispatch.
Against: baseline already qualifies these chains, any incomplete/foreign/cyclic scope becomes qualified, an unreadable peer is omitted from collision evidence, the walk exceeds64nodes or another source/authority change is necessary.
Refs: docs/notebook/2026-11-11-suno-studio.md; output/suno-studio-20261111/parent-chains.json; python/jevdual/ax.py; tests/test_ax_semantics.py; tests/test_session_scenarios.py
