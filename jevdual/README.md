# jevdual

A dual-process browser agent on top of [browser-use](https://github.com/browser-use/browser-use),
pinned and not forked. **System 1** is [TypeSafe Jev](https://docs.typesafe.ai): one speculative
fan-out request per step that picks an operation and a target from a code-owned menu and answers six
yes/no questions about the situation. **System 2** is the stock browser-use LLM loop. A code-owned
arbiter decides which system acts; verification needs evidence before any run is called done; a
destructive gate covers actions from either system. Measured hot paths in the DOM pipeline run in
Rust through PyO3, each with a pure-Python twin and equality tests.

## Results

Every number below is in a file under `results/`.

Dev split, 23 local tasks (`results/g2-dev-three-arms.md`; measured before the verification changes
below, not rerun since):

| arm | pass | false done | LLM calls | Jev calls | est. cost USD | wall s |
|---|---|---|---|---|---|---|
| S1 only (Jev) | 10/23 | 11 (2 paused) | 0 | 76 | 0.013 | 133 |
| stock browser-use (Muse Spark 1.3 Contributor) | 21/23 | 2 | 65 | 0 | 0.098 | 1,578 |
| dual (Jev + Muse) | 23/23 | 0 (2 paused) | 55 | 189 | 0.122 | 1,412 |

Heldout split, 10 local tasks, settings frozen, rerun once on adoption of the verification changes
(`results/heldout-adopt.md`):

| arm | pass | false done | LLM calls | Jev calls | est. cost USD | wall s |
|---|---|---|---|---|---|---|
| stock | 9/10 | 1 | 33 | 0 | 0.049 | 708 |
| dual | 10/10 | 0 (1 paused) | 24 | 76 | 0.049 | 522 |

Live split, 55 tasks on public and practice sites, three arms after the verification changes
(`results/q6-live-paired.md`):

| arm | pass | false done | LLM calls | Jev calls | est. cost USD | wall s |
|---|---|---|---|---|---|---|
| S1 only | 13/55 | 23 | 0 | 427 | 0.192 | 787 |
| stock | 51/55 | 1 | 265 | 0 | 0.382 | 5,508 |
| dual | 51/55 | 0 (2 paused) | 196 | 458 | 0.504 | 6,158 |

Q9, the four-arm test of System 2 directing System 1 on the same 55 live tasks
(`results/q9-live-dev.md`): a guarded System 2 alone (gate and verification, no S1 decisions)
matched every arm on verified completions at the lowest cost, \$0.0100 per verified pass against
dual's \$0.0117 and delegation's \$0.0137, with zero false completions everywhere. Dual keeps 26%
fewer LLM calls than the guarded arm and the fewest steps; the first delegation build cost more and
is being rebuilt with explicit ownership before the next measurement.

What the splits say: Jev alone handles navigation, search, pagination, modals and login in two to
five steps and cannot read or answer; the LLM alone reads and answers and will click "Delete
account" when asked to reach a page, and its own judge accepts that as success; the pair is the only
arm with zero false completions on every split. On the fixture heldout the pair now matches stock's
cost with 27% fewer LLM calls and 26% less wall time. On live sites it uses 26% fewer LLM calls than
stock at 1.32× its estimated cost, with the whole gap being Jev call volume (458 calls), and wall time
not distinguishable. Steps run by Jev take a median 1.4 s against 15.7 s for a Muse step. Jev calls
count every request, including verification. Live pass rates are against sites that drift between
runs (stock lost 5 saucedemo checkout tasks in an evening run that passed in the morning). Per-run
failure taxonomies are in each run directory's `taxonomy.md`.

Native hot paths, replayed DOM CPU per step on recorded pages (`results/r5-dom-pipeline.md`,
`results/r7-boundary-decision.md`):

| fixture | upstream | with patches | notes |
|---|---|---|---|
| wikipedia-python (18k nodes) | 146–164 ms | 118 ms | paint order 10 ms to 2.7 ms; per-node uuid removed |
| amazon-usb-c-hub (10k nodes) | 86–90 ms | 64 ms | |

The 50 ms gate was not met. The snapshot-lookup port is equality-proven but not faster, because
upstream's cost is building 18k Python dataclasses, not the lookup; it ships opt-in. The evidence
matcher is 46 to 82x faster and byte-identical to the Python reference on the fixture corpus.

## How it works

- `jevdual/agent.py`: `DualProcessAgent` overrides one upstream method, `_get_next_action`, and
  gates every action before dispatch.
- `jevdual/menu.py` builds the action space from browser-use's selector map within Jev's token budget
  and strips password, card and one-time-code values that upstream leaves in static attributes.
- `jevdual/policy.py` and `prompts.py`: the fan-out request; `arbiter.py` and `arbiter.toml`: the
  escalation rules; `verify.py`: evidence bands and claim checks; `text.py`: literal, secret
  placeholder or a strict helper contract for typed text; `secrets.py`: names only reach models,
  values resolve at dispatch on the matching origin; `tools.py`: `act_toward_goal`, the S1 loop as a
  tool System 2 can call.
- `crates/jevdual-core`: paint order, snapshot lookup, element hashes, evidence matcher.
  `JEVDUAL_PURE_PY=1` forces the Python twins; CI runs both.

## Run it

```sh
uv sync                                    # builds the extension with maturin
uv run pytest                              # native; JEVDUAL_PURE_PY=1 for pure Python
JEVDUAL_BROWSER_TESTS=1 uv run pytest tests/integration tests/test_tools.py
uv run python -m evals.runner --split dev --arm stock --arm dual --llm meta
```

Keys are files under `~/.config/jevdual` (`TYPESAFE_API_KEY`, `META_MODEL_API_KEY`), materialized
from the Sift vault; `jevdual/keys.py` exports them. Requires Rust 1.95 and Python 3.11+.

## Credits

Ideas from the MIT-licensed jev-ultrafast, fastbrowse, jev-browser, jev-for-chrome and
public-browser projects: speculative fan-out, consume-once decisions, evidence-before-done,
origin-bound secrets, proposed-versus-executed traces, stable element references. browserclaw
(AGPL) informed the micro-loop-as-tool design; no code was taken from it. browser-use is the
foundation and stays a dependency.
