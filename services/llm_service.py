"""
Thin Azure OpenAI wrapper for SupportAgent.
Loads env values and refreshes them on each call so .env is respected both in CLI and API.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import openai

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        # Attempt to load .env at init time
        load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
        self._refresh_from_env()

    def _refresh_from_env(self):
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        openai.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        if not self.model:
            logger.warning("AZURE_OPENAI_DEPLOYMENT_NAME not set; LLM calls will fail.")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = "auto",
    ):
        # Ensure env is fresh for each call (covers CLI and API lifecycles)
        if not self.model:
            self._refresh_from_env()
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if functions:
            kwargs["functions"] = functions
            if function_call:
                kwargs["function_call"] = function_call
        return await asyncio.to_thread(openai.chat.completions.create, **kwargs)


llm_service = LLMService()
