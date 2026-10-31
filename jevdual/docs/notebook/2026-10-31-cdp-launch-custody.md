# CDP launch profile custody

## LC1 · prediction · 2026-10-31 12:00
Question: can the owned Chrome launcher alter a profile it did not create?
Hypothesis: accepting an existing profile directory and unlinking its DevToolsActivePort before launch destroys another Chrome's discovery file even if the new process never starts.
Test: call launch with existing empty, populated and symlink profile paths while a Popen sentinel rejects any process creation. Assert typed refusal before Popen, byte-identical retained discovery/profile files, and no symlink target mutation. First run against the current launcher, then require exclusive creation of a private fresh directory and rerun with existing real-Chrome observation tests.
Predicts: the original code reaches Popen and deletes a populated profile's discovery file; exclusive directory creation refuses all existing paths without touching them, while fresh profiles still launch and observe Chrome.
Against: the original code already refuses before mutation; an existing path or symlink target changes after the correction; a fresh profile can no longer launch.
Refs: python/jevdual/effectors/cdp/launch.py; tests/test_cdp_effector.py; PR 16 review.
