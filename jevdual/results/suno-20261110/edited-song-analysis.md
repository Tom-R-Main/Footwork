# Actual ending-fade verification

The bounded legacy-editor creation/export/fade/save/Library-reopen journey is verified. The first exported ending shows progressive attenuation over the requested final eight seconds. A further public-command pass created, exported and reopened a separate four-second fade from the same original. This does not establish bit-exact preservation, aesthetic improvement or human preference. The selected Qwen route failed the blinded ending-discrimination check.

Core UI work used frozen source `a64b6f2` with the existing project-local focus1 CUA overlay. Outcome commit `260a3ff` records SUN36 held; notebook updates SUNU47–51 retain the export, comparison, failed critic and Library/reload evidence. The additional pass used frozen `1cccdcb` and public commands throughout, without an implementation change, private SDK helper or user handoff; outcome `47054d4` records SUN38 held. Newer-editor popup qualification used `ca4e7dc`, with SUN39 held in `0d6c6d9`; it did not mutate or save the timeline. These sources are distinct from the first fade’s source.

## Files and intended edit

The source was the second run-owned instrumental from one Create submission. Through the product's observed Legacy Editor link, named FADE OUT mode exposed a readable From field. The operator set `03:16.80`, independently rechecked it and the selected ending, then applied Fade out once to the 204.8-second source. The intended fade interval is `[196.8, 204.8)` seconds. One distinct derivative was created, exported once through the authenticated owner route, and saved to a fresh project file. No original overwrite or publication occurred.

| Artifact | Duration | Bytes | SHA256 |
| --- | ---: | ---: | --- |
| `candidate-b.mp3` | 204.8 s | 4,639,077 | `138821e47c9a2e68c267942e308f3b055aa932cde5a031d0aae2df4d6d63d349` |
| `candidate-b-fade-8s.mp3` | 204.8 s | 4,693,331 | `9a02e024eb44a7b2caa8864a545b1db27a804b4539b6e06b71cb10bf1c5ae924` |
| `candidate-b-fade-4s-repeat.mp3` | 204.8 s | 4,703,603 | `070c687276937b71d67cbabe1840b4c4cf2666b5ee3e1719438f4cb0b749dc64` |

All three files are stereo 48kHz MP3, and all complete FFmpeg decode checks passed. Private validation manifests retain exact UI/file source identity; this report omits private song IDs. Library subsequently showed the derivative and both source candidates separately. Reopening the derivative through its actual Library link and then Reload retained the intended page/player identity and `3:24` display, consistent with the independently decoded 204.8-second file. Optional direct HTTP metadata reads returned 403 and stopped; they were not bypassed or used as success evidence.

## Signal comparison and limits

Diagnostic analysis downmixed/resampled the decoded files to 8kHz mono. Each had 1,638,400 samples. Independent alignment found zero lag; the diagnostic alignment correlation was 0.9982098. In the `[1,196)`-second prefix, correlation was 0.9984246 and derivative RMS was 0.30353dB lower. Independently hashed decoded float-PCM prefixes also differed. Earlier musical content is highly correlated, but sample identity and exact unaffected-region preservation are not established.

| Ending interval | Derivative RMS change relative to source |
| --- | ---: |
| 196.8–198.8 s | −0.45 dB |
| 198.8–200.8 s | −1.93 dB |
| 200.8–202.8 s | −5.57 dB |
| 202.8–204.8 s | −10.90 dB |

This progressive attenuation supports the requested ending fade. The analysis does not identify the cause of the broader small level change, prove full-band/stereo preservation, calibrate audible-difference thresholds, or decide whether the fade improves the music. The signal check and the saved-resource/reopen checks answer different requirements.

## Additional four-second pass

The original candidate B was selected through Library and reloaded to reconcile page/player identity. The menu’s Fade out opened a conditioned Create form, so the run-owned unsubmitted condition was cleared without generation. Public address-bar commands reopened the previously observed Legacy Editor URL. The From field retained `03:20.80` after blur and visual readback; one apply created a new derivative for `[200.8,204.8)` seconds.

The export used public PID-scoped window inventory to discover the Save sheet and, after Go to Folder, its untitled nested panel. Fresh exact bindings, destination/filename readback and one foreground Save preceded the independent file checks. A 15-second Save-label wait had expired; later inventory found the sheet, and Unlock was not repeated. All four resources, both originals and both derivatives, appeared separately in Library. Reopening the four-second derivative and Reload retained matching page/player identity, ID3 source binding and `3:24` duration.

