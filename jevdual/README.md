# jevdual

A dual-process browser agent built on [browser-use](https://github.com/browser-use/browser-use)
(pinned, not forked). System 1 is [TypeSafe Jev](https://docs.typesafe.ai), asked one
speculative fan-out question set per step and injected at the agent's decision seam.
System 2 is the stock browser-use LLM path. A code-owned arbiter decides which system
acts; verification requires evidence before any run is called done. Measured hot paths
in the DOM pipeline run in Rust via PyO3, each with a pure-Python twin and equality tests.

## Install

```sh
uv sync                      # builds the native extension with maturin
uv run pytest                # native backend
JEVDUAL_PURE_PY=1 uv run pytest   # pure-Python fallback
```

Requires Rust 1.95 (pinned in `rust-toolchain.toml`) and Python 3.11+.

## Layout

- `python/jevdual/` — the package; `_native.py` selects the backend, `_pure/` holds reference twins
- `crates/jevdual-core/` — the PyO3 extension (`jevdual._core`)
- `tests/contract/` — pins the browser-use seams we depend on
- `tests/equality/` — native vs pure-Python over recorded CDP fixtures
- `evals/` — three-arm eval rig (stock / S1-only / dual), dev and heldout task sets
- `results/` — every number in this README traces to a file here

## Credits

Ideas borrowed from the MIT-licensed jev-ultrafast, fastbrowse, jev-browser, jev-for-chrome and public-browser projects. browserclaw (AGPL) informed the micro-loop-as-tool design; no code was taken from it.
