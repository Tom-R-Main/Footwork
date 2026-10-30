# Linux consolidation: repository learning

The transfer question is how to consolidate the VM-tested Linux supervisor without importing weaker identity, readiness or cleanup assumptions. The inspected cloud source is `bd6f185c24327f5cf292067b7f84ed50bd118a31`; the local implementation is `65996ad03c6dff1e4802eaf5cd5719f5d0ea243c`. Their existing acceptance runs qualify separate artifacts. This learning pass changes no product implementation and does not qualify a combined build.

## Library and provenance

Canonical task library, outside the consulted source checkouts:

`/Users/thomasmain/projects/footwork/output/repo-learning/linux-consolidation/library`

SQLite is canonical; `patterns.md` is the human export. Five pattern families are current. Two model-backed cards have explicit v2 records superseding v1 to add complete reproduction paths; seven immutable records remain. Retrieval may return historical versions, so inspect `supersedes` before reuse. Use the [current-pattern manifest](../results/linux-repo-learning-20261030/reproducibility.json).

The seeded library at `/Users/thomasmain/Documents/Codex/2026-10-30/ti/outputs/repo-learning/library` was read through its exported Markdown and left unchanged. Its requested/resolved identity, bounded coverage and independent-oracle patterns informed the questions. This task library is a scoped extension, not an empty replacement for that seed.

Twenty-one evidence snapshots record actual source HEAD, exact lines and hashes. They cover the two Footwork candidates plus systemd, Coder, Selkies, River and CUA. [Source index](../results/linux-repo-learning-20261030/evidence-index.json) and [freshness](../results/linux-repo-learning-20261030/verify.json) retain identity: 19 fresh, two revision-advanced with unchanged file content. The cloud source is retained read-only at `/Users/thomasmain/projects/footwork/.worktrees/linux-cloud-grounding` for future verification. No reference checkout was fetched, edited, built or executed.

The `referencerepos/linux` kernel checkout is absent. That is unavailable source, not contrary evidence. Kernel-wide source conclusions are excluded. A separate small owned-child check exercised the actual local Linux syscall path; it does not establish the cloud Debian kernel's policy or API availability.

## Useful transfers and rejection conditions

| Pattern | Source mechanism and target application | Reject the transfer when |
| --- | --- | --- |
| `linux-signal-identity-and-scope-v2` | systemd `pidref.c:346–360,406–429` distinguishes pidfd delivery from numeric fallback; Coder `reaper_unix.go:54–77` separates orphan reaping from ordinary child waits. Cloud cleanup needs separate contracts for identity pinning, group membership and wait ownership. | A start-time check or numeric fallback is presented as race-free; a leader fd with flags0 is claimed to kill a process tree; a global competing reaper is introduced. |
| `linux-ready-is-owned-live-observation-v1` | Selkies bounds initial handshake as well as replies; systemd distinguishes startup readiness from continuing functionality. Preserve cloud-owned bus and ongoing AT-SPI/WM health, local displayfd allocation and EWMH self-check, and per-action target qualification. | A marker, WM selection, fresh profile or process liveness becomes permanent input authority. River's explicit unlock versus lock-client destruction is a counterexample to inferring positive state from disappearance. |
| `owned-browser-helper-is-not-another-root-v2` | The known launch helper has custody/lifetime distinct from persistent root discovery. Retain helper completion/reaping sequencing without loosening exact executable/profile/port/UID identity. | An arbitrary matching process is excluded, the first matching root is chosen, command-line similarity grants custody, or a helper acknowledgement substitutes for target readback. |
| `linux-bounded-inventory-preserves-unknown-v1` | Cloud process-table traversal is bounded but does not return truncation. Carry coverage into cleanup uncertainty rather than dropping omitted identities and claiming no survivors. | The verified 512-PID fixture is used to justify full visibility on an unrestricted host, or a larger cap is treated as completeness proof. |
| `verify-final-public-envelope-not-only-producer-v1` | CUA's platform producer is followed by core recovery decoration and SDK decoding. Preserve captured public-class regressions for `hint`/`next_call` and strict semantic refusal predicates. | A producer-only mock defines the final reply, unknown semantic keys are accepted, or advisory `next_call` is executed as authorization. |