The same 8kHz mono diagnostic produced 1,638,400 samples per file. Alignment again found zero lag, with correlation 0.9982002. Over the pre-fade `[1,200)`-second prefix, correlation was 0.9984056 and RMS was 0.27525dB lower. The three ending windows were:

| Interval | Four-second derivative RMS change relative to source |
| --- | ---: |
| 198.8–200.8 s, before fade | −0.24 dB |
| 200.8–202.8 s | −1.19 dB |
| 202.8–204.8 s | −5.27 dB |

These measurements support a distinct shorter fade, with the same full-band/stereo and preservation limits as the first comparison. No Qwen review or human preference decision was made for this derivative. One additional successful development pass does not estimate reliability or ease across ordinary variants.

The final `ca4e7dc` launcher also qualified one newer-editor clip-menu action: inspect the backed opaque target’s exact document, identity and visible frame, foreground-click once, observe Split/Create Section, then Escape. A frameless Hide Tips peer was not an action candidate. No newer-editor edit/save, direct visual FADE action or waveform drag was qualified. Its [offline suite](../opaque-named-peer-census-20261110/full-default.json) recorded 3339 passes and 62 skips; the [focused report](../opaque-named-peer-census-20261110/report.md) records 594 checks including 19 new cases. The user-local installed release remains unchanged.

## Blinded Qwen comparison

Two composite review files used the same ending interval `[180.8,204.8)` from each export, a two-second separator and no normalization, for 50 seconds total. One placed the faded ending first; the other reversed the order. Source order, hashes and intervals were retained privately and were not replaced by the model's interpretation of the input.

Both `qwen/qwen3.8-omni-flash` / Alibaba responses declined to distinguish the endings and asserted equivalent dynamics/no level difference. A no-preference answer could be valid; the unsupported identity assertions conflict with the measured signal difference. SUN37 therefore remains failed as a qualification of this route for the requested ending distinction. Agreement between the two outputs is not proof of correctness. Input segmentation, provider processing and model perceptual limits remain alternatives; this run establishes no cause.

A separate neutral full-derivative review described a complete natural ending and suggested shortening a repeated second-half passage. That is coarse model judgment, not a verified improvement or a precise cut instruction. No further critic call was made to tune the answer toward the known edit.

| Review | Reported OpenRouter cost | Reported reasoning tokens |
| --- | ---: | ---: |
| Faded ending first | $0.00023202 | 0 |
| Original ending first | $0.00019818 | 0 |
| Neutral full derivative | $0.00047252 | 0 |

All eleven successful requests in the amended media package report $0.02146825 combined. These are provider-reported OpenRouter charges, not all Suno, TypeSafe or project spending. Requests were independent, with no automatic retry or model/provider fallback. Requested token limits are not a hard financial cap.

## Evidence retained

Paths below are relative to `jevdual/`; private media and raw model outputs remain in ignored output:

- `output/suno-20261110/exports/{candidate-b.mp3,candidate-b-fade-8s.mp3,candidate-b-fade-4s-repeat.mp3}.validation.json`
- `output/suno-20261110/exports/fade-comparison.json` and `{original,fade}-prefix-196s.hash`
- `output/suno-20261110/exports/boundary-{fade,original}-first.manifest.json`
- `output/suno-20261110/review-boundary-{fade,original}-first/{manifest,response}.json`
- `output/suno-20261110/review-final-fade/{manifest,response}.json`
- `output/suno-20261110/{derivative-reopened-from-library,derivative-reopen-reload,derivative-reloaded-ready}.txt`
- `output/suno-20261110/exports/repeat-four-comparison.json`
- `output/suno-20261110/repeat-{four-second-apply-once,before-folder-inventory,folder-inventory,save-destination-confirmed,library-reopen,reopened-reload}.*`
- `docs/notebook/2026-11-10-suno-end-to-end.md`, SUN36–39 and SUNU47–55

The tested recipe and its separate new-editor limits are in [the workflow guide](../../docs/suno-workflow.md). The initial journey and additional public-command pass are verified, alongside the separate newer-editor popup. They do not establish a reliability rate, human musical preference or general Song Editor canvas editing.
