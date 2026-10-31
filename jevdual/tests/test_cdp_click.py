"""Native-button activation qualification against an independent loopback ingress ledger.

Only disposable profiles and fixture data are used. The setup connection is deliberately separate
from the product connection: it loads fixtures, forces stale state and reads fixture promises; the
HTTP server's saved records, not driver acknowledgements, establish the requested effect.
"""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from jevdual.browser_driver import BrowserBridge, chrome_executable
from jevdual.effectors.cdp import launch
from jevdual.effectors.cdp.operations import CdpBrowserOperations
from jevdual.effectors.cdp.transport import CdpConnection, CdpUnknownOutcome
from jevdual.posture import ExecutionPolicy

HTML = b'''<!doctype html><title>Activation fixture</title>
<script>
window.pending = [];
window.pointerCount = 0;
function record(name) {
  window.pending.push(fetch('/record', {method:'POST', body:name}).then(r=>r.text()));
}
</script>
<button type="button" id="intended" data-record-id="alpha" onclick="record('intended')">Commit fixture</button>
<button type="button" id="sentinel" onclick="record('sentinel')">Sentinel</button>
<button type="button" id="pointer" onpointerdown="window.pointerCount++; record('pointer')">Pointer only</button>
<label>Name <input id="name" value="Ada"></label>
'''


@pytest.fixture
def ingress(tmp_path):
    saved = tmp_path / "ingress.jsonl"
    saved.write_text("")
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML)

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode()
            with lock, saved.open("a") as stream:
                stream.write(json.dumps({"name": body}) + "\n")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"recorded")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
    thread.start()

    def records():
        with lock:
            return [json.loads(line)["name"] for line in saved.read_text().splitlines()]

    yield f"http://127.0.0.1:{server.server_address[1]}/fixture", records
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def owned(tmp_path):
    try:
        executable = chrome_executable()
    except RuntimeError as exc:
        pytest.skip(str(exc))
    chrome = launch.launch(executable, tmp_path / "profile")
    try:
        yield chrome
    finally:
        launch.stop(chrome)


async def evaluate(setup, session, expression, *, await_promise=False):
    reply = await setup.send("Runtime.evaluate", {
        "expression": expression, "returnByValue": True, "awaitPromise": await_promise,
    }, session_id=session)
    assert not reply.get("exceptionDetails"), reply
    return reply["result"].get("value")


class Fixture:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.setup.close()
        await self.ops.close()

    @classmethod
    async def open(cls, chrome, url):
        self = cls()
        self.ops = await CdpBrowserOperations.connect(chrome)
        self.setup = await CdpConnection.open(chrome.browser_url)
        try:
            page = next(t for t in (await self.setup.send("Target.getTargets"))["targetInfos"]
                        if t["type"] == "page")
            self.session = (await self.setup.send("Target.attachToTarget", {
                "targetId": page["targetId"], "flatten": True,
            }))["sessionId"]
            await self.setup.send("Page.enable", session_id=self.session)
            loaded = self.setup.listen("Page.loadEventFired", session_id=self.session)
            await self.setup.send("Page.navigate", {"url": url}, session_id=self.session)
            await asyncio.wait_for(loaded.get(), 5)
            self.setup.unlisten(loaded)
            self.bridge = BrowserBridge(None, chrome.pid, 0, operations=self.ops,
                                        policy=ExecutionPolicy("background_only"))
            await self.bridge.attach()
            return self
        except BaseException:
            await self.setup.close()
            await self.ops.close()
            raise

    async def eval(self, expression, **kwargs):
        return await evaluate(self.setup, self.session, expression, **kwargs)

    async def settle(self):
        await self.eval("Promise.all(window.pending)", await_promise=True)

    async def observe(self, label="Commit fixture"):
        nm = await self.bridge.observe()
        candidate = next(c for c in nm.menu.candidates if c.label == label)
        return nm, candidate.id

    async def reload(self):
        loaded = self.setup.listen("Page.loadEventFired", session_id=self.session)
        try:
            await self.setup.send("Page.reload", session_id=self.session)
            await asyncio.wait_for(loaded.get(), 5)
        finally:
            self.setup.unlisten(loaded)


def activation_call(method, params):
    from jevdual.effectors.cdp.click import ACTIVATE

    return method == "Runtime.callFunctionOn" and (params or {}).get("functionDeclaration") == ACTIVATE


