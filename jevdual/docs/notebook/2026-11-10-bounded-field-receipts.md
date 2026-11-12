# Bounded field projection receipts

## BFR1 · prediction · 2026-11-10 17:06
Question: do native field receipts mistake a bounded display preview for full readback, including a false mismatch on a correctly entered long field and false equality when the intended text equals only its truncated preview?
Hypothesis: recording projection truncation per native text candidate and persisting it with the menu allows field receipts to stay unverifiable whenever their comparison requires a bounded current value or append baseline, without weakening identity, password, nondispatch or roster checks.
Test: reproduce through public CLI simulated-Mac scenarios a correct long type, a full value whose bounded preview equals intended text, append with a truncated persisted baseline, and a full short field ending in a literal ellipsis. Check legacy baseline handling, metadata serialization and existing secret, identity and exact-readback regressions.
Predicts: baseline misclassifies the long type and preview-equality cases; explicit truncation provenance makes them unverifiable, preserves ordinary short-field confirmation, and prevents a capped append baseline from producing a definite equality or mismatch. A missing legacy flag is treated conservatively when its value has the native cap's ellipsis signature.
Against: a bounded preview still produces confirmed or definite unequal content, a nontruncated literal ellipsis is blindly classified as truncated, metadata disappears across session save/load, or a nondispatch/identity/secret gate is bypassed.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/drafts-type-styles.txt; python/jevdual/native.py::menu_from_snapshot; python/jevdual/session.py::_field_receipt

## BFRU1 · update · 2026-11-10 17:11
Resolves: BFR1 = held
Observed: the pre-repair public CLI scenarios reproduced a false partial receipt for correctly entered long text and a false confirmed receipt when an unseen suffix differed but its clipped preview equaled the intended text. A pending append reconstructed through public look also used a truncated persisted baseline as definite unequal content. Explicit projection provenance now makes these comparisons unverifiable. A literal ellipsis in an untruncated field remains confirmable, and missing legacy metadata with a native cap-shaped ellipsis remains uncertain. The affected session, native, menu, identity, secret, CLI and authorizer suites pass328 tests; Ruff passes.
Changes: record native Candidate.value_truncated, persist it in session observations and compact model state, label clipped displayed values, and stop receipt content comparisons that require clipped current or prior values. Existing refusal, ambiguous identity, placeholder roster and password gates run first. No raw full-value readback claim is added.
Next: freeze the repair, preserve evidence and hand it to the parent while live song work continues on the separately identified installed runtime.
Refs: prediction1b24585; results/bounded-field-receipts-20261110/red.txt; results/bounded-field-receipts-20261110/pytest.txt; results/bounded-field-receipts-20261110/report.md

## BFRS1 · summary · 2026-11-10 17:11
Established: native projection clipping no longer proves full-value equality, definite mismatch or append/no-op conclusions through the field receipt comparison. Truncation provenance survives session save/load; secure fields do not expose clipping metadata derived from secret length.
Uncertain: these offline scenarios do not establish live Suno content, persistence, successful replacement of a React field or installed-wheel behavior. The append baseline regression reconstructs an already-pending action before public look rather than asserting a new real append happened. A false projection flag establishes only that Footwork did not clip its supplied value, not that the external driver supplied exact complete content. Existing public read still carries a preview; native raw maps mix direct AX and SDK fallback provenance.
Decision: deliver the conservative receipt repair without a new full-read feature or installation. Keep the distinct observed Suno replacement no-op outside this package.
Refs: results/bounded-field-receipts-20261110/report.md

## BFRU2 · update · 2026-11-10 17:12
Observed:296 adjacent completion, capability, native receipt, Linux native, form acceptance and pinned CUA seam checks pass. No additional source changes were needed after the initial affected regressions.
Next: commit the tested repair and retain the installed/runtime and live Suno limits in the parent report.
Refs: results/bounded-field-receipts-20261110/adjacent.txt
