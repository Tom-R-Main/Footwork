"""Loopback browser orders with SQLite revision leases and independently checked fulfillment."""

import argparse
import contextlib
import importlib.util
import json
import os
import signal
import sqlite3
import stat
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import order_protocol as protocol

Refusal = protocol.Refusal
DB_NAME = "orders.sqlite3"
SOURCES = ("order_app.py", "order_protocol.py", "order_app.html", "controller.py", "episode_runner.py",
           "workcell.py", "image_guided.py", "episode_cases.py", "proposal.schema.json", "scene.xml")


def fingerprints():
    return {name: protocol.sha(protocol.read_bytes(BASE / name)) for name in SOURCES}


def work_order(order):
    return {key: order[key] for key in ("version", "order_id", "project", "part_id", "target_zone")}


def sqlite_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Refusal("application store must be an owned private regular file")
    return [info.st_dev, info.st_ino]


def initialize(app_dir, order_file, order_sha256):
    if not isinstance(order_sha256, str) or not protocol.DIGEST.fullmatch(order_sha256):
        raise Refusal("order SHA256 must be exact lowercase hexadecimal")
    content = protocol.read_bytes(Path(order_file))
    if protocol.sha(content) != order_sha256:
        raise Refusal("order input differs from its bound digest")
    order = protocol.validate_order(protocol.decode(content))
    if order["state"] == "fulfilled":
        raise Refusal("a seeded order cannot invent a fulfillment receipt")
    binding_path = app_dir / "app-binding.json"
    if binding_path.exists() or binding_path.is_symlink():
        store = Store(app_dir)
        if store.binding["seed_sha256"] != order_sha256:
            raise Refusal("application already belongs to a different seed order")
        return {"app_id": store.app_id, "app_dir": str(app_dir), "phase": "initialized", "order": store.order(order["order_id"])}
    if any(path.name != "app.lock" for path in app_dir.iterdir()):
        raise Refusal("unreceipted app files exist; implicit initialization/reset is forbidden")
    app_id, store_id = uuid.uuid4().hex, uuid.uuid4().hex
    protocol.create_file(app_dir / "seed-order.json", content)
    database = app_dir / DB_NAME
    protocol.create_file(database, b"")
    binding = {"version": 1, "app_id": app_id, "store_id": store_id, "app_dir": str(app_dir),
               "database": DB_NAME, "database_identity": sqlite_file(database), "seed_sha256": order_sha256,
               "source_fingerprints": fingerprints()}
    with contextlib.closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA synchronous=FULL")
        connection.executescript("""
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE orders (order_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                                 state TEXT NOT NULL, work_order_json TEXT NOT NULL);
            CREATE TABLE leases (lease_id TEXT PRIMARY KEY, order_id TEXT NOT NULL,
                                 revision INTEGER NOT NULL, lease_json TEXT NOT NULL);
            CREATE UNIQUE INDEX one_lease_per_revision ON leases(order_id, revision);
            CREATE TABLE operations (operation_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                                     order_id TEXT NOT NULL, lease_id TEXT NOT NULL,
                                     request_json TEXT NOT NULL, receipt_json TEXT NOT NULL);
        """)
        connection.execute("INSERT INTO meta VALUES ('binding', ?)", (protocol.encoded(binding).decode(),))
        connection.execute("INSERT INTO orders VALUES (?,?,?,?)", (
            order["order_id"], order["revision"], order["state"], protocol.encoded(work_order(order)).decode()))
        connection.commit()
    protocol.sync_directory(app_dir)
    protocol.create_file(binding_path, protocol.encoded(binding))
    protocol.directory(app_dir / "workcells", create=True)
    return {"app_id": app_id, "app_dir": str(app_dir), "phase": "initialized", "order": order}


