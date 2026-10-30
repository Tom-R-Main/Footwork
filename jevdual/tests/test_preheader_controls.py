"""Diagnostic sensitivity; these tests do not qualify native input or Chrome."""

from __future__ import annotations

import hashlib
import importlib.util
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from jevdual.app_qualification import TicketFixture
from jevdual.ticket_evidence import form_body

spec = importlib.util.spec_from_file_location(
    "preheader_controls", Path(__file__).parents[1] / "scripts/preheader_controls.py"
)
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)


def test_retry_summary_keeps_causal_event_and_excludes_headers_and_unrelated_values():
    log = {
        "constants": {"logEventTypes": {"HTTP_TRANSACTION_RESTART_AFTER_ERROR": 2, "OTHER": 3}},
        "events": [
            {
                "type": 2,
                "phase": 0,
                "time": "12",
                "source": {"id": 7},
                "params": {"net_error": -324, "headers": ["secret: value"], "url": "private"},
            },
            {"type": 3, "params": {"secret": "unrelated"}},
        ],
    }
    assert controls.network_summary(log) == [
        {
            "name": "HTTP_TRANSACTION_RESTART_AFTER_ERROR",
            "phase": 0,
            "time": "12",
            "source": {"id": 7},
            "params": {"net_error": -324},
        }
    ]


def test_handler_observation_distinguishes_requests_from_deduplicated_rows(tmp_path):
    expected = {
        "request_id": uuid.uuid4().hex,
        "artifact": "a.png",
        "orientation": "clockwise90",
        "digest": hashlib.sha256(b"test").hexdigest(),
    }
    with TicketFixture(tmp_path / "service") as fixture:
        handlers = controls.handler_observer(fixture)
        for _ in range(2):
            with urlopen(
                Request(fixture.url + "/tickets", data=form_body(expected), method="POST"), timeout=5
            ) as response:
                response.read()
        snapshot = fixture.store.snapshot()
    assert len(handlers) == len(snapshot["ingress"]) == 2
    assert len(snapshot["tickets"]) == 1
    assert handlers[0]["connection"] != handlers[1]["connection"]
    assert snapshot["ingress"][0]["body_sha"] == snapshot["ingress"][1]["body_sha"]


def test_http_disconnect_control_records_one_call_one_ingress_and_lost_reply(tmp_path):
    result = controls.run_slot("http", "disconnect", tmp_path / "slot")
    assert result["client"]["activation_calls"] == 1
    assert result["client"]["error"] is not None
    assert result["ingresses"] == result["tickets"] == len(result["handlers"]) == 1
    assert result["native_qualification"] is False
