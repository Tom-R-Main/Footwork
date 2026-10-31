"""Footwork's own CDP browser effector, observation slice (LCD1).

Transport and composition tests need no browser. Tests marked ``browser`` launch a real headless
Chrome into a temporary profile (never the person's or footwork's own profile) and serve the fixture
page from loopback.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from jevdual.browser_driver import BrowserBridge
from jevdual.effectors.cdp import launch as cdp_launch
from jevdual.effectors.cdp.snapshot import compose
from jevdual.effectors.cdp.transport import CdpClosed, CdpConnection, CdpError, CdpUnknownOutcome
from jevdual.posture import ExecutionPolicy

#: methods that change a page; none may be sent in the observation slice
MUTATING = ("Input.", "Runtime.", "DOM.focus", "DOM.setAttributeValue", "DOM.setNodeValue", "Page.navigate",
            "Page.reload", "Target.createTarget", "Target.closeTarget")


# ---- transport, against an in-memory socket


class FakeSocket:
    def __init__(self) -> None:
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.sent: list[dict] = []

    async def send(self, raw):
        self.sent.append(json.loads(raw))

    def reply(self, message) -> None:
        self.inbox.put_nowait(json.dumps(message))

    def drop(self) -> None:
        self.inbox.put_nowait(None)

    def __aiter__(self):
        return self

    async def __anext__(self):
        item = await self.inbox.get()
        if item is None:
            raise StopAsyncIteration
        return item

    async def close(self):
        self.drop()


def test_replies_are_matched_by_id_and_events_reach_listeners():
    async def run():
        ws = FakeSocket()
        conn = CdpConnection(ws)
        events = conn.listen("Page.loadEventFired", session_id="s1")
        first = asyncio.create_task(conn.send("A.one"))
        second = asyncio.create_task(conn.send("B.two", {"x": 1}, session_id="s1"))
        await asyncio.sleep(0)
        ws.reply({"method": "Page.loadEventFired", "sessionId": "s2", "params": {"n": 0}})
        ws.reply({"method": "Page.loadEventFired", "sessionId": "s1", "params": {"n": 1}})
        ws.reply({"id": 2, "result": {"second": True}})
        ws.reply({"id": 1, "result": {"first": True}})
        results = await first, await second
        event = await asyncio.wait_for(events.get(), 1)
        await conn.close()
        return ws.sent, results, event

    sent, results, event = asyncio.run(run())
    assert [m["method"] for m in sent] == ["A.one", "B.two"] and sent[1]["sessionId"] == "s1"
    assert results == ({"first": True}, {"second": True}) and event == {"n": 1}


def test_an_error_reply_is_a_received_refusal():
    async def run():
        ws = FakeSocket()
        conn = CdpConnection(ws)
        task = asyncio.create_task(conn.send("DOM.describeNode"))
        await asyncio.sleep(0)
        ws.reply({"id": 1, "error": {"code": -32000, "message": "No node"}})
        with pytest.raises(CdpError, match="No node"):
            await task
        await conn.close()

    asyncio.run(run())


def test_a_lost_connection_leaves_in_flight_commands_unknown_and_sends_nothing_after():
    async def run():
        ws = FakeSocket()
        conn = CdpConnection(ws)
        task = asyncio.create_task(conn.send("Input.insertText", {"text": "x"}))
        await asyncio.sleep(0)
        ws.drop()
        with pytest.raises(CdpUnknownOutcome) as unknown:
            await task
        assert unknown.value.dispatched is None
        with pytest.raises(CdpClosed) as closed:
            await conn.send("Page.navigate")
        assert closed.value.dispatched is False and [m["method"] for m in ws.sent] == ["Input.insertText"]

    asyncio.run(run())


def test_no_reply_within_the_deadline_is_unknown_not_failed():
    async def run():
        conn = CdpConnection(FakeSocket())
        with pytest.raises(CdpUnknownOutcome, match="no reply"):
            await conn.send("Input.dispatchMouseEvent", timeout=0.05)
        await conn.close()

    asyncio.run(run())


def test_only_a_loopback_endpoint_is_opened():
    with pytest.raises(CdpClosed, match="non-loopback"):
        asyncio.run(CdpConnection.open("ws://10.0.0.5:9222/devtools/browser/x"))


# ---- composition, against recorded-shape replies


def _ax(node_id, role, name=None, *, parent=None, backend=None, value=None, props=(), ignored=False):
    node = {"nodeId": node_id, "ignored": ignored, "role": {"value": role}}
    if name is not None:
        node["name"] = {"value": name}
    if value is not None:
        node["value"] = {"value": value}
    if parent:
        node["parentId"] = parent
    if backend is not None:
        node["backendDOMNodeId"] = backend
    node["properties"] = [{"name": k, "value": {"value": v}} for k, v in props]
    return node


def _dom(*children):
    return {"root": {"backendNodeId": 1, "nodeName": "#document", "children": [
        {"backendNodeId": b, "nodeName": tag, "attributes": [x for kv in attrs.items() for x in kv]}
        for b, tag, attrs in children
    ]}}


def _layout(rows):
    strings = ["block", "visible", "1", "auto", "default"]
    return {"strings": strings, "documents": [{
        "nodes": {"backendNodeId": [b for b, _ in rows]},
        "layout": {"nodeIndex": list(range(len(rows))), "bounds": [r for _, r in rows],
                   "styles": [[0, 1, 2, 3, 4] for _ in rows]},
    }]}


METRICS = {"cssVisualViewport": {"pageX": 0, "pageY": 0, "clientWidth": 1000, "clientHeight": 800}}


def test_composition_withholds_sensitive_values_and_disables_disabled_controls():
    composed = compose(
        snapshot_id="s", url="http://127.0.0.1/x", child_frames=0, metrics=METRICS,
        ax={"nodes": [
            _ax("1", "RootWebArea", "Form"),
            _ax("2", "textbox", "Secret", parent="1", backend=10, value="•••••", props=[("editable", "plaintext")]),
            _ax("3", "textbox", "Card", parent="1", backend=11, value="4111", props=[("editable", "plaintext")]),
            _ax("4", "button", "Later", parent="1", backend=12, props=[("disabled", True)]),
            _ax("5", "button", "Go", parent="1", backend=13),
            _ax("6", "StaticText", "Go", parent="5"),
            _ax("7", "link", "Far", parent="1", backend=14),
        ]},
        document=_dom((10, "INPUT", {"type": "password"}), (11, "INPUT", {"autocomplete": "cc-number"}),
                      (12, "BUTTON", {}), (13, "BUTTON", {}), (14, "A", {"href": "/far"})),
        dom_snapshot=_layout([(10, [0, 0, 10, 10]), (11, [0, 20, 10, 10]), (12, [0, 40, 10, 10]),
                              (13, [0, 60, 10, 10]), (14, [0, 5000, 10, 10])]),
    )
    refs = {r["name"]: r for r in composed.semantic["refs"]}
    assert "value" not in refs["Secret"] and "value" not in refs["Card"]
    assert "Later" not in refs  # no operation, so no ref
    assert refs["Far"]["visibility"] == "offscreen" and refs["Go"]["visibility"] == "in_viewport"
    assert composed.semantic["page"]["title"] == "Form"
    assert composed.semantic["content_refs"] == [{"role": "link", "name": "Far"}]  # "Go" text is redundant
    assert set(composed.backend.values()) == {10, 11, 13, 14}


def test_a_controls_user_agent_internals_never_become_candidates_or_labels():
    """Chrome 156 exposes an input's inner editor (generic, editable) and its text; a password's text is
    one bullet per character. Their DOM nodes sit in a user-agent shadow root outside the DOM index."""
    composed = compose(
        snapshot_id="s", url="u", child_frames=0, metrics=METRICS,
        ax={"nodes": [
            _ax("1", "RootWebArea", "Form"),
            _ax("2", "textbox", "Secret", parent="1", backend=10, value="•••", props=[("editable", "plaintext")]),
            _ax("3", "generic", parent="2", backend=90, props=[("editable", "plaintext")]),
            _ax("4", "StaticText", "•••", parent="3", backend=91),
        ]},
        document=_dom((10, "INPUT", {"type": "password"})),
        dom_snapshot=_layout([(10, [0, 0, 10, 10])]),
    )
    assert [r["name"] for r in composed.semantic["refs"]] == ["Secret"]
    assert "•" not in json.dumps(composed.semantic)


def test_child_frames_make_the_snapshot_incomplete():
    composed = compose(snapshot_id="s", url="u", ax={"nodes": []}, document=_dom(), dom_snapshot={},
                       metrics=METRICS, child_frames=2)
    snap = composed.semantic["snapshot"]
    assert snap["complete"] is False and snap["omitted"]["child_frames"] == 2


@pytest.mark.parametrize("autocomplete", [
    "section-billing billing cc-number", "shipping one-time-code", "section-X CC-CSC",
])
def test_compound_sensitive_autocomplete_never_exposes_the_field_value(autocomplete):
    secret = "9876543210123456"
    composed = compose(
        snapshot_id="s", url="u", child_frames=0, metrics=METRICS,
        ax={"nodes": [_ax("1", "textbox", "Protected field", backend=10, value=secret)]},
        document=_dom((10, "INPUT", {"autocomplete": autocomplete})),
        dom_snapshot=_layout([(10, [0, 0, 10, 10])]),
    )
    assert secret not in json.dumps(composed.semantic)


def test_omitted_custom_controls_prevent_a_complete_observation_claim():
    composed = compose(snapshot_id="s", url="u", ax={"nodes": []}, document=_dom(), dom_snapshot={},
                       metrics=METRICS, child_frames=0)
    assert composed.semantic["snapshot"]["omitted"]["custom_controls_unobserved"]
    assert composed.semantic["snapshot"]["complete"] is False


# ---- a real headless Chrome


def _chrome() -> str | None:
    override = os.environ.get("FOOTWORK_CHROME_EXECUTABLE")
    candidates = [override] if override else [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/opt/google/chrome/chrome",
        *filter(None, (shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser"))),
    ]
    return next((c for c in candidates if c and Path(c).is_file()), None)


FIXTURE = b"""<!doctype html><html><head><title>Ticket</title></head><body>
<h1>New ticket</h1>
<button id=go>Continue</button>
<label>Name <input id=name value="Ada"></label>
<label>Note <input id=note></label>
<label>Secret <input id=secret type=password value="hunter2"></label>
<label><input id=agree type=checkbox checked> Agree</label>
<button disabled>Later</button>
<div style="height:4000px"></div>
<a href="/far">Far link</a>
<iframe srcdoc="<button>Inner</button>"></iframe>
</body></html>"""


@pytest.fixture
def fixture_url():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(FIXTURE)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/ticket"
    server.shutdown()


@pytest.fixture
def chrome(tmp_path):
    executable = _chrome()
    if executable is None:
        pytest.skip("no Chrome executable")
    owned = cdp_launch.launch(executable, tmp_path / "profile")
    yield owned
    cdp_launch.stop(owned)


async def _goto(ops, url):
    """Test setup only: load the fixture through a separate connection, outside the effector."""
    conn = await CdpConnection.open(ops.chrome.browser_url)
    try:
        page = next(t for t in (await conn.send("Target.getTargets"))["targetInfos"] if t["type"] == "page")
        session = (await conn.send("Target.attachToTarget", {"targetId": page["targetId"], "flatten": True}))[
            "sessionId"]
        await conn.send("Page.enable", session_id=session)
        loaded = conn.listen("Page.loadEventFired", session_id=session)
        await conn.send("Page.navigate", {"url": url}, session_id=session)
        await asyncio.wait_for(loaded.get(), 10)
        return conn, session
    except BaseException:
        await conn.close()
        raise


@pytest.mark.browser
def test_the_owned_browser_is_observed_as_the_fixture_declares(chrome, fixture_url):
    from jevdual.effectors.cdp.operations import CdpBrowserOperations

    async def run():
        ops = await CdpBrowserOperations.connect(chrome)
        setup, _ = await _goto(ops, fixture_url)
        try:
            bridge = BrowserBridge(None, chrome.pid, 0, operations=ops, policy=ExecutionPolicy("exclusive_desktop"))
            await bridge.attach(expect_url=fixture_url)
            nm = await bridge.observe()
            return ops, bridge, nm
        finally:
            await setup.close()

    ops, bridge, nm = asyncio.run(run())
    got = [(c.label, c.role, c.operations, c.value, c.checked, c.offscreen) for c in nm.menu.candidates]
    assert got == [
        ("Continue", "button", ("click",), None, None, False),
        ("Name", "textbox", ("type",), "Ada", None, False),
        ("Note", "textbox", ("type",), None, None, False),
        ("Secret", "textbox", ("type",), None, None, False),
        ("Agree", "checkbox", ("click",), None, True, False),
        ("Far link", "link", ("click",), None, None, True),
    ]
    shown = json.dumps([nm.menu.page_text, [(c.label, c.value) for c in nm.menu.candidates], nm.values])
    assert "hunter2" not in shown and "\u2022" not in shown  # neither the password nor its length
    assert nm.page_title == "Ticket" and nm.page_url == fixture_url
    assert nm.elements_complete is False and nm.menu.omitted.get("child_frames") == 1
    assert bridge.binding.persistent_target_identity is False
    assert not [m for m in ops.conn.sent if m.startswith(MUTATING)]


@pytest.mark.browser
def test_actions_refuse_before_dispatch_and_a_reload_invalidates_refs(chrome, fixture_url):
    from jevdual.effectors.cdp.operations import CdpBrowserOperations

    async def run():
        ops = await CdpBrowserOperations.connect(chrome)
        setup, session = await _goto(ops, fixture_url)
        try:
            bridge = BrowserBridge(None, chrome.pid, 0, operations=ops, policy=ExecutionPolicy("exclusive_desktop"))
            await bridge.attach()
            nm = await bridge.observe()
            name = next(c.id for c in nm.menu.candidates if c.label == "Name")
            go = next(c.id for c in nm.menu.candidates if c.label == "Continue")
            effects = [await bridge.act(nm, "click", go)]
            nm = await bridge.observe()
            effects.append(await bridge.act(nm, "type", name, "Grace"))
            effects.append(await bridge.navigate("http://127.0.0.1:9/elsewhere"))
            nm = await bridge.observe()
            stale = nm.refs[go]
            loaded = setup.listen("Page.loadEventFired", session_id=session)
            await setup.send("Page.reload", session_id=session)  # test setup, outside the effector
            await asyncio.wait_for(loaded.get(), 10)
            after = await ops.validate(target_id=bridge.target_id, tab_id=bridge.tab_id, ref=stale)
            return ops, effects, after
        finally:
            await setup.close()

    ops, effects, after = asyncio.run(run())
    assert [(e.effect, e.error_code, e.dispatched, e.delivery) for e in effects] == [
        ("refused", "browser_mutation_unqualified", False, "not_sent")
    ] * 3
    assert after.refusal.code == "document_changed" and after.dispatched is False
    assert not [m for m in ops.conn.sent if m.startswith(MUTATING)]


@pytest.mark.browser
def test_a_stale_port_file_or_a_foreign_endpoint_is_refused(chrome, tmp_path):
    from jevdual.effectors.cdp.operations import CdpBrowserOperations

    # a DevToolsActivePort older than the launch never names the endpoint
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "DevToolsActivePort").write_text("1\n/devtools/browser/old\n")
    os.utime(stale / "DevToolsActivePort", (1, 1))
    assert cdp_launch._read_port_file(stale / "DevToolsActivePort", not_before=2.0) is None

    # an endpoint whose browser process is not the launched pid
    from dataclasses import replace

    impostor = replace(chrome, pid=chrome.pid + 1)
    with pytest.raises(cdp_launch.LaunchRefused) as refused:
        asyncio.run(CdpBrowserOperations.connect(impostor))
    assert refused.value.code == "browser_identity_mismatch" and refused.value.dispatched is False


def test_the_cdp_package_imports_no_third_party_module_until_a_connection_opens():
    import subprocess
    import sys

    code = ("import sys; import jevdual.effectors.cdp.operations, jevdual.effectors.cdp.launch; "
            "print(sorted(m for m in ('websockets', 'cua_driver', 'browser_use') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "python")})
    assert out.stdout.strip() == "[]"


def test_only_an_effector_that_refused_before_sending_reports_not_sent():
    from jevdual.effectors import BrowserReply
    from jevdual.effectors.cdp.operations import _refused

    class Operations:
        def __init__(self, click):
            self.click_reply = click

        async def prepare(self, **_):
            return BrowserReply("ok", "", False, {})

        async def bind(self, **_):
            return BrowserReply("ok", "", False, {"status": "ok", "target_id": "b",
                                                  "tabs": [{"tab_id": "t", "active": True, "url": "u"}]})

        async def snapshot(self, **_):
            return BrowserReply("ok", "", False, {"status": "ok", "page": {"url": "u"}, "snapshot": {"id": "s"},
                                                  "refs": [{"ref": "s:1", "role": "button", "name": "Go",
                                                            "actions": ["click"]}]})

        async def click(self, **_):
            return self.click_reply

    async def act(reply):
        b = BrowserBridge(None, 1, 0, operations=Operations(reply))
        await b.attach()
        return await b.act(await b.observe(), "click", 1)

    before = asyncio.run(act(_refused("browser_mutation_unqualified", "not yet")))
    after = asyncio.run(act(_refused("browser_input_trust_unavailable", "acknowledged", dispatched=None)))
    assert (before.effect, before.dispatched, before.delivery) == ("refused", False, "not_sent")
    assert (after.effect, after.dispatched, after.delivery) == ("refused", True, None)
