# Arbiter sweep over g1-s1-only-20260921-010334 (22 traces with S1 decisions)

Counts are recorded S1 steps re-judged offline; 'on failed tasks' means the task did not pass in this run.

| setting | value | act | escalate | confirm | retry | escalations on passed tasks | escalations on failed tasks | top rules |
|---|---|---|---|---|---|---|---|---|
| baseline |  | 35 | 55 | 5 | 1 | 29 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
| act_operation_confidence | 0.45 | 35 | 55 | 5 | 1 | 29 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
| act_operation_confidence | 0.65 | 34 | 56 | 5 | 1 | 30 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
| act_target_confidence | 0.35 | 35 | 55 | 5 | 1 | 29 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
| act_target_confidence | 0.55 | 34 | 56 | 5 | 1 | 30 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
| goal_done_escalate | 0.75 | 35 | 55 | 5 | 1 | 29 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
| goal_done_escalate | 0.95 | 35 | 55 | 5 | 1 | 29 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
| needs_reasoning_escalate | 0.5 | 35 | 55 | 5 | 1 | 29 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
| needs_reasoning_escalate | 0.7 | 35 | 55 | 5 | 1 | 29 | 32 | stuck 33, done_requires_verification 20, destructive 5 |
