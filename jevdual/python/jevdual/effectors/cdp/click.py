"""The bounded native-button activation route, not CUA's pointer/mouse event sequence.

Only directly named, plain ``button[type=button]`` controls are qualified. The DOM snapshot supplies
the entire bounded fingerprint; the isolated-world function compares it immediately before native
activation. No host-supplied script, selector replacement, pointer fallback or retry is exposed.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any

from .snapshot import _clean

ROUTE = "dom_event_native_button"
MAX_FINGERPRINT = 8192
MAX_ATTRIBUTES = 64
MAX_ANCESTORS = 64
MAX_TEXT_NODES = 128


@dataclass(frozen=True)
class ButtonTarget:
    fingerprint_json: str

    def argument(self) -> dict[str, Any]:
        return json.loads(self.fingerprint_json)


def button_targets(document: dict[str, Any], refs: list[dict[str, Any]], backend: dict[str, int]) -> dict[int, ButtonTarget]:
    """Extract only buttons whose complete direct name is represented by the offered AX label."""
    offered = {backend[r["ref"]]: r for r in refs if r.get("ref") in backend}
    out = {}

    def attrs(node):
        raw = node.get("attributes") or []
        if len(raw) > MAX_ATTRIBUTES * 2 or sum(len(str(v)) for v in raw) > MAX_FINGERPRINT:
            return None
        return sorted([[str(raw[i]), str(raw[i + 1])] for i in range(0, len(raw) - 1, 2)])

    def walk(node, ancestors):
        tag = str(node.get("nodeName") or "").lower()
        attributes = attrs(node)
        if attributes is None or len(ancestors) > MAX_ANCESTORS:
            return
        mapping = dict(attributes)
        children = node.get("children") or []
        row = offered.get(node.get("backendNodeId"))
        if row is not None and tag == "button" and mapping.get("type", "").lower() == "button":
            blocked = {"role", "aria-labelledby", "form", "popovertarget", "command", "commandfor"}
            pieces = [str(c.get("nodeValue") or "") for c in children if c.get("nodeType") == 3]
            if len(children) > MAX_TEXT_NODES or sum(map(len, pieces)) > MAX_FINGERPRINT:
                return
            text = "".join(pieces)
            raw_name = mapping.get("aria-label", text)
            bad_char = any(unicodedata.category(c) in {"Cf", "Co", "Cc"} and c not in "\t\n\r" for c in raw_name)
            name = _clean(raw_name)
            form = any(a["tag"] == "form" for a in ancestors)
            if (not blocked.intersection(mapping) and not form and not bad_char
                    and not any(c.get("nodeType") == 1 for c in children)
                    and not node.get("shadowRoots") and name and len(name) <= 120
                    and name == row.get("name") and row.get("role") == "button"
                    and "click" in (row.get("actions") or [])):
                fingerprint = {"tag": tag, "attrs": attributes, "text": text, "ancestors": ancestors}
                encoded = json.dumps(fingerprint, ensure_ascii=False, separators=(",", ":"))
                if len(encoded.encode()) <= MAX_FINGERPRINT:
                    out[node["backendNodeId"]] = ButtonTarget(encoded)
        next_ancestors = [*ancestors, {"tag": tag, "attrs": attributes}] if node.get("nodeType") == 1 else ancestors
        for child in children:
            walk(child, next_ancestors)
        # Shadow roots and contentDocument belong to unsupported naming/frame scopes.

    walk(document.get("root") or {}, [])
    return out


# The object is resolved into the observation's existing isolated context, not a new document's
# world. Validation and activation share this synchronous turn. Page click handlers still execute
# and can have arbitrary effects; the returned acknowledgement establishes no business postcondition.
ACTIVATE = r"""function(expected) {
    const reject = code => ({status: 'refused', code});
    try {
        let budget = 8192;
        const take = value => {
            budget -= value.length;
            if (budget < 0) throw new Error('fingerprint bound');
            return value;
        };
        const attrNames = Element.prototype.getAttributeNames;
        const attr = Element.prototype.getAttribute;
        const attributes = node => {
            if (node.attributes.length > 64) throw new Error('attribute bound');
            return attrNames.call(node).sort().map(name => [take(name), take(attr.call(node, name))]);
        };
        if (!this.isConnected || this.ownerDocument !== document || Node.prototype.getRootNode.call(this) !== document)
            return reject('stale_ref');
        if (this.localName !== 'button' || attr.call(this, 'type')?.toLowerCase() !== 'button'
            || this.childElementCount !== 0 || this.shadowRoot !== null || this.form !== null)
            return reject('button_changed');
        for (const name of ['role', 'aria-labelledby', 'form', 'popovertarget', 'command', 'commandfor'])
            if (Element.prototype.hasAttribute.call(this, name)) return reject('button_changed');
        if (Element.prototype.matches.call(this, ':disabled')
            || Element.prototype.closest.call(this, '[inert], [aria-disabled="true"], [aria-hidden="true"]'))
            return reject('button_disabled');
        if (!Element.prototype.checkVisibility.call(this, {checkOpacity: true, checkVisibilityCSS: true}))
            return reject('button_hidden');
        for (const pseudo of ['::before', '::after']) {
            const content = getComputedStyle(this, pseudo).content;
            if (!['none', 'normal', '""', "''"].includes(content)) return reject('button_changed');
        }
        const ancestors = [];
        for (let p = this.parentElement; p; p = p.parentElement) {
            ancestors.unshift({tag: take(p.localName), attrs: attributes(p)});
            if (ancestors.length > 64) return reject('button_changed');
        }
        if (this.childNodes.length > 128) return reject('button_changed');
        let text = '';
        for (const child of this.childNodes) {
            if (child.nodeType === Node.TEXT_NODE) {
                if (child.length > budget) return reject('button_changed');
                text += take(child.data);
            }
        }
        const actual = {tag: take(this.localName), attrs: attributes(this), text, ancestors};
        if (JSON.stringify(actual) !== JSON.stringify(expected)) return reject('button_changed');
    } catch (_) {
        return reject('button_validation_unavailable');
    }
    HTMLElement.prototype.click.call(this);
    return {status: 'invoked'};
}"""
