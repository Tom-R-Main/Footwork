import pytest
from browser_use.agent.views import AgentOutput
from browser_use.tools.service import Tools
from jevdual.bridge import Bridge, BridgeError, assert_fresh
from jevdual.menu import Candidate, Menu
from jevdual.policy import Decision


@pytest.fixture(scope="module")
def bridge():
    am = Tools().registry.create_action_model()
    return Bridge(am, AgentOutput.type_with_custom_actions(am))


def decision(op, target=None, **nouls):
    return Decision(
        operation=op,
        operation_confidence=0.8,
        operation_probabilities={op: 0.8},
        target=target,
        target_confidence=0.7 if target is not None else None,
        target_probabilities={target: 0.7} if target is not None else {},
        alternates=(),
        nouls={"goal_done": 0.1, "stuck": 0.05, "destructive": 0.02, **nouls},
        model="jev-1.13.0",
        request_tokens=100,
        latency_ms=300.0,
    )


MENU = Menu(
    url="http://s/",
    title="Home",
    page_text="hi",
    candidates=(
        Candidate(id=3, label="About", role="a", operations=("click",), href="/about.html"),
        Candidate(id=5, label="Search", role="input", operations=("type", "click", "enter"), input_type="search"),
        Candidate(id=8, label="Topic", role="select", operations=("select", "click"), options=("a", "b")),
        Candidate(id=9, label="Feed", role="div", operations=("scroll",)),
    ),
    by_operation={},
)


def dumped(b):
    return [a.model_dump(exclude_unset=True) for a in b.output.action]


def test_click_and_memory(bridge):
    b = bridge.build(decision("click", 3), MENU, step=2)
    assert dumped(b) == [{"click": {"index": 3}}]
    assert b.proposed[0].name == "click" and b.proposed[0].params == {"index": 3}
    assert b.memory_line.startswith("S1 step 2: click [3] 'About' p=0.70")
    assert b.output.memory == b.memory_line


def test_type_select_enter_scroll(bridge):
    assert dumped(bridge.build(decision("type", 5), MENU, step=1, text="hello")) == [{"input": {"index": 5, "text": "hello", "clear": True}}]
    assert dumped(bridge.build(decision("select", 8), MENU, step=1, text="b")) == [{"select_dropdown": {"index": 8, "text": "b"}}]
    assert dumped(bridge.build(decision("enter", 5), MENU, step=1)) == [{"click": {"index": 5}}, {"send_keys": {"keys": "Enter"}}]
    assert dumped(bridge.build(decision("scroll", 9), MENU, step=1)) == [{"scroll": {"down": True, "pages": 1.0, "index": 9}}]


def test_non_targeted(bridge):
    assert dumped(bridge.build(decision("scroll_page"), MENU, step=1)) == [{"scroll": {"down": True, "pages": 1.0}}]
    assert dumped(bridge.build(decision("back"), MENU, step=1)) == [{"go_back": {}}]
    assert dumped(bridge.build(decision("wait"), MENU, step=1)) == [{"wait": {"seconds": 2}}]
    assert dumped(bridge.build(decision("done"), MENU, step=1, done_text="ok")) == [{"done": {"text": "ok", "success": True}}]
    blocked = dumped(bridge.build(decision("blocked"), MENU, step=1, blocked_reason="login wall"))
    assert blocked[0]["done"]["success"] is False and "login wall" in blocked[0]["done"]["text"]


def test_errors(bridge):
    with pytest.raises(BridgeError) as e:
        bridge.build(decision("type", 5), MENU, step=1)
    assert e.value.reason == "text_required"
    with pytest.raises(BridgeError) as e:
        bridge.build(decision("click", 42), MENU, step=1)
    assert e.value.reason == "target_missing"
    with pytest.raises(BridgeError) as e:
        bridge.build(decision("type", 3), MENU, step=1, text="x")
    assert e.value.reason == "unsupported"
    with pytest.raises(BridgeError) as e:
        bridge.build(decision("teleport"), MENU, step=1)
    assert e.value.reason == "unknown_operation"


class _State:
    def __init__(self, url, ids):
        self.url = url
        self.dom_state = type("D", (), {"selector_map": {i: object() for i in ids}})()


class _Agent:
    def __init__(self, cached):
        self.browser_session = type("S", (), {"_cached_browser_state_summary": cached})()


def test_freshness_guard():
    state = _State("http://s/", [3, 5])
    assert_fresh(_Agent(state), state, MENU, decision("click", 3))
    with pytest.raises(BridgeError) as e:
        assert_fresh(_Agent(_State("http://s/", [3])), state, MENU, decision("click", 3))
    assert e.value.reason == "stale"
    with pytest.raises(BridgeError):
        assert_fresh(_Agent(state), state, MENU, decision("click", 8))  # 8 not in selector map
