# SIM10: Browser workbench on a persistent network body

Hypothesis: an image-guided browser operator can use the existing durable network client while keeping physical authority local and making transport uncertainty recoverable by explicit user controls.

Predictions if true: successive browser jobs retain one body, independently verified measurements and contact resets; a lost motion reply visibly blocks the queue; disconnect/reconnect and reload do not resend that command; receipt lookup settles only retained evidence and requires explicit Resume before fresh planning.

Predictions if false: the browser reports completion without proof, hides uncertainty, repeats an uncertain effect, silently resumes after reconnect, replaces body identity, or grants action authority using a retained image.

Design: separate new browser runtime, HTTP server and HTML from the existing local operator. Reuse BodyClient and BodyService without changing core guards. An owned loopback diagnostic link retains its exact endpoint and provides disconnect, bounded delay, dropped reply and duplicate controls. The browser host uses TCP-only public observations/results, durable queue and pending-stage records, exact identity/source pins and the existing actual Codex image policy. Restart is paused; recovery is read-only and explicit.

Primary metric: all required product transitions pass in a real browser: enqueue two jobs, show a lost dispatch reply as uncertain, show a disconnected link, refuse receipt recovery while disconnected, reconnect without sending, check the exact receipt, explicitly resume, complete both jobs with measurement and contact reset evidence, and reload without replay or loss of completed history.

Secondary checks: deterministic real-socket cases cover uncertain start/proposal/dispatch, queue-stage restart recovery, duplicate and delayed dispatches, connection identity, source changes, pause cancellation and cached-image integrity. The frozen actual-model trial is scored separately from native snapshots, SQLite and transport/model receipts. Fake planners are conformance evidence only.

Guardrails: no direct native calls from the browser host, no teleport, no private pose in model inputs, no uncertain retries, no automatic resume on reconnect or receipt lookup, no source edits during the measured model trial, and no changes to the existing body/core guard files. Lost receipt without proof remains blocked. Already admitted bounded motion may finish after disconnect or pause. Preserve failed attempts.

Decision rule: adopt and show the network browser product only if conformance checks and the independently scored frozen browser/model trial pass. Otherwise retain the prior idle local product and report the failed boundary.

Scope: same-Mac loopback simulation; remote authentication, hardware and emergency stopping remain outside this experiment.

## Amendment · 2026-10-11 17:27

Host admission is the durable checked stage write, before handing the exact command to BodyClient. Pause/Disconnect prevent later host admissions; an admitted request may reach the body after the control returns. The body retains its separate lease/freshness/effect checks. Qualification must not claim that Pause interrupts this in-flight request. Add a control-boundary check: pause before admission yields no command; pause after admission permits only that command to settle and admits no successor.
