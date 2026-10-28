# OD: operator dispatch uncertainty

Engineering diagnostic protocol, baseline 5d494c6, October 28, 2026.

## Hypothesis and competing explanations

Driver exceptions after input are mislabeled as no-send; native -25204 retry can duplicate input. Separately, cancellation after grant consumption escapes before operation recording. Alternatives are an existing qualified no-send gate, retained blocking state, or a fixture that never reaches input.

## Design

Use existing native bridge tests and real CLI scenarios against tests/fixtures/native_world.py. Observe independent press counts and persisted session/grant records. Add post-press errors and cooperative cancellation at the actual driver/bridge boundary. Run safety regressions before runtime edits and retain failing output, then fix only the demonstrated error/retry mechanism and rerun. Cancellation diagnosis is retained as a passing characterization until durable admission is implemented. Include positive pre-input refusal controls. No live app, provider, dependency change, heldout or paid evaluation.

## Predictions and primary metric

Primary metric: underlying input count for one admitted simulated command after an injected post-input error. Predicted old behavior is refusal misclassification or count greater than one on -25204; corrected behavior is one input with uncertain effect. Cancellation predicts consumed grant without a do record and duplicate effect after a newly granted retry. Notebook OD1/OD2 define contradicting outcomes.

## Guardrails and decision

Change no authority policy or verifier threshold. Keep secrets opaque. Distinguish cancellation from SIGKILL and simulated commands from installed qualification. If the boundary never reaches input, repair the reproduction before interpreting it. Preserve failed predictions and old-path output. Accept package 1 only when the reproduction passes after the fix, qualified no-send remains no-send, and relevant regression/lint checks pass. Durable process-death/cancellation safety belongs to the subsequent admission package.
