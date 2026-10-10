# D1 Decisions contract probe

On committed implementation 5962744, one authenticated request returned all three registered
native answer types and the correct synthetic answers. Returned model gpt-6-luna; input usage
392 tokens, output zero; input-only estimated charge $0.0000392. Wall latency 1288.83 ms includes
client construction, connection and local receipt handling. See results.json, budget.json,
started.json and closed.json. Redaction reported no changed files.

This establishes usable access and this response shape, not accuracy, calibration or latency
against Jev. The complete development comparison remains unrun. Include this charge in its cap.
