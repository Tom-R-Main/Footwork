# CUA 0.46 integration and native form acceptance

## C46P1 · prediction · 2026-11-09 21:36
Hypothesis: the published CUA0.46 SDK/native pair can replace the older custom reference after adapting documented contract changes, provided its shutdown cleanup preserves the locally patched guarantees; Footwork form fixes still require explicit projection and action-boundary validation.
Test: compare the exact release source with the cleanup2 patch, install the matched published wheel in an isolated project-owned environment, run pinned contracts and deterministic regressions, then exercise an owned local Chrome form through the public native CLI. The fixture includes repeated row actions, a late dropdown, empty placeholders, dynamic nameserver rows and save/reload persistence with an independent server ledger. Inspect the actual Namecheap page read-only if accessible, without editing DNS. Merge only the verified final source and audit branch/artifact ownership before cleanup.
Predicts: narrow ABI adaptations plus retained/new upstream safety behavior pass source and installed contracts; the real native fixture exposes and safely addresses all reported controls, refuses stale dynamic targets, records nondispatch failures and proves persistence independently of click receipts.
Against: upstream omits a required cleanup guarantee, its ABI requires an unsafe compatibility fallback, a native fixture action lands on the wrong backing row, placeholder text becomes an entered value, an early refusal disappears from the log, or a save receipt is claimed without server/reload evidence. Simulated tests cannot substitute for the native acceptance run.
Refs: docs/notebook/2026-11-09-native-form-targeting.md; results/native-form-targeting-20261109/report.md; vendor/cua-driver/PROVENANCE.md; https://github.com/trycua/cua/releases/tag/cua-driver-rs-v0.46.0

## C46U1 · update · 2026-11-09 21:39
Resolves: C46P1 = failed
Observed: exact upstream0.46.0 source still spawns untracked browser and protected-grant session cleanup, and runtime shutdown does not drain those tasks. The published matched macOS SDK/native wheel imports successfully but does not preserve Footwork cleanup2. Its ActionResult constructor adds required fast_path metadata; the baseline contracts caught that and the old version pin.
Inferred: installing the stock wheel would regress a known native lifecycle guarantee. Its import success and form tests cannot qualify that guarantee.
Next: retain the cleanup2 patch on the0.46 source, build the matched patched SDK/native wheel, and validate its cleanup regression plus public native form behavior before adopting it.
Refs: output/cua-046-upgrade/contract-baseline.txt; vendor/cua-driver/patches/session-cleanup-join.patch; upstream5486b624; source review runtime.rs285-302, browser/engine.rs705, tool.rs1379

## C46P2 · prediction · 2026-11-09 21:39
Revises: C46P1
Hypothesis: the bounded cleanup2 task-ownership patch can be carried onto0.46 without changing its new input-authority semantics, while its generated Python/native ABI remains matched.
Test: regenerate exact patched provenance, compile the release wheel with the pinned installed compiler, run cleanup task completion/cancellation/reaping regressions, install that wheel, then run complete Footwork contracts and owned live native form acceptance. Keep build/cache writes in the project and monitor free space.
Predicts: patched shutdown waits for all registered cleanup work and preserves abnormal-task failure, the wheel imports with its exact distribution pin, Footwork tests pass and the local form satisfies all report acceptance checks.
Against: patch conflicts require broad authority changes, compilation or lifecycle regressions fail, the installed artifact differs from the retained build, or actual native form operation remains incomplete or unsafe.
Refs: vendor/cua-driver/PROVENANCE.md; docs/upstream/cua-driver-build.md; output/cua-046-upgrade

