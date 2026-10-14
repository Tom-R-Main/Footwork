"""One-shot diagnostic TCP faults; command payload bytes are forwarded unchanged.

FaultProxy(origin, root).start() exposes .origin. arm(mode, operation='dispatch',
delay_s=.2) affects one matching command. Events are immutable private JSON files.
This loopback test instrument is not an authentication or production proxy.
"""
import concurrent.futures
import contextlib
import fcntl
import http.client
import os
import socket
import stat
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import body_client
import order_protocol as protocol

MODES = {"delay_before", "delay_after", "drop_before", "drop_after", "duplicate"}


class FaultProxy:
    def __init__(self, origin, root):
        self.upstream = origin
        body_client.endpoint(origin)
        self.root = protocol.directory(root, create=True)
        self.origin = None
        self._mutex = threading.Lock()
        self._arm = None
        self._sequence = 0
        self._server = None
        self._thread = None
        self._fd = None

    def _event(self, kind, **data):
        with self._mutex:
            if self._sequence >= 2048:
                raise protocol.Refusal("proxy event budget exhausted")
            self._sequence += 1
            value = {"sequence": self._sequence, "kind": kind, **data}
            protocol.create_file(self.root / "events" / f"{self._sequence:06d}.json", protocol.encoded(value))
            return value

    def start(self):
        if self._server is not None:
            raise protocol.Refusal("proxy already started")
        fd = os.open(self.root / "proxy.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise protocol.Refusal("invalid proxy lock")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if any(path.name != "proxy.lock" for path in self.root.iterdir()):
                raise protocol.Refusal("fault proxy requires a fresh private journal")
            (self.root / "events").mkdir(mode=0o700)
            (self.root / "requests").mkdir(mode=0o700)
            owner = self

            class Handler(BaseHTTPRequestHandler):
                protocol_version = "HTTP/1.1"

                def log_message(self, *_):
                    pass

                def do_GET(self):
                    self.handle_request()

                def do_POST(self):
                    self.handle_request()

                def drop(self):
                    self.close_connection = True
                    with contextlib.suppress(OSError):
                        self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()

                def handle_request(self):
                    self.connection.settimeout(30)
                    try:
                        host = owner.origin.removeprefix("http://")
                        if (self.headers.get_all("Host") != [host] or self.headers.get("Transfer-Encoding") is not None or
                                self.headers.get("Origin") is not None or urlsplit(self.path).scheme or
                                not self.path.startswith("/")):
                            raise protocol.Refusal("proxy request shape refused")
                        for name in ("X-Body-Id", "X-Adapter-Id", "X-Source-Sha256"):
                            if len(self.headers.get_all(name, [])) > 1:
                                raise protocol.Refusal("proxy refuses duplicate identity headers")
                        if self.command == "POST" and self.headers.get_all("Content-Type") != ["application/json"]:
                            raise protocol.Refusal("proxy requires one exact JSON content type")
                        lengths = self.headers.get_all("Content-Length", [])
                        if len(lengths) > 1 or (lengths and (not lengths[0].isdigit() or int(lengths[0]) > protocol.MAX_BYTES)):
                            raise protocol.Refusal("proxy request exceeds bounded size")
                        length = int(lengths[0]) if lengths else 0
                        payload = self.rfile.read(length)
                        if len(payload) != length:
                            raise protocol.Refusal("proxy request body is incomplete")
                        operation, command_id = None, None
                        if self.command == "POST" and self.path == "/commands":
                            command = protocol.decode(payload)
                            operation, command_id = command.get("operation"), command.get("command_id")
                        elif self.command == "POST" and self.path == "/lease":
                            operation = "lease"
                        headers = {key: value for key, value in self.headers.items()
                                   if key.lower() not in {"host", "connection", "content-length", "transfer-encoding"}}
                        headers["Content-Length"] = str(length)
                        with owner._mutex:
                            fault = owner._arm if owner._arm and owner._arm["operation"] == operation else None
                            if fault:
                                owner._arm = None
                        event = owner._event("received", operation=operation, command_id=command_id,
                                             method=self.command, path=self.path, payload_sha256=protocol.sha(payload),
                                             fault=fault)
                        request_file = owner.root / "requests" / f"{event['sequence']:06d}.bin"
                        protocol.create_file(request_file, payload)
                        mode = fault["mode"] if fault else None
                        if mode == "drop_before":
                            owner._event("dropped_before", command_id=command_id)
                            self.drop()
                            return
                        if mode == "delay_before":
                            owner._event("delay_before", command_id=command_id, delay_s=fault["delay_s"])
                            time.sleep(fault["delay_s"])

                        def forward(copy_index):
                            owner._event("forwarded", command_id=command_id, copy_index=copy_index,
                                         payload_sha256=protocol.sha(payload))
                            status, content = body_client.http_call(owner.upstream, self.command, self.path,
                                                                   headers, payload if self.command == "POST" else None,
                                                                   timeout=30, maximum=body_client.MAX_IMAGE)
                            owner._event("upstream_reply", command_id=command_id, copy_index=copy_index,
                                         http_status=status, response_sha256=protocol.sha(content))
                            return status, content

                        if mode == "duplicate":
                            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                                futures = [pool.submit(forward, index) for index in (1, 2)]
                                responses = [future.result() for future in futures]
                            status, content = responses[0]
                            owner._event("duplicate_replies", command_id=command_id,
                                         same_reply=responses[0] == responses[1])
                        else:
                            status, content = forward(1)
                        if mode == "delay_after":
                            owner._event("delay_after", command_id=command_id, delay_s=fault["delay_s"])
                            time.sleep(fault["delay_s"])
                        if mode == "drop_after":
                            owner._event("dropped_after", command_id=command_id)
                            self.drop()
                            return
                        self.send_response(status)
                        self.send_header("Content-Type", "image/png" if self.path.startswith("/images/") else "application/json")
                        self.send_header("Content-Length", str(len(content)))
                        self.send_header("Connection", "close")
                        self.close_connection = True
                        self.end_headers()
                        self.wfile.write(content)
                        owner._event("reply_sent", command_id=command_id, http_status=status)
                    except (OSError, http.client.HTTPException, protocol.Refusal, KeyError, ValueError) as exc:
                        with contextlib.suppress(Exception):
                            owner._event("transport_failure", reason=str(exc))
                        self.drop()

            self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            self._server.daemon_threads = False
            self.origin = f"http://127.0.0.1:{self._server.server_port}"
            self._fd = fd
            self._thread = threading.Thread(target=self._server.serve_forever, name="body-fault-proxy", daemon=True)
            self._thread.start()
            self._event("started", origin=self.origin, upstream=self.upstream)
            return self
        except Exception:
            os.close(fd)
            raise

    def arm(self, mode, operation="dispatch", delay_s=.2):
        if mode not in MODES or operation not in {"start_job", "observe", "propose", "dispatch", "disturb", "lease"}:
            raise protocol.Refusal("unsupported one-shot proxy fault")
        delay = protocol.finite(delay_s)
        if not 0 <= delay <= 2:
            raise protocol.Refusal("proxy delay exceeds its two-second budget")
        with self._mutex:
            if self._server is None or self._arm is not None:
                raise protocol.Refusal("proxy must be running with no outstanding fault")
            self._arm = {"mode": mode, "operation": operation, "delay_s": delay}
        self._event("armed", mode=mode, operation=operation, delay_s=delay)

    def close(self):
        if self._server is not None:
            self._server.shutdown()
            try:
                self._server.server_close()
                self._thread.join(timeout=2)
                self._event("closed")
            finally:
                self._server = None
                os.close(self._fd)
                self._fd = None
