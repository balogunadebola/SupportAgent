"""
Safe tool executor for SupportAgent.
Executes registered tools with basic error handling and optional argument validation.
"""

import json
import logging
from typing import Any, Dict

from services.tool_registry import tool_registry

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self):
        self.registry = tool_registry

    async def execute(self, name: str, args: Dict[str, Any]):
        fn = self.registry.get(name)
        if not fn:
            return {
                "success": False,
                "error": f"Unknown tool '{name}'",
                "retryable": False,
            }
        try:
            result = fn(**(args or {}))
            # If tool returns JSON string, attempt to parse
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                except Exception:
                    parsed = {"result": result}
                return {"success": True, "result": parsed}
            return {"success": True, "result": result}
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Tool '%s' failed", name)
            return {
                "success": False,
                "error": str(exc),
                "retryable": True,
            }


tool_executor = ToolExecutor()
