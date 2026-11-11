# Media evidence integrity

Preregistration: `581abf0`, notebook `docs/notebook/2026-11-11-media-evidence-integrity.md`. This package uses fixture credentials and mocked transport only, without real key reads, provider calls, installs or UI work.

## Retained metadata redaction

The provider response metadata was copied into `manifest.json`, whose writer previously redacted only the credential. New tests echo primary and sidecar base64 in model/provider/response-ID fields as well as content. They also force response-file persistence failure after receipt. Both cases failed before repair (`red-redaction.txt`). Every main artifact writer now receives the same credential and exact media encodings, including intent, success and failure manifests. Existing recursive redaction also covers structured metadata.

`green-redaction.txt`:63 helper/notebook checks pass. Media hashes, usage, one-request behavior and other existing transport contracts remain covered. Changed-file Ruff, notebook validation and diff checks pass. This fixes retained evidence handling; it does not establish media perception or a financial cap.

## Output ownership

A deterministic mkdir-boundary test creates a competing owner's pending intent after validation and fails this invocation's mkdir. Both dry-run and execute cases previously wrote a failed manifest into that directory (`red-ownership.txt`). A local ownership flag is now set only after successful exclusive mkdir; error persistence requires that flag. The loser leaves the directory unchanged and dispatches nothing. Existing owned-failure tests continue to retain evidence.

`green-ownership.txt`:65 helper/notebook checks pass, including both integrity repairs. `ruff.txt` records changed-file lint. Notebook validation and `git diff --check` pass; result redaction changed zero files. Prediction commit: `581abf0`; redaction fix: `8312f72`. Both findings were source-audit discoveries confirmed by failing tests, not observed disclosure or corruption in the historical live run.

These are reusable evidence-handling repairs. They do not change media routing, provider selection, request budgets, app-specific extenders or calibration results. The ownership flag addresses competing acquisition, not hostile path replacement after ownership. Exact-string redaction does not remove arbitrary transformed media or generally de-identify model output. No paid or live operation is needed to qualify this package.
