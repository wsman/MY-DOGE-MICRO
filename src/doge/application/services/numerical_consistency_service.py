"""Numerical consistency checks for generated financial artifacts."""

from __future__ import annotations

import re
from typing import Any

from doge.core.domain.agent_models import AgentEvent, EventType


class NumericalConsistencyService:
    """Compare artifact numbers against deterministic tool result numbers."""

    def score_artifact(self, artifact_text: str, events: list[AgentEvent]) -> float | None:
        artifact_numbers = _numbers(artifact_text)
        tool_numbers: list[float] = []
        for event in events:
            if event.event_type == EventType.TOOL_RESULT:
                tool_numbers.extend(_numbers(event.payload.get("result", {})))
        return self.score_numbers(artifact_numbers, tool_numbers)

    def score_numbers(self, artifact_numbers: list[float], reference_numbers: list[float]) -> float | None:
        if not artifact_numbers or not reference_numbers:
            return None
        matched = sum(1 for value in artifact_numbers if any(_near(value, ref) for ref in reference_numbers))
        return matched / len(artifact_numbers)

    def score_claim_numbers(self, claim_text: str, evidence_snippets: list[str]) -> float | None:
        claim_numbers = _numbers(claim_text)
        evidence_numbers: list[float] = []
        for snippet in evidence_snippets:
            evidence_numbers.extend(_numbers(snippet))
        return self.score_numbers(claim_numbers, evidence_numbers)


def _numbers(value: Any) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        result: list[float] = []
        for item in value.values():
            result.extend(_numbers(item))
        return result
    if isinstance(value, list):
        result: list[float] = []
        for item in value:
            result.extend(_numbers(item))
        return result
    text = str(value)
    return [float(item) for item in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", text.replace("%", ""))]


def _near(left: float, right: float) -> bool:
    return abs(left - right) <= max(0.01, abs(right) * 0.01)
