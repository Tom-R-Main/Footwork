# Native app repair and installed rerun

**The repairs are implemented and checked; the portfolio remains unqualified.** The frozen installed CLI completed an exact Finder rename and a Preview clockwise rotation that persisted through autosave and window closure. A killed controller resumed the partial Finder-to-Preview chain. Finder move remains unsupported. Installed Chrome passed URL-scope admission/refusal checks, but its form was unavailable in the background while foreground setup was refused by the active-user gate.

## Artifact and checks

- Runtime commit: `4c2c4cffb29a9c0b31d513b3b3a72e0f808d3426`.
- Offline pure-Python wheel SHA-256: `2da4bd202be6b9c56debe014a39b454b115d163a28b98f22ce909c6c162b5704`.
- Exact installed inventory/module hashes: [candidate.json](candidate.json). Six inspected runtime modules resolve inside the installed candidate directory: [runtime.json](runtime.json).
- Existing host dependencies were reused. This establishes the installed candidate entry point, not clean-machine onboarding.
- macOS 26.4; Finder 26.4; Preview 11.0; Chrome 156.0.8078.48.
- Full suite: **2025 passed, 26 skipped**, 125.23 seconds: [full-suite.txt](full-suite.txt). Focused selection: 154 passed before the final two binary-save regression cases were added; the full suite includes those cases. Ruff and notebook validation passed.

The required predictions were committed in `bc90736`, `7c039d4` and `0be130b`. Development diagnostics preceded the frozen installed trial. No provider calls, network dependency downloads or runtime flag changes to bypass action policy occurred.

## What changed

Finder sessions can bind an owned fixture manifest and accept `file:/absolute/path` selectors. Startup selects the unique window containing that file among identically titled windows. Every use resolves its Foundation file-reference URL, manifest scope, retained device/inode, complete bounded AX traversal and current frame. Unreadable subtrees, cycles, duplicate matches, symlinks and replacement inodes refuse. The rename route selects the sole exact row, opens File to validate Rename, enters the actual transient editor, writes its value and sends one foreground Return. A same-inode path transition qualifies its result. Acknowledged input counts are a lower bound; unavailable SDK counts remain unavailable.

Preview can retain narrow menu predicates: a new exact Undo Rotate marker on its bound document, or a Save-associated edited/file-digest transition. These are checked against the admitted operation, arguments, PID/window and producer schema. The independent image oracle decides pixel correctness. A plain menu acknowledgement still cannot establish task completion. SDK nested errors are preserved.

Chrome scope now comes from a separate complete bounded trusted-toolbar walk, excluding web-content descendants. Method, PID/window, errors, coverage and the real omnibox are checked independently of whole-page completeness. Input evidence retains this scope provenance. Missing or changed scope refuses.

## Frozen installed observations

| Requirement | Observed result | Qualification limit |
| --- | --- | --- |
| Exact Finder rename | Final/applied retained receipt; same inode at `inbox/renamed.png`; unchanged bytes and protected siblings | Required move to `organized/renamed.png` did not occur; `move` is unsupported and sent no input |
| Wrong-directory file | Same-basename decoy refused before admission | Live ownership negative; replacement/duplicate/window/error cases also have simulated CLI/module coverage |
| Rename replay | Original token returned its retained result after the old pathname disappeared | No second rename input; token handling precedes target lookup |
| Preview rotation | Final/applied receipt for Rotate Right; independent 3-by-5 pixels match the prescribed clockwise transform | One fresh rotation; repeated same Undo marker is not a supported proof |
| Preview persistence | Correct PNG on disk and after closing the exact owned document | Autosave, not an explicit Save input; initial 12-second wait timed out and was retained |
| Interrupted handoff | Owned controller received SIGKILL after settled Finder rename; replacement controller accepted its checkpoint and ran Preview | A stage-boundary interruption of a rename-only partial chain; not the required rename-and-move portfolio chain or a mid-input crash |
| Chrome scope | Exact PID/window/native URL start accepted; mismatched URL refused | Form fields were unavailable in the background capture; no installed form input was admitted |
| Installed lost-response submission | Not reached; independent server ledger has zero ingress/records | Foreground setup refused twice for recent user input; no permission/posture widening or uncertain retry |

The first Preview oracle wait expired before autosave completed. The harness process exited; a later read-only check found the correct persisted pixels within the original lane budget. It resumed from the retained applied rotation receipt without repeating rotation or Save. Chrome startup likewise continued through a read-only native start after foreground setup refusal; its absent form field refused before admission. The trial did not turn those failures into passes.

The handoff controller records Finder and Preview as completed for this **rename-only diagnostic chain**. This does not close the portfolio's Finder move requirement. Chrome is active with no completed submission; no missing receipt was synthesized. The frozen trial's authority has no unresolved input because the only admitted mutations—rename and rotation—settled. See [live-summary.json](live-summary.json), [live-authority.json](live-authority.json) and [live-handoff.json](live-handoff.json).

## Retained development failures

[development.json](development.json) retains the deciding probes and unknown operations:

- A Chrome traversal initially mistook recycled transient AX wrapper pointers for repeated elements. Retaining wrapper lifetimes fixed the deciding capture; the second capture completed with one trusted toolbar bar.
- Finder name-cell AXValue/AXConfirm acknowledgements changed displayed text without renaming the file, in background and foreground. These attempts remain unknown. They were not retried on the same artifact.
- Entering the actual Rename editor worked in a separate direct AX diagnostic. The combined CLI still failed until it opened File and observed enabled Rename before pressing the leaf. The final development CLI rename then settled with independent same-inode/byte/sibling checks.
- A separate development Chrome probe typed four synthetic fields and persisted one ticket. Its click lacked qualified delivery and remains unknown; input was not repeated. Its supplied digest was the original manifest value, so this was a form transport probe, not a transformed-artifact handoff qualification. The durable server record was not promoted into a native receipt.

Unit and scenario tests cover false cell-write success, ID renumbering, same-title windows, duplicate source windows, destination races, disabled Rename, strict AX read failures, web-content scope impersonation, partial/wrong-window scope, mismatched native predicates and binary Save proof retention. Offline HTTP/lost-response and subprocess tests remain separate from installed UI evidence.

## Cleanup and remaining work

Exact owned Finder/Preview windows closed; both owned Chrome process trees and both listeners stopped. The saved image still passed the pixel oracle after closure. Shared Finder and Preview stayed running. Seven old/development unknown operations remain retained, including the previous portfolio attempt. Evidence and fixture artifacts remain available: [cleanup.json](cleanup.json).

Next prerequisites are a qualified Finder move route and Chrome form readiness that respects active-user posture, followed by submission qualification/reconciliation against independently bound durable ingress evidence. Repeat the full required cells and connected chain on a new frozen candidate. Current matching files or one deduplicated server row cannot clear historical uncertainty by themselves.
