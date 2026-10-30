from __future__ import annotations

from types import SimpleNamespace

import pytest
from jevdual.ax import AXError
from jevdual.capability.backend import BoundResource, ScopedBackend
from jevdual.capability.contracts import CapabilityError


class FakeBridge:
    pid, window_id = 3, 4

    def __init__(self, document):
        self.content = "Original prefix\n"
        self.label = "Document body"
        self.document = str(document)
        self.dispatches = 0
        self.effect = "confirmed"
        self.ax = SimpleNamespace(
            AXError=AXError,
            document_path=lambda *a: self.document,
            Frame=lambda *a: a,
            resolve=lambda *a: self,
            value=lambda el: el.content,
            can_insert=lambda el: True,
        )

    async def observe(self):
        candidate = SimpleNamespace(
            id=1, label=self.label, role="textbox", operations=("append",), value=None
        )
        menu = SimpleNamespace(
            candidates=(candidate,),
            title="fixture.txt",
            url="",
            page_text=self.content,
            omitted={},
            candidate=lambda cid: candidate if cid == 1 else None,
        )
        return SimpleNamespace(
            menu=menu,
            app_name="TextEdit",
            values={1: self.content},
            frames={1: (0, 0, 100, 100)},
            ax_roles={1: "AXTextArea"},
            elements_complete=True,
            truncated=False,
            degraded=False,
        )

    async def act(self, snapshot, operation, cid, text, *, append_precondition=None):
        assert append_precondition.value == snapshot.values[cid]
        assert append_precondition.role == snapshot.ax_roles[cid]
        assert append_precondition.frame == snapshot.frames[cid]
        self.dispatches += 1
        self.content += text
        return SimpleNamespace(dispatched=True, effect=self.effect, error_code=None, summary="")


@pytest.fixture
def setup(tmp_path, monkeypatch):
    from jevdual.capability import backend as backend_module

    # The fake below models TextEdit, independently of the test runner's host.
    monkeypatch.setattr(backend_module, "sys", SimpleNamespace(platform="darwin"))
    scope = {
        "task": "fixture",
        "source": {"pid": 1, "window_id": 2, "url": "http://127.0.0.1:8000/"},
        "destination": {"pid": 3, "window_id": 4, "document": str(tmp_path / "fixture.txt")},
    }
    backend = ScopedBackend(scope)
    bridge = FakeBridge(tmp_path / "fixture.txt")
    resource = backend.resource_id("destination")
    backend.bound[resource] = BoundResource("destination", None, bridge, None)
    return backend, bridge, resource


async def test_offered_target_appends_to_exact_prefix_and_reads_back(setup):
    backend, bridge, resource = setup
    observed = await backend.observe(resource)
    target = observed["elements"][0]["target"]
    validated = await backend.validate(resource, observed["observation"], target, "append", {"text": "17.25"})
    delivered = await backend.dispatch(validated)
    readback = await backend.readback(validated)
    assert delivered.phase == "sent"
    assert readback["outcome"] == "applied"
    assert bridge.content == "Original prefix\n17.25"
    assert readback["persistence"] == "not_checked"


@pytest.mark.parametrize("change", ["content", "label", "document"])
async def test_changed_target_content_or_document_sends_nothing(setup, change):
    backend, bridge, resource = setup
    observed = await backend.observe(resource)
    setattr(bridge, change, "different")
    with pytest.raises(CapabilityError):
        await backend.validate(
            resource, observed["observation"], observed["elements"][0]["target"], "append", {"text": "17.25"}
        )
    assert bridge.dispatches == 0


async def test_new_observation_expires_prior_target_and_refused_delivery_is_unknown(setup):
    backend, bridge, resource = setup
    first = await backend.observe(resource)
    await backend.observe(resource)
    with pytest.raises(CapabilityError, match="expired"):
        backend.offered(first["elements"][0]["target"])
    observed = await backend.observe(resource)
    validated = await backend.validate(
        resource, observed["observation"], observed["elements"][0]["target"], "append", {"text": "17.25"}
    )
    bridge.effect = "refused"  # a bridge label is insufficient evidence of non-delivery
    assert (await backend.dispatch(validated)).phase == "ambiguous"


def test_restart_preserves_logical_resource_key_but_loses_live_incarnation(setup):
    backend, _, resource = setup
    restarted = ScopedBackend(backend.scope)
    assert restarted.resource_id("destination") == resource
    assert not restarted.same_incarnation(resource)


def test_scope_cannot_use_remote_browser_or_relative_document(setup):
    backend, _, _ = setup
    scope = {**backend.scope, "source": {**backend.scope["source"], "url": "https://example.com/"}}
    with pytest.raises(CapabilityError):
        ScopedBackend(scope)


async def test_known_append_guard_is_no_send_but_other_native_error_remains_unknown(setup):
    from jevdual.native import NativeBridgeError

    backend, bridge, resource = setup
    observed = await backend.observe(resource)
    validated = await backend.validate(
        resource, observed["observation"], observed["elements"][0]["target"], "append", {"text": "17.25"}
    )

    async def stale(*args, **kwargs):
        raise NativeBridgeError("stale", "snapshot changed before input")

    bridge.act = stale
    with pytest.raises(CapabilityError) as caught:
        await backend.dispatch(validated)
    assert caught.value.code == "stale" and bridge.dispatches == 0

    async def other(*args, **kwargs):
        raise NativeBridgeError("not_key", "possibly prepared input before failure")

    bridge.act = other
    with pytest.raises(NativeBridgeError):
        await backend.dispatch(validated)
