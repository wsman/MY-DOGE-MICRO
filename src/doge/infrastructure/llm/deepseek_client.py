"""DeepSeek LLM adapter — implements :class:`~doge.core.ports.llm.ILLMClient`.

This adapter wraps the OpenAI SDK (used by DeepSeek's compatible API) and is
intentionally the **only** module under ``doge.infrastructure`` that imports
``openai``. It degrades to ``None`` when the API key is missing or the request
fails, so callers never need to catch SDK-specific exceptions.
"""

import logging
from typing import Optional

from doge.config import get_settings
from doge.core.ports.llm import ILLMClient
from doge.core.ports.secrets import ISecretProvider
from doge.infrastructure.secrets import EnvSecretProvider

logger = logging.getLogger(__name__)


class DeepSeekClient(ILLMClient):
    """DeepSeek-compatible LLM client adapter.

    Reads endpoint, model, and API key from :class:`~doge.config.settings.Settings`.
    Lazy-imports ``openai`` inside :meth:`chat` so the rest of the package can be
    imported without the optional ``openai`` extra installed.
    """

    def __init__(self, *, secret_provider: ISecretProvider | None = None) -> None:
        self._secret_provider = secret_provider or EnvSecretProvider()

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Send a chat completion request and return the generated text.

        Returns ``None`` when the API key is missing, ``openai`` is unavailable,
        or any request failure occurs.
        """
        settings = get_settings()
        api_key = self._secret_provider.get_secret("deepseek.api_key") or settings.deepseek.api_key
        if not api_key:
            logger.warning("DeepSeek API key not configured")
            return None

        try:
            import openai
        except ImportError:  # pragma: no cover - optional extra
            logger.warning("openai package not installed")
            return None

        try:
            client = openai.OpenAI(api_key=api_key, base_url=settings.deepseek.base_url)
            response = client.chat.completions.create(
                model=settings.deepseek.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as exc:  # noqa: BLE001 - degraded behavior
            logger.warning("DeepSeek chat request failed: %s", exc)
            return None
