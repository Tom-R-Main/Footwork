# Consumer installation CI follow-through

## CINS1 · prediction · 2026-10-28 21:40
Hypothesis: PR #7's macOS Python 3.12 installation failure is transient registry DNS failure, not incompatible dependencies; the installer retains its stderr but omits that evidence from the console failure report.
Test: rerun only failed hosted jobs and exercise the installer main boundary with controlled subprocess failure and timeout; require failure reports to expose bounded stderr and retained log locations while leaving passed false.
Predicts: the failed-job rerun gets past installation; before the reporting repair, failure and timeout console records omit the underlying error and evidence locations.
Against: the rerun fails on a deterministic dependency conflict, or current console records already expose the retained cause.
Refs: GitHub Actions run 40800078711; output/ci-failure-40800078711/ci-dependencies/install.stderr.log.

## CINSU1 · update · 2026-10-28 21:42
Resolves: CINS1 = held
Observed: retained install.stderr.log identifies DNS failure fetching typesafe-sdk wheel metadata after uv retries. The independent push workflow on merged 239ed8e passed all consumer platforms (run 40800449923). The new main-boundary regression failed before repair with missing timed_out; 33 installer/onboarding tests passed after repair, and the final six isolation tests and Ruff passed. A real CLI invocation against an intentionally invalid local wheel exited 1, retained passed=false, and printed its zip-metadata error with log paths (output/install-diagnostic-probe/run). A fresh GPT-6.1 Sol review found no actionable findings and independently passed six isolation tests.
Inferred: the original packaging failure was transient DNS rather than incompatible wheel requirements; surfacing retained stderr avoids downloading artifacts merely to diagnose such failures.
Next: open the bounded reporting PR and follow hosted checks; keep the separate physical simulation job's result explicit.

## CINSS1 · summary · 2026-10-28 21:42
Established: failed and timed-out installer stages emit bounded JSON-quoted stderr, log paths, and timeout state; failure still stops qualification without retry or dependency borrowing.
Uncertain: the original network timeout was not reproduced locally; the physical simulation CI job remains in progress. Tests use controlled failures and a real malformed-wheel CLI probe, not a live outage.
Decision: retain existing installation gates and ship only the failure-reporting improvement.
