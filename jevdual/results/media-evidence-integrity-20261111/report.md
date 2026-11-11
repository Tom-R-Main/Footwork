# Media evidence integrity

Preregistration: `581abf0`, notebook `docs/notebook/2026-11-11-media-evidence-integrity.md`. This package uses fixture credentials and mocked transport only, without real key reads, provider calls, installs or UI work.

## Retained metadata redaction

The provider response metadata was copied into `manifest.json`, whose writer previously redacted only the credential. New tests echo primary and sidecar base64 in model/provider/response-ID fields as well as content. They also force response-file persistence failure after receipt. Both cases failed before repair (`red-redaction.txt`). Every main artifact writer now receives the same credential and exact media encodings, including intent, success and failure manifests. Existing recursive redaction also covers structured metadata.

`green-redaction.txt`:63 helper/notebook checks pass. Media hashes, usage, one-request behavior and other existing transport contracts remain covered. Changed-file Ruff, notebook validation and diff checks pass. This fixes retained evidence handling; it does not establish media perception or a financial cap.

## Output ownership

MEI2 remains pending in this first fix commit.
