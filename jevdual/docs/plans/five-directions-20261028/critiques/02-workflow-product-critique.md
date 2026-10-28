# Critique: Plan 2, source-to-note workflow

Reviewed October 28, 2026 against `5d494c6`. Read-only review; nothing was run.

**Verdict.** The evidence discipline is right, but the chosen job is wrong. A public page saved to a new plain-text file is the one case where computer use adds nothing, so it cannot test demand for Footwork. The runtime work is also much larger than "a modest extension".

## 1. Factual claims

**These claims hold.** The loopback-only, pid/window scope is at `capability/backend.py:40-63`. The persistence disclaimer is at `capability/contracts.py:69`. U2's post-grant fixture failed (`results/u2-…-v1/report.md:25`) and was not re-graded (`:29`). NOS1 is at `notebook/2026-10-28-native-observation-repair.md:36-38` (the plan cites `:35`). The bundle builder is at `build_agent_bundle.py:72-104`, and the save readback is at `native.py:1231-1243` and `1312-1343`.

**These claims are imprecise or overstated:**
- **Citation.** `report.md:5` only says `persistence not_checked`. The disclaimers of persistence, other hosts and cold setup are at `:9` and `:11`.
- **"Exact passage bytes".** The page text is a normalized accessibility projection, not page bytes. Whitespace is collapsed (`browser_driver.py:199`), repeated lines are dropped (`:200`), and text stops at 6000 characters (`:215`, `observations.py:78`). Values are clipped at 200 characters (`browser_driver.py:188`). An independent check needs a second way to read the page and a stated normalization rule. Re-reading the same projection does not count.
- **"Modest extension".** The job needs:
  - navigation to a remote origin;
  - file creation;
  - opening a document in TextEdit ("No apps or tabs are created", `contracts.py:75`);
  - a save operation (the service accepts only `append`, `backend.py:172`);
  - window discovery, where the scope is currently "trusted configuration" (`backend.py:3-5`);
  - a file-byte oracle.

  That is roughly Plan 1's milestone 4 (`01-execution-core.md:43`).
- **Save readback as a starting point.** `save_readback` compares the decoded file (`native.py:1330`) with the window's text (`:1334`), not with the expected note. A save of the wrong content therefore reports "confirmed". It also takes the foreground (`:1245-1250`). The byte oracle that refuses symlinks and binds a digest already exists at `artifacts.py:42`, and the plan never cites it.
- **Omitted evidence.** First Command-S readbacks are timing-sensitive: in G5, four of six read "differs" at 0.5 s (`native.py:1234-1236`).

## 2. Product value

- **No case needs a GUI.** A host can fetch a public page and write a cited `.txt` without any GUI. The cases where Footwork matters (authenticated pages, real note apps) are postponed (`02:13`).
- **"My research note" cannot be repeated.** Every job requires a *new* destination (`02:7`), and existing files are refused (`02:38`). Yet the plan also "preserve[s] existing note bytes" (`02:32`). Nobody can add to the same note twice, so the repeat-use phase is unmeasurable as written.
- **Demand evidence is a sample of one.** The test uses the author's own task (`02:28`), timed against copy-paste, which Footwork loses by construction. There is no primary metric (`CONTRIBUTING.md:11-14` requires one), no sample size, and the decision rule is deferred (`02:36`).
- **Cheaper demand test.** Before milestone 3, log by hand for two weeks every cited excerpt the user actually saves, and in which app.

## 3. Feasibility and sequencing

- **Discovery is filed as packaging but is a security change.** Milestone 2 hides resource discovery under packaging (`02:30`). Replacing trusted startup scope with selections the host makes changes the authority model. It belongs in milestone 3 with its own prediction.
- **Line 13 contradicts itself.** It says "begin with … public HTTPS page" and also "qualify redirects … before offering remote pages". Run the loopback version end to end first.
- **Chrome first launch is a known failure.** It caused U2's failure (`report.md:25`), but only "missing-Chrome" is listed.
- **Recovery breaks across restarts.** Identity is keyed to pid and window (`backend.py:65-70`), so a job repeated over days loses recovery identity whenever an app restarts.
- **The reopen check adds little.** Close/reopen (`02:32`) adds GUI risk and no information beyond reading the bytes on disk.

## 4. Acceptance criteria

The zero-error targets are falsifiable but have little power at small n, which the plan admits. "Zero author coaching" conflicts with permission grants that only a person can make (U2 `:19-23`), so record grants as an expected human step. Name one primary metric, for example *share of independent first-use jobs ending in a byte-verified saved note, with zero wrong certifications*. Everything else is a guardrail.

## 5. Blind spots

- **Prompt injection.** Text from public pages enters the host's context.
- **Encoding.** UTF-8, NFC normalization and line endings are unspecified.
- **Plain text needs setup.** TextEdit defaults to RTF.
- **Focus.** Save takes focus from the user.
- **Charter conflict.** Recipes and job states drift toward the workflow layer that the October 9 direction excludes (`agent-superpowers-product-20261009.md:15`). Q9e did not earn adoption (`:72`).

## 6. Strongest ideas to keep

1. **Journaled save.** Save is its own journaled operation with its own evidence. An uncertain append blocks save and continuation, and a new token is not recovery (`02:15`, `02:38`).
2. **Exact quotation.** Requiring an exact quote keeps summarization quality out of the oracle (`02:5`). Add the normalization rule and a second read route.
3. **Job manifest.** It binds the observation ID, the passage digest, the destination, the append and save operation IDs, and the final artifact digest, checked by `check_artifact`.
4. **Two separate trials.** Run an already-permitted host and an observed denied-to-granted journey separately. Record every attempt and never re-grade one (`02:34`).
5. **Scenario list.** Changed source, wrong document, duplicate request, conflicting edit, save refusal and lost reply (`02:32`). These map directly onto `tests/test_session_scenarios.py`.
6. **Stop rules.** Any wrongly certified effect stops expansion. If users prefer copying by hand, revisit the premise (`02:40`).

## 7. Ideas to drop

- A public HTTPS page and a new TextEdit `.txt` as the first target.
- A new destination for every job.
- The GUI reopen check.
- The n=1 elapsed-time comparison.
- "Modest extension" as the scope estimate.
