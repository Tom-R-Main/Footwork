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

## CL3 · prediction · 2026-10-09 16:50
Hypothesis: AppleScript's open POSIX file lacks the per-file sandbox extension TextEdit needs, while Launch Services open -a TextEdit grants it. The owned alert says this fixture cannot be opened despite same-UID readable file permissions; this is not absent Accessibility or a locked screen.
Alternatives: TextEdit has a broader filesystem permission problem that neither opening route can solve; an earlier modal dialog prevented processing the request.
Test: Acknowledge only the alert explicitly naming this run's owned fixture, then use Launch Services to open the next fresh run-owned plain-text document. Wait for its exact AXDocument path before constructing scope. No OS permission changes or provider calls.
Predicts: the Launch Services route yields an exact fixture document AX identity without a file-access alert, permitting the unpaid MCP preflight.
Against: the exact fixture remains inaccessible or the same owned permission alert appears after Launch Services opening.
Refs: scripts/capability_fixture.py; output/capability-live-20261009-1647; 64ddfdb
