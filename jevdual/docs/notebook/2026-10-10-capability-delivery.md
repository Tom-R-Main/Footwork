# Capability delivery preparation

## DP1 · prediction · 2026-10-10 18:08
Hypothesis: a separate dependency-free wheel installation check can protect the consumer artifact without the development environment, Rust build, native permissions or live UI.
Test: build and verify two wheels, install one without dependencies in a fresh owned environment, plant host-directory shadow modules, run the installed CLI, and check missing-journal reporting and missing-prerequisite strict exit. Wire this check into Linux and macOS CI and reuse U1's binary-only dependency installation on the macOS profiles.
Predicts: the two builds match within each interpreter, installed imports and metadata belong to the fresh environment, isolated CLI invocations ignore host-directory shadows, and unsupported prerequisites or unavailable journals cannot certify completion. CI needs no model credentials or native input.
Against: source/development dependencies are required, the installed CLI imports the planted modules, the checker accepts a false completion, or CI implicitly grants permissions or launches input.
Refs: scripts/build_capability_wheel.py; scripts/capability_clean_install.py; results/clean-installation-20261010/report.md
