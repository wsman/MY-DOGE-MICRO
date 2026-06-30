"""Evaluation helpers for MY-DOGE financial research workflows."""

from doge.eval.metrics import (
    EvaluationScore,
    average_metric,
    binary_precision,
    score_observations,
)
from doge.eval.runner import ObservationRunner, run, run_cases

__all__ = [
    "EvaluationScore",
    "ObservationRunner",
    "average_metric",
    "binary_precision",
    "run",
    "run_cases",
    "score_observations",
]
