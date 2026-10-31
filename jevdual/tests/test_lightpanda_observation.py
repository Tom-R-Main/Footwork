"""DOM-only observation schema and refusal controls, modeled from Lightpanda's CDP writers.

These unit models are not engine/runtime qualification. Real-engine tests belong
to the installed command gate. Source: Node.zig Writer, target.zig create/attach,
and page.zig FrameTreeWriter at Lightpanda 49d717 (unchanged used handlers at56980af).
"""

from __future__ import annotations

import asyncio
import copy
import json

import pytest
from jevdual.effectors.cdp.transport import CdpUnknownOutcome
from jevdual.effectors.lightpanda.observation import (
    MAX_DEPTH,
    MAX_NODES,
    MAX_OUTPUT_BYTES,
    MAX_RECORDS,
    MAX_TEXT_CHARS,
    LightpandaObservation,
    ObservationRefused,
    project_document,
)

URL = "http://127.0.0.1:8000/fixture?private=unpublished#part"
IDENTITY = {"boot": "test-boot", "pid": 123, "start": "1234.5", "binary_sha256": "a" * 64}
FRAME = "FID-0000000001"
LOADER = "LID-0000000001"


def document(body):
    next_id = 0

    def node(kind, name, value="", attrs=None, children=()):
        nonlocal next_id
        next_id += 1
        return {"nodeId": next_id, "backendNodeId": next_id, "nodeType": kind, "nodeName": name,
                "nodeValue": value, "attributes": attrs or [], "children": list(children),
                "childNodeCount": len(children)}

    def text(value):
        return node(3, "#text", value)

    def element(tag, *children, attrs=None):
        return node(1, tag.upper(), attrs=attrs, children=children)

    content = body(element, text)
    html = element("html", element("head", element("title", text("Fixture"))), element("body", *content))
    html["frameId"] = FRAME
    root = node(9, "#document", children=[html])

    def parents(parent):
        for child in parent["children"]:
            child["parentId"] = parent["nodeId"]
            parents(child)

    parents(root)
    return root


def ordinary():
    return document(lambda e, t: [e("h1", t("A useful heading")), e("p", t("Hello "), e("em", t("world"))),
                                 e("a", t("Read more"), attrs=["href", "/next?token=unpublished#anchor"]),
                                 e("button", t("Commit fixture"))])


def shallow(root):
    value = copy.deepcopy(root)
    for child in value["children"]:
        child.pop("children", None)
    return value


class Connection:
    def __init__(self, root=None):
        self.root = root if root is not None else ordinary()
        self.sent = []
        self.queue = None
        self.loaded = True
        self.url = "about:blank"
        self.target = FRAME
        self.frame = FRAME
        self.loader = LOADER
        self.title = "Metadata title is not captured content"
        self.hook = None
        self.replies = {}

    async def send(self, method, params=None, *, session_id=None, timeout=10):
        self.sent.append((method, params, session_id))
        if self.hook:
            self.hook(method, params, session_id)
        if method in self.replies:
            value = self.replies[method]
            if isinstance(value, BaseException):
                raise value
            return value
        if method == "Target.createTarget":
            assert params == {"url": "about:blank"} and session_id is None
            return {"targetId": self.target}
        if method == "Target.getTargets":
            return {"targetInfos": [{"type": "page", "targetId": self.target, "browserContextId": "BID-1",
                                     "url": self.url, "title": self.title, "attached": True}]}
        if method == "Target.attachToTarget":
            assert params == {"targetId": self.target, "flatten": True}
            return {"sessionId": "SID-1"}
        if method == "Page.enable":
            assert session_id == "SID-1"
            return {}
        if method == "Page.navigate":
            assert session_id == "SID-1"
            self.url = params["url"]
            if self.loaded:
                self.queue.put_nowait({"timestamp": 100})
            return {"frameId": self.frame, "loaderId": self.loader}
        if method == "Page.getFrameTree":
            assert session_id == "SID-1"
            return {"frameTree": {"frame": {"id": self.frame, "loaderId": self.loader, "url": self.url}}}
        if method == "DOM.getDocument":
            assert session_id == "SID-1" and params["pierce"] is False
            return {"root": self.root if params["depth"] == -1 else shallow(self.root)}
        raise AssertionError("unqualified command: " + method)

    def listen(self, method, *, session_id=None):
        assert method == "Page.loadEventFired" and session_id == "SID-1"
        self.queue = asyncio.Queue()
        return self.queue

    def unlisten(self, queue):
        assert queue is self.queue
        self.queue = None


