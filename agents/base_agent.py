"""
Minimal base agent for SupportAgent.
Wraps prompt loading and Azure OpenAI chat calls.
"""

import asyncio
import logging
from typing import Any, Dict, List

from services.llm_service import llm_service
from utils.prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, *, name: str, prompt_key: str, fallback_prompt: str, functions: List[Dict[str, Any]]):
        self.name = name
        self.prompt_key = prompt_key
        self.fallback_prompt = fallback_prompt
        self.functions = functions
        self.logger = logging.getLogger(name)

    def _system_prompt(self) -> str:
        prompt = prompt_manager.get(self.prompt_key)
        return prompt or self.fallback_prompt

    async def chat_async(self, messages: List[Dict[str, Any]], function_call: str = "auto"):
        """
        Async chat wrapper. Prepends system prompt and returns the OpenAI message object.
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self._system_prompt()}] + messages

        functions = self.functions or None
        call_mode = function_call if functions else None
        resp = await llm_service.chat(messages=messages, functions=functions, function_call=call_mode)
        self.logger.info("Response content: %s", resp.choices[0].message.content)
        return resp.choices[0].message

    def chat(self, messages: List[Dict[str, Any]], function_call: str = "auto"):
        """
        Sync wrapper for CLI use.
        """
        return asyncio.run(self.chat_async(messages, function_call=function_call))
