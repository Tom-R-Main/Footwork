"""Loopback browser product for the guarded simulated bench operator."""
import argparse
import json
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import operator_runtime as runtime
import order_protocol as protocol

BASE = Path(__file__).resolve().parent


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, operator):
        super().__init__(address, Handler)
        self.operator = operator
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"
        self.host = f"127.0.0.1:{self.server_address[1]}"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def reply(self, code, body, content_type="application/json"):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def exact_header(self, name, value):
        return self.headers.get_all(name) == [value]

    def do_GET(self):
        try:
            if not self.exact_header("Host", self.server.host):
                raise protocol.Refusal("exact loopback Host is required")
            parsed = urlsplit(self.path)
            if parsed.path == "/" and not parsed.query:
                self.server.operator._identity()
                self.reply(200, protocol.read_bytes(BASE / "bench_operator.html"), "text/html; charset=utf-8")
            elif parsed.path == "/api/state" and not parsed.query:
                self.reply(200, self.server.operator.state())
            elif parsed.path == "/api/frame":
                self.reply(200, self.server.operator.frame(self.path), "image/png")
            else:
                self.reply(404, {"error": "Unknown operator route"})
        except (protocol.Refusal, OSError, ValueError) as exc:
            self.reply(409, {"error": str(exc)})

    def do_POST(self):
        try:
            app_id = self.server.operator.m["app_id"]
            if (not self.exact_header("Host", self.server.host) or
                    not self.exact_header("Origin", self.server.origin) or
                    not self.exact_header("X-Footwork-App-ID", app_id)):
                raise protocol.Refusal("exact loopback origin and application identity are required before mutation")
            lengths = self.headers.get_all("Content-Length")
            if (lengths is None or len(lengths) != 1 or not lengths[0].isascii() or
                    not lengths[0].isdigit() or not 1 <= int(lengths[0]) <= 4096 or
                    self.headers.get_all("Transfer-Encoding") is not None or
                    not self.exact_header("Content-Type", "application/json")):
                raise protocol.Refusal("request requires one bounded JSON body with an exact content length")
            self.connection.settimeout(5)
            content = self.rfile.read(int(lengths[0]))
            if len(content) != int(lengths[0]):
                raise protocol.Refusal("JSON body is incomplete")
            request = protocol.decode(content)
            if self.path == "/api/jobs":
                result = self.server.operator.enqueue(request)
            elif self.path in ("/api/pause", "/api/resume"):
                protocol.fields(request, (), "operator control")
                result = getattr(self.server.operator, self.path.rsplit("/", 1)[1])()
            else:
                raise protocol.Refusal("unknown operator mutation route")
            self.reply(200, result)
        except (protocol.Refusal, OSError, TypeError, ValueError) as exc:
            self.reply(409, {"error": str(exc)})


def serve(root, port, policy):
    root = protocol.directory(root)
    operator = runtime.Operator(root, policy)
    server = None
    try:
        server = Server(("127.0.0.1", port), operator)
        readiness = root / "readiness.json"
        if readiness.exists():
            previous = protocol.decode(protocol.read_bytes(readiness))
            if previous["app_id"] != operator.m["app_id"] or previous["origin"] != server.origin:
                raise protocol.Refusal("retained application origin changed; restart on its exact port")
        protocol.persist(readiness, {"app_id": operator.m["app_id"], "origin": server.origin,
                                    "port": server.server_address[1], "simulation": True})
        print(json.dumps(protocol.decode(protocol.read_bytes(readiness))), flush=True)
        def stop(*_):
            operator.cancel.set()
            threading.Thread(target=server.shutdown, daemon=True).start()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        server.serve_forever(poll_interval=.2)
    finally:
        if server:
            server.server_close()
        operator.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--root", type=Path, required=True)
    run = commands.add_parser("serve")
    run.add_argument("--root", type=Path, required=True)
    run.add_argument("--port", type=int, default=0)
    run.add_argument("--backend", choices=("codex",), default="codex")
    args = parser.parse_args()
    try:
        if args.command == "init":
            print(json.dumps({"app_id": runtime.initialize(args.root), "simulation": True}))
        else:
            if not 0 <= args.port <= 65535:
                raise protocol.Refusal("port must be in the TCP range")
            from codex_policy import decide
            serve(args.root, args.port, decide)
        return 0
    except (protocol.Refusal, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
