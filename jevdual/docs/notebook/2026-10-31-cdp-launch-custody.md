# CDP launch profile custody

## LC1 · prediction · 2026-10-31 12:00
Question: can the owned Chrome launcher alter a profile it did not create?
Hypothesis: accepting an existing profile directory and unlinking its DevToolsActivePort before launch destroys another Chrome's discovery file even if the new process never starts.
Test: call launch with existing empty, populated and symlink profile paths while a Popen sentinel rejects any process creation. Assert typed refusal before Popen, byte-identical retained discovery/profile files, and no symlink target mutation. First run against the current launcher, then require exclusive creation of a private fresh directory and rerun with existing real-Chrome observation tests.
Predicts: the original code reaches Popen and deletes a populated profile's discovery file; exclusive directory creation refuses all existing paths without touching them, while fresh profiles still launch and observe Chrome.
Against: the original code already refuses before mutation; an existing path or symlink target changes after the correction; a fresh profile can no longer launch.
Refs: python/jevdual/effectors/cdp/launch.py; tests/test_cdp_effector.py; PR 16 review.

## LCU1 · update · 2026-10-31 12:01
Resolves: LC1 = held
Observed: the five existing-path cases failed before the correction: existing directories and their symlink reached Popen, while files and dangling symlinks raised untyped FileExistsError. The fresh-private-directory control passed. With exclusive mkdir and no discovery-file deletion, all six custody cases and the current CDP effector tests pass, including the three real-Chrome cases. Ruff passes for the changed launcher and custody tests.
Changes: launch now creates its profile exclusively with mode 0700 and returns browser_profile_unavailable for an existing or unavailable path before Popen. Existing discovery and preference bytes, directory contents and symlink targets remain unchanged.
Next: parent review and hosted CI; no claim of full descendant cleanup follows from fresh-profile ownership. The current group-TERM/root-wait cleanup does not inventory surviving descendants, so a root exit alone cannot prove an empty process group.
Refs: tests/test_cdp_launch_custody.py; output/cdp-launch-custody/before.txt; output/cdp-launch-custody/after.txt; prediction commit 4e001c7.

## LCS · summary · 2026-10-31 12:01
Established: an owned CDP launch requires a newly created private profile; pre-existing files, directories and symlinks refuse before mutation or process creation. Fresh real-Chrome launch and observation still pass.
Uncertain: shutdown of a TERM-resistant descendant after its root exits; root termination is not a full process-tree postcondition. Linux runtime behavior remains the parent's installed-wheel CI check.
Decision: hand off the scoped profile-custody correction and its negative controls. Preserve process-tree cleanup as a separate qualification issue rather than claiming group TERM proves cleanup.
Refs: python/jevdual/effectors/cdp/launch.py; tests/test_cdp_launch_custody.py.

## LC2 · prediction · 2026-10-31 12:05
Question: does owned cleanup leave a TERM-resistant descendant alive when the root exits promptly?
Hypothesis: waiting only for the root after group TERM returns before a TERM-resistant child exits. Capturing descendant pid/start identities while the root is owned and live, then revalidating and stopping those exact processes, closes this demonstrated path without group signaling after the root is reaped.
Test: a dedicated Python helper starts a child that installs SIGTERM ignore and records readiness. A separate sentinel process shares no custody. Run stop and assert the root is reaped, the captured child no longer runs, and the unrelated sentinel is alive. Also exercise a root that exits before inventory: cleanup must raise a typed uncertainty rather than claim success. First run the resistant-child case against the current cleanup, then fix and rerun with real-Chrome observation and profile-custody tests.
Predicts: current stop returns with the resistant child alive; revised cleanup stops the captured child, leaves the sentinel alone, and refuses already-lost custody. It never issues a second group signal after root reaping.
Against: current cleanup already stops the resistant child; revised cleanup signals the unrelated sentinel, targets a changed process incarnation, returns with a live captured child or claims full cleanup without an inventory.
Refs: python/jevdual/effectors/cdp/launch.py; tests/test_cdp_launch_custody.py; parent review request.
