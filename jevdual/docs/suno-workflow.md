# Suno creation, editing and media judgment

Engineering recommendation, researched November 10, 2026. This is a development workflow and a capability roadmap, not a claim that Footwork has completed Suno editing.

User-selected reviewer: `qwen/qwen3.8-omni-flash` through OpenRouter, superseding the tentative provider shortlist below. The credential destination is the Git-ignored `jevdual/.env`, variable `OPENROUTER_API_KEY`; enter the key locally and never retain it in reports or requests logged to disk. The [canonical model guide](https://openrouter.ai/qwen/qwen3.8-omni-flash/llms.txt) documents the Chat Completions endpoint. Qualify actual audio/video input on the chosen provider before claiming musical perception: text completion alone does not establish it, and [video URL support varies by provider](https://openrouter.ai/docs/guides/overview/multimodal/videos).

User-selected musical grounding: the existing songs on [Softtrigr's YouTube channel](https://www.youtube.com/@Softtrigr). Review actual media before deriving sonic characteristics; titles, channel description and lyrics are supporting context. Create new test songs iterating from those references while preserving existing material.

## Current live evidence

One observed Create submission produced two run-owned, complete, unpublished instrumentals. Exact song-page metadata reports durations of 214.88 and 204.8 seconds; the requested 90–120-second duration was not achieved. This qualifies creation, not audition or editing. The later original French-English lyrics were entered into the run-owned creation form and independently verified exactly, but no vocal generation from that form has been submitted.

The first generated playback downloads were opaque `m4a-opus`/encoding 1.0.0 bytes that FFmpeg could not decode. Those bytes were not sent to the critic. Authenticated owner export has now resolved that blocker for candidate B: after MP3-only format selection and one included Unlock Download, explicitly bound native panels saved `candidate-b.mp3` into the project exports directory. The actual file has 4,639,077 bytes, duration 204.8 seconds and a complete error-free FFmpeg decode. The file hash is retained in the run evidence. Closing the Save sheet alone was not treated as proof, and the unlock was not repeated.

The chosen Qwen route reviewed actual audio from three reference songs, passed limited synthetic audio checks, and then reviewed the full decoded candidate B export once. The candidate review reports zero reasoning tokens and $0.00052498; eight successful paid requests report $0.02056553 combined. It describes a natural melodic ending and an overlong middle. Those are model judgments, not human preference acceptance or precise edit timestamps; candidate A has not been auditioned for an A/B choice. The video checks missed known short defects and did not establish reliable embedded-audio perception or precise localization; explicit audio sidecar input improved the audible-event account, not the fine-defect result. These are development observations, not a general accuracy or taste benchmark.

No bounded song-editor change, transition comparison or saved/reopened derivative is complete. Keep creation, field readback, model critique and editor persistence as separate milestones. Run evidence: [main report](../results/suno-20261110/report.md), [reference analysis](../results/suno-20261110/reference-analysis.md) and [video calibration](../results/suno-20261110/video-calibration.md).

## The useful sequence

| Milestone | Required evidence | Friction to solve before advancing |
| --- | --- | --- |
| 1. Bind the right signed-in surface | Exact Chrome process and selected Suno window; current screenshot and creation-specific controls | Multiple Chrome processes; background accessibility can lag behind visible navigation |
| 2. Create one owned draft | Prompt/settings readback, one submission, generated song identity and ready state | Duplicate Create controls, delayed generation, uncertain submission, generation-credit budget |
| 3. Audition and select | Actual audio for each candidate, timestamps, short comparison against the brief | A playing icon or waveform cannot establish what the agent heard |
| 4. Make one deterministic editor change | Open Song Editor, observe original duration, add an ending fade or crop, preview changed duration/boundary | Waveform geometry, zoom, playhead position, unlabeled handles, undo |
| 5. Make one generative section change | Original song retained, exact selected interval, requested change, generated alternatives and chosen edit | Selecting the wrong section; changing surrounding content; unverified transitions |
| 6. Check the joins | Before/after audio spanning each boundary, plus a whole-song context pass | Clicks, silence, abrupt timbre/loudness/tempo changes, unintended lyric or musical changes |
| 7. Save and reopen | New song identity, saved derivative, reopened editor state and playable output | Delivery of Save is distinct from persistence; title changes alone prove little |

For a fresh generic qualification, an instrumental and a fade isolate control failures from lyric alignment and stochastic regeneration. This run has created the instrumental batch, separately verified the original French-English lyric field and obtained/reviewed actual candidate B audio. Next make and verify a bounded editor change. Test lyric/section replacement and Studio/stems separately: a successful Song Editor journey does not qualify a different editor.

Suno documents section replacement, alternative previews, draggable transition boundaries, fades and section rearrangement in its [Song Editor guide](https://help.suno.com/en/articles/6141505). Discover the current UI each time; do not assume that the historical guide describes every current account or plan.

Proposed ease criterion: after setup, one natural-language brief reaches a saved, reopened derivative with no user assistance for ordinary controls; an interrupted run resumes without submitting generation twice; evidence explains every edit. Repeat on fresh owned drafts before calling it reliable. This criterion has not been measured.

## Give the agent a timeline it can inspect

Use three complementary observations:

1. **Structured state:** selected resource, duration, playhead, zoom, selected interval, section/track identifiers, prompt/settings, generation status and save state, where the actual UI exposes them. Record unknown fields as unknown.
2. **Rendered evidence:** the current screenshot for buttons/handles, and a short recording around the action for movement, transitions and UI responsiveness.
3. **Sound:** the generated media or a bounded capture of the intended app's playback, with verified non-silent audio. Retain the mapping between song time and recording time. A silent screen recording cannot evaluate a song.

An evidence manifest should link action ID, monotonic capture timestamps, song ID, media hashes, playback interval, screenshot/frame timestamps, audio track and capture gaps. Seeking, buffering, pauses and capture latency make wall-clock time different from song time. Report uncertainty rather than assuming synchronization. Keep recordings limited to the selected app/window.

For long media, first inspect coarse structure, then request short, dense excerpts around uncertain edits. For a visual glitch, inspect adjacent frames; for a music join, listen to several seconds before and after the boundary. Inspect the final rendered/exported output in addition to editor preview. These are engineering recommendations, not universal sampling thresholds.

## Judge defects and taste separately

| Question | Suitable evidence/check | What it does not establish |
| --- | --- | --- |
| Did the command reach the intended control? | Fresh target binding and action receipt | That the edit sounds right or was saved |
| Did the intended interval change? | Editor state plus before/after playback and duration | Preservation of every other sample after generative re-encoding |
| Is there an obvious technical defect? | Decode/duration checks, loudness/silence/clipping analysis, boundary audition | Whether a sparse passage or distortion was intentional |
| Is the UI janky? | Action-to-paint timing, frame pacing, input latency and performance trace | Whether the resulting music is compelling |
| Is the song/edit good? | Equal-loudness A/B excerpts, full context, explicit brief and user preference | An objective universal aesthetic score |

Ask a critic for timestamped observations, severity, confidence, evidence and one proposed edit. Use criteria such as groove, melodic phrasing, section contrast, lyric intelligibility, timbral consistency and ending. Allow “cannot tell.” Compare A/B candidates without revealing which is newer. Keep a small set of the user's accepted/rejected examples; use those preferences to guide later choices.

[Fréchet Audio Distance](https://research.google/pubs/frechet-audio-distance-a-reference-free-metric-for-evaluating-music-enhancement-algorithms/) is research on perceived audio distortion. It is not a substitute for deciding which of two songs the user prefers. Likewise [VBench](https://github.com/Vchitect/VBench) provides separate visual quality dimensions such as flicker and motion; adapting those to a particular product recording requires validation. No generic scalar certifies musical or editorial craft.

## Components worth using

| Layer | Candidate | Why it fits | Current boundary |
| --- | --- | --- | --- |
| Guarded UI actions | Footwork native CLI | Existing signed-in Chrome, fresh targets, posture and receipts | Creation and one authenticated export verified; actual candidate B audio reviewed; A/B selection/editor/derivative persistence remain unverified |
| In-app semantic editing | [Suno Studio Chat](https://suno.com/blog/studio-chat-assistant) | Documented track naming, multi-fader changes, effects/parameter setup and feedback | Closed hosted assistant; no Studio Chat UI operation tested here, and documented examples do not qualify crop/fade control |
| Browser state and controls | [Playwright MCP/CLI](https://github.com/microsoft/playwright-mcp) | Structured snapshots and browser automation | Default owned profile does not inherit this user's login; the documented [extension route](https://github.com/microsoft/playwright/blob/main/packages/extension/README.md) supports existing tabs but requires setup and connection approval |
| Browser performance | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) | Diagnose browser behavior and performance | Requires an actual permitted connection; distinct from an audio critic |
| Capture | OBS + [obs-websocket](https://github.com/obsproject/obs-websocket) | Programmatic recording control | Screen and intended system/app audio must both be configured and checked; available MCP tools do not prove OBS is running or connected |
| Media mechanics | [FFmpeg](https://github.com/FFmpeg/FFmpeg), [librosa](https://github.com/librosa/librosa) | Clip/decode/probe media; derive audio and music features | Features support diagnosis, not taste; FFmpeg is installed. The user separately authorized project-only yt-dlp installation for reference acquisition |
| Hosted multimodal perception | [Gemini video](https://ai.google.dev/gemini-api/docs/video-understanding) and [audio](https://ai.google.dev/gemini-api/docs/audio) APIs | Direct audio/video input and timestamped questions | Provider documentation notes fixed-rate video sampling can miss rapid events; validate critical excerpts at suitable resolution. Gemini was not activated in this run |
| Open-weight multimodal perception | [Qwen3-Omni](https://github.com/QwenLM/Qwen3-Omni) | Text, images, audio and video in one model family | Benchmark against real Suno edits; assess model license and serving requirements before adoption |
| Open music specialist | [Music Flamingo / Audio Flamingo](https://github.com/nvidia/audio-flamingo) | Music/audio understanding and question answering | Candidate critic, not proof of expert taste or browser control; not installed or benchmarked here |
| Tool orchestration reference | [Microsoft MusicAgent](https://github.com/microsoft/muzic/tree/main/musicagent) | Existing pattern for routing music tasks to specialist tools | Historical research architecture; not a turnkey Suno driver |
| Source separation | [Demucs](https://github.com/facebookresearch/demucs) | Optional stem analysis when a mixed track hides an artifact | Upstream states it is no longer maintained; separation can introduce artifacts; prefer Suno's own available stems first |
| Video generation for a later workflow | [Runway API](https://docs.dev.runwayml.com/guides/using-the-api/) | Closed hosted generation with programmatic task completion | Generation endpoint does not supply creative evaluation or operate Suno's editor |
| Structural video editing | Installed Final Cut Pro MCP tool | FCPXML inspection/edit/preview interface is discoverable | Tool availability is observed; no timeline, server startup, render or live editing was tested |

MCP is a transport for tools. It supplies neither perception nor musical taste by itself. Expose bounded verbs such as observe, preview interval, inspect media, propose edit, apply one edit, undo and verify save. Keep one controller of a shared UI and carry evidence between controller and critic. Reuse CLI tools when their interface is already adequate; adding servers is not the first requirement.

## Priority for Footwork

1. Require a creation/editor-specific control after navigation; expose bounded waiting instead of making the operator repeat look manually. Preserve incomplete-observation warnings.
2. Keep exact process/window binding across the journey. Surface foreground refusal clearly; continue only when the human activity condition clears.
3. Add a scoped playback/capture evidence path with checked audio and timestamps. Prove the agent receives the intended sound using a known short fixture before evaluating Suno output.
4. Qualify interval selection, zoom, scrubbing and drag in the actual editor. Anchor coordinates to a fresh viewport; verify state and playback after each edit. Retain uncertainty when an operation may have landed.
5. Add an A/B review loop and saved-state readback, then exercise interrupt/restart and ordinary variants.

The first target is a narrow end-to-end journey with inspectable failures. General autonomous creative judgment is a later, separately evaluated capability.

## Recipes from the native Suno run

The current source behavior is frozen at `a64b6f2`, using the exact focus-guarded CUA `0.46.0+footwork.5486b624.cleanup2.focus1` through a project-local overlay. Its full default offline suite passed 3256 tests with 62 skips; see the [recorded suite result](../results/exact-window-start-20261110/full-default.json). The user-local installed release is unchanged. Establish the source/runtime from the run report before using the repaired commands; a passing source test is not an installed-release or live-editor qualification.

### Bind, wait and inspect

Use the observed PID and window rather than an app name alone when multiple Chrome processes exist. Keep one owner of the shared window and the foreground idle guard. Session start must use a new directory because it resets session files.

```sh
suno_fw=/absolute/footwork/jevdual/output/foreground-web-text/footwork
suno_session=/absolute/footwork/jevdual/output/NEW-suno-session
"$suno_fw" start "Create and edit only run-owned Suno drafts" --app "Google Chrome" --pid OBSERVED_PID --window "OBSERVED_WINDOW_TITLE" --mode foreground_permitted --session "$suno_session"
"$suno_fw" look --until "EXACT_CREATION_CONTROL_LABEL" --timeout 10 --session "$suno_session"
"$suno_fw" inspect-target OBSERVED_ID --operation click --postcondition "The own-song menu exposes Edit and Download" --session "$suno_session"
"$suno_fw" do click OBSERVED_ID --click-delivery foreground --session "$suno_session"
```

Placeholders are selected from fresh observations; do not reuse the IDs in old receipts. The wait proves an offered label appeared, not complete page readiness. Before the click, match the inspected bounds, document and control identity to the intended UI context. One generic More actions control in this run opened a comment emoji picker; it was dismissed without submitting a comment. A popup alone does not establish that the song menu opened.

Same-title native links now retain independently qualified complete hrefs; distinct buttons/popups can retain a complete DOM identifier scoped to their actual closest WebArea document. These qualify only the observed peer group and must survive fresh rematching. Choose a fresh numeric candidate when the label remains shared. Links do not lend identity to neighboring buttons, and unqualified duplicate Play controls still refuse. After internal song navigation, verify the player resource separately: the run observed a player retaining the previous song until Reload. Reload is appropriate only after checking that it will not discard unsaved work.

Sources: [link resources](../results/native-link-resources-20261110/report.md), [foreground click](../results/foreground-native-click-20261110/report.md) and [scoped control identity](../results/native-control-identity-20261110/report.md).

### Enter text without inventing a readback

`do type OBSERVED_FIELD_ID "TASK_OWNED_TEXT" --web-text-delivery foreground` explicitly selects the guarded foreground route; ordinary background behavior remains unchanged. It requires the exact supported runtime, foreground posture, fresh target/value checks and addressed-field focus. `enter` presses Return; it does not type a trailing argument. Never use diagnostic text in a field that might be submitted as a song.

For an already qualified selection, `--web-text-range START:LENGTH` uses UTF-16 units, not Python character counts. It does not select the requested region. The route performs bounded field-focus preparation, then independently requires the actual selection and exact text before one paced input. Preserve the full prefix/suffix; unreadable selection, terminal-LF mismatch or changed focus is a refusal, not permission to trim whitespace or retry.

The original lyric payload illustrates the readback limit: intended text had 461 characters/24LF, while AXValue reported 456/19LF and selected text 442/5LF. Those conflicting native serializations did not prove lost lyrics. A controlled verification-only Select All/Copy, bound to the owned focused field, advanced the clipboard change counter from 3537 to 3538. Only the new plaintext was read, and it matched the intended 461-character text exactly. No prior clipboard content was read, and no unmatched clipboard text was retained. The non-LF agreement used to qualify that copy's source was not an edit normalization rule; the final equality criterion included every LF and accent.

For a similar copy verification, establish source ownership and actual focus, observe Select All, record only the clipboard counter, invoke the observed Copy once, and compare new plaintext only after the counter advances. Store equality/provenance, not unrelated clipboard content. If provenance or exact equality fails, stop and retain uncertainty. This is an independent content check, not a generic whole-task completion mechanism.

Sources: [foreground web text](../results/foreground-web-text-20261110/report.md), [selected-range decoding](../results/selected-range-decoding-20261110/report.md), [selected-range edits](../results/foreground-web-selection-20261110/report.md) and [focus preparation](../results/range-focus-preparation-20261110/report.md).

### Read receipts at their actual scope

A clipped field preview cannot prove full equality. Current ordinary multiline replacement reports unverifiable when native text differs only in internal LF representation; it never normalizes the value or confirms delivery from that condition. Strict selected-range receipts still require exact qualified readback.

A menu action with no visible change is also unverifiable because clipboard, disk and other-window effects are not covered by that UI diff. The controlled Copy succeeded despite its older suspected-no-op receipt. Preserve that historical receipt and add the independent evidence; do not rewrite the past or repeat the action for a better receipt. Likewise Unlock Download is not proof that a file was saved or that generated audio is decodable. Verify selected format, actual project destination, file bytes, decode, duration and hash before any critic request.

Source: [receipt ambiguities](../results/native-receipt-ambiguities-20261110/report.md). The broader [run report](../results/suno-20261110/report.md) retains the failed hypotheses and live limits.

### Save an authenticated export through native panels

This run qualified the following sequence for one complete MP3 export. Discover each actual PID/window ID and prove its same-process modal association; the numeric IDs in historical evidence are not reusable targets. A parent-bound session never implicitly redirects input to a child panel.

1. In the actual own-song Download dialog, inspect format state. Its options are multiselect: selecting MP3 did not clear the default M4A. Require MP3-only selection, then unlock once under the existing included allowance. Wait and reconcile the prepared export rather than invoking Unlock again.
2. Bind the observed Save sheet explicitly. From that session invoke the guarded foreground `cmd+shift+g` hotkey. If Go to Folder opens an untitled nested panel, observe and bind its exact ID in a new session:

   ```sh
   "$suno_fw" start "Choose the owned export directory" --app "Google Chrome" --pid OBSERVED_PID --window-id OBSERVED_FOLDER_PANEL_ID --mode foreground_permitted --session /absolute/footwork/jevdual/output/NEW-folder-panel-session
   ```

3. Type the full authorized project exports directory into the freshly observed directory field and verify exact readback. Ordinary background `enter` left this panel unchanged in the live run; the existing foreground `do hotkey return` route closed it. Reobserve the original Save session and require the intended destination together with the run-owned filename before one guarded foreground Save.
4. Verify the actual project file, full decode, duration and hash. The successful source export was 4,639,077 bytes and 204.8 seconds, SHA256 `138821e47c9a2e68c267942e308f3b055aa932cde5a031d0aae2df4d6d63d349`. A closed-panel observation failure after Save does not invalidate this independent file evidence or justify saving again.

An untitled binding requires `--pid` with `--window-id`, not a title guess or session-file edit. Absent, duplicate or unproven IDs refuse. Sources: [modal resolution](../results/save-modal-binding-20261110/report.md), [exact-window start](../results/exact-window-start-20261110/report.md), and notebook entries SUNU40–42 referenced by the [run report](../results/suno-20261110/report.md).

### Qualify one bounded editor change

Suno's [dedicated Crop Song guide](https://help.suno.com/en/articles/3166529) describes opening a song's triple-dot menu, choosing Remix/Edit then Crop Song, adjusting a waveform selection and applying Crop Song to create a new song in Library/Workspace. Its [Song Editor guide](https://help.suno.com/en/articles/6141505) separately describes inline section removal and fades at clip corners. Discover which interface is open and whether its selection means a retained range or a removed interval; do not transfer semantics between those controls. These are documented routes, not completed steps in this live run.

1. Bind a run-owned source and preserve its identity, baseline duration and decodable audio. State one intended change and its interval before touching the waveform. Inspect current controls, selection times and preview; when positions are only approximate, do not claim an exact time range from pixels alone.
2. Make one crop or fade and audition the affected boundary with surrounding context. A visible waveform change establishes draft editor state. Apply the observed commit/save action once and reconcile it; for dedicated Crop Song, require a distinct new Library/Workspace resource and verify the original remains available.
3. Export that derivative to a fresh project path. Verify identity, file hash, complete decode and duration against the selected interval, allowing only separately explained encoding effects. A fade should preserve duration; check the audible ending and level envelope instead. Neither a download receipt nor a model's description establishes the intended audio change.
4. Reopen the saved derivative through Library and inspect its current editor/playback state. Compare its actual audio with the baseline around the edit, then in whole-song context. Record draft-state, saved-resource, exported-artifact and reopened-state evidence separately. Qualify lyric regeneration only as a later test with its own preservation and transition checks.

## Live qualification of the selected reviewer

The project-local `scripts/openrouter_media_review.py` now supplies actual local audio/video to the user's selected Qwen route. It retains media hashes, provider/model response, usage and uncertainty without saving credentials or media payloads in logs. It has explicit reasoning control, a total exchange deadline and no automatic retry. A deadline cannot prove that a remote generation stopped or was unbilled. Requested output tokens are not a hard total-token or spend limit.

In this development run, the route correctly distinguished a known tone pattern from silence and produced audio-grounded accounts of three Softtrigr reference songs. The video route identified a blue-to-green scene and rightward motion, but missed a known freeze and one-frame flash, invented some spatial detail and gave inaccurate times. Adding the same audio explicitly as a sidecar produced an audible-events account where embedded audio alone had been inconclusive. These are small mechanism checks, not accuracy-rate or taste validation. See `results/suno-20261110/reference-analysis.md`, `video-calibration.md` beside it and `results/openrouter-media-review-20261110/report.md`.

The later generated-song review consumed the independently decoded candidate B MP3 rather than an opaque playback URL. Its suggestion to reduce middle repetition is a proposal for human/editor consideration. Do not invent a precise cut point from that prose or promote it to verified audible improvement; no edited before/after pair has been reviewed yet.

Use the model for coarse observations and proposed edits with stated uncertainty. Use actual editor state, exported audio, independent duration/silence/frame checks and reopened saved state to verify the intended change. A model saying “smooth” does not clear a known defect. Human preference acceptance remains separate.

## Research to use as design tests

- [Timeline-Bench](https://arxiv.org/abs/2609.35143), a September 2026 preprint, evaluates finished video edits and reports that output quality remains a major obstacle. Use human editorial comparison as a separate acceptance check.
- [VideoAgent](https://arxiv.org/abs/2403.11481), ECCV 2024, studies structured temporal memory and retrieval of relevant segments. Borrow selective reinspection rather than repeatedly supplying a whole recording.
- [AVE-Compass](https://arxiv.org/abs/2607.24821), a July 2026 preprint, evaluates coupled audio/video edits including preservation of non-target content. Borrow explicit preservation and synchronization checks.

These research systems and benchmarks do not establish that an integration works in Suno. Validate their useful ideas against the actual editor, media and user's preferences.

The full Consensus report is preserved verbatim in the private run output and is also available in the [Consensus research thread](https://consensus.app/search/research-practical-approaches-for-an-ai-computer-u/GU-Il5niRwSp_ujPkPWy4Q/). The component choices above are independent engineering recommendations linked to their primary documentation; the research report is not a qualification of these integrations.

## Supplement from the supplied research notes

Two user-supplied research documents were reviewed on November 10. Their recommendations are reference material; embedded setup instructions are not authorization to install packages, connect accounts or operate other repositories. The material adds several useful priorities, verified below against primary sources.

### Supported Suno operations and the UI journey

Suno launched its [official MCP beta](https://suno.com/release-notes/suno-mcp-beta) on October 28, 2026. Its [capability overview](https://help.suno.com/en/articles/14551361) documents creation, covers, extensions, mashups, speech, audio upload and plan/credit queries. Its [FAQ](https://help.suno.com/en/articles/14486145) documents authenticated connection at `https://api.suno.com/mcp`. No Suno or Qwen tool was exposed in this chat's callable tool inventory when checked; no connection or installation was attempted.

Evaluate the official service for supported semantic operations and independent library/credit readback once connected. Keep the requested Footwork creation/editor UI qualification explicit. MCP-created music would establish a different entry path, and the published feature list does not establish full Song Editor or Studio timeline control.

### Suno Studio Chat as a separate semantic route

Suno's [October 29 Studio Chat announcement](https://suno.com/blog/studio-chat-assistant) documents naming tracks from clips, changing multiple faders by a requested dB amount, adding EQ/compressor effects with parameters, and asking for feedback. The [Studio 2.0 announcement](https://suno.com/blog/studio-2) introduced the chat beta alongside MIDI, plugins and automation, and describes Premier multitrack/stem exports at 32-bit/48kHz. These vendor-documented capabilities are worth a separate Studio qualification; they are not evidence of an operation in this run or of an exposed external critique API.

Start that qualification with one reversible change to a run-owned track. Capture its exact prior name or numeric fader value, submit one bounded request through the observed Chat control, then read the actual track/effect state and inspect exported audio where the change affects sound. Preserve an undo path and reopen the project before claiming persistence. Chat's confirmation or feedback is not independent readback. The cited posts do not document Chat selecting exact crop/fade boundaries, so retain the observed Song Editor route for those tests. Qwen through OpenRouter remains the user's selected external reviewer.

### Prioritize actual exported audio

Prefer a rendered WAV for the first listening milestone. Suno's [Studio export documentation](https://help.suno.com/en/articles/8128193) describes whole-mix, selected-range and multitrack exports, plus individual-clip WAV downloads. These are documented capabilities, not live qualifications of this account. Use app-output capture when interactive preview requires it; microphone capture is not proof of the exact Suno output.

For Studio's separate qualification, [take lanes](https://help.suno.com/en/articles/13670913) provide in-place auditioning, ratings and non-destructive promotion. They are a useful A/B surface. Do not infer that Song Editor has the same controls or persistence behavior. Verify the original remains recoverable in the actual run.

### Evaluate existing perception adapters before building them

[Qwen MM Plugins](https://github.com/QwenLM/Qwen-MM-Plugins) supplies multimodal file tools and model-backed capabilities. It is a high-priority adapter candidate, alongside the existing Gemini and open-model shortlist. Keep frame extraction distinct from delivery of actual audio/video to a capable model. Record provider, actual supplied bytes, intervals and sampling; tool names alone do not establish what was perceived.

[Qwen Live Harness](https://github.com/QwenLM/Qwen-Live-Harness) is an architectural reference for realtime audio/video interaction around an agent harness. Its existence does not establish capture of Suno's selected process audio on this Mac. Compare the host/daemon boundary without replacing Footwork's target, posture or receipt checks. FilmCraft and mcp-video implementation claims in the supplied notes remain unverified in this task; no other repository was inspected or changed.

### Strengthen the critic's evidence and negative controls

Add a review manifest with media hash/revision, intended and actually inspected intervals, modality, source-frame timestamps, sampling/resolution, audio routing, capture gaps, model and detector provenance. Let findings report categorical uncertainty before assigning uncalibrated probabilities.

Use blinded A/B comparisons in both presentation orders. Include muted/swapped audio, clean controls, intentional freeze/black/silence, and known timestamped defects when evaluating the reviewer. Measure detection, localization, repair and human preference separately. A critic that repeats the prompt when supplied the wrong sound has failed the perception check.

### Corrections and limits to retain

- [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html) such as blackdetect, freezedetect and silencedetect report thresholded signal patterns. Intentional static screens, holds and silence can trigger them. Duplicate imagery does not by itself prove a dropped frame. Compare findings with the intended timeline and playback context before proposing a repair.
- Sparse sampling can miss a brief defect; it does not imply an approximately zero detection probability for every three-frame glitch. Duration, source frame rate, sample phase and model preprocessing determine exposure. Inspect consecutive source frames around a flag and retain their true timestamps.
- Keep editor responsiveness, recording defects and exported-output defects separate. A slow preview or poor recording does not prove the final media is damaged.
- Treat fixed FPS settings, token counts, model rankings, commercial API access, benchmark scores and installation commands in the supplied notes as leads until checked for the selected version and task. No headline benchmark numbers were adopted as Footwork acceptance thresholds.

The practical next milestone is one bounded UI edit to the already-created, exported and reviewed candidate B, followed by a separately saved derivative, actual boundary comparison and reopened saved state. Do not regenerate the completed batch to bypass editor or targeting frictions. Broad NLE integration remains a separate work package.
