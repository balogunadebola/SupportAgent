"""
Core orchestration wrapper used by the FastAPI backend.
Encapsulates agent wiring, tool execution, context trimming, and fallbacks.
"""

import asyncio
import json
import logging
import os
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from agents import OrchestratorAgent, SalesAgent, SupportAgent
from user_functions import user_functions


class SupportAssistantCore:
    """
    Encapsulates orchestrator + agents + tools + LLM client.
    The OpenAI client remains configured globally (via the agents module).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.logger = logging.getLogger("support_core")
        self.max_history_tokens = int(self.config.get("max_history_tokens", 4000))
        self._configure_openai()
        deployment = self.config.get("deployment_name") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")

        # Initialize agents and tool map
        self.orchestrator = OrchestratorAgent(deployment)
        self.sales = SalesAgent(deployment)
        self.support = SupportAgent(deployment)
        self.tools = {fn.__name__: fn for fn in user_functions}

    def _configure_openai(self) -> None:
        """
        Configure the global OpenAI client for Azure. This keeps parity with the CLI flow.
        """
        load_dotenv(dotenv_path=Path(__file__).parent / ".env")
        import openai  # imported lazily to keep dependency surface small

        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
        openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        if not openai.api_base:
            self.logger.warning("AZURE_OPENAI_ENDPOINT is not set; OpenAI calls will fail.")

    async def _call_agent(self, agent: Any, messages: List[Dict[str, str]]) -> Any:
        """
        Call an agent's chat method in a worker thread to keep FastAPI event loop non-blocking.
        """
        return await asyncio.to_thread(agent.chat, messages)

    @staticmethod
    def _safe_json_loads(payload: Optional[str]) -> Dict[str, Any]:
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except Exception:
            return {}

    @staticmethod
    def _guess_route(user_message: str) -> str:
        """
        Heuristic fallback routing when orchestrator fails to call a tool.
        """
        text = (user_message or "").lower()
        support_terms = ("support", "issue", "ticket", "problem", "status", "help", "bug")
        if any(t in text for t in support_terms):
            return "support"
        return "sales"

    def build_context(self, history: List[Dict[str, str]], max_tokens: int) -> List[Dict[str, str]]:
        """
        Truncate conversation history to stay under a rough token budget.
        We approximate tokens with characters (4 chars ~= 1 token) for simplicity.
        """
        if not history:
            return []
        budget_chars = max_tokens * 4
        total = 0
        trimmed: List[Dict[str, str]] = []
        for msg in reversed(history):
            content = msg.get("content") or ""
            total += len(content)
            trimmed.append(msg)
            if total >= budget_chars:
                break
        return list(reversed(trimmed))

    def _fallback_reply(self, reason: str) -> str:
        self.logger.warning("Fallback reply triggered: %s", reason)
        return (
            "I'm having trouble completing that request right now. "
            "Please try again in a moment or share a bit more detail so I can help."
        )

    async def handle_user_message(
        self,
        session_id: str,
        user_message: str,
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Routes through orchestrator and sub-agents with resilient tool handling.
        Returns a structured dict with reply, updated history, tool metadata, and latency.
        """
        start_time = time.perf_counter()
        history = deepcopy(conversation_history or [])
        history.append({"role": "user", "content": user_message})
        history = self.build_context(history, self.max_history_tokens)

        fallback_used = False
        tool_calls: List[Dict[str, Any]] = []
        used_agent = "orchestrator"

        try:
            orch_msg = await self._call_agent(self.orchestrator, history)
        except Exception as exc:  # openai errors and routing failures
            self.logger.exception("Orchestrator failed for session %s", session_id)
            return {
                "reply": self._fallback_reply("orchestrator_error"),
                "updated_history": history,
                "used_agent": used_agent,
                "tool_calls": tool_calls,
                "latency_ms": (time.perf_counter() - start_time) * 1000,
                "fallback_used": True,
            }

        target = None
        if getattr(orch_msg, "function_call", None):
            args = self._safe_json_loads(orch_msg.function_call.arguments)
            target = args.get("target")
            content = json.dumps(args) if args else "{}"
            history.append({"role": "function", "name": "route_to_agent", "content": content})

        if not target:
            # Orchestrator failed; route heuristically without surfacing its message to the user.
            target = self._guess_route(user_message)
            fallback_used = True

        agent = self.sales if target == "sales" else self.support
        used_agent = agent.name

        try:
            agent_msg = await self._call_agent(agent, history)
        except Exception:
            self.logger.exception("Agent call failed for %s", used_agent)
            fallback_used = True
            reply = self._fallback_reply("agent_error")
            history.append({"role": "assistant", "content": reply})
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "reply": reply,
                "updated_history": history,
                "used_agent": used_agent,
                "tool_calls": tool_calls,
                "latency_ms": latency_ms,
                "fallback_used": fallback_used,
            }

        if getattr(agent_msg, "function_call", None):
            fname = agent_msg.function_call.name
            fargs = self._safe_json_loads(agent_msg.function_call.arguments)
            tool_fn = self.tools.get(fname)

            if not tool_fn:
                fallback_used = True
                reply = self._fallback_reply("unknown_tool")
                history.append({"role": "assistant", "content": reply})
            else:
                try:
                    result = await asyncio.to_thread(tool_fn, **fargs)
                except Exception:
                    self.logger.exception("Tool %s failed for session %s", fname, session_id)
                    fallback_used = True
                    reply = self._fallback_reply("tool_error")
                else:
                    tool_calls.append({"name": fname, "args": fargs, "result": result})
                    history.append({"role": "function", "name": fname, "content": result})
                    try:
                        parsed = json.loads(result)
                        reply = parsed.get("user_reply") or parsed.get("message") or "Request completed."
                    except Exception:
                        reply = "Your request was processed."
                history.append({"role": "assistant", "content": reply})
        else:
            reply = agent_msg.content or self._fallback_reply("empty_agent_message")
            fallback_used = fallback_used or not agent_msg.content
            history.append({"role": "assistant", "content": reply})

        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "reply": reply,
            "updated_history": history,
            "used_agent": used_agent,
            "tool_calls": tool_calls,
            "latency_ms": latency_ms,
            "fallback_used": fallback_used,
        }
