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

## SUNU5 · update · 2026-11-10 16:59
Observed: the user confirmed local key entry and approved project-only yt-dlp installation. The existing project environment now has yt-dlp2026.10.26 and its default dependencies (certifi updated to2026.10.23); no global install or project lockfile change. Three user-owned uploads were retrieved as full MP3 references and ffprobe-checked: Te Trago, Cleanup Complete and Encore, Silence. Foregrounding the observed YouTube window through its Window menu restored current AX controls. Selecting an observed Suno tab exposed current Lyrics editor, Styles and title inputs. Two initial OpenRouter probe attempts failed with generic transport errors; an independent public metadata request in the same interpreter demonstrates missing CA roots (SSLCertVerificationError20), not bad credentials or perception failure.
Inferred: source identity and actual media bytes are established for three references; sonic characteristics remain unreviewed. The installed runtime can operate the selected foreground tab, with stale AX behavior still needing explicit readiness checks. TLS transport must be repaired without disabling verification before any probe retry.
Next: fix and qualify TLS context, then rerun the preregistered audio controls on fresh output directories before reference reviews. Preserve failed intent records; no song generation submitted yet.
Refs: output/suno-20261110/reference-audio/manifest.json; output/suno-20261110/reference-show-window.txt; output/suno-20261110/drafts-select-suno.txt; output/suno-20261110/probe-a-review/manifest.json; output/suno-20261110/probe-b-review/manifest.json

## SUNU6 · update · 2026-11-10 17:03
Resolves: SUN5 = held
Observed: on TLS repair e3eaecb, both WAV requests returned the selected Qwen model from Alibaba. Probe A was described as three isolated tones, two equal low tones followed by one longer high tone; probe B as silence. Timing estimates were inaccurate: A was reported near1–3,4–6,7–10 seconds versus actual2–3,4–5,6–8. OpenRouter usage reports audio_tokens0 despite the supplied input_audio and discrimination result; do not interpret this accounting field as direct perceptual coverage. Both responses and hashes are retained. The combined reported cost was0.00042524 dollars.
Inferred: the bounded actual-audio discrimination mechanism holds; timestamp precision and musical taste are not established. Reference observations must retain uncertainty, and exact edit times require DSP/editor evidence.
Changes: verified request-local CA trust without global changes; native enter trailing text is now refused in source a1aae82 rather than accepted and ignored. The original failed TLS attempts remain preserved and were not treated as provider/media failures.
Next: three full-reference audio reviews are running under the initial paid-request budget. Use their qualified sonic findings for a new original test brief; then enter inputs with fresh numeric targets where field/header names collide.
Refs: output/suno-20261110/probe-a-tls-review/response.json; output/suno-20261110/probe-b-tls-review/response.json; results/openrouter-media-review-20261110/report.md; results/native-enter-arity-20261110/report.md

## SUNU7 · update · 2026-11-10 17:04
Observed: all three full-MP3 reference reviews returned the pinned Qwen model from Alibaba with stop finish reasons. They describe intimate breathy delivery and negative space across the references, Spanish guitar/sub-bass atmosphere in Te Trago, sparse piano/English AI narrative in Cleanup Complete, and bilingual French/English electronic house texture in Encore, Silence. These are delegated model observations, not human acceptance. References cost0.00410187 dollars combined; five successful paid requests including probes have now run. A run-owned original bilingual brief and lyrics were saved for Sous le signal, combining piano space with restrained house pulse. The Styles/header label collision required a numeric textbox target; a read of the empty field explicitly carried its label, not previous text, so it must not be used as a restoration value.
Next: type/read back the original inputs, submit one generation batch, identify resulting drafts, then open Song Editor for a deterministic ending edit. Retain model timing limitations and original/reference files.
Refs: output/suno-20261110/review-te-trago/response.json; output/suno-20261110/review-cleanup-complete/response.json; output/suno-20261110/review-encore-silence/response.json; output/suno-20261110/draft-brief/brief.json; output/suno-20261110/prior-styles-numeric.txt

