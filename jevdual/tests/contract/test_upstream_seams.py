"""Contract tests pinning the browser-use 0.13.10 seams jevdual depends on.

Each assertion names the jevdual module that relies on it. If a bump of
browser-use turns one of these red, that module needs a look before the
upgrade lands. Nothing here launches a browser; it is all inspect/import.
"""

from __future__ import annotations

import dataclasses
import importlib.metadata
import inspect
import re
import typing

import pytest

PINNED_VERSION = "0.13.10"


def _src(obj) -> str:
    return inspect.getsource(obj)


# --------------------------------------------------------------------------- version


def test_browser_use_version_is_pinned():
    # every module: the whole suite is written against this exact version
    assert importlib.metadata.version("browser_use") == PINNED_VERSION


# --------------------------------------------------------------------------- agent.py


def test_agent_step_phase_order():
    # agent.py: DualProcessAgent overrides _get_next_action and relies on step()
    # calling the four phases in this order
    from browser_use.agent.service import Agent

    src = _src(Agent.step)
    positions = [src.find(name) for name in ("_prepare_context", "_get_next_action", "_execute_actions", "_post_process")]
    assert all(p >= 0 for p in positions), positions
    assert positions == sorted(positions), positions


def test_get_next_action_signature_and_assignment():
    # agent.py: the override must accept (self, browser_state_summary) and set state.last_model_output
    from browser_use.agent.service import Agent
    from browser_use.browser.views import BrowserStateSummary

    sig = inspect.signature(Agent._get_next_action)
    assert list(sig.parameters) == ["self", "browser_state_summary"]
    assert sig.parameters["browser_state_summary"].annotation is BrowserStateSummary
    assert "self.state.last_model_output = " in _src(Agent._get_next_action)


def test_execute_actions_reads_last_model_output_into_multi_act():
    # agent.py / bridge.py: our AgentOutput.action list is what multi_act executes
    from browser_use.agent.service import Agent

    src = _src(Agent._execute_actions)
    assert "self.state.last_model_output.action" in src
    assert "self.multi_act(" in src
    sig = inspect.signature(Agent.multi_act)
    assert list(sig.parameters) == ["self", "actions"]


def test_setup_action_models_defines_action_model_and_agent_output():
    # bridge.py: builds self.ActionModel(**{name: params}) and self.AgentOutput(...)
    from browser_use.agent.service import Agent

    src = _src(Agent._setup_action_models)
    assert "self.ActionModel = self.tools.registry.create_action_model(" in src
    variants = set(re.findall(r"AgentOutput\.type_with_custom_actions\w*", src))
    assert variants == {
        "AgentOutput.type_with_custom_actions",
        "AgentOutput.type_with_custom_actions_no_thinking",
        "AgentOutput.type_with_custom_actions_flash_mode",
    }, variants


def test_agent_output_reasoning_fields_optional_action_required():
    # bridge.py: an S1 step emits AgentOutput with only action (+ a synthesized memory line)
    from browser_use.agent.views import AgentOutput

    for name in ("thinking", "evaluation_previous_goal", "memory", "next_goal"):
        assert AgentOutput.model_fields[name].is_required() is False, name
    assert AgentOutput.model_fields["action"].is_required() is True


# --------------------------------------------------------------------------- tools.py / bridge.py


def test_tools_action_decorator_signatures():
    # tools.py: act_toward_goal is registered through Tools.action
    from browser_use.tools.registry.service import Registry
    from browser_use.tools.service import Tools

    assert list(inspect.signature(Tools.action).parameters) == ["self", "description", "kwargs"]
    reg_params = inspect.signature(Registry.action).parameters
    assert list(reg_params) == ["self", "description", "param_model", "domains", "allowed_domains", "terminates_sequence"]


