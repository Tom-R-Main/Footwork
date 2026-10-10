# Fresh dependency installation and setup

## UI1 · prediction · 2026-10-10 16:34
Hypothesis: the current pure wheel and pinned driver seams resolve as binaries in a fresh macOS arm64 environment without borrowing installed dependencies or compiling Rust, and the installed capability worker remains usable.
Test: U1 empty-cache default Python3.14 and Python3.12 dependency installations, consistency/origin probes and owned real native consumer flow on a supported profile.
Predicts: at least one profile resolves full declared dependencies, all product/dependency imports originate fresh environment or stdlib/system frameworks, and actual installed append/restart-token/report evidence passes. Any unsupported profile is explicitly retained.
Against: no profile can resolve pinned binary dependencies, an undeclared runtime prerequisite is needed, code needs source/borrowed environment or effect/recovery/report semantics regress.
Refs: docs/experiments/U1-clean-installation.md; results/capability-packaging-20261010/report.md

## UIU1 · update · 2026-10-10 16:36
Observed: both v1 fresh environments are created with system-site disabled, but install stops before resolution because the installed uv rejects combining --only-binary with --no-build. No dependency/runtime result is established. Reference review recommends isolated binary-only installation, structured doctor blockers/strict exit and exact emitted MCP startup checks. It also flags newer Cua doctor destructive cleanup and an incorrect newer browser-use platform marker; neither will be adopted.
Next: retain v1, use --only-binary :all: alone (same no-source-build policy), freeze and run separate v2 profiles. Reproduce doctor prerequisite reporting before adding opt-in strict readiness.
Refs: output/u1-py314-v1/install.stderr.log; output/u1-py312-v1/install.stderr.log; local reference Cua doctor.rs571; open-codex-computer-use install-config-helper.mjs613

## UI2 · prediction · 2026-10-10 16:36
Hypothesis: structured prerequisite blockers and an opt-in strict exit make incomplete installs diagnosable without mistaking diagnostic success for operational readiness or granting permissions.
Test: public doctor with missing/incompatible dependency or permission/platform/scope prereqs, unknown ledger and normal supported profile; compare diagnostic0 vs strict1, inspect runtime provenance, and require actual emitted MCP command plus bind for resource qualification.
Predicts: strict mode refuses incomplete/unknown prerequisites, normal diagnostics retain their behavior, no resource/input/permission/journal mutation occurs, and prerequisite status never certifies window identity, effects or job completion.
Against: false prerequisite-met output, strict mode accepts a blocker or doctor starts apps/requests permissions/reconciles; startup is checked with a reconstructed command instead of emitted configuration.
Refs: docs/experiments/U1-clean-installation.md; python/jevdual/capability/setup.py; local Cua structured probe mechanism and open-codex-computer-use startup probe

## UIU2 · update · 2026-10-10 16:41
Observed: v2 binary installs pass on actual Python3.14.5 and3.12.6, each115packages, consistency checks and fresh-site import probes pass. /opt/homebrew/bin/python3 is3.14.5; the shell default is a different Framework3.14.7 interpreter. These runs isolate dependencies but still inherit HOME. A bare/no-deps installed doctor reports missing AX and unverified deps with exit0, confirming a need for opt-in strict prerequisites. Claude identifies HOME/config/telemetry inheritance, actual-process origin gaps and optimization-stripped asserts.
Next: retain v2 as dependency-only baseline, add private HOME/XDG/temp and explicit checks independent of -O, capture actual server/worker import context through optional private diagnostics, disable known browser-use telemetry/cloud-sync in generated host config, and qualify a fresh version including the real shell-default3.14.7 profile.
Refs: output/u1-py314-v2/receipt.json; output/u1-py312-v2/receipt.json; output/u1-doctor-bare-v1/receipt.json; Claude mailbox1791664577072686000

## UI3 · prediction · 2026-10-10 16:41
Hypothesis: explicit private HOME/XDG/temp environments, no-optimization-dependent gates and runtime context emitted by the actual installed server/worker remove the borrowing paths exposed by the initial harness.
Test: fresh v3 profile installs with actual binary tags/cache-size evidence; exact generated command runs under private environment and private opt-in runtime audit; optimized negative guard test and installed native postconditions.
Predicts: no configured dependency/source/home/cache borrow, actual server/worker origins/dylib remain in fresh venv, known browser-use telemetry/cloud sync are disabled, and -O cannot bypass a gate. Diagnostics are separate from authority/receipts and their absence never certifies installation.
Against: HOME-resident helper/config or source imports are needed, a gate vanishes under optimization, actual running origins disagree with probes, or added diagnostics alter input/recovery/report semantics.
Refs: scripts/capability_clean_install.py; scripts/capability_installed_trial.py; docs/experiments/U1-clean-installation.md

## UIU3 · update · 2026-10-10 16:50
Observed: v3 full binary/profile installs pass on Framework3.14.7 and3.12.6 with private state/cache; strict prerequisites pass. Native3.14 v1 executes one applied append plus restart-token collection, then correctly rejects its actual-process HOME evidence: the harness passed a relative isolation-root, so child HOME is relative rather than the intended private absolute directory. Claude reproduced a product cwd-shadowing blocker: generated server and worker -m commands can import planted cwd packages, despite cleared PYTHONPATH. Full current suite1484pass/27skip; that does not cure this launch defect.
Next: retain nativev1, normalize isolation-root before building env; add -I to generated server/report and worker invocations, plant shadow packages in the native host cwd, freeze/rebuild/requalify separately.
Refs: output/u1-native-py314-v1/runtime-context; output/u1-py314-v3/receipt.json; output/u1-py312-v3/receipt.json; Claude mailbox1791665246732519000

## UI4 · prediction · 2026-10-10 16:50
Hypothesis: isolated Python invocations prevent cwd/Python-env shadowing across the actual server, detached worker and authoritative report adapter, preserving venv identity and non-Python private-state settings.
Test: installed -I server/worker/report against planted jevdual/psutil/mcp/cua_driver cwd packages, with explicit actual-process audit and a positive native append/restart/report oracle; compare plain -m shadow baseline.
Predicts: plain -m baseline imports the planted package; generated -I commands use only installed modules even in the shadow cwd, private HOME remains correct and one effect/record plus conservative report semantics hold.
Against: any planted/source module is used, worker/adapter loses installed dependencies/venv, HOME mismatch persists or launch isolation alters durable effect/recovery/report behavior.
Refs: python/jevdual/capability/setup.py; python/jevdual/capability/recovery.py; scripts/capability_installed_trial.py
