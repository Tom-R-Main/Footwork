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

## SUNU13 · update · 2026-11-10 17:37
Resolves: SUN13 = inconclusive
Observed: joint MP4 plus explicit WAV sidecar returned the correct blue-to-green square scene and two short beeps followed by one sustained tone. Relative pitch was not reported, so the full predicted two-low/one-high account was not established in this joint probe. Timestamps again overran the source (video to12s despite a10s file), the square was incorrectly described as leaving the frame, and flash/freeze were missed. Reasoning disable was reported honored: zero reasoning tokens,137 completion tokens, cost0.00020179 dollars, returned within60s. The helper records both media hashes and unknown vendor inspection coverage.
Inferred: separate audio restores an audible-events account in the joint route and explicit reasoning control works on this request; precise temporal/spatial and fine-defect judgments remain unqualified. This is not a controlled latency comparison because both payload and settings changed.
Changes: helper72bd20b adds explicit reasoning settings, sidecar evidence and budget-report fields, with61 affected tests passed; total-deadline fix8f1e3b3 has45 tests. Seven successful paid requests now report0.02004055 dollars combined. One request remains in the amended package for edited-song review; no additional media probe is needed now.
Next: continue the foreground Suno input qualification after the patched native package is frozen. Use direct audio and measured edit boundaries; do not rely on model timestamps or smoothness claims.
Refs: output/suno-20261110/joint-probe-review/response.json; output/suno-20261110/joint-probe-review/manifest.json; results/openrouter-media-review-20261110/report.md; results/suno-20261110/video-calibration.md

## SUNU14 · update · 2026-11-10 17:39
Observed: the driver source patch now verifies addressed-field focus inside the existing exact-window foreground guard before synthesis, with explicit foreground/background separation. It reproduced three failed focus cases before repair and passes33 focused Rust tests;407 affected Python/build-provenance checks pass. The new exact custom pin is0.46.0+footwork.5486b624.cleanup2.focus1. Its SDK/CLI is being rebuilt offline against the verified source archive in the existing cache, with a project-local overlay planned; no global release replacement or live foreground text call has occurred.
Inferred: fixture and source-contract evidence supports the new refusal boundary, not live Suno input readiness. The explicit option is type-only; append remains unsupported rather than reconstructing a value from a preview.
Next: verify overlay import/ABI and frozen source, run full default offline checks, then SUN11 short diagnostic plus actual rendered/readback evidence. Do not invoke the new option on the older installed runtime.
Refs: output/foreground-web-text/rust-red.txt; output/foreground-web-text/rust-green-final.txt; output/foreground-web-text/python-affected.txt; python/jevdual/native.py FOREGROUND_WEB_TEXT_CUA_VERSION

## SUNU15 · update · 2026-11-10 17:52
Observed: source a516212 and the project-local focus1 wheel are frozen. Independent review's two blockers were reproduced and fixed: unreadable field values now refuse before text selection, and strict foreground typing uses positive pacing to disable the SDK batched-tail resend. The narrow independent re-review reports both resolved;84 overlay contracts and33 Rust focus checks pass. Root full default offline suite is running. A read-only live refresh found the bound window on YouTube, with the existing Create Suno tab still visible beside it. One observed Select Previous Tab menu request refused as human_active before input; no new foreground text or generation was sent.
Inferred: source and contract readiness is distinct from desktop availability and live rich-text success. SUN11 remains open because its typing test has not run.
Next: finish the broad regression check and wait for the requested idle-desktop handoff, then refresh Suno and perform SUN11 without bypassing the guard.
Refs: results/foreground-web-text-20261110/report.md; output/suno-20261110/full-offline-pytest.txt; output/suno-20261110/foreground-repair-preflight.txt; output/suno-20261110/foreground-repair-select-suno.txt

