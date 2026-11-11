# Merge and installed macOS coordination qualification

## MCI1 · prediction · 2026-11-11 11:02
Hypothesis: a fresh full-profile wheel/bundle built from the merged qualified source can replace the user-local release without checkout imports, missing coordination modules, dependency drift or modification of the previous release.
Test: merge through a PR after required CI succeeds. Build a fresh bundle from the exact merged source with the already qualified cleanup2 CUA wheel, install into a new versioned release, verify wheel/installed hashes and installed discovery/doctor/schema from an owned non-checkout directory, then atomically switch the existing current symlink. Retain the previous release and stable launcher bytes. Verify source/runtime identities before native input; no global skill/memory edit.
Predicts: installed product and CUA bytes match their wheels, exact pin is retained, installed control/discovery commands use the new release independently of cwd/PYTHONPATH, and current resolves only to the intended complete release.
Against: checkout shadowing, missing modules, source/SDK/hash drift, a changed prior release or launcher, failed installed discovery, or partial activation.
Refs: results/macos-coordination-20261111-fix/REPORT.md; scripts/build_agent_bundle.py; /Users/thomasmain/.local/share/footwork/current/footwork-release.json

## MCI2 · prediction · 2026-11-11 11:02
Hypothesis: the stable user-local installed CLI preserves the tested macOS reservation fairness, recorded pointer approach, independent background edit, cancellation and stale-token handoff behavior of source768967a.
Test: adapt the existing synthetic native fixture runner to invoke only /Users/thomasmain/.local/bin/footwork for product commands from an owned non-checkout directory. Confirm installed import/source/wheel/SDK identities, exact owned targets and actual macOS idle/unlocked state; run the15criteria with real pointer recording and independent AX/Quartz/page readback after explicit user desktop handoff. Retain failures and diagnostics without lowering timing gates or changing SDK/native entrypoints. Clean up only owned processes and tokens.
Predicts: all15installed public-CLI criteria pass, the film owner completes while its competitor still waits, and pointer motion reaches the observed target while the independent text/focus remains exact. No active owned request or reservation remains afterward.
Against: installed execution differs from qualified source, wrong resource/focus changes, valid owner stalls, a motion abort, revoked input, stale release, or incomplete cleanup. A packaging/doctor pass alone does not settle native qualification.
Refs: results/macos-coordination-20261111-fix/live_probe.py; results/installed-coordination-20261111/

## MCIU1 · update · 2026-11-11 11:24
Resolves: MCI1 = held
Observed: PR22 merged at f821f032a81ba567a4c20298789fae55f79edc78 with exact expected head a3f3ff5. Main is unprotected and has no required status checks or branch rules. Five hosted checks pass, including both macOS full consumer jobs; the Linux test job fails before product installation/tests because the runner cannot resolve Ubuntu package mirrors, and the Linux consumer job remains in prerequisite installation. This status was disclosed before/after merge; no CI result is labeled successful by substitution.
Observed: the committed head and actual merge have the same source tree c0fdea1798105147ae4f4fb0617ebb1ac2292a30. A new full bundle reuses the hash-verified exact cleanup2 CUA wheel. The offline candidate install initially refuses missing cached pinned dependencies; an authorized binary-only network install prepares the cache. The final versioned release installs offline. Candidate, inactive final release and active stable-launcher verification match all218Footwork runtime/resource files and8CUA files to the wheels. Installed discovery, doctor, control schema/status and six unified discovery/simulator checks pass from a hostile owned cwd outside the checkout. The stable launcher bytes are unchanged and current atomically selects the new complete release; the old release remains unchanged/available.
Next: finish MCI2 via the stable launcher after the user's pending desktop handoff; installed native pointer behavior is not inferred from byte/package checks.
Refs: results/installed-coordination-20261111/activation.json; results/installed-coordination-20261111/active-verification.json; results/installed-coordination-20261111/unified-cli.json; results/installed-coordination-20261111/linux-ci-failure.json; output/installed-coordination-20261111/

## MCIU2 · update · 2026-11-11 11:32
Resolves: MCI2 = failed
Observed: the first stable installed-launcher rehearsal passes12of15criteria. The reservation owner completes while its competitor still waits; native background append/focus, observe-only, revocation and stale-token checks pass. The approach posts19samples then safely refuses pointer_contended:pointer_moved; endpoint and hover checks consequently fail. Recorded maximum successful gap34.0ms, maximum post32.7ms and stall_gap=null distinguish this from the earlier playback-stall refusal. Actual imported product/SDK paths are the new installed release, and all requests/reservations and owned apps are cleaned up. The refusal does not establish whether another actor moved the pointer or queued own events lagged readback.
Next: one separately preregistered capture-readiness contrast. Keep this failed cold-start attempt; do not infer cause or relax geometry/timing guards.
Refs: results/installed-coordination-20261111/live-cold-capture.json; output/installed-coordination-20261111/native/rehearsal.mov

## MCI3 · prediction · 2026-11-11 11:32
Hypothesis: immediately starting recording alongside the timed installed approach can contribute to transient pointer/event-readback contention; allowing capture setup to settle may permit the same guarded approach without changing core input behavior.
Test: one fresh task-only take through the unchanged installed stable launcher, same target and independent background append, with1.5seconds of capture setup before timed motion and an8second recording. Retain both attempts. No source/SDK/guard change or arbitrary repeated retry. Check exact endpoint/hover and the full15criteria, then cleanup.
Predicts: if capture startup contributes, the ready-capture take reaches its exact target without guard refusal while the cold attempt remains failed. A single contrast can qualify this tested setup but cannot establish universal causality or reliability.
Against: pointer contention recurs, another guard refuses, or independent state/focus/cancellation changes. Do not call cold-start capture qualified from a later pass.
Refs: results/installed-coordination-20261111/live_probe_warm.py; results/installed-coordination-20261111/live-cold-capture.json
