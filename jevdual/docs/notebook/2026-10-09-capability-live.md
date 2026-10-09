# Real fixture route and host acceptance

## CL1 · exploratory · 2026-10-09 16:43
Question: can the committed thin MCP slice bind and observe a dedicated loopback browser window and a scoped TextEdit fixture, append its known value and obtain exact native field readback on this machine?
Test: Prepare a run-owned HTTP page, dedicated Chrome profile and TextEdit plain-text document under the project's private output directory. Use the real MCP subprocess/public four tools against implementation d49b0fd, without a model/provider. Record explicit resource IDs and exact observations/readback; retain an independent document oracle. This is surface prerequisite/development verification, not the fresh-agent CS2 trial or the C1 comparison. No user browser profile or unrelated document is changed, and only run-owned resources are cleaned up.
Refs: docs/notebook/2026-10-09-capability-slice.md:CS2; docs/experiments/C1-capability-slice.md; python/jevdual/capability/mcp_server.py; d49b0fd

## CL2 · update · 2026-10-09 16:46
Observed: First live fixture prerequisite failed before scope creation or append: the pinned Cua ListWindowsInput requires on_screen_only, omitted by the fixture helper. Cleanup then failed because the fixture was absent from TextEdit's scripting document collection. Independently terminated only the Chrome instance identified by this run's exact profile path; no model calls occurred. This is a harness failure, not measured adapter or CS2 behavior.
Changes: Supply the required SDK field, explicitly open the exact file through TextEdit, use a unique document basename and make failed document cleanup unable to skip browser/process cleanup.
Next: Check the fixture helper against the installed SDK and retry prerequisite verification with fresh owned resources. Do not start CS2 until the actual scoped resources are observed.
Refs: scripts/capability_fixture.py; output/capability-live-20261009-1643; f8009e4
