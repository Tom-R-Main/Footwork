# OA: durable native operator admission

Baseline `deacfa9`; October 28, 2026. This engineering protocol precedes implementation tests.

## Hypothesis and design

Reuse Journal's SQLite transaction/lock/operation model with versioned operator admission and authority bookkeeping. Explicit native sessions enroll in one configured absolute authority database. Legacy sessions and MCP remain outside this guarantee. Test through the actual CLI against the existing simulated Mac, plus isolated service/subprocess boundaries. No live applications, provider calls, dependency installs, heldout tasks or personal data.

Primary metric: independent driver input count on replay/recovery after an interrupted admitted operation. The expected count is unchanged by replay, blocked admission, or projection repair. Also assert intent/reservation conservation, phase/state validity, session ownership and retained history. Preparation may recover no-send only under a validated protocol preventing input before a durable started marker. A started operation cannot acquire no-send from absence of a result or from matching external state.

## Coverage and decision

Exercise before admission, prepared, started, effect before finish, and finish before projection/response; distinguish cooperative cancellation from real subprocess SIGKILL with a durable independent ledger. Exercise two session directories and alias labels against one domain, request-token conflict, secret/carry-independent replay, process reincarnation, and unsupported version refusal. Spent authority does not imply a resolved effect. Required grants reserve atomically; ordinary policy-authorized input records its basis with no artificial grant.

Require the actual command interruption reproduction to show blocking/replay in durable mode; retain legacy characterization explicitly as an excluded migration path. Existing capability/recovery contracts must remain intact. Stop qualification on any extra input, false no-send, lost authority or unsafe projection. Record failures and amendments rather than weakening guarantees. Do not infer installed app support or power-loss durability from these tests. Append results below after execution.
