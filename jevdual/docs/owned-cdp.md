# An owned browser, with a memory for uncertain actions

The headless CDP lane lets an agent observe a page and activate a narrowly supported button without
starting a desktop session. It needs Chrome, a configured judgment provider and durable storage.
It does not need CUA, X11, a window manager or AT-SPI at runtime.

The useful part is what happens when the connection disappears. Footwork records an operation before
it can activate the button. The next CLI process can retrieve that operation by its original token.
It will not click again to find out whether the first click worked.

This is an explicit preview route, `footwork browser cdp`. The older `footwork browser start/look/do`
commands keep their existing CUA behavior. The package still declares its full dependencies; the
CUA-free **install** is a later packaging change. A manually assembled qualification environment is
not yet the supported light installer.

## The loop

After installing Footwork, configure Jev through `TYPESAFE_API_KEY`, then use a fresh, short absolute
session path. Keep the authority database on durable storage. Sessions that share a database also
share its unresolved-operation gate.

```sh
footwork doctor
footwork schema browser cdp start
footwork browser cdp guide              # this installed version's contract

footwork browser cdp start 'Commit the fixture once' \
  --session /tmp/fw-example \
  --authority /absolute/durable/browser-authority.db \
  --url http://127.0.0.1:8000/fixture

footwork browser cdp look --session /tmp/fw-example
footwork browser cdp click --session /tmp/fw-example \
  --ref REF_FROM_LOOK --token fixture-commit-1
footwork browser cdp status --session /tmp/fw-example --token fixture-commit-1
footwork browser cdp stop --session /tmp/fw-example
```

Choose the opaque ref returned by `look`. Repeating the exact ref and token retrieves the retained
operation; changing the request under that token conflicts. A new observation cannot clear an
uncertain operation. If the holder disappears, use `recover --session DIR` to inspect the journal.
Recovery does not start Chrome, adopt a tab or reconstruct a target from its URL.

Only directly named, plain main-document `button[type=button]` controls are eligible. The activation
route is `dom_event_native_button`; it is not a pointer sequence or trusted input. Typing remains
disabled because the focus race is unresolved. There is no navigation RPC; loading the initial URL
is explicit setup and can itself have website effects outside the guarded click protocol.

## Read the operation, then decide

| Retained evidence | What Footwork reports |
| --- | --- |
| Prepared intent, interrupted before durable start | `not_sent` after read-only recovery |
| Qualified refusal before activation | `not_sent` |
| Activation acknowledged by Chrome | `unknown`, phase `sent`, completion `unverified` |
| Start committed, reply unavailable | `unknown`, completion `unverified`; do not retry |

An acknowledgement tells you that activation was invoked. It does not establish the website's
business effect. This tranche has no qualified browser completion reader, so an acknowledged or
ambiguous activation blocks further mutations in that authority database. The lane is useful for
qualifying durable execution; it is not yet a general multi-step browser agent. A future reader must
bind independent application evidence to the admitted operation and arguments. A success banner or
matching current DOM cannot do that by itself.

Do not switch databases or invent a new token to work around an unknown. Keep the original operation
and resolve the real application state before continuing outside this preview lane.

## Bring a judgment adapter

The default judgment provider is Jev. For a different provider, `--guard-command FILE` accepts a JSON
argv array whose first entry is an absolute executable path. This is trusted policy code chosen by
the operator, not a sandbox or a built-in approval stub. The executable receives one JSON object on
stdin and must return one bounded JSON object on stdout within the deadline.

The request names `footwork.browser.guard.request`, version `1`, and includes `digest`, `task`,
`targets`, `url`, `title` and the complete browser `binding`. The response must contain exactly:

```json
{"producer":"footwork.browser.guard","version":1,"digest":"THE_REQUEST_DIGEST","probabilities":[0.8]}
```

The probability is the provider's destructive-action judgment, not an allow flag. The existing
Authorizer applies its keyword checks and destructive threshold. Missing, malformed, failed or
high-risk judgment refuses before admission. There is no `--no-judge` or destructive-grant bypass
in this preview route.

## Custody and cleanup

One holder owns the Chrome handle, CDP connection, exact document refs and authority lock. Clients
use a private Unix socket and check the holder's process incarnation and kernel peer identity.
That protects cooperative session routing; it does not isolate Footwork from arbitrary code running
as the same user. Chrome still exposes its owned loopback CDP endpoint. Process-owned pipe transport
remains future custody hardening.

`stop` closes the original owned process handles and reports bounded cleanup separately from action
outcome. Holder death may leave Chrome descendants alive. Recovery never guesses which PIDs to kill,
and a cleanup acknowledgement never settles an uncertain business effect.
