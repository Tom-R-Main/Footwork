"""B1 spike: DualProcessAgent with a scripted always-S1 policy.

Runs four short tasks against a local page and reports where the upstream seams
resist. No model is called: the LLM double raises if System 2 is reached, and the
fourth task deliberately escalates to prove that path is reachable.
"""

from __future__ import annotations

import asyncio
import http.server
import json
import logging
import sys
import tempfile
import threading
from pathlib import Path

from browser_use.agent.views import AgentOutput
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.views import BrowserStateSummary
from jevdual.agent import DualProcessAgent
from jevdual.testing import RefusingLLM

logging.basicConfig(level=logging.WARNING)
logging.getLogger("jevdual").setLevel(logging.INFO)

SITE = {
    "/": """<html><head><title>Spike Home</title></head><body>
<h1>Spike Home</h1><nav><a href="/about.html">About</a> <a href="/list.html">List</a></nav>
<form action="/search.html" method="get"><input type="search" name="q" placeholder="Search here"></form>
</body></html>""",
    "/about.html": "<html><head><title>About</title></head><body><h1>About page</h1><p>Reached about.</p><a href='/'>Home</a></body></html>",
    "/search.html": "<html><head><title>Results</title></head><body><h1>Results</h1><p>You searched.</p></body></html>",
    "/list.html": "<html><head><title>List</title></head><body><h1>Long list</h1>"
    + "".join(f"<p>Row {i}</p>" for i in range(200))
    + "<a href='/'>Bottom home link</a></body></html>",
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        body = SITE.get(path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_port}", srv.shutdown


def find_index(state: BrowserStateSummary, *, text: str | None = None, placeholder: str | None = None) -> int | None:
    for idx, node in state.dom_state.selector_map.items():
        attrs = node.attributes or {}
        if placeholder and attrs.get("placeholder") == placeholder:
            return idx
        if text:
            label = (node.ax_node.name if node.ax_node and node.ax_node.name else "") or node.get_all_children_text()
            if text.lower() in (label or "").lower():
                return idx
    return None


class ScriptedPolicy:
    """Plays a fixed list of intents; returns None (escalate) for the 'escalate' intent."""

    def __init__(self, script):
        self.script = list(script)
        self.log = []

    async def decide(self, agent: DualProcessAgent, state: BrowserStateSummary) -> AgentOutput | None:
        step = agent.state.n_steps
        intent = self.script[min(step - 1, len(self.script) - 1)] if self.script else ("done", "no script")
        kind = intent[0]
        if kind == "escalate":
            return None
        if kind == "click":
            idx = find_index(state, text=intent[1])
            action = agent.ActionModel(click={"index": idx})
        elif kind == "input":
            idx = find_index(state, placeholder=intent[1])
            action = agent.ActionModel(input={"index": idx, "text": intent[2]})
        elif kind == "enter":
            action = agent.ActionModel(send_keys={"keys": "Enter"})
        elif kind == "scroll":
            action = agent.ActionModel(scroll={"down": True, "pages": 1.0})
        elif kind == "done":
            action = agent.ActionModel(done={"text": intent[1], "success": True})
        else:
            raise ValueError(kind)
        line = f"S1 step {step}: {kind} {intent[1:]} on {state.url}"
        self.log.append(line)
        return agent.AgentOutput(action=[action], memory=line)


async def run_task(base: str, name: str, task: str, script, outdir: Path, max_steps: int):
    policy = ScriptedPolicy(script)
    gif = outdir / f"{name}.gif"
    conv = outdir / f"{name}_conv"
    profile = BrowserProfile(headless=True)
    agent = DualProcessAgent(
        task=task,
        llm=RefusingLLM(),
        browser_profile=profile,
        s1_policy=policy,
        generate_gif=str(gif),
        save_conversation_path=str(conv),
        use_vision=True,
    )
    await agent.browser_session.start()
    await agent.browser_session.navigate_to(base + "/")
    findings = {}
    try:
        history = await agent.run(max_steps=max_steps)
    except Exception as exc:  # the escalation task should not raise; record if it does
        findings["run_raised"] = repr(exc)
        history = agent.history
    findings.update(
        {
            "s1_steps": agent.s1_steps,
            "s2_steps": agent.s2_steps,
            "n_history": len(history.history),
            "is_done": history.is_done(),
            "final_url": history.history[-1].state.url if history.history else None,
            "interacted_elements": [
                [None if e is None else (e.node_name, (e.attributes or {}).get("href") or (e.attributes or {}).get("placeholder")) for e in h.state.interacted_element]
                for h in history.history
            ],
            "model_output_memory": [h.model_output.memory if h.model_output else None for h in history.history],
            "errors": [r.error for h in history.history for r in h.result if r.error],
            "gif_exists": gif.exists() and gif.stat().st_size > 0,
            "conversation_files": sorted(p.name for p in conv.glob("*")) if conv.exists() else [],
            "s2_context_has_s1_memory": any(
                "S1 step" in (m.text if hasattr(m, "text") else str(getattr(m, "content", "")))
                for m in agent._message_manager.get_messages()
            ),
        }
    )
    await agent.close()
    return findings


async def main():
    base, stop = serve()
    outdir = Path(tempfile.mkdtemp(prefix="spike_b1_"))
    results = {}
    results["t1_click_done"] = await run_task(
        base, "t1", "Open the About page", [("click", "About"), ("done", "on about")], outdir, 4
    )
    results["t2_type_enter"] = await run_task(
        base,
        "t2",
        "Search for hello",
        [("input", "Search here", "hello"), ("enter",), ("done", "searched")],
        outdir,
        5,
    )
    results["t3_scroll"] = await run_task(
        base, "t3", "Scroll the list", [("click", "List"), ("scroll",), ("scroll",), ("done", "scrolled")], outdir, 6
    )
    results["t4_escalate"] = await run_task(base, "t4", "Escalate to S2", [("escalate",)], outdir, 1)
    stop()
    print(json.dumps(results, indent=1, default=str))
    (outdir / "results.json").write_text(json.dumps(results, indent=1, default=str))
    print("outdir", outdir)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
