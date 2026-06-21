"""Financial research evaluation helpers."""

from __future__ import annotations

from typing import Any

from doge.application.services.citation_service import CitationService
from doge.application.services.numerical_consistency_service import NumericalConsistencyService
from doge.core.domain.agent_models import AgentEvent, EventType


class FinancialEvalService:
    """Compute finance-specific quality metrics from a completed run."""

    def __init__(
        self,
        *,
        numerical_service: NumericalConsistencyService | None = None,
        citation_service: CitationService | None = None,
    ) -> None:
        self._numerical = numerical_service or NumericalConsistencyService()
        self._citation = citation_service or CitationService()

    def score_artifact(
        self,
        artifact_text: str,
        events: list[AgentEvent],
        *,
        evidence_records: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        model_usage = _latest_usage(events)
        return {
            "numerical_consistency": self._numerical.score_artifact(artifact_text, events),
            "citation_precision": self._citation.citation_precision_score(
                artifact_text,
                evidence_records or _evidence_records(events),
            ),
            "latency_ms": model_usage.get("latency_ms"),
            "cost_usd": model_usage.get("cost_usd"),
            "cached_token_ratio": _cached_token_ratio(model_usage),
        }


def _latest_usage(events: list[AgentEvent]) -> dict[str, Any]:
    for event in reversed(events):
        if event.event_type == EventType.MODEL_RESPONSE:
            usage = event.payload.get("usage") or {}
            if isinstance(usage, dict):
                return usage
    return {}


def _cached_token_ratio(usage: dict[str, Any]) -> float | None:
    prompt_tokens = usage.get("prompt_tokens")
    cached_tokens = usage.get("cached_tokens")
    if not prompt_tokens:
        return None
    return float(cached_tokens or 0) / float(prompt_tokens)


def _evidence_records(events: list[AgentEvent]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for event in events:
        if event.event_type != EventType.TOOL_RESULT:
            continue
        result = event.payload.get("result", {})
        data = result.get("data", {}) if isinstance(result, dict) else {}
        evidence = data.get("evidence") or data.get("results") or []
        if isinstance(evidence, list):
            records.extend(item for item in evidence if isinstance(item, dict))
    return records
