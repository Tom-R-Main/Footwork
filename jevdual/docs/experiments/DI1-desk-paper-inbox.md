# DI1: Camera paper note to a Footwork-checked desk inbox

Mode: bounded engineering/workflow feasibility. Not a model qualification or product-demand test.

## Hypothesis

An existing native-camera frame can supply a small paper note to local Apple Vision text recognition; an explicit review bound to the candidate digest can save exactly that text into a private inbox and Footwork can independently verify the saved bytes.

## Predictions

A known synthetic printed note yields expected text through the real Vision helper. A live paper note, when presented clearly and reviewed, can yield a saved note matching approved text. No text, altered candidates/source images, mismatched approval digests or invalid saved bytes cannot become verified notes. Repeating an accepted operation does not create duplicate notes.

Against: a verified result without exact matching saved bytes, fabricated browser/native carries, unreviewed capture triggering an action, or a repeat creating another note.

## Design

Keep camera acquisition in the existing tools/camera-capture-experiment package and desk workflow in tools/desk-inbox-experiment. Use one native frame per deliberate operation; microphone disabled. Use installed Swift/Vision for local English OCR, with no cloud provider. Preserve OCR lines/confidence as fallible evidence, never execution authority. Explicit review approves a text digest; corrections are retained separately from original recognition. Keep images, recognized/private text, review pages, notes and per-operation receipts in ignored private output.

Introduce a narrow provider-free read-only footwork check-artifact command and library boundary. It checks a digest-bound reviewed source and exact destination bytes. It supplies current artifact equality, not OCR correctness, native UI completion, authorization authentication or an exactly-once physical effect. Do not synthesize Footwork session carries or change native recovery/guard interfaces.

Primary metric: one accepted note exists exactly once and matches its independently approved source bytes (binary feasibility), with source/candidate provenance retained.

Checks: real Vision on a known generated printed note; public CLI whole workflow; repeat across processes; missing text; changed source/candidate; changed approval digest; missing/tampered destination; concurrency and interrupted write/receipt handling as appropriate. A human live note is a separate validation requiring positioning and review; if unavailable, report that gap explicitly.

Decision rule: qualify only demonstrated source/OCR/file behavior. Advance toward a daily desk inbox only after one real note is reviewed and saved. Keep synthetic proof separate from live paper utility and semantic correctness. No model calls, UI automation, external task creation, publication or robot movement.

## Result

Pending.

## Amendment · 2026-10-10 14:54
The user asks whether the camera mirrors. Preparation will expose an explicit --mirror-input option for OCR orientation and review display, bind it in request provenance, and retain original capture bytes. Mirroring is chosen from readable calibration text, not inferred from faces or OCR confidence. Normal/mirrored synthetic fixtures and the live LEFT 123 RIGHT line will assess orientation.
