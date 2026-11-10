"""Owned loopback native Chrome acceptance, with server-side save/reload evidence.

Run only on an unlocked Mac with existing Accessibility permission::

    python scripts/native_form_acceptance.py run --out results/native-form-live-UNIQUE \
        --footwork /absolute/path/to/venv/bin/footwork

``run`` launches one Chrome process using a new profile under --out, drives the real public native
CLI, then terminates only that owned process. It never attaches to personal Chrome. All mutations
use ``footwork do``; HTTP reads inspect the independent fixture ledger. --no-judge is deliberately
used only for this harmless localhost fixture. ``serve`` exposes the fixture for manual inspection
and prints exact URL/title metadata; it launches no browser. No live DNS is involved.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DOMAINS = ("alpha.example.test", "beta.example.test")
EXPECTED = [f"ns{i}.example.test" for i in range(1, 5)]

PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>__TITLE__</title>
<link rel="icon" href="data:,"><style>
body{font:14px system-ui;margin:12px;max-width:1160px}h1{font-size:20px;margin:4px 0}
button,a{cursor:pointer}button{padding:5px 9px;margin:3px}input{padding:5px;margin:3px;width:240px}
#domains{display:flex;gap:30px}#domains>div{border:1px solid #aaa;padding:8px}
#reference-links{display:grid;grid-template-columns:repeat(18,1fr);gap:2px;font-size:10px;margin:8px 0}
#reference-links a{display:block;line-height:16px}#fields{display:grid;grid-template-columns:1fr 1fr}
#combo{display:inline-block;border:1px solid #777;padding:5px;min-width:230px}
[role=option]{padding:6px;cursor:pointer}[role=option]:hover{background:#ddf}
[hidden]{display:none!important}#status{min-height:24px}
</style></head><body><h1>Native nameserver fixture</h1>
<p>Owned localhost test. All domains and nameservers are synthetic.</p>
<div id="domains"></div><div>
<button id="reorder">Reorder domain rows</button>
<button id="add">ADD NAMESERVER</button><button id="remove">Remove first nameserver</button>
<button id="save">Save DNS changes</button><button id="reload">Reload persisted form</button>
</div><div id="reference-links">__LINKS__</div>
<section aria-label="Nameserver settings"><h2 id="heading">Select a domain</h2>
<div id="combo" role="combobox" aria-label="Nameserver mode" aria-expanded="false" tabindex="0">
<span id="mode-text">Basic DNS</span><div id="choices" role="listbox" aria-label="DNS choices" hidden>
<div role="option" aria-selected="true" tabindex="0" data-mode="Basic DNS">Basic DNS</div>
<div role="option" aria-selected="false" tabindex="0" data-mode="Web Hosting DNS">Web Hosting DNS</div>
<div role="option" aria-selected="false" tabindex="0" data-mode="Custom DNS">Custom DNS</div>
</div></div><div id="fields"></div></section><p id="status" role="status">Ready</p>
<script>
const initial=__INITIAL__, names=Object.keys(initial.domains);
let selected=initial.selected, mode='Basic DNS', fields=[], counter=0, queue=Promise.resolve();
const byId=id=>document.getElementById(id), status=text=>byId('status').textContent=text;
function post(path,payload){queue=queue.then(async()=>{
 const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 if(!r.ok)throw Error(await r.text());return r.json();});return queue;}
function event(kind,extra={}){return post('/event',{kind,domain:selected,...extra});}
function renderDomains(){byId('domains').replaceChildren();for(const domain of names){
 const row=document.createElement('div');row.setAttribute('role','group');row.setAttribute('aria-label',domain);
 const text=document.createElement('span');text.textContent=domain+' ';
 const link=document.createElement('a');link.href='';link.textContent='MANAGE';
 link.onclick=e=>{e.preventDefault();selected=domain;loadDomain();event('manage',{backing_domain:domain});};
 row.append(text,link);byId('domains').append(row);}}
function loadDomain(){const saved=initial.domains[selected];mode=saved.mode;
 fields=saved.fields.map(f=>({...f}));counter=Math.max(0,...fields.map(f=>+f.id.split(':').pop()));
 byId('heading').textContent='Managing '+selected;renderFields();renderMode();}
function renderMode(){byId('mode-text').textContent=mode;
 for(const option of byId('choices').children)option.setAttribute('aria-selected',String(option.dataset.mode===mode));}
function renderFields(){byId('fields').replaceChildren();if(mode!=='Custom DNS')return;
 fields.forEach((field,index)=>{const input=document.createElement('input');input.type='text';
 input.placeholder='Nameserver '+(index+1);input.value=field.value;input.autocomplete='off';
 input.dataset.backing=field.id;input.oninput=()=>{field.value=input.value;
 event('input',{field_id:field.id,placeholder:input.placeholder,value:input.value});};
 byId('fields').append(input);});}
byId('combo').onclick=()=>{const open=byId('choices').hidden;byId('choices').hidden=!open;
 byId('combo').setAttribute('aria-expanded',String(open));};
for(const option of byId('choices').children)option.onclick=e=>{e.stopPropagation();if(!selected)return;
 mode=option.dataset.mode;byId('choices').hidden=true;byId('combo').setAttribute('aria-expanded','false');
 renderMode();renderFields();event('mode',{mode});};
byId('add').onclick=()=>{if(!selected||mode!=='Custom DNS')return;
 const field={id:selected+':'+(++counter),value:''};fields.push(field);renderFields();event('add',{field_id:field.id});};
byId('remove').onclick=()=>{if(!selected||fields.length<2)return;
 const removed=fields.shift();renderFields();event('remove',{field_id:removed.id});};
byId('reorder').onclick=()=>{names.reverse();renderDomains();event('reorder',{order:[...names]});};
byId('save').onclick=async()=>{if(!selected)return;
 const result=await post('/save',{domain:selected,mode,fields:fields.map(f=>({...f}))});
 status('Saved version '+result.version+' for '+selected);};
byId('reload').onclick=async()=>{await event('reload');location.reload();};
renderDomains();if(selected)loadDomain();
</script></body></html>"""


