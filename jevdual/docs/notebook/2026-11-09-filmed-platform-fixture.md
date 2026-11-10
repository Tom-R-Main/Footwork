# Filmed typing fixture platform isolation

## FPF1 · prediction · 2026-11-09 22:15
Hypothesis: the standalone filmed typing test simulates a Mac AX/web field but leaves native and posture platform routing tied to the host, so Linux correctly selects its qualified native-text route and does not dispatch the Mac web insertion command that the test expects.
Test: run the unchanged test with only the native/posture platform selectors set to Linux in an isolated pytest process, then explicitly use the existing simulated-Mac contract fixture and repeat under both host selector values. Run the affected filmed, posture and Linux native suites without changing production guards.
Predicts: the Linux-selector baseline reproduces the missing type_text failure; explicit fixture isolation restores the same paced web insertion on either host while Linux native safety tests remain green.
Against: the baseline failure instead originates in the new SDK ABI, the Mac fixture still fails to dispatch, or the repair requires relaxing production text qualification or posture checks.
Refs: output/cua-046-upgrade/ci-failure-final.txt; tests/test_filmed_session.py::test_filmed_typing_paces_the_characters; tests/conftest.py::mac_native_contract
