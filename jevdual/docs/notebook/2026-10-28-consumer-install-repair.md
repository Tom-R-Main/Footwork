# Consumer installation CI follow-through

## CINS1 · prediction · 2026-10-28 21:40
Hypothesis: PR #7's macOS Python 3.12 installation failure is transient registry DNS failure, not incompatible dependencies; the installer retains its stderr but omits that evidence from the console failure report.
Test: rerun only failed hosted jobs and exercise the installer main boundary with controlled subprocess failure and timeout; require failure reports to expose bounded stderr and retained log locations while leaving passed false.
Predicts: the failed-job rerun gets past installation; before the reporting repair, failure and timeout console records omit the underlying error and evidence locations.
Against: the rerun fails on a deterministic dependency conflict, or current console records already expose the retained cause.
Refs: GitHub Actions run 40800078711; output/ci-failure-40800078711/ci-dependencies/install.stderr.log.
