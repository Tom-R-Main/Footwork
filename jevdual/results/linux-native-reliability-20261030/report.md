# Linux native reliability — Debian x86-64 VM

This tranche starts from merged main `52601b1`. It reproduces the public browser recovery's post-success native abort and repairs its unjoined session-end cleanup. It also adds probe phase/exit evidence, a WM client-service acknowledgement before editor launch, and bounded sole-owner direct-child joins. Identity, consent, pidfd-only signaling, incomplete-inventory uncertainty and Chrome sandbox defaults remain intact.

**Qualification is still running.** The corrected product source is `6ff8370`; final status and exact denominators will be appended here before merge. The earlier candidate's failed cleanup attempts remain failures.

## Demonstrated native cause and patch

At diagnostic product `5324f6f` with the original native CUA wheel, the real installed public zero-window recovery completed its application work and explicit `driver.shutdown()`, emitted success JSON, then received **SIGABRT (-6) in 2/10 attempts** ([attempts](recovery-isolated/attempts.json), [captures](recovery-isolated/captures.jsonl)). All ten retained the same strict browser root identity. The plain minimal create/list/observe/shutdown experiment completed **40/40 processes**, three driver cycles each; it lacked the configured browser host/session-end path.

Normal GDB startup yielded 0/30 aborts and changed timing. A diagnostic native signal handler therefore stopped only after an actual SIGABRT had begun, permitting attachment to that owned process. One of ten public attempts aborted; its numeric -6 and complete native stacks remain ([capture](recovery-capture/captures.jsonl), [signal handler](harness/reliability-abort-capture.c)). No synthetic abort was injected. The stack identifies the `BrowserEngine::new_with_runtime_services` session-end task on `async-compat/to`, glibc forced-unwind cleanup through Tokio's panic catcher, and the main thread in `Py_FinalizeEx`.

The pinned source's synchronous session revocation schedules browser socket/grant release and protected-consent cleanup without joining those tasks. Their engine/provider captures can outlive explicit SDK shutdown and cross into a foreign destructor during interpreter finalization. The fix owns both hook tasks in the runtime's `ApprovalBroker` and drains them after admission closes, lifecycle maintenance joins and sessions revoke. Awaiting handles stays cancellation-safe in the owner queue; task failure remains sticky. No arbitrary sleeps, exit suppression, extra Python shutdown call or dependency bump was used.

The proposed UniFFI continuation-race diagnosis was rejected: the pinned scheduler serializes callback completion, and all three baseline plus three delayed-continuation GDB tests exited normally ([captures](callback/captures.jsonl)). This negative result is retained.

The native SDK regression fails without the drain ([before](reliability-native-before-linked.txt)); **four shutdown tests** pass afterward, plus **two core cleanup tests** for completion, cancelled drains, separate owners and task failure ([SDK](reliability-native-sdk-after.txt), [core](reliability-native-core-after.txt)). Initial build/reference-borrow and rootless link failures remain in the build logs.

## Readiness and cleanup

Ten corrected-home admissions before the WM acknowledgement yielded **8 ready / 2 failed**. Another phase-rich ten yielded **9 ready / 1 failed**, with persistent zero qualified windows. A failed native/X11 observation found the editor unmapped, outside the WM client list and without WM_STATE while both editor and Openbox waited in their event loops ([captures](windowattrs10/captures.jsonl), [editor stack](editor10/captures.jsonl)). The matching Debian Openbox source publishes EWMH before subsequent startup work; publication alone does not demonstrate client service.

Startup now requires a disposable owned client's MapRequest to receive normal WM_STATE and client-list membership before Mousepad starts. The client is destroyed on completion/failure; ordinary health checks create no window. The added acknowledgement uses one second per attempt within unchanged startup/probe/grace bounds **30/3/2 seconds**. With the original native wheel, **10/10** fresh admissions passed after this change ([attempts](wm-ack10/attempts.json)). The exact internal cause of every historical overwritten target-timeout log remains unclassified; this evidence does not retroactively identify all old failures.

Probe attempts have unique result/stderr/phase files, fixed content-free phase names and monotonic times. Parent receipts distinguish numeric normal exit, signal, timeout phase, termination/escalation and final wait. Valid ready JSON cannot override a nonzero process exit. Exact document text is never placed in phase diagnostics. JSON remains on its own channel.

The first combined candidate `c43a044` completed all 30 admissions, all 90 worker driver cycles, and all ten public journeys/recoveries. Its strict acceptance nevertheless failed **3/40 attempts**: lifecycle26, lifecycle28 and journey5 retained an editor zombie with a pending direct wait. An extra nonblocking poll was insufficient. All three snapshot PIDs were absent at subsequent /proc inspection ([follow-up](final/cleanup-followup.json)); the original snapshots remain unchanged ([sessions](final/sessions.jsonl), [attempts](final/attempts.json)).

Source `6ff8370` uses the remaining existing cleanup grace to join each solely owned Popen child. It preserves pre-reap zombies and final numeric waits, and a pending direct wait sets cleanup uncertainty. It installs no global reaper and never waits unowned orphans. The deterministic waitability regression fails before this correction; **30 focused lifecycle tests** pass afterward. This establishes a concrete wait race, not the precise cause of the earlier arm64 snapshot.

## Frozen artifacts and constraints

Corrected product wheel SHA256: `a52b8db77f57b391f109dacd150a51dfe9cfe4a08ef0777ac47aa2f8b9230d21`.
Native wheel: `cua_driver-0.38.0+footwork.d5373879.cleanup1-py3-none-linux_x86_64.whl`, SHA256 `b94c00c0abda1b039e4dc3ce3f72217fe053544fbf3ec2d18a81dd7ef273fd11`.
[Fresh consumer byte identity](reliability-qualified-identity.json) compares every packaged product/native file. Product/native bundle and consumer paths are `/workspace/scratch/fw-reliability-qualified-bundle` and `/workspace/scratch/fw-reliability-qualified-consumer`.

The [native patch](../../vendor/cua-driver/patches/session-cleanup-join.patch) changes four Rust files over upstream `d5373879`; [provenance](../../vendor/cua-driver/patches/session-cleanup-join.json) records upstream/patched archive and file hashes. Generated Python bindings and Cargo dependencies remain unchanged. The supplied complete-file reference hashes were verified against the original pinned archive before changing it. Debian source packages consulted are Mousepad0.6.3-1 and Openbox3.6.1-12; the Mac canonical learning library is unavailable in this VM. No kernel-source review is claimed.

Runs use Debian13/native x86-64, installed Python3.12.14, init, **512 PIDs / two CPUs / 3 GiB / zero swap**, disabled external networking, dropped capabilities and no-new-privileges. Selected VM runtime/library mounts are read-only; no host desktop or API credentials are supplied. Normal product Chrome sandbox behavior is unchanged; only the isolated Chrome fixture explicitly chooses no-sandbox.

## Validation and limits

At preceding candidate c43a044, the non-browser suite passed **2535**, with28 skips and13 browser deselections; browser tests passed **13/13**. Ruff, **103 resources**, **97 JavaScript tests**, Rust checks and notebook validation passed. The final direct-wait correction requires a fresh final regression result before merge.

A finite zero-failure batch qualifies its measured configuration. It cannot establish universal Linux reliability, other architectures/kernels/distributions, Wayland, shared foreground, physical devices or provider-backed planning. Original failures, setup errors, rejected hypotheses and all scheduled attempts remain available. No unresolved mutation is automatically retried.