## C46U2 · update · 2026-11-09 21:46
Observed: the patched0.46 CLI/SDK release build completed successfully with the installed upstream-pinned compiler. Independent review verified896 archived files, exactly four cleanup changes, unchanged Cargo dependencies and byte-matched release Python bindings. The stock-wheel full suite reported2924 passes and only the two expected old-version/ActionResult-constructor failures; those seams are updated for the custom distribution. The owned native fixture runner passed nine offline tests and its JavaScript syntax check, but has not yet driven Chrome.
Changes: dependency and lock advance only the CUA version; preserve prior provenance under vendor history. Add the independently journaled localhost form runner. Resolve the nine previously reported IR1 lint issues through import ordering, explicit subprocess return-code handling, diagnostic exception annotations and journal context management; these archived harness edits were linted/compiled, not replay-qualified.
Next: package through the verified archive build hook, run cleanup lifecycle tests and installed contracts, then execute actual native form acceptance at the committed source snapshot.
Refs: output/cua-046-upgrade/build-native.txt; output/cua-046-upgrade/initial-pytest.txt; scripts/native_form_acceptance.py; tests/test_native_form_acceptance.py; vendor/cua-driver/history

## C46U3 · update · 2026-11-09 21:50
Observed: the built custom wheel is installed in the actual project environment. Native fixture run1 correctly refused unqualified MANAGE and dispatched its qualified alpha-domain link, verified by the server ledger. The runner had opted into durable authority, which then correctly blocked further actions because the generic SDK click returned unverifiable delivery. The reported Namecheap journey used ordinary native sessions, so run1 does not resolve the form acceptance question. Its browser was closed and its unresolved journal retained; no uncertain input was replayed.
Changes: align the fixture with the original ordinary native route on a fresh owned browser PID/profile, retaining its exact nonce title and independent localhost ledger. Do not relax production durable gates. Runner results explicitly withhold durable qualification. Three native cleanup task ownership/reaping regressions also passed on the exact patched source.
Next: rerun the six form acceptance checks using the corrected route and fresh fixture; finish SDK lifecycle and source checks.
Refs: output/cua-046-upgrade/live-1; output/cua-046-upgrade/cleanup-core-tests.txt; scripts/native_form_acceptance.py

## C46U4 · update · 2026-11-09 21:59
Resolves: C46P2 = held
Observed: patched native cleanup tests pass (three core, one SDK). The SDK regression needed only a test-local AtomicBool import removed by upstream; the rebuilt final archive and wheel retain identical production logic. The actual installed environment passes all60 seam/build contracts and the full Python suite passed2935 tests with51 skips and66 deselections. Real Chrome acceptance passed seven checks in23 commands twice: editable source and the final freshly installed binary-dependency bundle. Independent server state confirms four backing fields persisted after reload with beta unchanged. Ruff and tool-resource synchronization pass.
Inferred: the retained cleanup patch preserves its tested ownership guarantees on0.46, and the reported form-targeting defects satisfy the original ordinary-native acceptance criteria on an owned local Chrome fixture.
Next: finish hosted CI, publish consolidated main and retire branch refs only after verifying their archive tags. Retain local evidence and unresolved durable journal.
Refs: results/cua-046-native-forms-20261109/report.md; output/cua-046-upgrade/live-final; output/cua-046-upgrade/wheel-manifest-final.json; docs/branch-archive-20261109.md

## C46S1 · summary · 2026-11-09 21:59
Established: CUA0.46 custom cleanup build, matched native/Python artifacts, source contracts, lifecycle regressions and real installed native form acceptance pass. Stock0.46 was rejected because its cleanup guarantee is insufficient. The bug fix required Footwork projection, identity and audit changes in addition to the dependency upgrade.
Uncertain: actual Namecheap provider page was unavailable and has not been requalified; no DNS edits occurred. Durable native delivery is not qualified by the ordinary-native fixture. Hosted CI is pending at this boundary. Generated external build caches lack a supported cleanup-adapter qualification and remain retained.
Decision: adopt the exact patched dependency and form fixes subject to hosted CI. Preserve seven historical tips as verified remote archive tags before retiring branches; keep the sealed and rejected experiments separate from adopted runtime code.
Refs: results/cua-046-native-forms-20261109; docs/branch-archive-20261109.md; output/cua-046-upgrade/cleanup-plan-pre-release.md
