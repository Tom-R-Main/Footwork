# Suno workflow development run

Date: November 10, 2026. Status: partial; creation verified, audition/edit/save/reopen remain unverified.

## Artifact and boundary

Preregistration: `docs/experiments/suno-end-to-end-20261110.md`, commit `25d4107`.
Notebook: `docs/notebook/2026-11-10-suno-end-to-end.md`.
Live entry point: `/Users/thomasmain/.local/bin/footwork`, installed source `f5d41c482e158eac18b15f5820bd6be150f00097`, CUA `0.46.0+footwork.5486b624.cleanup2`.
The run used the existing signed-in Suno Chrome window through the native CLI, not an API or a replacement browser profile.
Private observations, receipts, screenshots and the verbatim Consensus document remain in ignored `output/suno-20261110/` relative to `jevdual/`. This report intentionally omits unrelated browser content.

## Live evidence

| Requirement | Kind | Evidence | Result |
| --- | --- | --- | --- |
| Establish signed-in Suno surface | Current state | `start.txt`, native target inspection manifest | Window bound and screenshot observed |
| Navigate to Create | Historical action | `create-navigation.txt`; screenshot `session/inspection/5f55aaddf4774509a7d910de182b440e.png` | Visible Create form; receipt's title change alone was insufficient |
| Create a new song | Historical action and current saved state | `instrumental-create-once.txt`, `instrumental-candidates-ready.txt`, `generated-link-identities.json`, exact song-page metadata | One submission produced two complete unpublished instrumentals,214.88 and204.8 seconds; requested90–120-second length missed |
| Audition/select a candidate | Answer grounded in audio | Retrieved playback bytes were not decodable; no generated-song audio supplied to Qwen | Unverified; authenticated export route pending |
| Perform bounded editor change | Historical action and current state | No editor action submitted | Unverified |
| Check transition quality | Answer grounded in playback | No original/edited playback pair | Unverified |
| Save and reopen derivative | Current state | No derivative submitted | Unverified |

The preregistered five-milestone metric has one completed milestone. A single generation command created two run-owned songs; their metadata independently reports complete, instrumental and not public. Existing songs were not intentionally edited, and no purchase or publication command was submitted. Creation is separate from audition, editing and saved-derivative verification.

## Friction log

| ID | Observed friction | Resolution or remaining prerequisite |
| --- | --- | --- |
| F1 | Title/address changed to Create while repeated native AX menus still exposed profile controls; screenshot showed the creation form | Require a specific control and cross-check rendered evidence. Driver source documents possible Chromium AX delay; cause is not proven here. A source change adds bounded control-appearance waiting, separately tested below |
| F2 | App-name-only start selected a different concurrently running Chrome process and could not find the Suno window | Resolved for this run with explicit `--pid 24992` and selected window title |
| F3 | `elements_incomplete` appeared even when target inspection succeeded | Source inspection distinguishes conservative Chromium coverage from actual truncation; numeric target inspection can still be qualified. Do not treat the flag as an empty page or full-page evidence |
| F4 | Two Window menu attempts returned `human_active` before input delivery | User agreed to pause input; subsequent guarded Window menu actions succeeded. The idle gate remains active; availability must be rechecked for each action |
| F5 | Initially no live audio/video judgment path | Project-local OpenRouter helper now supplied actual audio to the selected Qwen route, distinguished tones from silence and reviewed three reference songs. Video macro perception held, but fine defects and precise timing failed qualification; see the separate reports |
| F6 | `do enter FIELD TEXT` pressed Return without typing the trailing text | Source now rejects trailing enter text before dispatch; use type for text and enter for Return. No navigation was inferred from the failed sequence |
| F7 | A clipped480-character field preview caused false mismatch/equality reasoning | Candidate truncation provenance now makes incomplete content comparisons explicitly unverifiable; no full-value assertion from a preview |
| F8 | Suno's visible rich Lyrics field stayed blank while AX exposed x after background replacement/append attempts | Default native web typing hard-coded background delivery. The explicit foreground route and guarded field-focus preparation delivered the original461-character lyrics. Controlled new-copy equality independently verified all24line breaks; native AX getters serialized them differently |
| F9 | First guarded foreground live test raised `tuple has no attribute location` while decoding selected range | Fixed in be8ea6b with338 focused checks; live retest reached the selection guard. Historical unknown preparation receipt is retained |
| F10 | Fresh visible-empty rich editor reports AXValue LF and one character, while selection is0,0 | Exact read-only probes retained. No stripping or implicit terminal-LF exception. Explicit selected-range editing114a1b9 preserves the suffix and passes542 checks; guarded focus preparation4e3297a permits visible insertion. Empty-paragraph canonicalization still violates exact suffix preservation, so that receipt remains partial; ordinary whole-field replacement and controlled copy separately qualify intended lyrics |
| F11 | Two generated songs share a title, so native link click refused ambiguity | Fixed in e6785a7 with615 affected checks. Live source exposes distinct hrefs and correctly opens the second actual song. URL navigation separately reached the first. Player resource must also be verified: internal navigation retained the previous player until Reload |
| F12 | Generic More actions popup refuses background opening | Explicit guarded foreground click e802740 passes686 affected checks and opens that popup. Screenshot reveals the caller chose the comment emoji picker rather than the intended song menu. Picker dismissed, no comment submitted. Actual song-menu targeting was later qualified with a distinct DOM ID and exact document URL |
| F13 | Progressive playback files are not recognized audio containers | Song-page media metadata and received hashes retained; FFmpeg failed decoding. No critic request with opaque bytes and no attempt to bypass the format. Use authenticated Suno export |
| F14 | TypeSafe judgment returned400 max_tokens_exceeded for Escape | Request paused before dispatch; exact per-action authorization for the already-authorized harmless popup dismissal succeeded with normal gates. Provider-error cause unknown; no general judge disable or retry after uncertain input |
| F15 | Main song Play and own-song menu refuse duplicate native identities | a6defe1 qualifies complete unique native control DOM IDs within the same independently proven AXWebArea URL. Inspected hero menu opens the actual song operations. Main Play peers have no qualifying IDs and remain refused |

