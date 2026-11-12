# Driver release: connected-node click with HelpTag

Option 1 from the BH15 decision (docs/notebook/2026-11-11-browser-holder.md#bh15): one driver release
that carries the HelpTag exclusion (today an optional overlay, cleanup2.focus1.helptag1) and a new
patch that refuses a page-route click on a node no longer in its document, landing before the panel
or DemoGeek migration. Branch claude/driver-isconnected-20261111 from main 6e8bb5e. Not upstreamed.

## DC1 · prediction · 2026-11-11 23:55
Question: does a liveness read before the synthetic click close the detached-node gap that BH13 found, without changing a click on a live node?
Hypothesis: browser_click's dom_event branch (cua-driver-core browser/tools.rs) resolves the ref's backend node with DOM.resolveNode, which still yields an object for a node the page has removed, then runs DOM_EVENT_CLICK_SEQUENCE on it. Reading this.isConnected on that object first, and refusing browser_ref_stale unless it is true, stops every event for a removed node; a live node reads true and proceeds as before.
Alternatives: (a) the liveness read changes the mock's or a real page's click accounting, so existing dom_event tests or live receipts change; (b) a removed node that is reattached elsewhere reads connected, so a moved node is still clicked (accepted: it is in the document); (c) the read cannot run while a dialog blocks the page, so a click that should proceed now refuses.
Test: in the helptag1 source, a new mock-CDP test for a removed node (red before the patch, green after); the existing dom_event tests unchanged; then the rebuilt driver through scripts/probe_document_binding.py on an isolated profile, port 9466.
Predicts: Rust: the new test fails before the patch (the click sequence is dispatched) and passes after (browser_ref_stale, no pointer sequence, nothing dispatched); every existing browser test passes. Live: the reload case still refuses browser_ref_stale; the re-render case's late click now refuses browser_ref_stale and the page logs no handler activation for the removed button; both fresh clicks land once.
Against: the re-render's late click running any handler; a fresh click refused; any existing browser test failing.
Refs: docs/notebook/2026-11-11-browser-holder.md#bh13; scripts/probe_document_binding.py
