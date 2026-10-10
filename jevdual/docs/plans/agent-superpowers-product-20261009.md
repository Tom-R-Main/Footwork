# Footwork as an MIT-licensed capability system for agents

Product direction selected by the user on October 9, 2026: other agents should use Footwork with minimal configuration, call it for additional capabilities, and have browser/native computer-use mechanics abstracted behind an intuitive interface. This selects **H4, the capability broker**, from the reviewed architectural alternatives. Implementation and capability qualification remain separate work.

## Product promise

**Give an existing agent dependable hands and eyes through a small tool interface.** The host agent keeps its conversation, intent, planning and model. Footwork manages selected resources, driver mechanics, fresh targets, guarded operations, settling, evidence, uncertainty and recoverable tool calls.

An agent should not need to learn Chrome debugging ports, AX/DOM differences, target-renumbering rules, fixed sleeps, screenshot scales or receipt regexes to do ordinary supported work. It should receive a real resource handle, current supported moves, a structured result and the next useful move. Abstract mechanics; preserve meaningful capability and evidence limits.

The repository and Python package already carry MIT licenses (`LICENSE`, `jevdual/LICENSE`, `pyproject.toml`). Keep the core, protocol, SDK and distributed examples MIT-licensed. Dependency/adaptor components retain their own licenses and notices; the root license does not automatically relicense third-party code. Distribution checks must account for shipped components. API/provider accounts and service terms are separate from the code license. No license file changes are needed for this design decision.

## Ownership and deployment

The host owns the overall job. Footwork owns each governed operation and its durable pending/evidence state. Bounded local routines may be offered as capabilities; they do not take ownership of the host's whole plan. No independent agent swarm or mandatory workflow-authoring layer is part of the first product.

Use a shared execution library behind three consistent entry points:

- **Local MCP server over stdio** as the primary integration: an MCP-capable host launches the tool process from one registration.
- **Python SDK** for direct integrations and tests, using the same contracts.
- **CLI with structured JSON output** for hosts without MCP and for troubleshooting.

