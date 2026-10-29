# October 28 native operator review and PR verification

October 29, 2026. The full unmerged October 28 operator branch was reviewed, nine findings were repaired, and the integrated runtime passed fresh installed nominal and interrupted v2 chains. The duplicate-ingress cause remains deferred; pre-header disconnect cannot obtain new v2 qualification.

## Scope and independence

Original review: `5d494c6a22921d092e67399badce708e8418bf2a` → `a9b260180980e305ebc414568cf92ab02987f941`. This covers the dispatch correction, durable admission, structured observations/receipts, Finder/Preview/Chrome targeting, independent oracles, ticket recovery, handoffs, notebooks and retained qualification claims. Changes already merged through main `8de9c9ab797e0daafd8b897df61ec03006bde31f` were integrated in `e4b7199`; overlap review preserved the control-state/blocker and installer-diagnostic work.

Three fresh read-only reviewer contexts independently audited durable admission/callers, native targeting/delivery, and evidence/qualification. They inherited this session's model; the tooling does not expose a more specific reviewer model ID. No alternate model provider was invoked. Each returned concrete paths, triggers and consequences against the same intent and rubric. The parent traced findings, reproduced them, inspected fixes and ran verification. Reviewers then cross-checked remediation they did not author; the two live Finder guard corrections also received bounded independent delta checks. These are separate contexts, not model-family diversity or gstack review receipts.

Applicable standards: root `AGENTS.md`, `CONTRIBUTING.md`, the five-directions implementation plan, durable-native usage and app-qualification boundaries, and the pstack review rubric. Requirement conformance was checked separately from correctness. Notebook predictions precede the tests that resolve them.

## Findings and repairs

| Finding | Trigger and consequence | Final correction |
| --- | --- | --- |
| P1: unqualified second key | Opaque exceptions/error prose or mixed positively delivered replies containing an ambiguity phrase triggered a foreground retry | Only typed qualified no-send or the exact pinned SDK pre-actuator refusal can authorize escalation; all uncertain/contradictory outcomes retain the first result |
| P2: delayed Finder ownership check | Another window/selection could take over during Rename enablement; the process-global leaf or editor write could then target it | Fresh front/main/window/selection before Rename and exact editor ownership plus original inode before writing |
| P2: interrupted JSONL projection | A partial record remained in the repaired file and crashed subsequent readers | Preserve original bytes in quarantine, atomically retain readable records, and reproject canonical operations under authority ownership, including durable contexts |
| P2: legacy blocker status | A reused journal's unresolved non-operator row had no operator projection, making status fail | Explicit conservative legacy receipt with no invented operator proof; all unresolved rows remain visible, beyond the recent-display limit |
| P1 conformance: completion bypassed custody | Verifier acceptance could close a session with own/domain/context or unprojected legacy uncertainty | Deterministic custody checks precede key, app and provider access; participating context locks remain held through completion; corrupt legacy context evidence refuses explicitly |
| P1: first-ingress qualification race | A handler paused after its first commit could be reconciled before its headerless disconnect and later duplicate | v2 pre-binds response mode and requires an immutable supported header-flush event for the exact ingress; disconnect mode cannot qualify even at transient count one |
| P2: unrelated Chrome oracle | A receipt for submission A could be combined with a passing database/nonce B for the same image | Require the admitted v2 service receipt and exact ledger identity, origin, request fields and artifact, then recapture that bound source read-only |
| P2: receipt target overwritten | Foreground handback reused the candidate-target variable for a restoration PID | Keep restoration PID separate; both the requested target and correct handback are tested |
| P2: stale exact field fact | A cleared/shortened raw field or absent raw field with a matching display prefix preserved an earlier exact readback | Require exact fresh raw equality; missing raw values and every actual difference limit the earlier fact |

The first seven findings came from independent static review; the parent found the receipt-target defect while tracing the changed foreground helper. Their reproduction outputs are retained under [regressions](regressions/). Initial red runs observed eleven native failures, seven core failures, two context-log failures and three service/handoff failures; those groups overlap final suites and must not be summed as coverage totals. The parent target test independently observed the wrong restoration PID in `effect.target` before repair.

The first live review build stopped before Rename because the owned File menu legitimately moved focus to AXApplication and cleared AXFocusedWindow. The next stopped before writing because the transient editor replaced its original filename row. Both partial attempts remain unknown. Narrow corrections retain strict initial key-window checks, exact front/main/selection before Rename, and exact editor/name/geometry/window plus original inode before writing. Only the acknowledged File-menu stage accepts application focus without a focused-window ID. `file_row_missing` alone supplies no authority: existing AX helpers can also produce that label after a read failure, so the editor and inode checks remain mandatory. Fresh positive and adversarial public scenarios passed before another installed trial.

