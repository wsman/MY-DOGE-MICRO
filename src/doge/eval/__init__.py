"""Evaluation helpers for MY-DOGE financial research workflows."""

from doge.eval.metrics import (
    EvaluationScore,
    average_metric,
    binary_precision,
    score_observations,
)

__all__ = [
    "EvaluationScore",
    "average_metric",
    "binary_precision",
    "score_observations",
]
