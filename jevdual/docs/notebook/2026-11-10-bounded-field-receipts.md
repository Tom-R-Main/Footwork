# Bounded field projection receipts

## BFR1 · prediction · 2026-11-10 17:06
Question: do native field receipts mistake a bounded display preview for full readback, including a false mismatch on a correctly entered long field and false equality when the intended text equals only its truncated preview?
Hypothesis: recording projection truncation per native text candidate and persisting it with the menu allows field receipts to stay unverifiable whenever their comparison requires a bounded current value or append baseline, without weakening identity, password, nondispatch or roster checks.
Test: reproduce through public CLI simulated-Mac scenarios a correct long type, a full value whose bounded preview equals intended text, append with a truncated persisted baseline, and a full short field ending in a literal ellipsis. Check legacy baseline handling, metadata serialization and existing secret, identity and exact-readback regressions.
Predicts: baseline misclassifies the long type and preview-equality cases; explicit truncation provenance makes them unverifiable, preserves ordinary short-field confirmation, and prevents a capped append baseline from producing a definite equality or mismatch. A missing legacy flag is treated conservatively when its value has the native cap's ellipsis signature.
Against: a bounded preview still produces confirmed or definite unequal content, a nontruncated literal ellipsis is blindly classified as truncated, metadata disappears across session save/load, or a nondispatch/identity/secret gate is bypassed.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/drafts-type-styles.txt; python/jevdual/native.py::menu_from_snapshot; python/jevdual/session.py::_field_receipt
