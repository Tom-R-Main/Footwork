# What we take from trycua/cua

Survey date 2026-09-24. Checkout: `external/cua` (git-ignored; MIT except where noted below).
Surveyed: `libs/cua-driver`, `libs/cua-s1`, `libs/cua-bench-s1`, `libs/cua-bench`,
`libs/python/*`, `rfcs/3931`, `rfcs/2512`, `rfcs/2549`, `rfcs/3007`, `skills/jev-use`.

## The short version

cua has already converged on our architecture for native computer use, and says so in an
accepted RFC (3931, 2026-09-18): the client builds a bounded table of complete actions from a
fresh observation, Jev picks only a candidate id, the client validates the id against the same
snapshot before dispatch, one capture yields at most one action, then reobserve. Their `jev-use`
recipe is that loop for one browser form. What they do not have is the part we have built:
a calibrated arbiter with escalation to a reasoning model, evidence-based verification, a
consent gate, and a pre-registered measurement program. What we did not have is a native
desktop backend, and theirs is good.

## What we consume

**Cua Driver** as a dependency, not vendored: `cua-driver==0.28.2` wheel (Python 3.10+, no
dependencies, bundles the Rust runtime and the `cua-driver` binary). `CuaDriver.create()` runs
in-process with the host process's Accessibility grant; no daemon, no CuaDriver.app needed for
development. Telemetry disabled with `cua-driver telemetry disable`.

What it gives us, verified on this Mac against Calculator:

- `get_window_state(pid, window_id)`: a flat element list (`element_index`, `role`, `label`,
  `value`, `enabled`, `selected`, `actions`, `parent_index`, `frame`, `element_token`) plus
  `tree_markdown` with the static text, `snapshot_id`, `elements_complete`, `truncated`,
  `degraded`. Tokens are snapshot-bound (`s00000001:11`); a newer snapshot makes older tokens
  stale by construction. This is the same contract as browser-use's `selector_index` and our
  freshness guard.
- `click(position=ELEMENT(token), delivery_mode=BACKGROUND)`: AX press without raising the
  window or moving the pointer. `set_value(element_token, value)` for text fields and popups.
  `press_key`, `hotkey`, `scroll`, `move_cursor`, `invoke_menu(path)`, browser tools.
- `ActionResult.effect` in the Driver's own words: `confirmed`, `partial`, `unverifiable`,
  `suspected_noop`, `refused`, with `route` and `evidence` (value readback, window change).
  Button presses come back `unverifiable` (no readback); our reobserve supplies the evidence.
- `verify_state(expect=[ElementPredicate(selector, value_equals/exists/enabled/selected)])`
  returning satisfied / unsatisfied / unknown, where unknown never means success.
- `docs/action-support.md`: an empirical ledger of which action shapes deliver in the
  background per platform and app framework (Electron refuses background scroll on macOS, and
  so on). Use it to set expectations before an experiment, not after.

## What we take as design

1. **Menu from AX tree** (`python/jevdual/native.py`): role map AXButton/AXTextField/... to our
   `Candidate` roles and operations; the menu bar subtree excluded by default (110 of 155
   elements on Calculator); sections from labelled AXGroup/AXToolbar ancestors; secure fields
   never carry their value; page text from the static-text leaves of `tree_markdown`.
2. **Driver effect as evidence**: `NativeEffect` keeps `effect`/`route`/`evidence` verbatim;
   `confirmed` is the Driver's word, ours is the reobserved menu diff (`effects.diff`).
3. **Reserved `abstain` and `reobserve` candidates** (RFC 3931). We already have `blocked`
   and the `stuck` noul; the native loop adds `reobserve` when a snapshot is `truncated`,
   `degraded` or `elements_complete` is false, rather than acting on a partial menu.
4. **`verify_state` predicates as task end-state checks** for native tasks, next to our text
   evidence, so a native task YAML can declare `expect: [{role: AXStaticText, value_equals: "72"}]`.
5. **Oracle solvers** (cua-bench `@solve_task`): every native task ships a scripted solution
   that must make its own verifier pass before an agent is measured on it. Cheap and it catches
   broken verifiers, which we have hit twice on the browser side.
6. **cua-bench-s1 metrics** for Q1-style calibration work: selective accuracy, abstention rate,
   unsafe-action rate (acting when gold says abstain), ECE over argmax confidence, and a
   pre-registered dataset hash. Their `safety_gate` family (destructive_irreversible,
   financial_commitment, credential_exposure, scope_creep) is the taxonomy our Q8 consent
   classes should be reported against.

## What we do not take

- `cua-agent`, `cua-computer`, `computer-server`, `mcp-server`: the older pixels-only loop with
  no safety gate (OpenAI safety checks auto-acknowledged), being folded into Driver per RFC 2512.
- `cua-som` (AGPL-3.0) and `cua-perception` (AGPL OmniParser detector): licence and not needed
  while the AX tree or DOM is available. Pixel fallback is a later question.
- `cua-s1` models: a Jev-like tiny scorer (`tinyx`, adapted from Minimal Labs' jevlike) and a
  Qwen3.5-4B LoRA that scores letters A–Z. Interesting as a second System 1 to compare, not as
  a replacement. Their hard split reports hosted Jev at 0.000–0.576 task accuracy on GUI-360
  Windows trees, which says more about their serialisation (16-element samples, letter
  options) than about Jev; our menu format is a variable worth measuring against theirs.
- `cua-bench` runtime: simulated tasks cannot load real URLs, native tasks want Docker/KVM
  VMs, and there is no paired-comparison tooling. Task shape and trace schema only.
- Lume VMs: not yet. Native tasks run on the host against real apps behind the same gate.

## First result (spike, not an experiment)

`scripts/spike_native.py --app Calculator --task "Clear the calculator, then compute 9 times 8
and leave the result on the display" --act`: five System 1 steps (All Clear, 9, Multiply, 8,
Equals) at target confidence 0.72–0.99, 144–352 ms per Jev decision, every dispatch a
background AX press, display read back `9×8 / 72`, then `done` with goal_done 0.93 escalated
by `done_requires_verification`. Log: `results/native-spike-20260924/`. One button press
(`All Clear` on a freshly launched Calculator) was refused once with AX error -25204 in the
scripted run and succeeded on the Jev run; worth watching, not yet a finding.

## Open questions before Q10 is pre-registered

- Text entry on native fields: `set_value` writes AXValue and reads it back (`confirmed`);
  Electron and Catalyst echo AX writes and come back `unverifiable`. Which apps are in scope?
- Menu bar: expose top-level menus as a `menu` operation backed by `invoke_menu(path)`, or
  keep the whole subtree out and rely on toolbar controls and hotkeys.
- Foreground escalation: Driver refuses some shapes in the background; the arbiter must treat
  a `refused` effect as a step that did nothing and let System 2 decide about foreground.
- What "page text" means for a native app: static text only, or labels of everything visible.
