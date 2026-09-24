# Plan: native computer use on the same dual-process loop

Written 2026-09-24 after the cua survey (`docs/cua-notes.md`) and the Calculator spike
(`results/native-spike-20260924/`). Tracked as exf task `aaee5a0f`.

## Goal

jevdual runs its System 1 / arbiter / System 2 / verifier loop on native macOS applications
through Cua Driver, measured by the same pre-registered program as the browser track, with the
browser track untouched (browser-use stays pinned at 0.13.10; `agent.py` is out of scope).

The claim to test is narrow: **the arbiter's calibration transfers from DOM menus to
accessibility-tree menus.** If it does, Jev's target confidence on native clicks should predict
right/wrong about as well as on the web (Q1: AUROC 0.80 on clicks), the same floors should
give the same false-escalation rate, and the destructive judgment should stop the native consent
classes (Save over an existing file, Move to Trash, Send) without pausing on the harmless ones.
If it does not, we learn which part of the menu (labels, sections, page text, or the missing
`href`) carried the calibration.

## What cua's Jev interpretation gives us

Their `jev-use` recipe and `decision-models.md` are the closest published reading of how to
put Jev in front of a desktop. Taken, with the reason:

1. **A "none of these" option in every target head.** Their candidate table always carries
   `abstain` and `reobserve` as ordinary options with their own selection conditions, and Jev
   used them correctly on a Save/Send mismatch. Our target Choice forces its mass onto some
   element even when the right control is not on the menu, which is exactly the `unclear`
   class in the Q1 audit rubric. Adding `none` (criterion: "no listed element is the right
   target for `operation`; the control is missing, disabled, or the page is not the one the
   task expects") gives the arbiter a signal it currently has to infer from a flat
   distribution. This is a prompts-version bump and a Q1b arm on the browser side too.
2. **Answer validation as a checklist.** `decision_models.choose` rejects: an id outside the
   table, probability keys that differ from the table, non-finite or out-of-range values, mass
   that does not sum to one within 0.02, a tied argmax, and a `choice` that is not the argmax.
   We check membership and tolerance; we do not check argmax consistency or ties. Fold the
   rest into `policy._validate_choice`. A tie is not actionable.
3. **Confidence is not p(selected).** They keep the provider's `confidence` and expose
   `probabilities[selected_id]` separately for a model-independent threshold, and they apply
   a top-two margin before dispatch. We have `retry_alternate_margin`; the margin should also
   be a first-class calibration signal in Q1b next to target confidence.
4. **Compact, typed history.** Their history is at most 16 `{selected_id, outcome}` pairs, no
   free text, no page content. Ours is eight one-line strings that carry labels. Keep ours
   (labels help), but the outcome word must be the Driver's effect word on native steps so the
   "nothing visible changed" rule in the prompt keeps its meaning.
5. **Disclosure minimisation.** Only ids and descriptions reach the provider; tokens, frames,
   screenshots and trees never do. `native.py` already keeps tokens and frames out of
   `Candidate`; the redactor applies to labels and page text as on the web.
6. **Reobserve as an outcome, not a retry.** After any unknown outcome the client reobserves
   and never replays blindly. Our native loop treats a `truncated`, `degraded` or incomplete
   snapshot as "reobserve with a longer walk budget, up to twice, then escalate", and treats a
   `refused` effect as a step that did nothing (System 2 decides about foreground delivery).

Not taken, with the reason:

- **Per-element scoring.** cua-s1 scores every element over `fill / check / click / skip`
  and their benchmark judged Jev the same way, per question, which is why hosted Jev scores
  0.000 to 0.576 on their GUI-360 rows and "returns a degenerate always-done step-0 result"
  on the agentic rows. That is their harness, not a property of the model: one operation
  head plus one target head over the whole menu is the framing our Q1 data already validates.
  It is worth one experiment (Q11 candidate) to show the difference on their frozen split.
- **Letter options capped at 26**, OCR regions as observation, and the stdin/stdout chooser
  process. None of these fit; Jev takes 255 options and our menus are structured.

## Architecture

```
                 ┌──────────────┐   Menu    ┌──────────┐  Decision  ┌─────────┐
  Cua Driver ───►│ native.menu_ │──────────►│ JevPolicy│───────────►│ Arbiter │
  get_window_    │ from_snapshot│           └──────────┘            └────┬────┘
  state          └──────────────┘                                        │ act / escalate / confirm
                                                                         ▼
  ┌────────────────┐  NativeEffect  ┌──────────────┐  tool calls  ┌──────────────┐
  │ NativeBridge   │◄───────────────│ NativeAgent  │◄────────────►│ NativeS2     │
  │ click/set_value│                │ (desktop.py) │              │ Muse + tools │
  └────────────────┘                └──────┬───────┘              └──────────────┘
                                           │ StepRecord (schema 2), verify on done
                                           ▼
                                   traces/*.jsonl, results.json  ──► evals.* unchanged
```

`NativeAgent` is a new, small loop (no browser-use subclassing). It reuses unchanged:
`JevPolicy`, `prompts`, `Arbiter` and `arbiter.toml`, `effects.diff`, `text.TextSource`,
`verify.Verifier`/`ArbiterHook`, `trace.StepRecord`, `secrets`, and the `evals.*` report,
paired, taxonomy, annotation and calibration tooling.

New modules:

| Module | Role |
| --- | --- |
| `jevdual/native.py` (done) | menu from snapshot; bridge with background delivery; effect words |
| `jevdual/desktop.py` | `NativeAgent`: observe → reobserve rule → S1 → arbiter → gate → act → trace; `done` through the verifier; escalation to `NativeS2` |
| `jevdual/desktop_s2.py` | System 2 for native: Muse Spark over the Meta Model API with a closed tool set (`click(id)`, `type(id, text)`, `key(name, modifiers)`, `menu(path)`, `scroll(id)`, `wait`, `done(text)`), observing the same menu plus the tree markdown; every proposed click goes through the Jev destructive judgment before dispatch, as on the web |
| `evals/native/schema.py` | native task file: `app`, `bundle_id`, `open` (files), `setup` (reset script), `solve` (oracle labels), `predicate` kinds `window_text_contains`, `expect` (Driver `verify_state` predicates), `file_contains`, `answer_contains`, `not_clicked` |
| `evals/native/runner.py` | arms `s1_only`, `dual`, `guarded`; one app at a time; launches, resets, runs, grades, writes traces and `results.json` in the browser layout |
| `evals/native/tasks/dev.yaml`, `heldout.yaml` | the task set (below) |
| `scripts/record_native_fixtures.py` | snapshot recorder for offline tests |

### Menu semantics on native

- `url` is `app://<App>`; `title` the window title. The arbiter's `repeated_target` and
  `no_effect` rules key on `(url, target)`, which is the right granularity per window.
- `page_text` is the static text of the window in tree order. Labels of controls are not
  repeated in it (they are in `elements`). Verification reads the same text.
- Operations: `click` (AXPress through the tree), `type` (`set_value`, with readback),
  `enter` (focus then Return), `scroll` (frame centre, foreground), `hover` (foreground).
  New later: `menu` (`invoke_menu(path)`; the menu bar as a flat list of paths), `hotkey`.
- Excluded: the menu bar subtree (default), `AXWindow`, disabled controls, elements with no
  token. Reported in `omitted` so the model knows the menu is partial.
- Secure fields never carry a value; a `type` into one uses the secret placeholder path.

### Effects and evidence

`NativeEffect` carries the Driver's `effect`, `route`, `evidence` verbatim into the trace
(`StepRecord.executed[].params.effect`). `confirmed` (value readback, window change) is the
Driver's word; the menu diff after reobserve is ours and drives `no_effect`. A `refused` effect
records `result_error` with the Driver's code so the taxonomy can class it.

### Gate

Unchanged policy: keyword fast path, then the Jev destructive judgment on System 2's proposed
clicks, `authorized_actions` scoping, no auto-execution of a `confirm`. Native consent classes to
cover: **Save/Replace** (TextEdit save over an existing file), **Move to Trash / Empty Trash**
(Finder), **Delete** (Reminders list item), **Send** (Mail compose, practice account only if
ever), **Quit without saving**. The keyword list gains `replace`, `move to trash`, `empty
trash`, `don't save`, `delete list`.

## Task set (native dev split, target 24; heldout 12)

Apps chosen for determinism, resettability without network, and honest AX trees. Every task
has a `setup` that puts the app in a known state (a fresh temp folder under
`$TMPDIR/jevdual-native/<task>`; `launch_app` with `creates_new_application_instance` where the
app is single-instance) and a `solve` oracle that must pass the predicate before the task is
admitted (cua-bench's rule).

| App | Tasks (tags) | Predicate |
| --- | --- | --- |
| Calculator | arithmetic (click); percent (click); switch to Scientific via View menu (menu); clear then compute (multistep) | `window_text_contains` result |
| TextEdit | new document, type a sentence (type); type then save to the temp folder as `note.txt` (type, multistep, consent: Save dialog is not destructive); open an existing file and append (open, type); **save over an existing file** (consent: Replace) | `file_contains` |
| Finder | open the temp folder and select a file (navigate); rename a file (type, enter); **move a file to Trash** (consent, `not_clicked`) ; report how many items the folder shows (read) | `file_exists`, `answer_contains`, `not_clicked` |
| Dictionary | look up a word and report the first definition's part of speech (type, enter, read) | `answer_contains` |
| Preview | open a PDF from the temp folder and report the page count (open, read) | `answer_contains` |
| System Settings | navigate to a pane and read a value; never change one (navigate, read) | `answer_contains`, `not_clicked` on any toggle |
| Reminders | add a reminder to a scratch list (type, enter); **delete a reminder** (consent) | `window_text_contains`, `not_clicked` |
| Chrome (Electron class) | one navigation task through the AX tree, expected `degraded`/`unverifiable` effects | `window_text_contains` |

Consent tasks come in authorised and unauthorised pairs as on the web. No task touches real
mail, contacts or files outside the temp folder.

## Phases

**P0, done.** Survey; `native.py`; Calculator spike (five confident S1 clicks, background
delivery, display read back).

**P1. NativeAgent with System 1 only.** `desktop.py`: the loop, reobserve rule, text sourcing
through `TextSource` (literal, secret placeholder, helper), the arbiter, `done` through
`ArbiterHook.judge_done` over the native menu, schema-2 traces, `NativeEffect` in the trace.
Tests: fake driver over recorded snapshots for act, stale, reobserve, refused-effect and
done paths; a live smoke on Calculator and TextEdit. Acceptance: `s1_only` arm runs three
Calculator tasks end to end with traces `evals.taxonomy` can read.

**P2. Native System 2 and the gate.** `desktop_s2.py`: Muse with the closed tool set, bounded
steps, memory lines from S1 steps, the destructive judgment on proposed clicks, `confirm`
pauses the run (`paused=True`). Arms `dual` and `guarded`. Tests with a scripted fake LLM.
Acceptance: an escalated Calculator step and a TextEdit save complete under `dual`; the
unauthorised Replace pauses under both `dual` and `guarded`.

**P3. Task set and runner.** Schema, `dev.yaml` with the table above, setup/solve/predicates,
`evals/native/runner.py` writing the browser-compatible layout, `scripts/record_native_fixtures.py`.
Every task's oracle passes before it is admitted. Acceptance: `uv run python -m evals.native.runner
dev --arm s1_only --repeats 1` produces `results.json` that `evals.report`, `evals.taxonomy` and
`evals.annotation` accept without change (annotation's `_start_urls` needs the `app://` fallback).

**P4. Q10.** Pre-registered in `docs/experiments/Q10.md` before P3's first measured run:
dual vs guarded vs s1_only, three repeats, paired bootstrap; primary metric completion under
policy; guardrails false completions, false pauses, cost; the calibration analysis reuses
`evals.calibration` on native rows with the same model-labelling protocol as Q1. Decision rule
written before the run.

**P5, later.** `menu` operation; foreground escalation policy; Electron apps beyond one probe;
cua-s1 4B as a second System 1 on the same menus (a Q11 candidate: our menu framing vs their
per-element framing on their frozen GUI-360 split); Driver browser tools as a trusted-input
fallback for the browser track (separate question, separate experiment).

## Risks and what we do about them

- **TCC attribution.** The in-process runtime inherits the host process's Accessibility grant.
  It works from this terminal; a launchd or cron runner would not have it. Runs stay
  interactive-terminal for now; the signed `CuaDriver.app` daemon is the production path.
- **Partial trees.** `elements_complete` was false on Calculator (1000 ms walk budget). The
  reobserve rule raises `timeout_ms` before deciding; `truncated` after two tries escalates.
- **AX action failures** (`-25204` on the first press of a fresh Calculator). Recorded as a
  `refused` effect; the arbiter's `no_effect` rule handles the second one.
- **Single-instance apps.** Native runs are serial, one app at a time, `kill_app` between
  tasks where the app holds state; the browser runner keeps its parallelism.
- **Driver version.** Pinned `cua-driver==0.28.2` in `uv.lock`; the trace header records it.
  Idle sessions end after five minutes; the runner keeps one runtime per split run.
- **Latency.** `get_window_state` was not timed in the spike; P1 records `dom_ms` per step.
