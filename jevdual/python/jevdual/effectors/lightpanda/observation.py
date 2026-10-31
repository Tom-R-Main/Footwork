"""Bounded DOM text from one owned Lightpanda connection; never input authority.

No AX names, JavaScript evaluation, layout, visibility or action references are
imported into this projection. The initial URL load can execute site JavaScript;
"read-only" means Footwork exposes no subsequent input/mutation operation.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
import secrets
import time
import unicodedata
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from ..cdp.transport import CdpClosed, CdpError, CdpUnknownOutcome

MAX_NODES = 10_000
MAX_DEPTH = 96
MAX_RECORDS = 256
MAX_TEXT_CHARS = 32_768
MAX_RECORD_CHARS = 2_048
MAX_OUTPUT_BYTES = 262_144
_FORMS = frozenset({"input", "textarea", "select", "option", "datalist"})
_EXCLUDED = frozenset({"script", "style", "template", "noscript", "head", "iframe", "frame", "object", "embed"})
_EDITABLE_ROLES = frozenset({"textbox", "searchbox", "combobox"})
_BLOCKS = {
    "p": "paragraph", "div": "text", "body": "text", "main": "text", "section": "text",
    "article": "text", "li": "list_item", "td": "table_cell", "th": "table_header",
    "dt": "term", "dd": "definition", "pre": "preformatted", "button": "button_label",
    "a": "link", "label": "label",
}
_HIDDEN_STYLE = re.compile(
    r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse)|"
    r"content-visibility\s*:\s*hidden|opacity\s*:\s*0(?:\.0*)?)\s*(?:!important\s*)?(?:;|$)", re.IGNORECASE
)


class ObservationRefused(RuntimeError):
    """A fixed diagnostic, never a raw page/protocol exception or no-network claim."""

    input_dispatched = False

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _refuse(code: str, message: str) -> None:
    raise ObservationRefused(code, message)


def _id(value: Any, prefix: str) -> str:
    if not isinstance(value, str) or re.fullmatch(re.escape(prefix) + r"-\d{1,10}", value) is None:
        _refuse("lightpanda_protocol_invalid", "the engine did not identify a real target, frame or session")
    return value


def _url(value: Any, *, initial: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > 16_384:
        _refuse("lightpanda_url_invalid", "a bounded HTTP(S) URL is required")
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme in {"http", "https"} and parsed.hostname
                 and not parsed.username and not parsed.password and parsed.port != 0)
    except ValueError:
        valid = False
    if not valid and not (not initial and value == "about:blank"):
        _refuse("lightpanda_url_invalid", "a bounded HTTP(S) URL without userinfo is required")
    return value


def _public_url(value: str) -> dict[str, Any]:
    parsed = urlsplit(value)
    public = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return {"url": public, "url_sha256": hashlib.sha256(value.encode()).hexdigest(),
            "query_or_fragment_withheld": bool(parsed.query or parsed.fragment)}


def _identity(value: Any) -> dict[str, Any]:
    if (not isinstance(value, dict) or set(value) != {"boot", "pid", "start", "binary_sha256"}
            or not isinstance(value["boot"], str) or not value["boot"] or len(value["boot"]) > 256
            or type(value["pid"]) is not int or value["pid"] <= 0
            or not isinstance(value["start"], str)
            or not isinstance(value["binary_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", value["binary_sha256"]) is None):
        _refuse("lightpanda_identity_invalid", "the observation needs its owned process identity")
    try:
        start = float(value["start"])
        if not math.isfinite(start) or start <= 0:
            raise ValueError
    except ValueError:
        _refuse("lightpanda_identity_invalid", "the observation needs its process incarnation")
    return dict(value)


def _attrs(node: dict) -> dict[str, str]:
    raw = node.get("attributes", [])
    if not isinstance(raw, list) or len(raw) % 2 or len(raw) > 512:
        _refuse("lightpanda_document_invalid", "the DOM attributes are malformed or exceed their bound")
    out = {}
    for key, value in zip(raw[::2], raw[1::2], strict=True):
        if not isinstance(key, str) or not isinstance(value, str) or not key or len(key) > 256:
            _refuse("lightpanda_document_invalid", "the DOM attributes are malformed")
        key = key.casefold()
        if key in out:
            _refuse("lightpanda_document_invalid", "the DOM attributes are ambiguous")
        # No attribute values are exported; these few are used only for withholding/links.
        if key in {"id", "for", "hidden", "aria-hidden", "inert", "style", "contenteditable", "role", "href"}:
            if len(value) > 16_384:
                _refuse("lightpanda_document_invalid", "a DOM attribute exceeds its read bound")
            out[key] = value
    return out


def _editable(tag: str, attributes: dict[str, str]) -> bool:
    return (tag in _FORMS or ("contenteditable" in attributes
                             and attributes["contenteditable"].strip().casefold() != "false")
            or attributes.get("role", "").strip().casefold() in _EDITABLE_ROLES)


def _shape(root: Any, *, full: bool) -> tuple[list[tuple[dict, int | None]], tuple[int, int, str]]:
    """Validate an iterative tree before any text projection; no recursive untrusted walk."""
    if not isinstance(root, dict) or root.get("nodeType") != 9:
        _refuse("lightpanda_document_invalid", "the engine did not return a document root")
    stack = [(root, None, 0)]
    seen_objects, node_ids, backend_ids = set(), set(), set()
    ordered = []
    html = []
    while stack:
        node, parent, depth = stack.pop()
        if (not isinstance(node, dict) or id(node) in seen_objects or depth > MAX_DEPTH
                or len(ordered) >= MAX_NODES):
            _refuse("lightpanda_document_invalid", "the DOM is cyclic, malformed or exceeds its read bound")
        seen_objects.add(id(node))
        for key, used in (("nodeId", node_ids), ("backendNodeId", backend_ids)):
            value = node.get(key)
            if type(value) is not int or value <= 0 or value in used:
                _refuse("lightpanda_document_invalid", "the DOM node identities are missing or ambiguous")
            used.add(value)
        if (type(node.get("nodeType")) is not int or not 1 <= node["nodeType"] <= 12
                or not isinstance(node.get("nodeName"), str) or len(node["nodeName"]) > 256
                or not isinstance(node.get("nodeValue"), str)):
            _refuse("lightpanda_document_invalid", "the DOM node schema is malformed")
        if "parentId" in node and node["parentId"] != parent:
            _refuse("lightpanda_document_invalid", "the DOM parent identity is inconsistent")
        attributes = _attrs(node)
        tag = node["nodeName"].casefold()
        if depth == 1 and node["nodeType"] == 1 and tag == "html":
            html.append(node)
        children = node.get("children", [])
        count = node.get("childNodeCount", len(children) if isinstance(children, list) else -1)
        if (not isinstance(children, list) or type(count) is not int or count < 0
                or len(children) > MAX_NODES or count < len(children)):
            _refuse("lightpanda_document_invalid", "the DOM children are malformed")
        if full and count != len(children):
            _refuse("lightpanda_document_incomplete", "the requested complete DOM tree was truncated")
        ordered.append((node, parent))
        # A depth-zero root check intentionally carries shallow child records.
        if full or depth == 0:
            stack.extend((child, node["nodeId"], depth + 1) for child in reversed(children))
        elif children:
            _refuse("lightpanda_document_invalid", "the shallow root check returned an unexpected nested tree")
        del attributes
    if len(html) != 1:
        _refuse("lightpanda_document_unsupported", "only a main HTML document is qualified for this projection")
    frame = _id(html[0].get("frameId"), "FID")
    return ordered, (root["backendNodeId"], html[0]["backendNodeId"], frame)


def _text(value: str) -> str:
    value = "".join(c for c in value if unicodedata.category(c) not in {"Cc", "Cf", "Co"} or c in "\n\r\t")
    return " ".join(value.split())


def _document_title(root: dict) -> str:
    """Read the main HTML title from the same validated DOM reply as the content."""
    html = next(child for child in root["children"] if child["nodeName"].casefold() == "html")
    head = next((child for child in html.get("children", []) if child["nodeName"].casefold() == "head"), None)
    if head is None:
        return ""
    title = next((child for child in head.get("children", []) if child["nodeName"].casefold() == "title"), None)
    if title is None:
        return ""
    # Only direct text is qualified here, rather than synthesizing an accessible name.
    parts = []
    remaining = 2_048
    for child in title.get("children", []):
        if child["nodeType"] in (3, 4):
            parts.append(child["nodeValue"][:remaining])
            remaining -= len(parts[-1])
            if remaining <= 0:
                break
    return _text("".join(parts))[:512]


def project_document(root: dict, *, url: str) -> dict[str, Any]:
    """DOM text only. Field values and raw attributes never enter the public result."""
    ordered, _ = _shape(root, full=True)
    form_ids, controls = set(), set()
    # The engine reports baseURL=null. Never guess link semantics when a base exists.
    unqualified_base = any(node["nodeName"].casefold() == "base" and "href" in _attrs(node)
                           for node, _ in ordered)
    parents = {node["nodeId"]: parent for node, parent in ordered}
    nodes = {node["nodeId"]: node for node, _ in ordered}
    for node, _ in ordered:
        attributes = _attrs(node)
        if _editable(node["nodeName"].casefold(), attributes):
            controls.add(node["nodeId"])
            if attributes.get("id"):
                form_ids.add(attributes["id"])
    # Withhold associated form labels too: an engine/page can derive one from a field value.
    private_labels = set()
    for node, _ in ordered:
        if node["nodeName"].casefold() == "label" and _attrs(node).get("for") in form_ids:
            private_labels.add(node["nodeId"])
    for control in controls:
        parent = parents[control]
        while parent is not None:
            if nodes[parent]["nodeName"].casefold() == "label":
                private_labels.add(parent)
            parent = parents[parent]

    omitted = {"form_subtrees": 0, "form_labels": 0, "excluded_subtrees": 0,
               "obvious_hidden_subtrees": 0, "shadow_roots": 0, "link_destinations": 0, "text_budget": False}
    skipped, contexts = set(), {}
    records, last_context, total = [], None, 0
    for node, parent in ordered:
        nid, tag = node["nodeId"], node["nodeName"].casefold()
        if parent in skipped:
            skipped.add(nid)
            continue
        attributes = _attrs(node)
        if nid in controls:
            omitted["form_subtrees"] += 1
            skipped.add(nid)
            continue
        if nid in private_labels:
            omitted["form_labels"] += 1
            skipped.add(nid)
            continue
        if tag in _EXCLUDED:
            omitted["excluded_subtrees"] += 1
            skipped.add(nid)
            continue
        if ("hidden" in attributes or "inert" in attributes
                or attributes.get("aria-hidden", "").strip().casefold() == "true"
                or _HIDDEN_STYLE.search(attributes.get("style", ""))):
            omitted["obvious_hidden_subtrees"] += 1
            skipped.add(nid)
            continue
        shadows = node.get("shadowRoots", [])
        if not isinstance(shadows, list):
            _refuse("lightpanda_document_invalid", "the shadow-root schema is malformed")
        omitted["shadow_roots"] += len(shadows)
        context = contexts.get(parent, ("text", root["nodeId"], None))
        if tag in _BLOCKS or re.fullmatch("h[1-6]", tag):
            kind = "heading" if tag.startswith("h") and len(tag) == 2 else _BLOCKS[tag]
            link = None
            if tag == "a" and attributes.get("href") and unqualified_base:
                omitted["link_destinations"] += 1
            elif tag == "a" and attributes.get("href"):
                try:
                    destination = _url(urljoin(url, attributes["href"]))
                except ObservationRefused:
                    destination = None
                link = _public_url(destination) if destination else None
            context = (kind, nid, {"heading_level": int(tag[1])} if kind == "heading" else link)
        contexts[nid] = context
        if node["nodeType"] not in (3, 4):
            continue
        # Excluded field subtrees were skipped before this point, including their string length.
        value = _text(node["nodeValue"][:MAX_TEXT_CHARS + 1])
        if not value:
            continue
        separator = 1 if records else 0
        allowed = min(MAX_RECORD_CHARS, MAX_TEXT_CHARS - total - separator)
        if allowed <= 0 or len(records) >= MAX_RECORDS:
            omitted["text_budget"] = True
            break
        clipped = value[:allowed]
        omitted["text_budget"] |= len(value) > allowed or len(node["nodeValue"]) > MAX_TEXT_CHARS
        total += len(clipped) + separator
        if records and context == last_context and len(records[-1]["text"]) + len(clipped) + 1 <= MAX_RECORD_CHARS:
            records[-1]["text"] += " " + clipped
        else:
            record = {"record_id": len(records) + 1, "kind": context[0], "text": clipped}
            if context[0] == "heading":
                record.update(context[2])
            elif context[0] == "link" and context[2] is not None:
                record["destination"] = context[2]
            records.append(record)
        last_context = context
    return {"content": records, "text": "\n".join(row["text"] for row in records), "omitted": omitted}


class LightpandaObservation:
    """One initial load and bounded captures on the same owned connection."""

    def __init__(self, conn, identity: dict[str, Any]):
        self.conn = conn
        self.identity = _identity(identity)
        self.connection_id = secrets.token_hex(16)
        self.target = self.session = self.context = None
        self._used = self._ready = self._failed = False
        self._lock = asyncio.Lock()

    async def _target(self) -> dict:
        reply = await self.conn.send("Target.getTargets")
        infos = reply.get("targetInfos") if isinstance(reply, dict) else None
        if not isinstance(infos, list) or len(infos) != 1 or not isinstance(infos[0], dict):
            _refuse("lightpanda_target_changed", "the owned connection no longer has its one real page")
        page = infos[0]
        if (page.get("type") != "page" or _id(page.get("targetId"), "FID") != self.target
                or _id(page.get("browserContextId"), "BID") != self.context):
            _refuse("lightpanda_target_changed", "the page or browser context changed; it is not rebound")
        _url(page.get("url"))
        if not isinstance(page.get("title"), str) or len(page["title"]) > 16_384:
            _refuse("lightpanda_protocol_invalid", "the page metadata is malformed")
        return page

    async def _frame(self) -> tuple[dict, int]:
        reply = await self.conn.send("Page.getFrameTree", session_id=self.session)
        tree = reply.get("frameTree") if isinstance(reply, dict) else None
        pending = [(tree, None)]
        seen, frame_ids, count, main = set(), set(), 0, None
        while pending:
            branch, parent = pending.pop()
            if not isinstance(branch, dict) or id(branch) in seen or count >= 128:
                _refuse("lightpanda_protocol_invalid", "the frame tree is malformed or exceeds its bound")
            seen.add(id(branch))
            frame = branch.get("frame")
            if not isinstance(frame, dict):
                _refuse("lightpanda_protocol_invalid", "the frame tree has no real frame")
            frame_id = _id(frame.get("id"), "FID")
            if frame_id in frame_ids or ("parentId" in frame and frame["parentId"] != parent):
                _refuse("lightpanda_protocol_invalid", "the frame identities are inconsistent")
            frame_ids.add(frame_id)
            _id(frame.get("loaderId"), "LID")
            if parent is None:
                _url(frame.get("url"))
            elif not isinstance(frame.get("url"), str) or len(frame["url"]) > 16_384:
                _refuse("lightpanda_protocol_invalid", "the omitted child-frame metadata is malformed")
            if main is None:
                main = frame
            children = branch.get("childFrames", [])
            if not isinstance(children, list) or len(children) > 128:
                _refuse("lightpanda_protocol_invalid", "the frame children are malformed")
            pending.extend((child, frame_id) for child in children)
            count += 1
        return main, count - 1

    async def open(self, url: str, timeout: float = 15) -> None:
        url = _url(url, initial=True)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            _refuse("lightpanda_timeout_invalid", "a finite positive readiness deadline is required")
        async with self._lock:
            if self._used:
                _refuse("lightpanda_already_open", "this observer permits one initial URL load only")
            self._used = True
            try:
                async with asyncio.timeout(timeout):
                    created = await self.conn.send("Target.createTarget", {"url": "about:blank"})
                    self.target = _id(created.get("targetId") if isinstance(created, dict) else None, "FID")
                    pages = await self.conn.send("Target.getTargets")
                    infos = pages.get("targetInfos") if isinstance(pages, dict) else None
                    if (not isinstance(infos, list) or len(infos) != 1 or not isinstance(infos[0], dict)
                            or infos[0].get("targetId") != self.target or infos[0].get("type") != "page"):
                        _refuse("lightpanda_protocol_invalid", "target creation did not produce one real page")
                    self.context = _id(infos[0].get("browserContextId"), "BID")
                    attached = await self.conn.send("Target.attachToTarget", {"targetId": self.target, "flatten": True})
                    self.session = _id(attached.get("sessionId") if isinstance(attached, dict) else None, "SID")
                    await self.conn.send("Page.enable", session_id=self.session)
                    loaded = self.conn.listen("Page.loadEventFired", session_id=self.session)
                    try:
                        navigated = await self.conn.send("Page.navigate", {"url": url}, session_id=self.session)
                        if not isinstance(navigated, dict) or navigated.get("errorText"):
                            _refuse("lightpanda_load_failed", "the initial URL did not load")
                        frame = _id(navigated.get("frameId"), "FID")
                        loader = _id(navigated.get("loaderId"), "LID")
                        event = await loaded.get()
                        if (not isinstance(event, dict) or type(event.get("timestamp")) not in (int, float)
                                or not math.isfinite(event["timestamp"]) or event["timestamp"] < 0):
                            _refuse("lightpanda_protocol_invalid", "the load event is malformed")
                    finally:
                        self.conn.unlisten(loaded)
                    await self._target()
                    current, _ = await self._frame()
                    if (current["id"], current["loaderId"]) != (frame, loader):
                        _refuse("lightpanda_document_changed", "the page changed while initial loading settled")
                    self._ready = True
            except asyncio.CancelledError:
                self._failed = True
                raise
            except (CdpError, CdpClosed, CdpUnknownOutcome, TimeoutError) as exc:
                self._failed = True
                raise ObservationRefused("lightpanda_load_unavailable", "initial loading lost its bounded owned connection") from exc
            except ObservationRefused:
                self._failed = True
                raise
            except Exception as exc:
                self._failed = True
                raise ObservationRefused("lightpanda_load_unavailable", "initial loading could not be qualified") from exc

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            if not self._ready or self._failed:
                _refuse("lightpanda_observation_unavailable", "no current observation is available on this owned connection")
            started = time.time()
            try:
                async with asyncio.timeout(20):
                    page = await self._target()
                    before, child_frames = await self._frame()
                    if page["url"] != before["url"]:
                        _refuse("lightpanda_document_changed", "target and main-frame URLs disagree before capture")
                    document = await self.conn.send("DOM.getDocument", {"depth": -1, "pierce": False}, session_id=self.session)
                    root = document.get("root") if isinstance(document, dict) else None
                    _, root_identity = _shape(root, full=True)
                    if root_identity[2] != before["id"]:
                        _refuse("lightpanda_document_changed", "the DOM belongs to another main frame")
                    projected = project_document(root, url=before["url"])
                    checked = await self.conn.send("DOM.getDocument", {"depth": 0, "pierce": False}, session_id=self.session)
                    _, after_root = _shape(checked.get("root") if isinstance(checked, dict) else None, full=False)
                    after, after_children = await self._frame()
                    target_after = await self._target()
                    if (root_identity != after_root or child_frames != after_children
                            or target_after["url"] != after["url"]
                            or any(before[key] != after[key] for key in ("id", "loaderId", "url"))):
                        _refuse("lightpanda_document_changed", "reported document identity changed during capture")
                    result = {
                        "schema_version": "1", "producer": "footwork.browser.lightpanda.dom_text", "engine": "lightpanda",
                        "observation_id": "lpobs_" + secrets.token_hex(12),
                        "identity": {**self.identity, "connection_id": self.connection_id,
                                     "browser_context_id": self.context, "target_id": self.target,
                                     "session_id": self.session, "frame_id": before["id"], "loader_id": before["loaderId"]},
                        "capture": {"start": started, "end": time.time(), "atomic": False,
                                    "reported_identifiers_unchanged": True, "numeric_alias_resistance": "unqualified"},
                        "page": {**_public_url(before["url"]), "title": _document_title(root),
                                 "title_source": "DOM.getDocument"},
                        **projected,
                        "complete": False, "actions": [], "input_dispatched": False,
                        "mutation_authority": False, "completion": "not_asserted",
                        "capabilities": {"dom_text": True, "layout": False, "visibility": False,
                                         "screenshots": False, "click": False, "typing": False, "raw_script": False},
                        "limits": ["DOM text is not rendered/visible text; CSS-hidden content may remain.",
                                   "Form values and associated labels are withheld; child frames and shadow roots are omitted.",
                                   "Link destinations are withheld when a captured base href makes the effective base unqualified.",
                                   "Record IDs identify this capture's text only and cannot authorize input.",
                                   "Matching numeric identifiers does not prove an atomic or mutation-safe document binding.",
                                   "Initial URL loading executes site code and may have network effects."],
                    }
                    result["omitted"]["child_frames"] = child_frames
                    import json

                    if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode()) > MAX_OUTPUT_BYTES:
                        _refuse("lightpanda_observation_too_large", "the observation exceeds its output bound")
                    return result
            except asyncio.CancelledError:
                self._failed = True
                raise
            except (CdpError, CdpClosed, CdpUnknownOutcome, TimeoutError) as exc:
                self._failed = True
                raise ObservationRefused("lightpanda_observation_unavailable", "capture lost its bounded owned connection") from exc
            except ObservationRefused:
                self._failed = True
                raise
            except Exception as exc:
                self._failed = True
                raise ObservationRefused("lightpanda_observation_unavailable", "capture could not be qualified") from exc
