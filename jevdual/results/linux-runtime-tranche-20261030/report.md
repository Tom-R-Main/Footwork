# Linux runtime tranche — Debian VM, 2026-10-30

Units 1–3 of the [source-grounded plan](../../docs/linux-next-tranche.md) are implemented and exercised in this Codex Cloud Debian 13/native x86-64 VM. The final implementation is `07297b8`; later commits add tests, documentation and evidence. CUA remains pinned to `d5373879` / `0.38.0+footwork.d5373879`. Application/Wayland expansion and shared-user foreground authority are unchanged.

## Installed SDK receipt

A fresh `ad60bae` wheel matched all 191 installed files. The [real broken-WM repeat](ad60bae-refused-profile.json) now reports **refused, dispatched=false, delivered_count=0, readback=null**, with unchanged independently checked disk bytes. The [working control](ad60bae-working-profile.json) passed the documented CLI/MCP/replay/restart/save/artifact journey. Both public SDK envelopes are retained. The qualification harness deliberately exits at its no-dispatch save guard in the refusal case; that expected nonzero harness status is not a failed receipt assertion.

## Bounded X11 session

`jevdual.linux_session` replaces the fixture shell's implicit lifecycle. It reserves an unused display, creates fresh private XDG config/cache/data/state/runtime directories, owns its session D-Bus and retains process handles plus observed kernel start identities. An optional explicit rootless prefix supplies desktop library/data/config paths without deleting ambient user settings.

One monotonic startup deadline covers staged, independently bounded subprocess probes: X handshake, private D-Bus, a live WM selection, accessibility-bus access, and the unique explicit Mousepad document with exact fixture text. The marker is published only after those checks. Recovery modals and root-only trees refuse readiness. After startup, critical children are monitored and bounded WM/accessibility health checks reject a changed bus identity.

Cancellation or component death performs bounded TERM then KILL escalation on owned groups and observed incarnation-bound descendants. It reaps only direct child handles. Forced cleanup, live survivors and orphan zombies are separately recorded. Container init handles adopted orphans; no global competing reaper is introduced. The [outer VM run](lifecycle-native-dev.json) stopped every observed running descendant but recorded four zombies under its `tail` PID1. The init-container repeats reported **no live survivors and no zombies**.

`host_probe.py` additionally records bounded visible PID limits/current/events, memory/swap counters and selected PID1 facts. Missing/delegated/hidden facts remain unknown; snapshots do not reserve capacity or establish actual reaping behavior. A stale-root PID classification regression [failed before](pid-reuse-before.txt) and was corrected in `bb37205` before final qualification.

## Linux browser recovery

The public CLI scenario [reproduced macOS open on Linux](browser-recovery-before.txt) before replacement. The Linux route now launches the qualified ELF executable with the exact owned profile and debugging port, uses monotonic startup/window/attachment deadlines and rechecks process incarnation throughout binding. Failed/cancelled attachment closes the driver and reaps only newly owned launches/helpers, preserving reused browser roots. Tests cover early exit, failed spawn, cancellation, unrelated windows, replaced identities, conflicting roots and executable/profile/port/UID checks.

The [native final run](container-final/acceptance.json) closed every page window while retaining the owned Chromium root. Public `browser start` recovered a visible window with the **same PID, incarnation and profile**. No macOS launcher, identity exception or mutation retry was used.

The initial container repeat found a separate prerequisite issue: Chromium checks sandbox setup even in secondary singleton helpers. [Actual helper stderr](recovery-helper-sandbox-stderr.txt) shows this container's namespace/no-new-privileges restrictions. The test root had explicitly selected `--no-sandbox`. Recovery now preserves only that already-explicit flag from the same qualified root after incarnation validation. It does not copy arbitrary arguments or disable the sandbox for normal launches. Absent sandbox flags and changed identities have explicit regressions.

## Consumer and constrained acceptance

[Installed identity](final-installed-identity.json) verifies all **192** packaged files; [source-to-wheel verification](final-source-wheel.json) also passes. Binary consumer installation avoided Rust compilation. The product wheel is `c1158f450319bd78b33edc085316369766a353019d49e8b4f3a468749f3f985f`; the reused native CUA wheel is `0595b6042a98538b3c79ddef07301dd9481e477a5fbf64278b6cc63c2ed474c9`. Dependencies and package hashes are retained. The final bundle and consumer remain at `/workspace/scratch/footwork-runtime-final-bundle` and `/workspace/scratch/footwork-runtime-final-consumer`.

