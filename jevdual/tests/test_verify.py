import asyncio
import json
from pathlib import Path

import pytest
from jevdual._pure.evidence_match import evidence_match
from jevdual.menu import Menu
from jevdual.policy import PolicyError
from jevdual.verify import ArbiterHook, Verifier, VerifyPolicy, band_for, check_claims, split_claims
from typesafe_sdk import SystemOneResponse

FIXTURES = Path(__file__).parent / "fixtures" / "jev_responses"


def load(name: str) -> SystemOneResponse:
    return SystemOneResponse.model_validate(json.loads((FIXTURES / f"{name}.json").read_text()))


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def system_one(self, state, questions, *, model=None, **kwargs):
        self.calls.append({"state": state, "questions": questions, "model": model, "kwargs": kwargs})
        return self.responses.pop(0)


PAGE = (
    "Kestrel Bay Lighthouse\n"
    "Order confirmed. Thank you, Ada.\n"
    "The lighthouse was built in 1874 and stands 31 metres tall.\n"
    "Its lamp was electrified in 1932; the keeper's cottage became a museum in 1998.\n"
)


def menu(text=PAGE):
    return Menu(url="http://s/article.html", title="Kestrel Bay", page_text=text, candidates=(), by_operation={})


REQS = ("Order was placed", "Confirmation names the customer")


def run(v, *args, **kw):
    return asyncio.run(v.verify(*args, **kw))


# ---- evidence matcher (pure reference for R4) ---------------------------------------------


def test_evidence_match_grades_and_spans():
    res = evidence_match(
        ["built in 1874", "BUILT   in 1874", "keepers cottage became a museum", "built in 1875", "  "],
        PAGE,
    )
    assert [r["grade"] for r in res] == ["exact", "normalized", "normalized", "none", "none"]
    assert PAGE[res[0]["start"] : res[0]["end"]] == "built in 1874"
    assert PAGE[res[1]["start"] : res[1]["end"]] == "built in 1874"
    assert PAGE[res[2]["start"] : res[2]["end"]] == "keeper's cottage became a museum"
    assert res[3]["start"] == -1 and res[3]["end"] == -1


def test_evidence_match_curly_quotes_and_nbsp():
    page = "The keeper’s cottage “became” a museum"
    res = evidence_match(["keeper's cottage \"became\" a museum"], page)
    assert res[0]["grade"] == "normalized" and page[res[0]["start"] : res[0]["end"]].startswith("keeper")


def test_split_claims_and_check_claims():
    assert split_claims("Built in 1874. It stands 31 metres tall!\nElectrified in 1932") == [
        "Built in 1874.",
        "It stands 31 metres tall!",
        "Electrified in 1932",
    ]
    checks = check_claims("built in 1874. Electrified in 1955.", PAGE)
    assert [c.supported for c in checks] == [True, False]
    assert check_claims(None, PAGE) == [] and check_claims("", PAGE) == []


# ---- bands ---------------------------------------------------------------------------------


def test_band_thresholds():
    p = VerifyPolicy()
    assert band_for(0.9, {"a": 0.1}, p)[0] == "accept"
    assert band_for(0.9, {"a": 0.25}, p)[0] == "verify"
    assert band_for(0.84, {"a": 0.1}, p)[0] == "verify"
    assert band_for(0.9, {"a": 0.7}, p)[0] == "reject"
    assert band_for(0.3, {"a": 0.1}, p)[0] == "reject"
    assert band_for(0.9, {}, p)[0] == "accept"


# ---- verifier over recorded responses -----------------------------------------------------


def test_request_shape():
    client = FakeClient(load("verify_accept"))
    v = Verifier(client)
    run(v, "Place the order", REQS, menu(), None)
    call = client.calls[0]
    assert call["model"] == "jev-1.13.0"
    assert list(call["questions"]) == ["complete", "unmet_0", "unmet_1"]
    assert all(q.type == "noul" for q in call["questions"].values())
    assert call["state"]["requirements"] == list(REQS) and call["state"]["page"]["text"] == PAGE
    assert "answer" not in call["state"]
    assert "requirements[1]" in call["questions"]["unmet_1"].instructions


def test_accept_path():
    verdict = run(Verifier(FakeClient(load("verify_accept"))), "Place the order", REQS, menu(), None)
    assert verdict.band == "accept" and verdict.complete == 0.94
    assert verdict.unmet == {REQS[0]: 0.05, REQS[1]: 0.08}
    assert verdict.claims == [] and verdict.supported_answer is None
    t = verdict.to_trace()
    assert t["band"] == "accept" and t["unsupported"] == 0 and set(t) == {"band", "complete", "unmet", "claims", "unsupported", "reason"}


def test_reject_on_one_unmet():
    verdict = run(Verifier(FakeClient(load("verify_reject_unmet"))), "Place the order", REQS, menu(), None)
    assert verdict.band == "reject" and REQS[1] in verdict.reason


def test_verify_band_when_uncertain():
    verdict = run(Verifier(FakeClient(load("verify_uncertain"))), "Place the order", REQS, menu(), None)
    assert verdict.band == "verify" and "uncertain" in verdict.reason


def test_unsupported_claims_are_dropped_but_accept_survives_if_some_supported():
    answer = "The lighthouse was built in 1874. It was electrified in 1955."
    verdict = run(Verifier(FakeClient(load("verify_accept"))), "Report facts", REQS, menu(), answer)
    assert verdict.band == "accept"
    assert verdict.unsupported_claims == ("It was electrified in 1955.",)
    assert verdict.supported_answer == "The lighthouse was built in 1874."
    assert "1 unsupported claim(s) dropped" in verdict.reason
    assert verdict.to_trace()["claims"] == ["normalized", "none"]  # trailing period folds away


def test_confidently_wrong_done_cannot_accept_without_evidence():
    # Jev says complete=0.90, unmet=0.10, but the answer quotes a value the page does not contain.
    verdict = run(Verifier(FakeClient(load("verify_confident_wrong"))), "Report the height", ("Height reported",), menu(), "It stands 45 metres tall.")
    assert verdict.band == "verify"
    assert verdict.supported_answer is None and verdict.unsupported_claims == ("It stands 45 metres tall.",)
    assert "no claim quoted from the page" in verdict.reason


def test_missing_answer_key_is_policy_error():
    bad = SystemOneResponse.model_validate({"model": "jev-1.13.0", "usage": {"input_tokens": 1, "output_tokens": 0}, "answers": {"complete": {"type": "noul", "noul": 0.9}}})
    with pytest.raises(PolicyError):
        run(Verifier(FakeClient(bad)), "t", ("r",), menu(), None)


def test_arbiter_hook():
    class Agent:
        task = "Place the order"

    hook = ArbiterHook(Verifier(FakeClient(load("verify_reject_unmet"))), REQS)
    band, reason = asyncio.run(hook.judge_done(Agent(), menu()))
    assert band == "reject" and hook.last is not None and hook.last.band == "reject"
