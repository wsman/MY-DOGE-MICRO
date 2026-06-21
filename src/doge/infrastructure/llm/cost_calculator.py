"""Token cost helpers for Kimi-compatible agent calls.

The defaults intentionally use zero-priced demo values. Operators can provide
real per-million-token prices from current provider terms without changing
source code; platform pricing is commercial data and can change independently
from this repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ModelPricing:
    prompt_per_million_usd: float = 0.0
    completion_per_million_usd: float = 0.0
    cached_prompt_per_million_usd: float = 0.0


DEFAULT_PRICING: dict[str, ModelPricing] = {
    "kimi-k2.6": ModelPricing(),
    "kimi-k2.7-code": ModelPricing(),
    "kimi-k2.7-code-highspeed": ModelPricing(),
    "scripted": ModelPricing(),
}


class CostCalculator:
    """Calculate approximate model call cost from usage counters."""

    def __init__(self, pricing: Mapping[str, ModelPricing] | None = None) -> None:
        self._pricing = dict(pricing or DEFAULT_PRICING)

    def calculate_cost(
        self,
        *,
        model: str | None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cached_tokens: int = 0,
    ) -> float:
        price = self._pricing.get(model or "", ModelPricing())
        billable_prompt = max(0, int(prompt_tokens) - int(cached_tokens))
        cached_prompt = max(0, int(cached_tokens))
        return round(
            (billable_prompt * price.prompt_per_million_usd)
            + (cached_prompt * price.cached_prompt_per_million_usd)
            + (int(completion_tokens) * price.completion_per_million_usd),
            10,
        ) / 1_000_000


def calculate_cost(
    model: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cached_tokens: int = 0,
) -> float:
    """Convenience wrapper using the default pricing table."""

    return CostCalculator().calculate_cost(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_tokens=cached_tokens,
    )
