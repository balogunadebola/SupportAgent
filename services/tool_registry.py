"""
Simple tool registry for SupportAgent.
Maps function names to callables and basic metadata, enabling plug-and-play tools.
"""

import logging
from typing import Any, Callable, Dict

from user_functions import user_functions

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        # preload existing user_functions
        self._tools: Dict[str, Callable[..., Any]] = {fn.__name__: fn for fn in user_functions}
        self._meta: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, fn: Callable[..., Any], metadata: Dict[str, Any] = None):
        self._tools[name] = fn
        if metadata:
            self._meta[name] = metadata
        logger.info("Registered tool: %s", name)

    def get(self, name: str) -> Callable[..., Any] | None:
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Dict[str, Any]:
        return self._meta.get(name, {})

    def names(self):
        return list(self._tools.keys())

    def all(self):
        return self._tools.copy()


tool_registry = ToolRegistry()
