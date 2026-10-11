# Standalone packet v3 review remediation

Frozen helper/doc commit: `33e1afb06710e2d2a57a0f7d1aea7ea0e19a878d`.
Packet: `output/u2-packet-v3/footwork-onboarding-u2.zip`.
SHA256: `769c08c89061731368db33d78b180e7c8c96d531190f43bee44263642a76fd0f`.
Two builds match at14members. The product wheel remains the PR2-reviewed9bb0440d artifact, byte for byte.

Claude B1/N1/N2 are addressed: both receipt paths obtain manifest provenance before resource creation; checkout fallback runs Git only at an owned .git marker; the runbook uses one explicit Python executable and records paths/versions; a stdlib guest command verifies every extracted payload and rejects extra members.

23 focused tests pass, plus Ruff and notebook validation. `output/u2-remediation-smoke-v3/receipt.json` records actual unpacked installer invocations on existing installed3.12.6 and3.14.7 interpreters. Git is trapped and uv intentionally exits17 at the external environment-creation boundary: v2 invokes Git and loses its receipt; v3 does not invoke Git and preserves its frozen source commit in a failed-stage receipt. This is a receipt-path smoke, not a fresh dependency installation. Both profiles run the guest verifier successfully and native entry refuses an invalid manifest before output creation or scope access. Native effects and the final successful native receipt have not been rerun here; U2 will exercise them in the independent guest. Tamper/symlink/escape/extra-member cases are covered by CLI tests.

The checkout development .venv disappeared between checks and was recreated empty by uv; no cause was established. The repeated23tests and Ruff used the main checkout's existing development environment with the isolated checkout's source/tests. Packet tests used the retained separate full-dependency environments. No new host dependencies were installed for these checks.

PR2 merged exact7669d3d at268f0fc; both post-merge workflows passed (38160734302,38160734323). The new packet changes remain on the local independent-onboarding branch. Claude's v3 review is requested. The user approved SSD VM launcher/image provisioning; actual clean-Mac permission qualification remains unexecuted.
