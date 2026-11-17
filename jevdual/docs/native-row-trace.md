# Private row observation diagnostics

This opt-in diagnostic observes the existing SDK row census. It adds no input route,
traversal, predicate, foreground exception or census budget. It is not a qualified
recipient and must never be used to authorize a click.

Set `FOOTWORK_ROW_TRACE_CONFIG` to an absolute private JSON file containing exactly
`pid`, `window_id`, `url`, and `output`. The target must match the native session;
`url` must be the authorized exact ASCII HTTP numeric-loopback page, with an optional decimal port 1–65535 and no credentials, query, fragment, whitespace or backslash. The same strict authority grammar runs at typed and native SDK ingress before collection. `output` must be a new
absolute file in the private evidence directory. Run the normal public `start`
once using app/title selection and exact diagnostic PID/window configuration: start itself observes. Explicit `--pid` start currently observes twice and is unsuitable for this one-collection route. A discovery result that differs from the configuration refuses before the SDK collection; there is no fallback. Do not also call `look`. Native URL/title guards require their already-authorized durable route; `--url` is navigation and is excluded.
Configuration is checked before the SDK call; output is created exclusively with
mode 0600 after collection. An existing output refuses rather than overwriting it.

The typed request adds `row_trace_url`; the typed reply adds `row_trace_json`.
The private artifact records the actual request, snapshot id, SDK stage, first
capture error or canonical graph/per-key results, proof attachment, typed element
proofs/token presence and projected candidate proofs. Object IDs are local census
integers. Raw AX pointers and actionable token strings are not retained.

The graph is retained only if the existing census has exactly one web area with
the requested URL. Before scope is established, only request identity, fixed error
messages, node/role, budgets and counters survive. Unscoped page content and proofs
are withheld. `attribute_action_reads` counts the existing attribute/action reads;
it does not claim to count PID/window identity C calls. There are no extra AX calls.

Limits: graph 2 MiB, SDK payload 3 MiB, private artifact 4 MiB; key/result lists 128,
attachment/typed elements 2048 and candidates 1000. Every exceeded bound marks
`truncated`; missing SDK data, scope mismatch and retention failures are distinct
from success. Truncation or missing evidence is not qualification. A whole SDK call
that fails before returning cannot supply the census trace; retain its public error
and treat the missing artifact as a stop, never repeat automatically.

Bookkeeping costs CPU and memory. Existing 2-second/2048-node/4096-reference/500000-
comparison limits remain unchanged; a scheduling difference near a wall-time limit
cannot be excluded. Pure graph on/off checks compare the same decisions; no live AX
budget, latency or page topology is claimed from fixtures. Serialization and file
I/O occur after the AX collection. Callback ownership remains byte-identical.

The authorized live use is one bound Tasks observation after reviewed delivery,
with Desktop's owner channel paused. No activation, input or functional repair is
part of this diagnostic. A start observation consumes the entire collection slot.

Snapshot identity is compared across request, enclosing SDK response and embedded trace. A disagreement is invalid; missing/empty snapshot IDs are `snapshot_unproven`, with only explicitly unbound failure context retained and no graph or proofs. Diagnostics remain non-authoritative.

Capture node/role fields are last-current context; a budget refusal before the next node assignment does not identify a new faulting object. Byte limits bound serialized retention, not peak process allocations.
