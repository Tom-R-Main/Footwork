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
