# CDP transport command deadline and cancellation

## CTD1 · prediction · 2026-10-31 12:00
Question: does a command deadline bound socket backpressure as well as reply waiting?
Hypothesis: the current transport starts its timer after WebSocket send completes, so a blocked send outlives its command timeout; cancellation also retains the pending command. One deadline around sending and waiting, with terminal pending-future cleanup and retirement after an interrupted send, bounds both phases without making an uncertain send retryable.
Alternatives: WebSocket sending already imposes the requested command deadline, or the reader removes cancelled pending entries before connection close.
Test: deterministic socket doubles block send under an external watchdog, spend part of the shared budget sending, and cancel commands during sending or reply waiting. Assert timeout classification, no resend, pending cleanup and refusal of further commands after an interrupted send. Rerun existing CDP effector tests including real headless Chrome.
Predicts: before the fix the blocked-send watchdog and cancellation cleanup assertions fail; after it every command consumes one total budget, timeout during sending remains CdpUnknownOutcome, cancellation is preserved, and a retired connection sends no further command.
Against: the unchanged transport already satisfies those checks; the fix retries input, reports an uncertain send as not sent, leaks pending commands, or breaks correlated replies and normal Chrome observation.
Refs: https://github.com/Tom-R-Main/Footwork/pull/16#discussion_r2483370893; python/jevdual/effectors/cdp/transport.py; docs/notebook/2026-10-31-light-cdp-read.md

## CTD2 · prediction · 2026-10-31 12:03
Hypothesis: checking a WebSocket URL by prefix accepts a userinfo authority whose actual host is external. Parsed scheme, host, credentials, port and browser-path checks reject these URLs before a connection opens.
Test: a no-network connect sentinel checks loopback-looking userinfo URLs, missing/invalid ports, non-browser paths, query strings and remote hosts; a valid loopback browser URL reaches the sentinel once.
Predicts: only the valid credential-free loopback browser URL reaches connect; every invalid URL raises CdpClosed before the sentinel.
Against: any invalid URL reaches connect or the valid loopback endpoint is refused.
Refs: python/jevdual/effectors/cdp/transport.py CdpConnection.open; https://github.com/Tom-R-Main/Footwork/pull/16