## SUNU16 · update · 2026-11-10 17:54
Observed: the full default offline suite on a516212 with the qualified focus1 overlay exited0:3098 passed,62 skipped in261.07s. No browser/live opt-in flags were enabled. The independent re-review found both original source blockers resolved. No further source edits or native rebuilds followed this check. The idle-desktop handoff is still pending; SUN11 typing has not run.
Inferred: broad offline regression readiness holds for this frozen runtime, while live rich-text delivery remains unverified.
Next: on the requested ready handoff, refresh the existing Suno tab and run the preregistered diagnostic followed by intended content only if verified.
Refs: results/suno-20261110/offline-suite.json; output/suno-20261110/full-offline-pytest.txt; results/foreground-web-text-20261110/runtime.json

## SUNU17 · update · 2026-11-10 18:05
Resolves: SUN11 = failed
Observed: the user supplied the ready handoff. The former bound window no longer contained Suno; a fresh session bound the observed Create Suno window306787 in the same Chrome process24992. On frozen a516212/focus1, foreground Lyrics editor replacement signal ended unverifiable with AttributeError: tuple has no attribute location. Its post-observation and independent read both retain x; the rendered editor still appears blank. No generation was submitted. Source diagnosis places the error in AX selected-range decoding after possible Select All and before type_text; the historical command receipt remains unknown rather than rewritten.
Inferred: the mock/contract suites missed a real PyObjC representation variant. The addressed-field selection decoder must accept the actual validated tuple form in addition to CFRange objects before this route can qualify. No new SDK build is required.
Next: repair the owning decoder with red-before-green public CLI coverage, freeze the source and run affected checks. Reobserve and run a new-version diagnostic only after the text boundary is known not to have been reached.
Refs: output/suno-20261110/ready-drafts-start.txt; output/suno-20261110/foreground-lyrics-signal.txt; output/suno-20261110/foreground-lyrics-signal-readback.txt; python/jevdual/ax.py selected_range

## SUN14 · prediction · 2026-11-10 18:05
Hypothesis: the actual native selected-range tuple is the remaining pre-text failure on this guarded foreground path.
Test: after the owning decoder repair is frozen and affected regression/ABI checks pass, obtain a fresh Suno observation and replace the run-owned Lyrics field with the short diagnostic signal; inspect the rendered field and exact readback. If verified, replace it with intended original lyrics and verify before any generation. Keep the prior unknown selection receipt intact.
Predicts: tuple decoding validates the full selected range, exactly one foreground text call is reached, and both actual rendering and field readback show signal. Intended lyrics subsequently agree in visible and exact value evidence.
Against: decoder refuses, another pre-text guard fails, synthesis remains unverifiable or content changes only in AX while the rendered editor stays blank.
Refs: output/suno-20261110/foreground-lyrics-signal.txt; results/foreground-web-text-20261110/report.md

## SUNU18 · update · 2026-11-10 18:08
Resolves: SUN14 = failed
Observed: decoder repair be8ea6b passed338 focused checks with unchanged native bytes. The new live foreground diagnostic no longer raises AttributeError; it stops with selection_unqualified because the exact field/value is not wholly selected. This check precedes text synthesis in the frozen path. The command receipt remains unverifiable because preparation/selection may have occurred. No new song generation was sent.
Inferred: the selection guard is now functioning; the current field's AX x versus blank rendering is not a sound replacement precondition. Do not weaken the selection check or repeat the same input.
Next: use the actual observed New draft control to reset only run-owned lyrics, then independently verify fresh empty value and rendering before testing insertion without replacement selection.
Refs: results/selected-range-decoding-20261110/report.md; output/suno-20261110/tuple-repair-preflight.txt; output/suno-20261110/tuple-repair-lyrics-signal.txt

