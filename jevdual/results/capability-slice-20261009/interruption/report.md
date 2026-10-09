# Real-route interruption: CS3 held

Both preregistered cases ran once through the public MCP interface and held. No model/provider calls were made.

| Case | Trigger | Durable state at kill | Field insertion after kill | Restart | Same-token repeat | Fresh tokenless append |
|---|---|---|---|---|---|---|
| A | Exact field changed | dispatching | exactly once | unknown/ambiguous | original operation, no insertion | busy |
| B | Durable intent observed | dispatching | absent in observations | unknown/ambiguous | original operation, no insertion | busy |

The caller withheld the act reply and used only public status/act/bind/observe after restarting on the same journal. Independent AX checks after kill, settle, repeat and attempted tokenless append found no additional insertion. Read-only journal watchers only classified the kill evidence; they did not steer the recovery caller. Case B does not prove the OS call could never have been in flight; conservative unknown is intentional.

Predictions were committed in 703ebd8 and verifier in 808d86f before either case. receipt.json records raw evidence paths and hashes. This is scoped recovery evidence, not a universal exactly-once or raw-backend superiority claim.
