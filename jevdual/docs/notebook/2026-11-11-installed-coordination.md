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
