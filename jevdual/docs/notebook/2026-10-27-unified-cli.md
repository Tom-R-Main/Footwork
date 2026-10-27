# Unified agent CLI

## UC1 · prediction · 2026-10-27 17:59
Hypothesis: a packaged command router and discoverable machine-readable catalog can expose existing browser/native operations and auxiliary Footwork tools through one installed executable without weakening existing admission or claiming unavailable integrations.
Test: package tool resources and route existing entry points; exercise installed CLI discovery/help/JSON envelopes and failure paths, existing session scenarios and headless browser tests, clean wheel installation outside the checkout, hosted CI and review before merge.
Predicts: installed commands resolve independently of checkout paths, preserve underlying exit/authority semantics, report missing optional runtimes explicitly, and cover every public operational tool family in the catalog with executable routes or explicit adapter prerequisites.
Against: a command requires checkout-relative files, dispatch bypasses an existing gate, unsafe output is promoted to success, or an advertised operation has no working installed route.
Refs: python/jevdual/cli.py; python/jevdual/capability/cli.py; tools/; scripts/build_capability_wheel.py

## UCU1 · update · 2026-10-27 18:10
Observed: unified discovery, argument schemas, JSON invocation, browser/desktop routing and capability commands are implemented. Installed auxiliary operations use bundled resources and private workspace roots; source-frozen research and injected browser-adapter requirements remain explicit. An initial simulator probe refused a symlinked macOS temporary root; using its canonical path fixes the probe without relaxing the gate. Readiness streaming and installer role-pointer validation were repaired before publication. Broad local suite passes 1679 tests; final focused CLI/packaging/onboarding checks pass 66. Both wheel formats contain the same 103 resources, and a full-tools bundle installs and runs actual simulator init/status outside checkout. Installed native desktop observation returns a JSON envelope without asserting a verified effect.
Inferred: the command and packaging boundary supports one installed operational entrypoint while preserving underlying authority and honest adapter prerequisites.
Next: publish the candidate, verify installed discovery and simulator in hosted CI, address review, then merge only after checks pass.
Refs: output/unified-cli-full-tests.txt; output/unified-cli-final-focused.txt; output/unified-cli-installed-native.json; output/unified-installed-fresh-bench.json; scripts/unified_cli_check.py

## UCS1 · summary · 2026-10-27 18:10
Established: local CLI and installed packaging checks pass; original commands remain available, public operational families are discoverable, and all bundled runtime resources are checked for drift.
Uncertain: hosted platform runs and final review remain pending. Host Node/Swift/ffmpeg/hardware/permission prerequisites are explicit, as are research checkout and browser adapter requirements; no new model/provider qualification is claimed.
Decision: hand off the tested candidate to hosted CI and PR review under the user's explicit merge authorization.
Refs: docs/unified-cli.md; tests/test_agent_cli.py; tests/test_tool_catalog.py; tests/test_unified_packaging.py

## UCU2 · update · 2026-10-27 18:16
Observed: hosted review identified dropped string-valued SystemExit diagnostics; actual session parse_do errors and malformed-secret regressions failed before the repair. The router now preserves error text and exit semantics while redacting even malformed secret arguments; 103 focused CLI/session regressions pass. The separate preregistration finding is contradicted by parent f2b3047, whose notebook contains UC1 alone before 1cf30f4 adds results.
Next: publish the diagnostic repair, resolve review threads with commit evidence, and verify final-head hosted checks before merge.
Refs: output/unified-systemexit-before.txt; output/unified-systemexit-after.txt; f2b3047; PR5 review threads
