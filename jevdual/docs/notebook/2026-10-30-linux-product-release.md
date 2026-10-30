# Linux preview and product onboarding

## LP1 · prediction · 2026-10-30 14:37
Hypothesis: merging the VM-tested Linux consolidation with current main preserves its source contracts and produces an installable bundle whose public artifact checker distinguishes matching from changed bytes without provider access.
Test: freeze the merged source and product docs, run the non-browser regression suite and resource checks, build a bundle with the pinned native wheel, install into a fresh Linux environment and run the documented positive/negative artifact checks. Retain revision, wheel and process-exit evidence.
Predicts: regression and resource checks pass; the installed checker returns success only for the matching file and nonzero with ok=false for the changed file.
Against: the merged source regresses, a bundle differs from its source or cannot install, or either public checker reports the wrong outcome.
Refs: results/linux-product-release-20261030/; results/linux-consolidation-vm-20261030/report.md

## LPS1 · summary · 2026-10-30 14:37
Established: independent source review found the repeated native teardown abort and target-readiness timeouts remain unresolved. Product docs now introduce useful workflows, a key-free first result and explicit Linux preview scope. Reference README review of uv, Playwright and Coder supports a short runnable path before architectural and deployment depth; historical measurement tables remain intact.
Uncertain: this documentation change does not repair repeated native sessions, qualify Wayland/shared foreground, or publish portable binaries for all Linux distributions.
Decision: ship bounded Linux preview functionality and evidence with honest operating limits; retain the native reliability findings for follow-up rather than suppress exits or widen identity predicates.
Refs: docs/quickstart.md; docs/linux-support.md; docs/linux-consolidation-learning.md; results/linux-consolidation-vm-20261030/report.md

## LPU1 · update · 2026-10-30 14:43
Resolves: LP1 = held
Observed: source 40ae59f passes 2464 host tests with 94 platform/dependency skips and 13 browser deselections; all 97 JavaScript tests, lint, resource and notebook checks pass. The fresh Linux bundle matches all 193 installed package files and its public artifact checker distinguishes matching bytes from changed bytes with exit 0/6. The installed browser/CLI/MCP/save/replay/restart journey passes with process exit 0. The initial harness invocation used an unavailable Chrome path; its failure remains retained. Cleanup recorded one editor zombie, absent in a subsequent proc check.
Next: publish the reviewable preview PR and require hosted checks before merge. Preserve the earlier native teardown and repeated-session timeouts as unresolved; this first-result test is not a reliability repair.
Refs: results/linux-product-release-20261030/report.md; results/linux-consolidation-vm-20261030/report.md
Changes: the LPU1 heading used an estimated minute; the shell clock immediately after commit a984f19 read 2026-10-30 14:41 America/Detroit. Git ordering, including prediction commit 40ae59f before the tests, is authoritative.
