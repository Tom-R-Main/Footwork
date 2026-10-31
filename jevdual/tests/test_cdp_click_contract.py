"""Bounded native-button admission, dispatch classification and connection-local no-replay."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from jevdual.browser_driver import BrowserBridge
from jevdual.effectors.base import BrowserReply
from jevdual.effectors.cdp.click import ACTIVATE, MARK_DOCUMENT, ROUTE, button_targets
from jevdual.effectors.cdp.operations import CdpBrowserOperations, RefBinding
from jevdual.effectors.cdp.transport import CdpClosed, CdpError, CdpUnknownOutcome


def document(*, text="Continue", attrs=None, children=None, ancestors=None):
    button = {"nodeType": 1, "nodeName": "BUTTON", "backendNodeId": 10,
              "attributes": [k for pair in (attrs or {"id": "go", "type": "button"}).items() for k in pair],
              "children": children if children is not None else [{"nodeType": 3, "nodeName": "#text", "nodeValue": text}]}
    root = button
    for tag, attributes in reversed(ancestors or [("HTML", {}), ("BODY", {})]):
        root = {"nodeType": 1, "nodeName": tag, "attributes": [k for pair in attributes.items() for k in pair],
                "children": [root]}
    return {"root": {"nodeType": 9, "nodeName": "#document", "children": [root]}}


def target(doc=None, name="Continue"):
    return button_targets(doc or document(), [{"ref": "s:1", "name": name, "role": "button", "actions": ["click"]}],
                          {"s:1": 10})


def test_button_target_keeps_complete_attributes_text_and_ancestor_identity():
    got = target(document(attrs={"type": "button", "data-record": "customer-7", "id": "go"}))
    assert got[10].argument() == {
        "tag": "button", "attrs": [["data-record", "customer-7"], ["id", "go"], ["type", "button"]],
        "text": "Continue", "ancestors": [{"tag": "html", "attrs": []}, {"tag": "body", "attrs": []}],
    }


@pytest.mark.parametrize("doc,name", [
    (document(attrs={"type": "submit"}), "Continue"),
    (document(attrs={"type": "button", "aria-labelledby": "outside"}), "Continue"),
    (document(attrs={"type": "button", "role": "button"}), "Continue"),
    (document(attrs={"type": "button", "form": "elsewhere"}), "Continue"),
    (document(attrs={"type": "button", "popovertarget": "outside"}), "Continue"),
    (document(ancestors=[("HTML", {}), ("BODY", {}), ("FORM", {})]), "Continue"),
    (document(children=[{"nodeType": 1, "nodeName": "SPAN", "children": []}]), "Continue"),
    (document(text="Continue"), "Delete"),
    (document(text="A" * 121), "A" * 121),
    (document(text="Con\u200btinue"), "Con tinue"),
    (document(attrs={"type": "button", "data-large": "x" * 8192}), "Continue"),
])
def test_unsupported_or_unrepresentable_button_is_not_admitted(doc, name):
    assert target(doc, name) == {}


def test_aria_label_is_admitted_only_when_the_offered_name_matches():
    doc = document(text="Icon", attrs={"type": "button", "aria-label": "Continue"})
    assert 10 in target(doc)
    assert not target(doc, "Delete")


class Connection:
    def __init__(self, activation=None):
        self.activation = {"result": {"value": {"status": "invoked"}}} if activation is None else activation
        self.sent = []
        self.entered = asyncio.Event()
        self.release = None
        self.resolve_error = None

    async def send(self, method, params=None, **kwargs):
        self.sent.append((method, params, kwargs))
        if method == "Target.getTargets":
            return {"targetInfos": [{"type": "page", "targetId": "tab", "browserContextId": "ctx"}]}
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "frame", "loaderId": "loader"}}}
        if method == "DOM.describeNode":
            return {"node": {"backendNodeId": 10}}
        if method == "DOM.resolveNode":
            if self.resolve_error:
                raise self.resolve_error
            return {"object": {"objectId": "exact-object", "subtype": "node"}}
        if method == "Runtime.callFunctionOn":
            if params.get("functionDeclaration") == MARK_DOCUMENT:
                return {"result": {"value": {"status": "document_marked", "token": params["arguments"][1]["value"]}}}
            self.entered.set()
            if self.release:
                await self.release.wait()
            if isinstance(self.activation, BaseException):
                raise self.activation
            return self.activation
        return {}


def operations(conn):
    chrome = SimpleNamespace(pid=42, incarnation=7.0, alive=lambda: True)
    ops = CdpBrowserOperations(chrome, conn)
    ops._contexts["tab"] = "ctx"
    ops._sessions["tab"] = "session"
    admit(ops)
    return ops


def admit(ops):
    ops._refs["s:1"] = RefBinding(7.0, "ctx", "tab", "session", "frame", "loader", 10, 99,
                                 target()[10], "observed-document-token")


async def click(ops, **kwargs):
    return await ops.click(target_id=ops.browser_id, tab_id="tab", ref="s:1", input_route=kwargs.get("route", "dom_event"))


def activation_count(conn):
    return sum(name == "Runtime.callFunctionOn" and params.get("functionDeclaration") == ACTIVATE
               for name, params, _ in conn.sent)


def test_native_activation_consumes_refs_and_resolves_only_into_the_observed_world():
    async def run():
        conn = Connection()
        ops = operations(conn)
        reply = await click(ops)
        assert reply.route == ROUTE and reply.status == "ok" and reply.dispatched is True
        assert not ops._refs and not ops._click_unknown
        assert next(p for m, p, _ in conn.sent if m == "DOM.resolveNode") == {
            "backendNodeId": 10, "executionContextId": 99,
        }
        invocation = next(p for m, p, _ in conn.sent if m == "Runtime.callFunctionOn")
        assert invocation["arguments"][1:] == [{"value": ops._document_key}, {"value": "observed-document-token"}]
        again = await click(ops)
        assert again.refusal.code == "stale_ref" and again.dispatched is False
        assert activation_count(conn) == 1
        assert conn.sent[-1][0] != "Input.dispatchMouseEvent"

    asyncio.run(run())


def test_a_ref_without_an_observation_document_token_cannot_activate():
    from dataclasses import replace

    async def run():
        conn = Connection()
        ops = operations(conn)
        ops._refs["s:1"] = replace(ops._refs["s:1"], document_token=None)
        reply = await click(ops)
        assert reply.dispatched is False and reply.refusal.code == "document_unavailable"
        assert activation_count(conn) == 0
        assert not any(m == "DOM.resolveNode" for m, _, _ in conn.sent)

    asyncio.run(run())


def test_observation_marks_one_private_slot_before_reading_nodes_and_replaces_the_token():
    class SnapshotConnection(Connection):
        async def send(self, method, params=None, **kwargs):
            if method == "Page.createIsolatedWorld":
                self.sent.append((method, params, kwargs))
                return {"executionContextId": 99}
            if method == "Accessibility.getFullAXTree":
                self.sent.append((method, params, kwargs))
                return {"nodes": []}
            if method == "DOM.getDocument":
                self.sent.append((method, params, kwargs))
                return document()
            return await super().send(method, params, **kwargs)

    async def run():
        conn = SnapshotConnection()
        ops = operations(conn)
        for _ in range(2):
            reply = await ops.snapshot(target_id=ops.browser_id, tab_id="tab")
            assert reply.status == "ok"
        markers = [p for m, p, _ in conn.sent if m == "Runtime.callFunctionOn"]
        assert len(markers) == 2 and all(p["functionDeclaration"] == MARK_DOCUMENT for p in markers)
        assert markers[0]["arguments"][0] == markers[1]["arguments"][0] == {"value": ops._document_key}
        assert markers[0]["arguments"][1] != markers[1]["arguments"][1]
        methods = [m for m, _, _ in conn.sent]
        assert methods.index("Runtime.callFunctionOn") < methods.index("DOM.getDocument")
        assert activation_count(conn) == 0

    asyncio.run(run())


@pytest.mark.parametrize("marker_reply", [
    {}, {"result": {"value": {"status": "document_marked", "token": "foreign-token"}}},
    {"exceptionDetails": {"text": "not established"}},
])
def test_malformed_marker_setup_keeps_the_observation_unavailable(marker_reply):
    class SnapshotConnection(Connection):
        async def send(self, method, params=None, **kwargs):
            if method == "Page.createIsolatedWorld":
                return {"executionContextId": 99}
            if method == "Runtime.callFunctionOn" and params.get("functionDeclaration") == MARK_DOCUMENT:
                return marker_reply
            return await super().send(method, params, **kwargs)

    async def run():
        conn = SnapshotConnection()
        ops = operations(conn)
        reply = await ops.snapshot(target_id=ops.browser_id, tab_id="tab")
        assert reply.dispatched is False and reply.refusal.code == "document_unavailable"
        assert not ops._refs and activation_count(conn) == 0

    asyncio.run(run())


@pytest.mark.parametrize("result", [
    {"result": {"value": {"status": "other"}}},
    {"result": {"value": {"status": "invoked"}}, "exceptionDetails": {"text": "interrupted"}},
    {"result": []}, [],
    CdpError("Runtime.callFunctionOn", -32000, "context lost"),
    CdpUnknownOutcome("Runtime.callFunctionOn", "ack lost"),
    RuntimeError("unclassified transport loss"),
])
def test_ambiguous_activation_blocks_even_a_new_observation_ref(result):
    async def run():
        conn = Connection(result)
        ops = operations(conn)
        reply = await click(ops)
        assert reply.refusal.delivery == "unknown" and reply.refusal.retryable is False
        assert reply.dispatched is None and ops._click_unknown
        admit(ops)  # even refs from a new read cannot settle the earlier operation
        blocked = await click(ops)
        assert blocked.refusal.code == "browser_delivery_unknown" and blocked.dispatched is False
        assert activation_count(conn) == 1

    asyncio.run(run())


def test_known_pre_activation_refusal_and_closed_socket_are_not_sent():
    async def run(result, code):
        conn = Connection(result)
        ops = operations(conn)
        reply = await click(ops)
        assert reply.refusal.code == code and reply.dispatched is False and not ops._click_unknown

    asyncio.run(run({"result": {"value": {"status": "refused", "code": "button_changed"}}}, "button_changed"))
    asyncio.run(run({"result": {"value": {"status": "refused", "code": "document_changed"}}}, "document_changed"))
    asyncio.run(run(CdpClosed("already closed"), "browser_connection_closed"))


def test_read_only_validation_loss_never_claims_input_was_sent():
    async def run():
        conn = Connection()
        conn.resolve_error = CdpUnknownOutcome("DOM.resolveNode", "reply lost")
        ops = operations(conn)
        reply = await click(ops)
        assert reply.dispatched is False and not ops._click_unknown and activation_count(conn) == 0

    asyncio.run(run())


def test_concurrent_callers_cannot_reuse_the_admitted_ref():
    async def run():
        conn = Connection()
        conn.release = asyncio.Event()
        ops = operations(conn)
        first = asyncio.create_task(click(ops))
        await conn.entered.wait()
        second = asyncio.create_task(click(ops))
        conn.release.set()
        one, two = await asyncio.gather(first, second)
        assert one.status == "ok" and two.refusal.code == "stale_ref"
        assert activation_count(conn) == 1

    asyncio.run(run())


def test_cancellation_keeps_unknown_and_does_not_enable_a_retry():
    async def run():
        conn = Connection()
        conn.release = asyncio.Event()
        ops = operations(conn)
        task = asyncio.create_task(click(ops))
        await conn.entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        admit(ops)
        reply = await click(ops)
        assert reply.refusal.code == "browser_delivery_unknown" and activation_count(conn) == 1

    asyncio.run(run())


def test_cancellation_during_handle_cleanup_cannot_lose_the_successful_activation():
    class CleanupConnection(Connection):
        def __init__(self):
            super().__init__()
            self.cleanup_entered = asyncio.Event()

        async def send(self, method, *args, **kwargs):
            if method == "Runtime.releaseObject":
                self.cleanup_entered.set()
                await asyncio.Event().wait()
            return await super().send(method, *args, **kwargs)

    async def run():
        conn = CleanupConnection()
        ops = operations(conn)
        task = asyncio.create_task(click(ops))
        await conn.cleanup_entered.wait()
        assert activation_count(conn) == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        admit(ops)
        blocked = await click(ops)
        assert blocked.refusal.code == "browser_delivery_unknown"
        assert activation_count(conn) == 1

    asyncio.run(run())


def test_typing_navigation_and_trusted_click_remain_disabled():
    async def run():
        conn = Connection()
        ops = operations(conn)
        replies = [await click(ops, route="trusted"),
                   await ops.type_text(target_id=ops.browser_id, tab_id="tab", ref="s:1", text="x", replace=False),
                   await ops.navigate(target_id=ops.browser_id, tab_id="tab", url="https://example.invalid")]
        assert all(r.refused and r.dispatched is False for r in replies)
        assert activation_count(conn) == 0 and not any(m.startswith("Input.") for m, _, _ in conn.sent)

    asyncio.run(run())


def test_bridge_reports_actual_activation_route_without_promoting_business_completion():
    class Ops:
        async def click(self, **kwargs):
            return BrowserReply("ok", "invoked; business effect unverified", False, route=ROUTE, dispatched=True)

    async def run():
        from jevdual.browser_driver import menu_from_semantic

        bridge = BrowserBridge(None, 42, 0, operations=Ops())
        bridge.target_id, bridge.tab_id = "target", "tab"
        bridge.last = menu_from_semantic({"status": "ok", "snapshot": {"id": "s"}, "refs": [
            {"ref": "s:1", "role": "button", "name": "Continue", "actions": ["click"]},
        ]})
        effect = await bridge.act(bridge.last, "click", 1)
        assert effect.route == ROUTE and effect.effect == "unverifiable" and effect.dispatched is True

    asyncio.run(run())
