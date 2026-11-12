// DC8 model check: run DOM_EVENT_CLICK_SEQUENCE, extracted from a tools.rs, against DOM stubs.
// A model with stubs, not a browser. Usage: node sequence_stubs_dc8.mjs OLD_tools.rs NEW_tools.rs
import { readFileSync } from "node:fs";

function extract(path) {
  const src = readFileSync(path, "utf8");
  const head = 'const DOM_EVENT_CLICK_SEQUENCE: &str = "';
  const start = src.indexOf(head) + head.length;
  return src.slice(start, src.indexOf('}";', start) + 1).replace(/\\\n\s*/g, "").replace(/\\"/g, '"');
}

class Ev { constructor(type, init) { this.type = type; Object.assign(this, init); this.defaultPrevented = false; } }
function world() {
  const log = [];
  const w = {};
  const doc = { defaultView: { screenX: 0, screenY: 0, PointerEvent: Ev, MouseEvent: Ev } };
  const node = (name, tag) => ({
    name, tag, parent: null, isConnected: true, ownerDocument: doc, listeners: {}, children: [],
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 10, height: 10 }),
    contains(other) { for (let n = other; n; n = n.parent) if (n === this) return true; return false; },
    closest() { for (let n = this; n; n = n.parent) if (n.tag === "button" || n.tag === "focusable") return n; return null; },
    focus() { log[log.length] = { at: this.name, type: "focus", connected: this.isConnected, moved: this.name === "icon" && w.icon.parent === w.other }; },
    on(type, fn) { const list = (this.listeners[type] ||= []); list[list.length] = fn; },
    dispatchEvent(ev) {
      log[log.length] = { at: this.name, type: ev.type, connected: this.isConnected, moved: this.name === "icon" && w.icon.parent === w.other };
      for (const fn of this.listeners[ev.type] || []) fn(ev);
      return !ev.defaultPrevented;
    },
  });
  const adopt = (parent, child) => { if (child.parent) child.parent.children = child.parent.children.filter((c) => c !== child); child.parent = parent; parent.children[parent.children.length] = child; };
  const button = node("button", "button"), other = node("other-button", "button"), icon = node("icon", "span");
  adopt(button, icon);
  const root = { elementFromPoint: () => icon };
  for (const n of [button, other, icon]) n.getRootNode = () => root;
  const detach = (n) => { n.isConnected = false; if (n.parent) { n.parent.children = n.parent.children.filter((c) => c !== n); n.parent = null; } };
  return Object.assign(w, { button, other, icon, log, adopt, detach });
}

function run(source, setup) {
  const w = world();
  const restore = setup(w) || (() => {});
  let result;
  try { result = new Function(`return (${source})`)().call(w.button); }
  catch (e) { result = { threw: String(e && e.message || e) }; }
  finally { restore(); }
  return {
    result,
    delivered: w.log.map((e) => `${e.at}:${e.type}${e.connected ? "" : "(detached)"}`),
    to_detached: w.log.filter((e) => !e.connected).length,
    to_moved_icon: w.log.filter((e) => e.moved).length,
  };
}

const cases = {
  focusable_icon_removed_on_mousedown: (w) => { w.icon.tag = "focusable"; w.icon.on("mousedown", () => w.detach(w.icon)); },
  icon_moved_to_another_button_on_pointerdown: (w) => { w.icon.on("pointerdown", () => w.adopt(w.other, w.icon)); },
  dispatch_wrapper_throws_before_click: (w) => {
    const real = w.icon.dispatchEvent.bind(w.icon);
    w.icon.dispatchEvent = (ev) => { if (ev.type === "mouseup") throw new Error("wrapper"); return real(ev); };
  },
  noop_array_push_then_ref_removed_on_pointerdown: (w) => {
    w.icon.on("pointerdown", () => { w.detach(w.button); w.icon.isConnected = false; });
    const push = Array.prototype.push;
    Array.prototype.push = function () { return this.length; };
    return () => { Array.prototype.push = push; };
  },
  noop_array_push_connected: (w) => {
    const push = Array.prototype.push;
    Array.prototype.push = function () { return this.length; };
    return () => { Array.prototype.push = push; };
  },
};

const out = {};
for (const [label, path] of [["connected2", process.argv[2]], ["new", process.argv[3]]]) {
  const source = extract(path);
  out[label] = Object.fromEntries(Object.entries(cases).map(([name, setup]) => [name, run(source, setup)]));
}
console.log(JSON.stringify(out, null, 1));
