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

Dev split, 23 local tasks (`results/g2-dev-three-arms.md`):

| arm | pass | false done | LLM calls | Jev calls | est. cost USD | wall s |
|---|---|---|---|---|---|---|
| S1 only (Jev) | 10/23 | 12 | 0 | 99 | 0.010 | 97 |
| stock browser-use (Muse Spark 1.3 Contributor) | 21/23 | 2 | 67 | 0 | 0.095 | 1,143 |
| dual (Jev + Muse) | 22/23 | 0 (1 paused) | 31 | 39 | 0.063 | 987 |

Heldout split, 10 local tasks, settings frozen first, never debugged (`results/heldout-final.md`):

| arm | pass | false done | LLM calls | Jev calls | est. cost USD | wall s |
|---|---|---|---|---|---|---|
| S1 only | 1/10 | 7 | 0 | 47 | 0.005 | 60 |
| stock | 9/10 | 1 | 33 | 0 | 0.047 | 674 |
| dual | 10/10 | 0 (1 paused) | 20 | 22 | 0.038 | 551 |

What the split says: Jev alone handles navigation, search, pagination, modals and login in two to
five steps and cannot read or answer; the LLM alone reads and answers and will click "Delete
account" when asked to reach a page; the pair does both, with 40 to 60% fewer LLM calls. The
failure taxonomy per run is in each run directory's `taxonomy.md`.

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
