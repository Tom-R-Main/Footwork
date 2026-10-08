"""Native CLI proof using owned AppKit/loopback fixtures; no keys, remote calls or action dispatch."""
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import httpx
from jevdual import cli, visual_native
from jevdual.decisions import ENDPOINT, MODEL
from jevdual.desktop_s2 import NativeS2
from jevdual.native import NativeBridge
from jevdual.session import SessionState
from jevdual.visual_decisions import VisualDecisionsClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "runs/visual-checks-native-20261008"
RESULTS = ROOT / "results/visual-checks-native-20261008"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2))

class Server(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        data = json.loads(raw)
        self.server.requests += 1
        images = []
        assert self.path == "/v1/decisions"
        content = data["input"][0]["content"]
        assert len(content) == 3 and data["model"] == MODEL
        for image in content[1:]:
            with Image.open(io.BytesIO(base64.b64decode(image["image_url"].split(",", 1)[1]))) as opened:
                assert opened.format == "PNG"
                images.append({"dimensions": opened.size,
                               "sha256": hashlib.sha256(base64.b64decode(image["image_url"].split(",", 1)[1])).hexdigest()})
                opened.verify()
        mode = self.server.mode
        self.server.receipts.append({"mode": mode, "body_sha256": hashlib.sha256(raw).hexdigest(),
                                     "body_bytes": len(raw), "images": images, "model": data["model"]})
        if mode == "source_changed":
            self.server.asset.write_bytes(self.server.asset.read_bytes() + b"source-revision-changed")
        elif mode == "generation_changed":
            state = SessionState.load(self.server.session)
            state.visual_generation = "different-generation"
            state.save()
        elif mode == "timeout":
            time.sleep(1.5)
        answer = {"type": "predicate", "name": "required", "probability": .97}
        if mode == "refusal":
            answer = {"type": "refusal", "name": "required", "reason": "insufficient evidence"}
        body = json.dumps({"model": MODEL, "answers": [answer], "usage": {"input_tokens": 100}}).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

class LoopbackTransport(httpx.AsyncBaseTransport):
    def __init__(self, port):
        self.port = port

    async def handle_async_request(self, request):
        assert str(request.url) == ENDPOINT, "unexpected external endpoint"
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
            response = await client.post(f"http://127.0.0.1:{self.port}/v1/decisions", content=request.content)
            return httpx.Response(response.status_code, content=response.content, request=request)

def invoke(*args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(list(args))
    return {"argv": list(args), "exit": code, "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}

def latest(session):
    receipts = [p for p in (session / "visual").glob("*.json") if p.name != "budget.json"]
    path = max(receipts, key=lambda p: p.stat().st_mtime_ns)
    return path, json.loads(path.read_text())

def main():
    global PRIVATE, RESULTS
    if len(sys.argv) > 1:
        attempt = sys.argv[1]
        assert len(sys.argv) == 2 and attempt.replace("-", "").isalnum(), "safe attempt name required"
        PRIVATE, RESULTS = PRIVATE / attempt, RESULTS / attempt
    assert not PRIVATE.exists() and not RESULTS.exists(), "use fresh evidence directories"
    PRIVATE.mkdir(parents=True)
    RESULTS.mkdir(parents=True)
    fixture = PRIVATE / "fixture"
    fixture.mkdir()
    source = ROOT / "results/d3-capture-20261008/native/native-crop_boundary-supported"
    for filename in ("view.png", "config.json"):
        shutil.copyfile(source / filename, fixture / filename)
    document = PRIVATE / "document-fixture"
    document.mkdir()
    doc_source = ROOT / "results/d3-capture-20261008/native/native-document_identity-supported"
    for filename in ("view.png", "config.json", "source-0.pdf", "source-1.pdf", "source-2.pdf"):
        shutil.copyfile(doc_source / filename, document / filename)
    subprocess.run(["pdftoppm", "-singlefile", "-f", "1", "-l", "1", "-r", "96", "-png",
                    str(document / "source-0.pdf"), str(document / "reference")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes = []
    for scene in (fixture, document):
        with (scene / "app.log").open("w") as log:
            processes.append(subprocess.Popen([sys.executable, str(ROOT / "evals/visual/d3/native/app.py"), str(scene)],
                                              stdout=log, stderr=log))
    server = ThreadingHTTPServer(("127.0.0.1", 0), Server)
    server.requests, server.mode, server.receipts = 0, "valid", []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original_provider, original_capture = visual_native.make_provider, visual_native.capture_request
    captured = []
    action_calls = []
    actions = {name: getattr(NativeBridge, name) for name in ("act", "key", "hotkey", "menu")}

    async def forbid_action(*args, **kwargs):
        action_calls.append(True)
        raise AssertionError("visual command dispatched an action")

    for name in actions:
        setattr(NativeBridge, name, forbid_action)

    async def capture(*args, **kwargs):
        answer = await original_capture(*args, **kwargs)
        captured.append(answer)
        return answer

    def provider():
        client = httpx.AsyncClient(transport=LoopbackTransport(server.server_port))
        return VisualDecisionsClient("run-owned-fixture-key-not-a-secret", client=client)

    visual_native.make_provider, visual_native.capture_request = provider, capture
    checks, commands = {}, []
    proof = {"provider_boundary": "production client, official URL intercepted into owned loopback server",
             "semantic_accuracy": "unqualified; fixed provider predicates", "application_discovery": "unqualified",
             "reference_recipe": "pdftoppm page 1, 96 dpi PNG; run-owned source-0.pdf",
             "reference_resource_sha256": sha(document / "source-0.pdf"),
             "fixture_binding": "ready pid/window supplied; real CLI and Cua SDK observations",
             "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), *[
                 ROOT / f"python/jevdual/{name}.py" for name in (
                     "visual_checks", "visual_decisions", "visual_native", "native", "session", "cli", "desktop_s2")]]}}
    try:
        for _ in range(100):
            if all((scene / "ready.json").exists() for scene in (fixture, document)):
                break
            assert all(app.poll() is None for app in processes), "fixture failed to launch"
            time.sleep(.1)
        readiness = {scene: json.loads((scene / "ready.json").read_text()) for scene in (fixture, document)}
        proof["fixture_readiness"] = list(readiness.values())

        def setup(name, role="document_reference_match"):
            session = PRIVATE / name
            (session / "assets").mkdir(parents=True)
            asset = session / "assets/source.png"
            scene = fixture if role == "crop_subject_containment" else document
            ready = readiness[scene]
            shutil.copyfile(scene / ("view.png" if scene == fixture else "reference.png"), asset)
            SessionState(str(session), "Python", ready["pid"], ready["window_id"], "Advisory visual QA").save()
            commands.append(invoke("look", "--session", str(session)))
            assert commands[-1]["exit"] == 0
            state = SessionState.load(session)
            label = "Apply proposed crop" if scene == fixture else "Select Candidate A"
            target = next(c["id"] for c in state.last_candidates if c["label"] == label)
            spec = {"version": 1, "role": role, "criterion": "Compare the offered document preview to the supplied reference page",
                    "criterion_version": "qa-v1", "target": target}
            image = {"path": "assets/source.png", "sha256": sha(asset), "resource_id": "qa-source",
                     "revision": "qa-v1", "page": 1, "render_recipe": ("supplied_png" if scene == fixture
                                                                           else "pdftoppm-96dpi-page-1")}
            if role == "document_reference_match":
                spec["reference"] = image
            else:
                # NSImageView fits the full source proportionally; derive its global coordinates.
                commands.append(invoke("inspect-target", str(target), "--session", str(session),
                                       "--postcondition", "Read-only source canvas geometry"))
                assert commands[-1]["exit"] == 0
                inspection = max((session / "inspection").glob("*.json"), key=lambda p: p.stat().st_mtime_ns)
                from jevdual.visual_evidence import Bounds
                v = Bounds(**json.loads(inspection.read_text())["viewport"])
                with Image.open(asset) as opened:
                    w, h = opened.size
                scale = min(620 / w, 316 / h)
                spec.update(source=image, rectangle=[220, 45, 180, 235], orientation="upright",
                            displayed_bounds=[v.x + 20 + (620 - w * scale) / 2,
                                              v.y + 90 + (316 - h * scale) / 2, w * scale, h * scale],
                            criterion="Retain the whole visible subject inside the supplied crop")
            write(session / "request.json", spec)
            return session, asset

        def run(session, mode="valid", extra=(), expect="valid"):
            server.mode, server.session, server.asset = mode, session, session / "assets/source.png"
            before = server.requests
            commands.append(invoke("visual-check", "--session", str(session), "--request", "request.json", *extra))
            path, record = latest(session)
            assert record["result"]["status"] == expect, record["result"]
            assert record["execution_authority"] is False
            assert record["escalation"]["image_visible_to_s2"] is False
            assert "token" not in record["request"]["evidence"]["capture"]["target"]
            shot = path.parent / record["screenshot"]
            with Image.open(shot) as opened:
                opened.verify()
            checks[session.name + "-" + mode + "-" + expect] = {"status": expect, "calls": server.requests - before,
                                                                  "receipt": str(path.relative_to(ROOT))}
            if expect == "budget_exhausted":
                assert server.requests == before
            return path, record

        explicit = ("--provider", "decisions", "--disclose")
        session, _ = setup("prepare")
        _, record = run(session, expect="unavailable")
        assert record["result"]["reason"] == "provider_unconfigured" and server.requests == 0
        for role in ("document_reference_match", "crop_subject_containment"):
            session, _ = setup(role, role)
            path, record = run(session, extra=explicit)
            assert record["result"]["p"] == .97 and SessionState.load(session).last_visual_check
            shutil.copyfile(path, RESULTS / f"{role}.json")
            shutil.copyfile(path.parent / record["screenshot"], RESULTS / f"{role}.png")
            request, nm, _ = captured[-1]
            from jevdual.visual_checks import VisualCheckResult
            values = dict(record["result"])
            values["phases_ms"] = tuple(tuple(pair) for pair in values["phases_ms"])
            answer = VisualCheckResult(**{k: v for k, v in values.items()
                                          if k not in ("advisory_only", "execution_authority")})
            agent = SimpleNamespace(task="Advisory QA", requirements=(), memory=[], secrets=None,
                                    visual_check=(request, answer), bridge=SimpleNamespace(policy=None))
            handoff = NativeS2(None).messages(agent, nm, "visual advisory", SimpleNamespace(decision=None, step=0))
            assert json.loads(handoff[1]["content"])["visual_check"]["image_visible_to_s2"] is False
            write(RESULTS / f"{role}-handoff.json", handoff)
            _, second = run(session, extra=explicit, expect="budget_exhausted")
            assert second["result"]["p"] is None
        for mode, expected in (("refusal", "refusal"), ("timeout", "timeout"),
                               ("source_changed", "invalidated"), ("generation_changed", "invalidated")):
            session, _ = setup(mode)
            run(session, mode, extra=explicit + (("--timeout", "1") if mode == "timeout" else ()), expect=expected)
        ledger = json.loads((PRIVATE / "timeout/visual/budget.json").read_text())
        assert ledger["entries"][0]["settled"] is False and ledger["entries"][0]["tokens"] == 64_000
        for case, update in (("no-disclosure", {}), ("secret", {"secret_names": ["OPAQUE"]}),
                             ("browser", {"mode": "browser"})):
            session, _ = setup(case)
            state = SessionState.load(session)
            for name, value in update.items():
                setattr(state, name, value)
            state.save()
            before = server.requests
            commands.append(invoke("visual-check", "--session", str(session), "--request", "request.json",
                                   "--provider", "decisions"))
            assert commands[-1]["exit"] == 4 and server.requests == before and not (session / "visual").exists()
        assert not action_calls and not any((scene / "effect.json").exists() for scene in (fixture, document))
        assert not list(PRIVATE.rglob("grants.json"))
        proof.update(checks=checks, commands=commands, requests=server.requests, request_receipts=server.receipts,
                     no_effect=True, no_grants=True, action_dispatches=len(action_calls),
                     source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
        write(RESULTS / "verification.json", proof)
        print(json.dumps({"checks": len(checks), "requests": server.requests, "no_effect": True}))
    finally:
        visual_native.make_provider, visual_native.capture_request = original_provider, original_capture
        for name, method in actions.items():
            setattr(NativeBridge, name, method)
        server.shutdown()
        server.server_close()
        for app in processes:
            app.terminate()
            app.wait(timeout=10)
        proof["cleanup"] = [{"pid": app.pid, "returncode": app.returncode} for app in processes]
        proof["loopback_server_closed"] = True
        write(RESULTS / "verification.json", proof)

if __name__ == "__main__":
    main()
