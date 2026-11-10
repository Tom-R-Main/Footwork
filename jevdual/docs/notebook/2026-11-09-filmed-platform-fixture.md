# Filmed typing fixture platform isolation

## FPF1 · prediction · 2026-11-09 22:15
Hypothesis: the standalone filmed typing test simulates a Mac AX/web field but leaves native and posture platform routing tied to the host, so Linux correctly selects its qualified native-text route and does not dispatch the Mac web insertion command that the test expects.
Test: run the unchanged test with only the native/posture platform selectors set to Linux in an isolated pytest process, then explicitly use the existing simulated-Mac contract fixture and repeat under both host selector values. Run the affected filmed, posture and Linux native suites without changing production guards.
Predicts: the Linux-selector baseline reproduces the missing type_text failure; explicit fixture isolation restores the same paced web insertion on either host while Linux native safety tests remain green.
Against: the baseline failure instead originates in the new SDK ABI, the Mac fixture still fails to dispatch, or the repair requires relaxing production text qualification or posture checks.
Refs: output/cua-046-upgrade/ci-failure-final.txt; tests/test_filmed_session.py::test_filmed_typing_paces_the_characters; tests/conftest.py::mac_native_contract

## FPFU1 · update · 2026-11-09 22:17
Resolves: FPF1 = held
Observed: the unchanged test failed under Linux native/posture selectors with exactly the hosted missing-type_text assertion. Explicit use of the existing mac_native_contract fixture passes with both Linux and Darwin initial selectors. The filmed, posture and Linux native affected suites pass93 tests; Ruff passes.
Changes: the standalone simulated-Mac test now declares its platform fixture. No production route, capability check or skip changed.
Next: parent commits the two-line fixture correction and reruns hosted CI.
Refs: prediction85abc00; output/cua-046-upgrade/filmed-platform/baseline-linux.txt; output/cua-046-upgrade/filmed-platform/fixed-linux.txt; output/cua-046-upgrade/filmed-platform/fixed-darwin.txt; output/cua-046-upgrade/filmed-platform/affected.txt

## FPFS1 · summary · 2026-11-09 22:17
Established: the standalone test depended on host-specific routing while supplying Mac-only observations; declaring its existing Mac contract fixture fixes the reproduced failure and preserves Linux safety coverage.
Uncertain: the local Linux-selector probe is not a Linux runtime qualification; hosted CI has not rerun at this handoff.
Decision: deliver the minimal test-only repair for parent integration and hosted verification. Product artifact bytes remain unchanged.
Refs: tests/test_filmed_session.py::test_filmed_typing_paces_the_characters; output/cua-046-upgrade/filmed-platform