class Fixture:
    """The persistence oracle has no dependency on Footwork's observations or receipts."""

    def __init__(self, root: Path):
        self.root = root
        self.title = f"Footwork native form {uuid.uuid4().hex[:12]}"
        self.lock = threading.Lock()
        self.version = 0
        self.selected = None
        self.domains = {
            domain: {"mode": "Basic DNS", "fields": [{"id": f"{domain}:{i}", "value": ""} for i in (1, 2)]}
            for domain in DOMAINS
        }
        self.events: list[dict] = []

    def record(self, payload: dict) -> dict:
        record = {"sequence": len(self.events) + 1, "time": time.time(), **payload}
        self.events.append(record)
        with (self.root / "server-ledger.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")
        return record

    def state(self) -> dict:
        with self.lock:
            return copy.deepcopy({"version": self.version, "selected": self.selected, "domains": self.domains, "events": self.events})

    def page(self, *, record_load: bool = True) -> bytes:
        with self.lock:
            if record_load:
                self.record({"kind": "page_load", "version": self.version, "selected": self.selected})
            initial = json.dumps({"domains": self.domains, "selected": self.selected}).replace("<", "\\u003c")
        links = "".join(f'<a href="#" onclick="event.preventDefault()">Reference {i:03d}</a>' for i in range(180))
        return PAGE.replace("__TITLE__", html.escape(self.title)).replace("__INITIAL__", initial).replace("__LINKS__", links).encode()

    def post(self, path: str, payload: dict) -> dict:
        with self.lock:
            domain = payload.get("domain")
            if domain not in self.domains:
                raise ValueError("unknown fixture domain")
            if path == "/event":
                if payload.get("kind") not in {"manage", "input", "mode", "add", "remove", "reorder", "reload"}:
                    raise ValueError("unknown fixture event")
                if payload["kind"] == "manage":
                    if payload.get("backing_domain") != domain:
                        raise ValueError("domain identity mismatch")
                    self.selected = domain
                self.record(payload)
                return {"ok": True}
            if path != "/save":
                raise ValueError("unknown endpoint")
            fields = payload.get("fields")
            if payload.get("mode") != "Custom DNS" or not isinstance(fields, list) or not 2 <= len(fields) <= 8:
                raise ValueError("invalid fixture form")
            ids = [field.get("id") for field in fields if isinstance(field, dict)]
            if len(ids) != len(fields) or len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i.startswith(domain + ":") for i in ids):
                raise ValueError("invalid field identity")
            if any(set(f) != {"id", "value"} or not isinstance(f["value"], str) or len(f["value"]) > 256 for f in fields):
                raise ValueError("invalid field value")
            self.version += 1
            self.domains[domain] = copy.deepcopy({"mode": "Custom DNS", "fields": fields})
            self.record({"kind": "save", "version": self.version, "domain": domain, "fields": fields})
            (self.root / "persisted.json").write_text(json.dumps({"version": self.version, "domains": self.domains}, indent=2))
            return {"ok": True, "version": self.version}


