"""Did the input reach the page, and what changed that the element diff cannot see (package D).

A receipt's effect word says what the page shows after a step. It cannot say why nothing changed:
the click may never have arrived (package C: Chrome's breached-password warning dropped every
dispatched click, and receipts said only "suspected no-op"), or it arrived and the page ignored it.
Nor does the element diff see scrolling, a focus move, or a navigation that lands after the step's
read. A :class:`PageProbe` is a small read of the top document taken before and after each step by a
listener installed once per document; :func:`delivery_between` turns two probes into a delivery word
and the extra observations.

Delivery words:

``delivered``      the page received trusted input during the step
``not_delivered``  input was dispatched and the page received none (same document, top frame)
``by_script``      only untrusted clicks arrived (browser-use's ``this.click()`` fallback)
``new_document``   the document was replaced, so the old listener cannot count; the navigation is the
                   evidence
``unknown``        no probe, or focus sits in a frame the top document's listener cannot see
``not_applicable`` the step dispatched no input (navigate, scroll, extract, done)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DELIVERY_WORDS = ("delivered", "not_delivered", "by_script", "new_document", "unknown", "not_applicable")

#: actions that dispatch pointer or keyboard input to the page
INPUT_ACTIONS = frozenset(
    {"click", "input", "send_keys", "select_dropdown", "select_dropdown_option", "upload_file", "input_text"}
)

#: Installed once per document (guarded by a flag), then read. Counts trusted and untrusted input in
#: the capture phase on window, so a handler that stops propagation cannot hide it.
PROBE_JS = """(()=>{const w=window;if(!w.__fwp){const c={t:0,u:0,s:0};w.__fwp=c;
const f=e=>{if(e.isTrusted)c.t++;else if(e.type==='click')c.u++;};
for(const k of ['mousedown','keydown','input','click'])w.addEventListener(k,f,true);
w.addEventListener('scroll',()=>{c.s++},true);}
const a=document.activeElement,c=w.__fwp;
const sig=a&&a!==document.body?(a.tagName.toLowerCase()+(a.id?'#'+a.id:'')+
(a.getAttribute('aria-label')?' '+a.getAttribute('aria-label'):a.name?' '+a.name:'')).slice(0,80):'';
return JSON.stringify({origin:performance.timeOrigin,url:location.href,trusted:c.t,untrusted:c.u,
scrolls:c.s,y:Math.round(w.scrollY),x:Math.round(w.scrollX),focus:sig,
frame_focus:!!(a&&(a.tagName==='IFRAME'||a.tagName==='FRAME'))});})()"""


@dataclass(frozen=True)
class PageProbe:
    origin: float
    url: str
    trusted: int
    untrusted: int
    scrolls: int
    x: int
    y: int
    focus: str
    frame_focus: bool = False

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> PageProbe:
        return cls(
            origin=float(data.get("origin") or 0),
            url=str(data.get("url") or ""),
            trusted=int(data.get("trusted") or 0),
            untrusted=int(data.get("untrusted") or 0),
            scrolls=int(data.get("scrolls") or 0),
            x=int(data.get("x") or 0),
            y=int(data.get("y") or 0),
            focus=str(data.get("focus") or ""),
            frame_focus=bool(data.get("frame_focus")),
        )


@dataclass(frozen=True)
class Delivery:
    word: str
    #: what else changed, in plain words: scrolling, focus, a delayed navigation
    observed: tuple[str, ...] = ()


def expects_input(action_names: list[str] | tuple[str, ...]) -> bool:
    return any(n in INPUT_ACTIONS for n in action_names)


def delivery_between(before: PageProbe | None, after: PageProbe | None, dispatched_input: bool) -> Delivery:
    """Compare the probes taken before and after one step."""
    if before is None or after is None:
        return Delivery("unknown" if dispatched_input else "not_applicable")
    if before.origin != after.origin:
        return Delivery("new_document" if dispatched_input else "not_applicable")
    observed: list[str] = []
    dy, dx = after.y - before.y, after.x - before.x
    if dy or dx:
        observed.append(
            f"scrolled {'down' if dy > 0 else 'up' if dy < 0 else 'sideways'} {abs(dy) or abs(dx)}px"
        )
    elif after.scrolls > before.scrolls:
        observed.append("an inner region scrolled")
    if after.focus != before.focus:
        observed.append(f"focus moved to {after.focus}" if after.focus else "focus left the element")
    if not dispatched_input:
        return Delivery("not_applicable", tuple(observed))
    if after.trusted > before.trusted:
        return Delivery("delivered", tuple(observed))
    if after.untrusted > before.untrusted:
        return Delivery("by_script", tuple(observed))
    if after.frame_focus or before.frame_focus:
        return Delivery("unknown", tuple(observed))
    return Delivery("not_delivered", tuple(observed))


def navigated_between_steps(last_after: PageProbe | None, next_before: PageProbe | None) -> str | None:
    """A navigation that landed after one step's read and before the next step's: the page moved
    without an action in between (a redirect, a delayed submit)."""
    if last_after is None or next_before is None:
        return None
    if next_before.origin != last_after.origin or next_before.url != last_after.url:
        return next_before.url
    return None


async def read_probe(browser_session: Any) -> PageProbe | None:
    """Install (once per document) and read the probe in the focused page; None if it cannot."""
    import json

    try:
        cdp = await browser_session.get_or_create_cdp_session()
        r = await cdp.cdp_client.send.Runtime.evaluate(
            params={"expression": PROBE_JS, "returnByValue": True}, session_id=cdp.session_id
        )
        value = (r.get("result") or {}).get("value")
        return PageProbe.from_json(json.loads(value)) if value else None
    except Exception:  # noqa: BLE001 - no probe is an honest "unknown", never a guess
        return None
