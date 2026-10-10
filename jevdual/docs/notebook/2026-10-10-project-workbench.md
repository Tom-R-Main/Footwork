# Project-linked workbench notes

## WB1 · prediction · 2026-10-10 15:11
Hypothesis: a reviewed physical note plus explicit caller-supplied project/question/check metadata can produce a truthful project-bound, independently checked workbench packet without taking the proposed action.
Test: implement isolated link/status/list with exact namespaced project binding, retained desk source and code/revision context; freeze source, run focused conformance and public integration using the user's first live note and chosen Footwork project.
Predicts: one JSON/Markdown record preserves evidence versus interpretation, labels its next check proposed, and verifies exact saved bytes; repeats reuse it; changed/missing/tampered bindings and uncertain writes refuse replay; repo drift is separate from saved bytes.
Against: forged source/carries, name-only project matching, silent different-project linkage, task execution from note text, false completed-check claims, duplicate records or false artifact verification.
Refs: docs/experiments/WB1-project-workbench.md; results/desk-inbox-20261010/report.md; tools/desk-inbox-experiment/; /Volumes/External SSD/referencerepos/openhtf/openhtf/core/test_record.py

## WB2 · prediction · 2026-10-10 15:11
Hypothesis: current on-demand note/hash/JSON work is small compared with public process startup and native OCR, so a Rust rewrite of the orchestration is not supported by the current workload.
Test: measure bounded local repeated file/hash/exact-artifact library work, public CLI/status startup, and one real Vision invocation on retained fixture; record medians/ranges and input hashes on fixed source. No new camera or provider calls.
Predicts: direct small-note validation and image hashing take materially less time than public command/native OCR stages; identify existing native work and process overhead separately.
Against: direct Python processing or hashing dominates the measured route, a sustained high-rate frame workload is found, or local native work was wrongly assumed to be Python.
Refs: docs/rust-boundary.md; crates/jevdual-core/Cargo.toml; tools/desk-inbox-experiment/recognize.swift; results/desk-inbox-20261010/source.json
