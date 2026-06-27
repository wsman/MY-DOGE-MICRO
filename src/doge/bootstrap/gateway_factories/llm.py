"""Gateway factory helpers for LLM adapters."""
from __future__ import annotations
from doge.config import get_settings
from doge.infrastructure.llm.deepseek_client import DeepSeekClient
from doge.infrastructure.llm.kimi_client import KimiAgentModel
from doge.infrastructure.llm.kimi_text_client import KimiTextClient
from doge.bootstrap.gateway_factories.secrets import build_secret_provider


def build_kimi_agent_model(secret_provider=None):
    return KimiAgentModel(secret_provider=secret_provider or build_secret_provider())


def build_default_text_llm_client():
    settings = get_settings()
    secret_provider = build_secret_provider()
    if settings.llm.text_provider.lower() == "deepseek":
        return DeepSeekClient(secret_provider=secret_provider)
    return KimiTextClient(KimiAgentModel(secret_provider=secret_provider))
