# Pre-header transport diagnosis and sealed-source qualification

October 30 package. The observed duplicate submission was traced to Chromium's plain-form navigation transaction restart. An opt-in fetch route avoided that restart in the finite controls and native trials. New preadmitted v3 recovery qualifies the exact terminal fixture epoch after browser retirement, listener closure, handler drain and an immutable ledger seal. The original navigation/disconnect challenge remains unsupported; historical unknowns remain unknown.

## Six work packages

| Package | Observed outcome | Evidence |
| --- | --- | --- |
| Freeze and protocol | Predictions and amendments committed before corresponding probes; base is merged main 1301074 | docs/experiments/preheader-20261030.md; docs/notebook/2026-10-30-preheader.md |
| Causal reproduction | 26 diagnostic slots; four navigation/disconnect Chrome controls each show one submission event, one logical CDP POST, two handler connections/ingresses, one row; the same NetLog transaction restarts with error -324 between two POST header sends | controls/summary.json and retained control exports |
| Mechanism correction | Default navigation challenge retained. Opt-in fetch makes one guarded encoded submission, preserves the form/title, disables further activation and renders text safely. Both fetch controls and both installed native v2 fetch trials show one ingress; v2 correctly stays unknown | cc7279b, f2eb844, 984cd86; trials/native-fetch-1 and native-fetch-2 |
| Qualified reconciliation | Optional v3 binds policy and source epoch before dispatch. Positive closure/drain precedes an atomic snapshot seal; guards/triggers fence subsequent mutations and reopening is refused. Duplicate, missing, wrong-mode, malformed, tampered or legacy evidence refuses | badb0c2, 6c0f8a0; seal regression outputs; sealed-public-green.txt |
| Installed qualification | Frozen 6c0f8a0: native pre-header trial recovers after an actual controller kill; nominal chain and interrupted pre-header chain complete Finder, Preview and Chrome with one ingress each | candidate-6c0f8a0; trials/native-sealed-qualified, live-sealed-nominal, live-sealed-interrupted |
| Review and release | Two inherited-model agent contexts cross-reviewed controls/runtime; parent inspected deltas, ran public reconciliation tests, full suite and installed checks. One v3 response-mode consistency finding was corrected | independent-v3-review.txt; hosted checks and merge must be observed separately |

## Artifact and checks

Runtime: `6c0f8a02be61baeda3360f2ab4b8ef6883698c07`. The candidate manifest records its wheel hash and 189-file inventory; runtime.json confirms eight selected module origins inside the installed site and records OS, SDK and app versions. Later documentation/results commits do not change that runtime.

Full key-free suite: **2269 passed, 26 skipped** (full-suite.txt). Ruff passed (ruff.txt). Independent ticket/reconciliation/handoff review: **123 passed**. The isolated offline consumer package passed (consumer-package.json). Before v3, the fetch runtime passed 2260 tests; that earlier receipt is not substituted for final verification. No paid providers or network dependency installations were used.

## Live accounting and probe repairs

All **12 live slots** are retained in trials.json, separately from the 26 diagnostic controls. Two setup slots failed before input: initial missing-window readiness, and a mistaken candidate wrapper path. They are not successes. Two native navigation trials reproduced two ingresses and retained unknown custody. Two installed native fetch/v2 trials produced one ingress but correctly remained unknown. Earlier baseline and fetch/v2 nominal/interrupted chains are retained alongside the final v3 trials.

The native-sealed-qualified component also retains ticket_oracle.ok=false from the same legacy header oracle: its observed result establishes v3 custody recovery and one ingress, not success of that old oracle. The final v3 interrupted chain observed all three SIGKILLs (return code -9), including after ingress before CLI result retention. It finalized from the sealed source, then its old response-header oracle rejected the deliberately headerless response. That harness failure is retained. A separate read-only repair checked the exact row/fields, one ingress and sealed lifecycle, completed the pending handoff through HandoffRun's bound v3 recapture, and replayed the original token without additional ingress. No input or submission was repeated to repair the oracle. The successful result is explicitly labeled passed after read-only oracle repair.

Independent Finder checks confirm exact destination, file identity/content and sibling preservation; Preview checks independently decode the intended saved rotation and dimensions. Cleanup rechecks final saved images, records closed owned listeners/helpers and retains four new v2 unknowns. Previous authorities and unrelated worktrees were not modified. Raw browser NetLogs, profiles and broad captures remain private under output/preheader-20261030; published controls retain only diagnostic identities, fixed endpoint request lines, counts and causal event metadata.

## Exact support boundary

The narrow owned Finder → Preview → fetch-submission workflow now has installed nominal and interrupted pre-header recovery proof under **preadmitted sealed_fixture v3**. Service closure is part of this workflow: the browser is retired and the single-use fixture source cannot reopen. A process death or elapsed quiet interval alone cannot authorize recovery.

The seal proves the enrolled cooperative fixture epoch's final ledger, not browser/network termination, universal exactly-once delivery, hostile SQLite authentication, arbitrary origins or active-user coexistence. Another source at the same loopback port is outside this epoch; it cannot supply matching source identity/evidence. Default v2 still requires supported headers and refuses disconnect mode. V1/v2 unknowns cannot upgrade or enroll retroactively. Plain-form navigation still duplicates under the retained challenge and remains unqualified.

Local checks and finite installed proof are complete. PR review, hosted CI and merge are separate observations recorded during follow-through; this report does not anticipate their outcomes.