# Names as they exist in 0.13.10. Surprises relative to the plan's assumptions:
#   - the tab switch action is named ``switch`` (param ``tab_id``), not ``switch_tab``
#   - ``go_back`` uses NoParamsAction, whose only field is a free-text ``description``
#   - ``input`` has a third field ``clear``; ``done`` has ``files_to_display``
EXPECTED_ACTIONS = {
    "click": ["index"],
    "input": ["index", "text", "clear"],
    "select_dropdown": ["index", "text"],
    "dropdown_options": None,
    "scroll": ["down", "pages", "index"],
    "go_back": ["description"],
    "send_keys": ["keys"],
    "switch": ["tab_id"],
    "close": ["tab_id"],
    "done": ["text", "success", "files_to_display"],
    "navigate": ["url", "new_tab"],
    "search": ["query", "engine"],
    "wait": ["seconds"],
    "evaluate": ["code"],
    "extract": None,
    "find_text": None,
    "find_elements": None,
    "search_page": None,
    "screenshot": None,
    "upload_file": None,
    "read_file": None,
    "write_file": None,
    "replace_file": None,
    "save_as_pdf": None,
}

TERMINATES_SEQUENCE = {"go_back", "switch", "evaluate", "navigate", "search"}


@pytest.fixture(scope="module")
def registry_actions():
    from browser_use.tools.service import Tools

    return Tools().registry.registry.actions


def test_default_registry_action_names(registry_actions):
    # bridge.py: every operation in the Jev policy maps to one of these names
    assert set(registry_actions) == set(EXPECTED_ACTIONS), sorted(set(registry_actions) ^ set(EXPECTED_ACTIONS))


def test_default_registry_param_fields(registry_actions):
    # bridge.py: the exact kwargs we build for each action
    for name, fields in EXPECTED_ACTIONS.items():
        if fields is None:
            continue
        assert list(registry_actions[name].param_model.model_fields) == fields, name


def test_terminating_actions(registry_actions):
    # arbiter.py: navigation-type actions abort the rest of a multi-action queue
    got = {n for n, a in registry_actions.items() if a.terminates_sequence}
    assert got == TERMINATES_SEQUENCE, got


# --------------------------------------------------------------------------- menu.py


def test_selector_map_annotation():
    # menu.py: the Jev menu is built from dict[int, EnhancedDOMTreeNode]
    from browser_use.dom.views import EnhancedDOMTreeNode, SerializedDOMState

    hints = typing.get_type_hints(SerializedDOMState)
    assert hints["selector_map"] == dict[int, EnhancedDOMTreeNode]


def test_serializer_allocates_indices_from_backend_node_id():
    # menu.py: selector_index keys are allocated per backend_node_id and map to original nodes
    from browser_use.dom.serializer.serializer import DOMTreeSerializer

    assert list(inspect.signature(DOMTreeSerializer._allocate_selector_index).parameters) == ["self", "backend_node_id"]
    assert "self._selector_map[node.selector_index] = node.original_node" in _src(DOMTreeSerializer)


def test_serialize_accessible_elements_contract():
    # menu.py / patch.py: entry point returns (SerializedDOMState, timing dict) and runs paint-order removal
    from browser_use.dom.serializer.serializer import DOMTreeSerializer

    sig = inspect.signature(DOMTreeSerializer.serialize_accessible_elements)
    assert list(sig.parameters) == ["self"]
    src = _src(DOMTreeSerializer)
    assert "PaintOrderRemover" in src
    assert "paint_order_filtering" in src
    assert "calculate_paint_order" in src


# --------------------------------------------------------------------------- patch.py (R2 snapshot lookup)


def test_build_snapshot_lookup_signature():
    # patch.py: native replacement must accept the same (snapshot, device_pixel_ratio) shape
    from browser_use.dom import enhanced_snapshot as es

    params = inspect.signature(es.build_snapshot_lookup).parameters
    assert list(params) == ["snapshot", "device_pixel_ratio"]
    assert params["device_pixel_ratio"].default == 1.0


