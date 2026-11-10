# Suno creation, editing and media judgment

Engineering recommendation, researched November 10, 2026. This is a development workflow and a capability roadmap, not a claim that Footwork has completed Suno editing.

User-selected reviewer: `qwen/qwen3.8-omni-flash` through OpenRouter, superseding the tentative provider shortlist below. The credential destination is the Git-ignored `jevdual/.env`, variable `OPENROUTER_API_KEY`; enter the key locally and never retain it in reports or requests logged to disk. The [canonical model guide](https://openrouter.ai/qwen/qwen3.8-omni-flash/llms.txt) documents the Chat Completions endpoint. Qualify actual audio/video input on the chosen provider before claiming musical perception: text completion alone does not establish it, and [video URL support varies by provider](https://openrouter.ai/docs/guides/overview/multimodal/videos).

User-selected musical grounding: the existing songs on [Softtrigr's YouTube channel](https://www.youtube.com/@Softtrigr). Review actual media before deriving sonic characteristics; titles, channel description and lyrics are supporting context. Create new test songs iterating from those references while preserving existing material.

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

For a fresh generic qualification, an instrumental and a fade isolate control failures from lyric alignment and stochastic regeneration. This user's run instead uses original French-English lyrics grounded in their selected references. Then test a lyric/section replacement. Test Studio/stems separately: a successful Song Editor journey does not qualify a different editor.

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
| Guarded UI actions | Footwork native CLI | Existing signed-in Chrome, fresh targets, posture and receipts | Live Suno creation/editor completion remains unverified; native Chrome AX can lag |
| Browser state and controls | [Playwright MCP/CLI](https://github.com/microsoft/playwright-mcp) | Structured snapshots and browser automation | Default owned profile does not inherit this user's login; the documented [extension route](https://github.com/microsoft/playwright/blob/main/packages/extension/README.md) supports existing tabs but requires setup and connection approval |
| Browser performance | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) | Diagnose browser behavior and performance | Requires an actual permitted connection; distinct from an audio critic |
| Capture | OBS + [obs-websocket](https://github.com/obsproject/obs-websocket) | Programmatic recording control | Screen and intended system/app audio must both be configured and checked; available MCP tools do not prove OBS is running or connected |
| Media mechanics | [FFmpeg](https://github.com/FFmpeg/FFmpeg), [librosa](https://github.com/librosa/librosa) | Clip/decode/probe media; derive audio and music features | Features support diagnosis, not taste; FFmpeg is installed locally, no new packages installed in this run |
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

## Live qualification of the selected reviewer

The project-local `scripts/openrouter_media_review.py` now supplies actual local audio/video to the user's selected Qwen route. It retains media hashes, provider/model response, usage and uncertainty without saving credentials or media payloads in logs. It has explicit reasoning control, a total exchange deadline and no automatic retry. A deadline cannot prove that a remote generation stopped or was unbilled. Requested output tokens are not a hard total-token or spend limit.

In this development run, the route correctly distinguished a known tone pattern from silence and produced audio-grounded accounts of three Softtrigr reference songs. The video route identified a blue-to-green scene and rightward motion, but missed a known freeze and one-frame flash, invented some spatial detail and gave inaccurate times. Adding the same audio explicitly as a sidecar produced an audible-events account where embedded audio alone had been inconclusive. These are small mechanism checks, not accuracy-rate or taste validation. See `results/suno-20261110/reference-analysis.md`, `video-calibration.md` beside it and `results/openrouter-media-review-20261110/report.md`.

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

The practical next milestone is still one identifiable Suno draft, actual audio supplied to a reviewer, a bounded UI edit, boundary comparison and reopened saved output. Capture/inspection plumbing supports that milestone; broad NLE integration is a separate work package.
