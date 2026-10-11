# Standalone packet review remediation

## UOR1 · prediction · 2026-10-11 13:43
Hypothesis: resolving provenance from the packet manifest before installation or native actions removes Git/Command Line Tools dependence and prevents a completed native trial from losing its receipt at the provenance stage.
Test: preserve the old packet's installer failure outside a repository with Git denied; test both receipt paths against a frozen unpacked v3 packet with Git denied, plus invalid manifest and checkout fallback cases. Exercise the guest member-verification command and refuse modified, extra and symlinked members. Rebuild twice and verify immutable source binding. No independent Mac/TCC claims from these checks.
Predicts: standalone receipt provenance equals the frozen manifest, no Git subprocess occurs in packet mode, bad provenance refuses before effects, and altered extracted payloads fail guest verification.
Against: either receipt still invokes Git, accepts an enclosing foreign checkout, fails after native effects for provenance, or guest verification accepts modified payloads.
Refs: Claude review1791739896683034000; scripts/capability_clean_install.py; scripts/capability_installed_trial.py; docs/independent-onboarding.md
