"""Reusable evaluation metrics for financial research agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationScore:
    """Aggregated deterministic evaluation result."""

    case_count: int
    observed_case_count: int
    metrics: dict[str, float | None]


def binary_precision(*, expected: set[str], observed: set[str]) -> float | None:
    """Return precision for set-valued observations."""

    if not observed:
        return 1.0 if not expected else 0.0
    return len(expected & observed) / len(observed)


def average_metric(values: list[float | int | None]) -> float | None:
    """Return the arithmetic average for present numeric values."""

    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def score_observations(observations: dict[str, dict[str, Any]]) -> EvaluationScore:
    """Score common observation fields emitted by runtime benchmark runners."""

    metrics = {
        "citation_precision": average_metric([
            binary_precision(
                expected=set(item.get("expected_evidence_ids") or item.get("retrieved_evidence_ids", [])),
                observed=set(item.get("cited_evidence_ids", [])),
            )
            for item in observations.values()
        ]),
        "usage_cost_record_coverage": average_metric([
            1.0 if item.get("usage") else 0.0
            for item in observations.values()
        ]),
        "avg_cost_usd": average_metric([
            (item.get("usage") or {}).get("cost_usd")
            for item in observations.values()
        ]),
        "avg_latency_ms": average_metric([
            item.get("latency_ms")
            for item in observations.values()
        ]),
    }
    return EvaluationScore(
        case_count=len(observations),
        observed_case_count=sum(1 for item in observations.values() if item),
        metrics=metrics,
    )


__all__ = [
    "EvaluationScore",
    "average_metric",
    "binary_precision",
    "score_observations",
]
