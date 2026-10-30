# Linux session and browser recovery tranche — 2026-10-30

Implementation commits: `306f322` (browser recovery) and `fdada77` (fixture lifecycle and diagnostics). Notebook predictions were committed in `d4e00ec` before their tests.

Implemented the first scoped units of the [source-grounded plan](../../docs/linux-next-tranche.md): staged X11 readiness with fresh profiles, bounded owned-child cleanup, process/swap diagnostics and exact-profile browser recovery. Wayland, new document adapters, shared foreground and hardware remain separate gates.

## Installed behavior

The [installed package identity](installed-identity.json) checks all 191 package files against portable wheel SHA256 `ec26e4dd7c69bf5f5e219f668abc57329a7bbc0f1e4a7fe7d9d6287a5f322771`. It uses the existing pinned arm64 CUA wheel; no native dependency was rebuilt or fetched.

- [Public CLI/MCP journey](installed-journey.json): exact native append, owned browser read, duplicate prevention, restart agreement and independent saved-file checking passed. [Historical/current status](restart-status.json) remains separate from [saved bytes](saved-artifact.json). The harness dispatches save directly through the scoped exclusive native bridge; no provider-backed save or model-guard bypass is claimed.
- [Zero-window recovery](browser-recovery.json): the installed public startup command began with zero visible Chrome windows, opened one, retained the same PID/process incarnation, and left the reused root alive. Product launch flags did not disable Chrome's sandbox.
- [Lifecycle acceptance](lifecycle.json): two fresh-profile startups reached all four readiness stages and stopped on cancellation with no live retained components and no unresolved cleanup. A deliberately missing WM stopped before editor readiness, never published ready, and left no live known component. Its already-exited WM leader is conservatively recorded as lost identity in cleanup; that is not a successful signal to a missing process.
- [Real no-WM save refusal](refused-save.json): the newly installed correction reports refused/dispatched=false/delivered_count=0/readback=null. [Independent disk comparison](refused-save-check.json) confirms unchanged bytes after an unsaved append. This deliberately incomplete diagnostic session is never presented as a ready desktop.

## Target and sandbox boundary

Runs used the existing local Docker Linux VM, native arm64 Ubuntu 26.04/Python 3.14.4 and the cached task image, not the separate Codex Cloud Debian VM. CPU/RAM/process/shared-memory ceilings were two CPUs/3 GiB/512 PIDs/512 MiB. The final sandbox-capable container disabled swap, retained dropped capabilities and no-new-privileges, and used container init. Its Docker seccomp profile was explicitly unconfined to permit unprivileged user namespaces; [selected configurations](container-limits.json) retain that difference. This is an isolated test configuration, not a product requirement or recommendation for shared desktops.

The initial recovery run on the older restricted container failed before profile forwarding: [Chrome stderr](sandbox-prerequisite-failure.txt) diagnosed its unusable SUID sandbox helper. We preserved that failure and verified that unprivileged user namespaces were usable in a separate disposable container. The successful recovery then used normal product flags and Chrome sandboxing. No host sysctl, system package, SUID mode or desktop configuration was changed.

## Verification

- [Linux regression lane](linux-suite.txt): 2,437 passed, 72 skipped, 13 browser cases deselected.
- [Linux browser lane](linux-browser.txt): all 13 passed; two non-browser tests deselected.
- [macOS regression lane](macos-suite.txt): 2,433 passed, 76 skipped, 13 browser cases deselected.
- [Final Linux fixture tests](linux-lifecycle-final.txt): nine passed, including stalled/malformed readiness, cancellation during a blocked probe, critical component death, partial editor readiness, TERM-ignoring child and grandchild cleanup. This targeted repeat covers the final process-manifest revision after the Linux full-suite source copy.
- [Focused macOS checks](macos-focused.txt): 99 passed, six Linux process tests skipped. [Ruff](ruff.txt), notebook validation and packaged resource checks passed.

The first macOS full-suite attempt aborted during browser-use's import-time AppKit display query inside the filesystem sandbox. The same lane completed outside that sandbox; it excluded browser launches. The failed attempt is not counted as a pass.

Readiness probes are isolated and bounded. The supervisor monitors critical children, signals only retained owned groups, rechecks PID start identities and records forced/unresolved cleanup. Orphan reaping still belongs to the container init, and a process snapshot cannot prove every unobserved daemonized descendant disappeared. Browser cleanup owns direct launch/helper children and preserves discovered persistent browsers; it is not a global process reaper. OS spawn/process enumeration are not forcibly interruptible by the async deadline.

The source and wheel identities above bind these observations. Hosted CI and a fresh Codex Cloud repeat of this tranche remain unexecuted here. No merge, release, paid model call, cloud allocation or reference-repository modification occurred.
