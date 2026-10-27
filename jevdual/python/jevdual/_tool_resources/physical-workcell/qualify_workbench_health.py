"""Own a frozen browser trial and a bounded relay delaying tagged health replies.

The relay never drives UI, plans actions, retries requests, or reads native state.
Only auxiliary GET /identity and /state replies receive the diagnostic delay.
"""
import argparse
import contextlib
import http.client
import json
import os
import signal
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import body_client
import order_protocol as protocol
import qualify_network_workbench as previous

BASE, REPO = previous.BASE, previous.REPO
SOURCES = list(dict.fromkeys(previous.SOURCES + [BASE / name for name in (
    "qualify_workbench_health.py", "score_workbench_health.py")]))
DELAY = 1.2
MAX_REQUESTS = 16384
MAX_WORKERS = 8


def retain(path, value):
    previous.retain(path, value)


class HealthRelay:
    """Bounded threaded TCP relay with immutable exact-byte request evidence."""

    def __init__(self, upstream, root, port=0):
        body_client.endpoint(upstream)
        if type(port) is not int or not 0 <= port <= 65535:
            raise protocol.Refusal("relay port must be a bounded integer")
        self.upstream, self.root, self.port = upstream, protocol.directory(root, create=True), port
        if any(self.root.iterdir()):
            raise protocol.Refusal("health relay needs a fresh owned directory")
        (self.root / "requests").mkdir(mode=0o700)
        self.control_path = self.root.parent / "health-relay-control.json"
        self.lock, self.stopping = threading.Lock(), threading.Event()
        self.sequence = self.active = self.peak = self.finished = 0
        self.server = self.thread = self.origin = None

    def delay_for(self, tagged, path):
        if not tagged:
            return 0.0
        enabled, paths = True, ["/identity", "/state"]
        if self.control_path.exists():
            control = protocol.decode(protocol.read_bytes(self.control_path))
            protocol.fields(control, ("enabled", "paths"), "owned health relay control")
            if (type(control["enabled"]) is not bool or not isinstance(control["paths"], list) or
                    any(value not in ("/identity", "/state") for value in control["paths"]) or
                    len(set(control["paths"])) != len(control["paths"])):
                raise protocol.Refusal("invalid owned health relay control")
            enabled, paths = control["enabled"], control["paths"]
        return DELAY if enabled and path in paths else 0.0

    def start(self):
        owner = self

        class Server(ThreadingHTTPServer):
            daemon_threads = False
            block_on_close = True

            def __init__(self, address, handler):
                self.capacity = threading.BoundedSemaphore(MAX_WORKERS)
                super().__init__(address, handler)

            def process_request(self, request, client_address):
                if not self.capacity.acquire(blocking=False):
                    self.shutdown_request(request)
                    return
                try:
                    super().process_request(request, client_address)
                except BaseException:
                    self.capacity.release()
                    raise

            def process_request_thread(self, request, client_address):
                try:
                    super().process_request_thread(request, client_address)
                finally:
                    self.capacity.release()

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_):
                pass

            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def forward(self):
                started_wall, started_mono = time.time(), time.monotonic()
                directory, record = None, None
                with owner.lock:
                    owner.active += 1
                    owner.peak = max(owner.peak, owner.active)
                try:
                    self.connection.settimeout(30)
                    parsed = urlsplit(self.path)
                    probes = self.headers.get_all("X-Footwork-Health-Probe", [])
                    tagged = probes == ["1"]
                    if (self.headers.get_all("Host") != [owner.origin.removeprefix("http://")] or
                            self.headers.get_all("Origin") or self.headers.get_all("Transfer-Encoding") or
                            parsed.scheme or parsed.netloc or parsed.fragment or not self.path.startswith("/") or
                            probes and (not tagged or self.command != "GET" or self.path not in ("/identity", "/state"))):
                        raise protocol.Refusal("relay requires a closed loopback route and exact auxiliary probe tag")
                    reads = parsed.path in ("/identity", "/state") or parsed.path.startswith(("/images/", "/commands/"))
                    if self.command == "GET" and not reads or self.command == "POST" and self.path not in ("/lease", "/commands"):
                        raise protocol.Refusal("unsupported relay route")
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) > 1 or lengths and (not lengths[0].isascii() or not lengths[0].isdigit() or int(lengths[0]) > protocol.MAX_BYTES):
                        raise protocol.Refusal("relay payload exceeds its bounded size")
                    length = int(lengths[0]) if lengths else 0
                    if self.command == "GET" and length or self.command == "POST" and (length < 1 or self.headers.get_all("Content-Type") != ["application/json"]):
                        raise protocol.Refusal("relay requires exact bounded JSON framing")
                    headers = {key: value for key, value in self.headers.items() if key.lower() not in
                               {"host", "connection", "content-length", "transfer-encoding"}}
                    if len(headers) != len([key for key in self.headers if key.lower() not in
                                          {"host", "connection", "content-length", "transfer-encoding"}]):
                        raise protocol.Refusal("duplicate relay headers are refused")
                    payload = self.rfile.read(length)
                    if len(payload) != length:
                        raise protocol.Refusal("relay payload is truncated")
                    operation = command_id = None
                    if self.command == "POST":
                        request = protocol.decode(payload)
                        operation = request.get("operation") if self.path == "/commands" else "lease"
                        command_id = request.get("command_id") if self.path == "/commands" else None
                    delay = owner.delay_for(tagged, self.path)
                    with owner.lock:
                        if owner.sequence >= MAX_REQUESTS:
                            raise protocol.Refusal("relay request evidence budget exhausted")
                        owner.sequence += 1
                        sequence = owner.sequence
                    directory = owner.root / "requests" / f"{sequence:06d}"
                    directory.mkdir(mode=0o700)
                    record = {"sequence": sequence, "method": self.command, "path": self.path,
                              "tagged_health": tagged, "operation": operation, "command_id": command_id,
                              "headers": headers, "payload_sha256": protocol.sha(payload),
                              "started_wall": started_wall, "started_monotonic": started_mono,
                              "injected_delay_s": delay, "upstream_sends": 1}
                    protocol.create_file(directory / "request.bin", payload)
                    retain(directory / "request.json", record)
                    upstream_started = time.monotonic()
                    status, content = body_client.http_call(owner.upstream, self.command, self.path, headers,
                        payload if self.command == "POST" else None, timeout=30, maximum=body_client.MAX_IMAGE)
                    upstream_finished = time.monotonic()
                    protocol.create_file(directory / "response.bin", content)
                    retain(directory / "upstream.json", {"http_status": status, "response_sha256": protocol.sha(content),
                        "started_monotonic": upstream_started, "finished_monotonic": upstream_finished,
                        "wall": time.time(), "upstream_elapsed_s": upstream_finished - upstream_started})
                    delay_started = time.monotonic()
                    interrupted = owner.stopping.wait(delay) if delay else False
                    delay_finished = time.monotonic()
                    delivered = False
                    if not interrupted:
                        self.send_response(status)
                        self.send_header("Content-Type", "image/png" if self.path.startswith("/images/") else "application/json")
                        self.send_header("Content-Length", str(len(content)))
                        self.send_header("Connection", "close")
                        self.end_headers()
                        self.wfile.write(content)
                        delivered = True
                    self.close_connection = True
                    retain(directory / "result.json", {"completed": True, "delivered": delivered,
                        "delay_interrupted": interrupted, "delay_elapsed_s": delay_finished - delay_started,
                        "finished_monotonic": time.monotonic(), "finished_wall": time.time(),
                        "elapsed_s": time.monotonic() - started_mono})
                except (OSError, http.client.HTTPException, protocol.Refusal, ValueError, TypeError, AttributeError) as exc:
                    if directory is not None and not (directory / "result.json").exists():
                        retain(directory / "result.json", {"completed": False, "error": type(exc).__name__ + ": " + str(exc),
                            "finished_monotonic": time.monotonic(), "finished_wall": time.time()})
                    self.close_connection = True
                    with contextlib.suppress(OSError):
                        self.connection.shutdown(socket.SHUT_RDWR)
                finally:
                    with owner.lock:
                        owner.active -= 1
                        owner.finished += 1

        self.server = Server(("127.0.0.1", self.port), Handler)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .1}, name="health-relay")
        self.thread.start()
        retain(self.root / "ready.json", {"origin": self.origin, "upstream": self.upstream,
               "delay_s": DELAY, "worker_bound": MAX_WORKERS, "source_sha256": protocol.sha(protocol.read_bytes(__file__))})
        return self

    def close(self):
        self.stopping.set()
        if self.server:
            self.server.shutdown()
            self.thread.join(3)
            self.server.server_close()  # Joins all non-daemon bounded request workers.
        retain(self.root / "cleanup.json", {"server_thread_exited": not self.thread or not self.thread.is_alive(),
               "active_workers": self.active, "peak_workers": self.peak, "completed_workers": self.finished,
               "request_count": self.sequence, "worker_bound": MAX_WORKERS})


