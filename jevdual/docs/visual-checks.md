# Native advisory visual checks

`footwork visual-check` asks one explicit visual question about an observed native target: document/reference appearance or crop/subject containment. It records the original window PNG, evidence identity, native probability or failure status, and a structured handoff. It never clicks, crops, saves, grants permission or verifies completion.

Use `footwork look --session SESSION` to obtain a current numeric target ID. Put the manifest and supplied PNG under the session. Files outside the session and symlink assets are refused. The check concerns one offered candidate; it does not claim every possible candidate was considered.

## Input

For document/reference matching, create `SESSION/request.json`:

```json
{
  "version": 1,
  "role": "document_reference_match",
  "criterion": "Does this offered preview match the supplied reference cover?",
  "criterion_version": "my-task-v1",
  "target": 12,
  "reference": {
    "path": "assets/reference.png",
    "sha256": "SHA256_OF_THE_EXACT_PNG",
    "resource_id": "reference-cover",
    "revision": "REFERENCE_RESOURCE_REVISION",
    "page": 1,
    "render_recipe": "supplied_png"
  }
}
```

Replace the example target, hashes and resource revision with actual task values. The PNG hash is checked. Resource ownership and the declared revision remain caller-supplied provenance; they do not prove which file a preview opens. For a document render, record its page and rendering recipe.

For `crop_subject_containment`, replace `reference` with a `source` asset having the same fields, identify the subject in `criterion`, and add:

```json
{
  "rectangle": [220, 45, 180, 235],
  "displayed_bounds": [70, 524, 620, 316],
  "orientation": "upright"
}
```

Both rectangles use `[x, y, width, height]`. `rectangle` is in source-image pixels; `displayed_bounds` is the image's declared global screen frame inside the window. Only upright, aspect-preserving display is supported. Source/display correspondence remains unverified. This check assesses the supplied crop; it does not generate coordinates or edit an image.

## Invocation and limits

Prepare evidence without loading keys or contacting a provider:

```sh
footwork visual-check --request request.json --session SESSION
```

This records a fresh capture and returns exit 4 with `provider_unconfigured`, without inventing a probability. Saved JSON and PNG paths appear in stdout.

Explicitly request a Decisions judgment with an existing configured key:

```sh
footwork visual-check --request request.json --session SESSION --provider decisions --disclose
```

`--disclose` permits the bound capture and supplied PNG upload for this purpose. Sessions that have handled a secret refuse before capture. Browser operator sessions remain unsupported. The current [Decisions guide](https://developers.openai.com/api/docs/guides/decisions) specifies inline base64 images and native predicate answers. The adapter sends one required predicate with no retry.

Initial operational limits: one call per session workflow, 4 MB encoded body, 64,000-token reservation, $0.0064 standard-input estimate, and a 10-second deadline spanning capture and judgment. These are advisory bounds, not calibrated admission thresholds. The local reservation is not a provider-enforced input or billing ceiling. Known usage above it is recorded and the answer rejected. Regional and other pricing configurations are not qualified by this estimate.

For one explicit recovery on materially changed evidence, configure `--max-calls 2 --max-cost 0.0128` on the first call. Ledger limits are fixed at workflow start. Metadata, wording, request IDs and timestamps cannot make unchanged visual evidence eligible again. No recovery is automatic. Unknown usage, cancellation and timeout retain their reservation. A new session must represent a new scoped workflow, rather than an automatic retry.

Exit 0 means a valid advisory probability for the recorded request. Refusal, unavailable evidence, timeout, invalid response, stale generation or exhausted budget returns exit 4. No .80/.20 or Jev action threshold is imported. Reobservation invalidates the session's latest summary. Source, manifest or session changes during a call invalidate a positive before it is printed as current. Receipts remain historical; stored hashes do not prove unchanged live pixels.

## Handoff and verification

Explicit workflow callers can use `capture_request` and `NativeAgent.check_visual`, owning source/disclosure scope. Normal Jev/action policy never invokes them automatically. Native System Two receives a redacted question/result summary identifying target, reference/source and crop geometry. Its text transport receives no pixels, and the handoff says so. Multimodal System Two and automatic visual-question classification remain outside this package.

Evidence remains under private `SESSION/visual/` until the operator removes the session. The directory must be owned by the current user and inaccessible to other users. Logs retain paths, hashes and statuses rather than images or opaque target tokens.

Run `python scripts/verify_visual_checks.py` from `jevdual/` for repeatable verification on task-owned AppKit scenes. It uses the actual CLI/Cua driver and production HTTP adapter directed to an owned loopback endpoint, with action dispatch forbidden. Fixed provider answers verify mechanics only. Independent model quality, real OpenAI access through this new adapter, browser capture and reviewed execution need separate qualification. See the [plan](visual-system-one-plan.md) for those gates.
