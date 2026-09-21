"""Scripted System 2 for agent-loop tests.

Adapted from browser-use ``tests/ci/conftest.py::create_mock_llm`` at the pinned submodule commit
d8110c5 (MIT licence, browser-use contributors). Differences: the action model comes from the agent
under test when one is given, so registered extra tools validate; a scripted item may also be a
judge verdict, which the upstream judge parses with ``JudgementResult`` after the run.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

from browser_use.agent.views import AgentOutput
from browser_use.llm import BaseChatModel
from browser_use.llm.views import ChatInvokeCompletion
from browser_use.tools.service import Tools

DONE = {
    "thinking": "null",
    "evaluation_previous_goal": "Successfully completed the task",
    "memory": "Task completed",
    "next_goal": "Task completed",
    "action": [{"done": {"text": "Task completed successfully", "success": True}}],
}


def step(*actions: dict[str, Any], memory: str = "step") -> str:
    """One scripted System 2 step: ``step({"navigate": {"url": ...}})``."""
    return json.dumps(
        {"thinking": "null", "evaluation_previous_goal": "ok", "memory": memory, "next_goal": memory, "action": list(actions)}
    )


def done(text: str = "Task completed successfully", success: bool = True) -> str:
    return step({"done": {"text": text, "success": success}}, memory="done")


def judgement(verdict: bool, failure_reason: str = "", impossible: bool = False, captcha: bool = False) -> str:
    return json.dumps(
        {
            "reasoning": "scripted",
            "verdict": verdict,
            "failure_reason": failure_reason,
            "impossible_task": impossible,
            "reached_captcha": captcha,
        }
    )


def create_mock_llm(actions: list[str] | None = None, *, tools: Tools | None = None) -> BaseChatModel:
    """A mock LLM that returns ``actions`` (JSON strings) in order, then ``done`` forever.

    Whatever ``output_format`` the caller passes is used to parse the next scripted item, so the
    same script can carry agent steps followed by a judge verdict.
    """
    tools = tools or Tools()
    action_model = tools.registry.create_action_model()
    output_with_actions = AgentOutput.type_with_custom_actions(action_model)

    llm = AsyncMock(spec=BaseChatModel)
    llm.model = "mock-llm"
    llm._verified_api_keys = True
    llm.provider = "mock"
    llm.name = "mock-llm"
    llm.model_name = "mock-llm"
    llm.calls: list[dict[str, Any]] = []

    queue = list(actions or [])

    def next_item() -> str:
        return queue.pop(0) if queue else json.dumps(DONE)

    async def mock_ainvoke(*args: Any, **kwargs: Any) -> ChatInvokeCompletion:
        output_format = args[1] if len(args) >= 2 else kwargs.get("output_format")
        raw = next_item()
        llm.calls.append({"output_format": getattr(output_format, "__name__", None), "raw": raw})
        if output_format is None:
            return ChatInvokeCompletion(completion=raw, usage=None)
        model = output_with_actions if output_format is output_with_actions else output_format
        return ChatInvokeCompletion(completion=model.model_validate_json(raw), usage=None)

    llm.ainvoke.side_effect = mock_ainvoke
    return llm
