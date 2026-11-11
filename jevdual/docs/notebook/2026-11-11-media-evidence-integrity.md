# Media evidence integrity

## MEI1 · prediction · 2026-11-11 00:10
Hypothesis: upstream metadata can retain exact encoded primary/sidecar media in the final manifest because its write applies credential-only redaction, unlike the response write.
Test: public helper with fixture credentials and mocked HTTP response echoing both encodings and the fixture key in model/provider/ID and content; also force response persistence failure after receipt to inspect the failure manifest. Inspect all retained artifacts and captured output. No real keys, provider calls or UI.
Predicts: baseline retains an exact media encoding in a manifest; uniformly applying the known sensitive strings to retained artifacts removes both encodings and key while preserving useful hashes, usage and one-request behavior.
Against: baseline artifacts already exclude both encodings, a repaired failure path still leaks, or the repair destroys non-sensitive provenance or submits another request.
Refs: scripts/openrouter_media_review.py; tests/test_openrouter_media_review.py

## MEI2 · prediction · 2026-11-11 00:10
Hypothesis: an invocation losing output-directory creation can write a failure manifest into the winning invocation's directory because error persistence tests directory existence rather than ownership.
Test: public helper with a deterministic mkdir boundary that creates a competing directory after validation, then raises FileExistsError; cover dry-run and execute with fixture credentials and a transport that must not dispatch. Verify competitor sentinels and absence of new artifacts. Check a separately owned failure still retains its manifest.
Predicts: baseline writes a failed manifest into the competing directory; recording ownership only after successful mkdir prevents every loser write and keeps owned failure evidence.
Against: baseline already preserves the competing directory exactly, losing creation dispatches a request, or the repair suppresses owned failure evidence or modifies existing files.
Refs: scripts/openrouter_media_review.py; tests/test_openrouter_media_review.py

## MEIU1 · update · 2026-11-11 00:11
Resolves: MEI1 = held
Observed: both new metadata-echo cases failed on the baseline, including the response-persistence failure path. After passing primary and sidecar encodings to every main artifact writer, all63 helper/notebook checks pass; hashes, reported cost and one-request behavior remain covered. Changed-file Ruff and notebook validation pass.
Changes: known sensitive encodings are computed after bounded media reads and applied consistently to dry-run, intent, response, success-manifest and failure-manifest writes.
Next: reproduce and repair output-directory ownership under MEI2. No live credentials, provider requests or UI were used.
Refs: results/media-evidence-integrity-20261111/red-redaction.txt; results/media-evidence-integrity-20261111/green-redaction.txt; prediction581abf0
