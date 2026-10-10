"""Real CLI scenarios with native driver and provider replaced at their boundaries."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from jevdual import visual_native
from jevdual.visual_decisions import VisualDecisionsClient
from PIL import Image

from tests.test_visual_inspection_session import operator as native_operator


@pytest.fixture
def operator(tmp_path, monkeypatch, capsys):
    return native_operator.__wrapped__(tmp_path, monkeypatch, capsys)


def spec(path, role="document_reference_match"):
    assets = path / "assets"
    assets.mkdir(exist_ok=True)
    image = assets / "source.png"
    Image.new("RGB", (100, 80), "white").save(image)
    asset = {"path": "assets/source.png", "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
             "resource_id": "task-resource", "revision": "task-revision", "page": 1,
             "render_recipe": "supplied_png"}
    data = {"version": 1, "role": role, "criterion": "Match the supplied page", "criterion_version": "v1", "target": 2}
    if role == "document_reference_match":
        data["reference"] = asset
    else:
        data.update(source=asset, rectangle=[0, 0, 100, 80], displayed_bounds=[429, 358, 100, 80],
                    orientation="upright", criterion="Retain the whole white subject")
    manifest = path / "request.json"
    manifest.write_text(json.dumps(data))
    return manifest, image


def record(path):
    receipts = [p for p in (path / "visual").glob("*.json") if p.name != "budget.json"]
    return json.loads(max(receipts, key=lambda p: p.stat().st_mtime_ns).read_text())


def provider(monkeypatch, answer=None, effect=None):
    seen = []
    async def response(request):
        seen.append(json.loads(request.content))
        if effect:
            effect()
        return httpx.Response(200, json={"model": "gpt-6-luna", "answers": [answer or {
            "type": "predicate", "name": "required", "probability": .99}], "usage": {"input_tokens": 100}})
    client = httpx.AsyncClient(transport=httpx.MockTransport(response))
    monkeypatch.setattr(visual_native, "make_provider", lambda: VisualDecisionsClient("fixture", client=client))
    return seen


@pytest.mark.parametrize("role", ["document_reference_match", "crop_subject_containment"])
def test_prepare_both_input_types_without_keys_or_actions(operator, role):
    world, path, run = operator
    manifest, _ = spec(path, role)
    code, out, err = run("visual-check", "--request", str(manifest))
    assert code == 4, err
    receipt = record(path)
    assert receipt["result"]["reason"] == "provider_unconfigured"
    assert receipt["request"]["role"] == role and not receipt["capture_atomic"]
    assert receipt["request"]["evidence"]["ownership_proven"] is False
    assert "no action" in out.lower() and not world.presses and not world.tool_calls
    assert "token" not in receipt["request"]["evidence"]["capture"]["target"]
    assert (path / "visual" / receipt["screenshot"]).is_file()
    assert not (path / "visual" / "budget.json").exists()


@pytest.mark.parametrize("role", ["document_reference_match", "crop_subject_containment"])
def test_explicit_provider_yields_bound_advisory_no_dispatch(operator, monkeypatch, role):
    world, path, run = operator
    manifest, _ = spec(path, role)
    seen = provider(monkeypatch)
    code, _, err = run("visual-check", "--request", str(manifest), "--provider", "decisions", "--disclose")
    assert code == 0, err
    receipt = record(path)
    assert receipt["result"]["p"] == .99
    assert receipt["result"]["execution_authority"] is False
    assert receipt["escalation"]["image_visible_to_s2"] is False
    assert len(seen) == 1 and len(seen[0]["input"][0]["content"]) == 3
    assert not world.presses and not world.tool_calls
    state = json.loads((path / "session.json").read_text())
    assert state["last_visual_check"]["result"]["evidence_digest"] == receipt["result"]["evidence_digest"]
    assert not (path / "grants.json").exists()


def test_no_disclosure_refuses_before_capture_or_provider(operator, monkeypatch):
    world, path, run = operator
    manifest, _ = spec(path)
    before = world.capture_calls
    monkeypatch.setattr(visual_native, "make_provider", lambda: pytest.fail("provider before disclosure"))
    code, _, error = run("visual-check", "--request", str(manifest), "--provider", "decisions")
    assert code == 4 and "pixels_withheld" in error
    assert before == world.capture_calls and not (path / "visual").exists()


@pytest.mark.parametrize("field,value,reason", [("secret_names", ["OPAQUE"], "pixels_withheld"),
                                               ("mode", "browser", "surface_unsupported")])
def test_unavailable_session_routes_do_not_capture(operator, field, value, reason):
    world, path, run = operator
    manifest, _ = spec(path)
    state = json.loads((path / "session.json").read_text())
    state[field] = value
    (path / "session.json").write_text(json.dumps(state))
    before = world.capture_calls
    code, _, error = run("visual-check", "--request", str(manifest))
    assert code == 4 and reason in error and before == world.capture_calls


def test_hash_changed_before_capture_cannot_call_provider(operator, monkeypatch):
    world, path, run = operator
    manifest, image = spec(path)
    Image.new("RGB", (100, 80), "red").save(image)
    before = world.capture_calls
    monkeypatch.setattr(visual_native, "make_provider", lambda: pytest.fail("provider on wrong source"))
    code, _, error = run("visual-check", "--request", str(manifest), "--provider", "decisions", "--disclose")
    assert code == 4 and "asset_hash_changed" in error and world.capture_calls == before


def test_source_changed_during_request_invalidates_advisory(operator, monkeypatch):
    _, path, run = operator
    manifest, image = spec(path)
    provider(monkeypatch, effect=lambda: image.write_bytes(b"changed"))
    code, _, _ = run("visual-check", "--request", str(manifest), "--provider", "decisions", "--disclose")
    assert code == 4
    receipt = record(path)
    assert receipt["result"]["status"] == "invalidated" and receipt["result"]["p"] is None
    assert json.loads((path / "session.json").read_text())["last_visual_check"] is None


def test_source_changed_during_provider_cleanup_invalidates_printed_receipt(operator, monkeypatch):
    _, path, run = operator
    manifest, image = spec(path)
    provider(monkeypatch)
    factory = visual_native.make_provider

    class ChangesOnExit:
        async def __aenter__(self):
            self.client = factory()
            return self.client

        async def __aexit__(self, *args):
            await self.client.aclose()
            image.write_bytes(b"changed during provider cleanup")

    monkeypatch.setattr(visual_native, "make_provider", ChangesOnExit)
    code, out, _ = run("visual-check", "--request", str(manifest), "--provider", "decisions", "--disclose")
    assert code == 4
    assert record(path)["result"]["status"] == "invalidated"
    assert record(path)["result"]["p"] is None
    assert '"p": 0.99' not in out


def test_receipt_publication_cannot_print_positive_after_detecting_source_change(operator, monkeypatch):
    _, path, run = operator
    manifest, image = spec(path)
    provider(monkeypatch)
    original = Path.write_text
    def changes_during_publication(file, data, *args, **kwargs):
        answer = original(file, data, *args, **kwargs)
        if file.parent == path / "visual" and file.name != "budget.json":
            image.write_bytes(b"changed during receipt publication")
        return answer
    monkeypatch.setattr(Path, "write_text", changes_during_publication)
    code, out, _ = run("visual-check", "--request", str(manifest), "--provider", "decisions", "--disclose")
    assert code == 4
    receipt = record(path)
    assert receipt["result"]["p"] is None and receipt["question"]["result"]["p"] is None
    assert receipt["result"]["status"] == "invalidated"
    assert '"p": 0.99' not in out


def test_look_invalidates_previous_visual_summary(operator, monkeypatch):
    _, path, run = operator
    manifest, _ = spec(path)
    provider(monkeypatch)
    assert run("visual-check", "--request", str(manifest), "--provider", "decisions", "--disclose")[0] == 0
    assert run("look")[0] == 0
    assert json.loads((path / "session.json").read_text())["last_visual_check"] is None


def test_repeat_new_generation_or_wording_does_not_reset_workflow_budget(operator, monkeypatch):
    _, path, run = operator
    manifest, _ = spec(path)
    seen = provider(monkeypatch)
    words = ("visual-check", "--request", str(manifest), "--provider", "decisions", "--disclose")
    assert run(*words)[0] == 0
    data = json.loads(manifest.read_text()); data["criterion"] = "Try a different wording"
    manifest.write_text(json.dumps(data))
    assert run(*words)[0] == 4
    assert len(seen) == 1
    assert record(path)["result"]["status"] == "budget_exhausted"


def test_refusal_keeps_native_status_no_fake_zero_probability(operator, monkeypatch):
    _, path, run = operator
    manifest, _ = spec(path)
    provider(monkeypatch, answer={"type": "refusal", "name": "required"})
    assert run("visual-check", "--request", str(manifest), "--provider", "decisions", "--disclose")[0] == 4
    assert record(path)["result"]["status"] == "refusal" and record(path)["result"]["p"] is None


def test_manifest_path_cannot_read_external_assets(operator, tmp_path):
    world, _, run = operator
    outsider = tmp_path / "outside.json"; outsider.write_text('{}')
    before = world.capture_calls
    code, _, error = run("visual-check", "--request", str(outsider))
    assert code == 4 and "asset_outside_session" in error and before == world.capture_calls


def test_visual_capture_reconciles_pending_action_before_replacing_effect_baseline(operator):
    world, path, run = operator
    manifest, _ = spec(path)
    state_path = path / "session.json"
    state = json.loads(state_path.read_text())
    state["pending"] = {"line": "click Seven", "op": "click", "driver_effect": "confirmed"}
    state["step"] = 1
    state_path.write_text(json.dumps(state))
    world.calc.press("7")  # historical delivered input, not an action from visual-check
    assert run("visual-check", "--request", str(manifest))[0] == 4
    assert json.loads(state_path.read_text())["pending"] is None
    records = [json.loads(line) for line in (path / "session.jsonl").read_text().splitlines()]
    receipt = next(item for item in records if item["kind"] == "receipt")
    assert receipt["effect"] == "confirmed"
    assert run("look")[0] == 0
    records = [json.loads(line) for line in (path / "session.jsonl").read_text().splitlines()]
    assert sum(item["kind"] == "receipt" for item in records) == 1


def test_duplicate_manifest_keys_are_rejected_before_capture(operator):
    world, path, run = operator
    manifest, _ = spec(path)
    content = manifest.read_text()
    manifest.write_text(content[:-1] + ', "target": 99}')
    before = world.capture_calls
    code, _, error = run("visual-check", "--request", str(manifest))
    assert code == 4 and "duplicate_manifest_field" in error and before == world.capture_calls


def test_preexisting_broad_readable_capture_directory_refuses(operator):
    world, path, run = operator
    manifest, _ = spec(path)
    (path / "visual").mkdir(mode=0o755)
    before = world.capture_calls
    code, _, error = run("visual-check", "--request", str(manifest))
    assert code == 4 and "visual_path_unsafe" in error and before == world.capture_calls


def test_native_capture_deadline_cancels_delayed_snapshot_without_replacing_baseline(operator, monkeypatch):
    import asyncio
    world, path, run = operator
    manifest, _ = spec(path)
    before = (path / "session.json").read_bytes()
    original = world.get_window_state
    finished = []
    async def delayed_snapshot(inp):
        await asyncio.sleep(.2)
        finished.append(True)
        return await original(inp)
    monkeypatch.setattr(world, "get_window_state", delayed_snapshot)
    code, _, error = run("visual-check", "--request", str(manifest), "--timeout", "0.01")
    assert code == 4 and "capture_timeout" in error
    assert not finished
    assert (path / "session.json").read_bytes() == before


def test_agent_explicit_service_and_text_handoff_invalidate_changed_snapshot(tmp_path):
    import asyncio
    import time
    from types import SimpleNamespace

    from jevdual.desktop import NativeAgent, StepOutcome
    from jevdual.desktop_s2 import NativeS2
    from jevdual.visual_decisions import VisualCallLedger

    from tests.test_visual_checks import evidence, request

    ev = replace(evidence(), capture_started=time.monotonic(), capture_finished=time.monotonic())
    req = request(evidence=ev, deadline_monotonic=time.monotonic()+10)
    menu = SimpleNamespace(title="Fixture", page_text="", candidates=[], omitted={})
    nm = SimpleNamespace(snapshot_id="observation", pid=11, window_id=22, menu=menu, app_name="Fixture")
    bridge = SimpleNamespace(last=nm)
    agent = NativeAgent(bridge, None, task="Inspect a page")
    async def response(_):
        return httpx.Response(200, json={"model":"gpt-6-luna", "answers":[{"name":"required","type":"predicate","probability":.99}]})
    async def call():
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as http:
            client = VisualDecisionsClient("fixture", client=http)
            return await agent.check_visual(req, client, VisualCallLedger(tmp_path / "budget.json"),
                                             is_current=lambda: True)
    result = asyncio.run(call())
    assert result.status == "valid"
    s2 = NativeS2(None)
    out = StepOutcome(1,"s2",nm)
    handoff = json.loads(s2.messages(agent,nm,"needs pixels",out)[1]["content"])["visual_check"]
    assert handoff["current_advisory_answer"] is True and handoff["result"]["p"] == .99
    assert handoff["image_visible_to_s2"] is False and not handoff["execution_authority"]
    assert handoff["question"]["target"]["id"] == "17"
    assert handoff["question"]["criterion"] == req.criterion
    assert handoff["question"]["reference"]["resource_id"] == "reference-1"
    assert "opaque-token" not in json.dumps(handoff)
    nm.snapshot_id="changed"
    handoff=json.loads(s2.messages(agent,nm,"changed",out)[1]["content"])["visual_check"]
    assert handoff["result"]["p"] is None and handoff["result"]["status"] == "invalidated"


def _agent_request():
    import time
    from types import SimpleNamespace

    from jevdual.desktop import NativeAgent, StepOutcome

    from tests.test_visual_checks import evidence, request

    ev = replace(evidence(), capture_started=time.monotonic(), capture_finished=time.monotonic())
    req = request(evidence=ev, deadline_monotonic=time.monotonic()+10)
    menu = SimpleNamespace(title="Fixture", page_text="", candidates=[], omitted={})
    nm = SimpleNamespace(snapshot_id="observation", pid=11, window_id=22, menu=menu, app_name="Fixture")
    agent = NativeAgent(SimpleNamespace(last=nm), None, task="Inspect a page")
    return agent, req, nm, StepOutcome(1, "s2", nm)


def test_text_handoff_cannot_resurrect_invalidated_owning_bridge():
    from jevdual.desktop_s2 import NativeS2

    from tests.test_visual_checks import result
    agent, req, nm, out = _agent_request()
    agent.visual_check = (req, result(req))
    agent.visual_check_current = lambda: True
    agent.bridge.last = None
    handoff = json.loads(NativeS2(None).messages(agent, nm, "bridge invalidated", out)[1]["content"])["visual_check"]
    assert handoff["current_advisory_answer"] is False
    assert handoff["result"]["p"] is None and handoff["question"]["result"]["p"] is None


def test_final_visual_handoff_redacts_result_and_escalation_metadata():
    from jevdual.desktop_s2 import NativeS2
    from jevdual.secrets import SecretStore
    from jevdual.visual_checks import VisualCheckResult
    fixture_value = "synthetic-credential-for-redaction-test"
    agent, req, nm, out = _agent_request()
    agent.secrets = SecretStore({"fixture": fixture_value})
    req = replace(req, request_id="request-"+fixture_value, criterion="Compare "+fixture_value)
    result = VisualCheckResult(req.request_id, req.evidence.digest, req.generation, req.role,
                               "unavailable", reason="pixels_withheld", request_digest=req.digest)
    agent.visual_check = (req, result)
    raw = NativeS2(None).messages(agent, nm, "withheld", out)[1]["content"]
    assert fixture_value not in raw
    assert json.loads(raw)["visual_check"]["result"]["status"] == "unavailable"


async def test_library_requires_workflow_source_guard_before_provider_dispatch(tmp_path):
    from tests.test_visual_checks import result
    agent, req, _, _ = _agent_request()
    calls = []
    class Provider:
        async def check(self, *args, **kwargs):
            calls.append(True)
            return result(req)
    answer = await agent.check_visual(req, Provider(), None)
    assert not calls
    assert answer.status == "unavailable" and answer.reason == "source_current_unavailable"


async def test_library_source_guard_is_retained_for_final_handoff(tmp_path):
    from jevdual.desktop_s2 import NativeS2
    from jevdual.visual_decisions import VisualCallLedger
    agent, req, nm, out = _agent_request()
    source = tmp_path / "owned-source-revision"
    source.write_text("original")
    async def response(_):
        return httpx.Response(200, json={"model":"gpt-6-luna", "answers":[{"name":"required","type":"predicate","probability":.99}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as http:
        answer = await agent.check_visual(req, VisualDecisionsClient("fixture", client=http),
                                           VisualCallLedger(tmp_path / "ledger.json"),
                                           is_current=lambda: source.read_text()=="original")
    assert answer.status == "valid"
    source.write_text("changed")
    handoff = json.loads(NativeS2(None).messages(agent,nm,"reference changed",out)[1]["content"])["visual_check"]
    assert not handoff["current_advisory_answer"]
    assert handoff["result"]["p"] is None and handoff["question"]["result"]["p"] is None
