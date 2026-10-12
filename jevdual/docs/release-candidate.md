# Footwork capability candidate

This MIT-licensed local candidate gives an agent five MCP tools for one scoped browser-to-TextEdit job: bind, observe, act, status and report. The Python wheel runs without Rust or a model provider account. A real agent host still needs its own working account.

The current slice reads one owned loopback browser page and appends to one exact TextEdit document on macOS. It checks resource identity and preserves durable operation results across server restarts. Configure a new job with the actual browser/document identifiers; reuse its journal only to reconnect that same job. This candidate does not discover arbitrary apps or authorize a broader task.

Start with [installation](capability-packaging.md), then [the agent-host recipe](installed-agent-host.md). The jevdual/scripts directory contains the qualified fixture and installation helpers. Use an existing compatible Python, uv and Chrome. Installation fetches binary dependencies from PyPI; the dependencies are not bundled. Run strict doctor from the responsible host before acting. Automated hosts should use the generated isolated Python commands.

After the agent finishes, validate its structured claims with the emitted report adapter and publish only the returned trusted summary. Native completion is historical evidence; saved-file persistence requires a separate check. If execution is uncertain, collect the durable result instead of repeating input with a new token.

`MANIFEST.json` binds every payload member to its SHA256. `qualification.json` identifies the exact wheel, helper source, measured host scope and supporting evidence. The evidence summaries distinguish the guest permission journey from the real agent task. The artifact is a local release candidate; it has not been published to a registry.

Qualification covers only the exact hosts and environments recorded in those summaries. A previously provisioned macOS guest permission reset is not a never-granted cold OS. Other agent hosts, macOS versions, MDM, pixel capture, arbitrary apps and disk persistence require their own evidence. Dependencies retain their own licenses.
