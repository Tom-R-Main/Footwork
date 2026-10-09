# Capability slice (thin H4 build)

The first product build after the H4 design: four MCP tools (`bind`, `observe`, `act`, `status`), one host (Claude Code), one flow (fixture browser value -> TextEdit append -> exact readback), one process, one SQLite operations table. Built jointly by Claude (journal, service, kill/busy tests) and Codex (contracts, MCP server, observation projection, backend, missing-judge triage) through the peer mailbox. Design: docs/plans/reference-capability-build-20261009.md, narrowed by docs/plans/agent-superpowers-joint-review-20261009.md.

## CS1 · prediction · 2026-10-09 16:04
Question: does committing intent before dispatch keep an interrupted `act` from turning into a repeated effect?
Hypothesis: with a `dispatching` row committed before the backend call and converted to `unknown` on the next open, an `act` killed mid-dispatch leaves a durable unknown operation that blocks further mutation of that resource. A retried identical call returns the original record, and a tokenless retry is refused as busy, so no second append reaches the document.
Alternatives: SQLite with WAL loses the last commit on SIGKILL under the chosen synchronous setting; or the backend's dispatch returns before the OS delivers input, so `phase` reports not_sent for an effect that later lands.
Test: test_capability_service.py with a fake backend whose dispatch blocks after recording a delivered input; the test SIGKILLs a child process running `act`, reopens the journal in a fresh process, calls `status` and then repeats `act` with the same token and with no token. A separate case raises after delivery (ambiguous phase).
Predicts: after the kill, `status` lists one operation with disposition `unknown`; the same-token repeat returns that operation ID without calling dispatch; the tokenless repeat returns `busy` naming it; the fake document holds the text exactly once; the ambiguous-raise case is `unknown`, never `refused` or `not_sent`.
Against: any run where the reopened journal has no row for the killed call, the fake document holds the text twice, or an ambiguous raise is recorded as refused or not sent.

## CS2 · prediction · 2026-10-09 16:04
Question: can an agent that has never seen Footwork's source use the four tools to complete the flow from the tool descriptions alone?
Hypothesis: offered opaque targets in `observe`, plus a result envelope that names the next useful call, are enough for a fresh Claude Code session given only the MCP registration and the task sentence to read the fixture value, append it to the scoped TextEdit document and confirm it by readback.
Alternatives: the agent stalls on argument shape (observation and target handles, move names), falls back to its own built-in computer-use or shell tools, or reads repository source to find out how to call the tools.
Test: three fresh Claude Code sessions in a clean directory with only the Footwork MCP server registered, the fixture page served locally and the TextEdit document scoped at bind. Task text fixed in advance; transcript and journal kept per session; no help from the operator during a session.
Predicts: in all three sessions an independent accessibility readback shows the document text equal to its starting text followed by the exact value once (observed content, not a save), and the journal holds an `applied` operation whose readback evidence matches; no session reads files under the repository or uses a non-Footwork tool to touch the browser or TextEdit; schema/argument repairs at most two per session.
Against: any session that needs source reading, operator help or a non-Footwork tool to finish; a duplicate or wrong append; or more than two argument repairs in a session.