## SUN15 · prediction · 2026-11-10 18:08
Hypothesis: Suno's New draft control resets the inconsistent run-owned lyrics state to a fresh readable empty editor that the guarded foreground insertion route can reach.
Test: reobserve and click New draft once; inspect exact Lyrics editor value and screenshot. Only if empty, type the short diagnostic signal through the frozen guarded foreground path and require exact readback plus visible text. If verified, replace with intended original lyrics and revalidate style/title before generation.
Predicts: New draft yields an empty lyrics field without editing an existing song; foreground insertion then visibly renders signal and exact readback agrees.
Against: the control opens a different flow, emptiness cannot be established, a guard refuses, or AX and rendering diverge again. Do not submit generation or force a replacement in these states.
Refs: output/suno-20261110/ready-drafts-start.txt; output/suno-20261110/tuple-repair-lyrics-signal.txt

## SUNU19 · update · 2026-11-10 18:11
Resolves: SUN15 = failed
Observed: New draft changed the lyrics to Suno's empty placeholder and0of5000 character counter, cleared the test title and preserved the style. The observed Auto-save onboarding was dismissed with Got it. The subsequent foreground diagnostic still stops at selection_unqualified before text synthesis; post-observation still shows the empty placeholder and0counter. No generation occurred.
Inferred: visual emptiness and the adapter's raw value/selection precondition disagree. A fresh draft alone does not resolve the mechanism. The guard remains intact; no further typing will be attempted until exact read-only SDK/direct-AX evidence identifies the disagreement.
Next: delegate one read-only inspection of the exact field's raw value, character count, range and code points, without focus writes or input. Preregister any ensuing source repair separately.
Refs: output/suno-20261110/new-lyrics-draft.txt; output/suno-20261110/new-draft-dismiss-onboarding.txt; output/suno-20261110/fresh-lyrics-signal.txt

## SUNU20 · update · 2026-11-10 18:13
Observed: a bounded read-only field probe found SDK value None but direct AXValue exactly one U+000A newline; AXNumberOfCharacters1 and selected range0,0. Fresh role/frame/title/description matched the intended Lyrics editor in window306787. No focus writes or input were performed. The adapter's supplemental exact value is truthy, so replacement expects a one-unit selection while Suno's empty editor remains at zero selection.
Inferred: the disagreement is a terminal-newline representation, not arbitrary invisible text. These facts alone do not establish that the newline is structural or safely excluded from replacement selection. No whitespace stripping or guard change is authorized by this diagnosis alone.
Next: inspect independent parameterized text/range attributes as a bounded read-only exploration before proposing any repair.
Refs: output/suno-20261110/lyrics-range-observation.json; output/suno-20261110/fresh-lyrics-signal.txt

## SUN16 · exploratory · 2026-11-10 18:13
Question: does the actual Lyrics editor expose an independent selectable-text boundary that distinguishes a structural terminal newline from ordinary text excluded by failed Select All?
Test: one bounded read-only probe of the same freshly resolved field: supported parameterized AX attributes, AXSelectedText, AXStringForRange for0,1 and0,0, plus AXRangeForLine0 or AXRangeForIndex0 when supported. No clicks, key events or focus writes. Retain exact strings and ranges; unsupported attributes are missing evidence, not empty values.
Refs: output/suno-20261110/lyrics-range-observation.json; python/jevdual/ax.py

## SUNU21 · update · 2026-11-10 18:16
Observed: the second bounded read-only probe confirms AXStringForRange0,1 returns LF, AXRangeForLine0 includes it, AXRangeForIndex0 is0,0, visible range0,1 and selected text empty. No input occurred. These APIs do not independently prove that excluding a terminal LF is valid whole-field replacement.
Inferred: a whitespace exception would assume more than the evidence. Explicit selected-range editing can instead preserve the exact unselected prefix/suffix and verify the requested edit without changing full-field replacement semantics. This capability is delegated as a separate preregistered source package.
Next: move the core creation/editor journey forward with an instrumental, using the observed empty-lyrics convention and ordinary Styles/title fields on frozen be8ea6b, isolated from concurrent source edits. The user's task does not require lyrics for the first song; original vocal draft remains available for the later range-edit test.
Refs: output/suno-20261110/lyrics-parameterized-observation.json; output/suno-20261110/new-draft-dismiss-onboarding.txt