class Store:
    def __init__(self, app_dir):
        self.app_dir = app_dir
        self.binding = protocol.decode(protocol.read_bytes(app_dir / "app-binding.json"))
        protocol.fields(self.binding, ("version", "app_id", "store_id", "app_dir", "database", "database_identity",
                                       "seed_sha256", "source_fingerprints"), "application binding")
        if (self.binding["version"] != 1 or self.binding["app_dir"] != str(app_dir) or
                self.binding["database"] != DB_NAME or not protocol.UUID.fullmatch(self.binding["app_id"]) or
                not protocol.UUID.fullmatch(self.binding["store_id"])):
            raise Refusal("application identity or store binding is invalid")
        self.app_id = self.binding["app_id"]
        self.database = app_dir / DB_NAME
        self.validate_current()
        with self.connection() as connection:
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise Refusal("application SQLite store failed integrity check")

    @contextlib.contextmanager
    def connection(self):
        sqlite_file(self.database)
        connection = sqlite3.connect(self.database, timeout=2, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
        finally:
            connection.close()

    @contextlib.contextmanager
    def transaction(self):
        self.validate_current()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def validate_current(self):
        if (protocol.decode(protocol.read_bytes(self.app_dir / "app-binding.json")) != self.binding or
                self.binding["source_fingerprints"] != fingerprints() or
                self.binding["database_identity"] != sqlite_file(self.app_dir / DB_NAME) or
                protocol.sha(protocol.read_bytes(self.app_dir / "seed-order.json")) != self.binding["seed_sha256"]):
            raise Refusal("application source, seed or store binding changed")
        with self.connection() as connection:
            row = connection.execute("SELECT value FROM meta WHERE key='binding'").fetchone()
            if row is None or protocol.decode(row[0].encode()) != self.binding:
                raise Refusal("SQLite application identity does not match its owned store")
            origin = connection.execute("SELECT value FROM meta WHERE key='origin'").fetchone()
            origin_path = self.app_dir / "origin.json"
            if ((origin is not None or origin_path.exists() or origin_path.is_symlink()) and
                    (origin is None or protocol.decode(protocol.read_bytes(origin_path)) != {
                        "app_id": self.app_id, "origin": origin[0]})):
                raise Refusal("application origin identity changed")

    def origin(self):
        with self.connection() as connection:
            row = connection.execute("SELECT value FROM meta WHERE key='origin'").fetchone()
            return row[0] if row else None

    def bind_origin(self, origin):
        prior = self.origin()
        if prior is not None:
            if prior != origin:
                raise Refusal("application restart must preserve its exact loopback origin")
            return
        with self.transaction() as connection:
            protocol.create_file(self.app_dir / "origin.json", protocol.encoded({"app_id": self.app_id, "origin": origin}))
            connection.execute("INSERT INTO meta VALUES ('origin', ?)", (origin,))

    def order(self, order_id, connection=None):
        protocol.identity(order_id)
        if connection is None:
            with self.connection() as opened:
                return self.order(order_id, opened)
        row = connection.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        if row is None:
            raise LookupError("order identity is unavailable")
        order = protocol.decode(row["work_order_json"].encode())
        order.update(revision=row["revision"], state=row["state"])
        return protocol.validate_order(order)

    def lease(self, lease_id, connection=None):
        if not isinstance(lease_id, str) or not protocol.UUID.fullmatch(lease_id):
            raise Refusal("lease identity must be an exact UUID")
        if connection is None:
            with self.connection() as opened:
                return self.lease(lease_id, opened)
        row = connection.execute("SELECT * FROM leases WHERE lease_id=?", (lease_id,)).fetchone()
        if row is None:
            raise LookupError("lease identity is unavailable")
        lease = protocol.decode(row["lease_json"].encode())
        protocol.fields(lease, ("app_id", "lease_id", "order_id", "expected_revision", "work_order", "work_order_sha256",
                                "binding_operation_id", "physical_completion_id", "completion_operation_id", "origin",
                                "app_dir", "workspace_dir", "run_dir", "controller_dir", "handoff_dir"), "retained lease")
        expected_paths = protocol.paths_for(self.app_dir, lease_id)
        if (lease["app_id"] != self.app_id or lease["lease_id"] != lease_id or
                lease["order_id"] != row["order_id"] or lease["expected_revision"] != row["revision"] or
                lease["work_order"]["order_id"] != row["order_id"] or
                any(lease[key] != value for key, value in expected_paths.items()) or
                lease["origin"] != self.origin() or
                protocol.sha(protocol.encoded(protocol.validate_work_order(lease["work_order"]))) != lease["work_order_sha256"]):
            raise Refusal("retained lease identity, origin, order or assigned paths changed")
        return lease

    def operation(self, operation_id, connection=None):
        protocol.identity(operation_id)
        if connection is None:
            with self.connection() as opened:
                return self.operation(operation_id, opened)
        row = connection.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        if row is None:
            raise LookupError("application operation is unavailable")
        return row

    def bind(self, order_id, request):
        protocol.fields(request, ("expected_revision", "binding_operation_id"), "bind request")
        protocol.revision(request["expected_revision"])
        operation_id = protocol.identity(request["binding_operation_id"])
        exact = {"order_id": order_id, **request}
        with self.transaction() as connection:
            previous = connection.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
            if previous:
                if previous["kind"] != "bind" or protocol.decode(previous["request_json"].encode()) != exact:
                    raise Refusal("binding operation ID belongs to different arguments")
                return {"app_id": self.app_id, "lease": self.lease(previous["lease_id"], connection),
                        "order": self.order(order_id, connection), "historical": True}
            order = self.order(order_id, connection)
            if order["state"] != "open" or order["revision"] != request["expected_revision"]:
                raise Refusal("only the exact current open revision can be bound")
            if connection.execute("SELECT 1 FROM leases WHERE order_id=? AND revision=?", (order_id, order["revision"])).fetchone():
                raise Refusal("this order revision already has a lease; reuse its original binding operation")
            lease_id = uuid.uuid4().hex
            snapshot = work_order(order)
            lease = {"app_id": self.app_id, "lease_id": lease_id, "order_id": order_id,
                     "expected_revision": order["revision"], "work_order": snapshot,
                     "work_order_sha256": protocol.sha(protocol.encoded(snapshot)),
                     "binding_operation_id": operation_id, "physical_completion_id": "stage-" + uuid.uuid4().hex,
                     "completion_operation_id": "fulfill-" + uuid.uuid4().hex, "origin": self.origin(),
                     **protocol.paths_for(self.app_dir, lease_id)}
            protocol.directory(Path(lease["workspace_dir"]), create=True)
            connection.execute("INSERT INTO leases VALUES (?,?,?,?)", (
                lease_id, order_id, order["revision"], protocol.encoded(lease).decode()))
            connection.execute("INSERT INTO operations VALUES (?,?,?,?,?,?)", (
                operation_id, "bind", order_id, lease_id, protocol.encoded(exact).decode(), protocol.encoded(lease).decode()))
            return {"app_id": self.app_id, "lease": lease, "order": order, "historical": False}

    def mutate(self, order_id, request, cancel=False):
        protocol.fields(request, ("expected_revision",) if cancel else ("expected_revision", "target_zone"), "order mutation")
        protocol.revision(request["expected_revision"])
        if not cancel:
            protocol.validate_zone(request["target_zone"])
        with self.transaction() as connection:
            order = self.order(order_id, connection)
            if order["state"] != "open" or order["revision"] != request["expected_revision"]:
                raise Refusal("order changed or is no longer open")
            order["revision"] = protocol.revision(order["revision"] + 1)
            if cancel:
                order["state"] = "cancelled"
            else:
                order["target_zone"] = request["target_zone"]
            connection.execute("UPDATE orders SET revision=?,state=?,work_order_json=? WHERE order_id=?", (
                order["revision"], order["state"], protocol.encoded(work_order(order)).decode(), order_id))
            return {"app_id": self.app_id, "order": order}

    def fulfilled_repeat(self, row, exact, connection):
        if row["kind"] != "fulfill" or protocol.decode(row["request_json"].encode()) != exact:
            raise Refusal("completion operation ID belongs to different arguments")
        return {"app_id": self.app_id, "receipt": protocol.decode(row["receipt_json"].encode()),
                "current_order": self.order(row["order_id"], connection), "historical": True}

    def fulfill(self, order_id, request):
        protocol.fields(request, ("lease_id", "completion_operation_id"), "fulfillment request")
        operation_id = protocol.identity(request["completion_operation_id"])
        exact = {"order_id": order_id, **request}
        # Reconcile a committed reply before consulting possibly unavailable physical evidence.
        with self.connection() as connection:
            previous = connection.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
            if previous:
                return self.fulfilled_repeat(previous, exact, connection)
            lease = self.lease(request["lease_id"], connection)
            order = self.order(order_id, connection)
        if (lease["order_id"] != order_id or lease["completion_operation_id"] != operation_id or
                order["state"] != "open" or order["revision"] != lease["expected_revision"]):
            raise Refusal("completion must reference the assigned operation and unchanged open leased order")
        proof = verify_physical(lease)
        with self.transaction() as connection:
            previous = connection.execute("SELECT * FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
            if previous:
                return self.fulfilled_repeat(previous, exact, connection)
            current_lease = self.lease(request["lease_id"], connection)
            current = self.order(order_id, connection)
            if (current_lease != lease or current["state"] != "open" or
                    current["revision"] != lease["expected_revision"] or work_order(current) != lease["work_order"]):
                raise Refusal("order or lease changed after physical verification; fulfillment refused")
            new_revision = protocol.revision(current["revision"] + 1)
            changed = connection.execute("UPDATE orders SET state='fulfilled', revision=? WHERE order_id=? AND revision=? AND state='open'",
                                         (new_revision, order_id, lease["expected_revision"])).rowcount
            if changed != 1:
                raise Refusal("current order no longer matches the leased revision")
            receipt = {"app_id": self.app_id, "order_id": order_id, "lease_id": lease["lease_id"],
                       "completion_operation_id": operation_id, "physical_completion_id": lease["physical_completion_id"],
                       "leased_revision": lease["expected_revision"], "fulfilled_revision": new_revision,
                       "work_order_sha256": lease["work_order_sha256"], "state": "fulfilled",
                       "committed_time_unix": time.time(), "physical_proof": {"historical": True, **proof}}
            connection.execute("INSERT INTO operations VALUES (?,?,?,?,?,?)", (
                operation_id, "fulfill", order_id, lease["lease_id"], protocol.encoded(exact).decode(), protocol.encoded(receipt).decode()))
            return {"app_id": self.app_id, "receipt": receipt, "current_order": self.order(order_id, connection), "historical": True}


def controller_module():
    spec = importlib.util.spec_from_file_location("order_frozen_controller", BASE / "controller.py")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:
        raise Refusal("pinned physical controller dependencies are unavailable") from exc
    return module


def controller_query(controller, control, request):
    try:
        return controller.client(control, request)
    except (controller.Refusal, OSError, ValueError, TypeError, KeyError) as exc:
        raise Refusal("assigned live controller evidence is unavailable") from exc


def controller_observe(lease):
    controller = controller_module()
    control = protocol.directory(Path(lease["controller_dir"]))
    observed = controller_query(controller, control, {"command": "observe"})
    if observed.get("phase") != "ready" or observed.get("current_health") != "ready":
        raise Refusal("assigned controller has no current supported observation")
    packet = observed["observation"]
    expected = {key: lease["work_order"][key] for key in ("order_id", "project", "part_id", "target_zone")}
    if (packet["task_intent"] != expected or packet["run_dir"] != lease["run_dir"] or
            packet["binding"]["work_order_sha256"] != lease["work_order_sha256"]):
        raise Refusal("controller observation does not belong to the leased order")
    return controller, observed, packet


def verify_physical(lease):
    controller = controller_module()
    control = protocol.directory(Path(lease["controller_dir"]))
    goal = controller_query(controller, control, {"command": "status", "operation_id": lease["physical_completion_id"]})
    if (goal.get("operation_id") != lease["physical_completion_id"] or goal.get("historical_outcome") != "staged" or
            goal.get("phase") != "staged" or goal.get("current_health") != "ready" or
            not goal.get("current_software_artifact_check", {}).get("ok")):
        raise Refusal("assigned physical completion has no staged history and current verified artifact")
    _, observed, packet = controller_observe(lease)
    receipt = goal["receipt"]
    if (receipt["decision"] != "complete" or receipt["token"] != lease["physical_completion_id"] or
            receipt["phase"] != "staged" or receipt["image_generation"] != packet["generation"] or
            receipt["after_generation"] != packet["generation"] or receipt["after_state_sha256"] != packet["state_sha256"] or
            receipt["image_sha256"] != packet["image_sha256"] or packet["perception"]["state"] != "recognized" or
            packet["calibration"]["valid"] is not True or not observed.get("current_software_artifact_check", {}).get("ok") or
            receipt.get("historical_visual_check", {}).get("inside_with_margin") is not True or
            goal["current_incarnation"] != observed["current_incarnation"]):
        raise Refusal("current RGB, calibration, controller history or software evidence is unsupported")
    content = protocol.read_bytes(Path(lease["run_dir"]) / "order.json")
    artifact_sha = protocol.sha(content)
    for checked in (goal["current_software_artifact_check"], observed["current_software_artifact_check"]):
        if checked.get("expected_sha256") != artifact_sha or checked.get("observed_sha256") != artifact_sha:
            raise Refusal("saved physical artifact bytes do not match the live checker")
    artifact = protocol.decode(content)
    expected = lease["work_order"]
    if (artifact.get("source_kind") != "mujoco_simulation" or artifact.get("state") != "staged" or
            artifact.get("work_order_sha256") != lease["work_order_sha256"] or
            any(artifact.get(key) != expected[key] for key in ("order_id", "project", "part_id", "target_zone")) or
            artifact.get("simulator_generation") != packet["generation"] or
            artifact.get("simulator_state_sha256") != packet["state_sha256"]):
        raise Refusal("saved physical artifact identity differs from the leased task")
    return {"source_kind": "mujoco_simulation", "operation_id": lease["physical_completion_id"],
            "controller_incarnation": goal["current_incarnation"], "accepted_incarnation": goal["accepted_incarnation"],
            "generation": packet["generation"], "state_sha256": packet["state_sha256"],
            "image_sha256": packet["image_sha256"], "artifact_sha256": artifact_sha, "verified_time_unix": time.time()}


class Server(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True

    def __init__(self, store, port):
        super().__init__(("127.0.0.1", port), Handler)
        self.store = store
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"
        self.incarnation = uuid.uuid4().hex
        self.timeout = .2


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *_):
        pass

    def send(self, value, status=200, content_type="application/json; charset=utf-8", extra_headers=None):
        content = value if isinstance(value, bytes) else protocol.encoded(value)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'")
        for key, header in (extra_headers or {}).items():
            self.send_header(key, str(header))
        self.end_headers()
        self.wfile.write(content)

    def gate(self, writing=False):
        expected_host = urlsplit(self.server.origin).netloc
        if self.client_address[0] != "127.0.0.1" or self.headers.get_all("Host") != [expected_host]:
            raise Refusal("request must target the exact loopback application host")
        if writing and self.headers.get_all("Origin") != [self.server.origin]:
            raise Refusal("write requires the exact application Origin")
        if writing and self.headers.get_all("X-Footwork-App-ID") != [self.server.store.app_id]:
            raise Refusal("write requires the exact immutable application identity")
        self.server.store.validate_current()

    def route(self):
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            raise Refusal("request path must be an exact local route")
        return [unquote(part) for part in parsed.path.split("/") if part]

    def execute(self, writing=False):
        try:
            self.gate(writing)
            route = self.route()
            store = self.server.store
            if not writing:
                if not route:
                    return self.send(protocol.read_bytes(BASE / "order_app.html"), content_type="text/html; charset=utf-8")
                if route == ["api", "health"]:
                    return self.send({"app_id": store.app_id, "app_dir": str(store.app_dir), "origin": self.server.origin,
                                      "server_incarnation": self.server.incarnation, "phase": "ready",
                                      "source_fingerprints": store.binding["source_fingerprints"]})
                if route == ["api", "orders"]:
                    with store.connection() as connection:
                        orders = [store.order(row[0], connection) for row in connection.execute("SELECT order_id FROM orders ORDER BY order_id")]
                    return self.send({"app_id": store.app_id, "orders": orders})
                if len(route) == 3 and route[:2] == ["api", "orders"]:
                    return self.send({"app_id": store.app_id, "order": store.order(route[2])})
                if len(route) == 3 and route[:2] == ["api", "leases"]:
                    return self.send({"app_id": store.app_id, "lease": store.lease(route[2])})
                if len(route) == 4 and route[:2] == ["api", "leases"] and route[3] == "frame":
                    lease = store.lease(route[2])
                    _, _, packet = controller_observe(lease)
                    expected_path = Path(lease["run_dir"]) / f"vision-frame-{packet['generation']:06d}.png"
                    if packet["image_path"] != str(expected_path):
                        raise Refusal("controller frame path differs from its assigned run")
                    content = protocol.read_bytes(expected_path, maximum=1024 * 1024)
                    if protocol.sha(content) != packet["image_sha256"] or not content.startswith(b"\x89PNG\r\n\x1a\n"):
                        raise Refusal("current rendered frame bytes do not match controller evidence")
                    return self.send(content, content_type="image/png", extra_headers={
                        "X-Image-Generation": packet["generation"], "X-Image-SHA256": packet["image_sha256"],
                        "X-Perception-State": packet["perception"]["state"],
                        "X-Calibration-Valid": str(packet["calibration"]["valid"]).lower()})
                if len(route) == 3 and route[:2] == ["api", "operations"]:
                    row = store.operation(route[2])
                    return self.send({"app_id": store.app_id, "receipt": protocol.decode(row["receipt_json"].encode()),
                                      "current_order": store.order(row["order_id"]), "historical": True})
                raise LookupError("application route is unavailable")
            if (self.headers.get_all("Content-Type") != ["application/json"] or
                    len(self.headers.get_all("Content-Length") or []) != 1 or self.headers.get("Transfer-Encoding") is not None):
                raise Refusal("write requires bounded exact JSON framing")
            length = int(self.headers["Content-Length"])
            if not 0 < length <= protocol.MAX_BYTES:
                raise Refusal("JSON request size is outside its bound")
            content = self.rfile.read(length)
            if len(content) != length:
                raise Refusal("JSON request ended before its declared length")
            request = protocol.decode(content)
            if len(route) != 4 or route[:2] != ["api", "orders"]:
                raise LookupError("application write route is unavailable")
            order_id, action = protocol.identity(route[2]), route[3]
            if action == "bind":
                result = store.bind(order_id, request)
            elif action in {"edit", "cancel"}:
                result = store.mutate(order_id, request, cancel=action == "cancel")
            elif action == "fulfill":
                result = store.fulfill(order_id, request)
            else:
                raise LookupError("application write route is unavailable")
            return self.send(result)
        except LookupError as exc:
            return self.send({"app_id": self.server.store.app_id, "phase": "unavailable", "reason": str(exc)}, 404)
        except (Refusal, OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            reason = str(exc) if isinstance(exc, Refusal) else "application input or current evidence is unavailable"
            return self.send({"app_id": self.server.store.app_id, "phase": "refused", "reason": reason}, 409)

    def do_GET(self):
        self.execute()

    def do_POST(self):
        self.execute(writing=True)


def serve(app_dir, port):
    if type(port) is not int or not 0 <= port <= 65535:
        raise Refusal("port must be a bounded integer")
    store = Store(app_dir)
    prior = store.origin()
    if prior is not None and port != urlsplit(prior).port:
        raise Refusal("restart requires the exact prior loopback port; origin changes are unsupported")
    with Server(store, port) as server:
        store.bind_origin(server.origin)
        ready = {"app_id": store.app_id, "app_dir": str(app_dir), "origin": server.origin, "pid": os.getpid(),
                 "server_incarnation": server.incarnation, "phase": "ready", "source_fingerprints": fingerprints()}
        protocol.persist(app_dir / "readiness.json", ready)
        stop = threading.Event()
        prior_handlers = {sig: signal.signal(sig, lambda *_: stop.set()) for sig in (signal.SIGTERM, signal.SIGINT)}
        try:
            while not stop.is_set():
                server.handle_request()
        finally:
            # server_close joins request threads before the app ownership lock can unwind.
            server.server_close()
            ready.update(phase="stopped", stopped_time_unix=time.time())
            protocol.persist(app_dir / "readiness.json", ready)
            for sig, handler in prior_handlers.items():
                signal.signal(sig, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "serve"):
        child = commands.add_parser(command)
        child.add_argument("--app-dir", required=True)
        if command == "init":
            child.add_argument("--order-file", required=True)
            child.add_argument("--order-sha256", required=True)
        else:
            child.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        app_dir = protocol.directory(args.app_dir, create=args.command == "init")
        with protocol.locked(app_dir):
            if args.command == "init":
                result = initialize(app_dir, args.order_file, args.order_sha256)
                print(json.dumps(result, sort_keys=True, indent=2))
            else:
                serve(app_dir, args.port)
        return 0
    except (Refusal, OSError, ValueError, TypeError, KeyError, sqlite3.Error, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else "application or owned store is unavailable"
        print(json.dumps({"phase": "refused", "reason": reason}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
