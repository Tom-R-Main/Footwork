# Critique: Plan 4, attended operator console

Reviewed October 28, 2026 against `5d494c6`. Paths are relative to `jevdual/`. Read-only check: `tests/test_visual_inspection_session.py`, 20 passed.

**Verdict.** The diagnosis is careful and the read-only first milestone is worth building. The plan as a whole stands on log data the session does not record. Its mutation milestones duplicate Plan 1, and its approval boundary does not hold against a same-user agent.

## 1. Factual claims

Claims that hold:
- Inspection fails closed on secrets, browser surfaces, changed targets, and truncated or degraded observations. Label lookup requires a complete observation (`python/jevdual/session.py:604-607,629-656`). The preview escapes text and sets `script-src 'none'` (`session.py:723-748`; `tests/test_visual_inspection_session.py:140`).
- Pending state is saved after dispatch. `state.step += 1` is at `session.py:985`; the dispatch runs at 986-1015; `pending` is written and saved at 1018-1035. The claim is understated: `grants.consume` spends and saves a grant use *before* dispatch (`session.py:966`, `grants.py:115-124`). A crash between those points loses the grant use and leaves no attempt record.
- CLI JSON reports `effect_verification: "not_asserted"` (`agent_cli.py:365`). Posture is separate from authorization (`posture.py:4-6`). Visual checks are advisory (`docs/visual-checks.md:3,65`). The journal commits intent before dispatch and is append-specific (`capability/journal.py:1-15`).

Claims that are wrong or overstated:
- **Most timeline records do not exist.** `session.jsonl` kinds are start, paused, grant, grant_used, do, receipt, s1, read, check_file, done, visual inspection, screenshot withheld. There is **no observation record**: `look` writes `screenshots/obs-NNN-*.png` without logging path or hash (`session.py:428-432`). Only `inspect-target` writes manifests.
- **Delivery is dropped.** `Receipt.delivery` exists separately (`receipts.py:16-18,53`), but the operator receipt logged keeps only `effect`, `evidence`, `text` (`session.py:165`) and is built without delivery, so it defaults to `unknown`. "Input delivered" would always read unknown on native sessions, masked by "missing fields remain unknown".
- **The log is not durable history.** `start` in a reused directory unlinks `session.jsonl` and `grants.json` but keeps `screenshots/` and `inspection/` (`session.py:470-471`), so a console could attribute an earlier session's PNGs to the current one, and "keep original session files intact" requires a behaviour change.
- **Approval binding is thinner than implied.** `Grant` binds op, location, element/ref, argument/value hashes and uses, not an observation generation (`grants.py:43-56`). `grants.json` and `session.json` are whole-file rewrites without locks (`grants.py:112-133`, `session.py:85-86`). Serialized access is new work.

## 2. UX and value

The October 9 direction makes the host agent the user and plan owner (`docs/plans/agent-superpowers-product-20261009.md:3,7,15`), avoids "repeated user approval" (`:64`) and counts user interventions as a cost (`:85`). Per-proposal human approval reverses that; the plan admits it (`04-operator-console.md:49`) but sequences as if additive.

Today's operator is an agent driving the CLI. The plausible human user is the developer *auditing what an agent did*, served by a post-hoc static page, not a live approval app. Cheapest test: `footwork report SESSION` emitting one script-free HTML file in the `_inspection_preview` style (timeline, receipts, screenshots, explicit "not recorded" for the gaps above). Compare it with raw `session.jsonl` on a comprehension task before any server code.

## 3. Feasibility and sequencing

- M1 first needs log changes (an observation record with screenshot path and hash; the delivery word on receipts), each with a notebook prediction; otherwise the projection has little to show.
- M2 (durable intent, single-use approval, serialized access) is Plan 1's milestone 1 (`01-execution-core.md:40`). Plan 4 pays for Plan 1's core anyway; the README table understates its cost.
- M3 adds a loopback HTTP server with token, same-origin and artifact bounds: the largest new attack surface of the five plans, against a direction that avoids listening ports (`agent-superpowers-product-20261009.md:25`).
- No sizing; M2 and M3 are not independently shippable.

## 4. Acceptance criteria

"Zero dispatches from stale/reused approval" is falsifiable via scenario tests and fits the repo. "Participants correctly identifying outcome limits on every critical case" has no case list, participant count or recruitment source; "reduced median effort" has no unit; and the CLI baseline arm is agent-operated, so the human baseline is undefined. Preregister one primary metric (e.g. correct outcome classification per case) in `docs/experiments/` before M1, not M2.

## 5. Risks and blind spots

- **Same-user bypass.** Any agent can run `footwork grant` (`session.py:1467-1503`). "Agent cannot approve through this console" needs authenticated presence (Touch ID, separate user); ownership flags in session files do not supply it.
- **Approval fatigue** is named but unmeasured (e.g. review time before Approve).
- **Freshness.** No pixel-equivalence policy exists, so "relevant changes" is undefined and could refuse without bound.
- **Privacy.** Withholding after a secret is forward-only (`session.py:421-427`); earlier PNGs in the directory stay browsable.

## 6. Strongest ideas to keep

1. **Four separate outcome labels:** "input delivered", "text observed", "saved file checked" and "unknown". Each comes from a structured field, and color is never the only signal.
2. **An approval record bound to the observation generation**, invalidated when arguments are edited, and revalidated just before dispatch. This also extends `Grant`.
3. **A fixture page in four states** (fresh, stale, withheld, uncertain) with controls disabled, as a test that needs no live app.
4. **Recovery behaviour:** a double click reuses the attempt ID, reconnecting never redispatches, and a restart opens in recovery mode.
5. **A fallback that still counts as a result:** the read-only diagnostic viewer.

## 7. Weakest ideas to drop

- The live local web server and token scheme (M3) and the "installed console" bundle entry.
- Console-owned sessions with checks that refuse legacy writers. This is ownership theatre without OS-level identity.
- Pixel revalidation before dispatch until a qualified equivalence rule exists.
- A full CLI-versus-console human study before a static report has shown any comprehension gain.
