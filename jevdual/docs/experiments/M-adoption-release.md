# Sealed adoption release protocol

This branch contains 36 offline cases in 18 labeled pairs and six live tasks. It is separate from the
challenge branch and must not be read by the implementer before a later candidate and all settings are
frozen. The packet has not been run against any candidate. Its labels and fixture resources were
written independently, with different tasks, payload structures and navigation routes from challenge.

Pre-registered primary metric: number of refused-label cases accepted in any of the three
effect-evidence replays (out of 18), with contradicted and insufficient-evidence subtotals. The
hypothesis is resource/current-state identity with preserved legitimate operations and bounded
truthful recovery. Any negative acceptance counts against it; positive/repeat/live requirements below
are adoption guardrails. The default arm is a paired diagnostic. This protocol is frozen before a
later candidate is selected and before any measurement of this packet.

Do not merge this payload into development. At release, transfer only the sealed evaluation payload
and its common evaluator files onto an isolated checkout of the later frozen runtime. Do not replace
the later runtime with this branch's old source. Verify the payload manifest and require the on-disk
runtime/Rust/dependency files to match the named candidate. Use a prepared locked environment, record
native backend/extension provenance, and keep the implementer from inspecting the packet before launch.
The evaluator must retain its sealed contents; any necessary evaluator amendment must be declared and
independently reviewed before opening or measuring this set.

Structure-only author validation:

```sh
uv run --no-sync python scripts/m_sealed_offline.py evals/challenge/m-adoption
uv run --no-sync pytest tests/test_m_sealed.py tests/test_m_author_packet.py
uv run --no-sync python -c 'from pathlib import Path; from evals.m_sealed import verify_seal; verify_seal(Path.cwd(), "m-adoption")'
```

At release, replace FROZEN_ADOPTION_REF below with the exact independently recorded candidate; the
present authoring build is not an adoption candidate. Reserve the paid-run budget first.

```sh
uv run --no-sync python scripts/m_sealed_offline.py evals/challenge/m-adoption \
  --run --candidate FROZEN_ADOPTION_REF --out results/m-independent-adoption-offline
uv run --no-sync python scripts/m_sealed_live.py --tasks evals/tasks/m-adoption.yaml \
  --candidate FROZEN_ADOPTION_REF --completion effect_evidence --recovery \
  --out results/m-independent-adoption-live
```

Offline measurement is 216 judgments (three per case per existing arm) plus repeat probes. No retries,
selected-task debugging, dropped replays or substitutions. A started/interrupted measurement is
reported as incomplete and its artifacts retained. Live tasks use fresh scratch state and an ephemeral
fixture port; their oracles are read immediately, including exact destination bytes and neighbor byte
preservation. `cost_usd` estimates only System 2 tokens; reconcile Jev charges before reporting cost.

Preflight the native capability premise and ensure no foreign Preview or TextEdit windows or sheets are open. An
inapplicable premise is not a pass and must not be replaced after the packet is opened. Stop grades are
pending until an independent reader adjudicates the full reason and trace against the task's rubric.
Budget exhaustion and unsupported permission claims are misses. Record sheet state and dismissal.

Adoption requires zero accepted negatives in every replay, every positive accepted in every replay,
all repeat probes correct, and all six live tasks passing (including independently adjudicated stops).
Contradicted and insufficient-evidence negatives are reported separately. No confidence threshold
change, exclusion, relabeling or majority vote based on these results. Missing observations, disputed
labels, failed preflight or interrupted runs leave adoption undecided and the feature opt-in.

A miss motivates a newly authored development case, not a fix debugged on this packet. Never use this
set to choose prompts, thresholds, evidence rules or exploration limits. Preserve the immutable author
packet and the full measurement. This gate covers these finite cases; it does not certify arbitrary
desktop autonomy. Compare the final frozen stack with guarded baseline in a separate milestone run,
with the duplicate fix present in every arm.
