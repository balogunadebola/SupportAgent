"""
Centralized configuration for SupportAgent.
Uses environment variables with sensible local defaults.
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # API/Server
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    reload: bool = os.getenv("RELOAD", "false").lower() == "true"

    # Azure OpenAI
    azure_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    azure_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    # Rate limiting
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "5"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW", "10"))

    # Prompt directory (reserved for future prompt file loading)
    prompt_dir: str = os.getenv("PROMPT_DIR", "prompts")


settings = Settings()
