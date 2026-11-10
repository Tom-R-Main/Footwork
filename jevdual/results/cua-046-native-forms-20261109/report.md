# CUA 0.46 and native Chrome form acceptance

The reported native targeting defects are resolved and passed an actual Chrome acceptance fixture through the public Footwork CLI. CUA advances to `0.46.0+footwork.5486b624.cleanup2`: latest upstream release plus the retained task-cleanup ownership patch, because stock 0.46 still omits that guarantee.

## Native acceptance

`acceptance.json` records all seven checks passing in 23 commands. The independent fixture server confirms alpha-domain selection before and after row reorder; beta never receives an action. A real link excluded by the default 160-candidate budget is refused and logged. The late Custom DNS popup remains selectable. Empty placeholder-labelled fields remain empty until typed. Removing and renumbering a field makes the stale pending target refuse without input. Four distinct backing fields receive ns1 through ns4.example.test, save exactly once, and reappear after a server reload; beta remains unchanged. `persisted.json` is the server-side saved state.

The runner uses an owned loopback fixture, temporary Chrome profile, exact PID and nonce window title. It runs the ordinary native route matching the original report. The fixture alone uses `--no-judge`. Browser and server are closed by the runner. No personal browser or actual nameservers were changed. No Namecheap page was open for a read-only comparison, so the actual provider page has not been requalified.

Raw local evidence: `output/cua-046-upgrade/live-2` includes command receipts, session journals and independent server ledger. These are retained locally, not copied into version control. The earlier `live-1` fixture accidentally opted into durable authority; its unknown-delivery gate correctly stopped after the first generic click. Its unresolved journal remains preserved. This acceptance makes no claim that durable native delivery is qualified.

## Validation

- Actual installed patched CUA environment: 2,935 passed, 51 skipped, 66 deselected (`pytest.txt`).
- Three native cleanup ownership/reaping/cancellation regressions pass (`cleanup-core-tests.txt`).
- SDK shutdown waits after a cancelled cleanup drain (`cleanup-sdk-tests.txt`). The first SDK test compile exposed a missing test-local AtomicBool import removed upstream; the carried patch now imports it locally. Production logic was unchanged.
- Full Ruff passes; acceptance runner has nine offline tests and a JavaScript syntax check.
- Source review: exact upstream release, bounded four-file cleanup patch, matching generated bindings and unchanged Cargo dependencies. Prior 0.38 cleanup provenance is retained under vendor history.

The live run and full Python suite used the first built 0.46 patch artifact. The final archive differs only by the SDK test-local import; installed contract and packaging checks are rerun against the final artifact. Exact final hashes and qualification are recorded below when completed.
