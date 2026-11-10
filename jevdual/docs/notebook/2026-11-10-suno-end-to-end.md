# Suno creation and editor workflow

## SUN1 · exploratory · 2026-11-10 16:30
Question: which concrete observation, targeting, timing, audio and persistence frictions prevent a Footwork operator from creating and editing a song in the user's signed-in Suno Chrome session?
Test: drive the installed CLI against the selected Suno window, retain private observations and receipts, create a run-owned draft, make a bounded editor change, and reopen the saved result. Do not modify existing songs or publish. Reproduce discovered product bugs as simulated-Mac public CLI scenarios before fixing them.
Refs: docs/experiments/suno-end-to-end-20261110.md; output/suno-20261110/

## SUNU1 · update · 2026-11-10 16:33
Observed: installed Footwork bound the signed-in Suno window and dispatched Create navigation. Title/address changed while subsequent AX menus retained profile controls; a target-bound screenshot showed the actual creation form. A later preflight saw the form controls. Reload subsequently exposed toolbar-only AX observations. A second Chrome process caused an app-name-only start to select the wrong PID; explicit --pid24992 bound the original window. Foreground-permitted Window menu attempts were twice refused with human_active and no dispatch. No song generation or editing has been submitted.
Inferred: neither title change nor a confirmed navigation receipt establishes form readiness. Driver source describes delayed Chromium AX updates, but the live cause is not proven; no cache repair is justified. Explicit process binding resolves the multi-instance selection for this run.
Changes: private artifacts actually use jevdual/output/suno-20261110 (git-ignored), correcting SUN1's shorthand output path. SUN1's heading time was mistakenly entered as16:30; the clock output before its commit was16:27 and commit25d4107 establishes ordering. Do not use that heading as a precise timestamp.
Next: add bounded control-readiness observation, wait for the user's desktop availability, then continue from the creation form. Preserve the full Consensus report and separately document engineering recommendations.
Refs: output/suno-20261110/create-navigation.txt; output/suno-20261110/create-look.txt; output/suno-20261110/session/inspection/5f55aaddf4774509a7d910de182b440e.json; output/suno-20261110/reload.txt; output/suno-20261110/show-window.txt; output/suno-20261110/show-window-retry.txt; docs/suno-workflow.md

## SUNU2 · update · 2026-11-10 16:36
Observed: repair0f691bd passed293 affected offline tests with Ruff and notebook checks. The live public checkout native look wait returned6 for Advanced after its five-second deadline and retained the partial toolbar menu; it returned0 for the actually offered View site information candidate. Neither command sent input. The user-local installed release was not replaced.
Changes: bounded exact-control observation with distinct screenshot names per poll; ordinary look behavior preserved. Research recommendations and the private verbatim Consensus report are saved.
Next: continue the actual create/edit journey after the pending desktop handoff. No generation or editor milestone is complete.
Refs: results/observation-until-20261110/report.md; results/suno-20261110/report.md; output/suno-20261110/checkout-until-advanced.txt; output/suno-20261110/checkout-until-present.txt

## SUNS1 · summary · 2026-11-10 16:36
Established: native control delivery navigated to the visible Create form; explicit process binding resolved concurrent Chrome selection; a bounded observation primitive was added, regression-tested and exercised read-only on live Chrome. Consensus and current primary-source research inform a staged workflow and candidate media stack.
Uncertain: underlying Chrome AX delay, stable creation-field access, actual song generation, audio audition, timeline editing, quality judgment and saved derivative persistence remain unverified. Human-active foreground refusal is an external prerequisite, not a product failure.
Decision: hand off the live run at Create while waiting for the user's desktop availability; preserve evidence and originals, with no release/install or claim of end-to-end readiness. Resume the notebook and run report before acting.
Refs: results/suno-20261110/report.md; docs/suno-workflow.md; docs/experiments/suno-end-to-end-20261110.md

## SUNU3 · update · 2026-11-10 16:45
Observed: the user supplied two additional research documents. Primary Suno sources verify the October28 official MCP beta and documented WAV exports and take lanes; primary Qwen repositories verify MM Plugins and Live Harness. No Suno/Qwen capability is exposed in this chat's callable tool inventory. No new live mutation, account connection, install or test run occurred.
Changes: docs/suno-workflow.md now prioritizes exported audio, lists the official service as a separate supporting route, adds Qwen adapter candidates, explicit review coverage and negative controls, and retains detector false-positive/sampling limits. Other-repository implementation claims and unverified numerical rankings in the documents were not adopted.
Next: preserve the pending live desktop handoff; continue the requested Footwork creation/editor journey when available. Actual listening and editor completion remain unverified.
Refs: docs/suno-workflow.md supplement; https://help.suno.com/en/articles/14551361; https://help.suno.com/en/articles/8128193; https://help.suno.com/en/articles/13670913; https://github.com/QwenLM/Qwen-MM-Plugins; https://github.com/QwenLM/Qwen-Live-Harness

## SUNU4 · update · 2026-11-10 16:51
Observed: the user selected existing Softtrigr YouTube songs as reference material and qwen/qwen3.8-omni-flash via OpenRouter as the reviewer. A fresh native look found the selected window now showing the Softtrigr channel, including18 video titles; no song audio has been reviewed. A new local jevdual/.env was created with an empty OPENROUTER_API_KEY entry, mode0600, and confirmed Git-ignored. The user was prompted to enter the value locally; no credential was received in chat or printed.
Changes: pin the selected reviewer/provider and musical source in the workflow. Treat actual audio/video qualification as a prerequisite to sonic claims. Do not substitute another model silently.
Next: await local key entry, qualify selected-provider media input, review representative channel songs, then create and edit run-owned tests through Footwork. The current window must be reobserved before any resumed Suno input.
Refs: docs/suno-workflow.md; output/suno-20261110/resume-look.txt; https://openrouter.ai/qwen/qwen3.8-omni-flash/llms.txt

## SUN5 · prediction · 2026-11-10 16:55
Hypothesis: the selected OpenRouter Qwen route consumes actual WAV bytes and distinguishes a known tone sequence from a silent negative control using an identical neutral prompt.
Test: on the committed media adapter, submit the two preregistered ten-second fixtures, then inspect semantic content and coarse timing against their known construction. Use at most500 output tokens per probe and no retry/fallback.
Predicts: two equal low tones then one longer high tone for the signal fixture, and silence for the negative control, without invented speech or music.
Against: unsupported input, empty or generic identical output, invented content for silence, or failure to identify relative pitch/order. Success does not establish musical taste or all video input.
Refs: docs/experiments/openrouter-media-live-20261110.md
