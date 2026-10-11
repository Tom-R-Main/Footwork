# Standalone packet review remediation

## UOR1 · prediction · 2026-10-11 13:43
Hypothesis: resolving provenance from the packet manifest before installation or native actions removes Git/Command Line Tools dependence and prevents a completed native trial from losing its receipt at the provenance stage.
Test: preserve the old packet's installer failure outside a repository with Git denied; test both receipt paths against a frozen unpacked v3 packet with Git denied, plus invalid manifest and checkout fallback cases. Exercise the guest member-verification command and refuse modified, extra and symlinked members. Rebuild twice and verify immutable source binding. No independent Mac/TCC claims from these checks.
Predicts: standalone receipt provenance equals the frozen manifest, no Git subprocess occurs in packet mode, bad provenance refuses before effects, and altered extracted payloads fail guest verification.
Against: either receipt still invokes Git, accepts an enclosing foreign checkout, fails after native effects for provenance, or guest verification accepts modified payloads.
Refs: Claude review1791739896683034000; scripts/capability_clean_install.py; scripts/capability_installed_trial.py; docs/independent-onboarding.md

## UORU0 · update · 2026-10-11 13:43
Observed: the prediction heading was entered13:43 while the terminal clock showed13:41. Its committed161e439 precedes the resolving tests; the prediction text is retained. PR2 merged exact7669d3d into268f0fc after four passing checks and an empty review-thread audit. User selected and authorized disposable VM provisioning on External SSD, including launcher/image downloads.
Next: reproduce the packet receipt defect, remediate and freezev3; independently provision a SIP-enabled guest without inherited grants.
Refs: https://github.com/Tom-R-Main/Footwork/pull/2; Claude review1791739896683034000

## UORU1 · update · 2026-10-11 13:48
Resolves: UOR1 = held
Observed: the baseline installer fails at trapped Git; v3 unpacks and retains manifest provenance without Git on installed3.12.6/3.14.7. Both guest verifier invocations pass; both native invalid-manifest paths refuse before resources.23 focused tests and Ruff pass, repeated14member builds match frozen33e1afb, with the reviewed wheel unchanged. The smoke stops at an intentional uv boundary and does not establish dependency installation or native effects. Initial headings ran ahead of terminal clock by one or two minutes; committed prediction order is authoritative.
Next: request Claude exact-artifact review and keep UO2 open for independent guest runtime/permission evidence.
Refs: results/onboarding-remediation-20261011; output/u2-remediation-smoke-v3/receipt.json; PR2 merge268f0fc
