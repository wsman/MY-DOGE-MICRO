"""Abstract LLM client interface (Port in Ports & Adapters).

Implementations live in :mod:`doge.infrastructure.llm`.
"""

from abc import ABC, abstractmethod
from typing import Optional


class ILLMClient(ABC):
    """Abstract interface for text-generation LLM clients.

    This port decouples the macro/industry report use cases from the concrete
    DeepSeek / OpenAI SDK. The interface is intentionally narrow: a single
    chat-style completion call with system + user prompts.
    """

    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Send a chat completion request and return the generated text.

        Args:
            system_prompt: System-level instructions for the model.
            user_prompt: The user-level prompt / task description.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            The generated text as a string, or ``None`` when the request fails
            (network error, missing API key, rate limit, empty response). Callers
            MUST handle ``None`` as a degraded signal rather than raise.
        """
        ...
