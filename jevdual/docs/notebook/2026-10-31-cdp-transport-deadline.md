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

## CTDU1 · update · 2026-10-31 12:03
Resolves: CTD1 = held
Observed: on ee5d010, the blocked-send and shared-budget tests ended at their external watchdog instead of the command deadline; cancellation during either sending or reply waiting retained a pending future. The revised transport passes those checks and existing CDP effector checks, including the real headless Chrome cases. A completed send can receive a late reply after its deadline without another send. An interrupted send retires the connection immediately, marks other pending commands unknown and sends no further commands. Connection-owned cleanup is bounded separately and joined by close; cancelling a close waiter leaves that cleanup owned. Serialization failures create neither pending entries nor a send.
Changes: one asyncio timeout covers send and reply, pending entries are released in finally, and interrupted sends retire the socket rather than reusing uncertain framing. The first revised test expected the socket-close coroutine to have finished at the command deadline; it now checks the immediate retired gate, then explicitly joins cleanup before checking socket closure. This preserves the command budget instead of making cleanup extend it.
Next: parent review and retained PR verification report, then hosted CI on the final head.
Refs: tests/test_cdp_transport_deadline.py; tests/test_cdp_effector.py; https://github.com/Tom-R-Main/Footwork/pull/16

## CTDU2 · update · 2026-10-31 12:03
Resolves: CTD2 = held
Observed: the connect sentinel is reached only by the valid credential-free loopback browser URL. Userinfo, remote host, missing or invalid port, wrong scheme/path, query and fragment cases refuse before connect. Error text does not echo the supplied endpoint.
Changes: endpoint validation parses authority components before importing the WebSocket client. The prior CTD1 discussion anchor was not verified; the canonical review source is PR 16. CTD1 and CTD2 heading times were inadvertently one minute ahead of the observed clock; their committed ordering remains authoritative (680e296 and bbe3965, both before their respective tests).
Next: preserve the absence of raw URL credentials in diagnostics and rerun final-head hosted checks.
Refs: tests/test_cdp_transport_deadline.py; https://github.com/Tom-R-Main/Footwork/pull/16

## CTDS · summary · 2026-10-31 12:03
Established: command backpressure and reply waiting share one deadline; cancellation releases pending custody; an interrupted send is unknown and retires the connection without retry. Endpoint validation uses the parsed authority and supports only the owned loopback browser endpoint shape.
Uncertain: real Chrome tests ran on macOS; Linux and full hosted qualification remain with the parent PR acceptance. These changes do not enable mutations or durable browser authority.
Decision: hand the bounded transport repair to the parent for final-head integration and merge review.
Refs: tests/test_cdp_transport_deadline.py; tests/test_cdp_effector.py