def observe(connection):
    async def run():
        observer = LightpandaObservation(connection, IDENTITY)
        await observer.open(URL)
        return await observer.snapshot()

    return asyncio.run(run())


def test_real_target_created_and_one_connection_supplies_bounded_dom_text():
    connection = Connection()
    result = observe(connection)
    assert result["engine"] == "lightpanda" and result["producer"] == "footwork.browser.lightpanda.dom_text"
    assert result["text"] == "A useful heading\nHello world\nRead more\nCommit fixture"
    assert result["content"][0]["kind"] == "heading" and result["content"][0]["heading_level"] == 1
    assert result["content"][2]["destination"]["url"] == "http://127.0.0.1:8000/next"
    assert result["page"]["url"] == "http://127.0.0.1:8000/fixture"
    assert result["page"]["title"] == "Fixture" and result["page"]["title_source"] == "DOM.getDocument"
    assert "unpublished" not in json.dumps(result)
    assert result["identity"] | IDENTITY == result["identity"]
    assert result["identity"]["target_id"] == result["identity"]["frame_id"] == FRAME
    assert result["capture"]["reported_identifiers_unchanged"] is True
    assert result["capture"]["atomic"] is False and result["capture"]["numeric_alias_resistance"] == "unqualified"
    assert result["complete"] is False and result["actions"] == [] and result["mutation_authority"] is False
    assert result["completion"] == "not_asserted" and result["input_dispatched"] is False
    assert result["capabilities"] == {"dom_text": True, "layout": False, "visibility": False,
                                       "screenshots": False, "click": False, "typing": False, "raw_script": False}
    methods = [call[0] for call in connection.sent]
    assert methods[0] == "Target.createTarget"
    assert set(methods) == {"Target.createTarget", "Target.getTargets", "Target.attachToTarget", "Page.enable",
                            "Page.navigate", "Page.getFrameTree", "DOM.getDocument"}


@pytest.mark.parametrize("value", ["short-demo", "another-demonstration-value-with-a-different-length", "•••••••••"])
def test_field_values_and_derived_form_labels_never_enter_projection(value):
    root = document(lambda e, t: [
        e("h2", t("Readable content")),
        e("input", attrs=["type", "password", "id", "secret", "value", value, "aria-label", value]),
        e("label", t(value), attrs=["for", "secret"]),
        e("label", t(value), e("textarea", t(value))),
        e("input", attrs=["type", "text", "value", value]),
        e("select", e("option", t(value))),
        e("div", e("p", t(value)), attrs=["contenteditable", "true"]),
        e("div", t(value), attrs=["role", "textbox"]),
        e("p", t("Safe final text")),
    ])
    projection = project_document(root, url=URL)
    assert projection["text"] == "Readable content\nSafe final text"
    assert value not in json.dumps(projection)
    assert not any(key in json.dumps(projection) for key in ("value_length", "password_length", "aria-label"))


def test_scripts_styles_templates_frames_shadow_and_obvious_hidden_content_are_omitted():
    root = document(lambda e, t: [
        e("p", t("Keep this")), e("script", t("private-script")), e("style", t("private-style")),
        e("template", e("p", t("private-template"))), e("iframe", t("private-frame")),
        e("p", t("private-hidden"), attrs=["hidden", "false"]),
        e("p", t("private-aria"), attrs=["aria-hidden", "true"]),
        e("p", t("private-inert"), attrs=["inert", ""]),
        e("p", t("private-style-hidden"), attrs=["style", "color:red; DISPLAY : none !important;"]),
        e("p", t("Unknown CSS class text"), attrs=["class", "hidden-by-external-css"]),
    ])
    root["children"][0]["children"][1]["shadowRoots"] = [{"nodeType": 11, "nodeValue": "private-shadow"}]
    result = observe(Connection(root))
    assert result["text"] == "Keep this\nUnknown CSS class text"
    assert "private-" not in json.dumps(result)
    assert result["omitted"]["shadow_roots"] == 1
    assert result["capabilities"]["visibility"] is False


