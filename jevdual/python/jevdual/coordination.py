"""Cooperative ownership across CLI processes, independent of durable authority databases.

The registry arbitrates resources; a kernel lock keeps an active request owned until
its dispatch, readback and cleanup finish. Revocation fences subsequent RPCs, never
hands an in-flight transaction to a new owner. Reservations deliberately have no TTL.
"""
from __future__ import annotations

import asyncio
import contextlib
import contextvars
import fcntl
import json
import os
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any


class CoordinationError(RuntimeError):
    code = "coordination_refused"


_CURRENT: contextvars.ContextVar[Any] = contextvars.ContextVar("footwork_owner", default=None)


def desktop_id() -> str:
    # A viewing stream, session name or authority database is not another desktop.
    if sys.platform.startswith("linux"):
        display = os.environ.get("DISPLAY", "unavailable").removesuffix(".0")
        return "x11:" + display.removeprefix("unix")
    return "console"


def app_resource(app: str, *, window: str = "") -> str:
    name = app.casefold().removesuffix(" (footwork)")
    if name in {"chrome", "chromium", "google chrome"}:
        name = "google chrome"
    # Encode components so names cannot introduce parent/child relationships.
    from urllib.parse import quote

    root = "app/" + quote(name, safe="")
    return root + ("/window/" + window if window else "")


def conflicts(left: list[str], right: list[str]) -> bool:
    return any(a == b or a.startswith(b + "/") or b.startswith(a + "/") for a in left for b in right)