def freeze(root, commit):
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != commit:
        raise protocol.Refusal("trial must start at its named source commit")
    files = {}
    for path in SOURCES:
        name = str(path.relative_to(REPO))
        content = protocol.read_bytes(path)
        if subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=REPO) != content:
            raise protocol.Refusal("trial source differs from its committed freeze: " + name)
        files[name] = protocol.sha(content)
    retain(root / "source-freeze.json", {"commit": commit, "files": files})


def run(root, commit, body_port=0, browser_port=0, relay_port=0):
    root = protocol.directory(root, create=True)
    freeze(root, commit)
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    processes, logs = [], []
    ledger = {"source_commit": commit, "planner": "actual_codex_cli_images_over_TCP", "simulation": True,
              "processes": [], "ready": False, "health_delay_s": DELAY, "limit_s": 2700}

    def launch(name, arguments):
        log = (root / (name + ".log")).open("xb")
        logs.append(log)
        process = subprocess.Popen([str(Path(os.environ.get("FOOTWORK_PYTHON", str(BASE / ".venv/bin/python")))), *arguments], cwd=REPO, stdout=log, stderr=log)
        processes.append(process)
        ledger["processes"].append({"role": name, "pid": process.pid})
        return process

    try:
        body_port = body_port or previous.available_port()
        browser_port = browser_port or previous.available_port()
        if body_port == browser_port or relay_port and relay_port in (body_port, browser_port):
            raise protocol.Refusal("trial services need distinct ports")
        body_origin, browser_origin = f"http://127.0.0.1:{body_port}", f"http://127.0.0.1:{browser_port}"
        launch("body", [str(BASE / "body_network.py"), "--root", str(root / "body"), "--port", str(body_port), "--initialize", "--diagnostic"])
        identity = previous.wait_json(body_origin, "/identity", processes)
        retain(root / "identity.json", identity)
        launch("health-relay", [str(BASE / "qualify_workbench_health.py"), "relay", "--root", str(root / "health-relay"),
                               "--upstream", body_origin, "--port", str(relay_port)])
        until = time.monotonic() + 20
        while not (root / "health-relay" / "ready.json").exists():
            if any(p.poll() is not None for p in processes) or time.monotonic() >= until:
                raise protocol.Refusal("owned health relay failed to start")
            stopped.wait(.1)
        relay_ready = protocol.decode(protocol.read_bytes(root / "health-relay" / "ready.json"))
        initialization = launch("initialize", [str(BASE / "network_bench_operator.py"), "init", "--root", str(root / "operator"),
                                               "--body-origin", relay_ready["origin"]])
        if initialization.wait(timeout=30):
            raise protocol.Refusal("network workbench initialization failed; evidence retained")
        launch("workbench", [str(BASE / "network_bench_operator.py"), "serve", "--root", str(root / "operator"),
                             "--port", str(browser_port), "--backend", "codex"])
        running = [p for p, entry in zip(processes, ledger["processes"], strict=True) if entry["role"] != "initialize"]
        initial = previous.wait_json(browser_origin, "/api/state", running)
        retain(root / "initial-public.json", initial)
        ledger.update(body_origin=body_origin, browser_origin=browser_origin, relay_origin=relay_ready["origin"],
                      ready=True, app_id=initial["app_id"], body_id=identity["body_id"])
        retain(root / "ready.json", ledger)
        print(json.dumps(ledger), flush=True)
        deadline = time.monotonic() + 2700
        while not stopped.is_set() and not (root / "stop-request.json").exists():
            if any(p.poll() is not None for p in running):
                raise protocol.Refusal("owned trial service exited before requested cleanup")
            if time.monotonic() >= deadline:
                raise protocol.Refusal("health qualification exceeded its 45-minute bound")
            stopped.wait(.2)
        retain(root / "final-public.json", previous.wait_json(browser_origin, "/api/state", running))
    except BaseException as exc:
        ledger["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for entry, process in zip(ledger["processes"], processes, strict=True):
            entry.update(exit_observed=process.poll() is not None, returncode=process.returncode)
        for log in logs:
            log.close()
        ledger["owned_processes_exited"] = all(p.poll() is not None for p in processes)
        retain(root / "process-ledger.json", ledger)
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    relay = commands.add_parser("relay")
    relay.add_argument("--root", type=Path, required=True)
    relay.add_argument("--upstream", required=True)
    relay.add_argument("--port", type=int, default=0)
    trial = commands.add_parser("trial")
    trial.add_argument("--root", type=Path, required=True)
    trial.add_argument("--source-commit", required=True)
    for name in ("body-port", "browser-port", "relay-port"):
        trial.add_argument("--" + name, type=int, default=0)
    args = parser.parse_args()
    if args.command == "relay":
        stopped = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
        signal.signal(signal.SIGINT, lambda *_: stopped.set())
        owned = HealthRelay(args.upstream, args.root, args.port)
        try:
            owned.start()
            print(json.dumps({"origin": owned.origin}), flush=True)
            stopped.wait(2700)
        finally:
            owned.close()
    else:
        if any(not 0 <= value <= 65535 for value in (args.body_port, args.browser_port, args.relay_port)):
            raise protocol.Refusal("trial ports must be in the TCP range")
        print(json.dumps(run(args.root, args.source_commit, args.body_port, args.browser_port, args.relay_port)), flush=True)


if __name__ == "__main__":
    main()
