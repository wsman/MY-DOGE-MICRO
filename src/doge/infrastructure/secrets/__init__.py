"""Secret provider adapters."""

from doge.infrastructure.secrets.env_provider import EnvSecretProvider
from doge.infrastructure.secrets.process_provider import ProcessSecretProvider

__all__ = ["EnvSecretProvider", "ProcessSecretProvider"]
