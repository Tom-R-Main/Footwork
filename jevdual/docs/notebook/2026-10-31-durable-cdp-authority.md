# Durable CDP authority and restart retention

## DCA1 · prediction · 2026-10-31 14:40
Hypothesis: a single holder preserving the observed CDP document marker and owning the existing durable admission lock can prevent blind redispatch across CLI and holder restart without relaxing native evidence validation.
Test: installed browser cdp CLI against an independent loopback ingress ledger; interrupt client and holder before admission, after prepared intent, after durable start, and after fixture effect; reopen authority and repeat the same token, then a new token. Challenge changed requests, missing/failed guard, stale document, foreign producer, absent readback, and disabled typing.
Predicts: prepared-only recovery is known not_sent; started or acknowledged activation remains unknown and completion unverified, blocks new tokens, and repeat tokens never add ingress. CLI restart reconnects only to the original live holder; holder loss never adopts or launches a browser. Native evidence continues rejecting browser bindings.
Against: any repeat adds ingress, any changed target is activated, an uncertain operation becomes completed from an ack or DOM appearance, a live holder is recovered by another owner, or a missing guard permits activation.
Refs: docs/plans/light-profile-20261030.md; results/cdp-dom-click-20261031/; reference anchors ev-cd1396cf9a543a0da0cb6fed, ev-cd2d3b7de9e879914b7b949f, ev-0860862fcd5501a1b90e9be5, ev-15d2df3506a0b868b3b39c3b in output/repo-learning/linux-consolidation/library.

## DCA2 · prediction · 2026-10-31 14:40
Hypothesis: discovery can make the owned headless CDP route findable without implying that CUA-free package metadata or general browser completion is already delivered.
Test: installed tools, doctor, schema browser cdp and the version-matched guide with no CUA/browser-use importable; inspect actual command requirements and refusal receipts.
Predicts: discovery names CDP setup and guard requirements, typed/native-button scope, unverified completion and disabled typing; describes the existing full dependency metadata separately from the future light install.
Against: a cold agent is directed to CUA/X11 for the CDP route, an unavailable light install is recommended as shipped, or discovery advertises typing/completion unsupported by the executable.

## DCAU1 · update · 2026-10-31 14:49
Observed: the first real CLI lost-client-ack test delivered exactly one fixture ingress and retained unknown, but recover failed because the CLI caught OSError/ValueError while the holder identity checker raises RuntimeError. The catch boundary was corrected; the three focused discovery/lost-client/missing-guard CLI checks then passed. Four existing unrelated-cwd discovery checks initially failed because the source test used a relative PYTHONPATH; rerunning with the absolute candidate source root passed all 47 focused guard/discovery/authorization checks. These are harness/integration failures, not evidence of browser completion.
Next: finish exact installed-wheel tests, independent review and VM qualification before resolving DCA1/DCA2. General completion readers, pipe custody and the light metadata split remain open.

## DCA3 · prediction · 2026-10-31 14:56
Hypothesis: a readiness RPC exception after spawning the owned holder bypasses the CLI startup timeout cleanup and leaves the new helper running.
Test: a bounded process-handle test raises from the first readiness RPC after the holder descriptor appears; assert termination and wait of the actual newly created child handle. Also check the CDP schema returns its full executable command path.
Predicts: current startup raises without closing the handle; wrapping all failed startup exits in owned-handle cleanup closes it without inspecting or signaling any metadata PID. The schema can include its browser prefix without changing legacy routing.
Against: cleanup already runs on the exceptional exit, or the fix stops a successfully established holder or a foreign process.

## DCAU2 · update · 2026-10-31 14:54
Observed: DCA3's first probe hit the Unix socket path guard before spawning because pytest's temporary path was too long; that cell did not test cleanup. The schema cell independently reproduced the missing browser command prefix. DCA3's heading time was a transcription error: the clock returned 14:53 when it was committed; Git ordering remains authoritative.
Next: shorten the test path and rerun the cleanup probe before its fix. Include the reviewer's related pre-readiness signal boundary below.

## DCA4 · prediction · 2026-10-31 14:54
Hypothesis: holder startup installs signal handlers too late, so terminating it while the Chrome launch thread is returning can bypass owned-handle cleanup even if the CLI waits for the holder.
Test: real subprocess startup shim delays return of the actual launched Chrome handle; send SIGTERM after independent identity capture but before holder readiness. Also exercise configured startup cancellation after the handle is acquired.
Predicts: installing a stop latch before launch and retaining acquisition of the launch-thread result allows the holder to stop the original Chrome handle and exit; a forced-kill fallback remains explicitly cleanup-unverified.
Against: graceful startup termination leaves live captured Chrome processes, loses the returned handle, or signals a process based only on metadata.

## DCAU3 · update · 2026-10-31 15:01
Resolves: DCA3 = held; DCA4 = held
Observed: after shortening the probe path, both the exceptional-startup handle test and schema-prefix test failed on the old implementation. The fixed CLI also preserves a successfully established holder. The old exact installed wheel e466146e failed the real launch/SIGTERM cell with holder_exit=-15 and needed test-only cleanup; the new source passed four real Chrome cells (TERM during launch/connect/navigation, INT during launch) plus launch-task cancellation/cleanup checks. Captured live-process absence is asserted before test cleanup; Linux orphan reaping remains test-supervisor behavior, not product evidence.
Changes: CLI failure exits close the actual direct child; holder handlers latch stop before launch, shield the launch-thread result, cancel only readiness tasks after retaining the Chrome handle, and never publish readiness after stop. Forced CLI termination carries browser_cleanup_unverified; startup cleanup exceptions propagate.
Next: rebuild the exact candidate, rerun installed checks and the VM fault cells, then resolve DCA1/DCA2 and close review.
Refs: tests/test_browser_startup_cli.py; tests/test_browser_startup_lifecycle.py; results/durable-cdp-authority-20261031/startup-signal-before.txt

## DCA5 · prediction · 2026-10-31 15:07
Hypothesis: if post-admission result retention and its unknown fallback both raise JournalError, the holder's outer pre-admission error handler can misreport dispatched=false after activation.
Test: an explicit retention-failure sensitivity control injects JournalError after one activation and again from mark_unknown; inspect the public RPC envelope, original durable row and a second-token attempt. This is injected protocol failure, not a reproduced storage incident; ordinary SQLite I/O exceptions already reach the unknown envelope.
Predicts: current code returns an incorrect no-send envelope; a narrow post-admission fallback returns dispatched=null, retryable=false and retention-unverified, leaves the persisted started row blocked, and never adds activation. Cancellation still propagates after retaining the best available uncertainty.
Against: the old code already preserves unknown, the fix claims durable retention despite its failure, the second token activates, or cancellation is swallowed.
