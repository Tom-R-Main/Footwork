"""Retained loopback workbench link; reconnect and restart never replay requests.

Command payload bytes and identity headers pass unchanged. One-shot faults are
local diagnostics. Ordinary read-only identity/state polling is not journaled.
Tagged auxiliary reads are single flight per path; late replies are discarded.
"""
import concurrent.futures
import contextlib
import copy
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

MODES = {"drop_after", "delay_after", "duplicate"}
MAX_EVENTS = 16384
HEALTH_HEADER = "X-Footwork-Health-Probe"
HEALTH_SOFT_SECONDS = .6
HEALTH_HARD_SECONDS = 30


class WorkbenchLink:
    def __init__(self, origin, root, port=0):
        body_client.endpoint(origin)
        if type(port) is not int or not 0 <= port <= 65535:
            raise protocol.Refusal("link port must be a bounded integer")
        self.upstream = origin
        self.root = protocol.directory(root, create=True)
        self.port = port
        self.origin = None
        self._mutex = threading.RLock()
        self._manifest = None
        self._server = self._thread = self._fd = None
        self._probe_flights = {}
        self._probe_closing = False
        self._probe_peak = 0

    def _probe_read(self, path, headers, flight):
        """Owned read-only socket, with an absolute deadline even for trickled replies."""
        host, port = body_client.endpoint(self.upstream)
        connection = http.client.HTTPConnection(host, port, timeout=HEALTH_HARD_SECONDS)
        socket_lock, expired = threading.Lock(), threading.Event()
        owned_socket = [None]

        def expire():
            expired.set()
            with socket_lock:
                transport = owned_socket[0]
            if transport is not None:
                with contextlib.suppress(OSError):
                    transport.shutdown(socket.SHUT_RDWR)

        timer = threading.Timer(max(0, flight["hard_deadline"] - time.monotonic()), expire)
        timer.start()
        try:
            connection.connect()
            with socket_lock:
                owned_socket[0] = connection.sock
            if expired.is_set():
                raise TimeoutError("auxiliary body read exceeded its hard deadline")
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            length = response.getheader("Content-Length")
            if length is not None and (not length.isdigit() or int(length) > protocol.MAX_BYTES):
                raise protocol.Refusal("body response exceeds its bounded size")
            content = response.read(protocol.MAX_BYTES + 1)
            if expired.is_set():
                raise TimeoutError("auxiliary body read exceeded its hard deadline")
            if len(content) > protocol.MAX_BYTES:
                raise protocol.Refusal("body response exceeds its bounded size")
            if 300 <= response.status < 400:
                raise protocol.Refusal("body redirects are refused")
            flight["reply"] = response.status, content
        except (OSError, http.client.HTTPException, protocol.Refusal, KeyError, TypeError, ValueError) as exc:
            flight["error"] = exc
        finally:
            connection.close()
            timer.cancel()
            timer.join()
            flight["finished_at"] = time.monotonic()
            flight["done"].set()
            # No journal writes or response reuse after an auxiliary caller expires.

    def _probe(self, path, headers):
        pending = (504, protocol.encoded({"version": 1, "kind": "health_read_pending", "path": path}))
        deadline = time.monotonic() + HEALTH_SOFT_SECONDS
        with self._mutex:
            if self._probe_closing:
                raise protocol.Refusal("link is closing")
            previous = self._probe_flights.get(path)
            if previous is not None:
                if previous["thread"].is_alive():
                    return pending
                del self._probe_flights[path]
            flight = {"done": threading.Event(), "hard_deadline": time.monotonic() + HEALTH_HARD_SECONDS}
            thread = threading.Thread(target=self._probe_read, args=(path, dict(headers), flight),
                                      name="workbench-health-" + path.removeprefix("/"))
            flight["thread"] = thread
            self._probe_flights[path] = flight
            thread.start()
            self._probe_peak = max(self._probe_peak, sum(item["thread"].is_alive() for item in self._probe_flights.values()))
        if not flight["done"].wait(max(0, deadline - time.monotonic())) or flight["finished_at"] > deadline:
            return pending
        if "error" in flight:
            raise flight["error"]
        return flight["reply"]

    def _public(self, manifest=None):
        m = self._manifest if manifest is None else manifest
        return {key: copy.deepcopy(m[key]) for key in ("connected", "origin", "upstream", "fault")}

    def state(self):
        with self._mutex:
            if self._manifest is None:
                raise protocol.Refusal("link has not started")
            return self._public()

    def _event(self, kind, _changes=None, **data):
        with self._mutex:
            m = {**self._manifest, **(_changes or {})}
            if m["sequence"] >= MAX_EVENTS:
                raise protocol.Refusal("link event budget exhausted")
            sequence = m["sequence"] + 1
            event = {"sequence": sequence, "kind": kind, "previous_sha256": m["event_sha256"],
                     "state_snapshot": self._public(m), **data}
            content = protocol.encoded(event)
            protocol.create_file(self.root / "events" / f"{sequence:06d}.json", content)
            updated = {**m, "sequence": sequence, "event_sha256": protocol.sha(content)}
            protocol.persist(self.root / "link.json", updated)
            self._manifest = updated
            return event

    def _restore(self):
        m = protocol.decode(protocol.read_bytes(self.root / "link.json"))
        protocol.fields(m, ("version", "origin", "upstream", "connected", "fault", "sequence", "event_sha256", "source_sha256"),
                        "retained link")
        source_sha = protocol.sha(protocol.read_bytes(__file__))
        if (type(m["version"]) is not int or m["version"] != 1 or m["upstream"] != self.upstream or
                m["source_sha256"] != source_sha or type(m["connected"]) is not bool or
                type(m["sequence"]) is not int or not 1 <= m["sequence"] <= MAX_EVENTS):
            raise protocol.Refusal("retained link identity, source or state changed")
        _, port = body_client.endpoint(m["origin"])
        if self.port not in (0, port):
            raise protocol.Refusal("retained link must use its exact original port")
        previous, tail, payloads = None, None, set()
        for sequence in range(1, m["sequence"] + 1):
            content = protocol.read_bytes(self.root / "events" / f"{sequence:06d}.json")
            event = protocol.decode(content)
            if event.get("sequence") != sequence or event.get("previous_sha256") != previous:
                raise protocol.Refusal("link event history changed")
            if event["kind"] == "received":
                payload_path = self.root / "requests" / f"{sequence:06d}.bin"
                if protocol.sha(protocol.read_bytes(payload_path)) != event["payload_sha256"]:
                    raise protocol.Refusal("link request payload history changed")
                payloads.add(payload_path.name)
            previous, tail = protocol.sha(content), event
        if (previous != m["event_sha256"] or tail["state_snapshot"] != {key: m[key] for key in
                ("connected", "origin", "upstream", "fault")} or
                len(list((self.root / "events").iterdir())) != m["sequence"] or
                {path.name for path in (self.root / "requests").iterdir()} != payloads):
            raise protocol.Refusal("retained link manifest or immutable journal changed")
        if m["fault"] is not None:
            self._validate_fault(**m["fault"])
        self._manifest, self.origin = m, m["origin"]
        return port

    def start(self):
        if self._server is not None:
            raise protocol.Refusal("link already started")
        fd = os.open(self.root / "link.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        server = None
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise protocol.Refusal("link lock must be an owned private regular file")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise protocol.Refusal("another process owns this link") from exc
            retained = (self.root / "link.json").exists()
            if retained:
                port = self._restore()
            else:
                if any(path.name != "link.lock" for path in self.root.iterdir()):
                    raise protocol.Refusal("new link requires an empty owned directory")
                (self.root / "events").mkdir(mode=0o700)
                (self.root / "requests").mkdir(mode=0o700)
                port = self.port
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
                        payload, operation, command_id, headers, audit, probe = self.validate_request()
                        with owner._mutex:
                            if not owner._manifest["connected"]:
                                if audit:
                                    owner._event("disconnected_request", method=self.command, path=self.path,
                                                 operation=operation, command_id=command_id,
                                                 payload_sha256=protocol.sha(payload))
                                self.drop()
                                return
                            fault = owner._manifest["fault"]
                            fault = copy.deepcopy(fault) if fault and fault["operation"] == operation else None
                            if audit:
                                sequence = owner._manifest["sequence"] + 1
                                protocol.create_file(owner.root / "requests" / f"{sequence:06d}.bin", payload)
                                owner._event("received", _changes={"fault": None} if fault else None,
                                             operation=operation, command_id=command_id, method=self.command, path=self.path, payload_sha256=protocol.sha(payload), fault=fault)
                        mode = fault["mode"] if fault else None

                        def forward(copy_index):
                            if audit:
                                owner._event("forwarded", command_id=command_id, copy_index=copy_index,
                                             payload_sha256=protocol.sha(payload))
                            status, content = body_client.http_call(owner.upstream, self.command, self.path, headers,
                                                                   payload if self.command == "POST" else None,
                                                                   timeout=30, maximum=body_client.MAX_IMAGE)
                            if audit:
                                owner._event("upstream_reply", command_id=command_id, copy_index=copy_index,
                                             http_status=status, response_sha256=protocol.sha(content))
                            return status, content

                        if probe:
                            status, content = owner._probe(self.path, headers)
                        elif mode == "duplicate":
                            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                                replies = [pool.submit(forward, index) for index in (1, 2)]
                                responses = [reply.result() for reply in replies]
                            status, content = responses[0]
                            owner._event("duplicate_replies", command_id=command_id, same_reply=responses[0] == responses[1])
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
                        if audit:
                            owner._event("reply_sent", command_id=command_id, http_status=status)
                    except (OSError, http.client.HTTPException, protocol.Refusal, KeyError, TypeError, ValueError) as exc:
                        with contextlib.suppress(Exception):
                            owner._event("transport_failure", reason=str(exc))
                        self.drop()

                def validate_request(self):
                    parsed = urlsplit(self.path)
                    if (self.headers.get_all("Host") != [owner.origin.removeprefix("http://")] or
                            self.headers.get("Origin") is not None or self.headers.get("Transfer-Encoding") is not None or
                            parsed.scheme or parsed.netloc or parsed.fragment or not self.path.startswith("/")):
                        raise protocol.Refusal("link requires exact loopback Host and no browser Origin")
                    read_route = parsed.path in {"/identity", "/state"} or parsed.path.startswith(("/commands/", "/images/"))
                    if (self.command == "GET" and not read_route) or (self.command == "POST" and self.path not in {"/lease", "/commands"}):
                        raise protocol.Refusal("unsupported link route")
                    probes = self.headers.get_all(HEALTH_HEADER, [])
                    if probes and (probes != ["1"] or self.command != "GET" or self.path not in {"/identity", "/state"}):
                        raise protocol.Refusal("auxiliary health annotation requires one exact read-only route")
                    for name in ("X-Body-Id", "X-Adapter-Id", "X-Source-Sha256"):
                        values = self.headers.get_all(name, [])
                        if len(values) > 1 or (parsed.path != "/identity" and len(values) != 1):
                            raise protocol.Refusal("one exact body identity header is required")
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) > 1 or (lengths and (not lengths[0].isascii() or not lengths[0].isdigit() or
                                                        int(lengths[0]) > protocol.MAX_BYTES)):
                        raise protocol.Refusal("link payload exceeds its bounded size")
                    length = int(lengths[0]) if lengths else 0
                    if self.command == "POST" and (length < 1 or self.headers.get_all("Content-Type") != ["application/json"]):
                        raise protocol.Refusal("link requires one exact bounded JSON body")
                    if self.command == "GET" and length:
                        raise protocol.Refusal("link read requests cannot have a payload")
                    payload = self.rfile.read(length)
                    if len(payload) != length:
                        raise protocol.Refusal("link payload is truncated")
                    operation = command_id = None
                    if self.command == "POST":
                        decoded = protocol.decode(payload)
                        if not isinstance(decoded, dict):
                            raise protocol.Refusal("link command payload must be an object")
                        if self.path == "/commands":
                            operation, command_id = decoded.get("operation"), decoded.get("command_id")
                            protocol.identity(operation)
                            protocol.identity(command_id)
                        else:
                            operation = "lease"
                    headers = {key: value for key, value in self.headers.items() if key.lower() not in
                               {"host", "connection", "content-length", "transfer-encoding"}}
                    headers["Content-Length"] = str(length)
                    return payload, operation, command_id, headers, parsed.path not in {"/identity", "/state"}, bool(probes)

            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            server.daemon_threads = False
            if not retained:
                self.origin = f"http://127.0.0.1:{server.server_port}"
                self._manifest = {"version": 1, "origin": self.origin, "upstream": self.upstream, "connected": True,
                                  "fault": None, "sequence": 0, "event_sha256": None,
                                  "source_sha256": protocol.sha(protocol.read_bytes(__file__))}
            elif self._manifest["fault"] is not None:
                cancelled = self._manifest["fault"]
                self._event("fault_cancelled_on_restart", _changes={"fault": None}, fault=cancelled)
            self._event("started", origin=self.origin, upstream=self.upstream, restarted=retained)
            self._server, self._fd = server, fd
            self._probe_closing = False
            self._thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .1}, daemon=True)
            self._thread.start()
            return self
        except Exception:
            if server is not None:
                server.server_close()
            os.close(fd)
            raise

    def set_connected(self, connected):
        if type(connected) is not bool:
            raise protocol.Refusal("connected state must be boolean")
        with self._mutex:
            if self._server is None:
                raise protocol.Refusal("link is not running")
            previous = self._manifest["connected"]
            self._event("connected" if connected else "disconnected", _changes={"connected": connected}, previous_connected=previous,
                        replayed_requests=0)
            return self._public()

    @staticmethod
    def _validate_fault(mode, operation="dispatch", delay_s=.2):
        if mode not in MODES or operation not in {"start_job", "observe", "propose", "dispatch", "disturb", "lease"}:
            raise protocol.Refusal("unsupported workbench link diagnostic fault")
        delay = protocol.finite(delay_s)
        if not 0 <= delay <= 2:
            raise protocol.Refusal("link delay exceeds its two-second budget")
        return {"mode": mode, "operation": operation, "delay_s": delay}

    def arm(self, mode, operation="dispatch", delay_s=.2):
        fault = self._validate_fault(mode, operation, delay_s)
        with self._mutex:
            if self._server is None or self._manifest["fault"] is not None:
                raise protocol.Refusal("link must be running with no outstanding fault")
            self._event("armed", _changes={"fault": fault}, **fault)
            return self._public()

    def close(self):
        if self._server is not None:
            with self._mutex:
                self._probe_closing = True
            self._server.shutdown()
            try:
                self._server.server_close()
                self._thread.join(timeout=2)
                # Tagged callers finish at the soft bound; their upstream reads remain owned.
                # Each worker's absolute hard deadline closes its socket before this join returns.
                for flight in self._probe_flights.values():
                    flight["thread"].join()
                self._probe_flights.clear()
                self._event("closed", health_readers_alive=0, health_readers_peak=self._probe_peak)
            finally:
                self._server = None
                os.close(self._fd)
                self._fd = None