# Note: there is no ``is_visible`` on EnhancedSnapshotNode; visibility is computed later in
# DomService from ``bounds`` and computed_styles. The bounding box field is ``bounds``.
SNAPSHOT_NODE_FIELDS = [
    "is_clickable",
    "cursor_style",
    "bounds",
    "clientRects",
    "scrollRects",
    "computed_styles",
    "paint_order",
    "stacking_contexts",
    "input_value",
    "input_checked",
]


def test_enhanced_snapshot_node_fields():
    # patch.py: the native SnapshotLookup must reproduce exactly these fields
    from browser_use.dom.views import EnhancedSnapshotNode

    assert [f.name for f in dataclasses.fields(EnhancedSnapshotNode)] == SNAPSHOT_NODE_FIELDS


def test_required_computed_styles_and_sensitive_inputs():
    # patch.py / secrets.py: style index order and the sensitive-value filter the port must preserve
    from browser_use.dom import enhanced_snapshot as es

    assert es.REQUIRED_COMPUTED_STYLES == [
        "display",
        "visibility",
        "opacity",
        "overflow",
        "overflow-x",
        "overflow-y",
        "cursor",
        "pointer-events",
        "position",
        "background-color",
    ]
    assert {"password", "file", "hidden"} <= set(es._SENSITIVE_INPUT_TYPES)
    assert es._SENSITIVE_AUTOCOMPLETE_PREFIXES == ("cc-", "one-time-code")


# --------------------------------------------------------------------------- patch.py (R1 paint order)


def test_paint_order_module_surface():
    # patch.py: native replacement mirrors Rect / RectUnionPure / PaintOrderRemover(root).calculate_paint_order()
    from browser_use.dom.serializer import paint_order as po
    from browser_use.dom.views import SimplifiedNode

    for name in ("Rect", "RectUnionPure", "PaintOrderRemover"):
        assert hasattr(po, name), name
    init = inspect.signature(po.PaintOrderRemover.__init__)
    assert list(init.parameters) == ["self", "root"]
    assert init.parameters["root"].annotation is SimplifiedNode
    assert callable(po.PaintOrderRemover.calculate_paint_order)
    assert list(inspect.signature(po.PaintOrderRemover.calculate_paint_order).parameters) == ["self"]


# --------------------------------------------------------------------------- effects.py (R3 hashing)


def test_element_hash_methods_use_sha256():
    # effects.py: the batched native hash must be byte-identical to these
    from browser_use.dom.views import EnhancedDOMTreeNode

    for name in ("compute_stable_hash", "element_hash", "parent_branch_hash"):
        assert hasattr(EnhancedDOMTreeNode, name), name
    src = _src(EnhancedDOMTreeNode.compute_stable_hash) + _src(EnhancedDOMTreeNode.parent_branch_hash)
    assert "hashlib.sha256" in src


# --------------------------------------------------------------------------- patch.py (R6 orjson)


def test_cdp_use_client_decodes_with_json_loads_raw():
    # patch.py: the orjson swap targets this exact call site
    import cdp_use.client as cdp_client

    assert "json.loads(raw)" in _src(cdp_client)


# --------------------------------------------------------------------------- secrets.py


def test_sensitive_data_accepts_domain_scoped_dict():
    # secrets.py: Agent(sensitive_data=...) takes {key: value} or {domain_pattern: {key: value}}
    from browser_use.agent.service import Agent

    ann = inspect.signature(Agent.__init__).parameters["sensitive_data"].annotation
    assert ann == (dict[str, str | dict[str, str]] | None), ann


def test_sensitive_data_resolved_per_url_in_registry():
    # secrets.py: values are substituted at dispatch time, scoped by domain pattern against current_url
    from browser_use.tools.registry.service import Registry

    params = inspect.signature(Registry._replace_sensitive_data).parameters
    assert list(params) == ["self", "params", "sensitive_data", "current_url"]
    src = _src(Registry._replace_sensitive_data)
    assert "match_url_with_domain_pattern(current_url, domain_or_key)" in src
    assert "<secret>" in src