The [container configurations](container-configurations.json) record `--init`, **512 PIDs, two CPUs, 3 GiB memory, zero swap**, 512 MiB shared memory, dropped capabilities, no-new-privileges and disabled external networking. The thin Debian 13 image uses selected read-only mounts of this VM's public application/runtime libraries, checkout, sysroot and installed environment; this is not a standalone release-image build. Private fixture passwd/group entries supply UID 1000 for D-Bus authentication. No host desktop socket or API credential was supplied. Containers share this VM's kernel.

The final installed CLI/MCP append, browser read, duplicate prevention and restart agreement passed. Scoped native save plus independent public artifact checking confirmed **109 codepoints / 117 UTF-8 bytes**, SHA256 `4c833c0e33e3cc5bde92d43db38d935f65dce6918d78e0ee88f4eec72edb7d3c` ([receipt](container-final/receipt.json), [file proof](container-final/saved-artifact.txt)). Save remains the documented direct bridge route, not a provider-backed public save journey.

[Native failure cases](native-fault-summary.json) cover cancellation before readiness, an actual occupied X server which survived refusal, missing rootless WM dependencies and private accessibility-bus replacement. The [main acceptance](container-final/acceptance.json) also covers Xvfb/session-bus/editor death. The supervisor rejects each failed startup or changed identity without input. Process tests cover TERM-ignoring children and orphan grandchildren under the same 512-PID cap. The successful final run recorded **zero PID-limit hits and zero OOM events**, without live cleanup survivors or zombies.

## Validation and retained failures

| Check | Result | Evidence |
| --- | --- | --- |
| Final implementation non-browser suite | **2,479 passed, 28 skipped**, 13 deselected | [output](final-full-tests.txt) |
| Final implementation browser suite | **13 passed**, no skips | [output](final-browser-tests.txt) |
| Corrected lifecycle/browser/session focused tests | **207 passed** | [output](corrected-focused.txt) |
| Lifecycle/resource tests inside 512-PID init container | **27 passed**, cache-write warning from read-only checkout | [output](container-final/lifecycle-tests.txt) |
| Additional native stalled-Xlib handshake and root-only tree tests | **2 passed**, added after the full-suite snapshot without product changes | [output](handshake-and-root-tree.txt) |
| Ruff, 103 tool-resource comparisons, notebook validator/tests | Passed | [lint](final-ruff.txt), [resources](final-resources.json), [notebook](final-notebook.txt), [tests](final-notebook-tests.txt) |

Earlier results remain separate: the pre-correction full suite passed 2,475 tests and 13 browser tests, but its live helper failed; those passing suites did not qualify the final recovery. The outer non-init run's orphan zombies, initial stale-PID regression, first container's missing passwd entry, and helper sandbox failure are retained. An initial diagnostic container mount layout also hid Docker's injected init binary; corrected selective public-runtime mounts preserved it. A later fault-injection script tried to select the accessibility daemon from current parent relationships and found none after reparenting; the corrected fault selected its PID through the exact private D-Bus service, then observed `accessibility_bus_changed`. That script failure did not establish a product failure or relax any identity check.

The updated [Linux guide](../../docs/linux-support.md) describes supervisor startup, readiness and cleanup. Orchestration programs and selected source/runtime hashes are retained in this run directory. Temporary owned fixtures/containers are stopped. The running-process guarantee covers owned groups and observed descendants; unseen processes which escape before observation are not covered. A nested X server does not establish physical-seat lock safety. Wayland, new application contracts, physical devices, provider-backed planning and hosted CI were not exercised.

## Publication boundary

During this run, the shared `codex/linux-support` branch independently advanced to `65996ad` with a separate implementation of the same tranche. This report qualifies this VM implementation at `07297b8` and its exact wheel; it does not claim VM validation of `65996ad`. To preserve both histories, the tested code and evidence are published on `codex/linux-runtime-cloud-tranche-20261030`, with no conflicting implementation merge or overwrite.