## SUNU8 · update · 2026-11-10 17:11
Observed: Suno's short title read back exactly. The initial485-character Styles insertion exceeded the480-character preview cap; source diagnosis confirmed a receipt wrongly treated truncation as unequal content. A later400-character Styles revision remained the old preview even after fresh observations and foregrounding; this is a distinct unresolved input effect. A461-character first insertion into Lyrics editor returned suspected_noop and its field now exposes x while the rendered editor appears blank. No Create action was submitted. A source repair for bounded-preview receipt metadata is underway, and a separate read-only diagnosis is investigating rich-text delivery. The intended original text remains in the run-owned brief.
Inferred: input delivery is not qualified for Suno's rich editor. Do not generate with the unverified lyric state or report the short Styles revision as applied. Label collisions and source-preview limits require stronger selection/readback semantics rather than accepting command exit0.
Next: resolve the rich-text input mechanism, re-drive the failed path with exact short text, then generate. Independent reference loudness/peak measurements supplement, rather than certify, model technical judgments.
Refs: output/suno-20261110/drafts-type-title.txt; output/suno-20261110/drafts-type-styles.txt; output/suno-20261110/drafts-short-styles.txt; output/suno-20261110/drafts-type-lyrics.txt; output/suno-20261110/drafts-before-create.txt; output/suno-20261110/drafts/screenshots/obs-010-1794348503.png

## SUN9 · prediction · 2026-11-10 17:13
Hypothesis: the Lyrics editor delivery failure is specific to multiline or accented text rather than all replacements in its rich-text surface.
Test: on the frozen checkout, reobserve the run-owned Lyrics editor holding x, replace it once with the short ASCII diagnostic signal, then read back. No generation is authorized with diagnostic text.
Predicts: signal reads back exactly and the long-text failure remains isolated to more complex input.
Against: the field remains x, becomes another value, or dispatch refuses before entering text. This would rule out multiline/Unicode as a sufficient explanation.
Refs: output/suno-20261110/drafts-type-lyrics.txt; output/suno-20261110/drafts-before-create.txt

## SUNU9 · update · 2026-11-10 17:14
Resolves: SUN9 = failed
Observed: the short ASCII replacement signal also returned an unverifiable driver effect and suspected-no-op receipt; Lyrics editor still exposed x. The repaired source correctly marks the unrelated long Styles preview as truncated. No generation was submitted.
Inferred: multiline/Unicode input is not a sufficient explanation. Replacement selection versus general rich-text delivery remains unresolved.
Next: one append diagnostic to separate replacement selection from input delivery, then use source diagnosis rather than repeating the same failed replacement.
Refs: output/suno-20261110/lyrics-ascii-diagnostic.txt

## SUN10 · prediction · 2026-11-10 17:14
Hypothesis: replacement selection fails in the rich Lyrics editor while appending can still deliver ordinary text.
Test: from a fresh observation of the run-owned field, append the ASCII diagnostic word signal once and read back; no generation with diagnostic text.
Predicts: xsignal (or x followed by a separator and signal) appears, distinguishing insertion from failed replacement.
Against: x remains, a different value appears, or dispatch refuses; this leaves general rich-text delivery/focus as the stronger hypothesis.
Refs: output/suno-20261110/lyrics-ascii-diagnostic.txt

## SUNU10 · update · 2026-11-10 17:17
Resolves: SUN10 = failed
Observed: append signal returned partial/content_mismatch and an unverifiable receipt. Its post-observation and a subsequent read-only observation still showed x in Lyrics editor; no generation occurred. Native preview repair51955f0 passed328 affected and296 adjacent tests and now reports bounded evidence honestly. Source diagnosis found _type_web hard-codes background delivery even when foreground is permitted; no origin for literal x was established.
Inferred: replacement selection alone does not explain the rich-text failure. The attempted append's historical delivery remains uncertain; do not repeat it to obtain a cleaner receipt. A different explicit guarded foreground route is the next testable mechanism, not an automatic retry/fallback.
Next: implement and freeze the opt-in foreground web-text route, then test a short run-owned diagnostic with actual rendered and exact readback evidence before intended lyrics.
Refs: output/suno-20261110/lyrics-append-diagnostic.txt; output/suno-20261110/lyrics-append-readback.txt; results/bounded-field-receipts-20261110/report.md; python/jevdual/native.py _type_web

