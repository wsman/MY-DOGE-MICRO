"""Environment-backed secret provider."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from doge.core.ports.secrets import ISecretProvider


_DEFAULT_ENV_NAMES = {
    "kimi.api_key": "MOONSHOT_API_KEY",
    "deepseek.api_key": "DEEPSEEK_API_KEY",
    "auth.static_bearer_token": "DOGE_AUTH_STATIC_BEARER_TOKEN",
}


@dataclass(frozen=True)
class EnvSecretProvider(ISecretProvider):
    """Resolve canonical secret names from environment variables."""

    env_names: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_ENV_NAMES))

    def get_secret(self, name: str) -> str | None:
        env_name = self.env_names.get(name, name)
        value = os.environ.get(env_name)
        if value is None or value == "":
            return None
        return value