## Verified artifact and outcomes

Frozen runtime: `ddf133f020b65df5abdee854aefb0343382b73bc`. [Wheel manifest](candidate-ddf133f/manifest.json) and [runtime/module hashes](candidate-ddf133f/runtime.json) identify the offline-installed artifact. Its wheel SHA-256 is `d796055500e309d33318b58cbc319c28f37852a800bb62a89c9a8c0ab997ddfe`. The 189-file inventory was verified and all eight selected runtime module origins were inside the installed site; source hashes were compared independently. Existing host dependencies were used for native driving, so this is not clean-machine SDK onboarding.

Observed checks:

- [Full key-free suite](full-suite-verified.txt): **2245 passed, 26 skipped**.
- [Node inspection/transport tests](node-tests.txt): **97 passed**.
- [Ruff](ruff-verified.txt) and [103-file tool-resource snapshot](resources-final.txt): passed.
- [Dependency-free consumer package](consumer-package/receipt.json): deterministic wheel build, isolated offline installation and CLI checks passed. [Installed discovery](installed-discovery-verified.json) passed outside the checkout.
- [Live v2 nominal chain](trials/live-v2-nominal/summary.json): exact Finder rename/two-window move, persisted clockwise Preview pixels, one Chrome ingress and one matching supported response event, actual v2 service reconciliation, three completed handoffs and no extra request on replay.
- [Live v2 interrupted/truncated chain](trials/live-v2-interrupted/summary.json): the same task checks passed after real SIGKILLs at Finder→Preview, Preview→Chrome and after submission ingress before CLI result retention. All three injections returned `-9`; the last was observed to land. No returned native receipt/count was invented.

v2 service events record the response boundary after the handler actually flushes supported headers. A fixed sleep is not evidence; the harness can only poll read-only reconciliation for that positive event. A paused pre-header-disconnect regression remains unknown before and after handler release. The transport cause is not investigated or suppressed by this PR.

Historical v1 final ticket receipts remain readable and replayable without source I/O or raw-record changes. A v1 unknown, including one with an old retained service receipt, cannot finalize under v2. New Chrome handoffs reject v1 service contracts and generic click-only evidence. The legacy completion-effect projection is not extended into a universal submission producer.

## Hosted review correction

GitHub's automated review on `5a55006` identified the stale exact-field comparison. Five new regressions failed before repair: cleared raw value, shortened prefix, leading/trailing whitespace changes and missing raw value with a matching display preview. The previous long-value fixture also confused the complete raw snapshot with its shortened display; it now retains those separately and continues to qualify matching full raw content.

Runtime `497c2f63ab1eb95e641ca7248ee32a3e6a1cb3da` requires fresh raw equality. The [full suite after correction](full-suite-review-fix.txt) passed **2250 tests, with 26 skipped**; Ruff and the notebook checker passed. [Red/green regressions](regressions/exact-field/) retain the failure and **337 passing** session/completion/evidence/scenario checks. Lossy driver normalization may now conservatively limit an earlier exact fact; normalized or display-prefix equivalence supplies no exact-current-state authority. The [offline consumer package](review-fix/consumer-package.json) passed with wheel SHA-256 `038064a8162c7d4820548bf2f2c33d6fd864c55e986dad9fe6008012343c4a78`.

The installed live results above remain bound to `ddf133f`; they were not rerun for this correction. [Source hashes](review-fix/source.json) distinguish the artifacts: native targeting is unchanged, and this correction only tightens structured field readback facts. Finder move, Preview save and Chrome service reconciliation retain their independent task checks. New PR-head CI must be observed separately.

## Accounting, limits and release verdict

[Four live trajectories](trials.json) retain the two conservative guard failures and the two successful fresh chains. [Cleanup](cleanup.json) confirms the two new uncertain operations are retained, all eleven historical package unknown rows retain their prior hashes, both successful saved images still pass independent pixel checks, owned listeners are closed, and shared Finder/Preview remain alive. Only verified owned helpers/windows were retired; unrelated worktrees were not altered.

Support remains limited to fresh owned fixtures under the user-reserved `exclusive_desktop` posture. The semantic browser's durable incarnation, generic folders/origins, active-human coexistence, arbitrary repeated Preview rotations, power-loss durability and independent SDK onboarding remain outside these claims. The original pre-header duplicate-ingress qualification gate stays open. Merging the experimental operator and its safer recovery contract does not mark that gate passed.

Verdict: no remaining blocking findings in the reviewed and corrected scope. Local behavior, independent review and installed proof are checked. Hosted CI and the exact PR-head merge must be observed separately before claiming the work landed. No provider calls, cloud changes or deployment were part of these checks.