@pytest.mark.browser
def test_observation_marker_has_no_fixture_effect(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            await f.observe()
            await f.settle()
            assert ingress[1]() == []
            assert await f.eval("document.getElementById('name').value") == "Ada"
            assert not [m for m in f.ops.conn.sent if m.startswith("Input.")]
    asyncio.run(run())


@pytest.mark.browser
def test_native_button_activation_records_exactly_one_independent_ingress(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            effect = await f.bridge.act(nm, "click", id)
            await f.settle()
            assert effect.effect == "unverifiable" and effect.dispatched is True
            assert effect.route == "dom_event_native_button"
            assert ingress[1]() == ["intended"]
            assert not [m for m in f.ops.conn.sent if m.startswith("Input.")]
    asyncio.run(run())


@pytest.mark.browser
@pytest.mark.parametrize("mutation", [
    "intended.textContent = 'Delete fixture'",
    "intended.setAttribute('data-record-id', 'other-record')",
    "intended.setAttribute('type', 'submit')",
    "intended.disabled = true",
    "intended.setAttribute('aria-label', 'Delete fixture')",
    "document.body.setAttribute('data-customer-id', 'other')",
    "let css=document.createElement('style'); css.textContent='#intended::before{content:\"Delete \"}'; document.head.append(css)",
    "intended.replaceWith(intended.cloneNode(true))",
    "document.body.setAttribute('inert', '')",
    "let fieldset=document.createElement('fieldset'); fieldset.disabled=true; intended.before(fieldset); fieldset.append(intended)",
    "let form=document.createElement('form'); intended.before(form); form.append(intended)",
])
def test_changed_subject_refuses_without_any_fixture_ingress(owned, ingress, mutation):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            await f.eval("const intended=document.getElementById('intended'); " + mutation)
            effect = await f.bridge.act(nm, "click", id)
            await f.settle()
            assert effect.effect == "refused" and effect.dispatched is False
            assert ingress[1]() == []
    asyncio.run(run())


@pytest.mark.browser
@pytest.mark.parametrize("mutation,label", [
    ("intended.textContent='A'.repeat(121)+' Delete fixture'", "A" * 120),
    ("intended.setAttribute('role','button')", "Commit fixture"),
    ("intended.innerHTML='<span>Commit fixture</span>'", "Commit fixture"),
    ("let name=document.createElement('span'); name.id='external'; name.textContent='Commit fixture'; document.body.append(name); intended.setAttribute('aria-labelledby','external')", "Commit fixture"),
    ("intended.setAttribute('data-payload','x'.repeat(9000))", "Commit fixture"),
])
def test_unsupported_or_incompletely_represented_button_names_refuse(owned, ingress, mutation, label):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            await f.eval("const intended=document.getElementById('intended'); " + mutation)
            nm, id = await f.observe(label)
            effect = await f.bridge.act(nm, "click", id)
            await f.settle()
            assert effect.effect == "refused" and effect.dispatched is False
            assert ingress[1]() == []
    asyncio.run(run())


@pytest.mark.browser
def test_page_method_and_getter_overrides_cannot_redirect_activation(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            await f.eval("""HTMLElement.prototype.click=function(){record('sentinel')};
                Element.prototype.getAttribute=function(){return 'overridden'};
                Object.defineProperty(Node.prototype, 'textContent', {get(){return 'overridden'}});
                document.getElementById('intended').click=function(){record('sentinel')};""")
            effect = await f.bridge.act(nm, "click", id)
            await f.settle()
            assert effect.effect == "unverifiable" and ingress[1]() == ["intended"]
    asyncio.run(run())


@pytest.mark.browser
def test_pointerdown_only_app_does_not_gain_a_business_completion_claim(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe("Pointer only")
            effect = await f.bridge.act(nm, "click", id)
            await f.settle()
            assert effect.effect == "unverifiable" and effect.route == "dom_event_native_button"
            assert await f.eval("window.pointerCount") == 0 and ingress[1]() == []
    asyncio.run(run())


@pytest.mark.browser
@pytest.mark.parametrize("late", [False, True])
def test_same_url_reload_never_uses_a_new_document_context(owned, ingress, late):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            original = f.ops.conn.send
            if late:
                async def send(method, params=None, **kwargs):
                    if method == "DOM.resolveNode":
                        await f.reload()
                    return await original(method, params, **kwargs)
                f.ops.conn.send = send
            else:
                await f.reload()
            effect = await f.bridge.act(nm, "click", id)
            await f.settle()
            assert effect.effect == "refused" and effect.dispatched is False
            assert ingress[1]() == []
    asyncio.run(run())


@pytest.mark.browser
def test_numeric_handle_alias_cannot_adopt_an_identical_new_document_button(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            original = f.ops.conn.send
            substituted = False

            async def send(method, params=None, **kwargs):
                nonlocal substituted
                if method == "DOM.resolveNode" and not substituted:
                    substituted = True
                    await f.reload()
                    frame = (await f.setup.send("Page.getFrameTree", session_id=f.session))["frameTree"]["frame"]
                    world = await f.setup.send("Page.createIsolatedWorld", {
                        "frameId": frame["id"], "worldName": "fixture-unmarked-replacement",
                    }, session_id=f.session)
                    root = (await f.setup.send("DOM.getDocument", session_id=f.session))["root"]["nodeId"]
                    node = (await f.setup.send("DOM.querySelector", {
                        "nodeId": root, "selector": "#intended",
                    }, session_id=f.session))["nodeId"]
                    backend = (await f.setup.send("DOM.describeNode", {
                        "nodeId": node,
                    }, session_id=f.session))["node"]["backendNodeId"]
                    # Simulate numeric ID aliasing by resolving the new subject while the effector
                    # still holds the old binding. This is a real Chrome object in a new realm.
                    return await original(method, {
                        "backendNodeId": backend, "executionContextId": world["executionContextId"],
                    }, **kwargs)
                return await original(method, params, **kwargs)

            f.ops.conn.send = send
            effect = await f.bridge.act(nm, "click", id)
            await f.settle()
            assert substituted, "the numeric-handle alias control was not exercised"
            assert ingress[1]() == [], "a new document inherited the old observation's activation"
            assert effect.effect == "refused" and effect.dispatched is False
    asyncio.run(run())


@pytest.mark.browser
def test_document_open_root_replacement_cannot_reuse_an_old_observation(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            await f.eval(f"""(() => {{
                const original = document.getElementById('intended');
                document.open(); document.write({json.dumps(HTML.decode())}); document.close();
                document.getElementById('intended').replaceWith(original);
            }})()""")
            effect = await f.bridge.act(nm, "click", id)
            await f.settle()
            assert effect.effect == "refused" and effect.dispatched is False
            assert ingress[1]() == []
    asyncio.run(run())


@pytest.mark.browser
def test_closed_pinned_tab_does_not_activate_a_live_sentinel_tab(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            sentinel = (await f.setup.send("Target.createTarget", {"url": ingress[0]}))["targetId"]
            await f.setup.send("Target.closeTarget", {"targetId": f.bridge.tab_id})
            effect = await f.bridge.act(nm, "click", id)
            assert effect.effect == "refused" and effect.dispatched is False
            pages = (await f.setup.send("Target.getTargets"))["targetInfos"]
            assert any(p["targetId"] == sentinel for p in pages) and ingress[1]() == []
    asyncio.run(run())


@pytest.mark.browser
def test_reobservation_and_foreign_connection_reject_old_refs(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            ref = nm.refs[id]
            await f.bridge.observe()
            old = await f.ops.click(target_id=f.bridge.target_id, tab_id=f.bridge.tab_id,
                                    ref=ref, input_route="dom_event")
            other = await CdpBrowserOperations.connect(owned)
            try:
                foreign = await other.click(target_id=f.bridge.target_id, tab_id=f.bridge.tab_id,
                                            ref=ref, input_route="dom_event")
            finally:
                await other.close()
            assert old.dispatched is False and foreign.dispatched is False and ingress[1]() == []
    asyncio.run(run())


@pytest.mark.browser
def test_concurrent_calls_with_one_ref_dispatch_once(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            args = {"target_id": f.bridge.target_id, "tab_id": f.bridge.tab_id,
                    "ref": nm.refs[id], "input_route": "dom_event"}
            replies = await asyncio.gather(f.ops.click(**args), f.ops.click(**args))
            await f.settle()
            assert sorted(r.status for r in replies) == ["ok", "refused"]
            assert ingress[1]() == ["intended"]
    asyncio.run(run())


@pytest.mark.browser
@pytest.mark.parametrize("cancel", [False, True])
def test_lost_ack_or_cancellation_after_ingress_blocks_even_a_fresh_ref(owned, ingress, cancel):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            original = f.ops.conn.send
            arrived = asyncio.Event()

            async def send(method, params=None, **kwargs):
                result = await original(method, params, **kwargs)
                if activation_call(method, params):
                    await f.settle()
                    assert ingress[1]() == ["intended"]
                    if cancel:
                        arrived.set()
                        await asyncio.Event().wait()
                    raise CdpUnknownOutcome(method, "fixture dropped acknowledgement after ingress")
                return result

            f.ops.conn.send = send
            if cancel:
                pending = asyncio.create_task(f.bridge.act(nm, "click", id))
                await asyncio.wait_for(arrived.wait(), 5)
                pending.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await pending
            else:
                effect = await f.bridge.act(nm, "click", id)
                assert effect.dispatched is True and effect.delivery == "unknown" and effect.retryable is False
            f.ops.conn.send = original
            after, next_id = await f.observe()
            blocked = await f.bridge.act(after, "click", next_id)
            await f.settle()
            assert blocked.effect == "refused" and blocked.dispatched is False
            assert ingress[1]() == ["intended"]
    asyncio.run(run())


@pytest.mark.browser
def test_typing_trusted_click_and_navigation_stay_disabled(owned, ingress):
    async def run():
        async with await Fixture.open(owned, ingress[0]) as f:
            nm, id = await f.observe()
            trusted = await f.bridge.act(nm, "click", id, route="trusted")
            nm, id = await f.observe("Name")
            typed = await f.bridge.act(nm, "append", id, " changed")
            nav = await f.bridge.navigate(ingress[0] + "?other")
            assert all(e.effect == "refused" and e.dispatched is False for e in (trusted, typed, nav))
            assert await f.eval("document.getElementById('name').value") == "Ada"
            assert ingress[1]() == [] and not [m for m in f.ops.conn.sent if m.startswith("Input.")]
    asyncio.run(run())