## SUN17 · prediction · 2026-11-10 18:16
Hypothesis: ordinary Styles and title controls accept guarded full-field foreground replacement, allowing creation of a private reference-grounded instrumental while rich-text range editing is repaired separately.
Test: on an exact project-local snapshot of be8ea6b and unchanged focus1 overlay, collapse the observed Lyrics panel, enter a short instrumental style and unique title, verify actual field values and rendering plus Suno's zero-lyrics counter, then submit Create song once. Reconcile generated identities and ready state without uncertain submission retries.
Predicts: intended style/title are present, lyrics remain visually empty, one submission produces identifiable new private instrumental candidates, and existing songs remain untouched.
Against: guards refuse, content is missing/truncated or mismatched, lyrics are not empty, Create delivery is unknown without reconcilable new candidates, or account/plan prerequisite prevents generation.
Refs: docs/experiments/suno-end-to-end-20261110.md; results/suno-20261110/reference-analysis.md

## SUNU22 · update · 2026-11-10 18:18
Observed: the instrumental style replacement on the isolated frozen runtime refused human_active before preparation or text. Five one-second passive HID idle readings were0.00to0.02seconds, so no continuous three-second idle interval was observed despite the earlier user-ready handoff. Styles remain unchanged and no generation occurred.
Inferred: desktop availability is again a separate blocker; continuous HID events may come from human use or other automation. No source/posture change or retry has occurred.
Next: inspect bounded passive event-type idle counters and cursor positions to identify the resetting event stream; ask for a precise external handoff only if needed.
Refs: output/suno-20261110/instrumental-type-styles.txt; python/jevdual/posture.py MacActivity

## SUN18 · exploratory · 2026-11-10 18:18
Question: which HID event category is continuously resetting the foreground-permitted idle counter after the user's ready handoff?
Test: read Quartz idle seconds for any input, mouse movement, keyboard down/up, button down, scroll and flags, plus cursor position, five times at one-second intervals. No event taps, key contents, clicks, pointer movement, focus writes or other input; retain only numeric counters and coordinates in private output.
Refs: python/jevdual/posture.py MacActivity

## SUNU23 · update · 2026-11-10 18:23
Observed: the bounded passive HID probe subsequently showed36to40seconds idle with stable cursor; the activity had cleared without a policy change. A fresh observation preceded the previously refused style request; foreground typing then confirmed the396-character instrumental style and unique title. After verified zero lyric characters, one Create song click produced two new candidates, visible durations3:35and3:25 and a Publish clip control for the first. Control-specific waiting observed a Play button. Opening first title by ID157 was then refused target_ambiguous before dispatch because both generated rows share a title/section, including a peer omitted from the compact menu.
Inferred: generation submission and new candidates are established; complete audio and exact resource identities remain to be retrieved. Duration missed the90to120second brief. Duplicate labels are a separate native resource-identity gap, not grounds to force the click.
Next: inspect exact AXURL attributes of only the two owned generated links; qualify unique resource navigation from observed URLs and repair native link identity separately.
Refs: output/suno-20261110/hid-availability.json; output/suno-20261110/instrumental-type-styles-idle.txt; output/suno-20261110/instrumental-type-title.txt; output/suno-20261110/instrumental-create-once.txt; output/suno-20261110/instrumental-candidates-ready.txt; output/suno-20261110/instrumental-open-candidate-a.txt

## SUN19 · exploratory · 2026-11-10 18:23
Question: do the two newly generated same-title song links expose distinct actual AXURL resource identities that Footwork's native menu currently omits?
Test: one bounded read-only SDK snapshot scoped to the exact test title in bound window306787; resolve each matching AXLink by its fresh frame, independently verify title/description and read AXURL. Save resource URLs with snapshot/frame provenance. No clicks, focus writes or navigation. If absent or invalid, do not invent song IDs.
Refs: output/suno-20261110/instrumental-open-candidate-a.txt; python/jevdual/native.py Candidate projection