@pytest.mark.parametrize("method,reply", [
    ("Target.createTarget", {}), ("Target.createTarget", {"targetId": "TID-STARTUP"}),
    ("Target.getTargets", {"targetInfos": []}),
    ("Target.getTargets", {"targetInfos": [{"targetId": FRAME, "type": "page"}]}),
    ("Target.attachToTarget", {}), ("Target.attachToTarget", {"sessionId": "SID-STARTUP"}),
    ("Page.navigate", {}), ("Page.navigate", {"frameId": FRAME, "loaderId": LOADER, "errorText": "private-error"}),
    ("Page.getFrameTree", {"frameTree": {"frame": {"id": "TID-STARTUP", "loaderId": "LID-STARTUP", "url": "about:blank"}}}),
])
def test_success_shaped_placeholders_and_bad_setup_schemas_refuse(method, reply):
    connection = Connection()
    connection.replies[method] = reply
    with pytest.raises(ObservationRefused) as failure:
        observe(connection)
    assert "private-error" not in str(failure.value)
    assert not any(call[0].startswith(("Input.", "Runtime.")) for call in connection.sent)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "data:text/html,x", "http://a:b@example.test/", "http://x:0/"])
def test_bad_initial_url_refuses_before_protocol(url):
    connection = Connection()
    observer = LightpandaObservation(connection, IDENTITY)
    with pytest.raises(ObservationRefused):
        asyncio.run(observer.open(url))
    assert connection.sent == []


@pytest.mark.parametrize("field,value", [("pid", True), ("start", "nan"), ("boot", ""), ("binary_sha256", "bad")])
def test_unqualified_process_metadata_refuses(field, value):
    with pytest.raises(ObservationRefused):
        LightpandaObservation(Connection(), {**IDENTITY, field: value})


def test_observer_has_no_input_or_arbitrary_script_methods_and_open_is_one_use():
    connection = Connection()
    observer = LightpandaObservation(connection, IDENTITY)
    for method in ("click", "type_text", "navigate", "evaluate", "hotkey", "press_key"):
        assert not hasattr(observer, method)

    async def run():
        with pytest.raises(ObservationRefused):
            await observer.snapshot()
        await observer.open(URL)
        count = len(connection.sent)
        with pytest.raises(ObservationRefused, match="one initial"):
            await observer.open(URL)
        assert len(connection.sent) == count

    asyncio.run(run())


def test_load_deadline_does_not_retry_or_open_another_target():
    connection = Connection()
    connection.loaded = False

    async def run():
        observer = LightpandaObservation(connection, IDENTITY)
        with pytest.raises(ObservationRefused):
            await observer.open(URL, timeout=0.01)
        count = len(connection.sent)
        with pytest.raises(ObservationRefused):
            await observer.snapshot()
        assert len(connection.sent) == count
        assert connection.queue is None

    asyncio.run(run())
    assert sum(method == "Target.createTarget" for method, *_ in connection.sent) == 1


@pytest.mark.parametrize("boundary", ["loader", "frame", "root", "target", "context"])
def test_detectable_document_or_target_change_refuses_without_rebinding(boundary):
    connection = Connection()
    captured = False

    def change(method, params, session):
        nonlocal captured
        if method == "DOM.getDocument" and params["depth"] == 0:
            if boundary == "loader":
                connection.loader = "LID-0000000002"
            elif boundary == "frame":
                connection.frame = "FID-0000000002"
            elif boundary == "root":
                connection.root = copy.deepcopy(connection.root)
                connection.root["children"][0]["backendNodeId"] += 100
            elif boundary == "target":
                connection.target = "FID-0000000002"
            else:
                connection.replies["Target.getTargets"] = {"targetInfos": [{"targetId": FRAME, "type": "page",
                    "browserContextId": "BID-2", "url": URL, "title": "Fixture"}]}
            captured = True

    connection.hook = change

    async def run():
        observer = LightpandaObservation(connection, IDENTITY)
        await observer.open(URL)
        with pytest.raises(ObservationRefused):
            await observer.snapshot()
        count = len(connection.sent)
        with pytest.raises(ObservationRefused):
            await observer.snapshot()
        assert len(connection.sent) == count

    asyncio.run(run())
    assert captured
    assert sum(method == "Target.createTarget" for method, *_ in connection.sent) == 1


def test_connection_loss_remains_a_fixed_refusal_with_no_reconnect():
    connection = Connection()

    async def run():
        observer = LightpandaObservation(connection, IDENTITY)
        await observer.open(URL)
        connection.replies["DOM.getDocument"] = CdpUnknownOutcome("DOM.getDocument", "private-page-error")
        with pytest.raises(ObservationRefused) as failure:
            await observer.snapshot()
        assert "private-page-error" not in str(failure.value)
        count = len(connection.sent)
        with pytest.raises(ObservationRefused):
            await observer.snapshot()
        assert len(connection.sent) == count

    asyncio.run(run())