## SUN11 · prediction · 2026-11-10 17:17
Hypothesis: explicit foreground web-text delivery, using Footwork's existing idle/window/identity gates, reaches the visible Suno rich-text editor where the background route failed.
Test: after the source route is committed and offline regressions pass, reobserve the run-owned Lyrics editor, enter one short ASCII diagnostic through the explicit foreground route, and inspect exact field readback plus the rendered editor. If held, replace with the intended short original lyrics and verify before generation. No fallback after uncertain input.
Predicts: the visible editor and bound text value both contain the requested diagnostic; subsequent intended lyrics agree in readback and rendering.
Against: only AX value changes while rendered editor stays blank, wrong window/field receives input, guards refuse, or content remains x. A refusal is not evidence that the permitted route works.
Refs: output/suno-20261110/lyrics-ascii-diagnostic.txt; output/suno-20261110/lyrics-append-diagnostic.txt

## SUN12 · prediction · 2026-11-10 17:23
Hypothesis: the selected Qwen OpenRouter route can reason over actual MP4 visual and audio content at a coarse temporal level, while brief-defect detection remains limited.
Test: supply the amended ten-second controlled video with a neutral prompt. Compare reported macro color change, direction of square movement and tone pattern against the generated source; separately record whether the known freeze and single-frame flash are noticed.
Predicts: blue then green background, white-square rightward movement and isolated tones are identified; missing the single-frame flash would limit fine temporal/jank claims rather than prove no video was perceived.
Against: missing or reversed macro sequence, generic unrelated video description, invented speech or silent-only interpretation. Provider errors are unverified capability, not a content judgment.
Refs: docs/experiments/openrouter-media-live-20261110.md amendment

## SUNU12 · update · 2026-11-10 17:30
Resolves: SUN12 = failed
Observed: the MP4 probe returned the pinned Qwen/Alibaba response with correct blue-to-green macro order and rightward white-square motion. It missed the known single-frame black flash and one-second freeze, described continuous smooth motion, could not confirm the embedded tones, and estimated coordinates outside the320px frame. FFmpeg independently detected black4.400–4.433333s, freeze5.966667–7.000s, and non-silent audio near2–3,4–5,6–8s in the same encoded file. The response arrived after several minutes despite a120s configured socket timeout, before parent termination; no process was killed or call repeated. Usage reports32300 completion tokens with31982 reasoning despite max_tokens1500, cost0.01531165 dollars.
Inferred: coarse visual perception holds but the preregistered combined audio/video criterion fails; fine-defect and exact-spatial judgments are not qualified. The response does not identify whether embedded audio was dropped or simply unattended. Source transport deadlines and reasoning controls need explicit qualification.
Changes: six successful paid calls now total0.01983876 dollars by provider accounting. A total-deadline repair is in progress independently of the native driver rebuild; no automatic retry. The source native field-focus fix reproduced three failing Rust cases before repair and is being tested offline.
Next: bound future requests and test separate audio alongside video only as a new protocol probe if needed; prioritize the Suno foreground typing recovery after the native contract is frozen.
Refs: results/suno-20261110/video-calibration.md; output/suno-20261110/video-probe-review/response.json; output/suno-20261110/audio-probes/video-defect-detection.txt; output/suno-20261110/audio-probes/video-audio-detection.txt

## SUN13 · prediction · 2026-11-10 17:35
Hypothesis: supplying the known audio as a separate input_audio part alongside MP4 resolves this route's unconfirmed embedded-audio result, and explicit reasoning.enabled=false prevents reported reasoning expansion.
Test: on frozen helper72bd20b, submit the same controlled MP4 plus its original time-aligned probe-A WAV as a sidecar, with a neutral joint-review prompt, requested500 completion tokens and60s total exchange deadline. This is a new multimodal payload, not a retry of the prior video request.
Predicts: the response identifies the blue-to-green square scene and the three-tone two-low/one-high pattern; reported reasoning_tokens is zero and the call returns within its total deadline. Missing flash/freeze still limits jank claims.
Against: audio remains unconfirmed, the macro scene or tone sequence is wrong, reasoning disable is not honored/unknown, or the transport deadline expires. No automatic retry or model fallback.
Refs: docs/experiments/openrouter-media-live-20261110.md amendment; output/suno-20261110/video-probe-review/response.json; results/openrouter-media-review-20261110/report.md
