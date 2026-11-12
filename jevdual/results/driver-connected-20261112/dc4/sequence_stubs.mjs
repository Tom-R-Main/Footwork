// DC4 model check: run DOM_EVENT_CLICK_SEQUENCE, extracted from a tools.rs, against DOM stubs.
// A model with stubs, not a browser. Usage: node sequence_stubs.mjs OLD_tools.rs NEW_tools.rs
import { readFileSync } from "node:fs";

function extract(path) {
  const src = readFileSync(path, "utf8");
  const start = src.indexOf('const DOM_EVENT_CLICK_SEQUENCE: &str = "') + 'const DOM_EVENT_CLICK_SEQUENCE: &str = "'.length;
  const end = src.indexOf('}";', start) + 1;
  return src.slice(start, end).replace(/\\\n\s*/g, "").replace(/\\"/g, '"');
}

class Ev { constructor(type, init) { this.type = type; Object.assign(this, init); this.defaultPrevented = false; } }
function world() {
  const log = [];
  const doc = { defaultView: { screenX: 0, screenY: 0, PointerEvent: Ev, MouseEvent: Ev } };
  const node = (name) => ({
    name, isConnected: true, ownerDocument: doc, listeners: {}, children: [],
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 10, height: 10 }),
    contains(other) { return other === this || this.children.includes(other); },
    closest() { return this.tag === "button" ? this : this.parent?.closest?.() ?? null; },
    focus() { log.push({ at: this.name, type: "focus", connected: this.isConnected }); },
    on(type, fn) { (this.listeners[type] ||= []).push(fn); },
    dispatchEvent(ev) {
      log.push({ at: this.name, type: ev.type, connected: this.isConnected });
      for (const fn of this.listeners[ev.type] || []) fn(ev);
      return !ev.defaultPrevented;
    },
  });
  const button = node("button"); button.tag = "button";
  const icon = node("icon"); icon.parent = button; button.children.push(icon);
  const root = { elementFromPoint: () => (icon.isConnected ? icon : button) };
  button.getRootNode = () => root; icon.getRootNode = () => root;
  return { button, icon, log };
}

function run(fnSource, setup, withIcon) {
  const w = world();
  if (!withIcon) w.button.children.length = 0;
  setup(w);
  const fn = new Function(`return (${fnSource})`)();
  let result;
  try { result = fn.call(w.button); } catch (e) { result = { threw: String(e) }; }
  const toDetached = w.log.filter((e) => !e.connected && e.type !== "pointerover_sentinel");
  return { result, delivered: w.log.map((e) => `${e.at}:${e.type}${e.connected ? "" : "(detached)"}`), afterDetach: toDetached.length };
}

const cases = {
  connected: [(w) => {}, false],
  detached_before_call: [(w) => { w.button.isConnected = false; }, false],
  detached_on_pointerover: [(w) => { w.button.on("pointerover", () => { w.button.isConnected = false; }); }, false],
  icon_replaced_on_pointerdown: [(w) => { w.icon.on("pointerdown", () => { w.icon.isConnected = false; }); }, true],
  button_removed_on_pointerdown_via_icon: [(w) => { w.icon.on("pointerdown", () => { w.button.isConnected = false; w.icon.isConnected = false; }); }, true],
};

const out = {};
for (const [label, path] of [["old", process.argv[2]], ["new", process.argv[3]]]) {
  const source = extract(path);
  out[label] = {};
  for (const [name, [setup, withIcon]] of Object.entries(cases)) out[label][name] = run(source, setup, withIcon);
}
console.log(JSON.stringify(out, null, 1));
