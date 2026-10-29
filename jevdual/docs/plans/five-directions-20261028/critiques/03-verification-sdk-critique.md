# Critique of Plan 3: verification SDK

Reviewed October 28, 2026 against `main` at `5d494c6`. Read-only: source inspection plus `tests/test_artifacts.py` (5 passed). No live apps or model calls were run. Paths are relative to `jevdual/`.

**Verdict.** The deterministic core is real, and it is smaller and more decoupled than the plan says. The product thesis has an internal contradiction: the plan's most distinctive claim families need evidence that only Footwork's own executor or capture stack produces.

## 1. Factual claims

| Claim | Status | Evidence |
| --- | --- | --- |
| Artifact check is digest-bound, makes no model call and uses no provenance | Holds | `python/jevdual/artifacts.py:42-67`; stdlib-only imports at `:3-9` |
| Symlink, mutation and size refusals exist | Holds, partly | `artifacts.py:22-37`. `O_NOFOLLOW` refuses only a final-component symlink. A symlinked parent directory is followed. |
| Capability completion reads a full bounded ledger | Holds | `capability/completion.py:86-128` (LIMIT 257, overflow refusal); read-only open with an identity check at `:205-228` |
| A2 separates a retained receipt from matching text | Holds | `results/operation-completion-20261010/report.md:8-10,14` |
| verify.py is coupled to TypeSafe and policy | Holds | `verify.py:28-43` |
| completion.py derives facts from receipt prose | Holds | `completion.py:32-34` (`_NAVIGATED`, `_HOLDS` regexes over `evidence` text) |
| The distribution installs browser-use and CUA | Holds | `pyproject.toml:15-26` |
| D1 argues against swapping the backend | Holds | `results/d1-v2-dev-20261008/report.md:3,16` |

**Omissions that change the sizing:**

- `completion.py`, `capability/completion.py`, `carry.py:13-20` and `_pure/evidence_match.py:10-13` are already stdlib-only. Only `verify.py`'s module-level imports pull in heavy dependencies. "Extraction" (M1) is therefore mostly packaging and contract design, not untangling code.
- The typed split the plan proposes (current state, event, answer) already exists: `completion.py:31` `KINDS` and the `Effect` dataclass at `:83-99`, which carries `limits` and `usable`. The plan does not cite it.
- `carry.check_file` and `check_append` (`carry.py:192,251`; CLI at `session.py:1358`) are a line and append-delta oracle with a before snapshot. For hosts, this is a more useful predicate than whole-file equality, and the plan ignores it.
- The bounded JSON CLI that M3 proposes already exists as `footwork-capability report` (`capability/cli.py:84-99`). A stdlib wheel builder (`scripts/build_capability_wheel.py`) and an offline isolated install check (`scripts/capability_package_check.py:85`) already exist too.

## 2. Market and integration value

An external host can honestly get three things:

1. **Current file-byte or line equality.** This is genuinely direct, because reading a file needs only the stdlib.
2. **Historical operation outcomes.** These are available only if the host executed through Footwork's journal. The `operations` table is written by `capability/journal.py:38-49`. A host that "retains its own driver" produces no such journal, so for the target customer this claim family is empty.
3. **Atom presence in supplied text.** `extract_atoms` (`verify.py:167-195`) checks quoted spans, numbers and colon values. It does not test entailment. "Revenue fell 5%" is matched by a page saying "rose 5%". Worse, `ClaimCheck.supported` returns `True` for `narrative` sentences (`verify.py:91-92`). Exposing that property to external callers would produce endorsements.

The "directly collected DOM/AX observation" adapter cannot exist in a dependency-light package. Direct capture requires browser-use, CUA or pyobjc, which are exactly the dependencies the plan excludes. `capability/observations.py:38` also makes observation IDs process-local UUIDs. The honest scope is: direct file checks, plus supplied-evidence checks labelled as supplied.

The limits-on-claims design is sound, and it is the plan's best asset. Its weak spot is adoption. A2 found that every v1 host put action prose into the operation-ID field (`report.md:22`). Hosts do not honor evidence contracts unprompted, and the SDK cannot force publication through it, which the plan concedes.

## 3. Feasibility and sequencing

- M1 is small and independently shippable. It has a hidden packaging dependency: `jevdual` must depend on the new distribution, which changes `uv.lock`. The maturin `python-source = "python"` layout (`pyproject.toml:46`) will not ship a sibling package by itself.
- M2 mixes three unrelated adapters (journal, observation envelope, Jev). The journal adapter already exists. The observation envelope has no direct producer. The Jev adapter brings back typesafe-sdk and a key. Split M2, and drop or defer the envelope.
- M3's "host performs an action through its existing driver, then asks for permitted readback" would test only file readback. It cannot exercise the history claim family.
- M4 depends on a recruited independent integrator. The plan gives no source or budget for one.

## 4. Acceptance criteria

- "Zero unsupported endorsements" and "positive coverage meets the preregistered threshold" have no set size and no threshold value. They cannot be falsified until a later document fills them in.
- "Frozen-corpus equivalence" does not name its corpus. Use the existing `tests/test_artifacts.py`, `tests/test_completion.py` and `tests/test_capability_completion.py` plus recorded A2 journals.
- The M1 "isolated install without browser-use" check can be passed vacuously. The existing builder copies every `Requires-Dist` (`build_capability_wheel.py:69`) and the existing check installs with `--no-deps`. The criterion must be: the wheel's `Requires-Dist` is empty (or matches an allowlist), and a normal resolving install pulls in no browser-use, cua-driver, pyobjc or typesafe-sdk.
- M1–M3 have no notebook prediction or disconfirming outcome. AGENTS.md requires one before each substantive harness change. The plan defers all of this to a final sentence.

## 5. Risks and blind spots

- **Parallel copies of the oracles.** `_tool_resources/workbench-notes` and `desk-inbox-experiment/inbox.py:54` already carry their own `read_regular`. Extraction without consolidation adds a fourth copy.
- **Rust twin rule.** `evidence_match` has a native port (`_native.py:52`). The SDK must pin the pure twin or carry the equality test (CONTRIBUTING.md).
- **Overlap with Plan 1.** Plan 1 owns typed effect evidence in `receipts.py`. The M2 prose refactor would collide with it.
- **Overlap with Plan 5.** Plan 5's packet verifier duplicates "supplied evidence with declared provenance".
- **Missing result fields.** Resource identity (`st_dev`/`st_ino`) and observation timestamps are absent from today's artifact result (`artifacts.py:44-46`). The plan describes these fields as if they already existed.

## 6. Ideas worth keeping

1. **A typed result record:** `{predicate, check_version, source_adapter, provenance: direct|supplied, resource: {path, dev, ino}, observed_at: [start, end], digests, outcome: supported|refuted|unknown|unavailable, limits[]}`. Build it on `completion.Effect`.
2. **Never fold one claim kind into another.** A current-state fact, a historical event and answer support are never converted into each other. `unknown` survives interruption.
3. **A dependency-light distribution** containing `artifacts`, `carry` file oracles, `capability/completion` and the pure `evidence_match`. Gate it on empty `Requires-Dist`.
4. **Version semantic changes and never regrade.** A semantic change mints a new `check_version`, and old runs are never regraded.
5. **An "imported transcript is insufficient" negative fixture** as a standing conformance case.

## 7. Ideas to drop

- The DOM/AX observation envelope and "directly collected" observation adapters inside the light package.
- An answer-support claim family presented as "support". Rename it `atoms_present` and never count narrative.
- A new JSON CLI or MCP sidecar. Reuse `footwork-capability report`.
