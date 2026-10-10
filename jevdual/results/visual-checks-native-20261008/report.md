# Native advisory visual checks: runtime verification

Observed: the actual `footwork` CLI parser and commands, Cua SDK, two task-owned AppKit scenes, production Decisions image transport and native System Two message builder passed the selected read-only integration checks. Product source was frozen at `82aef06e180915a4cfd75ca095a44b98a28ebd7c`; each proof records exact source hashes. The second run adds request-body hashes and explicit process cleanup to the verifier, without changing product code. Both runs are preserved.

## Reproduce

From `jevdual/`, run `.venv/bin/python scripts/verify_visual_checks.py repro1` with a fresh attempt name. A safe optional attempt name, such as `evidence1`, uses fresh nested run/result directories. The existing Python/Cua/AppKit runtime and `pdftoppm` are required. The script refuses existing output directories, preserving earlier evidence.

Read the final instrumented proof in [evidence1/verification.json](evidence1/verification.json). The original proof remains [verification.json](verification.json). Private native sessions and all request/receipt/capture files remain under `runs/visual-checks-native-20261008/`.

## Selected checks

| Check | Observed outcome |
|---|---|
| Default preparation | Capture and advisory unavailable receipt; no provider request or budget file |
| Document reference input | Real document-preview UI, genuine supplied PDF page render, valid bound advisory receipt |
| Crop input | Real crop-canvas UI; actual inspector viewport and caller-declared full-source transform; valid bound advisory receipt |
| Second request in each one-call workflow | Budget refusal; no second provider request |
| Native provider refusal | Refusal status and absent probability |
| Provider timeout | Timeout; pessimistic 64,000-token reservation remains unsettled |
| Supplied source changes after capture | Invalidated status, absent probability |
| Session generation changes while request is outstanding | Invalidated status, absent probability |
| Missing disclosure, secret session, browser session | Refused before capture/provider; no visual output directory |
| Native System Two handoff | Typed question/resource/crop association survives; pixels explicitly unavailable to the text transport |
| Authority/effect boundary | Zero calls to intercepted native action methods, zero fixture effects and zero grant files |
| Saved evidence | PNG decoding, safe receipt manifests, state readback and body/image hashes pass |
| Cleanup | Both owned AppKit processes terminated and loopback listener closed; separate process readback found neither scene running |

Each run exercises nine receipt scenarios and three early refusal scenarios, with six loopback requests. Native capture is sequential and coverage is explicitly incomplete. Neither AX completeness, resource ownership nor the caller-declared image transform is promoted to proof of authority.

## Boundaries

The verifier supplies each fixture's actual PID/window from its readiness file, then invokes the real CLI and Cua SDK. Application discovery and `footwork start` are unqualified. The document reference is page 1 of the run-owned `source-0.pdf`, rendered by existing `pdftoppm` at 96 dpi; its source PDF hash and render recipe are recorded. Captured PNGs are unchanged and separately archived for document and crop scenes.

Only the production client's HTTP transport is intercepted: its official URL is rewritten to a run-owned loopback HTTP server. No production provider, API key loader, external endpoint or paid request is used. Native probabilities and usage are fixed fixture responses, so perception accuracy, calibration and provider/workflow performance remain **unqualified**. The target selected in the document fixture intentionally receives the fixed advisory answer regardless of visual truth; it causes no action.

The native System Two check exercises the production message builder with the actual captured menu and result. It does not call a System Two model or prove a complete agent recovery workflow. Real Finder/Preview workflows, browser capture, crop execution, saved-artifact effects and automatic visual admission remain outside this verification.

Result directories and private run directories passed `scripts/redact_results.py`: zero files required changes.

Offline source validation: 1,023 tests passed, 26 skipped; global Ruff, notebook checks and installed CLI help passed. Exact command/count/source identity: [checks.json](checks.json). Parent independently confirmed proof source hashes, stored PNG hashes and process cleanup.
