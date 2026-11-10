"""Native acceptance fixture/oracle tests; these never launch a browser or send native input."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


@pytest.fixture
def module():
    path = Path(__file__).resolve().parents[1] / "scripts/native_form_acceptance.py"
    spec = importlib.util.spec_from_file_location("native_form_acceptance", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def served(module, tmp_path):
    fixture = module.Fixture(tmp_path)
    server = module.server_for(fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield fixture, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    assert not thread.is_alive()


def post(url, path, payload):
    request = Request(url + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def test_server_records_backing_targets_and_distinguishes_input_from_persistence(module, served, tmp_path):
    fixture, url = served
    domain = module.DOMAINS[0]
    assert post(url, "/event", {"kind": "manage", "domain": domain, "backing_domain": domain})["ok"]
    post(url, "/event", {"kind": "input", "domain": domain, "field_id": domain + ":2", "value": "ns1.example.test"})
    assert fixture.state()["version"] == 0
    assert fixture.state()["domains"][domain]["fields"][1]["value"] == ""
    fields = [{"id": f"{domain}:{i + 2}", "value": value} for i, value in enumerate(module.EXPECTED)]
    assert post(url, "/save", {"domain": domain, "mode": "Custom DNS", "fields": fields}) == {"ok": True, "version": 1}
    persisted = json.loads((tmp_path / "persisted.json").read_text())
    assert persisted["domains"][domain]["fields"] == fields
    assert persisted["domains"][module.DOMAINS[1]]["mode"] == "Basic DNS"
    with urlopen(url + "/", timeout=5) as response:
        page = response.read().decode()
    assert all(value in page for value in module.EXPECTED)
    assert fixture.state()["events"][-1]["kind"] == "page_load"
    assert fixture.state()["events"][-1]["version"] == 1
    ledger = [json.loads(line) for line in (tmp_path / "server-ledger.jsonl").read_text().splitlines()]
    assert [e["kind"] for e in ledger] == ["manage", "input", "save", "page_load"]


@pytest.mark.parametrize("invalid", ["domain", "duplicate_id", "other_domain_field", "extra_field_property", "mode"])
def test_save_rejects_invalid_or_cross_domain_backing_identity(module, served, invalid):
    fixture, url = served
    domain = module.DOMAINS[0]
    payload = {"domain": domain, "mode": "Custom DNS", "fields": [
        {"id": f"{domain}:1", "value": "ns1.example.test"},
        {"id": f"{domain}:2", "value": "ns2.example.test"},
    ]}
    if invalid == "domain":
        payload["domain"] = "real-domain.invalid"
    elif invalid == "duplicate_id":
        payload["fields"][1]["id"] = payload["fields"][0]["id"]
    elif invalid == "other_domain_field":
        payload["fields"][1]["id"] = module.DOMAINS[1] + ":2"
    elif invalid == "extra_field_property":
        payload["fields"][1]["unexpected"] = True
    else:
        payload["mode"] = "Basic DNS"
    with pytest.raises(HTTPError) as caught:
        post(url, "/save", payload)
    assert caught.value.code == 400
    assert fixture.state()["version"] == 0 and fixture.state()["events"] == []


def test_page_includes_budget_pressure_without_recording_a_fake_load(module, tmp_path):
    fixture = module.Fixture(tmp_path)
    page = fixture.page(record_load=False).decode()
    assert page.count('onclick="event.preventDefault()"') == 180
    assert page.index("Reference 179") < page.index('id="combo"')
    assert 'role="combobox"' in page and 'role="listbox"' in page
    assert "input.placeholder='Nameserver '" in page
    assert fixture.state()["events"] == []


def test_cli_commands_use_owned_pid_scope_and_native_public_interface(module, tmp_path, monkeypatch):
    commands = []

    def run(argv, **kwargs):
        commands.append(argv)
        assert kwargs["timeout"] == 120
        return subprocess.CompletedProcess(argv, 0, "fixture output", "")

    monkeypatch.setattr(module.subprocess, "run", run)
    runner = module.Acceptance(tmp_path, "/owned/footwork", "http://127.0.0.1:1234/", "fixture nonce", 4242)
    runner.start()
    assert commands[0][commands[0].index("--pid") + 1] == "4242"
    assert commands[0][commands[0].index("--native-url") + 1] == "http://127.0.0.1:1234/"
    assert commands[0][commands[0].index("--native-title") + 1] == "fixture nonce"
    assert "--browser" not in commands[0]
    runner.command("do", "type", "Nameserver 1", "ns1.example.test")
    assert commands[1][0:5] == ["/owned/footwork", "do", "type", "Nameserver 1", "ns1.example.test"]
    assert "--no-judge" in commands[1]
    assert json.loads((tmp_path / "command-02.json").read_text())["returncode"] == 0


def test_cli_failure_cannot_be_reported_as_acceptance(module, tmp_path, monkeypatch):
    monkeypatch.setattr(module.subprocess, "run", lambda argv, **kwargs: subprocess.CompletedProcess(argv, 4, "", "target missing"))
    runner = module.Acceptance(tmp_path, "/owned/footwork", "http://127.0.0.1:1234/", "fixture nonce", 4242)
    with pytest.raises(AssertionError, match="returned 4"):
        runner.command("do", "click", "Save DNS changes")
    assert not (tmp_path / "acceptance.json").exists()
