# E1: frozen settings before the heldout run

Frozen on 2026-09-21 after the dev-split runs in `results/g1-s1-only.md` and
`results/g2-dev-three-arms.md`. Nothing below changes for the heldout run.

| setting | value | source |
|---|---|---|
| System 1 model | jev-1.13.0 (pinned id, not the alias) | `jevdual/policy.py` JEV_MODEL |
| System 2 model | muse-spark-1.3-contributor via https://api.meta.ai/v1 | `jevdual/keys.py`, runner `--llm meta` |
| arbiter thresholds | as shipped in `python/jevdual/arbiter.toml` (unchanged by tuning) | offline sweep: confidence floors never bind on the local site because Jev's confidences are ~1.0; the nouls did the work |
| verification | VerifyPolicy defaults: accept complete ≥ 0.85 and unmet ≤ 0.20, reject unmet ≥ 0.70 or complete ≤ 0.30, answer_required ≥ 0.60 | `python/jevdual/verify.py` |
| destructive gate | agent-level, keyword list from arbiter.toml plus the destructive noul ≥ 0.5 for S1; off only when the task sets `authorize: true` | `python/jevdual/agent.py` |
| prompts | PROMPTS_VERSION 2026-09-21.1 plus the verification section | `python/jevdual/prompts.py` |
| patches | orjson decode, native paint order, lazy uuid; snapshot lookup opt-in (off) | `python/jevdual/patch.py` |
| task metadata changed during dev tuning | passwords moved to `secrets`; `authorize: true` on checkout-place-order, contact-form-basic, contact-form-newsletter (dev) and ho-contact-order-question (heldout, set before the run) | task files |

What tuning actually changed on dev: no threshold. The two changes were mechanisms, not numbers:
verification asks whether the task requires an answer, and the destructive gate covers System 2.

Heldout protocol: one run per arm, local tasks only (the two live tasks are excluded on both splits
for reproducibility), never debugged. Misses become new dev tasks.

## Addendum (after the Astra review)

The heldout run under these settings (`heldout-20260921-020103` and `heldout-dual-20260921-021807`)
was invalidated by rig defects found in the review (`results/review-astra-2026-09-21.md`) and rerun
as `heldout-v2` and `heldout-dual-v3`. Settings above are unchanged; what changed is mechanism:
System 2's done is now verified (max 2 rejections, then an `UNVERIFIED` done with `success=false`),
the destructive gate covers actions without element indices, the verifier grades evidence atoms
rather than sentences, and Jev call counts include escalation and verification calls.
`results/heldout-final.md` records the departure from "never debugged" that the verifier change
implies.