| F16 | Rich lyrics AXValue and AXSelectedText omit different line breaks; a generic Copy receipt saw no visible change | Controlled copy read only newly changed clipboard content and exactly verified461characters/24LF.6bf59a4 now reports these unsupported text/menu postconditions as unverifiable, requiring independent evidence instead of retry |
| F17 | Download format controls allow multiple simultaneous selections, with no AX selected-state exposed | Screenshot verified MP3 selected and default M4A deselected before one included unlock; no purchase |
| F18 | Native Save sheet is a separate exact window, so the parent-bound foreground hotkey refuses | SDK observes modal325928; explicitly rebound Save session confirms filename. Project-folder navigation awaits bounded exact AXSheet resolution; Save remains untouched |

## Resume

Continue from the already prepared second-song MP3 export in the native Save sheet, with filename candidate-b.mp3 and project destination still to be selected. Verify project-safe export destination before downloading, retrieve playable audio for both candidates, audition/select, make a bounded editor change, inspect the transition and verify saved/reopened output. Finish live range-edit qualification once proper field focus is available. Preserve originals; never generate diagnostic text or repeat the already-completed instrumental submission.

No local source patch has been installed into the user-local release. Use the checkout explicitly when verifying new behavior. The user subsequently authorized project-only yt-dlp installation and selected Qwen through OpenRouter with a local key. Audio probes and reference reviews have now run; see `reference-analysis.md`. No global installation, merge or deployment occurred.

## Source repair and verification

Commit `0f691bd`, following prediction `e9d3a8f`, adds native `look --until "Exact label" --timeout 10`. It performs fresh read-only observations, preserves partial-coverage warnings and distinct poll screenshots, succeeds only on exact candidate appearance, and exits 6 on deadline. It grants no action permission. The timeout bounds cooperative observation/polling; binding and shutdown can add elapsed time. The ordinary look route is unchanged.

The affected offline suites passed 293 tests; Ruff, notebook validation and diff checks passed. Reproduction and commands: `results/observation-until-20261110/report.md`.

Live public checkout verification used `.venv/bin/python -m jevdual.cli look` with the bound native foreground session. `--until Advanced --timeout 5` exited 6 after approximately 5 seconds with the toolbar-only partial observation retained. `--until 'View site information' --timeout 5` exited 0 on the actually present candidate. Neither sent input or established form readiness. Private command evidence: `output/suno-20261110/checkout-until-advanced.txt` and `checkout-until-present.txt`.

This resolves the missing bounded observation primitive. It does not repair Chromium's external accessibility behavior or establish song/editor completion.

The later foreground-web-text repair is frozen at `a516212`, using CUA `0.46.0+footwork.5486b624.cleanup2.focus1` through a project-local overlay. It requires readable replacement values and confirmed addressed-field focus, uses positive pacing to avoid SDK tail resends, and leaves default background typing unchanged. Both independent source-review blockers were fixed and rechecked. The full default offline suite passed3098 tests with62 skipped in261.07 seconds; see `offline-suite.json` and `results/foreground-web-text-20261110/report.md` for the separate focused/native-build evidence. This does not yet establish live Suno typing success.


Frozen source6bf59a4 includes qualified menu/link identities and the receipt scope corrections. Full default offline suite:3231passed,62skipped in220.28seconds; earlier a6defe1:3215passed,62skipped in225.09seconds. See the corresponding offline-suite JSON records. These counts establish offline regression coverage, not live editor completion. UI runs use immutable Git archives and the unchanged project-local focus1 overlay, independently of concurrent checkout edits.
