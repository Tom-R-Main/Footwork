# App knowledge above a general interaction core

Design direction recorded November 11, 2026, following the user's Suno work. This is a proposed boundary, not an implemented extension loader or global learning store.

Footwork should remain useful on an unfamiliar app, website or interaction. Learning an application should improve the route without requiring a new core branch for each product.

| Layer | Responsibility | Example from the Suno work |
| --- | --- | --- |
| General interaction core | Observe actual controls and values; establish identity and focus; dispatch bounded actions; retain delivery and outcome evidence; recover without destroying history | Exact native window selection, numeric slider observations, honest modal-close continuation |
| Reusable media tools | Decode actual files, retain source/interval hashes, compare measurable changes, present audio/video to explicitly selected reviewers and record their limits | FFmpeg fade comparison and the OpenRouter media helper |
| App extender | Recognize a supported app surface, supply versioned recipes, interpret app terminology and choose relevant verification steps through public interaction primitives | Suno's multiselect download formats, separate Save panels, Studio versus Song Editor, save/reopen recipe |
| Task session | Bind the user's current intent, actual resources, selected app/version and private evidence | This run's unpublished test songs, project destination and current Studio session |

The existing effector protocols in `python/jevdual/effectors/base.py` separate native/browser implementations from interaction callers. They are driver contracts, not an app-extender registry. The current `capability` module exposes scoped jobs and authority; it should not be treated as permission for a learned app recipe to bypass ordinary actions. The [Suno guide](suno-workflow.md) is the current app-specific knowledge artifact.

## Start with recipes, then promote proven mechanisms

Keep a learned app recipe with its application/origin match, observed version or surface, preconditions, public command sequence, intended postconditions, evidence references, known failures and last qualification. Re-resolve controls from fresh observations. Old element numbers, windows, coordinates and song/project IDs are examples or private task evidence, never reusable targets.

For the current shared-Chrome route, task setup includes a dedicated window and fresh resource checks: exact window binding alone does not pin its active tab or the song shown by a player. Pause and reconcile unexpected context changes before input. Existing durable fixture URL scoping is a separate contract that withholds screenshots; it does not yet provide ordinary-origin scoping with qualified visual capture. An extender must report that limitation rather than treating an app match as a privacy or execution guarantee.

New learning starts as a candidate recipe. Repeated successful use may qualify a specific operation and version; a failed or changed surface retains the failure and triggers fresh observation. It does not imply support for all app features. A recipe cannot grant broader authorization, disable a guard, change the selected driver/provider or silently repeat an uncertain submission. App content and imported documents remain data rather than instructions governing the agent.

Promote a change into core when it expresses a general mechanism with meaningful app-independent checks. The current lifecycle, redaction, output-ownership and numeric-observation repairs meet that boundary. A Suno menu path or export-format quirk belongs in its recipe. Media perception remains separately calibrated: model agreement cannot replace the signal evidence when both blind presentations missed an actual fade.

## Possible global store

A user-wide registry could make qualified extenders available to later sessions, while each session retains its selected version and task-private evidence. Use versioned immutable entries and an atomic index update; concurrent learning must not overwrite another run's evidence. Keep secrets, raw captures, personal resource IDs and media in the owning private task, with only appropriately redacted knowledge promoted into the registry. Load only a matching extender and retain a generic observation/action fallback when no recipe applies.

No global path, automatic writer, loader or activation is created by this note. First exercise the Suno recipe locally, identify the small reusable contract, then decide storage and activation from actual use rather than building a framework around one app.