Each card includes the causal trace, counterexample, tradeoff, evidence IDs and target compatibility checks. The source projects' abstractions are not dependencies to transplant wholesale. In particular, even systemd's PidRef can fall back to numeric signalling; its entire API cannot be described as uniformly reuse-safe.

## Checks that changed the decision

The [controlled models](../results/linux-repo-learning-20261030/models.py) compile the exact cloud source functions and replace process inventories, driver replies and signal sinks. They start no browser and send no OS signal. [Results](../results/linux-repo-learning-20261030/models.json):

- Stable signal control preserves original recipients. Substituting a member incarnation after group delivery makes the unchanged cloud individual loop address the replacement. A test-only immediate recheck skips that substituted recipient while preserving the stable neighbor. This exposes that transition; it does not prove a recheck eliminates the remaining check-to-kill race.
- The exited-helper control binds. A live invocation-owned helper satisfies the actual executable/profile/port predicate and triggers the multiple-root refusal. An unrelated matching root still refuses. The failing helper case must be fixed without relaxing the unrelated-root guard.

The initial model run failed because the fake subprocess omitted `DEVNULL`; that harness error is retained and is not counted as a negative control. Corrected controls passed for the intended assertions.

The [owned-child pidfd check](../results/linux-repo-learning-20261030/pidfd_check.py) passed on the existing local aarch64 Linux VM, kernel `7.0.14-linuxkit`, Python `3.14.4`: TERM through the fd ended the referenced child; signal0 through the retained fd after exit returned ESRCH; a separate live sentinel survived; the fd closed and both children were joined. [Receipt](../results/linux-repo-learning-20261030/pidfd-learning.json). No numeric signal fallback was used for the tested mechanism. This is syscall plumbing evidence, not real PID-reuse reproduction or product adoption. The temporary container was stopped.

A fresh-context retrieval check found the signal pattern from different wording about a background worker and a recycled identifier. It rejected both arbitrary payment retries and leader-only pidfd tree cleanup. [Retrieval record](../results/linux-repo-learning-20261030/retrieval-check.json). Lexical query matches are retrieval candidates, not domain support or demonstrated correctness gains.

## Consolidation handoff

Use the cloud state machine as the base; keep one supervisor and one record/qualification contract. Preserve native display reservation and stronger EWMH observation where compatible. Before claiming no-wrong-recipient cleanup, qualify a pinned individual-signal primitive on the actual cloud kernel, with unavailable/denied/resource-exhaustion states and explicit fallback policy. A newly opened pidfd binds the process found at acquisition time; it does not retroactively prove that a stale PID observation named that same incarnation. The adoption check must establish custody and validate the intended identity across handle acquisition. Retain a separately proven group/observed-descendant strategy and one wait owner per direct child.

Cheapest next gates:

1. Live/exited pidfd in the actual Debian VM; denied/unsupported fd paths must not silently retain a pinned-delivery claim. Keep the orphan-grandchild case separate.
2. Delayed singleton helper under the actual discovery predicate, plus an unrelated-root negative control and root-incarnation replacement.
3. Bus replacement with other components alive, WM selection without EWMH, blocked initial handshake, and partial process inventory. Require marker invalidation and explicit cleanup uncertainty.
4. Build one consolidated wheel, verify its bytes, and repeat both installed CLI/MCP/save controls and constrained lifecycle/browser tests at that same revision. Earlier green branches do not qualify that new artifact.

Retrieve and verify before reuse with `repo_learn.py --store <the task library> query ...` and `verify`; the helper path is `/Users/thomasmain/.codex/skills/repo-learn/scripts/repo_learn.py`. Exact commands, script hashes and absolute validation artifact paths are in the current v2 cards and reproduction manifest. No speed gain, complete source coverage, kernel portability or consolidated implementation success is claimed by the library schema checks.

## VM implementation follow-up

The [cloud-base consolidation report](../results/linux-consolidation-vm-20261030/report.md) identifies combined product revision `f16cc54`, its byte-checked wheel, real pidfd/helper/SDK controls and isolated lifecycle acceptance. It also retains one native teardown failure and intermittent repeated-batch target timeouts. This later implementation evidence is distinct from the learning models and earlier branch acceptance above.
