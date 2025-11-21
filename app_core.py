"""
Core orchestration wrapper used by the FastAPI backend.
Encapsulates agent wiring, tool execution, context trimming, and fallbacks.
"""

import asyncio
import json
import logging
import os
import re
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from agents import ConversationAgent, OrchestratorAgent, SalesAgent, SupportAgent
from services.tool_executor import tool_executor
from user_functions import user_functions
from utils.session_manager import session_manager


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
        # Initialize agents (deployment handled by llm_service)
        self.orchestrator = OrchestratorAgent()
        self.sales = SalesAgent()
        self.support = SupportAgent()
        self.conversation = ConversationAgent()
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
        Call an agent's async chat method.
        """
        return await agent.chat_async(messages)

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
        support_terms = ("support", "issue", "ticket", "problem", "status", "help", "bug", "broken", "warranty")
        sales_terms = ("buy", "purchase", "price", "order", "quote", "spec", "laptop", "catalog", "deal")
        if any(t in text for t in support_terms):
            return "support"
        if any(t in text for t in sales_terms):
            return "sales"
        return "conversation"

    def build_context(
        self,
        history: List[Dict[str, str]],
        max_tokens: int,
        summary: Optional[str] = None,
        slot_snapshot: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Truncate conversation history to stay under a rough token budget.
        We approximate tokens with characters (4 chars ~= 1 token) for simplicity.
        Injects summary and known slots as system messages when available.
        """
        if not history:
            trimmed: List[Dict[str, str]] = []
        else:
            budget_chars = max_tokens * 4
            total = 0
            trimmed = []
            for msg in reversed(history):
                content = msg.get("content") or ""
                total += len(content)
                trimmed.append(msg)
                if total >= budget_chars:
                    break
            trimmed = list(reversed(trimmed))

        prefix: List[Dict[str, str]] = []
        if slot_snapshot:
            prefix.append({"role": "system", "content": f"Known details: {slot_snapshot}"})
        if slot_snapshot and "budget_status=below_catalog" in slot_snapshot:
            prefix.append(
                {
                    "role": "system",
                    "content": (
                        "User budget is below current catalog pricing. "
                        "Acknowledge this before suggesting the closest matches."
                    ),
                }
            )
        if summary:
            prefix.append({"role": "system", "content": f"Earlier conversation summary: {summary}"})
        return prefix + trimmed

    def _fallback_reply(self, reason: str) -> str:
        self.logger.warning("Fallback reply triggered: %s", reason)
        return (
            "I'm having trouble completing that request right now. "
            "Please try again in a moment or share a bit more detail so I can help."
        )

    def _select_agent(self, target: str):
        if target == "sales":
            return self.sales
        if target == "support":
            return self.support
        return self.conversation

    def _update_slots(self, state, user_message: str):
        text = user_message or ""
        text_lower = text.lower()
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        if email_match:
            state.update_slot("email", email_match.group(0).lower())

        order_match = re.search(r"ORDER-[A-Za-z0-9]+", text.upper())
        if order_match:
            state.update_slot("order_id", order_match.group(0))

        ticket_match = re.search(r"TICKET-[A-Za-z0-9]+", text.upper())
        if ticket_match:
            state.update_slot("ticket_id", ticket_match.group(0))

        if "gaming" in text_lower:
            state.update_slot("category", "gaming")
        elif "business" in text_lower:
            state.update_slot("category", "business")
        elif "budget" in text_lower and "model" not in state.slots:
            state.update_slot("category", "budget")

        budget_match = re.search(r"\$?\s?(\d{3,5})", text)
        if budget_match and "budget" in text_lower:
            budget_value = budget_match.group(1)
            state.update_slot("budget", budget_value)
            try:
                budget_int = int(budget_value)
            except ValueError:
                budget_int = None
            if budget_int and budget_int < 1200:
                state.update_slot("budget_status", "below_catalog")

        quantity_match = re.search(r"\b(\d+)\b", text)
        if quantity_match and "quantity" not in state.slots and ("quantity" in text_lower or "units" in text_lower):
            state.update_slot("quantity", quantity_match.group(1))

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
        # Pull existing history for the session if not provided
        state = session_manager.get(session_id)
        history = deepcopy(conversation_history or state.history)
        history.append({"role": "user", "content": user_message})
        state.history = history
        state.rollup_history()
        self._update_slots(state, user_message)
        history = state.history
        llm_history = self.build_context(
            history,
            self.max_history_tokens,
            summary=state.summary,
            slot_snapshot=state.slot_snapshot(),
        )

        fallback_used = False
        tool_calls: List[Dict[str, Any]] = []
        used_agent = "orchestrator"

        try:
            orch_msg = await self._call_agent(self.orchestrator, llm_history)
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
        else:
            target = None

        if not target:
            target = self._guess_route(user_message)
            fallback_used = True
            history.append({
                "role": "function",
                "name": "route_to_agent",
                "content": json.dumps({"target": target, "auto_routed": True})
            })

        # Rebuild context after routing decision is recorded
        state.history = history
        state.rollup_history()
        history = state.history
        llm_history = self.build_context(
            history,
            self.max_history_tokens,
            summary=state.summary,
            slot_snapshot=state.slot_snapshot(),
        )

        agent = self._select_agent(target)
        used_agent = agent.name

        try:
            agent_msg = await self._call_agent(agent, llm_history)
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
            exec_result = await tool_executor.execute(fname, fargs)
            tool_calls.append({"name": fname, "args": fargs, "result": exec_result})

            # Persist tool output to history for LLM context
            history.append({
                "role": "function",
                "name": fname,
                "content": json.dumps(exec_result),
            })

            if not exec_result.get("success"):
                fallback_used = True
                reply = exec_result.get("error") or self._fallback_reply("tool_error")
            else:
                parsed = exec_result.get("result") or {}
                reply = parsed.get("user_reply") or parsed.get("message") or "Request completed."
            history.append({"role": "assistant", "content": reply})
        else:
            reply = agent_msg.content or self._fallback_reply("empty_agent_message")
            fallback_used = fallback_used or not agent_msg.content
            history.append({"role": "assistant", "content": reply})

        latency_ms = (time.perf_counter() - start_time) * 1000
        state.history = history
        state.rollup_history()
        history = state.history
        result = {
            "reply": reply,
            "updated_history": history,
            "used_agent": used_agent,
            "tool_calls": tool_calls,
            "latency_ms": latency_ms,
            "fallback_used": fallback_used,
        }
        # Persist updated state
        session_manager.upsert_history(
            session_id,
            state.history,
            summary=state.summary,
            slots=state.slots,
            last_agent=used_agent,
        )
        return result
