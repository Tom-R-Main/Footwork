# Why Footwork?

**Keep your planner. Give its computer actions a record you can check.**

An agent can find a button, send input and explain its plan. The next questions matter when the work
changes something: was it the intended document? Did the action land? Is the saved result correct?
What should the next process do if the answer never came back?

Footwork connects target checks, action permissions, retained receipts and result checks for supported
browser and native-app workflows. Use your own agent through the CLI or scoped MCP service, or choose
Footwork's model-driven loop. You do not need to hand over planning to use its execution tools.

## From “I clicked Save” to a checked note

Consider a small handoff: read a fact in a browser and append an approved note to a document.

1. **Bind the source and destination.** A browser observation or literal read identifies its source.
   Native actions use a fresh observation of the selected app/window/control. The scoped MCP route
   binds an explicit source and existing destination document.
2. **Check before changing.** Native exact append checks the current full field value and inserts at
   its measured end. A changed target or value can refuse the operation before input.
3. **Keep the operation's identity.** In the scoped MCP service, repeating an admitted client token
   returns that operation's result. In opt-in durable native sessions, retain the request token and
   authority database across interruptions. An unresolved admitted effect blocks new mutations in
   that authority domain; status and qualified reconciliation remain available.
4. **Check the result you need.** Field readback establishes field content at its capture time.
   `check-artifact` compares the explicitly selected saved file with approved bytes and their digest.
   A delivered keystroke, a field readback and a checked saved file remain separate facts.

The [quickstart](quickstart.md#check-saved-bytes) lets you try the last distinction without a desktop
or model key. The [installed agent-host recipe](installed-agent-host.md) shows the bounded MCP
browser-to-document workflow. Its current scope is a configured loopback source and an explicit
TextEdit document on macOS or Mousepad document on Linux X11; it is not general desktop access.

## Where it earns its place

- **Agent builders adding desktop tools.** Keep planning in your host agent and use explicit
  observations, actions and receipts through the CLI. Learn the current tool surface with
  `footwork tools` and inspect inputs with `footwork schema`.
- **Document and cross-app workflows.** Bind a particular resource, protect an exact append against
  stale content, and retain the distinction between historical execution and current agreement.
- **Work that must survive an interrupted response.** Opt in to durable native admission, keep a
  stable token, and inspect the existing operation rather than guessing whether to repeat it.
- **A shared Mac.** Start with background-only delivery. Foreground access is an explicit choice;
  macOS activity checks can yield while a person is using the computer. Linux shared foreground
  control remains unqualified; use the documented dedicated X11 setup.

The practical benefit is a reviewable handoff: the next person or agent can inspect what was attempted,
what evidence returned, and what remains unknown. That benefit is strongest when a duplicate action
or an incorrect completion report would be more expensive than stopping to investigate.

## Choose the right amount of machinery

Browser tools may already give you locators, actionability waits, assertions and traces. Footwork
connects a supported computer action to its admitted resource, permission, durable operation and
bounded result claim. Those checks take work to configure and can stop a task that a permissive
executor would continue.

A browser library or small tool set is a good fit for a read-only lookup, a deterministic web test or
a task whose application API already supplies authoritative results and retry semantics. Use the
application's native idempotency and reconciliation when available. Footwork is useful when your
agent also needs the supported GUI execution and evidence boundaries described here.

| Route | What to rely on |
| --- | --- |
| Native CLI with `--authority` | Experimental durable admission, immutable request tokens, retained execution receipts and conservative recovery within one shared authority database |
| Scoped MCP service | Its own journal for the qualified bind/observe/append/status/report workflow, including duplicate and restart handling |
| Dedicated browser CLI | Owned Chrome observation and supported actions; native durable authority is not available on this route |
| Model-driven loop | Action gating and completion assessment; it does not inherit the durable native CLI protocol |
| Saved-artifact checker | Exact bytes at an explicit path against the supplied expected file/digest; no judgment of whether the approved content itself is correct |

## Guarantees you can name

An uncertain GUI action is not an exactly-once transaction against an arbitrary application. Footwork
can preserve an admitted unknown and refuse automatic redispatch within the participating durable
authority. It cannot make an external app or browser's own internal retries disappear. A separate
authority database or an executor outside that protocol is outside its coordination boundary.

Action grants express the caller's declared authority. They are not an independently authenticated
human-approval system. A model's completion judgment is bounded by its evidence; it is not an oracle
of every business outcome. Extra app-specific checks may still be required.

See [durable native sessions](durable-native-operator.md) for the protocol and
[capability packaging](capability-packaging.md) for MCP scope. The dated
[agent comparison](../results/capability-comparison-20261009/comparison/report.md) illustrates the
tradeoff: fewer false completions and protected stale edits in those cases, with a clean-completion
guardrail that was not met. It is historical evidence, not a current throughput promise.

Linux X11 desktop support is a [preview](linux-support.md). The installed primary workflow passed;
repeated native sessions still have retained teardown and target-readiness failures. Start with the
qualified route you need, and keep its operating limits with the handoff.