@pytest.mark.parametrize("boundary", ["before", "after"])
def test_target_and_frame_url_disagreement_refuses_instead_of_mixing_capture(boundary):
    connection = Connection()

    async def run():
        observer = LightpandaObservation(connection, IDENTITY)
        await observer.open(URL)
        original = connection.send
        post_root = False

        async def mismatched(method, params=None, **kwargs):
            nonlocal post_root
            result = await original(method, params, **kwargs)
            if method == "DOM.getDocument" and params["depth"] == 0:
                post_root = True
            if method == "Target.getTargets" and (boundary == "before" or post_root):
                result["targetInfos"][0]["url"] = "http://127.0.0.1:8000/other"
            return result

        connection.send = mismatched
        with pytest.raises(ObservationRefused, match="URL|identity"):
            await observer.snapshot()
        if boundary == "before":
            assert not any(method == "DOM.getDocument" for method, *_ in connection.sent)

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["cycle", "duplicate_id", "missing_children", "wrong_parent", "bad_attributes", "deep", "wide"])
def test_malformed_incomplete_and_unbounded_documents_refuse(mode):
    root = ordinary()
    if mode == "cycle":
        root["children"].append(root)
        root["childNodeCount"] += 1
    elif mode == "duplicate_id":
        root["children"][0]["backendNodeId"] = root["backendNodeId"]
    elif mode == "missing_children":
        root["children"][0].pop("children")
    elif mode == "wrong_parent":
        root["children"][0]["parentId"] += 1
    elif mode == "bad_attributes":
        root["children"][0]["attributes"] = ["value"]
    elif mode == "deep":
        root = document(lambda e, t: [t("small")])
        parent = root["children"][0]["children"][1]
        for number in range(MAX_DEPTH + 1):
            child = {"nodeId": number + 100, "backendNodeId": number + 100, "nodeType": 1, "nodeName": "DIV",
                     "nodeValue": "", "children": [], "childNodeCount": 0, "parentId": parent["nodeId"]}
            parent["children"].append(child)
            parent["childNodeCount"] = len(parent["children"])
            parent = child
    else:
        root = document(lambda e, t: [e("p", t("x")) for _ in range(MAX_NODES)])
    with pytest.raises(ObservationRefused):
        project_document(root, url=URL)


def test_text_and_record_budgets_are_explicit_and_output_stays_bounded():
    root = document(lambda e, t: [e("p", t("x" * 4000)) for _ in range(300)])
    result = observe(Connection(root))
    assert result["omitted"]["text_budget"] is True
    assert len(result["content"]) <= MAX_RECORDS
    assert sum(len(row["text"]) for row in result["content"]) <= MAX_TEXT_CHARS
    assert len(result["text"]) <= MAX_TEXT_CHARS
    assert len(json.dumps(result).encode()) <= MAX_OUTPUT_BYTES


@pytest.mark.parametrize("child_url", ["https://child.invalid/", "about:srcdoc", "data:text/html,private-child"])
def test_child_frames_are_reported_unavailable_not_captured(child_url):
    connection = Connection()
    original = connection.send

    async def send(method, *args, **kwargs):
        result = await original(method, *args, **kwargs)
        if method == "Page.getFrameTree":
            result["frameTree"]["childFrames"] = [{"frame": {"id": "FID-0000000002", "loaderId": "LID-0000000002",
                                                               "parentId": FRAME, "url": child_url}}]
        return result

    connection.send = send
    result = observe(connection)
    assert result["omitted"]["child_frames"] == 1
    assert not any(call[0] == "Target.attachToTarget" and call[1]["targetId"] != FRAME for call in connection.sent)


def test_base_href_withholds_destinations_instead_of_guessing_document_relative_urls():
    root = document(lambda e, t: [e("base", attrs=["href", "https://cdn.example/reports/"]),
                                 e("a", t("Read report"), attrs=["href", "report"])])
    result = observe(Connection(root))
    link = next(row for row in result["content"] if row["kind"] == "link")
    assert link["text"] == "Read report" and "destination" not in link
    assert result["omitted"]["link_destinations"] == 1
    assert "cdn.example" not in json.dumps(result)
