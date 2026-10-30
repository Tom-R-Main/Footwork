# Linux native reliability — Debian x86-64 VM

This tranche starts from merged main `52601b1`. It reproduces the public browser recovery's post-success native abort and repairs its unjoined session-end cleanup. It also adds probe phase/exit evidence, a WM client-service acknowledgement before editor launch, and bounded sole-owner direct-child joins. Identity, consent, pidfd-only signaling, incomplete-inventory uncertainty and Chrome sandbox defaults remain intact.

**The final cleanup2 artifact passed 40/40 primary attempts:** 30 fresh lifecycle admissions (90 worker driver cycles) and ten full installed journeys, each with delayed-helper recovery. All public command/MCP processes exited normally, and every final cleanup had completed direct waits with no survivors, zombies or uncertainty. The earlier candidate's **3/40 failed cleanup snapshots** remain failures. Product build source: `51ee6e2`; later edits affect tests/documentation only.

## Demonstrated native cause and patch

At diagnostic product `5324f6f` with the original native CUA wheel, the real installed public zero-window recovery completed its application work and explicit `driver.shutdown()`, emitted success JSON, then received **SIGABRT (-6) in 2/10 attempts** ([attempts](recovery-isolated/attempts.json), [captures](recovery-isolated/captures.jsonl)). All ten retained the same strict browser root identity. The plain minimal create/list/observe/shutdown experiment completed **40/40 processes**, three driver cycles each; it lacked the configured browser host/session-end path.

Normal GDB startup yielded 0/30 aborts and changed timing. A diagnostic native signal handler therefore stopped only after an actual SIGABRT had begun, permitting attachment to that owned process. One of ten public attempts aborted; its numeric -6 and complete native stacks remain ([capture](recovery-capture/captures.jsonl), [signal handler](harness/reliability-abort-capture.c)). No synthetic abort was injected. The stack identifies the `BrowserEngine::new_with_runtime_services` session-end task on `async-compat/to`, glibc forced-unwind cleanup through Tokio's panic catcher, and the main thread in `Py_FinalizeEx`.

The pinned source's synchronous session revocation schedules browser socket/grant release and protected-consent cleanup without joining those tasks. Their engine/provider captures can outlive explicit SDK shutdown and cross into a foreign destructor during interpreter finalization. The fix owns both hook tasks in the runtime's `ApprovalBroker` and drains them after admission closes, lifecycle maintenance joins and sessions revoke. Awaiting handles stays cancellation-safe in the owner queue; task failure remains sticky. No arbitrary sleeps, exit suppression, extra Python shutdown call or dependency bump was used.

PR12's independent mechanism review found cleanup1 retained completed handles throughout a long-running driver. Cleanup2 prunes only fully finished tasks during ordinary operation, records abnormal drop before pruning through a completion guard, and removes joined slots in a linear pass. Pending joins remain owned across cancellation. The **1,000-completed-cleanup regression fails before the correction** and passes afterward, including sticky failure after pruning ([before](reliability-cleanup-history-before.txt), [after](reliability-cleanup-history-after.txt)). All **three cleanup2 core tests and four SDK shutdown tests** pass. The follow-up review of implementation `dd728e6` completed with no findings ([review](https://github.com/Tom-R-Main/Footwork/pull/12#issuecomment-6533266387)); the original finding is resolved.

The proposed UniFFI continuation-race diagnosis was rejected: the pinned scheduler serializes callback completion, and all three baseline plus three delayed-continuation GDB tests exited normally ([captures](callback/captures.jsonl)). This negative result is retained.

The native SDK regression fails without the drain ([before](reliability-native-before-linked.txt)); **four shutdown tests** pass afterward, plus **two core cleanup tests** for completion, cancelled drains, separate owners and task failure ([SDK](reliability-native-sdk-after.txt), [core](reliability-native-core-after.txt)). Initial build/reference-borrow and rootless link failures remain in the build logs.

## Readiness and cleanup

