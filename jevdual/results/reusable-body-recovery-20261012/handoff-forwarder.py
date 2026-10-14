"""Handoff-only loopback forwarding: no faults, response cache or automatic retries."""
import json
import http.client
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import body_client
import order_protocol as protocol

config = json.loads((Path(__file__).parent / "config.json").read_text())
origin = config["relay_origin"]
stopped = threading.Event()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def forward(self):
        self.connection.settimeout(15)
        try:
            route = urlsplit(self.path)
            if (self.headers.get_all("Host") != [urlsplit(origin).netloc] or
                    self.headers.get_all("Origin") or self.headers.get_all("Transfer-Encoding") or
                    route.scheme or route.netloc or route.fragment or len(self.path) > 8192):
                raise protocol.Refusal("closed loopback framing required")
            if (self.command == "GET" and not (route.path in ("/identity", "/state") or
                    route.path.startswith(("/commands/", "/images/"))) or
                    self.command == "POST" and self.path not in ("/lease", "/commands")):
                raise protocol.Refusal("unsupported body route")
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) > 1 or lengths and (not lengths[0].isascii() or not lengths[0].isdigit()):
                raise protocol.Refusal("invalid content length")
            length = int(lengths[0]) if lengths else 0
            if (length > protocol.MAX_BYTES or self.command == "GET" and length or
                    self.command == "POST" and (not length or self.headers.get_all("Content-Type") != ["application/json"])):
                raise protocol.Refusal("bounded JSON framing required")
            payload = self.rfile.read(length)
            if len(payload) != length:
                raise protocol.Refusal("incomplete body")
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection", "content-length")}
            code, data = body_client.http_call(config["body_origin"], self.command, self.path, headers,
                payload if self.command == "POST" else None, timeout=15, maximum=body_client.MAX_IMAGE)
            mime = "image/png" if route.path.startswith("/images/") else "application/json"
        except (OSError, http.client.HTTPException, ValueError, protocol.Refusal):
            code, data, mime = 502, protocol.encoded({"error": "Transport unavailable; request was not retried"}), "application/json"
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    do_GET = forward
    do_POST = forward


class Server(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True

    def __init__(self, address):
        self.capacity = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def process_request(self, request, address):
        if not self.capacity.acquire(False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.capacity.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.capacity.release()


server = Server(("127.0.0.1", urlsplit(origin).port))
signal.signal(signal.SIGTERM, lambda *_: stopped.set())
signal.signal(signal.SIGINT, lambda *_: stopped.set())
thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .1})
thread.start()
print(json.dumps({"origin": origin, "upstream": config["body_origin"], "faults": False, "retries": 0}), flush=True)
try:
    stopped.wait()
finally:
    server.shutdown()
    thread.join()
    server.server_close()
