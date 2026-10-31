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
