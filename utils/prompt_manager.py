"""
Prompt manager for SupportAgent.
Loads prompts from a directory if present; otherwise falls back to inline defaults.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PromptManager:
    def __init__(self, prompt_dir: str = "prompts"):
        self.prompt_dir = Path(prompt_dir)
        self.prompts: Dict[str, str] = {}
        self._load()

    def _load(self):
        if not self.prompt_dir.exists():
            logger.info("Prompt directory %s not found; using inline prompts", self.prompt_dir)
            return
        for file in self.prompt_dir.rglob("*.txt"):
            try:
                content = file.read_text(encoding="utf-8")
                key = str(file.relative_to(self.prompt_dir)).replace("\\", "/").replace(".txt", "")
                self.prompts[key] = content
                logger.info("Loaded prompt: %s", key)
            except Exception:
                logger.warning("Failed to load prompt file %s", file)

    def get(self, key: str) -> Optional[str]:
        return self.prompts.get(key)

    def list(self):
        return list(self.prompts.keys())


prompt_manager = PromptManager()
