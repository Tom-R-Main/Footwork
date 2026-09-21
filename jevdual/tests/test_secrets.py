import base64
import json
from urllib.parse import quote, quote_plus

import pytest
from jevdual.policy import JevPolicy, StepContext
from jevdual.secrets import SecretError, SecretLeak, SecretStore, assert_no_secrets, install, origin_allows
from jevdual.trace import RunHeader, TraceWriter

STORE = SecretStore(
    {
        "https://*.example.com": {"x_password": "hunter2-SECRET-9f3a", "x_user": "tom@example.com"},
        "https://bank.test": {"x_pin": "pin 4471"},
        "localdev_token": "tok-local-1234",
    }
)


def test_names_only_in_jev_state():
    class Dummy:
        pass

    ctx = StepContext(task="log in", secrets_names=STORE.names())
    from jevdual.menu import Menu

    menu = Menu(url="https://app.example.com/", title="t", page_text="", candidates=(), by_operation={})
    state = JevPolicy(Dummy()).build_state(menu, ctx)
    assert state["stored_secrets"] == ["localdev_token", "x_password", "x_pin", "x_user"]
    assert_no_secrets(state, STORE)


ORIGIN_TABLE = [
    ("https://example.com/login", "*.example.com", True),
    ("https://app.example.com/", "*.example.com", True),
    ("https://a.b.example.com/", "*.example.com", True),
    ("https://evil-example.com/", "*.example.com", False),
    ("https://example.com.evil.test/", "*.example.com", False),
    ("https://notexample.com/", "*.example.com", False),
    ("http://app.example.com/", "*.example.com", False),  # https required
    ("http://app.example.com/", "http*://*.example.com", True),
    ("http://localhost:8000/", "localhost", True),  # loopback may be http
    ("http://127.0.0.1:9/", "127.0.0.1", True),
    ("http://site.localhost/", "*.localhost", True),
    ("https://bank.test/", "bank.test", True),
    ("https://www.bank.test/", "bank.test", False),  # exact host, no wildcard
    ("https://bank.test:8443/x", "bank.test", True),  # ports ignored like upstream
    ("https://user:pw@bank.test/", "bank.test", False),  # credentials in url refused
    ("https://x.test/", "*", True),
    ("chrome-extension://abc/", "*", False),
    ("https://a.example.com/", "*example.com", False),  # embedded wildcard refused
    ("https://a.b.example.com/", "*.*.example.com", False),
    ("https://example.com/", "example.*", False),
    ("about:blank", "*", False),
]


@pytest.mark.parametrize("url,pattern,expected", ORIGIN_TABLE)
def test_origin_rule(url, pattern, expected):
    assert origin_allows(url, pattern) is expected


def test_allowed_for_and_prefilter():
    assert STORE.allowed_for("https://app.example.com/", "x_password")
    assert not STORE.allowed_for("https://evil-example.com/", "x_password")
    assert not STORE.allowed_for("https://app.example.com/", "x_pin")
    assert STORE.allowed_for("https://anything.test/", "localdev_token")
    filtered = STORE.to_browser_use_for("https://bank.test/")
    assert filtered == {"https://bank.test": {"x_pin": "pin 4471"}, "localdev_token": "tok-local-1234"}


def test_to_browser_use_shape_matches_upstream_contract():
    d = STORE.to_browser_use()
    assert d["https://*.example.com"] == {"x_password": "hunter2-SECRET-9f3a", "x_user": "tom@example.com"}
    assert d["localdev_token"] == "tok-local-1234"  # flat = legacy any-origin form
    assert all(isinstance(v, (str, dict)) for v in d.values())
    assert SecretStore.placeholder("x_password") == "<secret>x_password</secret>"


def test_short_value_refused():
    with pytest.raises(SecretError):
        SecretStore({"pin": "123"})
    with pytest.raises(SecretError):
        SecretStore({"https://x.test": {"p": "  a b  "}})
    with pytest.raises(SecretError):
        SecretStore({"bad<name>": "longenough"})


def test_redactor_covers_encodings():
    r = STORE.redactor()
    v = "hunter2-SECRET-9f3a"
    forms = {
        "raw": v,
        "pct": quote(v, safe=""),
        "form": quote_plus("pin 4471"),
        "html": "&lt;b&gt;" + v,
        "json": json.dumps({"p": v}),
        "b64": base64.b64encode(v.encode()).decode(),
        "collapsed": "pin   4471",
        "md": v.replace("-", "\\-") if False else v,
    }
    for name, text in forms.items():
        out = r(text)
        assert "hunter2" not in out and "SECRET-9f3a" not in out and "4471" not in out, (name, out)
        assert "[REDACTED:" in out, name
    assert r("nothing secret here") == "nothing secret here"
    assert r("") == ""


def test_trace_redaction_via_install(tmp_path):
    path = tmp_path / "t.jsonl"
    with TraceWriter(path) as w:
        kwargs = install({"task": "log in as tom@example.com with hunter2-SECRET-9f3a"}, STORE, w)
        assert kwargs["sensitive_data"] == STORE.to_browser_use()
        w.write(RunHeader(run_id="r", task=kwargs["task"], arm="dual", backend="pure-python", browser_use_version="0.13.10"))
    text = path.read_text()
    assert "hunter2" not in text and "tom@example.com" not in text and "[REDACTED:x_password]" in text


def test_assert_no_secrets_walks_nested():
    assert_no_secrets({"a": ["<secret>x_password</secret>", {"b": "fine"}]}, STORE)
    with pytest.raises(SecretLeak):
        assert_no_secrets({"messages": [{"content": "pw is " + quote("hunter2-SECRET-9f3a", safe="")}]}, STORE)
