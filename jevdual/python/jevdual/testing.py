"""Test doubles used by the spike and the eval rig."""

from __future__ import annotations

from typing import Any

from browser_use.llm.views import ChatInvokeCompletion


class RefusingLLM:
    """A BaseChatModel that raises if System 2 is ever invoked.

    Used to prove an S1-only run never touches the LLM. ``_verified_api_keys``
    short-circuits browser-use's key verification.
    """

    model = "refusing-llm"
    _verified_api_keys = True

    @property
    def provider(self) -> str:
        return "jevdual"

    @property
    def name(self) -> str:
        return self.model

    @property
    def model_name(self) -> str:
        return self.model

    async def ainvoke(self, messages: Any, output_format: Any = None, **kwargs: Any) -> ChatInvokeCompletion:
        raise RuntimeError("System 2 was invoked during an S1-only run")
