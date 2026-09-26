"""Input delivery inside the full agent loop (package C, prediction C5).

The isolated probes (E1, E2, C4) never lost a click after the saucedemo login; Q11 and Q12's agent
runs did. This runs the real runner on the real arm and records, per run, three things side by side:

- what browser-use sends: every `Input.dispatchMouseEvent` (type, x, y, CDP session) and every
  JavaScript `this.click()` fallback, with the element browser-use meant to click;
- what the page receives: every mousedown and click in the top document (trusted or not, target id,
  coordinates), from a listener installed once per document;
- what changed: the cart badge after each step.

    uv run python scripts/diag_agent_loop.py --task ls-add-backpack-cart --launches 8 \
        --out results/c-agent-loop-20260926

Costs System 2 calls (Muse Spark over the Meta Model API), as a live run does.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

LISTEN = (
    "(()=>{if(!window.__fw){window.__fw=[];const f=e=>window.__fw.push([e.type,e.isTrusted,"
    "(e.target&&(e.target.id||e.target.tagName)||'').slice(0,60),Math.round(e.clientX),"
    "Math.round(e.clientY),Math.round(performance.now())]);"
    "for(const t of ['mousedown','click'])window.addEventListener(t,f,true);}"
    "return performance.timeOrigin})()"
)
DRAIN = (
    "(()=>{const h=window.__fw||[];window.__fw=[];return JSON.stringify({origin:performance.timeOrigin,"
    "url:location.pathname,badge:(document.querySelector('.shopping_cart_badge')||{}).textContent||'',"
    "events:h})})()"
)

LOG: list[dict] = []
CURRENT: dict = {"run": None, "step": 0}


def rec(kind: str, **fields) -> None:
    LOG.append(
        {"run": CURRENT["run"], "step": CURRENT["step"], "t": round(time.time(), 3), "kind": kind} | fields
    )


def install() -> None:
    from browser_use.browser.session import BrowserSession
    from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog
    from cdp_use.cdp.input.library import InputClient
    from cdp_use.cdp.runtime.library import RuntimeClient

    from evals import runner

    send_mouse = InputClient.dispatchMouseEvent

    async def dispatch(self, params, session_id=None):
        if params.get("type") != "mouseMoved":
            rec(
                "sent",
                type=params.get("type"),
                x=round(params.get("x", 0)),
                y=round(params.get("y", 0)),
                sid=(session_id or "")[-8:],
            )
        return await send_mouse(self, params=params, session_id=session_id)

    InputClient.dispatchMouseEvent = dispatch

    call_on = RuntimeClient.callFunctionOn

    async def call_function_on(self, params, session_id=None):
        if "this.click()" in (params.get("functionDeclaration") or ""):
            rec("js_click", sid=(session_id or "")[-8:])
        return await call_on(self, params=params, session_id=session_id)

    RuntimeClient.callFunctionOn = call_function_on

    impl = DefaultActionWatchdog._click_element_node_impl

    async def click_impl(self, element_node):
        a = element_node.attributes or {}
        rec(
            "click_target",
            tag=element_node.tag_name,
            id=a.get("id", ""),
            backend=element_node.backend_node_id,
            target=(element_node.target_id or "")[-8:],
        )
        out = await impl(self, element_node)
        rec("click_returned", value=out)
        return out

    DefaultActionWatchdog._click_element_node_impl = click_impl

    async def listen(session: BrowserSession) -> None:
        try:
            cdp = await session.get_or_create_cdp_session()
            r = await cdp.cdp_client.send.Runtime.evaluate(
                params={"expression": LISTEN, "returnByValue": True}, session_id=cdp.session_id
            )
            rec(
                "listen",
                origin=r.get("result", {}).get("value"),
                sid=cdp.session_id[-8:],
                target=(cdp.target_id or "")[-8:],
            )
        except Exception as exc:  # noqa: BLE001
            rec("listen_failed", error=f"{type(exc).__name__}: {exc}"[:160])

    navigate = BrowserSession.navigate_to

    async def navigate_to(self, url, *a, **k):
        out = await navigate(self, url, *a, **k)
        await listen(self)
        return out

    BrowserSession.navigate_to = navigate_to

    capture_call = runner._EndStateCapture.__call__

    async def capture(self, agent):
        CURRENT["step"] = agent.state.n_steps
        try:
            cdp = await agent.browser_session.get_or_create_cdp_session()
            r = await cdp.cdp_client.send.Runtime.evaluate(
                params={"expression": DRAIN, "returnByValue": True}, session_id=cdp.session_id
            )
            rec("page", **json.loads(r.get("result", {}).get("value") or "{}"))
        except Exception as exc:  # noqa: BLE001
            rec("page_failed", error=f"{type(exc).__name__}: {exc}"[:160])
        await listen(agent.browser_session)  # a real navigation starts a new document
        return await capture_call(self, agent)

    runner._EndStateCapture.__call__ = capture

    once = runner._run_task_once

    async def run_once(task, arm, *a, **k):
        CURRENT["run"], CURRENT["step"] = f"{task.id}/{arm}/{len({e['run'] for e in LOG})}", 0
        return await once(task, arm, *a, **k)

    runner._run_task_once = run_once


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", action="append", required=True)
    ap.add_argument("--arm", default="guarded")
    ap.add_argument("--launches", type=int, default=8)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    install()
    from evals import runner

    out = Path(args.out)
    for k in range(args.launches):
        argv = ["--split", "live-dev", "--live", "--arm", args.arm, "--out", str(out / f"launch-{k}")]
        for t in args.task:
            argv += ["--task", t]
        runner.main(argv)
        (out / "input-log.jsonl").write_text("".join(json.dumps(e) + "\n" for e in LOG))


if __name__ == "__main__":
    main()
