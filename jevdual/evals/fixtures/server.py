"""Local fixture server for evals.

Serves the static site under ``evals/fixtures/site`` and records every POST so
a grader can check what was submitted rather than trusting the agent's claim.
Shape borrowed from fastbrowse's ``evals/local.py`` (MIT).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, quote

SITE = Path(__file__).with_name("site")


class Recorder:
    """Thread-safe log of POST submissions keyed by path."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._posts: dict[str, list[dict[str, str]]] = {}
        #: Q13: every GET with a query string, so a form that submits by GET is an observable effect
        self._gets: dict[str, list[dict[str, str]]] = {}

    def add_get(self, path: str, fields: dict[str, str]) -> None:
        with self._lock:
            self._gets.setdefault(path, []).append(fields)

    def gets(self) -> dict[str, list[dict[str, str]]]:
        with self._lock:
            return {path: list(q) for path, q in self._gets.items()}

    def add(self, path: str, fields: dict[str, str]) -> None:
        with self._lock:
            self._posts.setdefault(path, []).append(fields)

    def snapshot(self) -> dict[str, list[dict[str, str]]]:
        with self._lock:
            return {path: list(posts) for path, posts in self._posts.items()}

    def clear(self) -> None:
        with self._lock:
            self._posts.clear()


def _handler(recorder: Recorder) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            rel, _, query = self.path.partition("?")
            rel = rel.lstrip("/") or "index.html"
            if query:
                recorder.add_get("/" + rel, dict(parse_qsl(query)))
            target = (SITE / rel).resolve()
            if not target.is_file() or target.parent != SITE.resolve():
                self.send_error(404)
                return
            if target.suffix == ".txt":
                # Q13: a plain-text file the browser downloads rather than shows
                self._send(
                    200, target.read_bytes(), content_type="text/plain; charset=utf-8", attachment=target.name
                )
                return
            self._send(200, target.read_bytes())

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            fields = dict(parse_qsl(self.rfile.read(length).decode()))
            recorder.add(self.path, fields)
            if self.path.split("?")[0] == "/account.html":
                # Sign-in is checked server-side; the password never appears in a URL.
                user = fields.get("user", "")
                ok = user and fields.get("password") == "hunter2"
                self.send_response(303)
                self.send_header(
                    "Location", f"/account.html?user={quote(user)}&ok=1" if ok else "/login.html?error=1"
                )
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self._send(200, b"<!doctype html><title>Thanks</title><h1>Thanks, we received it.</h1>")

        def _send(
            self,
            status: int,
            body: bytes,
            *,
            content_type: str = "text/html; charset=utf-8",
            attachment: str = "",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            if attachment:
                self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(port: int = 0) -> tuple[str, Callable[[], None]]:
    """Start the fixture server on a background thread.

    Returns ``(base_url, stop)``. Port 0 picks a free ephemeral port. The
    server's :class:`Recorder` is reachable as ``stop.recorder``.
    """
    recorder = Recorder()
    server = ThreadingHTTPServer(("127.0.0.1", port), _handler(recorder))
    thread = threading.Thread(target=server.serve_forever, name="jevdual-fixture-server", daemon=True)
    thread.start()

    def stop() -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    stop.recorder = recorder  # type: ignore[attr-defined]
    return f"http://127.0.0.1:{server.server_port}", stop


if __name__ == "__main__":  # pragma: no cover - manual smoke run
    import time

    url, stop_server = serve(8765)
    print(f"serving {SITE} at {url} (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        stop_server()
