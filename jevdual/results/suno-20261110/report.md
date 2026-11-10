# Suno workflow development run

Date: November 10, 2026. Status: partial; live creation and editing are unverified.

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
| Create a new song | Historical action and current saved state | No generation submitted | Unverified |
| Audition/select a candidate | Answer grounded in audio | No song audio captured or supplied to a model | Unverified |
| Perform bounded editor change | Historical action and current state | No editor action submitted | Unverified |
| Check transition quality | Answer grounded in playback | No original/edited playback pair | Unverified |
| Save and reopen derivative | Current state | No derivative submitted | Unverified |

The preregistered five-milestone metric has zero completed milestones. Navigation is useful preflight evidence but does not count as song creation. Existing songs were not intentionally edited, and no generation, purchase or publication command was submitted.

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
| F8 | Suno's visible rich Lyrics field stayed blank while AX exposed x after background replacement/append attempts | Default native web typing hard-coded background delivery. An explicit foreground type route and addressed-field focus guard are under offline qualification; live success remains unverified |

## Resume

Reobserve the bound signed-in Suno creation window with the qualified project-local runtime. First verify a short diagnostic in the actual rendered Lyrics editor and exact field readback; replace it with the original run-owned lyrics before any generation. Verify style and title, submit once and reconcile generation state. Continue through actual-audio audition, a bounded editor change, transition playback and saved-state readback. Preserve originals. No generation with diagnostic text.

No local source patch has been installed into the user-local release. Use the checkout explicitly when verifying new behavior. The user subsequently authorized project-only yt-dlp installation and selected Qwen through OpenRouter with a local key. Audio probes and reference reviews have now run; see `reference-analysis.md`. No global installation, merge or deployment occurred.

## Source repair and verification

Commit `0f691bd`, following prediction `e9d3a8f`, adds native `look --until "Exact label" --timeout 10`. It performs fresh read-only observations, preserves partial-coverage warnings and distinct poll screenshots, succeeds only on exact candidate appearance, and exits 6 on deadline. It grants no action permission. The timeout bounds cooperative observation/polling; binding and shutdown can add elapsed time. The ordinary look route is unchanged.

The affected offline suites passed 293 tests; Ruff, notebook validation and diff checks passed. Reproduction and commands: `results/observation-until-20261110/report.md`.

Live public checkout verification used `.venv/bin/python -m jevdual.cli look` with the bound native foreground session. `--until Advanced --timeout 5` exited 6 after approximately 5 seconds with the toolbar-only partial observation retained. `--until 'View site information' --timeout 5` exited 0 on the actually present candidate. Neither sent input or established form readiness. Private command evidence: `output/suno-20261110/checkout-until-advanced.txt` and `checkout-until-present.txt`.

This resolves the missing bounded observation primitive. It does not repair Chromium's external accessibility behavior or establish song/editor completion.