class Coordinator:
    def __init__(self, path: Path | None = None):
        # Production entrypoints always use this one location, regardless of --authority.
        self.path = path or Path.home() / ".local/state/footwork/coordination.sqlite"
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.locks = self.path.parent / (self.path.name + ".locks")
        self.locks.mkdir(mode=0o700, exist_ok=True)
        with self.db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS requests (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE NOT NULL,
                owner TEXT NOT NULL, desktop TEXT NOT NULL, resources TEXT NOT NULL,
                state TEXT NOT NULL, reservation TEXT NOT NULL, pid INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS reservations (
                token TEXT PRIMARY KEY, owner TEXT NOT NULL, desktop TEXT NOT NULL,
                resources TEXT NOT NULL, state TEXT NOT NULL)""")

    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _prune(self, db):
        for row in db.execute("SELECT * FROM requests").fetchall():
            with (self.locks / row["token"]).open("a+") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                if "desktop" in json.loads(row["resources"]) and row["state"] in {"active", "revoked", "orphaned"}:
                    # A hard-killed pointer owner cannot run its finally blocks.
                    # Require explicit recovery after checking/releasing held input.
                    db.execute("UPDATE requests SET state='orphaned' WHERE token=?", (row["token"],))
                    continue
                db.execute("DELETE FROM requests WHERE token=?", (row["token"],))
                # Unique request tokens are never reused, so late cleanup cannot
                # unlock or delete a newer request's inode.
                (self.locks / row["token"]).unlink(missing_ok=True)

    @staticmethod
    def overlap(desktop, resources, row):
        shared_session = any(r.startswith("session/") for r in resources)
        return (shared_session or row["desktop"] == desktop) and conflicts(resources, json.loads(row["resources"]))

    def status(self) -> dict:
        with self.db() as db:
            self._prune(db)
            return {name: [dict(row) | {"resources": json.loads(row["resources"])}
                           for row in db.execute(f"SELECT * FROM {name}")]
                    for name in ("requests", "reservations")}

    def recover(self, token: str) -> None:
        with self.db() as db:
            self._prune(db)
            row = db.execute("SELECT state FROM requests WHERE token=?", (token,)).fetchone()
            if row is None or row["state"] != "orphaned":
                raise CoordinationError("recovery requires an orphaned request token; a live owner cannot be recovered")
            db.execute("DELETE FROM requests WHERE token=?", (token,))

    def revoke(self, token: str) -> None:
        with self.db() as db:
            reservation = db.execute("UPDATE reservations SET state='revoked' WHERE token=?", (token,))
            request = db.execute("UPDATE requests SET state='revoked' WHERE token=? AND state != 'orphaned'", (token,))
            if reservation.rowcount + request.rowcount == 0:
                raise CoordinationError("unknown ownership token")
            db.execute("UPDATE requests SET state='revoked' WHERE reservation=? AND state != 'orphaned'", (token,))

    def reserve(self, claim: Claim, resources: list[str]) -> str:
        with self.db() as db:
            claim._check(db)
            if not set(resources).issubset(claim.resources):
                raise CoordinationError("reservation requires ownership of every requested resource")
            token = uuid.uuid4().hex
            db.execute("INSERT INTO reservations VALUES (?,?,?,?,?)",
                       (token, claim.owner, claim.desktop, json.dumps(resources), "active"))
            return token

    def claim(self, owner: str, resources: list[str], *, reservation: str = "", timeout: float = 30):
        return Claim(self, owner, resources, reservation, timeout)


class Claim:
    def __init__(self, registry, owner, resources, reservation, timeout):
        self.registry, self.owner, self.resources = registry, owner, sorted(set(resources))
        self.reservation, self.timeout = reservation, timeout
        self.desktop, self.token = desktop_id(), uuid.uuid4().hex
        self.lock = None

    def _check(self, db):
        row = db.execute("SELECT state FROM requests WHERE token=?", (self.token,)).fetchone()
        if row is None or row["state"] != "active":
            raise CoordinationError("ownership revoked; no further input is admitted")
        if self.reservation:
            row = db.execute("SELECT * FROM reservations WHERE token=?", (self.reservation,)).fetchone()
            if (row is None or row["state"] != "active" or row["owner"] != self.owner
                    or row["desktop"] != self.desktop):
                raise CoordinationError("reservation revoked or belongs to another desktop/session")

    def check(self):
        with self.registry.db() as db:
            self._check(db)

    async def __aenter__(self):
        self.lock = (self.registry.locks / self.token).open("a+")
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with self.registry.db() as db:
                db.execute("INSERT INTO requests (token,owner,desktop,resources,state,reservation,pid) "
                           "VALUES (?,?,?,?,?,?,?)", (self.token, self.owner, self.desktop,
                           json.dumps(self.resources), "waiting", self.reservation, os.getpid()))
            deadline = asyncio.get_running_loop().time() + self.timeout
            while True:
                with self.registry.db() as db:
                    self.registry._prune(db)
                    own = db.execute("SELECT * FROM requests WHERE token=?", (self.token,)).fetchone()
                    if own is None or own["state"] == "revoked":
                        raise CoordinationError("waiting request canceled")
                    if self.reservation:
                        saved = db.execute("SELECT * FROM reservations WHERE token=?",
                                           (self.reservation,)).fetchone()
                        if (saved is None or saved["state"] != "active" or saved["owner"] != self.owner
                                or saved["desktop"] != self.desktop):
                            raise CoordinationError("reservation unavailable; explicit handoff required")
                    blocked = False
                    for row in db.execute("SELECT * FROM reservations WHERE state='active'"):
                        if row["token"] == self.reservation:
                            continue
                        if self.registry.overlap(self.desktop, self.resources, row):
                            blocked = True
                    for row in db.execute("SELECT * FROM requests WHERE token != ?", (self.token,)):
                        # Active revoked commands retain ownership through cleanup.
                        # Earlier conflicting waiters are a fairness barrier.
                        if ((row["state"] in {"active", "revoked", "orphaned"} or row["seq"] < own["seq"])
                                and self.registry.overlap(self.desktop, self.resources, row)):
                            blocked = True
                    if not blocked:
                        db.execute("UPDATE requests SET state='active' WHERE token=?", (self.token,))
                        return self
                if asyncio.get_running_loop().time() >= deadline:
                    raise CoordinationError("resources busy; inspect footwork control status for owners and waiters")
                await asyncio.sleep(0.025)
        except BaseException:
            self.close()
            raise

    def close(self):
        try:
            with self.registry.db() as db:
                db.execute("DELETE FROM requests WHERE token=?", (self.token,))
        finally:
            if self.lock is not None:
                self.lock.close()
                self.lock = None
            (self.registry.locks / self.token).unlink(missing_ok=True)

    async def __aexit__(self, *exc):
        self.close()


@contextlib.contextmanager
def activated(claim):
    token = _CURRENT.set(claim)
    try:
        yield
    finally:
        _CURRENT.reset(token)


def checkpoint() -> None:
    claim = _CURRENT.get()
    if claim is not None:
        claim.check()


def cancelled() -> bool:
    try:
        checkpoint()
        return False
    except CoordinationError:
        return True


class GuardedDriver:
    """Fence RPC boundaries. An already admitted SDK RPC finishes under ownership.

    SDK shutdown and release operations remain available for owned-input cleanup.
    """
    def __init__(self, driver):
        self._driver = driver

    def __getattr__(self, name):
        value = getattr(self._driver, name)
        if not callable(value) or name in {"shutdown", "close"}:
            return value

        async def call(*args, **kwargs):
            readonly = name in {"list_apps", "list_windows", "get_window_state", "verify_state"}
            if name == "call_tool" and args:
                readonly = args[0] in {"get_browser_state", "get_screen_size", "get_window_state", "screenshot"}
            if not readonly:
                checkpoint()
            return await value(*args, **kwargs)
        return call


def guard_driver(driver):
    return GuardedDriver(driver) if _CURRENT.get() is not None else driver


async def owned_thread(fn, *args, **kwargs):
    """Task cancellation cannot abandon a thread that still owns pointer input."""
    task = asyncio.create_task(asyncio.to_thread(fn, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        claim = _CURRENT.get()
        if claim is not None:
            claim.registry.revoke(claim.token)
        # Retain resource ownership until the thread's finally block releases input.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:  # noqa: BLE001 - consume worker failure while preserving caller cancellation
                break
        # Consume any worker exception, preserving cancellation of the caller.
        with contextlib.suppress(Exception):
            task.result()
        raise
