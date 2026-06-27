"""Gateway factory helpers for secrets."""
from __future__ import annotations
from doge.config import get_settings
from doge.infrastructure.secrets import EnvSecretProvider, ProcessSecretProvider


__all__ = [
    "secrets",
    "llm",
    "repositories",
    "market",
    "documents",
    "use_cases",
    "tools",
]


def build_secret_provider():
    settings = get_settings()
    provider = settings.secrets.provider
    if provider == "env":
        return EnvSecretProvider()
    if provider == "process":
        return ProcessSecretProvider(
            command=settings.secrets.process_command,
            timeout_seconds=settings.secrets.process_timeout_seconds,
            allowed_names=frozenset(settings.secrets.allowed_names),
        )
    raise ValueError(f"Unsupported DOGE_SECRET_PROVIDER: {provider}")
