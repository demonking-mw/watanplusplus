"""
AI provider configuration and credential management.

Credentials are loaded from environment variables. Set them before use:
  - OpenAI:    OPENAI_API_KEY
  - Anthropic: ANTHROPIC_API_KEY
  - Google:    GOOGLE_API_KEY

To add a new provider:
  1. Add an entry to AIProvider enum.
  2. Add its env-var key to _ENV_KEYS.
  3. Add default model to _DEFAULT_MODELS.
  4. Implement the sync/async call in query.py (_PROVIDER_DISPATCH / _PROVIDER_DISPATCH_ASYNC).
"""

from enum import Enum
from os import environ
from pathlib import Path
from typing import Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    # Look for .env in project root (two directories up from src/ai/config.py)
    _dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if _dotenv_path.exists():
        load_dotenv(_dotenv_path, override=True)
    else:
        print(f"[config] WARNING: .env not found at {_dotenv_path}")
except ImportError:
    print("[config] WARNING: python-dotenv not installed; .env will not be loaded")
    pass


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


# Map provider → environment variable that stores the API key
_ENV_KEYS: dict[AIProvider, str] = {
    AIProvider.OPENAI: "OPENAI_API_KEY",
    AIProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    AIProvider.GOOGLE: "GOOGLE_API_KEY",
}

# Default model per provider (override at call-time if needed)
DEFAULT_MODELS: dict[AIProvider, str] = {
    AIProvider.OPENAI: "gpt-5-mini",
    AIProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    AIProvider.GOOGLE: "gemini-2.5-flash",
}

# Sensible global default provider
DEFAULT_PROVIDER: AIProvider = AIProvider.OPENAI


def get_api_key(provider: AIProvider) -> str:
    """Retrieve the API key for *provider* from the environment."""
    env_var = _ENV_KEYS[provider]
    key = environ.get(env_var)
    if not key:
        raise EnvironmentError(
            f"Missing API key: set the {env_var} environment variable."
        )
    return key


def get_default_model(provider: AIProvider) -> str:
    """Return the default model string for *provider*."""
    return DEFAULT_MODELS[provider]


def get_available_providers() -> list[AIProvider]:
    """Return providers whose API key is currently set in the environment."""
    return [p for p in AIProvider if environ.get(_ENV_KEYS[p])]
