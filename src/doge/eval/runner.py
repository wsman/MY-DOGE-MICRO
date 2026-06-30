"""Small evaluation runner abstractions."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from doge.eval.metrics import EvaluationScore, score_observations

ObservationRunner = Callable[[dict[str, Any]], dict[str, Any]]


def run_cases(cases: Iterable[dict[str, Any]], runner: ObservationRunner) -> dict[str, Any]:
    """Run cases through ``runner`` and return observations plus score."""

    observations = {
        str(case["id"]): runner(case)
        for case in cases
    }
    score: EvaluationScore = score_observations(observations)
    return {
        "observations": observations,
        "score": {
            "case_count": score.case_count,
            "observed_case_count": score.observed_case_count,
            "metrics": score.metrics,
        },
    }


__all__ = ["ObservationRunner", "run_cases"]
