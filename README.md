# Footwork

A dual-process browser agent: fast, calibrated System 1 decisions from
[TypeSafe Jev](https://docs.typesafe.ai) in front of the deliberate System 2 LLM loop of
[browser-use](https://github.com/browser-use/browser-use), with a code-owned arbiter, evidence-based
verification, and Rust hot paths.

- `jevdual/` — the package (Python + PyO3 crate), eval rig, and results. Start with its README.
- `browser-use/` — the upstream foundation, pinned as a submodule at the commit the design and
  profiling were done against. `jevdual` depends on the released `browser-use==0.13.10` from PyPI;
  the checkout is here for reading, profiling and contract tests, not for import.

Six sibling repos studied for the design (jev-ultrafast, fastbrowse, jev-browser, jev-for-chrome,
public-browser, browserclaw) live alongside these directories locally but are git-ignored; they are
credited in `jevdual/README.md`.

```sh
git clone --recurse-submodules https://github.com/Tom-R-Main/Footwork.git
cd Footwork/jevdual && uv sync && uv run pytest
```