Ten corrected-home admissions before the WM acknowledgement yielded **8 ready / 2 failed**. Another phase-rich ten yielded **9 ready / 1 failed**, with persistent zero qualified windows. A failed native/X11 observation found the editor unmapped, outside the WM client list and without WM_STATE while both editor and Openbox waited in their event loops ([captures](windowattrs10/captures.jsonl), [editor stack](editor10/captures.jsonl)). The matching Debian Openbox source publishes EWMH before subsequent startup work; publication alone does not demonstrate client service.

Startup now requires a disposable owned client's MapRequest to receive normal WM_STATE and client-list membership before Mousepad starts. The client is destroyed on completion/failure; ordinary health checks create no window. The added acknowledgement uses one second per attempt within unchanged startup/probe/grace bounds **30/3/2 seconds**. With the original native wheel, **10/10** fresh admissions passed after this change ([attempts](wm-ack10/attempts.json)). The exact internal cause of every historical overwritten target-timeout log remains unclassified; this evidence does not retroactively identify all old failures.

Probe attempts have unique result/stderr/phase files, fixed content-free phase names and monotonic times. Parent receipts distinguish numeric normal exit, signal, timeout phase, termination/escalation and final wait. Valid ready JSON cannot override a nonzero process exit. Exact document text is never placed in phase diagnostics. JSON remains on its own channel.

The first combined candidate `c43a044` completed all 30 admissions, all 90 worker driver cycles, and all ten public journeys/recoveries. Its strict acceptance nevertheless failed **3/40 attempts**: lifecycle26, lifecycle28 and journey5 retained an editor zombie with a pending direct wait. An extra nonblocking poll was insufficient. A subsequent existence-only /proc check recorded those three snapshot PIDs absent ([follow-up](final/cleanup-followup.json)); the original snapshots remain unchanged ([sessions](final/sessions.jsonl), [attempts](final/attempts.json)).

Source `6ff8370` uses the remaining existing cleanup grace to join each solely owned Popen child. It preserves pre-reap zombies and final numeric waits, and a pending direct wait sets cleanup uncertainty. It installs no global reaper and never waits unowned orphans. The deterministic waitability regression fails before this correction; **30 focused lifecycle tests** pass afterward. This establishes a concrete wait race, not the precise cause of the earlier arm64 snapshot.

## Frozen artifacts and constraints

Final product wheel SHA256: `c8fdc3644f3e109377a819dc327f5f7621aab71a136e5ca3c214665e8b312e4b`.
Native wheel: `cua_driver-0.38.0+footwork.d5373879.cleanup2-py3-none-linux_x86_64.whl`, SHA256 `3d63eff31c16bcbeffe4acdea9a2291d10a26b4110bbbfa652906d8ed8a69a20`.
[Fresh consumer byte identity](reliability-release-identity.json) compares all 193 product and eight native package files. [Source-to-wheel verification](reliability-release-source-wheel.json) matches all 198 wheel entries. Bundle and consumer paths are `/workspace/scratch/fw-reliability-release-bundle` and `/workspace/scratch/fw-reliability-release-consumer`.

The original upstream archive plus the shipped diff reconstruct the exact measured native archive byte-for-byte: SHA256 `5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401` ([receipt](reliability-native2-reconstruction.json), [standalone reconstruction helper](harness/rebuild_native_archive.py)). No mutable reference checkout/cache is needed for that reconstruction. Cleanup1's separately retained 40/40 corrected-wait run does **not** qualify cleanup2.

The [native patch](../../vendor/cua-driver/patches/session-cleanup-join.patch) changes four Rust files over upstream `d5373879`; [provenance](../../vendor/cua-driver/patches/session-cleanup-join.json) records upstream/patched archive and file hashes. Generated Python bindings and Cargo dependencies remain unchanged. The supplied complete-file reference hashes were verified against the original pinned archive before changing it. Debian source packages consulted are Mousepad0.6.3-1 and Openbox3.6.1-12; the Mac canonical learning library is unavailable in this VM. No kernel-source review is claimed.

