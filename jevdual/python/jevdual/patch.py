"""Import-time patches that swap upstream hot paths for faster implementations.

Every patch is guarded by the contract tests in ``tests/contract`` (task A4), is
idempotent, and can be disabled with ``JEVDUAL_PURE_PY=1``. ``active_patches()``
is written into the trace header so a run records what it ran with.

R6: cdp-use decodes every CDP message with the stdlib ``json.loads``; on
DOMSnapshot payloads that is 12 to 75 ms per step. ``orjson`` is already a
dependency, so this swaps the decoder and keeps ``json.dumps`` for sending.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger("jevdual.patch")

_ACTIVE: dict[str, bool] = {}


class _JsonShim:
    """Stand-in for the ``json`` module inside ``cdp_use.client``.

    ``loads`` is orjson (accepts str or bytes, returns the same dict shape).
    ``dumps`` stays stdlib because the websocket send path expects ``str``.
    """

    @staticmethod
    def loads(raw: str | bytes) -> Any:
        import orjson

        return orjson.loads(raw)

    dumps = staticmethod(json.dumps)


def install_orjson_decode() -> bool:
    """Route cdp-use message decoding through orjson. Returns True if active."""
    if os.environ.get("JEVDUAL_PURE_PY") == "1":
        return False
    if _ACTIVE.get("orjson_decode"):
        return True
    from cdp_use import client

    if client.json is not json and client.json is not _JsonShim:  # pragma: no cover
        log.warning("cdp_use.client.json is not the stdlib module; leaving it alone")
        return False
    client.json = _JsonShim  # type: ignore[assignment]
    _ACTIVE["orjson_decode"] = True
    log.info("jevdual patch active: cdp-use orjson decode")
    return True


def install() -> dict[str, bool]:
    """Install every available patch; returns the active map for the trace header."""
    install_orjson_decode()
    return active_patches()


def active_patches() -> dict[str, bool]:
    return dict(_ACTIVE)