MCP supports host/server integration and local process transports; client setup remains host-specific. [MCP architecture](https://modelcontextprotocol.io/docs/learn/architecture), [local server connections](https://modelcontextprotocol.io/docs/develop/connect-local-servers). Protocol support alone does not prove support in every host or authorization enforcement.

Default to a host-launched local process with no public listening port or required cloud control plane. Keep driver connections warm while the tool process owns them. If the process exits, persisted pending operations and owed results survive for the next authorized invocation; no unattended planning/liveness promise is implied. Multiple broker processes need shared resource/task ownership and machine input arbitration before concurrent mutation is supported. A standalone shared daemon is a later optimization, not initial setup overhead.

Stdio integration attributes requests to the host that launched the process and its delegated task scope. It is not containment of a malicious same-user host. An optional multi-client/socket service needs separately qualified pairing, scope attenuation and credential protection. Keep assurance limited to mediated effects and observable external changes.

## A small semantic interface

These are proposed contracts, not implemented command names or a frozen tool-count target:

| Tool family | Agent intention | Footwork responsibility |
|---|---|---|
| Bind/open | Work with this URL, selected tab, app window or artifact | Resolve scope and identity; return an opaque handle and real capabilities; create only authorized resources |
| Observe | Show what can be read or done here | Fresh DOM/AX projection, offered targets, resource/evidence identity, generation and coverage limits |
| Act | Click, fill, append, choose, press, scroll, navigate or save on an offered resource | Route qualification, scope/preconditions, dispatch accounting, settle/reobserve and truthful readback |
| Verify | Check this declared result or artifact | Separate visible change, persistence, correctness and unsupported/unknown checks |
| Resume/status | Continue this operation/task or collect its result | Current projection, pending/unknown attempts, remaining reservations and result custody |

Keep common semantics where the surfaces genuinely support them. Surface-specific capabilities appear when needed. A `save` cannot pretend every native app offers the same save-copy semantics. A browser download must name the actual resulting artifact. Unsupported operations return a concrete limit rather than an invented fallback.

An opaque target is valid for its observation. The agent can select a unique observed semantic target without seeing a raw selector, but ambiguity or changed identity still requires resolution. Remapping must preserve the approved operation and arguments; visual judgments cannot silently rebind a target.

Example experience, not a runnable API:

```text
Host: open this scoped invoice page
Footwork: bound browser resource; current observations and capabilities
Host: read the total and append it to this scoped report
Footwork: source-bound value, destination readback, recorded operation IDs
Host: save a new copy in this folder and verify it
Footwork: saved artifact identity and exact checks, or an explicit unknown outcome
```

Structured tool replies include operation ID, disposition, delivery facts, observed change, resource/evidence references, fulfillment/check status and permitted recovery. A short model-visible explanation is rendered from those records. It never replaces them. An uncertain timeout produces reconciliation instructions, not advice to click again.

## Minimal configuration as an acceptance requirement

The intended first-run flow is: install a platform distribution, register the local tool command in the host, complete any required platform permission grants, and let the agent perform an authorized demonstration. Installation/registration can be agent-driven when the host has that authority. macOS Accessibility and applicable capture permissions still belong to the machine owner; do not promise an agent can grant them to itself.

Avoid making ordinary consumers compile Rust, assemble browser profiles, edit several environment files or create a Footwork account. Candidate packaging is prebuilt platform distributions and Python wheels, with optional native acceleration and surface/model adapters. The current Maturin build and unconditional dependency set do not yet satisfy that goal; release engineering is required.

A diagnostic command should distinguish missing executable, unsupported platform/route, denied platform permission, unavailable browser attachment, missing required judgment and invalid host setup. It should return structured remediation an agent can apply within its existing authority. It should not require repeated user approval for ordinary in-envelope repair or automatically install network dependencies without the host's authorization.

Observation and structurally qualified actions should use the caller's existing reasoning where adequate. Specialized semantic/visual services are opt-in and capability-declared, with explicit credentials, disclosure and cost. Do not make every ordinary tool call buy a second general-purpose model turn. Required checks remain mandatory on affected routes; missing model access returns `judgment_unavailable` rather than silently weakening the guard. Preserve current qualified Jev roles/settings until a measured migration earns a replacement.

## Extra capabilities that earn their abstraction

First deliver semantic observations, consistent guarded actions, cross-surface carried values, exact field/artifact readback and continuation after host turnover. Those are useful even when the host supplies all planning.

Then evaluate bounded routines such as navigating a known form or collecting a named output. Each routine declares resources, allowed effects, stop conditions, evidence and task-owned budgets. Footwork's earlier Q9e delegation comparison did not earn adoption, so a broad “do this goal for me” micro-agent should not be the default abstraction without new evidence. [Q9e](../../results/q9e-delegate-fixed.md).

Current native visual checks are advisory and opt-in; independent quality, browser geometry and visual execution remain qualification gates. OCR, new platform drivers and arbitrary app support must declare real readiness. An unavailable route should be easy for an agent to diagnose, not hidden behind a universal-computer-use claim.

## Design and delivery order

1. Freeze the public tool/result contracts with actual host callers and typed task scope. Include unknown effects and resume from the first version.
2. Extract a shared operation/evidence service from the current operator paths. Build transactional intent/grant/task-reservation accounting and source/resource identity before advertising reliable recovery.
3. Add MCP stdio, SDK and JSON CLI adapters over that same service. Preserve pinned browser/Cua behavior and qualified model roles.
4. Package one supported platform so consumers do not need a toolchain. Add diagnostics and host-specific registration helpers; configuration writes/installations remain explicit host actions.
5. Verify through actual external host integrations using the same browser-to-native task and adversarial scenario matrix. Do not substitute a direct unit call for host integration proof.
6. Broaden surface/platform coverage and higher-level routines only when they improve useful verified outcomes and setup/repair burden.

The primary product check is whether a fresh agent can discover, configure and use Footwork, recover from a tool/process interruption, and explain the result without reading source or reconstructing internal driver state. Measure first verified task time, configuration decisions, user interventions, schema/target repairs, verified coverage and cost/time per verified outcome. Compare multiple supported hosts and retain failures and unsupported cases.

This direction uses H1's library organization internally, H5-style bounded resource readback where useful, and optional H2 attachment techniques when measured. **H4 remains the product boundary and the host remains the owner of the broader plan.** The prior Opus reviews support the conditional H4 direction for external-agent use; this specific product brief has not received a new Opus review or implementation verification.