Runs use Debian13/native x86-64, installed Python3.12.14, init, **512 PIDs / two CPUs / 3 GiB / zero swap**, disabled external networking, dropped capabilities and no-new-privileges. Selected VM runtime/library mounts are read-only; no host desktop or API credentials are supplied. Normal product Chrome sandbox behavior is unchanged; only the isolated Chrome fixture explicitly chooses no-sandbox.

## Validation and limits

| Final cleanup2 check | Result | Evidence |
| --- | --- | --- |
| Fresh lifecycle cycles / worker driver cycles | **30/30 / 90/90** | [all scheduled attempts](release/attempts.json), [phases and transcripts](release/captures.jsonl) |
| Complete installed CLI/MCP journeys / delayed recoveries | **10/10 / 10/10**, normal exits | [parent exits and semantic receipts](release/receipts.jsonl) |
| Cleanup | **40/40** no final survivors/zombies/uncertainty/pending waits | [session snapshots](release/sessions.jsonl); pre-reap zombies remain recorded and joined |
| No-WM save refusal | No dispatch, zero delivered inputs, no readback, unchanged disk bytes | [receipt](release-controls/refusal.json), [actual SDK envelope](release-controls/refusal-sdk.json) |
| Negative readiness/inventory/signal gates | **6/6**, including valid-EWMH WM that never services mapping | [control reports](release-controls/faults.json) |
| Component failure / early cancellation controls | **5/5 / 1/1** expected failures/stopped outcome | [sessions](release-controls/sessions.jsonl), [parent exits](release-controls/receipts.jsonl) |
| Process/readiness/resource tests within init/512-PID boundary | **61 passed** | [output](release-controls/process-fault-tests.txt) |
| Full non-browser source suite | **2,537 passed, 28 skipped**, 13 deselected | [output](reliability-release-full-tests.txt) |
| Browser tests | **13 passed**, no skips | [output](reliability-release-browser-tests.txt) |
| Ruff / resources / JavaScript / Rust / notebook | Passed / **103** / **97 passed** / passed / passed | [lint](reliability-release-ruff.txt), [resources](reliability-release-resources.txt), [JS](reliability-release-node-tests.txt), [Rust](reliability-release-rust-tests.txt), [notebook](reliability-release-notebook.txt) |

Every scheduled primary attempt is retained; no replacement runs or timeout tuning were used. The final policy is startup30/probe3/cleanup-grace2 seconds, with one-second WM acknowledgement attempts inside those bounds. Final cgroup counters report no PID-limit or memory OOM events ([counters](release/counters.json)). Probe phase journals, numeric exit/signal records, public transcripts and cleanup snapshots remain separate. A ready JSON or application effect alone never overrides an abnormal process exit.

The earlier broad run without documented umask022 failed two permission-fixture tests; both pass unchanged under022 and the final broad suite uses022. A denied-signal Popen fake initially lacked the new wait seam and now explicitly models timeout while retaining its original unresolved-cleanup assertions. One fixture lambda triggered Ruff and was replaced with the equivalent dict callable; its focused test and final lint pass. Initial source-build/link, harness-home, final-reason and invocation-path failures remain retained. These setup/candidate failures are not removed from their denominators.

Final-head hosted checks and actual merge status are recorded on [PR12](https://github.com/Tom-R-Main/Footwork/pull/12), separately from local exact-artifact measurements.

A finite zero-failure batch qualifies its measured configuration. It cannot establish universal Linux reliability, other architectures/kernels/distributions, Wayland, shared foreground, physical devices or provider-backed planning. Original failures, setup errors, rejected hypotheses and all scheduled attempts remain available. No unresolved mutation is automatically retried.

All **22** task-owned qualification containers were stopped and removed after evidence capture ([cleanup receipt](owned-container-cleanup.json)). The wheel bundles, fresh consumers and source/build caches remain in the VM for inspection. This cleanup claim covers those owned containers, not every process in the outer VM.