def server_for(fixture: Fixture, port: int = 0) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status: int, body: bytes, mime: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/":
                self.reply(200, fixture.page(), "text/html; charset=utf-8")
            elif self.path == "/state":
                self.reply(200, json.dumps(fixture.state()).encode())
            else:
                self.reply(404, b'{}')

        def do_POST(self) -> None:
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 16384:
                    raise ValueError("invalid body size")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise TypeError("body must be an object")
                result = fixture.post(self.path, payload)
            except (ValueError, TypeError, KeyError) as exc:
                self.reply(400, json.dumps({"error": str(exc)}).encode())
            else:
                self.reply(200, json.dumps(result).encode())

        def log_message(self, *_: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


class Acceptance:
    def __init__(self, root: Path, executable: str, url: str, title: str, pid: int):
        self.root, self.executable, self.url, self.title, self.pid = root, executable, url, title, pid
        self.index = 0
        self.session = root / "session"
        self.checks: list[str] = []

    def oracle(self) -> dict:
        with urlopen(self.url + "state", timeout=5) as response:
            return json.load(response)

    def wait(self, predicate, description: str) -> dict:
        until = time.monotonic() + 10
        while time.monotonic() < until:
            state = self.oracle()
            if predicate(state):
                return state
            time.sleep(0.1)
        raise AssertionError(f"fixture did not report {description}")

    def command(self, *words: str, session: Path | None = None, expected: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess:
        self.index += 1
        argv = [self.executable, *words, "--session", str(session or self.session)]
        if words[0] == "do":
            argv += ["--settle", "0.3", "--no-judge"]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
        (self.root / f"command-{self.index:02d}.json").write_text(json.dumps({
            "argv": argv, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
        }, indent=2))
        print(json.dumps({"command": self.index, "operation": words[:3], "returncode": result.returncode}), flush=True)
        if result.returncode not in expected:
            raise AssertionError(f"command {self.index} returned {result.returncode}: {result.stderr[-500:]}")
        return result

    def start(self, session: Path | None = None) -> None:
        self.command(
            "start", "Exercise only the owned synthetic native form", "--app", "Google Chrome",
            "--pid", str(self.pid), "--window", self.title, "--authority", str(self.root / "authority.sqlite"),
            "--native-url", self.url, "--native-title", self.title, session=session,
        )

    def metadata(self) -> dict:
        return json.loads((self.session / "session.json").read_text())

    def records(self) -> list[dict]:
        return [json.loads(line) for line in (self.session / "session.jsonl").read_text().splitlines()]

    def refusal(self, selector: str, code: str) -> dict:
        attempt = next(r for r in reversed(self.records()) if r.get("kind") == "attempted_action")
        assert attempt["requested_selector"] == selector and attempt["code"] == code, attempt
        assert attempt["dispatched"] is False
        return attempt

    def candidate(self, label: str, role: str | None = None) -> dict:
        found = [c for c in self.metadata()["last_candidates"] if c["label"] == label and (role is None or c["role"] == role)]
        if len(found) != 1:
            raise AssertionError(f"expected one {role or ''} candidate {label!r}, found {len(found)}")
        return found[0]

    def exercise(self) -> dict:
        self.start()
        rows = [c for c in self.metadata()["last_candidates"] if c["label"] == "MANAGE"]
        assert {c["section"] for c in rows} == set(DOMAINS), rows
        self.command("do", "click", "MANAGE", expected=(4,))
        self.refusal("MANAGE", "target_ambiguous")
        assert not any(e["kind"] == "manage" for e in self.oracle()["events"])
        self.checks.append("unqualified MANAGE refused and audited without any domain event")
        self.command("do", "click", f"section:{DOMAINS[0]}::link:MANAGE")
        self.wait(lambda s: s["selected"] == DOMAINS[0], "alpha domain selection")
        self.checks.append("repeated MANAGE selected independent alpha backing domain")
        selected = next(c for c in rows if c["section"] == DOMAINS[0])
        mutation_session = self.root / "mutation-session"
        self.start(mutation_session)
        self.command("do", "click", "Reorder domain rows", session=mutation_session)
        self.wait(lambda s: any(e["kind"] == "reorder" for e in s["events"]), "domain row reorder")
        before = len(self.oracle()["events"])
        self.command("do", "click", str(selected["id"]), expected=(0, 4))
        events = self.oracle()["events"][before:]
        assert all(e.get("backing_domain") == DOMAINS[0] for e in events if e["kind"] == "manage")
        self.command("do", "click", f"section:{DOMAINS[0]}::link:MANAGE")
        self.checks.append("reordered rows rebound alpha or refused without beta dispatch")
        self.command("do", "click", "Nameserver mode")
        self.candidate("Custom DNS")
        assert self.metadata()["native_menu_cap"] == 160
        observation = next(r for r in reversed(self.records()) if r.get("kind") == "observation")
        assert observation["coverage"]["omitted"].get("cap", 0) > 0, observation["coverage"]
        offered = {c["label"] for c in self.metadata()["last_candidates"]}
        excluded = next(f"Reference {i:03d}" for i in range(180) if f"Reference {i:03d}" not in offered)
        self.command("do", "click", excluded, expected=(4,))
        assert self.refusal(excluded, "selector_not_observed")["coverage"]["omitted"]["cap"] > 0
        self.checks.append("real reference link excluded by160budget refused as not observed and audited")
        self.command("do", "click", "Custom DNS")
        self.wait(lambda s: any(e["kind"] == "mode" and e.get("mode") == "Custom DNS" for e in s["events"]), "Custom DNS mode")
        for i in (1, 2):
            field = self.candidate(f"Nameserver {i}", "textbox")
            assert field["placeholder"] == f"Nameserver {i}" and field["value"] in (None, "")
        self.checks.append("late popup option exposed at default budget and empty placeholders retained separately")
        self.command("do", "click", "ADD NAMESERVER")
        self.command("do", "click", "ADD NAMESERVER")
        selected = self.candidate("Nameserver 2", "textbox")
        self.command("do", "click", "Remove first nameserver", session=mutation_session)
        self.wait(lambda s: any(e["kind"] == "remove" and e.get("field_id") == DOMAINS[0] + ":1" for e in s["events"]), "first field removal")
        before = len(self.oracle()["events"])
        self.command("do", "type", str(selected["id"]), "must-not-send.example.test", expected=(0, 4))
        assert not any(e["kind"] == "input" for e in self.oracle()["events"][before:])
        self.command("look")
        self.command("do", "click", "ADD NAMESERVER")
        self.checks.append("removed and renumbered fields refused stale pending input")
        for i, value in enumerate(EXPECTED, 1):
            self.command("do", "type", f"Nameserver {i}", value)
            self.wait(lambda s, value=value: any(e["kind"] == "input" and e.get("value") == value for e in s["events"]), f"field {i} input")
        state = self.oracle()
        assert not any(e.get("value") == "must-not-send.example.test" for e in state["events"])
        final_inputs = {e["field_id"]: e["value"] for e in state["events"] if e["kind"] == "input"}
        assert final_inputs == {f"{DOMAINS[0]}:{i + 1}": value for i, value in enumerate(EXPECTED, 1)}, final_inputs
        self.command("do", "click", "Save DNS changes")
        saved = self.wait(lambda s: s["version"] == 1, "server persistence")
        assert [f["value"] for f in saved["domains"][DOMAINS[0]]["fields"]] == EXPECTED
        assert {f["id"]: f["value"] for f in saved["domains"][DOMAINS[0]]["fields"]} == final_inputs
        assert saved["domains"][DOMAINS[1]]["mode"] == "Basic DNS"
        assert all(f["value"] == "" for f in saved["domains"][DOMAINS[1]]["fields"])
        self.command("do", "click", "Reload persisted form")
        self.wait(lambda s: any(e["kind"] == "page_load" and e["version"] == 1 for e in s["events"]), "page reload after save")
        self.command("look")
        assert [self.candidate(f"Nameserver {i}", "textbox")["value"] for i in range(1, 5)] == EXPECTED
        self.checks.append("four backing fields saved once and reloaded from server; beta unchanged")
        return {"passed": True, "checks": self.checks, "server": self.oracle(), "commands": self.index}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("serve", "run"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--footwork", default=str(Path(sys.executable).with_name("footwork")))
    parser.add_argument("--chrome", default=CHROME)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=False)
    fixture = Fixture(root)
    server = server_for(fixture, args.port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    metadata = {"url": url, "title": fixture.title, "server_pid": os.getpid()}
    (root / "fixture.json").write_text(json.dumps(metadata, indent=2))
    (root / "fixture.html").write_bytes(fixture.page(record_load=False))
    print(json.dumps(metadata), flush=True)
    browser = None
    try:
        if args.mode == "serve":
            while True:
                time.sleep(1)
        if sys.platform != "darwin" or urlsplit(url).hostname != "127.0.0.1":
            raise RuntimeError("live run requires macOS and the owned loopback fixture")
        with (root / "chrome.log").open("w") as log:
            browser = subprocess.Popen([
                args.chrome, f"--user-data-dir={root / 'chrome-profile'}", "--no-first-run",
                "--no-default-browser-check", "--disable-background-networking", "--disable-sync",
                "--disable-component-update", "--force-renderer-accessibility", "--new-window", url,
            ], stdout=log, stderr=log)
            metadata["chrome_pid"] = browser.pid
            (root / "fixture.json").write_text(json.dumps(metadata, indent=2))
            until = time.monotonic() + 30
            while time.monotonic() < until:
                if browser.poll() is not None:
                    raise RuntimeError("owned Chrome exited before native binding")
                if any(e["kind"] == "page_load" for e in fixture.state()["events"]):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("owned Chrome did not load fixture")
            time.sleep(1)
            result = Acceptance(root, args.footwork, url, fixture.title, browser.pid).exercise()
            (root / "acceptance.json").write_text(json.dumps(result, indent=2))
            return 0
    except KeyboardInterrupt:
        return 130
    except (AssertionError, RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        (root / "acceptance.json").write_text(json.dumps({"passed": False, "error": f"{type(exc).__name__}: {exc}", "server": fixture.state()}, indent=2))
        print(f"acceptance failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if browser is not None and browser.poll() is None:
            browser.terminate()
            try:
                browser.wait(timeout=15)
            except subprocess.TimeoutExpired:
                browser.kill()
                browser.wait(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
