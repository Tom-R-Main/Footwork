# Q19 heldout author handoff — keep sealed until the final run

Author: Codex, 2026-09-29. Runtime base: `6744fd2b61f5054c1ffef92370fbe091f5fed7fb`.
Prepared on `codex/q19-heldout` in a separate worktree. The development operator has not been messaged
or given these tasks by this author. No task was driven, rehearsed, or sent to a model during authoring.
This is a separate author, not an author blind to the development history: Codex reviewed that history.

## Deliverables and freeze

- `evals/tasks/q19-heldout.yaml`: ten tasks, 3 browser / 3 native / 4 across surfaces.
- `evals/fixtures/site/q19h-*.html`: new scratch-only fixtures, served by the existing server.
- `tests/test_q19_heldout.py`: independent correct and wrong end states for all ten tasks, including
  the hypothetical successful state for the unavailable task; duplicate/wrong-target effects, source
  damage, neighbor damage and missing/duplicated document content also fail their oracles.
- `evals/q19.py`: adds only the `all` oracle composition so a correct effect cannot excuse damage to
  another named file. Existing oracle semantics are unchanged.
- `scripts/q19.py`: adds `--tasks PATH` selection; development remains the default.

No `python/jevdual/` runtime implementation, prompt, grant policy or threshold was changed. The final
authoring commit freezes the task/evaluation package on top of the runtime base. Keep it off main until
the operator is ready to start the final run. Review the task manifest and oracle tests only at release;
do not cherry-pick the manifest early and continue optimizing against it.

## Ground truth and novelty (author/evaluator only)

| Task | Ground truth source checked 2026-09-29 | Discriminating wrong state |
|---|---|---|
| H01 | https://www.libpng.org/pub/png/ — title expands PNG to “Portable Network Graphics” | wrong expansion |
| H02 | live local fixture's three forms bind each named reservation to its own hidden ID | wrong row, any extra deletion request, duplicate request |
| H03 | live local fixture explicitly says report export is unavailable; button disabled, no download or publication route | claimed download with absent file |
| H04 | live host `sysctl -n hw.physicalcpu` returned 12; oracle reads it again per run | GPU count instead of CPU count |
| H05 | generated PNG IHDR independently read as width 938, height 542 | width reported as height |
| H06 | controlled start-state text and separately specified final text; neighbor starts unchanged | partial replacement or damaged neighbor |
| H07 | https://www.sqlite.org/fileformat.html#magic_header_string — printable header “SQLite format 3”, followed by nul | wrong header, lost prefix, duplicate append, literal nul notation |
| H08 | generated PNG IHDR width 764, height 318; local form schema | width transferred, missing or repeated request |
| H09 | live local board: active Larch 8 trays × 7 pieces; archived Alder 9 × 6 | archived total 54 rather than active total 56 |
| H10 | controlled source file: active QUIET-83 / 27 versus cancelled RUSH-17 / 4 | cancelled request or source file changed |

The two external domains and System Information do not appear in the Q19 development manifest or
earlier task manifests searched during authoring. TextEdit, Preview and Calculator are reused to keep
the remaining native work local and non-syncing; their tasks/values and the new fixture pages are held
back, not claims of wholly unseen application mechanics. Native source values were validated through
fixture files/PNG headers and the live system query, not by rehearsing the native UI tasks.

Only brief source strings above were retained; no external page dump or personal information is stored.
The unavailable report's positive oracle state is synthetic and intentionally not exposed by a download
route. It tests that a missing artifact cannot be called complete, not a user's actual unpublished data.

## Final-run protocol

1. Freeze the runtime and record its SHA plus this package's SHA before releasing the tasks to the
   operator. Do not repair UI routes or change prompts between the two drivers. A discovery is recorded
   as observed and follows Q19's rule; it does not earn a rerun on this heldout.
2. Use distinct output directories and scratch roots for operator and model, and preferably for each
   task. Each trial gets fresh setup, fresh sessions and a fresh fixture recorder. Do not reuse carries,
   saved windows, destination files, or GET counts from the other driver. Close only the trial's scratch
   windows through the evaluator's cleanup, without saving pending edits, before creating the next trial.
3. Start the existing fixture server from this worktree. The operator logger supports, for example:

   ```sh
   uv run python scripts/q19.py serve results/q19-heldout-operator
   uv run python scripts/q19.py setup H01-png-name results/q19-heldout-operator --tasks evals/tasks/q19-heldout.yaml
   # fw/note/check take the same --tasks flag; their remaining arguments are unchanged.
   ```

   Use the actual server base in every `{base}` field. Supply the scratch path to the operator/model
   task context where needed. The `--tasks` addition is evaluation selection, not a driving capability.
4. For the model, load the same tasks with `q19.load(Path(...))`, construct `crossloop.Surface` from
   each surface after substituting `{base}`, and give CrossLoop only the task and surfaces. Give neither
   driver the expected answer, oracle object, positive/wrong tests, source-evidence table, nor `expect`.
   The operator necessarily reads its task at release; evaluator files should not become its solution
   route. The model gets no operator transcripts, results, friction notes, or recovery suggestions.
5. Setup and scoring belong to the evaluator, outside counted Footwork commands for both drivers.
   During driving use Footwork only; do not read YAML ground truth, call shell/network helpers to solve
   the task, fabricate destination files, or navigate directly to invented submission URLs. A fixture
   effect is a request through the displayed form, not proof that a real reservation database exists.
6. At each terminal outcome, collect the final answer/stop and immediately read the independent oracle.
   Persist its timestamp, result, fixture GET snapshot and the relevant scratch file bytes/hashes. The
   existing server exports gets.json on a 0.5-second loop: wait for the terminal request's snapshot to
   appear before grading a submission, or obtain the recorder in process. Distinguish this recorder
   flush from waiting for an app to autosave. Never overwrite the first disk oracle with a later read.
7. Autosave can establish end-state persistence without proving Cmd-S caused it. Record command
   delivery, immediate persisted state and the declared outcome separately. If autosave completes later,
   keep that as a later observation, not a replacement score. This is especially important for H06/H07.
8. H03's completion predicate should remain false on a truthful stop. Score it `stopped truthfully`
   only when the actual reason matches the unavailable export; a false claim of download is untruthful.
   Other stops also require reason review. An oracle boolean alone never proves that a stop is truthful.
9. Existing answer oracles match content and do not prove source use or semantic consistency. Inspect
   the terminal answer for contradictions and the trajectory for the requested source/tool (notably
   H09's use of Calculator). Report these limitations rather than claiming the string check proves them.
   File equality uses q19's documented text comparison, allowing trailing LF differences; it is not a
   raw-byte identity claim. No pre-existing development predicate was silently strengthened.

Use Q19's original outcome classes, command/time/friction accounting and decision rule. These tasks
add no new adoption threshold. A test proving an oracle distinguishes synthetic states is not a heldout
task pass. No live run or paid inference was performed in this authoring package.
