"""Q11: the declared task contract and the typed rejection message (jevdual.contract)."""

from __future__ import annotations

import json

from jevdual.arbiter import ArbiterPolicy
from jevdual.contract import TaskContract, declare, typed_rejection
from jevdual.verify import ClaimCheck, Verdict, VerifyPolicy


def _contract(**kw) -> TaskContract:
    base = {
        "requirements": ("Signed in", "Backpack in cart", "Order finished"),
        "answer_expected": False,
        "authorized_destructive": False,
        "authorized_actions": (),
        "gate": ArbiterPolicy(),
    }
    base.update(kw)
    return TaskContract.from_task(**base)


def test_declaration_lists_every_requirement_in_order():
    text = declare(_contract())
    assert "1. Signed in\n2. Backpack in cart\n3. Order finished" in text


def test_declaration_states_the_refusal_budget_the_agent_enforces():
    assert "After 2 refusals" in declare(_contract())
    assert "After 1 refusals" in declare(_contract(max_done_rejections=1))


def test_answer_line_only_when_the_task_expects_an_answer():
    assert "asks for an answer" not in declare(_contract())
    assert "quote the value as the page shows it" in declare(_contract(answer_expected=True))


def test_unauthorized_task_says_stop_and_report():
    text = declare(_contract())
    assert "No irreversible action is authorized" in text
    assert "Authorized for this task" not in text


def test_scoped_authorization_names_the_scope_and_keeps_the_rest_gated():
    text = declare(_contract(authorized_destructive=True, authorized_actions=("finish", "checkout")))
    assert "'finish', 'checkout'" in text and "Any other irreversible target still pauses" in text


def test_task_wide_authorization():
    assert "authorizes the irreversible actions it names" in declare(_contract(authorized_destructive=True))


def test_declared_gate_keywords_come_from_the_gate_policy():
    gate = ArbiterPolicy.from_toml()
    text = declare(_contract(gate=gate))
    for kw in ("delete", "place order", "move to trash"):
        assert kw in gate.destructive_keywords and kw in text
    assert "删除" not in text  # ASCII only in the English system message
    assert "`evaluate`) always counts as irreversible" in text  # the gate refuses page script outright


def _verdict(**kw) -> Verdict:
    base = {"band": "reject", "complete": 0.5, "unmet": {}, "claims": [], "reason": "", "unmet_effective": {}}
    base.update(kw)
    return Verdict(**base)


def test_typed_rejection_names_unmet_requirements_worst_first_without_probabilities():
    v = _verdict(
        unmet={"Signed in": 0.1, "Backpack in cart": 0.9, "Order finished": 0.5},
        unmet_effective={"Signed in": 0.1, "Backpack in cart": 0.9, "Order finished": 0.5},
        reason="Backpack in cart unmet with p=0.90",
    )
    msg = typed_rejection(v, VerifyPolicy(), refusals_left=1)
    assert msg.index("judged not met: Backpack in cart") < msg.index("not clearly shown yet: Order finished")
    assert "Signed in" not in msg
    assert "p=" not in msg and "0.9" not in msg
    assert "1 more refusal(s)" in msg


def test_typed_rejection_uses_the_ledger_adjusted_values():
    v = _verdict(unmet={"Signed in": 0.9}, unmet_effective={"Signed in": 0.1}, complete=0.2)
    msg = typed_rejection(v, VerifyPolicy(), refusals_left=0)
    assert "Signed in" not in msg
    assert "does not yet clearly show the task as complete" in msg
    assert "next `done` ends the run marked unverified" in msg


def test_typed_rejection_reports_unsupported_claims_and_missing_answer():
    v = _verdict(
        band="verify",
        complete=0.9,
        claims=[ClaimCheck("The total is $99", "none", 0, 0)],
        unsupported_claims=("The total is $99",),
        reason="answer carries no fact found on the page (1 unsupported, rest narrative); complete p=0.90",
    )
    msg = typed_rejection(v, VerifyPolicy(), refusals_left=1)
    assert "'The total is $99'" in msg
    assert "asks for an answer quoting what the page shows" in msg


def test_runner_declaration_for_the_two_declared_arms(monkeypatch):
    from evals.runner import declaration_for, default_policy_factory
    from evals.tasks.schema import Task

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-real")
    t = Task(
        id="q11",
        task="Report the total on the page",
        start_url="https://x.example/",
        tags=("live", "read"),
        requirements=("Total reported",),
        predicate={"kind": "answer_contains", "value": "1"},
        answer_expected=True,
    )
    factory = default_policy_factory()
    declared_guard = factory(t, None, "guarded_declared")
    text, feedback = declaration_for(t, "guarded_declared", declared_guard)
    assert "1. Total reported" in text and feedback is None
    legible_guard = factory(t, None, "guarded_legible")
    text2, feedback2 = declaration_for(t, "guarded_legible", legible_guard)
    assert text2 == text and callable(feedback2)
    # the verifier never sees the declaration: same requirements, same task sentence
    assert legible_guard.verifier.requirements == ("Total reported",)


def test_q11_arms_share_the_guarded_guard(monkeypatch):
    from jevdual.s1 import GuardOnly

    from evals.runner import ARMS, GUARDED_ARMS, S2_ARMS, default_policy_factory
    from evals.tasks.schema import Task

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-real")
    t = Task(
        id="g",
        task="Open the page",
        start_url="https://x.example/",
        tags=("live",),
        requirements=("Page opened",),
        predicate={"kind": "url_contains", "value": "x"},
    )
    for arm in GUARDED_ARMS:
        assert arm in ARMS and arm in S2_ARMS
        assert isinstance(default_policy_factory()(t, None, arm), GuardOnly)


def test_paired_counts_verified_and_q11_burden_fields(tmp_path):
    from evals.paired import _rows, compare

    rows = [
        {
            "task_id": "t",
            "arm": "guarded",
            "passed": True,
            "success": True,
            "llm_requests": 9,
            "done_rejections": 2,
        },
        {"task_id": "t", "arm": "guarded_legible", "passed": True, "success": True, "llm_requests": 6},
        {"task_id": "u", "arm": "guarded", "passed": True, "success": False, "llm_requests": 4},
        {"task_id": "u", "arm": "guarded_legible", "passed": True, "success": True, "llm_requests": 4},
    ]
    (tmp_path / "results.json").write_text(json.dumps(rows))
    res = compare(_rows(tmp_path, "guarded"), _rows(tmp_path, "guarded_legible"))
    assert res["fields"]["verified"]["b_better"] == 1
    assert res["fields"]["llm_requests"]["mean_diff"] == -1.5
    assert res["fields"]["done_rejections"]["b_better"] == 1


def test_rejections_reads_reasons_carried_on_result_rows(tmp_path):
    from evals.rejections import load

    rows = [
        {
            "task_id": "t",
            "arm": "guarded_legible",
            "passed": True,
            "final_url": "https://x/",
            "done_rejection_reasons": [
                "(reject) Backpack in cart unmet with p=0.90",
                "(verify) uncertain: complete p=0.70, max unmet p=0.40",
            ],
        }
    ]
    (tmp_path / "results.json").write_text(json.dumps(rows))
    (tmp_path / "traces").mkdir()
    rej = load(tmp_path, "guarded_legible")
    assert [(r.band, r.category) for r in rej] == [("reject", "process_unmet"), ("verify", "uncertain")]
    assert rej[0].requirement == "Backpack in cart" and rej[0].passed is True
