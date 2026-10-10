# WB1: Project-linked workbench observations

Mode: local engineering/workflow feasibility, not autonomous task execution or usefulness qualification.

## Hypothesis

An already reviewed camera note can become a project-bound workbench record with an explicit question, interpretation, proposed next check and acceptance criterion, preserving the distinction between physical evidence and engineering inference. Footwork can verify the saved record without inventing a native session or performing its proposed action.

## Predictions

The first live desk note binds to the user's explicitly selected Footwork project using exact namespaced project ID and canonical checkout, with the repository revision and selected code-reference hashes recorded. A saved JSON/Markdown packet retains approved source text and hashes, a source evidence trail, typed record purpose and clearly proposed work/check status. Public Footwork check-artifact validates each generated record. Repeating a binding does not create another record. Changed project, source, metadata or approval digest cannot reuse an existing binding. Unknown write outcomes do not replay. Later repo changes mark context drift separately from saved artifact integrity.

Against: guessed name-only project matching; note instructions executed as commands; a proposed check claimed as completed; incorrect/tampered/missing artifact claimed verified; duplicate/replayed writes; raw OCR or a stale repo context promoted into current evidence.

## Design

Add an isolated tools/workbench-notes package, reuse the desk source's current saved-status/provenance checks and Footwork exact-artifact checker. Only exact registered project metadata is accepted from an explicit bounded catalog. The initial real project is Footwork, selected by the user; records live in this active repository's ignored private output, with no writes into other repositories or cloud workspaces.

Caller-authored structured JSON supplies kind (observation/question/experiment/decision/blocker), question, interpretation, proposed next check, expected result and optional relative code references. These are attributed to the caller, not inferred authority from the photo. Keep immutable source-note identity/text and context snapshots, validate reference containment and secret/excluded-file patterns, bound reads and paths, use one intent per run and create-only output. Provide project-filtered listing and read-only status. Preserve historical recording and current file checks; repository/reference drift is a separate context state, never a claim that a check ran.

Primary metric: one explicit Footwork workbench packet saved once with all saved bytes independently matching bound expected sources (binary), plus accurate source/context/proposal labels.

Checks: public link/status/list path; source/project/metadata conflicts; duplicate labels and namespaced IDs; invalid catalog/reference escape/secret file; source/packet tamper; interrupted record/no replay; project HEAD/reference drift separated from bytes. Use one existing human-approved note; no new camera capture required.

Decision rule: qualify local project association and artifact verification only. A useful agent handoff must name an executable next check and expected observation, but this experiment does not execute it, create remote tasks, publish evidence or infer physical completion. Daily benefit requires later trials against ordinary project note-taking.

## Result

Pending.
