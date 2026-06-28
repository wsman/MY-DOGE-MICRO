"""Financial research evaluation helpers."""

from __future__ import annotations

from typing import Any

from doge.application.services.citation_support_classifier import CitationSupportClassifier
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
        support_classifier: CitationSupportClassifier | None = None,
    ) -> None:
        self._numerical = numerical_service or NumericalConsistencyService()
        self._citation = citation_service or CitationService()
        self._support_classifier = support_classifier or CitationSupportClassifier()

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

    def score_claim_evidence_relations(
        self,
        claims: list[dict[str, Any]],
        citations: list[dict[str, Any]],
        evidence_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        evidence_by_id = {
            str(item.get("evidence_id")): item
            for item in evidence_records
            if item.get("evidence_id")
        }
        claim_by_id = {
            str(item.get("claim_id")): item
            for item in claims
            if item.get("claim_id")
        }
        relations: list[dict[str, Any]] = []
        for citation in citations:
            claim_id = citation.get("claim_id")
            evidence_id = citation.get("evidence_id")
            if not claim_id or not evidence_id:
                continue
            claim = claim_by_id.get(str(claim_id))
            evidence = evidence_by_id.get(str(evidence_id), {})
            claim_text = str((claim or {}).get("claim_text") or (claim or {}).get("text") or "")
            snippet = str(
                citation.get("snippet")
                or evidence.get("support_snippet")
                or evidence.get("text")
                or ""
            )
            classification = self._support_classifier.classify(claim_text, snippet)
            relations.append(
                {
                    "claim_id": str(claim_id),
                    "evidence_id": str(evidence_id),
                    "support_status": classification.support_status,
                    "confidence": classification.confidence,
                    "method": classification.method,
                    "numerical_consistency": self._numerical.score_claim_numbers(claim_text, [snippet]),
                }
            )
        counts = _status_counts(relations)
        return {
            "relations": relations,
            "claim_evidence_relation_count": len(relations),
            "supported_relation_count": counts.get("supported", 0),
            "partial_relation_count": counts.get("partial", 0),
            "unrelated_relation_count": counts.get("unrelated", 0),
            "contradicted_relation_count": counts.get("contradicted", 0),
            "classification_confidence_avg": _average(
                [relation["confidence"] for relation in relations]
            ),
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


def _status_counts(relations: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relation in relations:
        status = str(relation.get("support_status") or "unrelated")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
